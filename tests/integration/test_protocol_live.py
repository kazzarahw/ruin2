"""Opt-in live test: resolve the strUSD vault proxy end to end."""

from __future__ import annotations

import os

import pytest

from ruin.services.protocol import resolve

pytestmark = pytest.mark.integration

STRUSD_VAULT = "0x280839980a7eD0D7717F64125fE241012E5F5815"
STRUSD_IMPL = "0x6561272e3ebc9f2e07cdb12b7c474db9132b977a"


@pytest.mark.skipif(os.getenv("RUIN_INTEGRATION") != "1", reason="opt-in")
def test_resolve_strusd_vault_end_to_end() -> None:
    # hits Sourcify, the public mainnet RPC, and downloads solc on first run
    protocol = resolve(STRUSD_VAULT, chain="ethereum")
    assert protocol.verified
    assert protocol.implementation.lower() == STRUSD_IMPL
    assert protocol.graph.contracts
    assert "setCooldownDuration" in protocol.graph.entrypoints
