"""Tests must never reach external or company networks; HTTP uses MockTransport."""

import socket
from typing import Any

import pytest


@pytest.fixture(autouse=True)
def no_ip_network(monkeypatch: pytest.MonkeyPatch) -> None:
    connect = socket.socket.connect

    def guarded_connect(sock: socket.socket, address: Any) -> Any:
        if sock.family in {socket.AF_INET, socket.AF_INET6}:
            raise AssertionError("Offline test attempted an IP network connection")
        return connect(sock, address)

    monkeypatch.setattr(socket.socket, "connect", guarded_connect)
