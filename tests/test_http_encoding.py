"""Synthetic wire encodings; no real platform bodies or credentials."""

import gzip
import json
import zlib
from collections.abc import Iterator

import httpx
import pytest
from pydantic import SecretStr

from dce.errors import DceError, ErrorCode
from dce.platforms.gitlab import GitLab
from dce.platforms.http import PlatformClient
from dce.settings import PlatformConfig, Settings


class WireBytes(httpx.SyncByteStream):
    def __init__(self, data: bytes) -> None:
        self.data = data

    def __iter__(self) -> Iterator[bytes]:
        yield self.data


def reader(handler: httpx.MockTransport, *, max_bytes: int = 2000) -> PlatformClient:
    config = PlatformConfig(
        instance_id="encoding-demo",
        base_url="https://api.example.invalid",
        token=SecretStr("synthetic-credential"),
    )
    return PlatformClient(
        config,
        Settings(request_interval=0),
        transport=handler,
        max_bytes=max_bytes,
        sleep=lambda _: None,
    )


@pytest.mark.parametrize("encoding", ["gzip", "deflate", "gzip, deflate"])
def test_compressed_json_is_decoded_once_with_consistent_headers(encoding: str) -> None:
    body = b'{"id": 101, "default_branch": "develop"}'
    encoded = zlib.compress(body) if encoding == "deflate" else gzip.compress(body)
    if encoding == "gzip, deflate":
        encoded = zlib.compress(encoded)

    def handle(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        return httpx.Response(
            200,
            stream=WireBytes(encoded),
            headers={
                "Content-Encoding": encoding,
                "Content-Length": str(len(encoded)),
                "Content-Type": "application/json",
                "X-Next-Page": "2",
            },
        )

    with reader(httpx.MockTransport(handle)) as http:
        response = http.get("/api/v4/projects/101")
    assert response.content == body
    assert response.json()["id"] == 101
    assert "content-encoding" not in response.headers
    assert response.headers["content-length"] == str(len(body))
    assert response.headers["content-type"] == "application/json"
    assert response.headers["x-next-page"] == "2"


def test_compressed_pagination_preserves_cursor_and_removes_transfer_header() -> None:
    calls = []

    def handle(request: httpx.Request) -> httpx.Response:
        page = int(request.url.params["page"])
        calls.append(page)
        body = json.dumps([{"id": page}]).encode()
        return httpx.Response(
            200,
            stream=WireBytes(gzip.compress(body)),
            headers={
                "Content-Encoding": "gzip",
                "Transfer-Encoding": "chunked",
                "Content-Type": "application/json",
                "X-Next-Page": "2" if page == 1 else "",
            },
        )

    with reader(httpx.MockTransport(handle)) as http:
        assert [p["id"] for p in GitLab(http).projects()] == [1, 2]
        response = http.get("/api/v4/projects", params={"page": 1})
        assert "transfer-encoding" not in response.headers
    assert calls == [1, 2, 1]


def test_size_limit_applies_to_decompressed_bytes_without_retry() -> None:
    body = b"x" * 500
    encoded = gzip.compress(body)
    assert len(encoded) < 64 < len(body)
    calls = []

    def handle(request: httpx.Request) -> httpx.Response:
        calls.append(request.method)
        return httpx.Response(200, stream=WireBytes(encoded), headers={"Content-Encoding": "gzip"})

    with reader(httpx.MockTransport(handle), max_bytes=64) as http:
        with pytest.raises(DceError) as error:
            http.get("/api/v4/projects/101")
    assert error.value.code == ErrorCode.PLATFORM_ERROR
    assert not error.value.retryable
    assert calls == ["GET"]


def test_corrupt_compression_is_payload_error_without_retry_or_raw_output() -> None:
    calls = []

    def handle(request: httpx.Request) -> httpx.Response:
        calls.append(request.method)
        return httpx.Response(
            200,
            stream=WireBytes(b"synthetic-secret-not-valid-gzip"),
            headers={"Content-Encoding": "gzip"},
        )

    with reader(httpx.MockTransport(handle)) as http:
        with pytest.raises(DceError) as error:
            http.get("/api/v4/projects/101")
    assert error.value.code == ErrorCode.PLATFORM_ERROR
    assert not error.value.retryable
    assert "synthetic-secret" not in json.dumps(error.value.as_dict())
    assert calls == ["GET"]


def test_migrated_portainer_logs_keep_stack_and_swarm_checks():
    import asyncio

    from dce.platforms.docker_logs import LogControls
    from dce.platforms.portainer import Portainer

    service = {
        "ID": "demo1",
        "Version": {"Index": 3},
        "Spec": {
            "Name": "demo_test_demo-api",
            "Labels": {"com.docker.stack.namespace": "demo_test"},
            "TaskTemplate": {"ContainerSpec": {"TTY": False}},
        },
    }
    calls = []
    line = (
        b"2026-11-16T00:00:01Z com.docker.swarm.task.id=task1,"
        b"com.docker.swarm.service.id=demo1 INFO succeeded\n"
    )
    frame = b"\x01\0\0\0" + len(line).to_bytes(4, "big") + line

    def handle(request):
        calls.append(request.url.path)
        path = request.url.path
        if path == "/api/stacks/1":
            return httpx.Response(
                200,
                json={
                    "Id": 1,
                    "EndpointId": 1,
                    "Type": 1,
                    "SwarmId": "swarm1",
                    "Name": "demo_test",
                },
            )
        if path.endswith("/info"):
            return httpx.Response(200, json={"Swarm": {"Cluster": {"ID": "swarm1"}}})
        if path.endswith("/version"):
            return httpx.Response(200, json={"ApiVersion": "1.41"})
        if path.endswith("/logs"):
            assert request.url.params["since"] == "1794787200"
            return httpx.Response(200, content=frame)
        assert path.endswith("/services/demo1")
        return httpx.Response(200, json=service)

    with reader(httpx.MockTransport(handle)) as http:
        controls = LogControls(start_time="2026-11-16T00:00:00Z", end_time="2026-11-16T00:01:00Z")
        result = asyncio.run(
            Portainer(http).service_logs(
                "1",
                "1",
                service_id="demo1",
                service_name=None,
                controls=controls,
            )
        )
    assert result["error_type"] is None
    assert result["identity"]["namespace"] == "demo_test"
    assert result["events"][0]["signals"] == ["succeeded"]
    assert calls.count("/api/endpoints/1/docker/services/demo1") == 2


def test_log_frame_corruption_is_distinct_from_expired_retention():
    from dce.platforms.docker_logs import LogControls, LogRead, project_logs

    result = project_logs(
        LogRead(content=b"invalid frame header"),
        LogControls(start_time="2026-11-16T00:00:00Z", end_time="2026-11-16T00:01:00Z"),
        tty=False,
        service_id="demo1",
    )
    assert result["error_type"] == "PLATFORM_ERROR"
    assert result["retention"] == "not_verified"


@pytest.mark.parametrize("status", [401, 403, 404, 429, 500])
def test_http_failure_preserves_platform_resource_status_and_next_step(status):
    with reader(httpx.MockTransport(lambda r: httpx.Response(status))) as http:
        with pytest.raises(DceError) as error:
            http.get("/api/v4/projects/101")
    assert "gitlab" in error.value.message.lower()
    assert "/api/v4/projects/101" in error.value.message
    assert str(status) in error.value.message
    assert error.value.hint
