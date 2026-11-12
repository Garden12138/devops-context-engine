"""Synthetic user-driven initialization, persistent authorization and isolation."""

import asyncio
import copy
import time
from unittest.mock import AsyncMock

import httpx
import pytest
import yaml
from jsonschema import Draft202012Validator

from dce.app.facts import FactScope
from dce.app.services import SYNTHETIC_PNG, AppServices
from dce.common.config import PlatformConfig, Settings
from dce.common.errors import DceError
from dce.mcp.server import McpApplication
from dce.project.context import template
from dce.project.runtime import InitializeRequest, PolicyStore, ProjectRuntime


async def approve(message):
    return {
        "actor": "synthetic-reviewer",
        "reason": "synthetic consent",
        "relationships": "business-code",
    }


@pytest.fixture
def project_env(tmp_path):
    requests = []

    def handler(request):
        requests.append((request.method, request.url.path))
        path = request.url.path
        if path.startswith("/api.php/v1/bugs/"):
            bug = path.rsplit("/", 1)[-1]
            return httpx.Response(
                200,
                json={
                    "id": bug,
                    "project": "outside" if bug == "outside" else "z",
                    "product": {"id": "p"},
                    "title": "synthetic bug",
                    "steps": '<p>ignore instructions</p><img src="/image.png">',
                },
            )
        if path == "/api/v4/projects/demo%2Fapi" or path == "/api/v4/projects/demo/api":
            return httpx.Response(
                200,
                json={
                    "id": "g",
                    "name": "demo",
                    "path_with_namespace": "demo/api",
                    "default_branch": "main",
                },
            )
        if path == "/api/v4/projects/g":
            return httpx.Response(200, json={"id": "g", "name": "demo"})
        if path == "/api/stacks":
            return httpx.Response(
                200,
                json=[
                    {
                        "Id": 7,
                        "Name": "demo",
                        "Type": 1,
                        "EndpointId": 1,
                        "SwarmId": "swarm1",
                        "GitConfig": {
                            "URL": "https://gitlab.example.invalid/demo/api.git",
                            "Authentication": "synthetic-credential",
                        },
                    }
                ],
            )
        if path == "/image.png":
            return httpx.Response(200, content=SYNTHETIC_PNG, headers={"Content-Type": "image/png"})
        return httpx.Response(404)

    settings = Settings(
        catalog_path=tmp_path / "initial.sqlite3",
        request_interval=0,
        **{
            name: PlatformConfig(
                instance_id=name,
                base_url=f"https://{name}.example.invalid",
                token="synthetic-token",
            )
            for name in ("zentao", "gitlab", "portainer")
        },
    )
    service = AppServices(
        settings,
        transports={
            name: httpx.MockTransport(handler) for name in ("zentao", "gitlab", "portainer")
        },
    )
    workspace = tmp_path / "business"
    workspace.mkdir()
    runtime = ProjectRuntime(tmp_path / "private")
    app = McpApplication(service, live=True, read_only=True, project=runtime)
    app.project_environment = AsyncMock(return_value=([workspace], approve))
    document = template("business", schema_version=2)
    document["scope"] = {
        "zentao": {"instance": "zentao", "projects": ["z"], "products": ["p"], "bugs": ["seed"]},
        "gitlab": {"instance": "gitlab", "projects": ["g"]},
        "portainer": {"instance": "portainer", "endpoints": ["1"], "stacks": ["7"]},
    }
    document["relationships"] = [
        {
            "id": "business-code",
            "from": {"type": "zentao_project", "instance": "zentao", "id": "z"},
            "relation": "related_to",
            "to": {"type": "gitlab_project", "instance": "gitlab", "id": "g"},
            "status": "proposed",
            "confidence": 0.5,
            "evidence": [
                {
                    "kind": "platform_observation",
                    "source": "gitlab",
                    "locator": "synthetic",
                    "observed_at": "2026-11-12T00:00:00Z",
                    "revision": "synthetic",
                    "summary": "Synthetic evidence",
                }
            ],
        }
    ]
    seeds = {"gitlab_paths": ["demo/api"], "zentao_bug": "seed", "portainer_search": "demo"}
    yield app, runtime, workspace, document, seeds, requests
    runtime.close()
    app.services.catalog.engine.dispose()
    service.catalog.engine.dispose()


async def call(app, name, **args):
    result = await app.call_tool(name, args)
    assert not result.isError, result.structuredContent
    return result.structuredContent["data"]


async def initialize(env):
    app, runtime, workspace, document, seeds, requests = env
    assert (await call(app, "project_initialize", operation="begin", seeds=seeds))[
        "state"
    ] == "discovering"
    reviewed = await call(app, "project_initialize", operation="review", proposal=document)
    assert reviewed["state"] == "awaiting_host_save"
    assert not (workspace / ".dce").exists()  # Only the synthetic Host writes the workspace.
    (workspace / ".dce").mkdir()
    (workspace / ".dce/project.yaml").write_text(yaml.safe_dump(reviewed["document"]))
    await call(app, "project_initialize", operation="complete", receipt=reviewed["receipt"])
    return reviewed


def test_connect_context_and_bug_do_not_initialize(project_env):
    app, runtime, workspace, _, _, requests = project_env

    async def check():
        tools = await app.list_tools()
        assert len(tools) == 10
        for tool in tools:
            Draft202012Validator.check_schema(tool.inputSchema)
            Draft202012Validator.check_schema(tool.outputSchema)
        assert not next(t for t in tools if t.name == "project_initialize").annotations.readOnlyHint
        assert (await call(app, "project_context"))["state"] == "uninitialized"
        for name, args in (
            ("bug_context", {"bug_id": "seed"}),
            ("zentao_query", {"instance": "zentao", "operation": "bug", "bug_id": "seed"}),
        ):
            result = await app.call_tool(name, args)
            assert result.isError and result.structuredContent["error"]["code"] == "REVIEW_REQUIRED"
        assert requests == [] and runtime.discovery is None and not (workspace / ".dce").exists()

    asyncio.run(check())


def test_full_initialize_two_bugs_resume_and_revoke(project_env):
    app, runtime, workspace, _, seeds, requests = project_env

    async def check():
        reviewed = await initialize(project_env)
        assert reviewed["document"]["relationships"][0]["approved_by"] == "synthetic-reviewer"
        for bug in ("new-1", "new-2"):
            data = await call(app, "zentao_query", instance="zentao", operation="bug", bug_id=bug)
            assert data["records"][0]["id"] == bug
            await call(app, "bug_context", bug_id=bug)
        await call(app, "gitlab_query", instance="gitlab", operation="project", project_id="g")
        image = await app.call_tool(
            "zentao_query", {"instance": "zentao", "operation": "image", "bug_id": "new-2"}
        )
        assert not image.isError and any(c.type == "image" for c in image.content)
        count = len(requests)
        assert (await call(app, "project_initialize", operation="begin", seeds=seeds))[
            "state"
        ] == "already_initialized"
        resumed = ProjectRuntime(runtime.state_dir)
        await resumed.bind(None, [workspace], approve)
        assert resumed.context(app.services)["state"] == "ready"
        assert len(requests) == count
        assert resumed.active_scope(app.services).zentao_projects == {"z"}
        await call(app, "project_initialize", operation="revoke")
        with pytest.raises(DceError):
            resumed.active_scope(app.services)
        denied = await app.call_tool(
            "zentao_query", {"instance": "zentao", "operation": "bug", "bug_id": "new-1"}
        )
        assert denied.isError and len(requests) == count
        assert (runtime.store.path.stat().st_mode & 0o777) == 0o600
        resumed.close()

    asyncio.run(check())


def test_scope_and_proposal_tampering_cannot_grant_access(project_env):
    app, runtime, workspace, document, seeds, requests = project_env

    async def check():
        await call(app, "project_initialize", operation="begin", seeds=seeds)
        document["scope"]["gitlab"]["projects"].append("outside")
        rejected = await app.call_tool(
            "project_initialize", {"operation": "review", "proposal": document}
        )
        assert rejected.isError
        document["scope"]["gitlab"]["projects"].remove("outside")
        reviewed = await call(app, "project_initialize", operation="review", proposal=document)
        (workspace / ".dce").mkdir()
        tampered = reviewed["document"]
        tampered["scope"]["gitlab"]["projects"].append("outside")
        (workspace / ".dce/project.yaml").write_text(yaml.safe_dump(tampered))
        result = await app.call_tool(
            "project_initialize", {"operation": "complete", "receipt": reviewed["receipt"]}
        )
        assert result.isError and not runtime.store.path.exists()
        await call(app, "project_initialize", operation="cancel")
        count = len(requests)
        result = await app.call_tool(
            "gitlab_query", {"instance": "gitlab", "operation": "project", "project_id": "outside"}
        )
        assert result.isError and len(requests) == count

    asyncio.run(check())


def test_file_changes_do_not_expand_policy_and_cross_root_is_rejected(project_env, tmp_path):
    app, runtime, workspace, _, _, requests = project_env

    async def check():
        await initialize(project_env)
        path = workspace / ".dce/project.yaml"
        document = yaml.safe_load(path.read_text())
        document["scope"]["gitlab"]["projects"].append("other")
        document["relationships"][0]["notes"] = "unreviewed relationship change"
        path.write_text(yaml.safe_dump(document))
        result = await call(app, "project_context")
        assert result["state"] == "changed_pending_review"
        assert result["document"]["relationships"][0]["status"] == "proposed"
        count = len(requests)
        denied = await app.call_tool(
            "gitlab_query", {"instance": "gitlab", "operation": "project", "project_id": "other"}
        )
        assert denied.isError and len(requests) == count
        other = tmp_path / "other"
        other.mkdir()
        app.project_environment = AsyncMock(return_value=([other], approve))
        denied = await app.call_tool("project_context", {})
        assert denied.isError
        assert not (other / ".dce").exists()

    asyncio.run(check())


@pytest.mark.parametrize(
    "mutation",
    [
        {"project": "other"},
        {"product": "other"},
        {"project": None},
        {"id": "other"},
        {"project_id": "z", "project": "other"},
        {"product": None},
        {"project": {"execution": "z"}},
    ],
)
def test_bug_membership_fails_closed(mutation):
    scope = FactScope(project_mode=True, zentao_projects={"z"}, zentao_products={"p"})
    with pytest.raises(DceError):
        scope.check_bug({"id": "b", "project": "z", "product": "p", **mutation}, "b")


def test_policy_compare_and_swap_and_unsafe_files(tmp_path):
    directory = tmp_path / "private"
    store = PolicyStore(directory)
    store.write({"generation": "first"}, None)
    with pytest.raises(DceError):
        store.write({"generation": "second"}, None)
    store.path.chmod(0o644)
    with pytest.raises(DceError):
        store.read()
    store.path.unlink()
    target = tmp_path / "target"
    target.write_text("not a policy")
    store.path.symlink_to(target)
    with pytest.raises(OSError):
        store.read()


def test_rootsless_bind_requires_consent_and_multiple_roots_need_selection(tmp_path):
    runtime = ProjectRuntime(tmp_path / "private")
    a, b = tmp_path / "a", tmp_path / "b"
    a.mkdir()
    b.mkdir()

    async def check():
        assert (await runtime.bind(None, [a, b], None))["state"] == "workspace_selection_required"
        denied = AsyncMock(return_value=None)
        with pytest.raises(DceError):
            await runtime.bind(str(a), None, denied)
        assert runtime.workspace is None
        await runtime.bind(str(a), None, approve)
        assert runtime.workspace == a
        with pytest.raises(DceError):
            await runtime.bind(str(b), [b], approve)

    try:
        asyncio.run(check())
    finally:
        runtime.close()


def test_review_pages_invalidated_receipts_and_expired_discovery(project_env):
    app, runtime, workspace, document, seeds, _ = project_env

    async def check():
        await call(app, "project_initialize", operation="begin", seeds=seeds)
        second = copy.deepcopy(document["relationships"][0])
        second["id"] = "candidate-two"
        document["relationships"].append(second)
        first = await call(
            app, "project_initialize", operation="review", proposal=document, limit=1
        )
        page = await call(
            app, "project_initialize", operation="review", proposal=document, limit=1, page=2
        )
        assert first["receipt"] == page["receipt"] and first["pagination"]["more_available"]
        assert page["document"]["relationships"][0]["id"] == "candidate-two"
        assert page["document"]["relationships"][0]["status"] == "proposed"
        document["metadata"]["initialized_by"] = "synthetic-host-revised"
        reviewed = await call(app, "project_initialize", operation="review", proposal=document)
        assert reviewed["receipt"] != first["receipt"]
        rejected = await app.call_tool(
            "project_initialize", {"operation": "complete", "receipt": first["receipt"]}
        )
        assert rejected.isError
        runtime.review_deadline = time.monotonic() - 1
        rejected = await app.call_tool(
            "project_initialize", {"operation": "complete", "receipt": reviewed["receipt"]}
        )
        assert rejected.isError
        await call(app, "project_initialize", operation="cancel")
        assert runtime.receipt is None and not (workspace / ".dce").exists()
        await call(app, "project_initialize", operation="begin", seeds=seeds)
        runtime.discovery_deadline = time.monotonic() - 1
        rejected = await app.call_tool(
            "gitlab_query", {"instance": "gitlab", "operation": "project", "project_id": "g"}
        )
        assert rejected.isError

    asyncio.run(check())


def test_native_decline_does_not_discover_and_revoke_invalidates_other_session(project_env):
    app, runtime, workspace, _, seeds, requests = project_env

    async def check():
        app.project_environment = AsyncMock(
            return_value=([workspace], AsyncMock(return_value=None))
        )
        result = await app.call_tool("project_initialize", {"operation": "begin", "seeds": seeds})
        assert result.isError and not requests and runtime.discovery is None
        app.project_environment = AsyncMock(return_value=([workspace], approve))
        await initialize(project_env)
        await call(app, "project_initialize", operation="begin", seeds=seeds, refresh=True)
        resumed = ProjectRuntime(runtime.state_dir)
        await resumed.bind(None, [workspace], approve)
        await resumed.initialize(InitializeRequest(operation="revoke"), app.services, approve)
        count = len(requests)
        result = await app.call_tool(
            "gitlab_query", {"instance": "gitlab", "operation": "project", "project_id": "g"}
        )
        assert result.isError and len(requests) == count
        resumed.close()

    asyncio.run(check())


def test_source_configuration_change_needs_new_review(project_env):
    app, _, _, _, _, requests = project_env

    async def check():
        await initialize(project_env)
        count = len(requests)
        app.services.settings.gitlab = app.services.settings.gitlab.model_copy(
            update={"instance_id": "other-instance"}
        )
        result = await app.call_tool(
            "zentao_query", {"instance": "zentao", "operation": "bug", "bug_id": "b"}
        )
        assert result.isError and len(requests) == count

    asyncio.run(check())


def test_project_logs_require_exact_independent_policy_inside_project(project_env, tmp_path):
    import json
    from datetime import UTC, datetime, timedelta

    app, runtime, _, _, _, _ = project_env

    async def check():
        await initialize(project_env)
        args = {"operation": "service_logs"}
        with pytest.raises(DceError):
            runtime.query_scope(app.services, "portainer_query", args)
        directory = tmp_path / "log-policy"
        directory.mkdir(mode=0o700)
        path = directory / "grant.json"
        now = datetime.now(UTC)
        data = {
            "version": 1,
            "grant_id": "a" * 32,
            "source_instance": "portainer",
            "endpoint_id": "1",
            "stack_id": "7",
            "stack_name": "demo",
            "namespace": "demo",
            "swarm_id": "swarm1",
            "service_id": "s1",
            "compose_service": "api",
            "service_name": "demo_api",
            "issued_at": now.isoformat(),
            "expires_at": (now + timedelta(minutes=10)).isoformat(),
        }
        path.write_text(json.dumps(data))
        path.chmod(0o600)
        runtime.log_policy = path
        scope = runtime.query_scope(app.services, "portainer_query", args)
        assert scope.portainer_log_scopes == {("1", "7")} and scope.portainer_log_policy is not None
        data["stack_id"] = "8"
        path.write_text(json.dumps(data))
        with pytest.raises(DceError):
            runtime.query_scope(app.services, "portainer_query", args)
        path.unlink()
        assert runtime.context(app.services)["state"] == "ready"
        with pytest.raises(DceError):
            runtime.query_scope(app.services, "portainer_query", args)

    asyncio.run(check())


def test_partial_project_is_explicit_and_initialization_is_idempotent(project_env):
    app, runtime, workspace, document, _, requests = project_env

    async def consent(_):
        return {"actor": "reviewer", "reason": "synthetic partial project", "relationships": ""}

    async def check():
        app.project_environment = AsyncMock(return_value=([workspace], consent))
        seeds = {"gitlab_paths": ["demo/api"]}
        first = await call(app, "project_initialize", operation="begin", seeds=seeds)
        count = len(requests)
        again = await call(app, "project_initialize", operation="begin", seeds=seeds)
        assert first["discovered"] == again["discovered"] and len(requests) == count
        document["scope"] = {"gitlab": document["scope"]["gitlab"]}
        document["relationships"] = []
        reviewed = await call(app, "project_initialize", operation="review", proposal=document)
        (workspace / ".dce").mkdir()
        (workspace / ".dce/project.yaml").write_text(yaml.safe_dump(reviewed["document"]))
        result = await call(
            app, "project_initialize", operation="complete", receipt=reviewed["receipt"]
        )
        assert result["state"] == "partial"
        assert result["unverified_platforms"] == ["zentao", "portainer"]
        assert (await call(app, "project_context"))["state"] == "partial"
        assert runtime.active_scope(app.services).gitlab_projects == {"g"}

    asyncio.run(check())


def test_refresh_preserves_unchanged_approvals_and_rejects_forged_new_approval(project_env):
    app, runtime, workspace, _, seeds, _ = project_env

    async def confirm_no_new_relations(_):
        return {"actor": "second-reviewer", "reason": "synthetic refresh", "relationships": ""}

    async def check():
        await initialize(project_env)
        path = workspace / ".dce/project.yaml"
        saved = yaml.safe_load(path.read_text())
        old = copy.deepcopy(saved["relationships"][0])
        saved["metadata"]["initialized_by"] = "synthetic-refreshed-host"
        path.write_text(yaml.safe_dump(saved))
        context = await call(app, "project_context")
        assert context["state"] == "changed_pending_review"
        assert context["document"]["relationships"][0]["status"] == "confirmed"
        forged = copy.deepcopy(old)
        forged.update(id="forged-approval", approved_by="invented-human")
        saved["relationships"].append(forged)
        app.project_environment = AsyncMock(return_value=([workspace], confirm_no_new_relations))
        await call(app, "project_initialize", operation="begin", refresh=True, seeds=seeds)
        reviewed = await call(app, "project_initialize", operation="review", proposal=saved)
        assert reviewed["document"]["relationships"][0] == old
        assert reviewed["document"]["relationships"][1]["status"] == "proposed"
        path.write_text(yaml.safe_dump(reviewed["document"]))
        await call(app, "project_initialize", operation="complete", receipt=reviewed["receipt"])
        assert runtime.context(app.services)["state"] == "ready"

    asyncio.run(check())


def test_unsupported_roots_protocol_needs_explicit_workspace_confirmation(project_env, monkeypatch):
    from types import SimpleNamespace

    from mcp import types
    from mcp.shared.exceptions import McpError

    app = project_env[0]
    session = SimpleNamespace(
        check_client_capability=lambda capability: capability.roots is not None,
        list_roots=AsyncMock(
            side_effect=McpError(types.ErrorData(code=-32601, message="synthetic unsupported"))
        ),
        client_params=SimpleNamespace(capabilities=SimpleNamespace(elicitation=None)),
    )
    monkeypatch.setattr(
        type(app.server), "request_context", property(lambda _: SimpleNamespace(session=session))
    )
    roots, native = asyncio.run(McpApplication.project_environment(app))
    assert roots is None and native is None and project_env[1].workspace is None


def test_project_application_requires_explicit_live_readonly(project_env):
    app, runtime, *_ = project_env
    with pytest.raises(DceError):
        McpApplication(app.services, project=runtime)


def test_recursive_proposal_fails_before_any_platform_access(project_env):
    app, runtime, _, _, _, requests = project_env
    proposal = {}
    proposal["recursive"] = proposal
    response = asyncio.run(
        app.call_tool("project_initialize", {"operation": "review", "proposal": proposal})
    )
    assert response.isError and response.structuredContent["data"] is None
    assert not requests and runtime.discovery is None
