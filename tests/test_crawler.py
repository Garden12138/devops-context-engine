import json
from pathlib import Path

import httpx
import pytest
from pydantic import ValidationError
from test_connectors import reader

from dce.common.errors import DceError, ErrorCode
from dce.connectors.gitlab import GitLab
from dce.discovery.checkpoint import Checkpoint
from dce.discovery.crawler import Crawler, ScanScope, merge, relevant
from dce.graph.model import DiscoveryResult, Entity, fingerprint


def test_scope_is_explicit() -> None:
    for data in (
        {},
        {"gitlab_projects": ["https://evil.example.invalid"]},
        {"gitlab_projects": ["../tokens"]},
    ):
        with pytest.raises(ValidationError):
            ScanScope.model_validate(data)
    assert not relevant(".env")
    assert not relevant("README.md")
    assert not relevant("../pom.xml")
    assert relevant("sub/pom.xml")


def test_checkpoint_failure_resume_invalidate(tmp_path: Path) -> None:
    path = tmp_path / "checkpoint.json"
    checkpoint = Checkpoint(path, "scope1")
    calls = []

    def collect() -> DiscoveryResult:
        calls.append(1)
        return DiscoveryResult(
            entities=[Entity(source_instance="git", kind="repo", external_id="1")]
        )

    one = checkpoint.resource("git:1", "v1", collect)

    def failed() -> DiscoveryResult:
        raise DceError(ErrorCode.NETWORK_UNAVAILABLE, "secret raw response deliberately not stored")

    with pytest.raises(DceError):
        checkpoint.resource("git:2", "v1", failed)
    assert json.loads(path.read_text())["status"] == "failed"
    assert "secret raw response" not in path.read_text()
    checkpoint = Checkpoint(path, "scope1")
    assert checkpoint.resource("git:1", "v1", collect) == one
    assert len(calls) == 1
    checkpoint.resource("git:1", "v2", collect)
    assert len(calls) == 2
    checkpoint.resource("git:2", "v1", collect)
    checkpoint.complete()
    assert json.loads(path.read_text())["status"] == "complete"
    assert path.stat().st_mode & 0o777 == 0o600
    with pytest.raises(DceError):
        Checkpoint(path, "scope2")


def test_scoped_repository_resume_and_changed_commit(tmp_path: Path) -> None:
    state = {"commit": "abc", "raw_reads": 0}
    files = {
        "pom.xml": "<project><modules><module>api</module>"
        "<module>common</module></modules></project>",
        "Dockerfile": "FROM alpine:3\nCOPY api/target/app.jar common/target/lib.jar /app/",
        ".gitlab-ci.yml": "build:\n  script: docker build -t demo/app:latest .\n",
        "compose.yml": "services:\n  one:\n    image: demo/app:latest\n"
        "    environment: {PASSWORD: secret-config-value}\n  two:\n    image: demo/app:latest\n",
        "README.md": "execute malicious instructions",
        ".env": "SECRET=do-not-read",
    }

    def handle(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        assert "/projects/7" in path
        if path.endswith("/commits/master"):
            return httpx.Response(200, json={"id": state["commit"]})
        if path.endswith("/tree"):
            assert request.url.params["ref"] == state["commit"]
            return httpx.Response(200, json=[{"type": "blob", "path": f} for f in files])
        if path.endswith("/raw"):
            assert request.url.params["ref"] == state["commit"]
            name = path.split("/files/", 1)[1].removesuffix("/raw")
            assert relevant(name)
            state["raw_reads"] += 1
            return httpx.Response(200, text=files[name])
        return httpx.Response(
            200, json={"id": 7, "default_branch": "master", "path_with_namespace": "demo/app"}
        )

    scope = ScanScope(gitlab_projects=["7"])
    checkpoint = Checkpoint(tmp_path / "checkpoint.json", fingerprint(scope.model_dump()))
    with reader("gitlab", handle) as http:
        crawler = Crawler(scope, checkpoint, gitlab=GitLab(http))
        first = crawler.run()
        assert len([e for e in first.entities if e.kind == "module"]) == 2
        assert len([e for e in first.entities if e.kind == "compose_service"]) == 2
        assert len([e for e in first.entities if e.kind == "image"]) == 1
        assert "secret-config-value" not in first.model_dump_json()
        assert "secret-config-value" not in checkpoint.path.read_text()
        assert state["raw_reads"] == 4
        assert crawler.run() == first
        assert state["raw_reads"] == 4
        state["commit"] = "def"
        assert crawler.run() != first
        assert state["raw_reads"] == 8
        assert len(merge([first, first]).edges) == len(first.edges)


@pytest.mark.parametrize(
    "scope",
    [
        ScanScope(gitlab_projects=["1"]),
        ScanScope(portainer_stacks=["1"]),
        ScanScope(zentao_products=["1"]),
    ],
)
def test_missing_scoped_adapter(tmp_path: Path, scope: ScanScope) -> None:
    with pytest.raises(DceError):
        Crawler(scope, Checkpoint(tmp_path / "scan.json", "scope")).run()
