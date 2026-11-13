"""Fail-closed log projection: arbitrary message text never reaches the Agent.

Regex redaction alone cannot reliably remove arbitrary PII, credentials or payloads.
Only fixed vocabulary and anonymous correlation digests leave this boundary.
"""

import hmac
import re
import secrets

_CORRELATION_KEY = secrets.token_bytes(32)

_SIGNALS = {
    "callback": r"\bcallback\b|回调",
    "review": r"\breview\b|\baudit\b|审核",
    "template": r"\btemplate\b|模板",
    "advertisement": r"\badvertisement\b|广告",
    "failed": r"\bfail(?:ed|ure)?\b|失败",
    "succeeded": r"\bsuccess(?:ful)?\b|\bsucceeded\b|成功",
    "timeout": r"\btime[ -]?out\b|超时",
    "rejected": r"\breject(?:ed)?\b|拒绝",
    "approved": r"\bapprov(?:e|ed|al)\b|通过",
}
_ERRORS = (
    "TimeoutException",
    "SocketTimeoutException",
    "ConnectException",
    "IOException",
    "NullPointerException",
    "IllegalArgumentException",
    "IllegalStateException",
    "SQLException",
    "ConnectionError",
    "TimeoutError",
    "ValueError",
    "KeyError",
)
_CORRELATION = re.compile(
    r'\b(trace[_-]?id|request[_-]?id|event[_-]?id|correlation[_-]?id)["\s]*[:=]\s*["\']?'
    r"([A-Za-z0-9_-]{8,128})\b",
    re.I,
)


def summarize(message: str) -> dict[str, object]:
    signals = [name for name, pattern in _SIGNALS.items() if re.search(pattern, message, re.I)]
    errors = [e for e in _ERRORS if re.search(r"\b" + e + r"\b", message)]
    level = re.search(r"\b(TRACE|DEBUG|INFO|WARN|WARNING|ERROR|FATAL)\b", message, re.I)
    status = re.search(
        r'\b(?:http[_ -]?status|status[_ -]?code)["\s]*[:=]\s*["\']?([1-5]\d\d)\b', message, re.I
    )
    correlations = sorted(
        {
            hmac.digest(_CORRELATION_KEY, m[2].encode(), "sha256").hex()[:24]
            for m in _CORRELATION.finditer(message)
        }
    )[:4]
    return {
        "level": level[1].upper() if level else "UNKNOWN",
        "signals": signals,
        "error_types": errors,
        "http_status": int(status[1]) if status else None,
        "correlation_hashes": correlations,
        "summary": "; ".join(signals + errors) or "unclassified log entry",
        "free_text": "omitted",
    }
