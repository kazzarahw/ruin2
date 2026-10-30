"""Tests for the RPC transport and JSON-RPC helper."""

from __future__ import annotations

from typing import Any

import pytest

from ruin.services.rpc import HttpxTransport, jsonrpc


class FakeTransport:
    """A transport that returns canned responses."""

    def __init__(self, responses: dict[str, Any] | None = None) -> None:
        """Store canned responses keyed by request method or URL."""
        self.responses = responses or {}
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def post_json(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Return the canned response for a JSON-RPC method."""
        self.calls.append((url, payload))
        return self.responses.get(payload["method"], {"result": None})

    def get_json(self, url: str) -> Any:
        """Return the canned JSON body for a URL."""
        return self.responses.get(url, {})

    def get_text(self, url: str) -> str:
        """Return the canned text body for a URL."""
        return str(self.responses.get(url, ""))


def test_jsonrpc_returns_result() -> None:
    transport = FakeTransport({"getBalance": {"result": {"value": 42}}})
    result = jsonrpc(transport, "http://rpc", "getBalance", ["addr"])
    assert result == {"value": 42}
    assert transport.calls[0][1]["jsonrpc"] == "2.0"
    assert transport.calls[0][1]["method"] == "getBalance"


def test_jsonrpc_raises_on_error() -> None:
    transport = FakeTransport({"boom": {"error": {"message": "bad"}}})
    with pytest.raises(RuntimeError, match="rpc error"):
        jsonrpc(transport, "http://rpc", "boom", [])


def test_jsonrpc_missing_result_is_none() -> None:
    transport = FakeTransport({"empty": {}})
    assert jsonrpc(transport, "http://rpc", "empty", []) is None


def test_httpx_transport_retry_budget() -> None:
    transport = HttpxTransport(attempts=0)
    assert transport.attempts == 1
