"""Tests for the TON chain adapter."""

from __future__ import annotations

import base64

import pytest

from ruin.core.enums import Chain
from ruin.services.ton import TonAdapter


class FakeTransport:
    """A transport that returns canned toncenter REST responses."""

    def __init__(self, url_results: dict[str, object]) -> None:
        """Store canned results keyed by request URL."""
        self.url_results = url_results

    def post_json(self, _url: str, _payload: dict[str, object]) -> dict[str, object]:
        """Return an empty JSON object."""
        return {}

    def get_json(self, url: str) -> object:
        """Return the canned response for the requested URL."""
        return self.url_results.get(url)

    def get_text(self, _url: str) -> str:
        """Return empty text."""
        return ""


ADDR = "EQB0_zxkA0XsT0nH8sYpQ2rN9dLmKjVfG7cEaZ3tYhWuSbXq"
STATE_URL = f"http://rpc/api/v2/getAccountState?address={ADDR}"


def test_validate_address() -> None:
    adapter = TonAdapter(FakeTransport({}))
    assert adapter.validate_address(ADDR) == ADDR


def test_validate_hex_address_normalizes() -> None:
    adapter = TonAdapter(FakeTransport({}))
    raw = "0:" + "ab" * 32
    assert adapter.validate_address(raw) == raw


def test_validate_rejects_bad_address() -> None:
    adapter = TonAdapter(FakeTransport({}))
    with pytest.raises(ValueError, match="invalid contract address"):
        adapter.validate_address("0x123")


def test_fetch_account_exists() -> None:
    payload = {
        "accountState": "accActive",
        "balance": "1000000000",
        "account": {"state": {"code": "eJxT", "data": "eJxU"}},
    }
    adapter = TonAdapter(FakeTransport({STATE_URL: payload}))
    info = adapter.fetch_account(ADDR, "http://rpc")
    assert info.chain is Chain.TON
    assert info.exists is True
    assert info.balance_native == "1000000000"
    assert "accountState=accActive" in info.note


def test_fetch_account_missing() -> None:
    payload = {"accountState": "accNotExists", "balance": "0"}
    adapter = TonAdapter(FakeTransport({STATE_URL: payload}))
    info = adapter.fetch_account(ADDR, "http://rpc")
    assert info.exists is False


def test_fetch_account_non_dict_response() -> None:
    adapter = TonAdapter(FakeTransport({STATE_URL: "not-json"}))
    info = adapter.fetch_account(ADDR, "http://rpc")
    assert info.exists is False
    assert info.balance_native == "0"


def test_fetch_bytecode_decodes_base64() -> None:
    raw = bytes([0xB5, 0xEE, 0x9C, 0x72])
    encoded = base64.b64encode(raw).decode()
    payload = {"accountState": "accActive", "account": {"state": {"code": encoded}}}
    adapter = TonAdapter(FakeTransport({STATE_URL: payload}))
    info = adapter.fetch_bytecode(ADDR, "http://rpc")
    assert info.kind == "ton"
    assert info.size_bytes == 4
    assert info.hexcode == raw.hex()


def test_fetch_bytecode_empty() -> None:
    payload = {"accountState": "accFrozen", "account": {"state": {}}}
    adapter = TonAdapter(FakeTransport({STATE_URL: payload}))
    info = adapter.fetch_bytecode(ADDR, "http://rpc")
    assert info.kind == "ton"
    assert info.size_bytes == 0
    assert info.note == "no code"


def test_fetch_bytecode_ignores_invalid_base64() -> None:
    payload = {"accountState": "accActive", "account": {"state": {"code": "!!!"}}}
    adapter = TonAdapter(FakeTransport({STATE_URL: payload}))
    info = adapter.fetch_bytecode(ADDR, "http://rpc")
    assert info.size_bytes == 0


def test_source_and_analyzers() -> None:
    adapter = TonAdapter(FakeTransport({}))
    src = adapter.fetch_source(ADDR)
    assert src is not None
    assert src.language == "FunC/Tact"
    assert src.verified is False
    assert adapter.analyzers() == []
