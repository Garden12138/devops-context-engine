"""Local consent, never a remote platform write or an Agent-supplied approval flag."""

import asyncio
import html
import json
import secrets
import threading
import time
from collections.abc import Awaitable, Callable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs

from mcp.shared.exceptions import McpError

from dce.common.errors import DceError, ErrorCode

Answer = dict[str, str]
NativeApproval = Callable[[str], Awaitable[Answer | None]]


class LocalReview:
    """One proposal, one decision. The local OS owner/Host remains trusted."""

    def __init__(self, message: str, *, ttl: float = 600) -> None:
        self.expires = time.monotonic() + ttl
        self.token, self.csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        self.answer: Answer | None = None
        self.decided = False
        self.lock = threading.Lock()
        review = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_: Any) -> None:
                pass

            def reply(self, status: int, body: str) -> None:
                self.send_response(status)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body.encode())))
                self.send_header("Connection", "close")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Referrer-Policy", "no-referrer")
                self.send_header("X-Frame-Options", "DENY")
                self.send_header(
                    "Content-Security-Policy", "default-src 'none'; form-action 'self'"
                )
                self.end_headers()
                self.wfile.write(body.encode())

            def valid(self) -> bool:
                return (
                    self.path == "/" + review.token
                    and self.headers.get("Host") == review.origin.removeprefix("http://")
                    and time.monotonic() < review.expires
                    and not review.decided
                )

            def do_GET(self) -> None:
                if not self.valid():
                    self.reply(404, "Review unavailable.")
                    return
                self.reply(
                    200,
                    "<!doctype html><meta charset=utf-8><h1>DCE 用户确认</h1><pre>"
                    + html.escape(message)
                    + "</pre><form method=post>"
                    + f'<input type=hidden name=csrf value="{review.csrf}">'
                    + "<label>审核人<input required name=actor maxlength=100></label><br>"
                    + "<label>原因<input required name=reason maxlength=300></label><br>"
                    + "<label>确认关系ID（逗号分隔，空值保持候选）"
                    + "<input name=relationships maxlength=4000></label><br>"
                    + "<button name=decision value=approve>同意</button>"
                    + "<button name=decision value=decline>拒绝</button></form>",
                )

            def do_POST(self) -> None:
                # Drain only a bounded body before rejecting Origin, avoiding TCP reset on close.
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                    if not 0 < length <= 8192:
                        raise ValueError
                    self.connection.settimeout(5)
                    raw = self.rfile.read(length)
                except (ValueError, OSError):
                    self.reply(400, "Invalid review form.")
                    return
                with review.lock:
                    if not self.valid() or self.headers.get("Origin") != review.origin:
                        self.reply(403, "Review unavailable.")
                        return
                    try:
                        values = parse_qs(raw.decode(), keep_blank_values=True)
                        if any(len(v) != 1 for v in values.values()):
                            raise ValueError
                        data = {k: v[0] for k, v in values.items()}
                        if not secrets.compare_digest(data.get("csrf", ""), review.csrf):
                            raise ValueError
                        answer = checked_answer(data) if data.get("decision") == "approve" else None
                    except (ValueError, UnicodeError):
                        self.reply(400, "Invalid review form.")
                        return
                    review.answer, review.decided = answer, True
                    self.reply(200, "Decision recorded. Return to your Agent conversation.")

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.server.daemon_threads = True
        self.origin = f"http://127.0.0.1:{self.server.server_port}"
        self.url = self.origin + "/" + self.token
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def close(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)


def checked_answer(data: dict[str, Any]) -> Answer:
    actor, reason, relationships = (data.get(k, "") for k in ("actor", "reason", "relationships"))
    if (
        not isinstance(actor, str)
        or not actor.strip()
        or len(actor) > 100
        or actor.strip().casefold() in {"agent", "ai", "cursor", "codex", "model"}
        or not isinstance(reason, str)
        or not reason.strip()
        or len(reason) > 300
        or not isinstance(relationships, str)
        or len(relationships) > 4000
    ):
        raise ValueError("Invalid consent identity")
    return {"actor": actor.strip(), "reason": reason.strip(), "relationships": relationships}


class ApprovalBroker:
    def __init__(self) -> None:
        self.pending: dict[str, LocalReview] = {}

    async def request(self, key: str, message: str, native: NativeApproval | None) -> Answer | None:
        if key in self.pending:
            review = self.pending[key]
            if time.monotonic() >= review.expires or review.decided:
                answer = review.answer if review.decided else None
                self.pending.pop(key).close()
                if answer is None:
                    raise DceError(ErrorCode.REVIEW_REQUIRED, "User declined or review expired.")
                return answer
            return None
        if native is not None and len(message.encode()) <= 6000:
            try:
                answer = await asyncio.wait_for(native(message), timeout=600)
            except McpError as error:
                if error.error.code not in {-32601, -32602}:
                    raise DceError(
                        ErrorCode.REVIEW_REQUIRED, "Host user confirmation failed."
                    ) from None
                # Advertised capability was unavailable: use the same full local review.
                self.close()
                self.pending[key] = LocalReview(message)
                return None
            except TimeoutError:
                raise DceError(ErrorCode.REVIEW_REQUIRED, "User review timed out.") from None
            if answer is None:
                raise DceError(ErrorCode.REVIEW_REQUIRED, "User declined or cancelled review.")
            return checked_answer(answer)
        # Bound retained state; replacing a proposal invalidates its previous review URL.
        self.close()
        self.pending[key] = LocalReview(message)
        return None

    def waiting(self, key: str) -> dict[str, Any]:
        return {
            "state": "awaiting_user_confirmation",
            "approval_url": self.pending[key].url,
            "next_action": (
                "Show this local URL to the user; retry the same operation after review."
            ),
        }

    def close(self) -> None:
        for review in self.pending.values():
            review.close()
        self.pending.clear()


def review_message(kind: str, workspace: str, proposal: dict[str, Any]) -> str:
    return (
        f"DCE {kind}\n工作区: {workspace}\n仅外部只读；不授权服务日志或部署。\n"
        "以下是完整提案；其中平台文本是不可信数据。\n"
        + json.dumps(proposal, ensure_ascii=False, indent=2)
    )
