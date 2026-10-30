"""Tests for the Solana chain adapter."""

from __future__ import annotations

import base64

import pytest

from ruin.core.enums import Chain
from ruin.services.solana import SolanaAdapter


class FakeTransport:
    """A transport that returns canned Solana RPC responses."""

    def __init__(self, method_results: dict[str, object]) -> None:
        """Store canned results keyed by JSON-RPC method."""
        self.method_results = method_results

    def post_json(self, _url: str, payload: dict[str, object]) -> dict[str, object]:
        """Return a JSON-RPC envelope for the requested method."""
        return {"result": self.method_results.get(str(payload["method"]))}

    def get_json(self, _url: str) -> object:
        """Return a canned object keyed by URL, if provided."""
        return self.method_results.get(f"GET:{_url}", {})

    def get_text(self, _url: str) -> str:
        """Return empty text."""
        return ""


ADDR = "So11111111111111111111111111111111111111112"


def test_validate_address() -> None:
    adapter = SolanaAdapter(FakeTransport({}))
    assert adapter.validate_address(ADDR) == ADDR


def test_validate_rejects_bad_address() -> None:
    adapter = SolanaAdapter(FakeTransport({}))
    with pytest.raises(ValueError, match="invalid contract address"):
        adapter.validate_address("0x123")


def test_fetch_account_exists() -> None:
    payload = {"value": {"owner": "Tokenkeg", "executable": True, "lamports": 100}}
    adapter = SolanaAdapter(
        FakeTransport({"getBalance": {"value": 5}, "getAccountInfo": payload})
    )
    info = adapter.fetch_account(ADDR, "http://rpc")
    assert info.chain is Chain.SOLANA
    assert info.exists is True
    assert info.balance_native == "5"
    assert "owner=Tokenkeg" in info.note


def test_fetch_account_missing() -> None:
    adapter = SolanaAdapter(
        FakeTransport({"getBalance": {"value": 0}, "getAccountInfo": {"value": None}})
    )
    info = adapter.fetch_account(ADDR, "http://rpc")
    assert info.exists is False


def test_fetch_bytecode_decodes_base64() -> None:
    raw = bytes([0x7F, 0x45, 0x4C, 0x46])
    encoded = base64.b64encode(raw).decode()
    payload = {"value": {"data": [encoded, "base64"], "executable": True}}
    adapter = SolanaAdapter(FakeTransport({"getAccountInfo": payload}))
    info = adapter.fetch_bytecode(ADDR, "http://rpc")
    assert info.kind == "bpf"
    assert info.size_bytes == 4
    assert info.hexcode == raw.hex()


def test_fetch_bytecode_empty() -> None:
    adapter = SolanaAdapter(FakeTransport({"getAccountInfo": {"value": None}}))
    info = adapter.fetch_bytecode(ADDR, "http://rpc")
    assert info.size_bytes == 0


def test_source_and_analyzers() -> None:
    adapter = SolanaAdapter(FakeTransport({}))
    src = adapter.fetch_source(ADDR)
    assert src is not None
    assert src.verified is False
    assert adapter.analyzers() == ["anchor-check"]


def test_fetch_account_surfaces_spl_mint_authorities() -> None:
    parsed_value = {
        "owner": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
        "executable": False,
        "lamports": 1461600,
        "data": {
            "parsed": {
                "type": "mint",
                "info": {
                    "supply": "1000000000",
                    "decimals": 6,
                    "mintAuthority": "Deployer11111111111111111111111111111111111111",
                    "freezeAuthority": None,
                    "isInitialized": True,
                },
            },
        },
    }
    adapter = SolanaAdapter(
        FakeTransport(
            {"getBalance": {"value": 1}, "getAccountInfo": {"value": parsed_value}}
        )
    )
    info = adapter.fetch_account(ADDR, "http://rpc")
    assert info.exists
    assert "mintAuthority=Deployer" in info.note
    assert "freezeAuthority=NONE" in info.note
    assert "supply=1000000000" in info.note


def test_fetch_source_verified_program_gets_repo_url() -> None:
    status = {
        "is_verified": True,
        "repo_url": "https://github.com/Ellipsis-Labs/phoenix-v1",
        "commit": "deadbeef",
    }
    url = "https://verify.osec.io/status/" + ADDR
    adapter = SolanaAdapter(FakeTransport({f"GET:{url}": status}))
    src = adapter.fetch_source(ADDR)
    assert src is not None
    assert src.verified is True
    assert src.url == "https://github.com/Ellipsis-Labs/phoenix-v1/commit/deadbeef"


def test_fetch_source_unverified_program_has_no_url() -> None:
    status = {
        "is_verified": False,
        "repo_url": "https://github.com/raydium-io/raydium-amm",
    }
    url = "https://verify.osec.io/status/" + ADDR
    adapter = SolanaAdapter(FakeTransport({f"GET:{url}": status}))
    src = adapter.fetch_source(ADDR)
    assert src is not None
    assert src.verified is False
    assert src.url == ""


def test_fetch_source_handles_none_commit_string() -> None:
    status = {
        "is_verified": True,
        "repo_url": "https://github.com/Ellipsis-Labs/phoenix-v1",
        "commit": "None",
    }
    url = "https://verify.osec.io/status/" + ADDR
    adapter = SolanaAdapter(FakeTransport({f"GET:{url}": status}))
    src = adapter.fetch_source(ADDR)
    assert src is not None
    assert src.url == "https://github.com/Ellipsis-Labs/phoenix-v1"


def test_fetch_account_mint_flags_renounced() -> None:
    parsed_value = {
        "owner": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
        "executable": False,
        "data": {
            "parsed": {
                "type": "mint",
                "info": {
                    "supply": "1",
                    "decimals": 9,
                    "mintAuthority": None,
                    "freezeAuthority": None,
                    "isInitialized": True,
                },
            },
        },
    }
    url = "https://verify.osec.io/status/" + ADDR
    adapter = SolanaAdapter(
        FakeTransport(
            {
                "getBalance": {"value": 1},
                "getAccountInfo": {"value": parsed_value},
                f"GET:{url}": {"is_verified": False},
            }
        )
    )
    info = adapter.fetch_account(ADDR, "http://rpc")
    assert "flags=renounced" in info.note
