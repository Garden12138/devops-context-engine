import json
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from dce.common.errors import DceError
from dce.security.redact import redact


def envelope(data: Any = None, *, error: DceError | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {
        "schema_version": "1.0",
        "request_id": str(uuid4()),
        "status": "error" if error else "ok",
        "data": redact(data),
        "evidence": [],
        "warnings": [],
        "uncertainties": [],
        "truncated": False,
        "snapshot_at": datetime.now(UTC).isoformat(),
    }
    if error:
        result["error"] = redact(error.as_dict())
    return result


def encode(result: dict[str, Any], budget: int = 16000) -> str:
    """Bound UTF-8 bytes; preserve metadata and explicit omission notice."""
    text = json.dumps(result, ensure_ascii=False, separators=(",", ":"))
    if len(text.encode()) > budget:
        result = {
            **result,
            "data": None,
            "evidence": [],
            "truncated": True,
            "warnings": ["OUTPUT_BUDGET_EXCEEDED"],
            "uncertainties": ["Data omitted; request a smaller page."],
            "next_action": "Reduce page size or query a specific resource.",
        }
        text = json.dumps(result, ensure_ascii=False, separators=(",", ":"))
    return text
