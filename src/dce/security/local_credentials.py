"""Explicit local credential loading. Never implicit dotenv, shell evaluation or persistence."""

import io
import os
import stat
import tomllib
from collections.abc import Mapping
from pathlib import Path

import httpx
from dotenv.parser import parse_stream
from pydantic import SecretStr

from dce.common.config import Settings, load_settings
from dce.common.errors import DceError, ErrorCode
from dce.connectors.http import Reader
from dce.connectors.zentao import ZenTao

PLATFORMS = ("zentao", "gitlab", "portainer")
KNOWN_ENV = {f"DCE_{name.upper()}" for name in Settings.model_fields} | {
    f"DCE_{platform.upper()}_{field}"
    for platform in PLATFORMS
    for field in ("URL", "TOKEN", "INSTANCE_ID")
}
ALIASES = {
    "ZEN_URL": "DCE_ZENTAO_URL",
    "GITLAB_URL": "DCE_GITLAB_URL",
    "PORTAINER_URL": "DCE_PORTAINER_URL",
    "ZEN_USER": "_zentao_account",
    "DCE_ZENTAO_ACCOUNT": "_zentao_account",
    "ZEN_PASSWORD": "_zentao_password",
    "DCE_ZENTAO_PASSWORD": "_zentao_password",
    "GITLAB_TOKEN": "DCE_GITLAB_TOKEN",
    "PORTAINER_API_KEY": "DCE_PORTAINER_TOKEN",
}


def credential_environment(path: Path) -> tuple[dict[str, str], str | None, SecretStr | None]:
    """Only callers explicitly given this credential path may read it; no values are reported."""
    try:
        flags = (
            os.O_RDONLY
            | getattr(os, "O_NOFOLLOW", 0)
            | getattr(os, "O_CLOEXEC", 0)
            | getattr(os, "O_NONBLOCK", 0)
        )
        descriptor = os.open(path, flags)
        with os.fdopen(descriptor, "rb") as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077:
                raise DceError(ErrorCode.PERMISSION_DENIED, "Credential file must be private.")
            payload = stream.read(65537)
        if len(payload) > 65536:
            raise ValueError("size")
        values: dict[str, str] = {}
        seen: set[str] = set()
        # parse_stream is literal parsing: no environment interpolation and no shell execution.
        for binding in parse_stream(io.StringIO(payload.decode("utf-8"))):
            if binding.error:
                raise ValueError("format")
            if binding.key is None:
                continue
            if binding.key in seen:
                raise ValueError("duplicate")
            seen.add(binding.key)
            target = ALIASES.get(binding.key, binding.key)
            if target not in KNOWN_ENV | {"_zentao_account", "_zentao_password"}:
                continue
            value = binding.value or ""
            if target in values and values[target] != value:
                raise ValueError("conflict")
            values[target] = value
        account, password = (
            values.pop("_zentao_account", None),
            values.pop("_zentao_password", None),
        )
        if (
            (account is None) != (password is None)
            or account is not None
            and (not account.strip() or password == "")
        ):
            raise DceError(
                ErrorCode.AUTH_FAILED, "ZenTao account and password are required together."
            )
        return values, account, SecretStr(password) if password is not None else None
    except DceError:
        raise
    except (OSError, ValueError, UnicodeError):
        raise DceError(ErrorCode.INVALID_PAYLOAD, "Local credential input is invalid.") from None


def local_settings(
    config: Path,
    credentials: Path,
    *,
    live: bool = False,
    read_only: bool = False,
    environment: Mapping[str, str] | None = None,
    zentao_transport: httpx.BaseTransport | None = None,
) -> Settings:
    if not live or not read_only:
        raise DceError(ErrorCode.PERMISSION_DENIED, "Local credentials require live --read-only.")
    values, account, password = credential_environment(credentials)
    env = dict(values)
    env.update(
        {
            k: v
            for k, v in (os.environ if environment is None else environment).items()
            if k in KNOWN_ENV
        }
    )
    env["DCE_AI_ENABLED"] = "false"
    try:
        if config.suffix != ".toml":
            raise ValueError("non-secret TOML required")
        data = tomllib.loads(config.read_text())
    except (OSError, ValueError):
        raise DceError(
            ErrorCode.INVALID_PAYLOAD, "Invalid non-secret connection configuration."
        ) from None
    active = {name for name in PLATFORMS if data.get(name) or env.get(f"DCE_{name.upper()}_URL")}
    if not active:
        raise DceError(ErrorCode.AUTH_FAILED, "Platform addresses are missing.")
    for name in set(PLATFORMS) - active:
        for suffix in ("TOKEN", "INSTANCE_ID"):
            env.pop(f"DCE_{name.upper()}_{suffix}", None)
    login = "zentao" in active and account is not None and password is not None
    if login:
        env["DCE_ZENTAO_TOKEN"] = "authentication-only-placeholder"
    settings = load_settings(config, environ=env)
    if login:
        with Reader(settings.platform("zentao"), settings, transport=zentao_transport) as reader:
            assert account is not None and password is not None
            reader.log_filter.secrets += (account, password.get_secret_value())
            token = ZenTao(reader).create_token(account, password)
        assert settings.zentao is not None
        settings.zentao = settings.zentao.model_copy(update={"token": token})
    return settings
