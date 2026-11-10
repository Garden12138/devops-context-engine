"""Private, exact-service, expiring single-use grants. No credentials or remote I/O."""

import hashlib
import json
import os
import stat
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from dce.common.errors import DceError, ErrorCode
from dce.common.service_logs import LogControls, LogTime, timestamp_ns


def refuse() -> None:
    raise DceError(
        ErrorCode.PERMISSION_DENIED, "Temporary log grant is unavailable or out of scope."
    )


class GrantSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    version: Literal[1]
    grant_id: str = Field(pattern=r"^[a-f0-9]{32}$")
    source_instance: str = Field(min_length=1, max_length=100)
    endpoint_id: str = Field(pattern=r"^[0-9]+$")
    stack_id: str = Field(pattern=r"^[0-9]+$")
    stack_name: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,199}$")
    namespace: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,199}$")
    swarm_id: str = Field(pattern=r"^[a-z0-9]{1,64}$")
    service_id: str = Field(pattern=r"^[a-z0-9]{1,64}$")
    compose_service: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,199}$")
    service_name: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,399}$")
    issued_at: LogTime
    expires_at: LogTime
    max_uses: Literal[1] = 1
    follow: Literal[False] = False
    max_window_seconds: int = Field(default=300, gt=0, le=300)
    max_lines: int = Field(default=20, gt=0, le=20)
    max_bytes: int = Field(default=16384, ge=1024, le=65536)
    max_output_bytes: int = Field(default=8192, ge=4096, le=8192)
    timeout_seconds: float = Field(default=10, gt=0, le=10)

    @model_validator(mode="after")
    def consistent(self) -> "GrantSpec":
        if self.service_name != self.namespace + "_" + self.compose_service:
            raise ValueError("exact service identity required")
        ttl = timestamp_ns(self.expires_at) - timestamp_ns(self.issued_at)
        if not 0 < ttl <= 3600 * 10**9:
            raise ValueError("temporary grant lifetime exceeds one hour")
        return self


def _unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate grant key")
        result[key] = value
    return result


def _private_read(path: Path) -> bytes:
    try:
        parent = path.parent.stat()
        if (
            path.parent.is_symlink()
            or not stat.S_ISDIR(parent.st_mode)
            or parent.st_mode & 0o077
            or parent.st_uid != os.geteuid()
        ):
            refuse()
        fd = os.open(
            path,
            os.O_RDONLY
            | getattr(os, "O_NOFOLLOW", 0)
            | getattr(os, "O_CLOEXEC", 0)
            | getattr(os, "O_NONBLOCK", 0),
        )
        with os.fdopen(fd, "rb") as stream:
            info = os.fstat(stream.fileno())
            if (
                not stat.S_ISREG(info.st_mode)
                or info.st_mode & 0o077
                or info.st_uid != os.geteuid()
            ):
                refuse()
            data = stream.read(8193)
        if len(data) > 8192:
            refuse()
        return data
    except OSError:
        refuse()
    raise AssertionError("unreachable")


class ServiceLogGrant:
    def __init__(self, path: Path, spec: GrantSpec, digest: bytes) -> None:
        self.path, self.spec, self.digest = path, spec, digest
        self.marker = path.with_name(f".log-grant-{spec.grant_id}.used")

    def __repr__(self) -> str:
        return "ServiceLogGrant(<private single-use policy>)"

    @classmethod
    def load(cls, path: Path) -> "ServiceLogGrant":
        if not path.is_absolute():
            raise DceError(ErrorCode.INVALID_PAYLOAD, "Log policy path must be absolute.")
        data = _private_read(path)
        try:
            spec = GrantSpec.model_validate(json.loads(data, object_pairs_hook=_unique))
        except (ValidationError, ValueError, UnicodeError):
            raise DceError(
                ErrorCode.INVALID_PAYLOAD, "Invalid private temporary log policy."
            ) from None
        return cls(path, spec, hashlib.sha256(data).digest())

    def used(self) -> bool:
        return os.path.lexists(self.marker)

    def _live(self) -> None:
        if hashlib.sha256(_private_read(self.path)).digest() != self.digest:
            refuse()
        now = time.time_ns()
        if (
            not timestamp_ns(self.spec.issued_at) <= now < timestamp_ns(self.spec.expires_at)
            or self.used()
        ):
            refuse()

    def available(self) -> bool:
        try:
            self._live()
            return True
        except DceError:
            return False

    def _limits(self, controls: LogControls) -> None:
        start, end = controls.bounds()
        now = time.time_ns()
        if end - start > self.spec.max_window_seconds * 10**9 or end > now:
            refuse()
        start = max(start, now - self.spec.max_window_seconds * 10**9)
        if start >= end:
            refuse()
        prefix = datetime.fromtimestamp(start // 10**9, UTC).strftime("%Y-%m-%dT%H:%M:%S")
        controls.start_time = prefix + f".{start % 10**9:09d}Z"
        controls.max_lines = min(controls.max_lines, self.spec.max_lines)
        controls.max_bytes = min(controls.max_bytes, self.spec.max_bytes)
        controls.max_output_bytes = min(controls.max_output_bytes, self.spec.max_output_bytes)
        controls.timeout_seconds = min(controls.timeout_seconds, self.spec.timeout_seconds)

    def authorize(
        self,
        instance: str,
        endpoint: str,
        stack: str,
        *,
        service_id: str | None,
        service_name: str | None,
        controls: LogControls,
    ) -> None:
        self._live()
        s = self.spec
        if (instance, endpoint, stack) != (s.source_instance, s.endpoint_id, s.stack_id):
            refuse()
        if bool(service_id) == bool(service_name):
            refuse()
        if service_id is not None and service_id != s.service_id:
            refuse()
        if service_name is not None and service_name != s.compose_service:
            refuse()
        self._limits(controls)

    def verify_identity(
        self, stack_name: object, namespace: str, swarm: str, service_id: str, service_name: str
    ) -> None:
        s = self.spec
        if (stack_name, namespace, swarm, service_id, service_name) != (
            s.stack_name,
            s.namespace,
            s.swarm_id,
            s.service_id,
            s.service_name,
        ):
            refuse()

    def consume(self, controls: LogControls) -> None:
        # Revalidate immediately before dispatch; a failed/cancelled attempt is never refunded.
        self._live()
        self._limits(controls)
        try:
            fd = os.open(
                self.marker,
                os.O_WRONLY
                | os.O_CREAT
                | os.O_EXCL
                | getattr(os, "O_NOFOLLOW", 0)
                | getattr(os, "O_CLOEXEC", 0),
                0o600,
            )
            with os.fdopen(fd, "w") as stream:
                json.dump(
                    {"grant_id": self.spec.grant_id, "consumed_at_ns": time.time_ns()}, stream
                )
                stream.flush()
                os.fsync(stream.fileno())
        except OSError:
            refuse()
