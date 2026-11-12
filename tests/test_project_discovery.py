"""Bounded initialization directories, partial results and strict source matching."""

import httpx
import pytest

from dce.app.services import AppServices
from dce.common.config import PlatformConfig, Settings
from dce.common.errors import DceError
from dce.project.discovery import DiscoverySeeds, ProjectDiscovery, repository


def test_discovery_is_bounded_and_keeps_partial_results(tmp_path):
    requests = []

    def handler(request):
        requests.append(request)
        if request.url.path.startswith("/api/v4"):
            return httpx.Response(403, json={"secret": "synthetic-not-for-output"})
        if request.url.path == "/api/stacks":
            return httpx.Response(
                200,
                json=[
                    {
                        "Id": 7,
                        "EndpointId": 1,
                        "Name": "demo",
                        "GitConfig": {"Authentication": "synthetic-not-for-output"},
                    },
                    {"Id": 8, "EndpointId": 2, "Name": "unrelated"},
                ],
            )
        kind = request.url.path.rsplit("/", 1)[-1]
        return httpx.Response(
            200,
            json={
                kind: [
                    {"id": f"{kind}-{i}", "name": "demo", "password": "synthetic-not-for-output"}
                    for i in range(30)
                ]
            },
        )

    settings = Settings(
        catalog_path=tmp_path / "cache",
        request_interval=0,
        **{
            name: PlatformConfig(
                instance_id=name, base_url="https://example.invalid", token="synthetic"
            )
            for name in ("gitlab", "zentao", "portainer")
        },
    )
    with AppServices(
        settings,
        transports={
            name: httpx.MockTransport(handler) for name in ("gitlab", "zentao", "portainer")
        },
    ) as services:
        discovery = ProjectDiscovery(services)
        discovery.run(
            DiscoverySeeds(gitlab_paths=["demo/api"], zentao_search="demo", portainer_search="demo")
        )
        assert len([r for r in requests if r.url.path.endswith("/projects")]) == 3
        assert len([r for r in requests if r.url.path.endswith("/products")]) == 3
        assert discovery.scope.portainer_stacks == {"7"}
        assert not discovery.scope.gitlab_projects
        assert "synthetic-not-for-output" not in str(discovery.records) + str(discovery.failures)
        assert {f["code"] for f in discovery.failures} == {
            "PERMISSION_DENIED",
            "DISCOVERY_PAGE_LIMIT",
        }


def test_no_seeds_no_network_and_remote_identity_is_verified(tmp_path):
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, json={"id": "other", "path_with_namespace": "other/project"})

    settings = Settings(
        catalog_path=tmp_path / "cache",
        gitlab=PlatformConfig(
            instance_id="gitlab", base_url="https://example.invalid", token="synthetic"
        ),
    )
    with AppServices(settings, transports={"gitlab": httpx.MockTransport(handler)}) as services:
        discovery = ProjectDiscovery(services)
        discovery.run(DiscoverySeeds())
        assert not requests
        discovery.run(DiscoverySeeds(gitlab_paths=["demo/api"]))
        assert not discovery.scope.gitlab_projects
        assert discovery.failures[0]["code"] == "API_INCOMPATIBLE"
    with pytest.raises(DceError):
        repository("https://user:synthetic@example.invalid/repo.git")
    assert repository("https://example.invalid/repo.git") == "example.invalid/repo"
