import json
from pathlib import Path

from typer.testing import CliRunner

from dce.cli import app

FIXTURE = str(Path("fixtures/synthetic-discovery.json").resolve())
runner = CliRunner()


def run(args: list[str]) -> dict[str, object]:
    result = runner.invoke(app, args)
    assert result.exit_code == 0, result.output + str(result.exception)
    return json.loads(result.stdout)


def test_cli_end_to_end(tmp_path: Path) -> None:
    prefix = ["--catalog", str(tmp_path / "catalog.sqlite3")]
    result = run([*prefix, "init", "--fixture", FIXTURE, "--no-ai"])
    assert result["data"]["counts"]["entities"] > 150
    anomalies = run([*prefix, "catalog", "anomalies", "--format", "json"])
    assert any(a["status"] == "config_drift_candidate" for a in anomalies["data"]["items"])
    page = run([*prefix, "catalog", "list", "--kind", "service", "--limit", "2"])
    assert len(page["data"]["items"]) == 2 and page["data"]["more_available"]
    service_key = page["data"]["items"][0]["id"]
    trace = run([*prefix, "trace", "service", service_key])
    assert trace["data"]["edges"]
    run([*prefix, "mapping", "suggest", "--offline"])
    candidates = run([*prefix, "mapping", "review"])
    candidate = candidates["data"]["items"][0]
    preview = run([*prefix, "mapping", "review", candidate["id"]])
    run(
        [
            *prefix,
            "mapping",
            "review",
            candidate["id"],
            "--action",
            "accept",
            "--actor",
            "demo-owner",
            "--reason",
            "synthetic owner verification",
            "--expected-version",
            str(preview["data"]["edge"]["version"]),
        ]
    )
    bug = run([*prefix, "bug", "context", "DEMO-1001", "--fixture", FIXTURE])
    assert len(bug["data"]["assets"]) == 2
    assert all(Path(asset["local_path"]).is_file() for asset in bug["data"]["assets"])
    assert any(item["status"] == "confirmed" for item in bug["data"]["modules"])
    pipeline = run([*prefix, "pipeline", "diagnose", "1001", "2001", "--fixture", FIXTURE])
    assert pipeline["data"]["failures"][0]["root_cause"] == "missing_make"
    stack = run([*prefix, "stack", "inspect", "101"])
    assert stack["data"]["stack"]["attributes"]["state"] == "stale_candidate"
    run([*prefix, "mapping", "verify"])


def test_cli_failure_modes_and_table(tmp_path: Path) -> None:
    prefix = ["--catalog", str(tmp_path / "catalog.sqlite3")]
    for args in (
        ["init", "--live"],
        ["discover", "--live", "--read-only"],
        ["bug", "context", "https://evil.example.invalid"],
        ["catalog", "list", "--limit", "101"],
        ["catalog", "list", "--format", "xml"],
    ):
        result = runner.invoke(app, [*prefix, *args])
        assert result.exit_code == 2, result.output
        assert json.loads(result.stdout)["status"] == "error"
    table = runner.invoke(app, [*prefix, "catalog", "list", "--format", "table"])
    assert table.exit_code == 0
    assert "schema_version" in table.stdout
