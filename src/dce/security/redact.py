import logging
import re
from collections.abc import Mapping
from typing import Any

_SENSITIVE = re.compile(
    r"token|password|secret|authorization|cookie|authentication|credential|private.key|api.key",
    re.I,
)
_URL = re.compile(r"\b(?:https?|ssh)://[^\s<>\"']+", re.I)
_ASSIGNMENT = re.compile(
    r"(?i)\b([\w-]*(?:token|password|secret|authorization|cookie|api.key)[\w-]*)"
    r"\s*[:=]\s*(?:\"[^\"]*\"|'[^']*'|[^\s,;]+)"
)
_IP = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_PRIVATE_HOST = re.compile(r"\b(?:[a-z0-9-]+\.)+(?:internal|local|corp|lan)\b", re.I)


def redact(value: Any, secrets: tuple[str, ...] = ()) -> Any:
    if isinstance(value, Mapping):
        return {
            str(k): "[REDACTED]" if _SENSITIVE.search(str(k)) else redact(v, secrets)
            for k, v in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [redact(item, secrets) for item in value]
    if isinstance(value, str):
        for secret in sorted((s for s in secrets if s), key=len, reverse=True):
            value = value.replace(secret, "[REDACTED]")
        value = _URL.sub("[URL]", value)
        value = _IP.sub("[ADDRESS]", value)
        value = _PRIVATE_HOST.sub("[HOST]", value)
        return _ASSIGNMENT.sub(r"\1=[REDACTED]", value)
    return value


class RedactingFilter(logging.Filter):
    def __init__(self, secrets: tuple[str, ...] = ()) -> None:
        super().__init__()
        self.secrets = secrets
        self.opaque = False

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = (
            "Platform HTTP diagnostic omitted."
            if self.opaque
            else redact(record.getMessage(), self.secrets)
        )
        record.args = ()
        # Raw traceback exception text may contain credential-bearing HTTP URLs.
        record.exc_info = None
        record.exc_text = None
        record.stack_info = None
        return True
