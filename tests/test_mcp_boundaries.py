import asyncio
import json
from pathlib import Path

from pydantic import AnyUrl
from typer.testing import CliRunner

from dce.app.services import AppServices
from dce.cli import app
from dce.common.config import Settings
from dce.mcp.server import McpApplication


def test_mcp_resource_integrity_and_direct_contracts(tmp_path: Path) -> None:
    with AppServices(Settings(catalog_path=tmp_path / "catalog.sqlite3")) as services:
        services.initialize()
        server = McpApplication(services)

        async def exercise() -> None:
            assert len(await server.list_tools()) == 9
            service_id = services.catalog.list_entities(kind="service")["items"][0]["id"]
            for name, arguments in (
                ("project_context", {"source": "gitlab-demo", "project_key": "1001"}),
                ("service_trace", {"service_key": service_id}),
                ("pipeline_diagnose", {"project_key": "1001", "pipeline_id": "2001"}),
                ("deployment_inspect", {"service_key": service_id}),
                ("deployment_inspect", {"stack_key": "103"}),
                ("discovery_status", {}),
            ):
                response = await server.call_tool(name, arguments)
                assert not response.isError
            invalid = await server.call_tool("deploy", {})
            assert invalid.structuredContent["error"]["code"] == "NOT_FOUND"
            invalid = await server.call_tool("deployment_inspect", {})
            assert invalid.structuredContent["error"]["code"] == "INVALID_PAYLOAD"
            bug = await server.call_tool(
                "bug_context", {"bug_id": "DEMO-1001", "include_assets": True}
            )
            asset = bug.structuredContent["data"]["assets"][0]
            uri = AnyUrl(asset["resource_uri"])
            assert len(await server.list_resources()) == 2
            assert (await server.read_resource(uri))[0].mime_type == "image/png"
            stored = server.assets[asset["asset_id"]]
            path = Path(stored["local_path"])
            path.write_bytes(b"tampered")
            refused = await server.read_resource(uri)
            assert "INVALID_PAYLOAD" in refused[0].content
            path.unlink()
            path.symlink_to(tmp_path / "untrusted-file")
            refused = await server.read_resource(uri)
            assert "INVALID_PAYLOAD" in refused[0].content
            assert (
                "PERMISSION_DENIED"
                in (await server.read_resource(AnyUrl("file:///etc/passwd")))[0].content
            )

        asyncio.run(exercise())


def test_mcp_initialization_errors_stay_off_stdout(tmp_path: Path) -> None:
    runner = CliRunner()
    for options in (["--transport", "http"], ["--live"]):
        result = runner.invoke(
            app, ["--catalog", str(tmp_path / "catalog.sqlite3"), "mcp", "serve", *options]
        )
        assert result.exit_code == 2
        assert result.stdout == ""
        assert json.loads(result.stderr)["status"] == "error"
