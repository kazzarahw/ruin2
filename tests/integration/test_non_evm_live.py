"""Live non-EVM RPC integration tests (opt-in via RUIN_INTEGRATION=1)."""

from __future__ import annotations

import os

import pytest

from ruin.core.enums import Chain
from ruin.services.chains import get_adapter
from ruin.services.rpc import HttpxTransport

pytestmark = pytest.mark.integration

SOLANA_RPC = "https://api.mainnet-beta.solana.com"
# SPL Token program id: a real, executable program account.
SPL_PROGRAM = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"


def _live() -> bool:
    return os.getenv("RUIN_INTEGRATION") == "1"


def test_solana_fetch_account_live() -> None:
    if not _live():
        pytest.skip("RUIN_INTEGRATION not set")
    adapter = get_adapter(Chain.SOLANA, HttpxTransport())
    try:
        info = adapter.fetch_account(SPL_PROGRAM, SOLANA_RPC)
    except RuntimeError as error:  # network/RPC unavailable
        pytest.skip(f"solana rpc unavailable: {error}")
    assert info.chain is Chain.SOLANA
    assert info.exists is True
    assert "executable=True" in info.note


def test_solana_fetch_bytecode_live() -> None:
    if not _live():
        pytest.skip("RUIN_INTEGRATION not set")
    adapter = get_adapter(Chain.SOLANA, HttpxTransport())
    try:
        info = adapter.fetch_bytecode(SPL_PROGRAM, SOLANA_RPC)
    except RuntimeError as error:
        pytest.skip(f"solana rpc unavailable: {error}")
    assert info.chain is Chain.SOLANA
    assert info.kind == "bpf"
    assert info.size_bytes > 0
