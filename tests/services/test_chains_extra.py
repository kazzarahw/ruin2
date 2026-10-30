"""Tests for the chain adapter registry and EVM adapter."""

from __future__ import annotations

from ruin.core.enums import Chain
from ruin.services.chains import EvmChainAdapter, get_adapter


def test_evm_validate_address() -> None:
    adapter = get_adapter(Chain.EVM)
    assert adapter.validate_address("0x" + "a" * 40) == "0x" + "a" * 40


def test_evm_analyzers() -> None:
    adapter = EvmChainAdapter()
    assert "slither" in adapter.analyzers()


def test_evm_source_unverified() -> None:
    src = EvmChainAdapter().fetch_source("0x" + "a" * 40)
    assert src is not None
    assert src.verified is False


def test_solana_adapter_resolved() -> None:
    adapter = get_adapter(Chain.SOLANA)
    assert adapter.chain is Chain.SOLANA
