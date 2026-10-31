import json
import logging
from pathlib import Path

import pytest
from pydantic import ValidationError
from typer.testing import CliRunner

from dce.cli import app
from dce.common.config import PlatformConfig, Settings, load_settings
from dce.common.errors import DceError, ErrorCode
from dce.common.output import encode, envelope
from dce.security.redact import RedactingFilter, redact

runner = CliRunner()


def test_help_and_mock_doctor() -> None:
    assert runner.invoke(app, ["--help"]).exit_code == 0
    result = runner.invoke(app, ["doctor", "--mock"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert set(payload["data"]["platforms"]) == {"zentao", "gitlab", "portainer"}
    assert all(p["live_status"] == "not_verified" for p in payload["data"]["platforms"].values())


@pytest.mark.parametrize(
    "args,code",
    [
        (["--live"], "PERMISSION_DENIED"),
        (["--mock", "--live"], "INVALID_PAYLOAD"),
        (["--live", "--read-only"], "API_INCOMPATIBLE"),
    ],
)
def test_cli_safe_failures(args: list[str], code: str) -> None:
    result = runner.invoke(app, ["doctor", *args])
    assert result.exit_code == 2
    assert json.loads(result.stdout)["error"]["code"] == code


def test_config_precedence(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "settings.toml"
    path.write_text('timeout = 12\n[gitlab]\nbase_url="https://gitlab.example.invalid"\n')
    monkeypatch.setenv("DCE_TIMEOUT", "20")
    monkeypatch.setenv("DCE_GITLAB_TOKEN", "synthetic-credential")
    assert load_settings(path).timeout == 20
    settings = load_settings(path, timeout=30)
    assert settings.timeout == 30
    assert settings.platform("gitlab").instance_id == "gitlab"
    assert "synthetic-credential" not in repr(settings)
    path.write_text('[gitlab]\ntoken="forbidden"\n')
    with pytest.raises(DceError, match="Credentials must use environment"):
        load_settings(path)


def test_no_dotenv_and_safe_validation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("DCE_ALLOW_HTTP=true")
    assert not load_settings().allow_http
    monkeypatch.setenv("DCE_TIMEOUT", "not-a-timeout-secret")
    with pytest.raises(DceError) as error:
        load_settings()
    assert "not-a-timeout-secret" not in str(error.value)
    with pytest.raises(DceError):
        load_settings(tmp_path / "absent.toml")


@pytest.mark.parametrize(
    "url",
    [
        "file:///tmp/data",
        "https://u:p@example.invalid",
        "https://example.invalid/?token=synthetic",
        "relative",
    ],
)
def test_url_validation(url: str) -> None:
    with pytest.raises(ValidationError):
        PlatformConfig(instance_id="demo", base_url=url, token="fake")


def test_http_and_credentials() -> None:
    with pytest.raises(ValidationError):
        PlatformConfig(instance_id="demo", base_url="https://example.invalid", token=" ")
    with pytest.raises(DceError) as error:
        Settings().platform("gitlab")
    assert error.value.code == ErrorCode.AUTH_FAILED
    config = PlatformConfig(instance_id="demo", base_url="http://example.invalid/", token="fake")
    with pytest.raises(DceError) as error:
        Settings(gitlab=config).platform("gitlab")
    assert error.value.code == ErrorCode.UNSAFE_URL
    assert Settings(gitlab=config, allow_http=True).platform("gitlab") == config


def test_redaction_and_logging() -> None:
    value = {
        "Token": "fake",
        "GitConfig": {"Authentication": "fake"},
        "text": "password=fake https://internal.example.invalid/a 10.2.3.4 bare-secret",
    }
    result = json.dumps(redact(value, ("bare-secret", "")))
    assert all(
        secret not in result for secret in ("fake", "internal.example", "10.2.3.4", "bare-secret")
    )
    record = logging.LogRecord("dce", 40, "", 1, "Token=%s", ("fake",), None)
    assert RedactingFilter().filter(record)
    assert "fake" not in record.getMessage()
    assert redact([1, "safe"]) == [1, "safe"]


def test_envelope_budget() -> None:
    payload = json.loads(encode(envelope({"large": "图" * 10000}), 1024))
    assert payload["truncated"]
    assert len(encode(payload).encode()) <= 1024
    error = envelope(error=DceError(ErrorCode.NOT_FOUND, "Missing resource."))
    assert error["status"] == "error"
