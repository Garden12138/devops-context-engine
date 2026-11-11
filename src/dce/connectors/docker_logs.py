"""Bounded Docker service log transport and stdcopy decoding. No disk or retries."""

import asyncio
import re
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from urllib.parse import unquote_plus

import httpx

from dce.common.errors import DceError, ErrorCode
from dce.common.service_logs import TIME_PATTERN, LogControls, timestamp_ns
from dce.connectors.http import AUTH_HEADERS, Reader
from dce.security.log_summary import summarize


def log_error(body: bytes, default: ErrorCode) -> ErrorCode:
    # Error bodies are classified in bounded memory and are never returned or logged.
    text = body[:4096].lower()
    if b"logging driver" in text and any(w in text for w in (b"not support", b"unsupported")):
        return ErrorCode.LOG_DRIVER_UNSUPPORTED
    if b"logs have expired" in text or b"logs expired" in text:
        return ErrorCode.LOGS_EXPIRED
    return default


@dataclass
class LogRead:
    content: bytes = b""
    error: ErrorCode | None = None
    reasons: list[str] = field(default_factory=list)


async def raw_chunks(response: httpx.Response) -> AsyncIterator[bytes]:
    # In-memory transports may supply a buffered response. Compression is rejected first.
    if response.is_stream_consumed:
        yield response.content
    else:
        async for chunk in response.aiter_raw():
            yield chunk


async def read_logs(reader: Reader, path: str, params: dict[str, str], c: LogControls) -> LogRead:
    result = LogRead()
    transport = reader.transport
    if transport is not None and not isinstance(transport, httpx.AsyncBaseTransport):
        raise DceError(ErrorCode.API_INCOMPATIBLE, "Async log transport is unavailable.")
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
                        result.error = ErrorCode.UNSAFE_URL
                        return result
                    if status in {401, 403, 404, 429}:
                        result.error = {
                            401: ErrorCode.AUTH_FAILED,
                            403: ErrorCode.PERMISSION_DENIED,
                            404: ErrorCode.NOT_FOUND,
                            429: ErrorCode.RATE_LIMITED,
                        }[status]
                        return result
                    if response.headers.get("Content-Encoding", "identity").lower() != "identity":
                        result.error = ErrorCode.LOG_FILTER_UNSUPPORTED
                        return result
                    cap = min(c.max_bytes, 4096) if status >= 400 else c.max_bytes
                    async for chunk in raw_chunks(response):
                        buffer.extend(chunk[: cap - len(buffer)])
                        if len(buffer) >= cap:
                            result.reasons.append("RAW_BYTE_LIMIT")
                            break
                    if status >= 400:
                        result.error = log_error(
                            bytes(buffer),
                            ErrorCode.LOG_FILTER_UNSUPPORTED
                            if status in {400, 422, 501}
                            else ErrorCode.API_INCOMPATIBLE,
                        )
                        buffer.clear()
    except (TimeoutError, httpx.TimeoutException):
        result.error = ErrorCode.LOG_READ_TIMEOUT
        result.reasons.append("HTTP_DEADLINE")
    except (httpx.RequestError, OSError):
        result.error = ErrorCode.LOG_READ_INTERRUPTED
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
                raise DceError(ErrorCode.LOG_STREAM_INVALID, "Log line scan limit exceeded.")

    def feed(self, data: bytes) -> None:
        if self.tty:
            self.payload("combined", data)
            return
        self.buffer.extend(data)
        while len(self.buffer) >= 8:
            stream = self.buffer[0]
            length = int.from_bytes(self.buffer[4:8], "big")
            if stream not in {1, 2, 3} or self.buffer[1:4] != b"\0\0\0":
                raise DceError(ErrorCode.LOG_STREAM_INVALID, "Invalid Docker frame header.")
            if length > self.cap:
                # Never allocate the advertised size. finish distinguishes EOF corruption
                # from a legitimate large frame stopped by the raw payload cap.
                return
            if len(self.buffer) < 8 + length:
                return
            payload = bytes(self.buffer[8 : 8 + length])
            del self.buffer[: 8 + length]
            if stream == 3:
                self.error = log_error(payload, ErrorCode.LOG_READ_INTERRUPTED)
                return
            self.payload("stdout" if stream == 1 else "stderr", payload)

    def finish(self, *, partial: bool) -> list[tuple[str, bytes]]:
        if self.buffer and not partial and self.error is None:
            raise DceError(ErrorCode.LOG_STREAM_INVALID, "Incomplete Docker frame.")
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
                    ErrorCode.LOG_STREAM_INVALID, "Invalid timestamp or task context."
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
        "retention": "expired" if error == ErrorCode.LOGS_EXPIRED else "not_verified",
        "summary": {
            "returned_events": len(events),
            "free_text": "omitted",
            "content_trust": "untrusted_data",
            "client_filters": ["end_time", "keywords"],
            "completeness": "not_verified",
        },
    }
