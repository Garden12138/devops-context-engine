import json
import os
from pathlib import Path

import httpx
import pytest

from dce.common.config import load_settings
from dce.common.errors import DceError


def files(tmp_path: Path, text: str):
    credentials = tmp_path / ".env"
    credentials.write_text(text)
    credentials.chmod(0o600)
    config = tmp_path / "connections.toml"
    config.write_text(
        '[zentao]\ninstance_id="z"\nbase_url="https://zentao.example.invalid"\n'
        '[gitlab]\ninstance_id="g"\nbase_url="https://gitlab.example.invalid"\n'
        '[portainer]\ninstance_id="p"\nbase_url="https://portainer.example.invalid"\n'
    )
    return config, credentials


CREDENTIALS = (
    'ZEN_USER=reader\nZEN_PASSWORD="  fake-pass#${NOT_EXPANDED}  "\n'
    "GITLAB_TOKEN=fake-git\nPORTAINER_API_KEY=fake-port\n"
)


def test_explicit_local_v1_login_keeps_secrets_in_process(tmp_path, caplog):
    from dce.connectors.http import Reader
    from dce.connectors.zentao import ZenTao
    from dce.security.local_credentials import local_settings

    config, credentials = files(tmp_path, CREDENTIALS)
    requests = []

    def handle(request):
        requests.append(request)
        if request.method == "POST":
            assert request.url.path == "/api.php/v1/tokens"
            assert request.headers.get("Token") is None
            assert json.loads(request.content) == {
                "account": "reader",
                "password": "  fake-pass#${NOT_EXPANDED}  ",
            }
            return httpx.Response(201, json={"token": "fake-fresh-session"})
        assert request.headers["Token"] == "fake-fresh-session"
        return httpx.Response(200, json={"id": "b"})

    transport = httpx.MockTransport(handle)
    before = dict(os.environ)
    with caplog.at_level("DEBUG"):
        settings = local_settings(
            config,
            credentials,
            live=True,
            read_only=True,
            environment={},
            zentao_transport=transport,
        )
        with Reader(settings.platform("zentao"), settings, transport=transport) as reader:
            assert ZenTao(reader).bug("b")["id"] == "b"
    assert dict(os.environ) == before
    assert settings.gitlab.token.get_secret_value() == "fake-git"
    assert settings.portainer.token.get_secret_value() == "fake-port"
    assert len(requests) == 2 and requests[0].method == "POST" and requests[1].method == "GET"
    assert all(
        secret not in repr(settings) + caplog.text
        for secret in ("fake-pass", "fake-fresh-session", "fake-git", "fake-port")
    )
    assert credentials.read_text() == CREDENTIALS


def test_v1_auth_failure_is_single_attempt_without_get_or_persistence(tmp_path):
    from dce.security.local_credentials import local_settings

    config, credentials = files(tmp_path, CREDENTIALS)
    requests = []

    def deny(request):
        requests.append(request)
        return httpx.Response(401, text="private-error fake-pass")

    settings = local_settings(
        config,
        credentials,
        live=True,
        read_only=True,
        environment={},
        zentao_transport=httpx.MockTransport(deny),
    )
    assert requests == []
    from dce.connectors.http import Reader
    from dce.connectors.zentao import ZenTao

    with pytest.raises(DceError) as error:
        with Reader(settings.zentao, settings) as reader:
            ZenTao(reader).bug("demo")
    assert error.value.code == "AUTH_FAILED" and len(requests) == 1
    assert "fake-pass" not in str(error.value)
    assert sorted(p.name for p in tmp_path.iterdir()) == [".env", "connections.toml"]


def test_literal_parser_private_file_and_alias_conflicts(tmp_path):
    from dce.security.local_credentials import credential_environment

    _, credentials = files(tmp_path, CREDENTIALS + 'IGNORED="$(touch /tmp/never-run)"\n')
    values, account, password = credential_environment(credentials)
    assert account == "reader" and password.get_secret_value() == "  fake-pass#${NOT_EXPANDED}  "
    assert values["DCE_GITLAB_TOKEN"] == "fake-git" and "IGNORED" not in values
    credentials.chmod(0o644)
    with pytest.raises(DceError):
        credential_environment(credentials)
    credentials.chmod(0o600)
    credentials.write_text(CREDENTIALS + "GITLAB_TOKEN=other\n")
    with pytest.raises(DceError):
        credential_environment(credentials)
    credentials.write_text(CREDENTIALS + "DCE_GITLAB_TOKEN=conflicting\n")
    with pytest.raises(DceError):
        credential_environment(credentials)
    credentials.write_text('ZEN_PASSWORD="unterminated\n')
    with pytest.raises(DceError):
        credential_environment(credentials)
    credentials.write_text("x" * 65537)
    with pytest.raises(DceError):
        credential_environment(credentials)
    credentials.unlink()
    credentials.symlink_to(tmp_path / "elsewhere")
    with pytest.raises(DceError):
        credential_environment(credentials)


def test_readonly_and_http_gates_happen_before_login(tmp_path):
    from dce.security.local_credentials import local_settings

    config, credentials = files(tmp_path, CREDENTIALS)
    requests = []
    transport = httpx.MockTransport(lambda r: requests.append(r))
    for live, readonly in ((False, False), (True, False), (False, True)):
        with pytest.raises(DceError):
            local_settings(
                config,
                credentials,
                live=live,
                read_only=readonly,
                environment={},
                zentao_transport=transport,
            )
    config.write_text(config.read_text().replace("https://zentao", "http://zentao"))
    with pytest.raises(DceError) as error:
        local_settings(
            config,
            credentials,
            live=True,
            read_only=True,
            environment={},
            zentao_transport=transport,
        )
    assert error.value.code == "UNSAFE_URL" and requests == []


def test_default_settings_does_not_load_credentials_and_environment_is_injectable(
    tmp_path, monkeypatch
):
    config, credentials = files(tmp_path, CREDENTIALS)
    monkeypatch.chdir(tmp_path)
    assert load_settings().zentao is None
    settings = load_settings(
        environ={
            "DCE_GITLAB_URL": "https://gitlab.example.invalid",
            "DCE_GITLAB_TOKEN": "fake-only",
        }
    )
    assert settings.gitlab and settings.zentao is None


def test_explicit_loader_supports_independent_platform_and_direct_token(tmp_path):
    from dce.security.local_credentials import local_settings

    config, credentials = files(tmp_path, CREDENTIALS)
    config.write_text('[gitlab]\nbase_url="https://gitlab.example.invalid"\n')
    settings = local_settings(config, credentials, live=True, read_only=True, environment={})
    assert settings.gitlab and settings.zentao is None and settings.portainer is None
    credentials.write_text("DCE_ZENTAO_TOKEN=fake-direct\n")
    config.write_text('[zentao]\nbase_url="https://zentao.example.invalid"\n')
    settings = local_settings(config, credentials, live=True, read_only=True, environment={})
    assert settings.zentao.token.get_secret_value() == "fake-direct"
    config.write_text("allow_http=false\n")
    with pytest.raises(DceError, match="addresses are missing"):
        local_settings(config, credentials, live=True, read_only=True, environment={})
    credentials.write_text("ZEN_USER=reader\n")
    from dce.security.local_credentials import credential_environment

    with pytest.raises(DceError):
        credential_environment(credentials)


def test_local_launcher_failure_stays_off_stdout(tmp_path):
    import subprocess

    config, credentials = files(tmp_path, CREDENTIALS)
    result = subprocess.run(
        [
            str(Path(".venv/bin/python").absolute()),
            str(Path("scripts/serve_dce_local.py").resolve()),
            "--config",
            str(config),
            "--credentials-file",
            str(credentials),
            "--catalog",
            str(tmp_path / "cache.sqlite3"),
        ],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 2 and result.stdout == ""
    assert json.loads(result.stderr)["error"]["code"] == "PERMISSION_DENIED"
    assert "fake-pass" not in result.stderr


def test_url_aliases_are_literal_and_conflicts_fail_closed(tmp_path):
    from dce.security.local_credentials import credential_environment

    _, credentials = files(
        tmp_path,
        CREDENTIALS
        + "ZEN_URL=https://zentao.example.invalid\nGITLAB_URL=https://gitlab.example.invalid\n"
        "PORTAINER_URL=https://portainer.example.invalid\n",
    )
    values, _, _ = credential_environment(credentials)
    assert values["DCE_ZENTAO_URL"] == "https://zentao.example.invalid"
    assert values["DCE_GITLAB_URL"] == "https://gitlab.example.invalid"
    assert values["DCE_PORTAINER_URL"] == "https://portainer.example.invalid"
    credentials.write_text(
        credentials.read_text() + "DCE_ZENTAO_URL=https://conflict.example.invalid\n"
    )
    with pytest.raises(DceError):
        credential_environment(credentials)


def test_explicit_process_address_overrides_local_file_alias(tmp_path):
    from dce.security.local_credentials import local_settings

    config, credentials = files(
        tmp_path, "DCE_ZENTAO_TOKEN=fixture\nZEN_URL=https://site.example.invalid\n"
    )
    config.write_text("allow_http=false\n")
    settings = local_settings(
        config,
        credentials,
        live=True,
        read_only=True,
        environment={"DCE_ZENTAO_URL": "https://site.example.invalid/application"},
    )
    assert settings.zentao.base_url == "https://site.example.invalid/application"
