"""Tests for the Cairo chain adapter."""

from __future__ import annotations

import pytest

from ruin.core.enums import Chain
from ruin.services.cairo import CairoAdapter


class FakeTransport:
    """A transport that returns canned Starknet JSON-RPC responses."""

    def __init__(self, method_results: dict[str, object]) -> None:
        """Store canned results keyed by JSON-RPC method."""
        self.method_results = method_results

    def post_json(self, _url: str, payload: dict[str, object]) -> dict[str, object]:
        """Return a JSON-RPC envelope for the requested method."""
        return {"result": self.method_results.get(str(payload["method"]))}

    def get_json(self, _url: str) -> object:
        """Return an empty object."""
        return {}

    def get_text(self, _url: str) -> str:
        """Return empty text."""
        return ""


ADDR = "0x" + "0" * 60 + "abcd"


def test_validate_address() -> None:
    adapter = CairoAdapter(FakeTransport({}))
    assert adapter.validate_address(ADDR) == ADDR


def test_validate_normalizes_case() -> None:
    adapter = CairoAdapter(FakeTransport({}))
    assert adapter.validate_address("0xABCD") == "0xabcd"


def test_validate_rejects_bad_address() -> None:
    adapter = CairoAdapter(FakeTransport({}))
    with pytest.raises(ValueError, match="invalid contract address"):
        adapter.validate_address("0xzz")


def test_fetch_account_exists() -> None:
    adapter = CairoAdapter(
        FakeTransport(
            {
                "starknet_getNonce": "0x2",
                "starknet_getBalance": {"amount": "0x2386f26fc10000"},
            }
        )
    )
    info = adapter.fetch_account(ADDR, "http://rpc")
    assert info.chain is Chain.CAIRO
    assert info.exists is True
    assert info.balance_native == "10000000000000000"
    assert "nonce=0x2" in info.note


def test_fetch_account_missing() -> None:
    adapter = CairoAdapter(
        FakeTransport({"starknet_getNonce": None, "starknet_getBalance": None})
    )
    info = adapter.fetch_account(ADDR, "http://rpc")
    assert info.exists is False
    assert info.balance_native == "0"


def test_fetch_bytecode_collects_selectors() -> None:
    class_at = {
        "entry_points_by_type": {
            "EXTERNAL": [{"selector": "0xabcdef"}, {"selector": "0x1234"}],
            "CONSTRUCTOR": [{"selector": "0xabcdef"}],
        }
    }
    adapter = CairoAdapter(FakeTransport({"starknet_getClassAt": class_at}))
    info = adapter.fetch_bytecode(ADDR, "http://rpc")
    assert info.kind == "cairo"
    assert info.size_bytes == 0
    assert info.decoded is not None
    assert info.decoded.selectors == ["0xabcdef", "0x1234"]
    assert info.decoded.strings == []


def test_fetch_bytecode_missing_class() -> None:
    adapter = CairoAdapter(FakeTransport({"starknet_getClassAt": None}))
    info = adapter.fetch_bytecode(ADDR, "http://rpc")
    assert info.kind == "cairo"
    assert info.size_bytes == 0
    assert info.decoded is None


def test_source_and_analyzers() -> None:
    adapter = CairoAdapter(FakeTransport({}))
    src = adapter.fetch_source(ADDR)
    assert src is not None
    assert src.language == "Cairo"
    assert src.verified is False
    assert adapter.analyzers() == []
