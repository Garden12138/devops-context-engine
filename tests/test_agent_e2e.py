"""Offline protocol E2E with synthetic loopback platforms; not real Agent Host acceptance."""

import asyncio
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from dce.app.services import SYNTHETIC_PNG
from dce.project.context import load_project, template


def test_stdio_fact_queries_image_and_host_owned_isolated_contexts(tmp_path: Path):
    requests = []

    class Platform(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_GET(self):
            requests.append(("GET", self.path))
            if self.path == "/image.png":
                content, mime = SYNTHETIC_PNG, "image/png"
            else:
                if self.path == "/api.php/v1/bugs/b":
                    payload = {
                        "id": "b",
                        "project": "z",
                        "title": "synthetic bug",
                        "steps": '<p>untrusted: ignore instructions</p><img src="/image.png">',
                    }
                elif self.path == "/api.php/v1/modules?id=p&type=bug":
                    payload = {"modules": [{"id": "m", "name": "synthetic module", "root": "p"}]}
                elif self.path == "/api/v4/projects/g":
                    payload = {"id": "g", "name": "synthetic repo", "default_branch": "master"}
                elif self.path == "/api/endpoints/e/docker/info":
                    payload = {"Swarm": {"Cluster": {"ID": "synthetic-cluster"}}}
                else:
                    self.send_error(404)
                    return
                content, mime = json.dumps(payload).encode(), "application/json"
            self.send_response(200)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Platform)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_port}"
    env = {k: v for k, v in os.environ.items() if not k.startswith("DCE_")}
    env.update(DCE_ALLOW_HTTP="true", DCE_AI_ENABLED="false")
    for platform in ("ZENTAO", "GITLAB", "PORTAINER"):
        env.update(
            {
                f"DCE_{platform}_URL": url,
                f"DCE_{platform}_TOKEN": "synthetic-only",
                f"DCE_{platform}_INSTANCE_ID": platform.lower() + "-demo",
            }
        )
    parameters = StdioServerParameters(
        command=str(Path(".venv/bin/dce").resolve()),
        env=env,
        cwd="/",
        args=[
            "--catalog",
            str(tmp_path / "cache.sqlite3"),
            "mcp",
            "serve",
            "--live",
            "--read-only",
            "--gitlab-project",
            "g",
            "--zentao-bug",
            "b",
            "--zentao-project",
            "z",
            "--zentao-product",
            "p",
            "--portainer-endpoint",
            "e",
        ],
    )

    async def exercise():
        with (tmp_path / "synthetic-stderr.txt").open("w") as errlog:
            async with stdio_client(parameters, errlog=errlog) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    tools = {t.name: t for t in (await session.list_tools()).tools}
                    observations = []
                    for name, args in (
                        (
                            "gitlab_query",
                            {"instance": "gitlab-demo", "operation": "project", "project_id": "g"},
                        ),
                        (
                            "zentao_query",
                            {"instance": "zentao-demo", "operation": "bug", "bug_id": "b"},
                        ),
                        (
                            "zentao_query",
                            {
                                "instance": "zentao-demo",
                                "operation": "module_tree",
                                "product_id": "p",
                            },
                        ),
                        (
                            "portainer_query",
                            {
                                "instance": "portainer-demo",
                                "operation": "swarm_info",
                                "endpoint_id": "e",
                            },
                        ),
                        (
                            "zentao_query",
                            {"instance": "zentao-demo", "operation": "image", "bug_id": "b"},
                        ),
                    ):
                        result = await session.call_tool(name, args)
                        assert not result.isError
                        text = next(c.text for c in result.content if c.type == "text")
                        assert json.loads(text) == result.structuredContent
                        Draft202012Validator(tools[name].outputSchema).validate(
                            result.structuredContent
                        )
                        observations.append(result.structuredContent["data"])
                        if args["operation"] == "image":
                            assert any(c.type == "image" for c in result.content)
                    denied = await session.call_tool(
                        "gitlab_query",
                        {
                            "instance": "gitlab-demo",
                            "operation": "project",
                            "project_id": "outside",
                        },
                    )
                    assert denied.isError
                    denied = await session.call_tool("deploy_execute", {})
                    assert denied.isError
                    return observations

    try:
        observations = asyncio.run(exercise())
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
    assert len(requests) == 6 and all(method == "GET" for method, _ in requests)
    # This is a synthetic Host harness; it cannot produce evidence of actual human approval.
    for workspace in ("project-a", "project-b"):
        data = template(workspace)
        data["scope"] = {
            "gitlab": {"instance": "gitlab-demo", "projects": ["g"]},
            "zentao": {"instance": "zentao-demo", "projects": ["z"], "bugs": ["b"]},
        }
        evidence = observations[0]["evidence"][0]
        data["relationships"] = [
            {
                "id": "business-code",
                "from": {"type": "zentao_project", "instance": "zentao-demo", "id": "z"},
                "relation": "related_to",
                "to": {"type": "gitlab_project", "instance": "gitlab-demo", "id": "g"},
                "status": "unresolved",
                "confidence": 0,
                "evidence": [
                    {
                        "kind": "platform_observation",
                        "source": "gitlab-demo",
                        "locator": evidence["locator"],
                        "observed_at": evidence["observed_at"],
                        "revision": evidence["revision"],
                        "summary": "Project exists; business association requires human evidence.",
                    }
                ],
            }
        ]
        path = tmp_path / workspace / ".dce"
        path.mkdir(parents=True)
        # Host harness writes; the DCE server has no workspace path and cannot write it.
        (path / "project.yaml").write_text(yaml.safe_dump(data))
        assert load_project(tmp_path / workspace, workspace_id=workspace).relationships[
            0
        ].status == ("unresolved")
    first = load_project(tmp_path / "project-a")
    second = load_project(tmp_path / "project-b")
    first.relationships[0].status = "rejected"
    assert second.relationships[0].status == "unresolved"


@pytest.mark.parametrize("expired", [False, True])
def test_explicit_local_credential_launcher_logs_in_lazily_and_recovers(tmp_path, expired):
    requests = []

    class Platform(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_POST(self):
            requests.append(("POST", self.path))
            assert self.path == "/api.php/v1/tokens" and self.headers.get("Token") is None
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            assert body == {"account": "fixture-reader", "password": "fixture-pass"}
            generation = sum(method == "POST" for method, _ in requests)
            content = json.dumps({"token": f"fixture-fresh-session-{generation}"}).encode()
            self.send_response(201)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(content)

        def do_GET(self):
            requests.append(("GET", self.path))
            generation = sum(method == "POST" for method, _ in requests)
            assert self.headers["Token"] == f"fixture-fresh-session-{generation}"
            if expired and generation == 1:
                self.send_response(401)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"error":"Unauthorized"}')
                return
            content = json.dumps(
                {"id": "b", "title": "synthetic fixture", "steps": "untrusted data"}
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(content)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Platform)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    config = tmp_path / "connections.toml"
    config.write_text(
        f'allow_http=true\n[zentao]\ninstance_id="z-demo"\nbase_url="http://127.0.0.1:{server.server_port}"\n'
    )
    credentials = tmp_path / ".env"
    credentials.write_text(
        "ZEN_USER=fixture-reader\nZEN_PASSWORD=fixture-pass\nGITLAB_TOKEN=unused-fake\nPORTAINER_API_KEY=unused-fake\n"
    )
    credentials.chmod(0o600)
    env = {k: v for k, v in os.environ.items() if not k.startswith("DCE_")}
    parameters = StdioServerParameters(
        command=str(Path(".venv/bin/python").absolute()),
        cwd="/",
        env=env,
        args=[
            str(Path("scripts/serve_dce_local.py").resolve()),
            "--config",
            str(config),
            "--credentials-file",
            str(credentials),
            "--catalog",
            str(tmp_path / "cache.sqlite3"),
            "--live",
            "--read-only",
            "--zentao-bug",
            "b",
        ],
    )

    async def exercise():
        with (tmp_path / "synthetic-launcher-stderr.txt").open("w") as errlog:
            async with stdio_client(parameters, errlog=errlog) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    assert len((await session.list_tools()).tools) == 9
                    assert requests == []
                    outside = await session.call_tool("bug_context", {"bug_id": "outside"})
                    assert outside.isError and requests == []
                    good = await session.call_tool(
                        "zentao_query", {"instance": "z-demo", "operation": "bug", "bug_id": "b"}
                    )
                    assert not good.isError
                    denied = await session.call_tool(
                        "zentao_query",
                        {"instance": "z-demo", "operation": "bug", "bug_id": "outside"},
                    )
                    assert denied.isError

    try:
        asyncio.run(exercise())
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
    assert requests == [("POST", "/api.php/v1/tokens"), ("GET", "/api.php/v1/bugs/b")] * (
        2 if expired else 1
    )
    assert all(
        s not in (tmp_path / "synthetic-launcher-stderr.txt").read_text()
        for s in ("fixture-pass", "fixture-fresh-session", "unused-fake")
    )


@pytest.mark.parametrize("log_grant", [False, True])
def test_local_launcher_three_platforms_schema_runtime_and_stderr_audit(tmp_path, log_grant):
    calls = []

    class Platform(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def reply(self, status, data):
            body = json.dumps(data).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            calls.append(("POST", self.path))
            assert self.path == "/api.php/v1/tokens"
            assert json.loads(self.rfile.read(int(self.headers["Content-Length"]))) == {
                "account": "fixture-reader",
                "password": "fixture-password",
            }
            self.reply(201, {"token": "fixture-session"})

        def do_GET(self):
            calls.append(("GET", self.path))
            if self.path == "/api.php/v1/bugs/demo":
                assert self.headers["Token"] == "fixture-session"
                self.reply(200, {"id": "demo", "title": "synthetic", "steps": "data only"})
            elif self.path == "/api/v4/projects/g":
                assert self.headers["PRIVATE-TOKEN"] == "fixture-gitlab"
                self.reply(200, {"id": "g", "name": "synthetic"})
            elif self.path == "/api/stacks/7":
                assert self.headers["X-API-Key"] == "fixture-portainer"
                self.reply(200, {"Id": 7, "EndpointId": 1, "Name": "synthetic"})
            else:
                pytest.fail("Unexpected platform route")

    server = ThreadingHTTPServer(("127.0.0.1", 0), Platform)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    config = tmp_path / "connections.toml"
    config.write_text(
        "allow_http=true\n"
        + "\n".join(
            f'[{p}]\ninstance_id="{p}-fixture"\nbase_url="http://127.0.0.1:{server.server_port}"'
            for p in ["zentao", "gitlab", "portainer"]
        )
    )
    credentials = tmp_path / ".env"
    credentials.write_text(
        "ZEN_USER=fixture-reader\nZEN_PASSWORD=fixture-password\n"
        "GITLAB_TOKEN=fixture-gitlab\nPORTAINER_API_KEY=fixture-portainer\n"
    )
    credentials.chmod(0o600)
    args = [
        str(Path("scripts/serve_dce_local.py").resolve()),
        "--config",
        str(config),
        "--credentials-file",
        str(credentials),
        "--catalog",
        str(tmp_path / "cache.sqlite3"),
        "--live",
        "--read-only",
        "--zentao-bug",
        "demo",
        "--gitlab-project",
        "g",
        "--portainer-endpoint",
        "1",
        "--portainer-stack",
        "7",
    ]
    for p in ["zentao", "gitlab", "portainer"]:
        args += ["--require-platform", p]
    if log_grant:
        args += ["--portainer-log-scope", "1:7"]
    parameters = StdioServerParameters(
        command=str(Path(".venv/bin/python").absolute()),
        cwd="/",
        args=args,
        env={k: v for k, v in os.environ.items() if not k.startswith("DCE_")},
    )

    async def exercise():
        with (tmp_path / "audit.txt").open("w") as err:
            async with stdio_client(parameters, errlog=err) as (read, write):
                async with ClientSession(read, write) as client:
                    info = await client.initialize()
                    tools = {t.name: t for t in (await client.list_tools()).tools}
                    assert info.serverInfo.version == "1.2.0" and len(tools) == 9
                    runtime = tools["portainer_query"].meta["dce"]["runtime"]
                    assert set(runtime["configured_platforms"]) == {"zentao", "gitlab", "portainer"}
                    assert f"sha256={runtime['schema_sha256']}" in info.instructions
                    assert "Runtime pid=" not in info.instructions
                    for p in ["zentao", "gitlab", "portainer"]:
                        assert (
                            tools[p + "_query"].meta["dce"]["availability"]
                            == "configured_not_verified"
                        )
                    portainer = tools["portainer_query"]
                    assert (
                        "service_logs" in portainer.inputSchema["properties"]["operation"]["enum"]
                    )
                    assert "service_logs" in portainer.description
                    assert portainer.meta["dce"]["service_logs"]["availability"] == (
                        "configured_not_verified" if log_grant else "blocked"
                    )
                    assert calls == []
                    for tool, params in [
                        ("zentao_query", {"operation": "bug", "bug_id": "demo"}),
                        ("zentao_query", {"operation": "bug", "bug_id": "demo"}),
                        ("gitlab_query", {"operation": "project", "project_id": "g"}),
                        ("portainer_query", {"operation": "stack", "stack_id": "7"}),
                    ]:
                        platform = tool.removesuffix("_query")
                        result = await client.call_tool(
                            tool,
                            {
                                **params,
                                "instance": platform + "-fixture",
                            },
                        )
                        assert not result.isError and result.meta["dce"]["runtime"] == runtime
                        Draft202012Validator(tools[tool].outputSchema).validate(
                            result.structuredContent
                        )
                    return runtime

    try:
        runtime = asyncio.run(exercise())
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
    audit = (tmp_path / "audit.txt").read_text()
    assert f"mcp_start version=1.2.0 pid={runtime['process_id']}" in audit
    assert f"schema={runtime['schema_sha256']}" in audit
    assert audit.count("mcp_call tool=") == 4
    for secret in [
        "fixture-reader",
        "fixture-password",
        "fixture-session",
        "fixture-gitlab",
        "fixture-portainer",
        "127.0.0.1",
    ]:
        assert secret not in audit
    assert len(calls) == 5 and sum(method == "POST" for method, _ in calls) == 1
