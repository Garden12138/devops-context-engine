"""Bounded Docker service log transport and stdcopy decoding. No disk or retries."""

import asyncio
import hmac
import re
import secrets
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Annotated
from urllib.parse import unquote_plus

import httpx
from pydantic import BaseModel, ConfigDict, Field

from dce.errors import DceError, ErrorCode
from dce.platforms.http import AUTH_HEADERS, PlatformClient

TIME_PATTERN = r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{1,9})?(?:Z|[+-]\d\d:\d\d)$"
LogTime = Annotated[str, Field(max_length=35, pattern=TIME_PATTERN)]
Keyword = Annotated[str, Field(min_length=1, max_length=64, pattern=r"^[^\x00-\x1f\x7f]+$")]


def timestamp_ns(value: str) -> int:
    if not re.fullmatch(TIME_PATTERN, value):
        raise ValueError("RFC3339 timestamp with timezone required")
    match = re.fullmatch(r"(.*?)(?:\.(\d{1,9}))?(Z|[+-]\d\d:\d\d)", value)
    assert match is not None
    try:
        dt = datetime.fromisoformat(match[1] + match[3]).astimezone(UTC)
    except (ValueError, OverflowError):
        raise ValueError("invalid RFC3339 timestamp") from None
    seconds = (dt - datetime(1970, 1, 1, tzinfo=UTC)).days * 86400
    seconds += dt.hour * 3600 + dt.minute * 60 + dt.second
    return seconds * 1_000_000_000 + int((match[2] or "").ljust(9, "0"))


class LogControls(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    start_time: LogTime | None = Field(default=None, description="Inclusive RFC3339 with timezone.")
    end_time: LogTime | None = Field(
        default=None, description="Exclusive RFC3339; window <=15 min."
    )
    keywords: list[Keyword] = Field(
        default_factory=list, max_length=8, description="Literal case-insensitive OR; never echoed."
    )
    max_lines: int = Field(
        default=100, ge=1, le=500, description="Finite server tail and event cap."
    )
    max_bytes: int = Field(
        default=65536, ge=1024, le=262144, description="Raw log payload byte cap."
    )
    max_output_bytes: int = Field(
        default=8192,
        ge=4096,
        le=16384,
        description="Complete MCP result cap, including both copies.",
    )
    timeout_seconds: float = Field(
        default=10, gt=0, le=15, description="Total log HTTP deadline; no retry or follow."
    )

    def bounds(self) -> tuple[int, int]:
        if self.start_time is None or self.end_time is None:
            raise ValueError("explicit start and end required")
        start, end = timestamp_ns(self.start_time), timestamp_ns(self.end_time)
        if start < 0 or not 0 < end - start <= 900_000_000_000:
            raise ValueError("invalid log time window")
        if any(not k.strip() for k in self.keywords):
            raise ValueError("empty keyword")
        return start, end


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


def log_error(body: bytes, default: ErrorCode) -> ErrorCode:
    # Error bodies are classified in bounded memory and are never returned or logged.
    text = body[:4096].lower()
    if b"logging driver" in text and any(w in text for w in (b"not support", b"unsupported")):
        return ErrorCode.PLATFORM_ERROR
    if b"logs have expired" in text or b"logs expired" in text:
        return ErrorCode.PLATFORM_ERROR
    return default


@dataclass
class LogRead:
    content: bytes = b""
    error: ErrorCode | None = None
    expired: bool = False
    reasons: list[str] = field(default_factory=list)


async def raw_chunks(response: httpx.Response) -> AsyncIterator[bytes]:
    # In-memory transports may supply a buffered response. Compression is rejected first.
    if response.is_stream_consumed:
        yield response.content
    else:
        async for chunk in response.aiter_raw():
            yield chunk


async def read_logs(
    reader: PlatformClient, path: str, params: dict[str, str], c: LogControls
) -> LogRead:
    result = LogRead()
    transport = reader.transport
    if transport is not None and not isinstance(transport, httpx.AsyncBaseTransport):
        raise DceError(ErrorCode.PLATFORM_ERROR, "Async log transport is unavailable.")
    buffer = bytearray()
    try:
        # wait_for-style cancellation closes the HTTP response, including a stalled/trickling body.
        async with asyncio.timeout(c.timeout_seconds):
            async with httpx.AsyncClient(
                transport=transport,
                timeout=min(c.timeout_seconds, reader.settings.timeout),
                follow_redirects=False,
                trust_env=False,
            ) as client:
                async with client.stream(
                    "GET",
                    reader.safe_url(path),
                    params=params,
                    headers={
                        AUTH_HEADERS["portainer"]: reader.config.token.get_secret_value(),
                        "Accept-Encoding": "identity",
                    },
                ) as response:
                    status = response.status_code
                    if 300 <= status < 400:
                        result.error = ErrorCode.OUT_OF_SCOPE
                        return result
                    if status in {401, 403, 404, 429}:
                        result.error = {
                            401: ErrorCode.AUTH_FAILED,
                            403: ErrorCode.PERMISSION_DENIED,
                            404: ErrorCode.NOT_FOUND,
                            429: ErrorCode.PLATFORM_UNAVAILABLE,
                        }[status]
                        return result
                    if response.headers.get("Content-Encoding", "identity").lower() != "identity":
                        result.error = ErrorCode.PLATFORM_ERROR
                        return result
                    cap = min(c.max_bytes, 4096) if status >= 400 else c.max_bytes
                    async for chunk in raw_chunks(response):
                        buffer.extend(chunk[: cap - len(buffer)])
                        if len(buffer) >= cap:
                            result.reasons.append("RAW_BYTE_LIMIT")
                            break
                    if status >= 400:
                        result.expired = any(
                            phrase in bytes(buffer).lower()
                            for phrase in (b"logs have expired", b"logs expired")
                        )
                        result.error = log_error(
                            bytes(buffer),
                            ErrorCode.PLATFORM_ERROR
                            if status in {400, 422, 501}
                            else ErrorCode.PLATFORM_ERROR,
                        )
                        buffer.clear()
    except (TimeoutError, httpx.TimeoutException):
        result.error = ErrorCode.TIMEOUT
        result.reasons.append("HTTP_DEADLINE")
    except (httpx.RequestError, OSError):
        result.error = ErrorCode.PLATFORM_UNAVAILABLE
        result.reasons.append("STREAM_INTERRUPTED")
    result.content = bytes(buffer)
    return result


class DockerLogDecoder:
    def __init__(self, *, tty: bool, cap: int) -> None:
        self.tty, self.cap = tty, cap
        self.buffer = bytearray()
        self.lines: dict[str, bytearray] = {}
        self.entries: list[tuple[str, bytes]] = []
        self.error: ErrorCode | None = None
        self.expired = False

    def payload(self, stream: str, payload: bytes) -> None:
        pending = self.lines.setdefault(stream, bytearray())
        # A task may omit its final newline. Preserve the next frame's task context
        # rather than concatenating two timestamped Docker messages into one entry.
        prefix = payload.split(b" ", 2)
        if (
            pending
            and len(prefix) == 3
            and re.fullmatch(TIME_PATTERN.encode(), prefix[0])
            and b"com.docker.swarm.task.id=" in prefix[1]
        ):
            self.entries.append((stream, bytes(pending)))
            pending.clear()
        pending.extend(payload)
        while b"\n" in pending:
            line, _, rest = pending.partition(b"\n")
            self.entries.append((stream, bytes(line)))
            pending[:] = rest
            if len(self.entries) > 10000:
                raise DceError(ErrorCode.PLATFORM_ERROR, "Log line scan limit exceeded.")

    def feed(self, data: bytes) -> None:
        if self.tty:
            self.payload("combined", data)
            return
        self.buffer.extend(data)
        while len(self.buffer) >= 8:
            stream = self.buffer[0]
            length = int.from_bytes(self.buffer[4:8], "big")
            if stream not in {1, 2, 3} or self.buffer[1:4] != b"\0\0\0":
                raise DceError(ErrorCode.PLATFORM_ERROR, "Invalid Docker frame header.")
            if length > self.cap:
                # Never allocate the advertised size. finish distinguishes EOF corruption
                # from a legitimate large frame stopped by the raw payload cap.
                return
            if len(self.buffer) < 8 + length:
                return
            payload = bytes(self.buffer[8 : 8 + length])
            del self.buffer[: 8 + length]
            if stream == 3:
                self.expired = any(
                    phrase in payload.lower() for phrase in (b"logs have expired", b"logs expired")
                )
                self.error = log_error(payload, ErrorCode.PLATFORM_UNAVAILABLE)
                return
            self.payload("stdout" if stream == 1 else "stderr", payload)

    def finish(self, *, partial: bool) -> list[tuple[str, bytes]]:
        if self.buffer and not partial and self.error is None:
            raise DceError(ErrorCode.PLATFORM_ERROR, "Incomplete Docker frame.")
        for stream, pending in self.lines.items():
            if pending and not partial:
                self.entries.append((stream, bytes(pending)))
        return self.entries


def project_logs(raw: LogRead, c: LogControls, *, tty: bool, service_id: str) -> dict[str, object]:
    start, end = c.bounds()
    decoder = DockerLogDecoder(tty=tty, cap=c.max_bytes)
    reasons = list(raw.reasons)
    error = raw.error
    events: list[dict[str, object]] = []
    in_window = 0
    try:
        decoder.feed(raw.content)
        error = error or decoder.error
        entries = decoder.finish(partial=bool(reasons or error))
        for stream, line in entries:
            try:
                text = line.decode("utf-8", errors="strict")
                timestamp, details, message = text.split(" ", 2)
                instant = timestamp_ns(timestamp)
                pairs = [unquote_plus(pair).split("=", 1) for pair in details.split(",")]
                attrs = dict(pairs)
                if len(attrs) != len(pairs):
                    raise ValueError
                task = attrs["com.docker.swarm.task.id"]
                if attrs["com.docker.swarm.service.id"] != service_id or not re.fullmatch(
                    r"[a-z0-9]{1,64}", task
                ):
                    raise ValueError
            except (ValueError, KeyError, UnicodeError):
                raise DceError(
                    ErrorCode.PLATFORM_ERROR, "Invalid timestamp or task context."
                ) from None
            if not start <= instant < end:
                continue
            in_window += 1
            if c.keywords and not any(k.casefold() in message.casefold() for k in c.keywords):
                continue
            if len(events) >= c.max_lines:
                reasons.append("EVENT_LINE_LIMIT")
                break
            events.append(
                {"timestamp": timestamp, "stream": stream, "task_id": task, **summarize(message)}
            )
        # Docker tail is per task; total >= tail is a conservative incompleteness test.
        if len(entries) >= c.max_lines:
            reasons.append("SERVER_TAIL_LIMIT_POSSIBLE")
    except DceError as exc:
        error = error or exc.code
        events = []  # No unverifiable prefix is presented as an observation.
    return {
        "events": events,
        "scanned_lines": len(decoder.entries),
        "in_window_lines": in_window,
        "bytes_read": len(raw.content),
        "truncated": bool(reasons or error),
        "truncation_reasons": sorted(set(reasons)),
        "error_type": error.value if error else None,
        "outcome": "error"
        if error
        else "truncated"
        if reasons
        else "matched"
        if events
        else "no_match_in_retained_logs"
        if in_window
        else "empty_retention_unknown",
        "retention": "expired" if raw.expired or decoder.expired else "not_verified",
        "summary": {
            "returned_events": len(events),
            "free_text": "omitted",
            "content_trust": "untrusted_data",
            "client_filters": ["end_time", "keywords"],
            "completeness": "not_verified",
        },
    }
