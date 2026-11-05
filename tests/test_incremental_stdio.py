"""New operations through actual stdio/HTTP, with strictly synthetic platform data."""

import asyncio
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def test_incremental_operations_and_nine_tools_stdio(tmp_path: Path):
    requests = []
    compose = yaml.safe_dump(
        {
            "services": {
                **{f"extra-{i}": {"image": "synthetic:v1"} for i in range(300)},
                "target": {"image": "synthetic:v2", "environment": {"PASSWORD": "never-output"}},
            }
        }
    )

    class Platform(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_GET(self):
            requests.append(self.path)
            route = self.path.partition("?")[0]
            if route == "/api/stacks/t":
                data = {"Id": "t", "EndpointId": "e"}
            elif route == "/api/stacks/t/file":
                data = {"StackFileContent": compose}
            elif route == "/api/v4/projects/g/jobs":
                data = [{"id": 1, "ref": "topic", "status": "manual", "name": "build"}]
            elif route == "/api/v4/projects/g/pipelines/q/jobs":
                data = []
            elif route == "/api/v4/projects/g/pipelines/q/bridges":
                data = [{"id": 2, "downstream_pipeline": {"project_id": "g", "id": 3}}]
            else:
                self.send_error(404)
                return
            body = json.dumps(data).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("X-Next-Page", "")
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Platform)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    address = f"http://127.0.0.1:{server.server_port}"
    env = {k: v for k, v in os.environ.items() if not k.startswith("DCE_")}
    env.update(DCE_ALLOW_HTTP="true", DCE_OUTPUT_BUDGET="8192", DCE_AI_ENABLED="false")
    for platform in ("GITLAB", "PORTAINER"):
        env.update(
            {
                f"DCE_{platform}_URL": address,
                f"DCE_{platform}_TOKEN": "fake-only",
                f"DCE_{platform}_INSTANCE_ID": "unit",
            }
        )
    parameters = StdioServerParameters(
        command=str(Path(".venv/bin/dce").absolute()),
        env=env,
        args=[
            "--catalog",
            str(tmp_path / "cache.sqlite3"),
            "mcp",
            "serve",
            "--live",
            "--read-only",
            "--gitlab-project",
            "g",
            "--portainer-endpoint",
            "e",
            "--portainer-stack",
            "t",
        ],
    )

    async def exercise():
        with (tmp_path / "synthetic-stderr.txt").open("w") as errlog:
            async with stdio_client(parameters, errlog=errlog) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    tools = {t.name: t for t in (await session.list_tools()).tools}
                    assert len(tools) == 9
                    assert tools["gitlab_query"].meta["dce"]["contract_revision"] == "2.1"
                    for tool, args in (
                        ("gitlab_query", {"operation": "project_jobs", "project_id": "g"}),
                        (
                            "gitlab_query",
                            {"operation": "branch_jobs", "project_id": "g", "ref": "topic"},
                        ),
                        (
                            "gitlab_query",
                            {"operation": "jobs", "project_id": "g", "pipeline_id": "q"},
                        ),
                        (
                            "gitlab_query",
                            {
                                "operation": "pipeline_bridges",
                                "project_id": "g",
                                "pipeline_id": "q",
                            },
                        ),
                        (
                            "portainer_query",
                            {"operation": "stack_file", "stack_id": "t", "endpoint_id": "e"},
                        ),
                        (
                            "portainer_query",
                            {
                                "operation": "stack_service",
                                "stack_id": "t",
                                "endpoint_id": "e",
                                "service_name": "target",
                            },
                        ),
                    ):
                        result = await session.call_tool(tool, {"instance": "unit", **args})
                        assert not result.isError
                        payload = result.structuredContent
                        Draft202012Validator(tools[tool].outputSchema).validate(payload)
                        assert json.loads(result.content[0].text) == payload
                        assert (
                            len(result.model_dump_json(by_alias=True, exclude_none=True).encode())
                            <= 8192
                        )
                        assert "never-output" not in result.model_dump_json()
                        if args["operation"] == "stack_file":
                            assert payload["truncated"] and payload["data"] is None
                        if args["operation"] == "stack_service":
                            assert not payload["truncated"]
                            assert payload["data"]["records"][0]["name"] == "target"

    try:
        asyncio.run(exercise())
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
    assert len(requests) == 8  # Two Stack metadata/file pairs, four independent GitLab pages.
