"""Synthetic wire encodings; no real platform bodies or credentials."""

import gzip
import json
import zlib
from collections.abc import Iterator

import httpx
import pytest
from pydantic import SecretStr

from dce.common.config import PlatformConfig, Settings
from dce.common.errors import DceError, ErrorCode
from dce.connectors.gitlab import GitLab
from dce.connectors.http import Reader


class WireBytes(httpx.SyncByteStream):
    def __init__(self, data: bytes) -> None:
        self.data = data

    def __iter__(self) -> Iterator[bytes]:
        yield self.data


def reader(handler: httpx.MockTransport, *, max_bytes: int = 2000) -> Reader:
    config = PlatformConfig(
        instance_id="encoding-demo",
        base_url="https://api.example.invalid",
        token=SecretStr("synthetic-credential"),
    )
    return Reader(
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
    assert error.value.code == ErrorCode.INVALID_PAYLOAD
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
    assert error.value.code == ErrorCode.INVALID_PAYLOAD
    assert not error.value.retryable
    assert "synthetic-secret" not in json.dumps(error.value.as_dict())
    assert calls == ["GET"]
