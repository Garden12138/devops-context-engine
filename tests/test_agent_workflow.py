import asyncio
import json
from pathlib import Path

from jsonschema import Draft202012Validator
from typer.testing import CliRunner

from dce.app.services import AppServices
from dce.cli import app
from dce.common.config import Settings
from dce.mcp.server import McpApplication
from dce.project.model import ProjectContext


def test_workflow_documents_match_real_tools_and_cli(tmp_path: Path):
    with AppServices(Settings(catalog_path=tmp_path / "cache.sqlite3")) as service:
        tools = {t.name for t in asyncio.run(McpApplication(service).list_tools())}
    assert {"zentao_query", "gitlab_query", "portainer_query"} <= tools
    for name in (
        "initialize",
        "refresh",
        "review",
        "bug-context",
        "service-trace",
        "pipeline-diagnose",
    ):
        text = (Path("prompts/agent-led") / (name + ".md")).read_text()
        assert "project.yaml" in text and "confirmed" in text and "不可信数据" in text
        assert all(t in text for t in ("zentao_query", "gitlab_query", "portainer_query"))
    assert json.loads(Path("schemas/project.schema.json").read_text()) == (
        ProjectContext.model_json_schema(by_alias=True)
    )
    result = CliRunner().invoke(app, ["mcp", "serve", "--help"])
    assert result.exit_code == 0
    # Typer inserts terminal styling/wrapping; inspect actual registered command parameters.
    from typer.main import get_command

    command = get_command(app).commands["mcp"].commands["serve"]
    names = {p.name for p in command.params}
    assert {
        "gitlab_project",
        "zentao_project",
        "zentao_product",
        "zentao_bug",
        "portainer_endpoint",
        "portainer_stack",
    } <= names


def test_fact_schemas_publish_required_operation_arguments(tmp_path: Path):
    with AppServices(Settings(catalog_path=tmp_path / "cache.sqlite3")) as service:
        tools = {t.name: t for t in asyncio.run(McpApplication(service).list_tools())}
    for name, bad, good in (
        (
            "gitlab_query",
            {"operation": "file", "project_id": "g"},
            {"operation": "file", "project_id": "g", "ref": "sha", "path": "README.md"},
        ),
        ("zentao_query", {"operation": "modules"}, {"operation": "modules", "product_id": "p"}),
        (
            "portainer_query",
            {"operation": "stack_file", "stack_id": "s"},
            {"operation": "stack_file", "stack_id": "s", "endpoint_id": "e"},
        ),
    ):
        validator = Draft202012Validator(tools[name].inputSchema)
        assert not validator.is_valid({"instance": "demo", **bad})
        validator.validate({"instance": "demo", **good})
