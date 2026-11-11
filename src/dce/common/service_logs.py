"""Shared, transport-independent limits for the scoped service log operation."""

import re
from datetime import UTC, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

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
