"""Process-local v1 session recovery. No scope decisions, disk cache or password retries."""

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from threading import RLock
from typing import TYPE_CHECKING, Any

import httpx
from pydantic import SecretStr

from dce.common.errors import DceError, ErrorCode

if TYPE_CHECKING:
    from dce.common.config import PlatformConfig


class AuthReason(StrEnum):
    AUTH_EXPIRED = "AUTH_EXPIRED"
    AUTH_FAILED = "AUTH_FAILED"
    AUTH_REFRESH_FAILED = "AUTH_REFRESH_FAILED"


@dataclass(frozen=True, repr=False)
class TokenLease:
    token: SecretStr
    generation: int


class ZenTaoTokenManager:
    def __init__(
        self,
        config: "PlatformConfig",
        account: str,
        password: SecretStr,
        login: Callable[[], SecretStr],
    ) -> None:
        self._config = config
        self._identity = (config.instance_id, config.base_url)
        self._account, self._password = SecretStr(account), password
        self._login = login
        self._lock = RLock()
        self._current: TokenLease | None = None
        self._failure: tuple[ErrorCode, str] | None = None
        self._generation = 0

    def __repr__(self) -> str:
        return "ZenTaoTokenManager(<private process state>)"

    def __deepcopy__(self, memo: dict[int, Any]) -> "ZenTaoTokenManager":
        # Copies of the same connection must share the single flight, never copy a lock.
        return self

    def require_connection(self, config: "PlatformConfig") -> None:
        if (config.instance_id, config.base_url) != self._identity:
            raise DceError(ErrorCode.PERMISSION_DENIED, "Authentication connection changed.")

    def secrets(self) -> tuple[str, ...]:
        with self._lock:
            return (self._account.get_secret_value(), self._password.get_secret_value()) + (
                (self._current.token.get_secret_value(),) if self._current else ()
            )

    def lease(self, *, failed_generation: int | None = None) -> TokenLease:
        with self._lock:
            if self._failure:
                raise DceError(*self._failure)
            if self._current is not None and (
                failed_generation is None or failed_generation != self._current.generation
            ):
                return self._current
            refreshing = self._current is not None
            try:
                token = self._login()
                if not isinstance(token, SecretStr) or not token.get_secret_value().strip():
                    raise DceError(ErrorCode.AUTH_FAILED, "Invalid authentication response.")
            except DceError as exc:
                reason = AuthReason.AUTH_REFRESH_FAILED if refreshing else AuthReason.AUTH_FAILED
                code = (
                    exc.code
                    if exc.code
                    in {
                        ErrorCode.NETWORK_UNAVAILABLE,
                        ErrorCode.UNSAFE_URL,
                    }
                    else ErrorCode.AUTH_FAILED
                )
                if not refreshing and code == ErrorCode.NETWORK_UNAVAILABLE:
                    reason_text = "NETWORK_UNAVAILABLE"
                else:
                    reason_text = reason.value
                self._failure = (
                    code,
                    f"{reason_text}: ZenTao login failed; check settings and restart.",
                )
                raise DceError(*self._failure) from None
            self._generation += 1
            self._current = TokenLease(token, self._generation)
            self._config.token = token
            return self._current

    def reject(self, generation: int) -> None:
        with self._lock:
            if self._current is not None and self._current.generation == generation:
                self._failure = (
                    ErrorCode.AUTH_FAILED,
                    "AUTH_EXPIRED: Renewed ZenTao session rejected; check settings and restart.",
                )


def auth_expired(response: httpx.Response) -> bool:
    """Exact allowlist, not substring search of arbitrary upstream resource text/HTML."""
    if response.status_code not in {401, 403}:
        return False
    try:
        data = response.json()
    except ValueError:
        return False
    if not isinstance(data, dict):
        return False
    # Official v1: HTTP401 {"error":"Unauthorized"}. No expiry metadata is provided.
    if response.status_code == 401 and data.get("error") == "Unauthorized":
        return True
    codes = {"TOKEN_EXPIRED", "INVALID_TOKEN", "AUTH_EXPIRED"}
    messages = {"Token expired", "Token has expired", "Invalid token", "Token is invalid"}
    return (isinstance(data.get("error"), str) and data["error"] in codes | messages) or (
        isinstance(data.get("code"), str) and data["code"] in codes
    )


def response_error(response: httpx.Response) -> DceError | None:
    if auth_expired(response):
        return DceError(
            ErrorCode.AUTH_FAILED, "AUTH_EXPIRED: ZenTao session is invalid or expired."
        )
    if response.status_code >= 400:
        code = {
            401: ErrorCode.AUTH_FAILED,
            403: ErrorCode.PERMISSION_DENIED,
            404: ErrorCode.NOT_FOUND,
            429: ErrorCode.RATE_LIMITED,
        }.get(response.status_code, ErrorCode.API_INCOMPATIBLE)
        return DceError(
            code,
            "ZenTao API request failed.",
            retryable=response.status_code in {429, 502, 503, 504},
        )
    return None
