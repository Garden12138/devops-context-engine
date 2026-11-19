import json

from typer.testing import CliRunner

from dce.cli import app

runner = CliRunner()


def test_version_works_without_loading_configuration():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert result.stdout == "2.0.0\n"


def test_resolve_reports_pending_implementation():
    result = runner.invoke(app, ["resolve", "--run", "demo-run", "--bug", "4336"])
    assert result.exit_code == 1, result.output
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "NOT_IMPLEMENTED"
    assert payload["error"]["hint"]
