"""Tests for the CosmWasm chain adapter."""

from __future__ import annotations

import base64

import pytest

from ruin.core.enums import Chain
from ruin.services.cosmwasm import CosmwasmAdapter


class FakeTransport:
    """A transport that returns canned Cosmos REST responses keyed by URL."""

    def __init__(self, url_results: dict[str, object]) -> None:
        """Store canned results keyed by request URL."""
        self.url_results = url_results

    def get_json(self, url: str) -> object:
        """Return the canned JSON body for the requested URL."""
        return self.url_results.get(url)

    def post_json(self, _url: str, _payload: dict[str, object]) -> dict[str, object]:
        """Return an empty object."""
        return {}

    def get_text(self, _url: str) -> str:
        """Return empty text."""
        return ""


ADDR = "cosmos1qypqxpq9qcrsszg2pvxq6rs0zqg3yyc5lzv7xu04"
RPC = "http://rpc"
CONTRACT_URL = f"{RPC}/cosmwasm/wasm/v1/contract/{ADDR}"
BALANCES_URL = f"{RPC}/cosmos/bank/v1beta1/balances/{ADDR}"
CODE_URL = f"{RPC}/cosmwasm/wasm/v1/code/5/raw"


def test_validate_address() -> None:
    adapter = CosmwasmAdapter(FakeTransport({}))
    assert adapter.validate_address(ADDR) == ADDR


def test_validate_rejects_bad_address() -> None:
    adapter = CosmwasmAdapter(FakeTransport({}))
    with pytest.raises(ValueError, match="invalid contract address"):
        adapter.validate_address("0x123")


def test_fetch_account_exists() -> None:
    contract = {"contract_info": {"code_id": "5", "label": "my contract"}}
    balances = {"balances": [{"denom": "uatom", "amount": "1234"}]}
    adapter = CosmwasmAdapter(
        FakeTransport({CONTRACT_URL: contract, BALANCES_URL: balances})
    )
    info = adapter.fetch_account(ADDR, RPC)
    assert info.chain is Chain.COSMWASM
    assert info.exists is True
    assert info.balance_native == "1234"
    assert "label=my contract" in info.note


def test_fetch_account_missing() -> None:
    adapter = CosmwasmAdapter(FakeTransport({}))
    info = adapter.fetch_account(ADDR, RPC)
    assert info.exists is False
    assert info.balance_native == "0"
    assert info.note == ""


def test_fetch_bytecode_decodes_base64() -> None:
    raw = bytes([0x00, 0x61, 0x73, 0x6D])
    encoded = base64.b64encode(raw).decode()
    contract = {"contract_info": {"code_id": "5"}}
    code = {"data": encoded}
    adapter = CosmwasmAdapter(FakeTransport({CONTRACT_URL: contract, CODE_URL: code}))
    info = adapter.fetch_bytecode(ADDR, RPC)
    assert info.kind == "wasm"
    assert info.size_bytes == 4
    assert info.hexcode == raw.hex()


def test_fetch_bytecode_empty() -> None:
    adapter = CosmwasmAdapter(FakeTransport({}))
    info = adapter.fetch_bytecode(ADDR, RPC)
    assert info.kind == "wasm"
    assert info.size_bytes == 0
    assert info.hexcode == ""


def test_source_and_analyzers() -> None:
    adapter = CosmwasmAdapter(FakeTransport({}))
    src = adapter.fetch_source(ADDR)
    assert src is not None
    assert src.language == "CosmWasm"
    assert src.verified is False
    assert adapter.analyzers() == []
