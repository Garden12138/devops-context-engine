import io
import os
import stat
import tomllib
from collections.abc import Mapping
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import urlsplit

import httpx
from dotenv.parser import parse_stream
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PrivateAttr,
    SecretStr,
    ValidationError,
    field_validator,
)

from dce.errors import DceError, ErrorCode

if TYPE_CHECKING:
    from dce.platforms.zentao_auth import ZenTaoTokenManager


class PlatformConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    instance_id: str = Field(min_length=1, max_length=100)
    base_url: str
    token: SecretStr

    @field_validator("token")
    @classmethod
    def nonempty_token(cls, value: SecretStr) -> SecretStr:
        if not value.get_secret_value().strip():
            raise ValueError("credential required")
        return value

    @field_validator("base_url")
    @classmethod
    def valid_url(cls, value: str) -> str:
        parsed = urlsplit(value)
        if (
            parsed.scheme not in {"https", "http"}
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("invalid platform address")
        return value.rstrip("/")


class Settings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    _zentao_tokens: "ZenTaoTokenManager | None" = PrivateAttr(default=None)
    _zentao_account: str | None = PrivateAttr(default=None)
    allow_http: bool = False
    timeout: float = Field(default=10, gt=0, le=120)
    max_retries: int = Field(default=2, ge=0, le=5)
    request_interval: float = Field(default=0.01, ge=0, le=5)
    page_size: int = Field(default=100, ge=1, le=100)
    output_budget: int = Field(default=24000, ge=1024, le=64000)
    zentao: PlatformConfig | None = None
    gitlab: PlatformConfig | None = None
    portainer: PlatformConfig | None = None

    def secrets(self) -> tuple[str, ...]:
        return tuple(
            c.token.get_secret_value()
            for c in (
                self.gitlab,
                self.zentao,
                self.portainer,
            )
            if c
        ) + (self._zentao_tokens.secrets() if self._zentao_tokens else ())

    def platform(self, name: str) -> PlatformConfig:
        config: PlatformConfig | None = getattr(self, name, None)
        if config is None:
            raise DceError(ErrorCode.CREDENTIALS_INVALID, f"{name}: 缺少平台连接或凭证配置。")
        if config.base_url.startswith("http:") and not self.allow_http:
            raise DceError(
                ErrorCode.CONFIG_INVALID,
                f"{name}.base_url 使用 HTTP，请在 connections.toml 加 allow_http = true。",
            )
        return config


def load_settings(
    connections: Path | None = None,
    credentials: Path | None = None,
    *, environ: Mapping[str, str] | None = None, **overrides: Any
) -> Settings:
    """CLI overrides > process environment > explicit non-secret TOML; no dotenv."""
    if credentials is not None:
        return local_settings(
            connections or Path.home() / '.config/dce/connections.toml', credentials,
            live=True, read_only=True, environment=environ,
        )
    environment = os.environ if environ is None else environ
    try:
        data: dict[str, Any] = {}
        if connections is not None:
            data = tomllib.loads(connections.read_text())
            for name, entry in data.items():
                if name == 'token' or isinstance(entry, dict) and 'token' in entry:
                    raise DceError(
                        ErrorCode.CONFIG_INVALID,
                        f"connections.toml {name}: 凭证只能放在凭证文件。",
                    )
        for name in Settings.model_fields:
            if name in {"zentao", "gitlab", "portainer"}:
                platform = dict(data.get(name, {}))
                for field, suffix in (
                    ("base_url", "URL"),
                    ("token", "TOKEN"),
                    ("instance_id", "INSTANCE_ID"),
                ):
                    key = f"DCE_{name.upper()}_{suffix}"
                    if key in environment:
                        platform[field] = environment[key]
                if platform:
                    source = f'DCE_{name.upper()}_URL'
                    alias = next((k for k, v in ALIASES.items() if v == source), source)
                    address = urlsplit(str(platform.get('base_url', '')))
                    if (address.scheme not in {'http', 'https'} or not address.hostname
                            or address.username or address.password or address.query
                            or address.fragment):
                        raise DceError(
                            ErrorCode.CONFIG_INVALID,
                            f'{name}.base_url（{alias} / {source}）: URL 无效或含用户名密码。',
                            '填写仅含协议、主机和平台路径的 URL。',
                        )
                    if not platform.get('token'):
                        label = {
                            'gitlab': '缺少 GitLab 令牌（GITLAB_TOKEN 或 DCE_GITLAB_TOKEN）',
                            'portainer': ('缺少 Portainer 令牌'
                                          '（PORTAINER_API_KEY 或 DCE_PORTAINER_TOKEN）'),
                            'zentao': '缺少禅道凭证（ZEN_USER 与 ZEN_PASSWORD）',
                        }[name]
                        raise DceError(ErrorCode.CREDENTIALS_INVALID, label)
                    platform.setdefault("instance_id", name)
                    data[name] = platform
            elif f"DCE_{name.upper()}" in environment:
                data[name] = environment[f"DCE_{name.upper()}"]
        data.update({key: value for key, value in overrides.items() if value is not None})
        settings = Settings.model_validate(data)
        for name in PLATFORMS:
            if getattr(settings, name) is not None:
                settings.platform(name)
        return settings
    except ValidationError as exc:
        fields = ', '.join('.'.join(map(str, e['loc'])) for e in exc.errors())
        raise DceError(
            ErrorCode.CONFIG_INVALID, f'connections.toml {fields}: 配置类型或取值无效。',
            '按 docs/v2/03 第 3.1 节修改对应字段。',
        ) from None
    except (OSError, ValueError) as exc:
        raise DceError(
            ErrorCode.CONFIG_INVALID,
            f'connections.toml: {type(exc).__name__}，无法读取或解析连接配置。',
            '检查文件路径、读取权限与 TOML 语法。',
        ) from None


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
            if not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode) != 0o600:
                raise DceError(
                    ErrorCode.CREDENTIALS_INVALID, "凭证文件必须为普通文件，权限必须为 0600。",
                    '对凭证文件执行 chmod 600。',
                )
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
    except (OSError, ValueError, UnicodeError) as exc:
        reason = {
            'size': '超过 64KB', 'format': '字面格式无效',
            'duplicate': '重复键', 'conflict': '别名冲突',
        }.get(str(exc), '读取失败或编码无效')
        raise DceError(
            ErrorCode.CREDENTIALS_INVALID,
            f"凭证文件: {type(exc).__name__}（{reason}）。",
            '检查文件路径、符号链接、大小上限、字面格式、重复键和别名冲突。',
        ) from None


def local_settings(
    config: Path,
    credentials: Path,
    *,
    live: bool = False,
    read_only: bool = False,
    environment: Mapping[str, str] | None = None,
    zentao_transport: httpx.BaseTransport | None = None,
) -> Settings:
    from dce.platforms.http import PlatformClient
    from dce.platforms.zentao import ZenTao
    from dce.platforms.zentao_auth import ZenTaoTokenManager

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
    try:
        if config.suffix != ".toml":
            raise ValueError("non-secret TOML required")
        data = tomllib.loads(config.read_text())
    except (OSError, ValueError):
        raise DceError(
            ErrorCode.CONFIG_INVALID, "Invalid non-secret connection configuration."
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
    settings._zentao_account = account
    if login:
        connection = settings.platform("zentao")
        assert account is not None and password is not None

        def authenticate() -> SecretStr:
            with PlatformClient(connection, settings, transport=zentao_transport) as reader:
                reader.log_filter.secrets += (account, password.get_secret_value())
                return ZenTao(reader).create_token(account, password)

        settings._zentao_tokens = ZenTaoTokenManager(connection, account, password, authenticate)
    return settings
