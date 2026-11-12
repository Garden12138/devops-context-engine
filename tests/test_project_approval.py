"""Browser fallback uses synthetic proposals and loopback only."""

import asyncio
import ipaddress
import re
import socket
import time
from unittest.mock import AsyncMock

import httpx
import pytest

from dce.common.errors import DceError
from dce.project.approval import ApprovalBroker, LocalReview, checked_answer


@pytest.fixture(autouse=True)
def no_ip_network(monkeypatch):
    """This module tests a real local page; external IP connections remain forbidden."""
    connect = socket.socket.connect

    def guarded(sock, address):
        if (
            sock.family in {socket.AF_INET, socket.AF_INET6}
            and not ipaddress.ip_address(address[0]).is_loopback
        ):
            raise AssertionError("External network forbidden")
        return connect(sock, address)

    monkeypatch.setattr(socket.socket, "connect", guarded)


def test_review_network_guard_still_blocks_external_ips():
    with socket.socket() as connection:
        with pytest.raises(AssertionError, match="External network forbidden"):
            connection.connect(("203.0.113.1", 80))


def test_local_review_origin_csrf_html_escape_and_single_use():
    review = LocalReview('Synthetic <script>alert("untrusted")</script>')
    try:
        with httpx.Client(trust_env=False) as client:
            response = client.get(review.url)
            assert response.status_code == 200
            assert "<script>" not in response.text and "&lt;script&gt;" in response.text
            assert response.headers["cache-control"] == "no-store"
            csrf = re.search('name=csrf value="([^"]+)"', response.text)[1]
            fields = {
                "csrf": csrf,
                "decision": "approve",
                "actor": "reviewer",
                "reason": "synthetic consent",
            }
            assert client.post(review.url, data=fields).status_code == 403
            assert (
                client.post(
                    review.url, data={**fields, "csrf": "wrong"}, headers={"Origin": review.origin}
                ).status_code
                == 400
            )
            assert (
                client.get(review.url, headers={"Host": "outside.example.invalid"}).status_code
                == 404
            )
            assert not review.decided
            assert (
                client.post(review.url, data=fields, headers={"Origin": review.origin}).status_code
                == 200
            )
            assert review.answer["actor"] == "reviewer"
            assert (
                client.post(review.url, data=fields, headers={"Origin": review.origin}).status_code
                == 403
            )
    finally:
        review.close()


def test_browser_pending_proposal_replacement_expiry_and_decline():
    broker = ApprovalBroker()

    async def check():
        assert await broker.request("one", "Synthetic proposal one", None) is None
        old = broker.pending["one"]
        assert broker.waiting("one")["state"] == "awaiting_user_confirmation"
        assert await broker.request("one", "Synthetic proposal one", None) is None
        assert broker.pending["one"] is old
        assert await broker.request("two", "Synthetic proposal two", None) is None
        assert "one" not in broker.pending
        broker.pending["two"].expires = time.monotonic() - 1
        with pytest.raises(DceError):
            await broker.request("two", "Synthetic proposal two", None)
        assert not broker.pending
        await broker.request("three", "Synthetic proposal three", None)
        review = broker.pending["three"]
        with httpx.Client(trust_env=False) as client:
            client.post(
                review.url,
                data={"csrf": review.csrf, "decision": "decline"},
                headers={"Origin": review.origin},
            )
        with pytest.raises(DceError):
            await broker.request("three", "Synthetic proposal three", None)
        await broker.request("four", "Synthetic approval", None)
        review = broker.pending["four"]
        with httpx.Client(trust_env=False) as client:
            response = client.post(
                review.url,
                data={
                    "csrf": review.csrf,
                    "decision": "approve",
                    "actor": "reviewer",
                    "reason": "synthetic",
                },
                headers={"Origin": review.origin},
            )
            assert response.status_code == 200
        assert (await broker.request("four", "Synthetic approval", None))["actor"] == "reviewer"
        assert not broker.pending

    try:
        asyncio.run(check())
    finally:
        broker.close()


def test_native_consent_refusal_identity_and_long_proposal_fallback():
    broker = ApprovalBroker()

    async def check():
        for answer in (None, {"actor": "agent", "reason": "synthetic", "relationships": ""}):
            with pytest.raises((DceError, ValueError)):
                await broker.request("native", "Synthetic", AsyncMock(return_value=answer))
        with pytest.raises(ValueError):
            checked_answer({"actor": True, "reason": "synthetic"})
        native = AsyncMock(
            return_value={"actor": "reviewer", "reason": "synthetic", "relationships": ""}
        )
        assert await broker.request("long", "Synthetic proposal " * 1000, native) is None
        native.assert_not_called()  # Full proposal stays on local page; no truncated approval.
        assert (await broker.request("ok", "Synthetic", native))["actor"] == "reviewer"

    try:
        asyncio.run(check())
    finally:
        broker.close()


def test_advertised_but_unsupported_native_confirmation_falls_back_without_overriding_denial():
    from mcp import types
    from mcp.shared.exceptions import McpError

    broker = ApprovalBroker()

    async def check():
        unavailable = AsyncMock(
            side_effect=McpError(types.ErrorData(code=-32601, message="synthetic unsupported"))
        )
        assert await broker.request("unsupported", "Synthetic", unavailable) is None
        assert "unsupported" in broker.pending
        broker.close()
        denied = AsyncMock(
            side_effect=McpError(types.ErrorData(code=-32000, message="synthetic denied"))
        )
        with pytest.raises(DceError):
            await broker.request("denied", "Synthetic", denied)
        assert not broker.pending

    try:
        asyncio.run(check())
    finally:
        broker.close()
