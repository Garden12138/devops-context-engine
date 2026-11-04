import json
import subprocess
from pathlib import Path

import httpx
import pytest

from dce.app.mapping import MappingService
from dce.app.services import AppServices, external_id
from dce.common.config import Settings
from dce.common.errors import DceError
from dce.discovery.crawler import ScanScope

FIXTURE = Path("fixtures/synthetic-discovery.json").resolve()


def test_offline_services_and_readonly_queries(tmp_path: Path) -> None:
    settings = Settings(catalog_path=tmp_path / "catalog.sqlite3")
    with AppServices(settings, fixture=FIXTURE) as service:
        service.initialize(legacy_mapping=True)
        counts = service.catalog.counts()
        assert service.project_context("gitlab-demo", "1001")["trace"]["edges"]
        assert (
            service.project_context("zentao-demo", "2801")["project"]["kind"] == "business_project"
        )
        status = service.discovery_status()
        scan_id = status["items"][-1]["id"]
        assert service.discovery_status(scan_id)["items"][0]["id"] == scan_id
        bug = service.bug_context("DEMO-1001", include_assets=False)
        assert bug["assets"] == [] and len(bug["modules"]) == 3
        assert "BUSINESS_MAPPING_UNCONFIRMED" in bug["warnings"]
        mappings = service.catalog.list_edges(status="unresolved", limit=100)["items"]
        for edge in mappings:
            MappingService(service.catalog).review(
                edge["id"],
                action="reject",
                actor="owner",
                reason="synthetic wrong mapping",
                expected_version=edge["version"],
            )
        assert service.bug_context("DEMO-1001", include_assets=False)["modules"] == []
        assert service.catalog.counts() == counts
        assert service.pipeline_diagnose("1001", "2001")["default_branch"] == "master"
        for operation in (
            lambda: service.bug_context("absent"),
            lambda: service.pipeline_diagnose("1001", "absent"),
            lambda: service.project_context("gitlab-demo", "absent"),
            lambda: service.discovery_status("absent"),
        ):
            with pytest.raises(DceError):
                operation()


def test_live_services_via_mock_transport(tmp_path: Path) -> None:
    calls = []

    def handle(request: httpx.Request) -> httpx.Response:
        calls.append((request.method, request.url.path))
        path = request.url.path
        if path.endswith("/bugs/1"):
            return httpx.Response(
                200,
                json={
                    "id": 1,
                    "title": "Token=synthetic-private",
                    "steps": '<p>data</p><img src="/image.png">',
                    "files": [],
                    "project": {"id": 2, "token": "private"},
                },
            )
        if path == "/image.png":
            return httpx.Response(
                200, text="<html>not an image</html>", headers={"Content-Type": "text/html"}
            )
        if path.endswith("/trace"):
            return httpx.Response(200, text="Token=synthetic-private\n/bin/sh: make: not found")
        if path.endswith("/jobs"):
            return httpx.Response(200, json=[{"id": 3, "status": "failed", "stage": "build"}])
        if "/pipelines/" in path:
            return httpx.Response(200, json={"id": 2, "status": "failed"})
        return httpx.Response(200, json={"id": 1, "default_branch": "master"})

    config = {
        "instance_id": "demo",
        "base_url": "https://demo.example.invalid",
        "token": "synthetic-private",
    }
    settings = Settings.model_validate(
        {"catalog_path": tmp_path / "catalog.sqlite3", "zentao": config, "gitlab": config}
    )
    with AppServices(
        settings, transports={name: httpx.MockTransport(handle) for name in ("zentao", "gitlab")}
    ) as service:
        with pytest.raises(DceError):
            service.bug_context("1", live=True)
        bug = service.bug_context("1", live=True, read_only=True)
        assert "ASSET_INVALID_PAYLOAD" in bug["warnings"] and bug["assets"] == []
        assert bug["project_id"] == 2
        assert "synthetic-private" not in json.dumps(bug)
        diagnosis = service.pipeline_diagnose("1", "2", live=True, read_only=True)
        assert diagnosis["failures"][0]["root_cause"] == "missing_make"
        assert "synthetic-private" not in json.dumps(diagnosis)
    assert all(method == "GET" for method, _ in calls)
    assert external_id([]) is None and external_id(True) is None


def test_discover_scope_live_gate_and_offline(tmp_path: Path) -> None:
    with AppServices(
        Settings(catalog_path=tmp_path / "catalog.sqlite3"), fixture=FIXTURE
    ) as service:
        scope = ScanScope(gitlab_projects=["1"])
        with pytest.raises(DceError):
            service.discover(scope, live=True, read_only=False)
        with pytest.raises(DceError):
            service.discover(scope, live=True, read_only=True)
        assert service.discover(scope, live=False, read_only=False)["verification"] == "synthetic"


def test_actual_cli_subprocess_and_budget(tmp_path: Path) -> None:
    executable = Path(".venv/bin/dce").resolve()
    prefix = [str(executable), "--catalog", str(tmp_path / "catalog.sqlite3")]
    completed = subprocess.run(
        [*prefix, "init", "--fixture", str(FIXTURE), "--no-ai"],
        capture_output=True,
        text=True,
        timeout=15,
        check=True,
    )
    assert json.loads(completed.stdout)["status"] == "ok"
    completed = subprocess.run(
        [*prefix, "--output-budget", "1024", "catalog", "list", "--limit", "100"],
        capture_output=True,
        text=True,
        timeout=15,
        check=True,
    )
    assert len(completed.stdout.encode()) < 1024
    assert json.loads(completed.stdout)["truncated"]
    assert not completed.stderr
