import asyncio
import hashlib
import json
from pathlib import Path

import httpx
import pytest
import yaml
from jsonschema import Draft202012Validator

from dce.app.facts import FactScope
from dce.app.services import AppServices
from dce.common.config import Settings
from dce.mcp.server import McpApplication


@pytest.fixture
def incremental(tmp_path: Path):
    config = {"instance_id": "unit", "base_url": "https://example.invalid", "token": "fake-only"}
    with AppServices(
        Settings(
            catalog_path=tmp_path / "cache.sqlite3",
            gitlab=config,
            portainer=config,
            output_budget=16000,
        )
    ) as services:
        app = McpApplication(
            services,
            live=True,
            read_only=True,
            fact_scope=FactScope(
                gitlab_projects={"g"}, portainer_endpoints={"e"}, portainer_stacks={"t"}
            ),
        )
        yield app


def invoke(app, platform, **args):
    response = asyncio.run(app.call_tool(platform + "_query", {"instance": "unit", **args}))
    tools = {t.name: t for t in asyncio.run(app.list_tools())}
    Draft202012Validator(tools[platform + "_query"].outputSchema).validate(
        response.structuredContent
    )
    assert json.loads(response.content[0].text) == response.structuredContent
    return response


def test_project_jobs_keep_manual_execution_identity_and_strip_secrets(incremental):
    app = incremental
    requests = []

    def handle(r):
        requests.append(r)
        return httpx.Response(
            200,
            json=[
                {
                    "id": 7,
                    "status": "manual",
                    "ref": "topic",
                    "name": "build",
                    "allow_failure": True,
                    "runner": {"token": "hidden"},
                    "pipeline": {
                        "id": 3,
                        "project_id": "g",
                        "sha": "a" * 40,
                        "ref": "topic",
                        "variables": [{"value": "hidden"}],
                    },
                }
            ],
            headers={"X-Next-Page": ""},
        )

    app.services.transports["gitlab"] = httpx.MockTransport(handle)
    response = invoke(
        app, "gitlab", operation="project_jobs", project_id="g", job_statuses=["manual"]
    )
    assert not response.isError
    record = response.structuredContent["data"]["records"][0]
    assert record["status"] == "manual" and record["allow_failure"]
    assert record["pipeline"]["id"] == 3 and record["pipeline"]["sha"] == "a" * 40
    assert "hidden" not in response.model_dump_json()
    assert requests[0].url.path == "/api/v4/projects/g/jobs"
    assert requests[0].url.params.get_list("scope[]") == ["manual"]
    assert all(r.method == "GET" for r in requests)


def test_branch_filter_is_local_and_an_empty_page_can_have_more(incremental):
    app = incremental
    requests = []

    def handle(r):
        requests.append(r)
        page = int(r.url.params["page"])
        return httpx.Response(
            200,
            json=[{"id": page, "ref": "other" if page == 1 else "topic", "status": "manual"}],
            headers={"X-Next-Page": "2" if page == 1 else ""},
        )

    app.services.transports["gitlab"] = httpx.MockTransport(handle)
    first = invoke(app, "gitlab", operation="branch_jobs", project_id="g", ref="topic", limit=1)
    data = first.structuredContent["data"]
    assert data["records"] == [] and data["pagination"]["next_page"] == 2
    assert "BRANCH_FILTER_LOCAL_TO_PROJECT_JOB_PAGE" in data["warnings"]
    assert "EMPTY_JOB_PAGE_NOT_PROOF_OF_NO_BUILD" in data["warnings"]
    second = invoke(
        app, "gitlab", operation="branch_jobs", project_id="g", ref="topic", page=2, limit=1
    )
    assert second.structuredContent["data"]["records"][0]["id"] == 2
    assert not second.structuredContent["data"]["pagination"]["more_available"]
    assert all("ref" not in r.url.params for r in requests)


def test_empty_pipeline_jobs_and_bridges_do_not_expand_scope(incremental):
    app = incremental
    requests = []

    def handle(r):
        requests.append(r)
        bridge = {
            "id": 5,
            "status": "manual",
            "downstream_pipeline": {
                "id": 9,
                "project_id": "foreign",
                "status": "success",
                "ref": "topic",
                "sha": "b" * 40,
                "web_url": "https://private.invalid",
                "token": "hidden",
            },
        }
        return httpx.Response(
            200,
            json=[bridge] if r.url.path.endswith("/bridges") else [],
            headers={"X-Next-Page": ""},
        )

    app.services.transports["gitlab"] = httpx.MockTransport(handle)
    empty = invoke(
        app, "gitlab", operation="jobs", project_id="g", pipeline_id="p", include_retried=True
    )
    assert not empty.isError and empty.structuredContent["data"]["records"] == []
    assert "CHECK_PIPELINE_BRIDGES_AND_JOB_VISIBILITY" in empty.structuredContent["warnings"]
    assert requests[0].url.params["include_retried"] == "true"
    bridges = invoke(app, "gitlab", operation="pipeline_bridges", project_id="g", pipeline_id="p")
    assert bridges.structuredContent["data"]["records"][0]["downstream_pipeline"]["id"] == 9
    assert "DOWNSTREAM_PIPELINES_NOT_EXPANDED" in bridges.structuredContent["warnings"]
    assert (
        "hidden" not in bridges.model_dump_json()
        and "private.invalid" not in bridges.model_dump_json()
    )
    assert len(requests) == 2
    denied = invoke(app, "gitlab", operation="jobs", project_id="foreign", pipeline_id="9")
    assert denied.isError and len(requests) == 2


@pytest.mark.parametrize("status,code", [(401, "AUTH_FAILED"), (403, "PERMISSION_DENIED")])
def test_job_permissions_are_errors_not_empty_success(incremental, status, code):
    app = incremental
    app.services.transports["gitlab"] = httpx.MockTransport(
        lambda _: httpx.Response(status, json={"message": "hidden"})
    )
    for args in (
        {"operation": "project_jobs"},
        {"operation": "branch_jobs", "ref": "topic"},
        {"operation": "pipeline_bridges", "pipeline_id": "p"},
    ):
        response = invoke(app, "gitlab", project_id="g", **args)
        assert response.isError and response.structuredContent["error"]["code"] == code
        assert "hidden" not in response.model_dump_json()


def test_job_cursors_limits_and_explicit_new_trigger_route(incremental):
    app = incremental
    requests = []

    def handle(r):
        requests.append(r)
        return httpx.Response(200, json=[{"id": 1}, {"id": 2}], headers={"X-Next-Page": ""})

    app.services.transports["gitlab"] = httpx.MockTransport(handle)
    result = invoke(
        app,
        "gitlab",
        operation="pipeline_bridges",
        project_id="g",
        pipeline_id="p",
        trigger_api="trigger_jobs",
        limit=1,
    )
    assert requests[0].url.path.endswith("/trigger_jobs")
    assert len(result.structuredContent["data"]["records"]) == 1
    assert result.structuredContent["data"]["pagination"]["next_page"] == 2
    app.services.transports["gitlab"] = httpx.MockTransport(
        lambda _: httpx.Response(200, json=[], headers={"X-Next-Page": "9"})
    )
    assert invoke(app, "gitlab", operation="project_jobs", project_id="g").isError


def test_new_job_selectors_do_not_silently_ignore_contradictory_coordinates(incremental):
    app = incremental
    tools = {t.name: t for t in asyncio.run(app.list_tools())}
    validator = Draft202012Validator(tools["gitlab_query"].inputSchema)
    for args in (
        {"operation": "project_jobs", "ref": "topic"},
        {"operation": "project_jobs", "pipeline_id": "q"},
        {"operation": "branch_jobs", "ref": "topic", "pipeline_id": "q"},
        {"operation": "project_jobs", "include_retried": True},
    ):
        parameters = {"instance": "unit", "project_id": "g", **args}
        assert not validator.is_valid(parameters)
        assert invoke(app, "gitlab", project_id="g", **args).isError
    app.services.transports["gitlab"] = httpx.MockTransport(
        lambda _: httpx.Response(200, json=[{"id": 1}], headers={"X-Next-Page": ""})
    )
    result = invoke(app, "gitlab", operation="branch_jobs", project_id="g", ref="topic")
    assert "JOB_REF_UNAVAILABLE_ON_UPSTREAM_PAGE" in result.structuredContent["warnings"]


def test_incremental_schemas_require_arguments_before_reader(incremental):
    app = incremental
    tools = {t.name: t for t in asyncio.run(app.list_tools())}
    assert len(tools) == 9
    for platform, args in (
        ("gitlab", {"operation": "branch_jobs", "project_id": "g"}),
        ("gitlab", {"operation": "pipeline_bridges", "project_id": "g"}),
        ("portainer", {"operation": "stack_service", "stack_id": "t", "endpoint_id": "e"}),
    ):
        validator = Draft202012Validator(tools[platform + "_query"].inputSchema)
        assert not validator.is_valid({"instance": "unit", **args})
        assert invoke(app, platform, **args).isError


def stack_transport(text, calls, endpoint="e"):
    def handle(r):
        calls.append(r)
        assert r.method == "GET"
        return httpx.Response(
            200,
            json={"StackFileContent": text}
            if r.url.path.endswith("/file")
            else {"Id": "t", "EndpointId": endpoint},
        )

    return httpx.MockTransport(handle)


def test_stack_service_is_filtered_before_output_and_unrelated_service_parsing(incremental):
    app = incremental
    services = {f"unrelated-{i}": {"image": "synthetic:v1"} for i in range(400)}
    services["target"] = {
        "image": "synthetic:v2",
        "environment": {"PASSWORD": "hidden-value"},
        "command": "do not execute",
        "ports": ["127.0.0.1:8080:80/tcp", {"target": 90, "published": 9090}],
        "labels": {"password": "hidden-value", "com.docker.stack.namespace": "demo"},
        "deploy": {"mode": "replicated", "replicas": 2},
    }
    text = yaml.safe_dump({"services": services})
    calls = []
    app.services.settings.output_budget = 8192
    app.services.transports["portainer"] = stack_transport(text, calls)
    full = invoke(app, "portainer", operation="stack_file", stack_id="t", endpoint_id="e")
    assert full.structuredContent["truncated"] and full.structuredContent["data"] is None
    services["bad-unrelated"] = {"image": "https://invalid.example.invalid/not-an-oci-reference"}
    text = yaml.safe_dump({"services": services})
    app.services.transports["portainer"] = stack_transport(text, calls)
    target = invoke(
        app,
        "portainer",
        operation="stack_service",
        stack_id="t",
        endpoint_id="e",
        service_name="target",
    )
    assert not target.isError and not target.structuredContent["truncated"]
    data = target.structuredContent["data"]
    record = data["records"][0]
    assert record["name"] == "target" and record["image"]["tag"] == "v2"
    assert record["deploy"] == {"mode": "replicated", "replicas": 2}
    assert record["ports"][0] == {"published": "8080", "target": "80", "protocol": "tcp"}
    assert record["stack_file_revision"] == hashlib.sha256(text.encode()).hexdigest()
    assert data["evidence"] and len(data["records"]) == 1
    for private in ("hidden-value", "do not execute", "unrelated-", "127.0.0.1"):
        assert private not in target.model_dump_json()


def test_stack_service_missing_scope_endpoint_and_unresolved_yaml(incremental):
    app = incremental
    calls = []
    app.services.transports["portainer"] = stack_transport("services: {}", calls)
    response = invoke(
        app,
        "portainer",
        operation="stack_service",
        stack_id="t",
        endpoint_id="e",
        service_name="missing",
    )
    assert response.structuredContent["error"]["code"] == "NOT_FOUND"
    calls.clear()
    assert invoke(
        app,
        "portainer",
        operation="stack_service",
        stack_id="foreign",
        endpoint_id="e",
        service_name="target",
    ).isError
    assert calls == []
    app.services.transports["portainer"] = stack_transport("services: {}", calls, endpoint="other")
    assert invoke(
        app,
        "portainer",
        operation="stack_service",
        stack_id="t",
        endpoint_id="e",
        service_name="target",
    ).isError
    assert len(calls) == 1
    for text in ("services: []", "services: &x {target: {image: demo:v1}}\ncopy: *x"):
        app.services.transports["portainer"] = stack_transport(text, [])
        assert invoke(
            app,
            "portainer",
            operation="stack_service",
            stack_id="t",
            endpoint_id="e",
            service_name="target",
        ).isError


def test_stack_service_marks_unresolved_safe_fields_without_exposing_values(incremental):
    app = incremental
    text = yaml.safe_dump(
        {
            "services": {
                "target": {
                    "image": "synthetic:v1",
                    "labels": ["com.docker.stack.namespace=demo", "PASSWORD=hidden"],
                    "deploy": {"replicas": "${UNRESOLVED}", "mode": "unsupported"},
                    "ports": [
                        "80/unsupported",
                        {"target": "hidden", "protocol": "hidden", "mode": "hidden"},
                    ],
                }
            }
        }
    )
    app.services.transports["portainer"] = stack_transport(text, [])
    result = invoke(
        app,
        "portainer",
        operation="stack_service",
        stack_id="t",
        endpoint_id="e",
        service_name="target",
    )
    assert not result.isError
    data = result.structuredContent["data"]["records"][0]
    assert data["incomplete"] and data["deploy"] == {}
    assert "hidden" not in result.model_dump_json()
    app.services.transports["portainer"] = stack_transport(
        "services: {api..one: {image: synthetic:v1}}", []
    )
    literal_key = invoke(
        app,
        "portainer",
        operation="stack_service",
        stack_id="t",
        endpoint_id="e",
        service_name="api..one",
    )
    assert not literal_key.isError
    assert literal_key.structuredContent["data"]["records"][0]["name"] == "api..one"


def test_malformed_environment_entries_are_not_serialized_as_names(incremental):
    app = incremental
    text = yaml.safe_dump(
        {
            "services": {
                "target": {
                    "image": "synthetic:v1",
                    "environment": [
                        {"PASSWORD": "never-output"},
                        "{bad: never-output}",
                        "GOOD=never-output",
                    ],
                }
            }
        }
    )
    app.services.transports["portainer"] = stack_transport(text, [])
    result = invoke(
        app,
        "portainer",
        operation="stack_service",
        stack_id="t",
        endpoint_id="e",
        service_name="target",
    )
    assert not result.isError
    record = result.structuredContent["data"]["records"][0]
    assert record["incomplete"] and record["environment_names"] == ["GOOD"]
    assert "never-output" not in result.model_dump_json()


def test_malformed_job_metadata_does_not_leak_nested_platform_configuration(incremental):
    app = incremental
    for record in (
        {"id": 1, "name": {"internal": "never-output"}},
        {"id": 1, "pipeline": {"ref": {"internal": "never-output"}}},
    ):
        app.services.transports["gitlab"] = httpx.MockTransport(
            lambda _, data=record: httpx.Response(200, json=[data])
        )
        response = invoke(app, "gitlab", operation="project_jobs", project_id="g")
        assert response.isError and "never-output" not in response.model_dump_json()
