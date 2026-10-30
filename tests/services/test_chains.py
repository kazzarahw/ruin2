"""Tests for chain adapters."""

from ruin.core.enums import Chain
from ruin.services.chains import get_adapter, rpc_for_family


def test_chain_adapter() -> None:
    adapter = get_adapter(Chain.EVM)
    assert adapter.validate_address("0x" + "1" * 40) == "0x" + "1" * 40


def test_rpc_for_family_covers_solana_and_ton() -> None:
    assert rpc_for_family(Chain.SOLANA) == "https://api.mainnet-beta.solana.com"
    assert rpc_for_family(Chain.TON) == "https://toncenter.com"
    assert rpc_for_family(Chain.EVM) == ""
