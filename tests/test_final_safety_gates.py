import json
import os
from pathlib import Path

import httpx
import pytest
from test_connectors import reader

from dce.common.config import PlatformConfig, Settings
from dce.common.errors import DceError
from dce.connectors.gitlab import GitLab
from dce.connectors.http import Reader
from dce.connectors.zentao import ZenTao
from dce.discovery.checkpoint import Checkpoint
from dce.discovery.crawler import Crawler, ScanScope
from dce.graph.model import DiscoveryResult
from dce.security.redact import redact


def test_corrupt_checkpoint_fails_safely_and_atomic_write_preserves_previous(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "scan.json"
    path.write_text(
        json.dumps(
            {"schema_version": 1, "scope_key": "demo", "resources": {"repo": {"version": "v1"}}}
        )
    )
    with pytest.raises(DceError):
        Checkpoint(path, "demo")
    path.unlink()
    checkpoint = Checkpoint(path, "demo")
    checkpoint.resource("repo", "v1", DiscoveryResult)
    original = path.read_bytes()

    def failed_replace(*_: object) -> None:
        raise OSError("synthetic failure")

    monkeypatch.setattr(os, "replace", failed_replace)
    with pytest.raises(OSError):
        checkpoint.resource("repo", "v2", DiscoveryResult)
    assert path.read_bytes() == original
    assert list(tmp_path.iterdir()) == [path]
    monkeypatch.undo()
    state = json.loads(path.read_text())
    state["resources"]["repo"]["result"] = {"entities": [{"invalid": "private"}]}
    path.write_text(json.dumps(state))
    with pytest.raises(DceError):
        Checkpoint(path, "demo").resource("repo", "v1", DiscoveryResult)


def test_malformed_api_discovery_and_zentao_routes(tmp_path: Path) -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/groups/demo/projects"):
            return httpx.Response(200, json=[{}])
        return httpx.Response(200, json={})

    with reader("gitlab", handle) as http:
        checkpoint = Checkpoint(tmp_path / "scan.json", "demo")
        with pytest.raises(DceError):
            Crawler(ScanScope(gitlab_groups=["demo"]), checkpoint, gitlab=GitLab(http)).run()
        assert checkpoint.state["error_code"] == "INVALID_PAYLOAD"
    with reader("zentao", handle) as http:
        for operation in (
            lambda: ZenTao(http).resource("unsupported", "1"),
            lambda: ZenTao(http).resource("projects", "1"),
            lambda: list(ZenTao(http).resources("bugs", "1", parent_kind="invalid")),
        ):
            with pytest.raises(DceError):
                operation()


def test_workspace_glob_only_recognizes_workspace_package_roots(tmp_path: Path) -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/tree"):
            return httpx.Response(
                200,
                json=[
                    {"type": "blob", "path": name}
                    for name in (
                        "package.json",
                        "apps/api/package.json",
                        "apps/api/src/main.js",
                        "apps/empty/README.md",
                    )
                ],
            )
        if request.url.path.endswith("/raw"):
            return httpx.Response(
                200,
                text='{"workspaces":["apps/*"]}'
                if "/files/package.json/" in request.url.path
                else "{}",
            )
        if "/commits/" in request.url.path:
            return httpx.Response(200, json={"id": "abc"})
        return httpx.Response(200, json={"id": 1, "default_branch": "master"})

    with reader("gitlab", handle) as http:
        result = Crawler(
            ScanScope(gitlab_projects=["1"]),
            Checkpoint(tmp_path / "scan.json", "demo"),
            gitlab=GitLab(http),
        ).run()
    assert [e.attributes["path"] for e in result.entities if e.kind == "module"] == ["apps/api"]
    assert "registry.private.internal" not in redact("registry.private.internal/app:latest")


def test_configured_platform_subpath_is_preserved() -> None:
    seen = []

    def handle(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.path)
        return httpx.Response(200, json=[])

    config = PlatformConfig.model_validate(
        {
            "instance_id": "demo",
            "base_url": "https://demo.example.invalid/gitlab",
            "token": "synthetic",
        }
    )
    with Reader(config, Settings(), transport=httpx.MockTransport(handle)) as http:
        assert list(GitLab(http).projects()) == []
    assert seen == ["/gitlab/api/v4/projects"]
