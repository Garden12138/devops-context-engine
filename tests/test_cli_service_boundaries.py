import json
from pathlib import Path

import httpx
import pytest
from typer.testing import CliRunner

from dce.app.services import AppServices
from dce.cli import app
from dce.common.config import Settings
from dce.common.errors import DceError
from dce.connectors.http import Reader
from dce.discovery.crawler import ScanScope
from dce.graph.model import DiscoveryResult, Entity


def test_live_discovery_application_scope_and_checkpoint(tmp_path: Path) -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        assert request.method == "GET"
        if path.endswith("/commits/master"):
            return httpx.Response(200, json={"id": "abc"})
        if path.endswith("/tree"):
            return httpx.Response(200, json=[])
        return httpx.Response(
            200, json={"id": 1, "default_branch": "master", "path_with_namespace": "demo/app"}
        )

    settings = Settings.model_validate(
        {
            "catalog_path": tmp_path / "catalog.sqlite3",
            "gitlab": {
                "instance_id": "demo",
                "base_url": "https://demo.example.invalid",
                "token": "synthetic",
            },
        }
    )
    with AppServices(settings, transports={"gitlab": httpx.MockTransport(handle)}) as service:
        report = service.discover(ScanScope(gitlab_projects=["1"]), live=True, read_only=True)
        assert report["scope"] == ScanScope(gitlab_projects=["1"]).model_dump()
        assert report["counts"]["entities"] == 1
        assert report["mapping"]["ai_status"] == "disabled"
        assert len(list((tmp_path / "checkpoints").glob("*.json"))) == 1


def test_ambiguous_ids_and_source_instance_queries(tmp_path: Path) -> None:
    with AppServices(Settings(catalog_path=tmp_path / "catalog.sqlite3")) as service:
        service.catalog.import_scan(
            DiscoveryResult(
                entities=[
                    Entity(source_instance="one", kind="repository", external_id="1"),
                    Entity(source_instance="two", kind="repository", external_id="1"),
                ]
            ),
            scope="demo",
        )
        with pytest.raises(DceError):
            service.catalog.find("repository", "1")
        assert service.project_context("one", "1")["project"]["source_instance"] == "one"


def test_invalid_external_pipeline_structure(tmp_path: Path) -> None:
    settings = Settings.model_validate(
        {
            "catalog_path": tmp_path / "catalog.sqlite3",
            "gitlab": {
                "instance_id": "demo",
                "base_url": "https://demo.example.invalid",
                "token": "synthetic",
            },
        }
    )

    def handle(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/jobs"):
            return httpx.Response(200, json=[{"status": "failed"}])
        return httpx.Response(200, json={})

    with AppServices(settings, transports={"gitlab": httpx.MockTransport(handle)}) as service:
        with pytest.raises(DceError):
            service.pipeline_diagnose("1", "2", live=True, read_only=True)


def test_cli_structured_config_storage_and_review_failures(tmp_path: Path) -> None:
    runner = CliRunner()
    prefix = ["--catalog", str(tmp_path / "catalog.sqlite3")]
    commands = [
        ["--output-budget", "1", "doctor"],
        [*prefix, "init", "--live", "--read-only"],
        [*prefix, "init", "--live", "--read-only", "--scope", "invalid-secret"],
        [*prefix, "mapping", "review", "--action", "accept"],
        [*prefix, "mapping", "review", "unknown-edge", "--action", "accept"],
    ]
    for args in commands:
        result = runner.invoke(app, args)
        assert result.exit_code == 2
        assert json.loads(result.stdout)["status"] == "error"
        assert "invalid-secret" not in result.stdout
    broken = tmp_path / "broken.sqlite3"
    broken.write_text("not a database; synthetic-private")
    result = runner.invoke(app, ["--catalog", str(broken), "catalog", "list"])
    assert result.exit_code == 2 and "synthetic-private" not in result.stdout
    assert json.loads(result.stdout)["error"]["code"] == "INVALID_PAYLOAD"


def test_all_cli_command_help_is_runnable() -> None:
    runner = CliRunner()
    for group, command in (
        ("catalog", "list"),
        ("catalog", "anomalies"),
        ("trace", "service"),
        ("mapping", "review"),
        ("mapping", "suggest"),
        ("mapping", "verify"),
        ("bug", "context"),
        ("pipeline", "diagnose"),
        ("stack", "inspect"),
    ):
        assert runner.invoke(app, [group, command, "--help"]).exit_code == 0


def test_cli_live_explicit_scope_uses_only_mock_transport(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DCE_GITLAB_URL", "https://demo.example.invalid")
    monkeypatch.setenv("DCE_GITLAB_TOKEN", "synthetic-only")

    def handle(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET" and "/projects/1" in request.url.path
        if request.url.path.endswith("/commits/master"):
            return httpx.Response(200, json={"id": "abc"})
        if request.url.path.endswith("/tree"):
            return httpx.Response(200, json=[])
        return httpx.Response(200, json={"id": 1, "default_branch": "master"})

    def mock_reader(self: AppServices, kind: str) -> Reader:
        return Reader(
            self.settings.platform(kind), self.settings, transport=httpx.MockTransport(handle)
        )

    monkeypatch.setattr(AppServices, "reader", mock_reader)
    runner = CliRunner()
    prefix = ["--catalog", str(tmp_path / "catalog.sqlite3")]
    for args in (
        ["init", "--live", "--read-only", "--scope", '{"gitlab_projects":["1"]}'],
        ["discover", "--live", "--read-only", "--gitlab-project", "1"],
    ):
        result = runner.invoke(app, [*prefix, *args])
        assert result.exit_code == 0, result.output
        assert json.loads(result.stdout)["data"]["verification"] == "live_read_only"
        assert json.loads(result.stdout)["data"]["mapping"]["ai_status"] == "disabled"
