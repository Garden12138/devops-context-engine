from enum import StrEnum


class ErrorCode(StrEnum):
    AUTH_FAILED = "AUTH_FAILED"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    NOT_FOUND = "NOT_FOUND"
    API_INCOMPATIBLE = "API_INCOMPATIBLE"
    RATE_LIMITED = "RATE_LIMITED"
    NETWORK_UNAVAILABLE = "NETWORK_UNAVAILABLE"
    INVALID_PAYLOAD = "INVALID_PAYLOAD"
    UNSAFE_URL = "UNSAFE_URL"
    SNAPSHOT_CONFLICT = "SNAPSHOT_CONFLICT"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    LOG_DRIVER_UNSUPPORTED = "LOG_DRIVER_UNSUPPORTED"
    LOG_FILTER_UNSUPPORTED = "LOG_FILTER_UNSUPPORTED"
    LOGS_EXPIRED = "LOGS_EXPIRED"
    LOG_READ_TIMEOUT = "LOG_READ_TIMEOUT"
    LOG_READ_INTERRUPTED = "LOG_READ_INTERRUPTED"
    LOG_STREAM_INVALID = "LOG_STREAM_INVALID"


class DceError(Exception):
    """Messages are fixed diagnostics, never raw HTTP/validation exceptions."""

    def __init__(self, code: ErrorCode, message: str, *, retryable: bool = False) -> None:
        self.code = code
        self.message = message
        self.retryable = retryable
        super().__init__(message)

    def as_dict(self) -> dict[str, object]:
        return {
            "code": self.code.value,
            "error_code": self.code.value,
            "message": self.message,
            "retryable": self.retryable,
        }
