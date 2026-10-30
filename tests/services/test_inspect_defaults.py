"""Tests for per-chain default RPC routing in inspect."""

from typing import Any
from unittest.mock import patch

from ruin.core.onchain import AccountInfo, BytecodeInfo, SourceInfo
from ruin.services import operations_ext as ext


class _StubAdapter:
    """Records the rpc string it was called with."""

    def __init__(self, chain: Any) -> None:
        self.chain = chain
        self.seen: list[str] = []

    def fetch_account(self, address: str, rpc: str) -> AccountInfo:
        self.seen.append(rpc)
        return AccountInfo(chain=self.chain, address=address, exists=True)

    def fetch_bytecode(self, address: str, _rpc: str) -> BytecodeInfo:
        return BytecodeInfo(chain=self.chain, address=address)

    def fetch_source(self, address: str) -> SourceInfo:
        return SourceInfo(chain=self.chain, address=address)

    def analyzers(self) -> list[str]:
        return []


def test_ton_and_solana_default_rpcs_are_used() -> None:
    stub = _StubAdapter(None)

    def _fake_get_adapter(chain: Any, transport: Any = None) -> Any:
        stub.chain = chain
        return stub

    with patch.object(ext, "get_adapter", _fake_get_adapter):
        ext._inspect({"address": "EQabc", "chain": "ton"})
        ext._inspect({"address": "Mint1", "chain": "sol"})
    assert stub.seen[0] == "https://toncenter.com"
    assert stub.seen[1] == "https://api.mainnet-beta.solana.com"


def test_evm_without_rpc_stays_offline() -> None:
    stub = _StubAdapter(None)
    with patch.object(ext, "get_adapter", lambda _chain, _transport=None: stub):
        out = ext._inspect({"address": "0xA", "chain": "ethereum"})
    assert stub.seen == []
    assert "no rpc provided" in out
