import json
from contextlib import ExitStack
from pathlib import Path

import httpx
import pytest
from test_connectors import reader

from dce.common.errors import DceError
from dce.connectors.gitlab import GitLab
from dce.connectors.portainer import Portainer
from dce.connectors.zentao import ZenTao
from dce.discovery.checkpoint import Checkpoint
from dce.discovery.crawler import Crawler, ScanScope


def test_three_platform_scoped_discovery(tmp_path: Path) -> None:
    calls = []

    def stack(stack_id: int) -> dict[str, object]:
        return {
            "Id": stack_id,
            "Name": "demo-current" if stack_id == 103 else "demo-old",
            "Namespace": "",
            "EndpointId": 1,
            "SwarmId": "current" if stack_id == 103 else "old",
            "GitConfig": {
                "URL": "https://user:auth-secret@demo.example.invalid/demo/app.git",
                "ReferenceName": "refs/heads/master",
                "ConfigFilePath": "compose.yml",
                "Authentication": {"Password": "auth-secret"},
            },
        }

    def handle(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        calls.append(path)
        assert request.method == "GET"
        if path == "/api/stacks":
            return httpx.Response(200, json=[stack(101), stack(102), stack(103)])
        if path in {f"/api/stacks/{n}" for n in (101, 102, 103)}:
            return httpx.Response(200, json=stack(int(path.rsplit("/", 1)[-1])))
        if path.endswith("/file"):
            return httpx.Response(
                200,
                json={
                    "StackFileContent": "services:\n  one:\n    image: demo/app:latest\n"
                    "    environment: {PASSWORD: compose-secret}\n"
                },
            )
        if path.endswith("/docker/info"):
            return httpx.Response(200, json={"Swarm": {"Cluster": {"ID": "current"}}})
        if path.endswith("/docker/services"):
            return httpx.Response(
                200,
                json=[
                    {
                        "ID": "runtime1",
                        "Spec": {
                            "Name": "demo-current_one",
                            "Labels": {"com.docker.stack.namespace": "demo-current"},
                            "TaskTemplate": {
                                "ContainerSpec": {
                                    "Image": "demo/app:latest",
                                    "Env": ["TOKEN=env-secret"],
                                }
                            },
                        },
                    },
                    {"ID": "infra", "Spec": {"Labels": {"com.docker.stack.namespace": "infra"}}},
                    {"Spec": {"Labels": {"com.docker.stack.namespace": "demo-current"}}},
                ],
            )
        if path == "/api/v4/groups/demo/projects":
            return httpx.Response(200, json=[{"id": 7}])
        if path == "/api/v4/projects/7":
            return httpx.Response(
                200, json={"id": 7, "default_branch": "master", "path_with_namespace": "demo/app"}
            )
        if path.endswith("/commits/master"):
            return httpx.Response(200, json={"id": "abc"})
        if path.endswith("/tree"):
            return httpx.Response(200, json=[{"type": "blob", "path": "compose.yml"}])
        if path.endswith("/raw"):
            return httpx.Response(
                200,
                text="services:\n  one:\n    image: demo/app:latest\n"
                "  two:\n    image: demo/app:latest\n",
            )
        if path.endswith("/bugs"):
            return httpx.Response(
                200,
                json={
                    "bugs": [{"id": 1001, "title": "Synthetic icon", "steps": "private raw steps"}]
                },
            )
        if "/api.php/v1/" in path:
            return httpx.Response(200, json={"id": 1, "name": "Demo"})
        pytest.fail(f"Unexpected route: {path}")

    scope = ScanScope(
        gitlab_groups=["demo"],
        portainer_endpoints=["1"],
        portainer_stacks=["103"],
        zentao_projects=["1"],
        zentao_products=["2"],
    )
    checkpoint = Checkpoint(tmp_path / "scan.json", "three-platform-demo")
    with ExitStack() as contexts:
        adapters = {
            name: contexts.enter_context(reader(name, handle))
            for name in ("gitlab", "portainer", "zentao")
        }
        crawler = Crawler(
            scope,
            checkpoint,
            gitlab=GitLab(adapters["gitlab"]),
            portainer=Portainer(adapters["portainer"]),
            zentao=ZenTao(adapters["zentao"]),
        )
        result = crawler.run()
        assert len([e for e in result.entities if e.kind == "service"]) == 1
        assert len([e for e in result.entities if e.kind == "stack"]) == 3
        assert len([a for a in result.anomalies if a["status"] == "stale_candidate"]) == 2
        diffs = [a for a in result.anomalies if a["status"] == "config_drift_candidate"]
        assert len(diffs) == 3
        assert all(diff["added"] == ["two"] for diff in diffs)
        assert len([e for e in result.entities if e.kind == "bug"]) == 1
        assert len([e for e in result.edges if e.relation == "contains_bug"]) == 2
        assert len(crawler.run().entities) == len(result.entities)
    text = result.model_dump_json() + checkpoint.path.read_text()
    for secret in ("auth-secret", "compose-secret", "env-secret", "private raw steps"):
        assert secret not in text
    assert len(json.loads(checkpoint.path.read_text())["resources"]) == 5
    assert any(warning.startswith("INCOMPLETE_SERVICE") for warning in result.warnings)


@pytest.mark.parametrize("payload", [{"default_branch": None}, {"default_branch": "master"}])
def test_bad_git_metadata_marks_checkpoint_failed(
    tmp_path: Path, payload: dict[str, object]
) -> None:
    with reader("gitlab", lambda _: httpx.Response(200, json=payload)) as http:
        checkpoint = Checkpoint(tmp_path / "scan.json", "scope")
        with pytest.raises(DceError):
            Crawler(ScanScope(gitlab_projects=["1"]), checkpoint, gitlab=GitLab(http)).run()
        assert json.loads(checkpoint.path.read_text())["status"] == "failed"


def test_portainer_unknown_endpoint_fails_closed(tmp_path: Path) -> None:
    def handle(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"Id": 1, "Name": "demo"})

    with reader("portainer", handle) as http:
        crawler = Crawler(
            ScanScope(portainer_stacks=["1"]),
            Checkpoint(tmp_path / "scan.json", "scope"),
            portainer=Portainer(http),
        )
        with pytest.raises(DceError):
            crawler.runtime({"Id": 1})
