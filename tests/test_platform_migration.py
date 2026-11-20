"""Offline regression checks for retained clients after the dependency cleanup."""

import httpx
import pytest
from pydantic import SecretStr

from dce.errors import DceError
from dce.platforms.gitlab import GitLab
from dce.platforms.http import PlatformClient
from dce.platforms.portainer import Portainer
from dce.platforms.zentao import ZenTao
from dce.settings import PlatformConfig, Settings


def client(handler):
    return PlatformClient(
        PlatformConfig(
            instance_id="demo", base_url="https://api.example.invalid", token=SecretStr("synthetic")
        ),
        Settings(request_interval=0, max_retries=0),
        transport=httpx.MockTransport(handler),
    )


def test_bug_body_extracts_images_and_removes_active_html():
    text, images = ZenTao.parse_steps(
        {
            "steps": "<script>hidden()</script><style>hidden</style><iframe>hidden</iframe>"
            '<p>demo steps</p><img src="/demo.png"><img src="/demo.png">',
            "files": {"1": {"url": "/attached.jpg"}, "2": "ignored"},
        }
    )
    assert text == "demo steps"
    assert images == ["/demo.png", "/attached.jpg"]


@pytest.mark.parametrize(
    "mime,body",
    [
        ("text/html", b"<html>login</html>"),
        ("image/png", b"not a PNG"),
    ],
)
def test_image_validation_survives_dependency_cleanup(mime, body):
    with client(
        lambda r: httpx.Response(200, headers={"Content-Type": mime}, content=body)
    ) as http:
        with pytest.raises(DceError, match="verified image"):
            ZenTao(http).image_content("/demo.png")


def test_retained_gitlab_routes_and_raw_file_encoding():
    requests = []

    def handle(request):
        requests.append(request)
        assert request.method == "GET" and request.headers["PRIVATE-TOKEN"] == "synthetic"
        if request.url.path.endswith("/raw"):
            assert b"dir%2Fdemo.yml" in request.url.raw_path
            assert request.url.params["ref"] == "develop"
            return httpx.Response(200, text="demo CI")
        if request.url.path.endswith(("/pipelines", "/jobs")):
            return httpx.Response(200, json=[{"id": 2}], headers={"X-Next-Page": ""})
        if request.url.path.endswith("/trace"):
            return httpx.Response(200, text="demo trace")
        return httpx.Response(200, json={"id": 1})

    with client(handle) as http:
        gitlab = GitLab(http)
        assert gitlab.project("1") == {"id": 1}
        assert gitlab.raw_file("1", "dir/demo.yml", "develop") == "demo CI"
        assert list(gitlab.pipelines("1", "develop")) == [{"id": 2}]
        assert gitlab.pipeline("1", "2") == {"id": 1}
        assert list(gitlab.jobs("1", "2")) == [{"id": 2}]
        assert gitlab.trace("1", "2") == "demo trace"
    assert len(requests) == 6


def test_retained_portainer_reads_filter_secrets_and_namespace():
    stack = {
        "Id": 1,
        "Name": "demo_test",
        "Env": [{"name": "secret", "value": "synthetic"}],
        "GitConfig": {
            "URL": "https://demo-user:synthetic@gitlab.example.invalid/demo/demo-cloud.git",
            "Authentication": "synthetic",
        },
    }
    service = {"ID": "demo1", "Spec": {"Labels": {"com.docker.stack.namespace": "demo_test"}}}

    def handle(request):
        assert request.method == "GET" and request.headers["X-API-Key"] == "synthetic"
        path = request.url.path
        if path.endswith("/stacks"):
            return httpx.Response(200, json=[stack])
        if path.endswith("/file"):
            assert request.url.params["endpointId"] == "1"
            return httpx.Response(200, json={"StackFileContent": "services: {}"})
        if path.endswith("/endpoints"):
            return httpx.Response(200, json=[{"Id": 1, "Name": "demo", "Secret": "synthetic"}])
        if path.endswith("/endpoints/1"):
            return httpx.Response(200, json={"Id": 1, "Secret": "synthetic"})
        assert path.endswith("/services")
        return httpx.Response(200, json=[service])

    with client(handle) as http:
        portainer = Portainer(http)
        stacks = portainer.stacks()
        assert stacks[0]["GitConfig"] == {
            "URL": "https://gitlab.example.invalid/demo/demo-cloud.git"
        }
        assert "Env" not in stacks[0]
        assert portainer.stack_file("1", "1") == "services: {}"
        assert portainer.endpoints() == [{"Id": 1, "Name": "demo"}]
        assert portainer.endpoint("1") == {"Id": 1}
        assert portainer.services("1", "demo_test") == [service]
        assert portainer.services("1", "demo_other") == []
