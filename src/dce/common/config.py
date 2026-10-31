import os
import tomllib
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, SecretStr, ValidationError, field_validator

from dce.common.errors import DceError, ErrorCode


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
    allow_http: bool = False
    ai_enabled: bool = False
    catalog_path: Path = Path(".local/catalog.sqlite3")
    timeout: float = Field(default=10, gt=0, le=120)
    max_retries: int = Field(default=2, ge=0, le=5)
    page_size: int = Field(default=100, ge=1, le=100)
    output_budget: int = Field(default=16000, ge=1024, le=64000)
    zentao: PlatformConfig | None = None
    gitlab: PlatformConfig | None = None
    portainer: PlatformConfig | None = None

    def platform(self, name: str) -> PlatformConfig:
        config: PlatformConfig | None = getattr(self, name, None)
        if config is None:
            raise DceError(ErrorCode.AUTH_FAILED, "Platform configuration is missing.")
        if config.base_url.startswith("http:") and not self.allow_http:
            raise DceError(ErrorCode.UNSAFE_URL, "HTTP requires explicit allow_http.")
        return config


def load_settings(path: Path | None = None, **overrides: Any) -> Settings:
    """CLI overrides > process environment > explicit non-secret TOML; no dotenv."""
    try:
        data: dict[str, Any] = {}
        if path is not None:
            data = tomllib.loads(path.read_text())
            if any("token" in entry for entry in data.values() if isinstance(entry, dict)):
                raise DceError(ErrorCode.INVALID_PAYLOAD, "Credentials must use environment input.")
        for name in Settings.model_fields:
            if name in {"zentao", "gitlab", "portainer"}:
                platform = dict(data.get(name, {}))
                for field, suffix in (
                    ("base_url", "URL"),
                    ("token", "TOKEN"),
                    ("instance_id", "INSTANCE_ID"),
                ):
                    key = f"DCE_{name.upper()}_{suffix}"
                    if key in os.environ:
                        platform[field] = os.environ[key]
                if platform:
                    platform.setdefault("instance_id", name)
                    data[name] = platform
            elif f"DCE_{name.upper()}" in os.environ:
                data[name] = os.environ[f"DCE_{name.upper()}"]
        data.update({key: value for key, value in overrides.items() if value is not None})
        return Settings.model_validate(data)
    except (OSError, ValueError, ValidationError):
        raise DceError(ErrorCode.INVALID_PAYLOAD, "Invalid DCE configuration.") from None
