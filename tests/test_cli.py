import json

import pytest
from typer.testing import CliRunner

from dce.cli import app

runner = CliRunner()


def test_version_works_without_loading_configuration():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert result.stdout == "2.0.0\n"


@pytest.mark.parametrize(
    "args",
    [
        ["merge", "--run", "demo-run", "--yes"],
        ["build", "--run", "demo-run", "--retry-failed"],
        ["build-status", "--run", "demo-run", "--wait", "300"],
        ["deploy", "--run", "demo-run"],
        ["deploy-status", "--run", "demo-run", "--logs", "100"],
        ["run", "update", "--run", "demo-run"],
        ["resolve", "--run", "demo-run", "--bug", "4336"],
    ],
)
def test_documented_commands_report_pending_implementation(args):
    result = runner.invoke(app, args)
    assert result.exit_code == 1, result.output
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["error"]["code"] == "NOT_IMPLEMENTED"
    assert payload["error"]["hint"]
