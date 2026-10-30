Reference adapter (Solana):

```python
"""Solana chain adapter for ``ruin``."""

from __future__ import annotations

import base64
from typing import TYPE_CHECKING, cast

from ruin.core.enums import Chain
from ruin.core.ids import validate_address
from ruin.core.onchain import AccountInfo, BytecodeInfo, SourceInfo
from ruin.services.rpc import jsonrpc

if TYPE_CHECKING:
    from ruin.services.rpc import RpcTransport


class SolanaAdapter:
    """Adapter for Solana, backed by cluster JSON-RPC."""

    chain = Chain.SOLANA

    def __init__(self, transport: RpcTransport) -> None:
        """Initialize the adapter with an RPC transport."""
        self.transport = transport

    def validate_address(self, address: str) -> str:
        """Validate and normalize a base58 Solana address."""
        return validate_address(Chain.SOLANA, address)

    def fetch_account(self, address: str, rpc: str) -> AccountInfo:
        """Fetch the lamport balance and account record for an address."""
        balance = jsonrpc(self.transport, rpc, "getBalance", [address])
        info = jsonrpc(
            self.transport, rpc, "getAccountInfo", [address, {"encoding": "base64"}]
        )
        value = info.get("value") if isinstance(info, dict) else None
        exists = value is not None
        owner = ""
        executable = False
        if isinstance(value, dict):
            owner = str(value.get("owner", ""))
            executable = bool(value.get("executable", False))
        return AccountInfo(
            chain=Chain.SOLANA,
            address=address,
            exists=exists,
            balance_native=str(balance.get("value", 0))
            if isinstance(balance, dict)
            else "0",
            raw=cast("dict[str, object]", value) if isinstance(value, dict) else {},
            note=f"owner={owner} executable={executable}",
        )

    def fetch_bytecode(self, address: str, rpc: str) -> BytecodeInfo:
        """Fetch program bytes (base64 BPF) for an executable account."""
        info = jsonrpc(
            self.transport, rpc, "getAccountInfo", [address, {"encoding": "base64"}]
        )
        value = info.get("value") if isinstance(info, dict) else None
        data = _decode_data(value)
        return BytecodeInfo(
            chain=Chain.SOLANA,
            address=address,
            kind="bpf",
            hexcode=data.hex() if data else "",
            size_bytes=len(data),
            note="BPF program bytes (base64-decoded)" if data else "no program data",
        )

    def fetch_source(self, address: str) -> SourceInfo | None:
        """Return an IDL placeholder; Anchor IDL lookup is a later ingestion step."""
        return SourceInfo(
            chain=Chain.SOLANA,
            address=address,
            language="Rust/Anchor",
            verified=False,
        )

    def analyzers(self) -> list[str]:
        """Return Solana analyzers available to the toolkit."""
        return ["anchor-check"]


def _decode_data(value: object) -> bytes:
    """Decode Solana account data, which may be base64 or base58 framed."""
    if not isinstance(value, dict):
        return b""
    payload = _data_payload(value.get("data"))
    if payload is None:
        return b""
    blob, encoding = payload
    if encoding != "base64":
        return b""
    try:
        return base64.b64decode(blob)
    except (ValueError, TypeError):
        return b""


def _data_payload(data: object) -> tuple[str, str] | None:
    """Return the (blob, encoding) pair for account data, if present."""
    if isinstance(data, list) and data and isinstance(data[0], str):
        encoding = data[1] if len(data) > 1 else "base64"
        return data[0], str(encoding)
    if isinstance(data, str):
        return data, "base64"
    return None
```

Reference test (FakeTransport):

```python
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
        """Return an empty object."""
        return {}

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
```
