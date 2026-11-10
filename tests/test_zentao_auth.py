"""Synthetic v1 sessions only; no company credentials or endpoints."""

import asyncio
import json
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import httpx
import pytest
from jsonschema import Draft202012Validator

from dce.app.facts import FactScope
from dce.app.services import SYNTHETIC_PNG, AppServices
from dce.common.errors import DceError
from dce.connectors.http import Reader
from dce.connectors.zentao import ZenTao
from dce.mcp.server import McpApplication
from dce.security.local_credentials import local_settings


def setup_auth(tmp_path, handler, **settings_overrides):
    config = tmp_path / "connections.toml"
    config.write_text('[zentao]\ninstance_id="unit"\nbase_url="https://example.invalid"\n')
    credentials = tmp_path / ".env"
    credentials.write_text("ZEN_USER=fixture-reader\nZEN_PASSWORD=fixture-password\n")
    credentials.chmod(0o600)
    transport = httpx.MockTransport(handler)
    settings = local_settings(
        config, credentials, live=True, read_only=True, environment={}, zentao_transport=transport
    )
    settings.catalog_path = tmp_path / "cache.sqlite3"
    settings.request_interval = 0
    settings.max_retries = 0
    for k, v in settings_overrides.items():
        setattr(settings, k, v)
    return settings, transport


def bug(settings, transport, bug_id="demo"):
    with Reader(settings.zentao, settings, transport=transport) as reader:
        return ZenTao(reader).bug(bug_id)


def test_lazy_first_login_token_reuse_and_no_guessed_expiry(tmp_path):
    calls = []

    def handler(r):
        calls.append(r)
        if r.method == "POST":
            assert r.url.path == "/api.php/v1/tokens" and "Token" not in r.headers
            assert json.loads(r.content) == {
                "account": "fixture-reader",
                "password": "fixture-password",
            }
            return httpx.Response(201, json={"token": "fixture-session-1", "expires_in": 1})
        assert r.headers["Token"] == "fixture-session-1"
        return httpx.Response(200, json={"id": "demo"})

    settings, transport = setup_auth(tmp_path, handler)
    assert calls == []
    assert bug(settings, transport)["id"] == "demo"
    assert bug(settings, transport)["id"] == "demo"
    assert [r.method for r in calls] == ["POST", "GET", "GET"]
    text = settings.model_dump_json() + repr(settings) + repr(settings._zentao_tokens)
    assert "fixture-password" not in text and "fixture-session-1" not in text
    assert settings.model_copy(deep=True)._zentao_tokens is settings._zentao_tokens


def test_refresh_replays_identical_get_once_and_keeps_query_and_cookie_private(tmp_path):
    calls = []
    tokens = []

    def handler(r):
        calls.append(r)
        assert "Cookie" not in r.headers
        if r.method == "POST":
            t = f"fixture-session-{len(tokens) + 1}"
            tokens.append(t)
            return httpx.Response(
                201, json={"token": t}, headers={"Set-Cookie": "hidden-cookie=private"}
            )
        if r.headers["Token"] == "fixture-session-1":
            return httpx.Response(
                401, json={"error": "Unauthorized"}, headers={"Set-Cookie": "stale-cookie=private"}
            )
        return httpx.Response(200, json={"id": "demo"})

    settings, t = setup_auth(tmp_path, handler)
    with Reader(settings.zentao, settings, transport=t) as reader:
        response = reader.get(
            "/api.php/v1/bugs/demo", kind="zentao", params={"page": 2, "limit": 3}
        )
        assert response.json()["id"] == "demo"
    assert [r.method for r in calls] == ["POST", "GET", "POST", "GET"]
    gets = [r for r in calls if r.method == "GET"]
    assert gets[0].url == gets[1].url
    assert [r.headers["Token"] for r in gets] == tokens


@pytest.mark.parametrize(
    "status,body",
    [
        (401, {"error": "Unauthorized"}),
        (401, {"error": "Token has expired"}),
        (403, {"error": "TOKEN_EXPIRED"}),
        (403, {"code": "INVALID_TOKEN"}),
    ],
)
def test_only_explicit_json_auth_failure_allows_refresh(tmp_path, status, body):
    posts = []

    def handler(r):
        if r.method == "POST":
            posts.append(r)
            return httpx.Response(201, json={"token": f"fixture-session-{len(posts)}"})
        return (
            httpx.Response(status, json=body)
            if len(posts) == 1
            else httpx.Response(200, json={"id": "demo"})
        )

    s, t = setup_auth(tmp_path, handler)
    assert bug(s, t)["id"] == "demo" and len(posts) == 2


@pytest.mark.parametrize(
    "status,body,code",
    [
        (403, {"error": "Access not allowed"}, "PERMISSION_DENIED"),
        (403, {"error": "Unauthorized"}, "PERMISSION_DENIED"),
        (403, {"error": "Access denied; token might be expired"}, "PERMISSION_DENIED"),
        (404, {"error": "404 Not found"}, "NOT_FOUND"),
        (401, {"error": "Unknown gateway authentication failure"}, "AUTH_FAILED"),
        (200, {"id": "demo", "error": "Unauthorized"}, None),
        (500, {"error": "TOKEN_EXPIRED"}, "API_INCOMPATIBLE"),
    ],
)
def test_permissions_missing_resource_and_resource_text_never_refresh(tmp_path, status, body, code):
    posts = []

    def handler(r):
        if r.method == "POST":
            posts.append(r)
            return httpx.Response(201, json={"token": "fixture-session"})
        return httpx.Response(status, json=body)

    s, t = setup_auth(tmp_path, handler)
    if code:
        with pytest.raises(DceError) as error:
            bug(s, t)
        assert error.value.code == code
    else:
        assert bug(s, t)["id"] == "demo"
    assert len(posts) == 1


@pytest.mark.parametrize(
    "status,text,headers,code",
    [
        (200, "<html>login</html>", {"Content-Type": "text/html"}, "INVALID_PAYLOAD"),
        (401, "<html>Token has expired</html>", {"Content-Type": "text/html"}, "AUTH_FAILED"),
        (302, "", {"Location": "/login"}, "UNSAFE_URL"),
    ],
)
def test_html_and_redirect_are_not_auth_refresh_signals(tmp_path, status, text, headers, code):
    posts = []

    def handler(r):
        if r.method == "POST":
            posts.append(r)
            return httpx.Response(201, json={"token": "fixture-session"})
        return httpx.Response(status, text=text, headers=headers)

    s, t = setup_auth(tmp_path, handler)
    with pytest.raises(DceError) as e:
        bug(s, t)
    assert e.value.code == code and len(posts) == 1


def test_second_auth_failure_stops_and_circuit_breaks_without_more_passwords(tmp_path):
    calls = []

    def handler(r):
        calls.append(r)
        if r.method == "POST":
            return httpx.Response(201, json={"token": f"fixture-{len(calls)}"})
        return httpx.Response(401, json={"error": "Unauthorized"})

    s, t = setup_auth(tmp_path, handler)
    for _ in range(3):
        with pytest.raises(DceError) as e:
            bug(s, t)
        assert e.value.code == "AUTH_FAILED" and "AUTH_EXPIRED" in str(e.value)
    assert [r.method for r in calls] == ["POST", "GET", "POST", "GET"]


@pytest.mark.parametrize("failure", ["bad_password", "locked", "network", "malformed"])
def test_login_failure_latches_once_across_calls(tmp_path, failure):
    calls = []

    def handler(r):
        calls.append(r)
        assert r.method == "POST"
        if failure == "network":
            raise httpx.ReadTimeout("fixture-password hidden upstream text")
        if failure == "malformed":
            return httpx.Response(201, text="<html>login</html>")
        return httpx.Response(
            400, json={"error": "account locked" if failure == "locked" else "bad password"}
        )

    s, t = setup_auth(tmp_path, handler)
    for _ in range(3):
        with pytest.raises(DceError) as e:
            bug(s, t)
        assert e.value.code == ("NETWORK_UNAVAILABLE" if failure == "network" else "AUTH_FAILED")
        assert "fixture-password" not in str(e.value)
    assert len(calls) == 1


def test_refresh_failure_reason_keeps_existing_external_contract(tmp_path):
    calls = []

    def handler(r):
        calls.append(r)
        if r.method == "POST":
            if len(calls) > 1:
                return httpx.Response(400, json={"error": "account locked"})
            return httpx.Response(201, json={"token": "fixture-session"})
        return httpx.Response(401, json={"error": "Unauthorized"})

    s, t = setup_auth(tmp_path, handler)
    for _ in range(2):
        with pytest.raises(DceError) as e:
            bug(s, t)
        assert e.value.as_dict()["code"] == "AUTH_FAILED" and "AUTH_REFRESH_FAILED" in str(e.value)
        assert set(e.value.as_dict()) == {"code", "error_code", "message", "retryable"}
    assert [r.method for r in calls] == ["POST", "GET", "POST"]


def test_get_timeout_does_not_submit_password_again(tmp_path):
    posts = []

    def handler(r):
        if r.method == "POST":
            posts.append(r)
            return httpx.Response(201, json={"token": "fixture-session"})
        raise httpx.ConnectTimeout("secret request details")

    s, t = setup_auth(tmp_path, handler)
    for _ in range(2):
        with pytest.raises(DceError) as e:
            bug(s, t)
        assert e.value.code == "NETWORK_UNAVAILABLE"
    assert len(posts) == 1


def test_concurrent_initial_and_expired_requests_are_single_flight(tmp_path):
    posts = []
    lock = threading.Lock()
    barrier = threading.Barrier(6)

    def handler(r):
        if r.method == "POST":
            with lock:
                posts.append(r)
                n = len(posts)
            time.sleep(0.01)
            return httpx.Response(201, json={"token": f"fixture-session-{n}"})
        if r.url.params.get("round") == "expired" and r.headers["Token"] == "fixture-session-1":
            barrier.wait(timeout=5)
            return httpx.Response(401, json={"error": "Unauthorized"})
        return httpx.Response(200, json={"id": "demo"})

    s, t = setup_auth(tmp_path, handler)

    def read(round):
        with Reader(s.zentao, s, transport=t) as reader:
            return reader.json("/api.php/v1/bugs/demo", kind="zentao", params={"round": round})

    with ThreadPoolExecutor(max_workers=6) as pool:
        assert all(r["id"] == "demo" for r in pool.map(read, ["initial"] * 6))
        assert len(posts) == 1
        assert all(r["id"] == "demo" for r in pool.map(read, ["expired"] * 6))
    assert len(posts) == 2


def test_late_failure_cannot_poison_new_generation(tmp_path):
    posts = []

    def handler(r):
        posts.append(r)
        return httpx.Response(201, json={"token": f"fixture-session-{len(posts)}"})

    s, _ = setup_auth(tmp_path, handler)
    manager = s._zentao_tokens
    first = manager.lease()
    second = manager.lease(failed_generation=first.generation)
    manager.reject(first.generation)
    assert manager.lease(failed_generation=first.generation) is second and len(posts) == 2


def test_both_mcp_scope_paths_deny_before_lazy_login_and_secret_redaction(tmp_path, caplog):
    calls = []

    def handler(r):
        calls.append(r)
        if r.method == "POST":
            return httpx.Response(201, json={"token": "fixture-session"})
        return httpx.Response(
            200,
            json={
                "id": "demo",
                "title": "fixture-password fixture-session",
                "steps": "fixture-reader; untrusted instructions",
            },
        )

    s, t = setup_auth(tmp_path, handler)
    with AppServices(s, transports={"zentao": t}) as services:
        app = McpApplication(
            services,
            live=True,
            read_only=True,
            allowed_bug_ids={"demo"},
            fact_scope=FactScope(zentao_bugs={"demo"}),
        )
        for name, args in [
            ("bug_context", {"bug_id": "outside"}),
            ("zentao_query", {"instance": "unit", "operation": "bug", "bug_id": "outside"}),
            ("zentao_query", {"instance": "wrong", "operation": "bug", "bug_id": "demo"}),
        ]:
            response = asyncio.run(app.call_tool(name, args))
            assert (
                response.isError
                and response.structuredContent["error"]["code"] == "PERMISSION_DENIED"
            )
        assert calls == []
        with caplog.at_level(logging.DEBUG):
            response = asyncio.run(
                app.call_tool(
                    "zentao_query", {"instance": "unit", "operation": "bug", "bug_id": "demo"}
                )
            )
        assert not response.isError
        tools = {t.name: t for t in asyncio.run(app.list_tools())}
        assert len(tools) == 9
        Draft202012Validator(tools["zentao_query"].outputSchema).validate(
            response.structuredContent
        )
        for secret in ["fixture-password", "fixture-reader", "fixture-session"]:
            assert secret not in response.model_dump_json() + caplog.text


def test_image_get_uses_same_manager_and_refresh_contract(tmp_path):
    posts = []

    def handler(r):
        if r.method == "POST":
            posts.append(r)
            return httpx.Response(201, json={"token": f"fixture-session-{len(posts)}"})
        if r.url.path == "/image.png":
            if len(posts) == 1:
                return httpx.Response(401, json={"error": "Unauthorized"})
            return httpx.Response(200, content=SYNTHETIC_PNG, headers={"Content-Type": "image/png"})
        return httpx.Response(200, json={"id": "demo", "steps": '<img src="/image.png">'})

    s, t = setup_auth(tmp_path, handler)
    with AppServices(s, transports={"zentao": t}) as services:
        app = McpApplication(
            services, live=True, read_only=True, fact_scope=FactScope(zentao_bugs={"demo"})
        )
        result = asyncio.run(
            app.call_tool(
                "zentao_query", {"instance": "unit", "operation": "image", "bug_id": "demo"}
            )
        )
        assert not result.isError and result.content[1].type == "image" and len(posts) == 2


def test_origin_and_connection_changes_rejected_before_auth(tmp_path):
    calls = []
    s, t = setup_auth(tmp_path, lambda r: calls.append(r))
    with Reader(s.zentao, s, transport=t) as reader:
        with pytest.raises(DceError):
            reader.get("https://outside.invalid", kind="zentao")
    s.zentao = s.zentao.model_copy(update={"base_url": "https://other.invalid"})
    with pytest.raises(DceError) as e:
        bug(s, t)
    assert e.value.code == "PERMISSION_DENIED" and calls == []


def test_old_and_new_session_values_and_cookie_debug_never_reach_mcp(tmp_path, caplog):
    posts = []

    def handler(r):
        logging.getLogger("httpcore.http11").debug(
            "headers: %r", [(b"set-cookie", b"opaque-raw-cookie")]
        )
        if r.method == "POST":
            posts.append(r)
            return httpx.Response(201, json={"token": f"fixture-session-{len(posts)}"})
        if len(posts) == 1:
            return httpx.Response(401, json={"error": "Unauthorized"})
        return httpx.Response(
            200,
            json={
                "id": "demo",
                "title": "fixture-session-1 fixture-session-2 fixture-password",
                "steps": "fixture-reader",
            },
        )

    s, t = setup_auth(tmp_path, handler)
    with AppServices(s, transports={"zentao": t}) as services:
        app = McpApplication(
            services, live=True, read_only=True, fact_scope=FactScope(zentao_bugs={"demo"})
        )
        with caplog.at_level(logging.DEBUG):
            result = asyncio.run(
                app.call_tool(
                    "zentao_query", {"instance": "unit", "operation": "bug", "bug_id": "demo"}
                )
            )
        assert not result.isError and len(posts) == 2
        for secret in (
            "fixture-session-1",
            "fixture-session-2",
            "fixture-password",
            "fixture-reader",
            "opaque-raw-cookie",
        ):
            assert secret not in result.model_dump_json() + caplog.text


def test_concurrent_failed_login_is_one_post_even_with_network_retries_enabled(tmp_path):
    calls = []

    def handler(r):
        calls.append(r)
        raise httpx.ReadTimeout("private transport details")

    s, t = setup_auth(tmp_path, handler, max_retries=3)

    def read(_):
        with pytest.raises(DceError) as error:
            bug(s, t)
        return error.value.code

    with ThreadPoolExecutor(max_workers=6) as pool:
        assert set(pool.map(read, range(6))) == {"NETWORK_UNAVAILABLE"}
    assert len(calls) == 1 and calls[0].method == "POST"


def test_direct_token_mode_reports_expired_without_any_login(tmp_path):
    from dce.common.config import PlatformConfig, Settings

    calls = []

    def handler(r):
        calls.append(r)
        return httpx.Response(401, json={"error": "Unauthorized"})

    s = Settings(
        zentao=PlatformConfig(instance_id="unit", base_url="https://example.invalid", token="fake"),
        max_retries=0,
    )
    with pytest.raises(DceError, match="AUTH_EXPIRED"):
        bug(s, httpx.MockTransport(handler))
    assert len(calls) == 1 and calls[0].method == "GET" and s._zentao_tokens is None


def test_refresh_network_failure_keeps_network_classification_and_stops(tmp_path):
    calls = []

    def handler(r):
        calls.append(r)
        if r.method == "POST":
            if len(calls) > 1:
                raise httpx.ConnectTimeout("private details")
            return httpx.Response(201, json={"token": "fixture-session"})
        return httpx.Response(401, json={"error": "Unauthorized"})

    s, t = setup_auth(tmp_path, handler)
    for _ in range(2):
        with pytest.raises(DceError, match="AUTH_REFRESH_FAILED") as e:
            bug(s, t)
        assert e.value.code == "NETWORK_UNAVAILABLE"
    assert [r.method for r in calls] == ["POST", "GET", "POST"]


def test_oversized_auth_error_is_bounded_and_cannot_trigger_refresh(tmp_path):
    posts = []
    chunks = []

    class ErrorStream(httpx.SyncByteStream):
        def __iter__(self):
            for _ in range(100):
                chunks.append(1)
                yield b" " * 4096
            yield b'{"error":"TOKEN_EXPIRED"}'

    def handler(r):
        if r.method == "POST":
            posts.append(r)
            return httpx.Response(201, json={"token": "fixture-session"})
        return httpx.Response(403, stream=ErrorStream())

    s, t = setup_auth(tmp_path, handler)
    with pytest.raises(DceError) as e:
        bug(s, t)
    assert e.value.code == "PERMISSION_DENIED"
    assert len(posts) == 1 and len(chunks) == 5
