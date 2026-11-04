import asyncio
import copy
import json
from pathlib import Path

import httpx
import pytest
from jsonschema import Draft202012Validator, ValidationError
from pydantic import SecretStr

from dce.app.services import AppServices
from dce.common.config import PlatformConfig, Settings
from dce.graph.model import DiscoveryResult, Entity
from dce.mcp.server import McpApplication


def test_list_tools_explains_platform_source_and_session_without_requests(tmp_path: Path) -> None:
    cases = [
        (False, False, None, False, "synthetic", "fixture"),
        (True, False, None, False, "blocked", "upstream"),
        (True, True, None, False, "blocked", "upstream"),
        (True, True, "http", False, "blocked", "upstream"),
        (True, True, "https", False, "configured_not_verified", "upstream"),
        (True, True, "http", True, "configured_not_verified", "upstream"),
    ]
    for live, scope, scheme, allow_http, status, source in cases:
        config = (
            PlatformConfig(
                instance_id="synthetic-source",
                base_url=f"{scheme}://example.invalid",
                token=SecretStr("synthetic-secret-not-for-tool-metadata"),
            )
            if scheme
            else None
        )
        with AppServices(
            Settings(
                catalog_path=tmp_path / "catalog.sqlite3",
                gitlab=config,
                zentao=config,
                allow_http=allow_http,
            )
        ) as services:

            def refuse_reader(*_: object) -> None:
                pytest.fail("Capability inspection must not open an upstream Reader.")

            services.reader = refuse_reader  # type: ignore[method-assign,assignment]
            server = McpApplication(
                services,
                live=live,
                read_only=live,
                allowed_bug_ids={"private-authorized-bug"} if scope else set(),
                allowed_gitlab_projects={"private-authorized-project"} if scope else set(),
            )
            tools = {t.name: t for t in asyncio.run(server.list_tools())}
            assert len(tools) == 9 and "mcp_auth" not in tools
            for name, platform in (("bug_context", "ZenTao"), ("pipeline_diagnose", "GitLab")):
                tool = tools[name]
                assert platform in tool.description and status in tool.description
                assert tool.meta["dce"]["availability"] == status
                assert tool.meta["dce"]["data_source"] == source
                assert tool.annotations.openWorldHint == (status == "configured_not_verified")
            assert "Portainer" in tools["deployment_inspect"].description
            assert "no live" in tools["deployment_inspect"].description.lower()
            for name in (
                "project_context",
                "service_trace",
                "deployment_inspect",
                "discovery_status",
            ):
                assert "Catalog" in tools[name].description
                assert tools[name].meta["dce"]["data_source"] == "catalog"
                assert tools[name].annotations.openWorldHint is False
            published = json.dumps([t.model_dump() for t in tools.values()])
            for private in (
                "example.invalid",
                "synthetic-secret-not-for-tool-metadata",
                "private-authorized-bug",
                "private-authorized-project",
            ):
                assert private not in published
            for tool in tools.values():
                Draft202012Validator.check_schema(tool.inputSchema)
                Draft202012Validator.check_schema(tool.outputSchema)
                assert all(p.get("description") for p in tool.inputSchema["properties"].values())


def test_deployment_schema_matches_runtime_exclusive_resource_rule(tmp_path: Path) -> None:
    with AppServices(Settings(catalog_path=tmp_path / "catalog.sqlite3")) as services:
        server = McpApplication(services)
        tools = {t.name: t for t in asyncio.run(server.list_tools())}
        validate = Draft202012Validator(tools["deployment_inspect"].inputSchema)
        for good in (
            {"stack_key": "102"},
            {"service_key": "service-id"},
            {"stack_key": "102", "service_key": None},
        ):
            validate.validate(good)
        for bad in (
            {},
            {"stack_key": None},
            {"stack_key": "102", "service_key": "id"},
            {"stack_key": ""},
            {"service_key": "https://example.invalid"},
            {"stack_key": "../private"},
            {"stack_key": "x" * 251},
            {"stack_key": "102", "unexpected": True},
        ):
            assert not validate.is_valid(bad), bad
            result = asyncio.run(server.call_tool("deployment_inspect", bad))
            assert result.isError and result.structuredContent["error"]["code"] == "INVALID_PAYLOAD"


def test_published_output_schemas_validate_success_errors_and_budget(tmp_path: Path) -> None:
    # Full-shape checks need room for both the text and structured copies of graph responses.
    with AppServices(
        Settings(catalog_path=tmp_path / "catalog.sqlite3", output_budget=64000)
    ) as services:
        services.initialize()
        orphan = Entity(source_instance="demo", kind="service", external_id="orphan")
        services.catalog.import_scan(DiscoveryResult(entities=[orphan]), scope="synthetic-orphan")
        server = McpApplication(services)
        tools = {t.name: t for t in asyncio.run(server.list_tools())}
        service_id = services.catalog.list_entities(kind="service")["items"][0]["id"]
        cases = [
            ("bug_context", {"bug_id": "DEMO-1001", "include_assets": True}, "bug_id"),
            ("pipeline_diagnose", {"project_key": "1001", "pipeline_id": "2001"}, "failures"),
            ("project_context", {"source": "gitlab-demo", "project_key": "1001"}, "project"),
            ("service_trace", {"service_key": service_id}, "resource"),
            ("deployment_inspect", {"stack_key": "102"}, "stack"),
            ("deployment_inspect", {"service_key": orphan.id}, "service"),
            ("discovery_status", {}, "items"),
        ]
        for name, args, required_field in cases:
            response = asyncio.run(server.call_tool(name, args))
            assert not response.isError
            payload = response.structuredContent
            validator = Draft202012Validator(tools[name].outputSchema)
            validator.validate(payload)
            damaged = copy.deepcopy(payload)
            del damaged["data"][required_field]
            with pytest.raises(ValidationError):
                validator.validate(damaged)
            damaged = copy.deepcopy(payload)
            damaged["data"] = None
            damaged["truncated"] = False
            assert not validator.is_valid(damaged)
            error = asyncio.run(server.call_tool(name, {"unexpected": True}))
            assert error.isError
            validator.validate(error.structuredContent)
            missing_version = copy.deepcopy(payload)
            del missing_version["schema_version"]
            assert not validator.is_valid(missing_version)
        stack = asyncio.run(server.call_tool("deployment_inspect", {"stack_key": "102"}))
        assert all(s["observed_at"] for s in stack.structuredContent["data"]["snapshots"])
        services.settings.output_budget = 1024
        result = asyncio.run(server.call_tool("deployment_inspect", {"stack_key": "102"}))
        assert result.structuredContent["truncated"] and result.structuredContent["data"] is None
        Draft202012Validator(tools["deployment_inspect"].outputSchema).validate(
            result.structuredContent
        )


def test_live_adapter_results_match_published_schemas_with_synthetic_http(tmp_path: Path) -> None:
    calls = []

    def handle(request: httpx.Request) -> httpx.Response:
        calls.append((request.method, request.url.path))
        path = request.url.path
        if path.endswith("/bugs/1"):
            return httpx.Response(
                200,
                json={
                    "id": 1,
                    "title": "synthetic bug",
                    "steps": "<p>synthetic steps</p>",
                    "project": {"id": 2},
                    "files": [],
                },
            )
        if path.endswith("/trace"):
            return httpx.Response(200, text="Token=synthetic-private\nmake: not found")
        if path.endswith("/jobs"):
            return httpx.Response(200, json=[{"id": 3, "status": "failed", "stage": None}])
        if "/pipelines/" in path:
            return httpx.Response(200, json={"id": 2, "status": "failed"})
        return httpx.Response(200, json={"id": 1, "default_branch": None})

    config = PlatformConfig(
        instance_id="demo", base_url="https://example.invalid", token=SecretStr("synthetic-private")
    )
    with AppServices(
        Settings(catalog_path=tmp_path / "catalog.sqlite3", zentao=config, gitlab=config),
        transports={kind: httpx.MockTransport(handle) for kind in ("zentao", "gitlab")},
    ) as services:
        server = McpApplication(
            services,
            live=True,
            read_only=True,
            allowed_bug_ids={"1"},
            allowed_gitlab_projects={"1"},
        )
        tools = {t.name: t for t in asyncio.run(server.list_tools())}
        for name, arguments in (
            ("bug_context", {"bug_id": "1"}),
            ("pipeline_diagnose", {"project_key": "1", "pipeline_id": "2"}),
        ):
            response = asyncio.run(server.call_tool(name, arguments))
            assert not response.isError
            Draft202012Validator(tools[name].outputSchema).validate(response.structuredContent)
            assert "synthetic-private" not in json.dumps(response.structuredContent)
        assert all(method == "GET" for method, _ in calls)
        assert len(calls) == 5


def test_invalid_service_output_fails_safely_against_published_contract(tmp_path: Path) -> None:
    with AppServices(Settings(catalog_path=tmp_path / "catalog.sqlite3")) as services:

        def malformed(*_: object, **__: object) -> dict[str, object]:
            return {"project": {"private": "synthetic-upstream-secret"}}

        services.project_context = malformed  # type: ignore[method-assign]
        server = McpApplication(services)
        tools = {t.name: t for t in asyncio.run(server.list_tools())}
        response = asyncio.run(
            server.call_tool("project_context", {"source": "demo", "project_key": "1"})
        )
        assert response.isError
        assert response.structuredContent["error"]["code"] == "INVALID_PAYLOAD"
        assert "synthetic-upstream-secret" not in json.dumps(response.structuredContent)
        Draft202012Validator(tools["project_context"].outputSchema).validate(
            response.structuredContent
        )
