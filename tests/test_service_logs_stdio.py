"""Real MCP stdio + loopback HTTP, exclusively synthetic data; no business workspace."""

import asyncio
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from jsonschema import Draft202012Validator
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def test_scoped_logs_through_stdio_and_http(tmp_path: Path):
    requests = []
    service = {
        "ID": "svc1",
        "Version": {"Index": 1},
        "Spec": {
            "Name": "demo_template",
            "Labels": {"com.docker.stack.namespace": "demo"},
            "TaskTemplate": {"ContainerSpec": {}},
        },
    }
    message = (
        b"2026-11-01T02:00:01.000000001Z com.docker.swarm.service.id=svc1,"
        b"com.docker.swarm.task.id=task1 ERROR callback failed password=never-output\n"
    )
    logs = b"\1\0\0\0" + len(message).to_bytes(4, "big") + message

    class Platform(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_GET(self):
            requests.append(self.path)
            route = urlsplit(self.path).path
            if route.endswith("/logs"):
                params = parse_qs(urlsplit(self.path).query)
                assert params["follow"] == ["false"] and params["tail"] == ["10"]
                body = logs
                kind = "application/vnd.docker.raw-stream"
            else:
                data = {
                    "/api/stacks/7": {
                        "Id": 7,
                        "EndpointId": 1,
                        "Type": 1,
                        "Name": "demo",
                        "SwarmId": "swarm1",
                    },
                    "/api/endpoints/1/docker/info": {"Swarm": {"Cluster": {"ID": "swarm1"}}},
                    "/api/endpoints/1/docker/services": [service],
                    "/api/endpoints/1/docker/services/svc1": service,
                    "/api/endpoints/1/docker/version": {"ApiVersion": "1.48"},
                }.get(route)
                if data is None:
                    self.send_error(404)
                    return
                body = json.dumps(data).encode()
                kind = "application/json"
            self.send_response(200)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            # Exercise real HTTP chunk boundaries inside the Docker header and timestamp.
            for offset in range(0, len(body), 3):
                self.wfile.write(body[offset : offset + 3])
                self.wfile.flush()

    server = ThreadingHTTPServer(("127.0.0.1", 0), Platform)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    env = {k: v for k, v in os.environ.items() if not k.startswith("DCE_")}
    env.update(
        DCE_ALLOW_HTTP="true",
        DCE_PORTAINER_URL=f"http://127.0.0.1:{server.server_port}",
        DCE_PORTAINER_TOKEN="fake-only",
        DCE_PORTAINER_INSTANCE_ID="unit",
    )
    parameters = StdioServerParameters(
        command=str(Path(".venv/bin/dce").absolute()),
        env=env,
        args=[
            "--catalog",
            str(tmp_path / "c.sqlite3"),
            "mcp",
            "serve",
            "--live",
            "--read-only",
            "--portainer-endpoint",
            "1",
            "--portainer-stack",
            "7",
            "--portainer-log-scope",
            "1:7",
        ],
    )

    async def exercise():
        with (tmp_path / "synthetic-stderr.txt").open("w") as errlog:
            async with stdio_client(parameters, errlog=errlog) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    tools = {t.name: t for t in (await session.list_tools()).tools}
                    assert len(tools) == 9
                    args = {
                        "instance": "unit",
                        "operation": "service_logs",
                        "endpoint_id": "1",
                        "stack_id": "7",
                        "service_name": "template",
                        "max_lines": 10,
                        "start_time": "2026-11-01T10:00:00+08:00",
                        "end_time": "2026-11-01T10:01:00+08:00",
                    }
                    response = await session.call_tool("portainer_query", args)
                    assert not response.isError
                    data = response.structuredContent
                    Draft202012Validator(tools["portainer_query"].outputSchema).validate(data)
                    assert json.loads(response.content[0].text) == data
                    item = data["data"]["records"][0]
                    assert item["events"][0]["signals"] == ["callback", "failed"]
                    assert item["identity"]["stack_id"] == "7" and not item["truncated"]
                    assert "never-output" not in response.model_dump_json()
                    assert (
                        len(response.model_dump_json(by_alias=True, exclude_none=True).encode())
                        <= 8192
                    )
                    denied = await session.call_tool("portainer_query", {**args, "stack_id": "8"})
                    assert denied.isError
                    Draft202012Validator(tools["portainer_query"].outputSchema).validate(
                        denied.structuredContent
                    )
                    assert (
                        denied.structuredContent["data"]["records"][0]["error_type"]
                        == "PERMISSION_DENIED"
                    )

    try:
        asyncio.run(exercise())
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
    assert sum("/logs?" in request for request in requests) == 1
    assert len(requests) == 7
