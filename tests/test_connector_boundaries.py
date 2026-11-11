import logging
import os
from pathlib import Path

import httpx
import pytest
from pydantic import SecretStr
from test_connectors import PNG, reader

from dce.app.doctor import doctor
from dce.common.config import PlatformConfig, Settings
from dce.common.errors import DceError
from dce.connectors.http import Reader
from dce.connectors.portainer import Portainer, safe_stack
from dce.connectors.zentao import ZenTao


def test_doctor_partial_failure_continues() -> None:
    config = PlatformConfig(
        instance_id="demo", base_url="https://demo.example.invalid", token="fake"
    )
    settings = Settings(zentao=config, gitlab=config, portainer=config)

    def handle(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/products"):
            return httpx.Response(403)
        if request.url.path.endswith("/projects") and "v1" in request.url.path:
            return httpx.Response(200, json={"projects": []})
        return httpx.Response(200, json=[])

    transports = {name: httpx.MockTransport(handle) for name in ("zentao", "gitlab", "portainer")}
    data = doctor(settings, transports=transports)
    assert data["platforms"]["zentao"]["status"] == "partial"
    assert data["platforms"]["zentao"]["capabilities"]["products_v1"]["code"] == "PERMISSION_DENIED"
    assert data["platforms"]["gitlab"]["status"] == "ok"
    assert data["platforms"]["portainer"]["status"] == "ok"


def test_readonly_enforced_before_transport() -> None:
    with reader("gitlab", lambda _: pytest.fail("mutation reached transport")) as http:
        for method, path, kind in [
            ("POST", "/api/v4/pipelines", "gitlab"),
            ("DELETE", "/api/stacks/1", "portainer"),
            ("POST", "/api.php/v1/bugs/1", "zentao"),
        ]:
            with pytest.raises(DceError):
                http._request(method, path, kind=kind)
    config = PlatformConfig(
        instance_id="demo", base_url="http://demo.example.invalid", token="fake"
    )
    with pytest.raises(DceError):
        Reader(config, Settings())


def test_retry_after_invalid_then_recovers() -> None:
    calls = []

    def handle(_: httpx.Request) -> httpx.Response:
        calls.append(1)
        return (
            httpx.Response(503, headers={"Retry-After": "invalid"})
            if len(calls) == 1
            else httpx.Response(200, json={})
        )

    with reader("gitlab", handle) as http:
        assert http.json("/api/v4/projects/1") == {}
    assert len(calls) == 2


def test_paging_limits_and_nonobject_items() -> None:
    with reader("gitlab", lambda _: httpx.Response(200, json=[1])) as http:
        with pytest.raises(DceError, match="objects"):
            list(http.pages("/api/v4/projects"))
    with reader(
        "gitlab", lambda _: httpx.Response(200, json=[{}], headers={"X-Next-Page": "2"})
    ) as http:
        with pytest.raises(DceError, match="Pagination limit"):
            list(http.pages("/api/v4/projects", max_pages=1))
    with reader(
        "gitlab", lambda _: httpx.Response(200, json=[], headers={"X-Next-Page": "bad"})
    ) as http:
        with pytest.raises(DceError, match="cursor"):
            list(http.pages("/api/v4/projects"))


def test_zentao_collections_and_files() -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api.php/v1/projects/1/bugs"
        page = int(request.url.params["page"])
        return httpx.Response(200, json={"bugs": [{"id": 1}] if page == 1 else []})

    with reader("zentao", handle) as http:
        http.settings.page_size = 1
        assert len(list(ZenTao(http).resources("bugs", parent="1"))) == 1
        with pytest.raises(DceError):
            list(ZenTao(http).resources("unsupported"))
    text, sources = ZenTao.parse_steps(
        {
            "steps": "safe",
            "files": {"1": {"url": "/one.png"}, "2": {"url": "/one.png"}, "3": "invalid"},
        }
    )
    assert text == "safe"
    assert sources == ["/one.png"]


def test_adapter_incompatible_shapes() -> None:
    with reader("zentao", lambda _: httpx.Response(200, json={})) as http:
        with pytest.raises(DceError):
            ZenTao(http).bug("1")
        with pytest.raises(DceError):
            ZenTao(http).create_token("demo", SecretStr("fake"))
        with pytest.raises(DceError):
            list(ZenTao(http).resources("projects"))
        with pytest.raises(DceError):
            Portainer(http).stack_file("1", "1")
        with pytest.raises(DceError):
            Portainer(http).docker_info("1")
    with reader("portainer", lambda _: httpx.Response(200, json={"GitConfig": ["bad"]})) as http:
        with pytest.raises(DceError):
            Portainer(http).stack("1")


def test_image_cache_symlink_refused(tmp_path: Path) -> None:
    target = tmp_path / "target"
    target.mkdir()
    link = tmp_path / "link"
    link.symlink_to(target, target_is_directory=True)
    with reader(
        "zentao", lambda _: httpx.Response(200, content=PNG, headers={"Content-Type": "image/png"})
    ) as http:
        with pytest.raises(DceError, match="private directory"):
            ZenTao(http).download_image("/file.png", link)
    assert not list(target.iterdir())


def test_zentao_page_limit() -> None:
    with reader("zentao", lambda _: httpx.Response(200, json={"projects": [{"id": 1}]})) as http:
        http.settings.page_size = 1
        with pytest.raises(DceError, match="pagination limit"):
            list(ZenTao(http).resources("projects", max_pages=1))


def test_asset_write_cleanup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_replace(*_: object) -> None:
        raise OSError("synthetic write failure")

    monkeypatch.setattr(os, "replace", fail_replace)
    with reader(
        "zentao", lambda _: httpx.Response(200, content=PNG, headers={"Content-Type": "image/png"})
    ) as http:
        with pytest.raises(OSError):
            ZenTao(http).download_image("/image.png", tmp_path)
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("url", ["file:///tmp/repo", "https://[broken", 1])
def test_unusable_repository_url_omitted(url: object) -> None:
    assert "URL" not in safe_stack({"GitConfig": {"URL": url}})["GitConfig"]


def test_auth_post_not_retried() -> None:
    calls = []

    def handle(_: httpx.Request) -> httpx.Response:
        calls.append(1)
        return httpx.Response(503)

    with reader("zentao", handle) as http:
        with pytest.raises(DceError):
            ZenTao(http).create_token("demo", SecretStr("fake"))
    assert len(calls) == 1


def test_http_log_does_not_expose_url_or_token(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)
    with reader("zentao", lambda _: httpx.Response(200, content=PNG)) as http:
        http.get("/image?Token=synthetic-credential", kind="zentao")
        logging.getLogger("httpcore.connection").debug("host='demo.example.invalid'")
    assert "synthetic-credential" not in caplog.text
    assert "demo.example.invalid" not in caplog.text


def test_malformed_attachment_url_is_structured(tmp_path: Path) -> None:
    with reader("zentao", lambda _: pytest.fail("Malformed URL reached transport")) as http:
        with pytest.raises(DceError):
            http.get("https://[broken")
        with pytest.raises(DceError):
            ZenTao(http).download_image("https://[broken", tmp_path)
