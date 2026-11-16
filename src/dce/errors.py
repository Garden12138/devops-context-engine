from enum import StrEnum


class ErrorCode(StrEnum):
    NOT_IMPLEMENTED = "NOT_IMPLEMENTED"  # Removed when M5 implements the final command.
    WORKSPACE_REQUIRED = "WORKSPACE_REQUIRED"
    WORKSPACE_MISMATCH = "WORKSPACE_MISMATCH"
    CONFIG_MISSING = "CONFIG_MISSING"
    CONFIG_INVALID = "CONFIG_INVALID"
    CREDENTIALS_INVALID = "CREDENTIALS_INVALID"
    AUTH_FAILED = "AUTH_FAILED"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"
    NOT_FOUND = "NOT_FOUND"
    PLATFORM_UNAVAILABLE = "PLATFORM_UNAVAILABLE"
    PLATFORM_ERROR = "PLATFORM_ERROR"
    PRECONDITION_FAILED = "PRECONDITION_FAILED"
    GIT_DIRTY = "GIT_DIRTY"
    GIT_CONFLICT = "GIT_CONFLICT"
    GIT_PUSH_REJECTED = "GIT_PUSH_REJECTED"
    GIT_ERROR = "GIT_ERROR"
    CI_JOB_MISSING = "CI_JOB_MISSING"
    CI_FAILED = "CI_FAILED"
    DEPLOY_FAILED = "DEPLOY_FAILED"
    TIMEOUT = "TIMEOUT"
    INTERNAL = "INTERNAL"


class DceError(Exception):
    def __init__(
        self,
        code: ErrorCode,
        message: str,
        hint: str | None = None,
        retryable: bool = False,
    ) -> None:
        self.code = code
        self.message = message
        self.hint = hint
        self.retryable = retryable
        super().__init__(message)

    def as_dict(self) -> dict[str, object]:
        return {
            "code": self.code.value,
            "message": self.message,
            "hint": self.hint,
            "retryable": self.retryable,
        }
