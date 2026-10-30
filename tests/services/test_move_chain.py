"""Tests for the Move chain adapter."""

from __future__ import annotations

import pytest

from ruin.core.enums import Chain
from ruin.services.move_chain import MoveAdapter


class FakeTransport:
    """A transport that returns canned Move REST responses."""

    def __init__(self, json_results: dict[str, object]) -> None:
        """Store canned results keyed by request URL."""
        self.json_results = json_results

    def post_json(self, _url: str, _payload: dict[str, object]) -> dict[str, object]:
        """Return an empty JSON object."""
        return {}

    def get_json(self, url: str) -> object:
        """Return the canned JSON body for a URL."""
        return self.json_results.get(url)

    def get_text(self, _url: str) -> str:
        """Return empty text."""
        return ""


ADDR = "0x" + "1" * 63 + "a"
RPC = "http://rpc"
ACCOUNT_URL = f"{RPC}/accounts/{ADDR}"
MODULES_URL = f"{RPC}/accounts/{ADDR}/modules"


def test_validate_address() -> None:
    adapter = MoveAdapter(FakeTransport({}))
    assert adapter.validate_address(ADDR) == ADDR


def test_validate_rejects_bad_address() -> None:
    adapter = MoveAdapter(FakeTransport({}))
    with pytest.raises(ValueError, match="invalid contract address"):
        adapter.validate_address("0x123")


def test_fetch_account_exists() -> None:
    payload = {"data": {"amount": "1000", "sequence_number": "7"}}
    adapter = MoveAdapter(FakeTransport({ACCOUNT_URL: payload}))
    info = adapter.fetch_account(ADDR, RPC)
    assert info.chain is Chain.MOVE
    assert info.exists is True
    assert info.balance_native == "1000"
    assert "sequence_number=7" in info.note


def test_fetch_account_missing() -> None:
    adapter = MoveAdapter(FakeTransport({ACCOUNT_URL: {"data": {}}}))
    info = adapter.fetch_account(ADDR, RPC)
    assert info.exists is False
    assert info.balance_native == "0"


def test_fetch_bytecode_present() -> None:
    hexcode = "0x71616263"
    adapter = MoveAdapter(FakeTransport({MODULES_URL: [{"bytecode": hexcode}]}))
    info = adapter.fetch_bytecode(ADDR, RPC)
    assert info.chain is Chain.MOVE
    assert info.kind == "move"
    assert info.hexcode == hexcode
    assert info.size_bytes == 4


def test_fetch_bytecode_empty() -> None:
    adapter = MoveAdapter(FakeTransport({MODULES_URL: []}))
    info = adapter.fetch_bytecode(ADDR, RPC)
    assert info.size_bytes == 0
    assert info.note == "no modules"


def test_source_and_analyzers() -> None:
    adapter = MoveAdapter(FakeTransport({}))
    src = adapter.fetch_source(ADDR)
    assert src is not None
    assert src.language == "Move"
    assert src.verified is False
    assert adapter.analyzers() == []
