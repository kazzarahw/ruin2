"""Tests for the shared chain registry."""

from ruin.core.chains import (
    CHAIN_SLUG_BY_ID,
    DEFAULT_EVM_RPC,
    EVM_CHAIN_IDS,
    EVM_CHAIN_RPCS,
    rpc_for,
)


def test_default_evm_rpc_is_the_table_entry() -> None:
    assert EVM_CHAIN_RPCS["ethereum"] == DEFAULT_EVM_RPC


def test_rpc_for_prefers_explicit_endpoint() -> None:
    assert rpc_for({"rpc": "http://mine", "chain": "base"}) == "http://mine"


def test_rpc_for_falls_back_to_chain_table() -> None:
    assert rpc_for({"chain": "Arbitrum"}) == "https://arb1.arbitrum.io/rpc"


def test_rpc_for_defaults_to_ethereum() -> None:
    assert rpc_for({}) == DEFAULT_EVM_RPC


def test_slug_table_resolves_known_chain_ids() -> None:
    assert CHAIN_SLUG_BY_ID[8453] == "base"
    assert CHAIN_SLUG_BY_ID[1] == "ethereum"
    assert CHAIN_SLUG_BY_ID[4663] == "robinhood"
    assert CHAIN_SLUG_BY_ID[42793] == "etherlink"


def test_slug_ids_cover_every_rpc_slug_and_agree_with_reverse_table() -> None:
    assert EVM_CHAIN_IDS["polygon"] == 137
    assert EVM_CHAIN_IDS["etherlink"] == 42793
    for chain_id, slug in CHAIN_SLUG_BY_ID.items():
        if slug in EVM_CHAIN_RPCS:
            assert EVM_CHAIN_IDS[slug] == chain_id


def test_niche_evm_chains_resolve_endpoints() -> None:
    assert rpc_for({"chain": "etherlink"}) == "https://node.mainnet.etherlink.com"
    assert rpc_for({"chain": "core"}) == "https://rpc.coredao.org/"
    assert EVM_CHAIN_RPCS["robinhood"] == "https://rpc.mainnet.chain.robinhood.com"
