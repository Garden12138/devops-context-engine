"""Real STDIO with synthetic loopback services; never contacts Portainer."""

import asyncio
import json
import os
import threading
from datetime import UTC, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


@pytest.mark.parametrize("launcher", ["local", "cli"])
def test_both_mcp_entrypoints_enforce_exact_policy_and_one_attempt(tmp_path, launcher):
    calls = []
    service = {
        "ID": "svc1",
        "Version": {"Index": 1},
        "Spec": {
            "Name": "demo_template",
            "Labels": {"com.docker.stack.namespace": "demo"},
            "TaskTemplate": {"ContainerSpec": {"TTY": False}, "LogDriver": {"Name": "json-file"}},
        },
    }

    class Platform(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_GET(self):
            from urllib.parse import parse_qs, urlsplit

            parts = urlsplit(self.path)
            calls.append(parts.path)
            if parts.path.endswith("/logs"):
                params = parse_qs(parts.query)
                assert params["tail"] == ["20"] and params["follow"] == ["false"]
                stamp = (
                    (datetime.now(UTC) - timedelta(seconds=10)).isoformat().replace("+00:00", "Z")
                )
                data = (
                    f"{stamp} com.docker.swarm.service.id=svc1,"
                    "com.docker.swarm.task.id=t1 INFO callback failed\n"
                ).encode()
                body = bytes([1, 0, 0, 0]) + len(data).to_bytes(4, "big") + data
            else:
                if parts.path.endswith("/stacks/7"):
                    data = {
                        "Id": 7,
                        "EndpointId": 1,
                        "Type": 1,
                        "Name": "demo",
                        "SwarmId": "swarm1",
                    }
                elif parts.path.endswith("/info"):
                    data = {"Swarm": {"Cluster": {"ID": "swarm1"}}}
                elif parts.path.endswith("/version"):
                    data = {"ApiVersion": "1.47"}
                elif parts.path.endswith("/services/svc1"):
                    data = service
                elif parts.path.endswith("/services"):
                    data = [service]
                else:
                    raise AssertionError("Unexpected synthetic route")
                body = json.dumps(data).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Platform)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    tmp_path.chmod(0o700)
    now = datetime.now(UTC)
    policy = tmp_path / "grant.json"
    policy.write_text(
        json.dumps(
            {
                "version": 1,
                "grant_id": "c" * 32,
                "source_instance": "unit",
                "endpoint_id": "1",
                "stack_id": "7",
                "stack_name": "demo",
                "namespace": "demo",
                "swarm_id": "swarm1",
                "service_id": "svc1",
                "compose_service": "template",
                "service_name": "demo_template",
                "issued_at": (now - timedelta(seconds=10)).isoformat(),
                "expires_at": (now + timedelta(minutes=10)).isoformat(),
            }
        )
    )
    policy.chmod(0o600)
    config = tmp_path / "connections.toml"
    config.write_text(
        f'allow_http=true\n[portainer]\ninstance_id="unit"\nbase_url="http://127.0.0.1:{server.server_port}"\n'
    )
    credentials = tmp_path / ".env"
    credentials.write_text("PORTAINER_API_KEY=fixture-key\n")
    credentials.chmod(0o600)
    scope = [
        "--live",
        "--read-only",
        "--portainer-endpoint",
        "1",
        "--portainer-stack",
        "7",
        "--portainer-log-scope",
        "1:7",
        "--portainer-log-policy",
        str(policy),
    ]
    env = {k: v for k, v in os.environ.items() if not k.startswith("DCE_")}
    if launcher == "local":
        command = str(Path(".venv/bin/python").absolute())
        args = [
            str(Path("scripts/serve_dce_local.py").resolve()),
            "--config",
            str(config),
            "--credentials-file",
            str(credentials),
            "--catalog",
            str(tmp_path / "cache.sqlite3"),
            *scope,
        ]
    else:
        command = str(Path(".venv/bin/dce").absolute())
        args = [
            "--config",
            str(config),
            "--catalog",
            str(tmp_path / "cache.sqlite3"),
            "mcp",
            "serve",
            *scope,
        ]
        env["DCE_PORTAINER_TOKEN"] = "fixture-key"
    params = StdioServerParameters(command=command, args=args, env=env, cwd="/")

    async def exercise():
        with (tmp_path / "stderr.txt").open("w") as err:
            async with stdio_client(params, errlog=err) as (read, write):
                async with ClientSession(read, write) as client:
                    await client.initialize()
                    tools = (await client.list_tools()).tools
                    assert len(tools) == 9
                    portainer = next(t for t in tools if t.name == "portainer_query")
                    state = portainer.meta["dce"]["service_logs"]
                    assert state["exact_service_policy"] and state["limits"]["max_lines"] == 20
                    assert state["availability"] == "configured_not_verified" and not calls
                    end = datetime.now(UTC)
                    args = {
                        "instance": "unit",
                        "operation": "service_logs",
                        "endpoint_id": "1",
                        "stack_id": "7",
                        "service_name": "ad",
                        "start_time": (end - timedelta(minutes=5)).isoformat(),
                        "end_time": end.isoformat(),
                        "max_lines": 20,
                    }
                    denied = await client.call_tool("portainer_query", args)
                    assert denied.isError and not calls
                    args["service_name"] = "template"
                    result = await client.call_tool("portainer_query", args)
                    assert not result.isError
                    again = await client.call_tool("portainer_query", args)
                    assert again.isError

    try:
        asyncio.run(exercise())
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
    assert sum(path.endswith("/logs") for path in calls) == 1
    assert len(list(tmp_path.glob(".log-grant-*.used"))) == 1
