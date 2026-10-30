"""Single chain registry: endpoints, chain ids, and slug lookups.

Every EVM RPC/LCD default in the toolkit resolves through this module so
chain knowledge lives in exactly one place. Family-level defaults
(Solana/TON) live in ``ruin.services.chains`` because they depend on the
``Chain`` enum, which imports this module for slug fallbacks.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping

EVM_CHAIN_RPCS: dict[str, str] = {
    "ethereum": "https://ethereum-rpc.publicnode.com",
    "base": "https://base-rpc.publicnode.com",
    "arbitrum": "https://arb1.arbitrum.io/rpc",
    "optimism": "https://optimism-rpc.publicnode.com",
    "polygon": "https://polygon-bor-rpc.publicnode.com",
    "bsc": "https://bsc-rpc.publicnode.com",
    "avalanche": "https://avalanche-c-chain-rpc.publicnode.com",
    "sonic": "https://rpc.soniclabs.com",
    "linea": "https://rpc.linea.build",
    "scroll": "https://rpc.scroll.io",
    "berachain": "https://berachain-rpc.publicnode.com",
    "cronos": "https://cronos-evm-rpc.publicnode.com",
    "hyperliquid": "https://rpc.hyperliquid.xyz/evm",
    "unichain": "https://unichain.drpc.org",
    "ink": "https://ink.drpc.org",
    "megaeth": "https://mainnet.megaeth.com/rpc",
    "robinhood": "https://rpc.mainnet.chain.robinhood.com",
    "hemi": "https://rpc.hemi.network/rpc",
    "tempo": "https://rpc.tempo.xyz",
    "soneium": "https://rpc.soneium.org",
    "gnosis": "https://rpc.gnosischain.com",
    "celo": "https://forno.celo.org",
    "tac": "https://rpc.tac.build",
    "fraxtal": "https://rpc.frax.com",
    "coredao": "https://rpc.coredao.org/",
    "core": "https://rpc.coredao.org/",
    "kava": "https://evm.kava.io",
    "injective": "https://sentry.evm-rpc.injective.network",
    "hedera": "https://mainnet.hashio.io/api",
    "bouncebit": "https://fullnode-mainnet.bouncebitapi.com/",
    "etherlink": "https://node.mainnet.etherlink.com",
}

DEFAULT_EVM_RPC = EVM_CHAIN_RPCS["ethereum"]

CHAIN_SLUG_BY_ID: dict[int, str] = {
    1: "ethereum",
    56: "bsc",
    137: "polygon",
    100: "gnosis",
    146: "sonic",
    250: "fantom",
    324: "zksync",
    8453: "base",
    42161: "arbitrum",
    43114: "avalanche",
    59144: "linea",
    534352: "scroll",
    10: "optimism",
    80094: "berachain",
    4663: "robinhood",
    42793: "etherlink",
}

# DeFiLlama display chain names (lowercased) mapped to EIP-155 ids, so the
# cold feed can reuse the keyless Sourcify check on feed-known chains.
LLAMA_CHAIN_IDS: dict[str, int] = {
    "ethereum": 1,
    "binance": 56,
    "bsc": 56,
    "polygon": 137,
    "xdai": 100,
    "gnosis": 100,
    "sonic": 146,
    "fantom": 250,
    "zksync era": 324,
    "base": 8453,
    "arbitrum": 42161,
    "avalanche": 43114,
    "linea": 59144,
    "scroll": 534352,
    "optimism": 10,
    "op mainnet": 10,
    "berachain": 80094,
    "etherlink": 42793,
    "robinhood chain": 4663,
    "robinhood": 4663,
}

# EIP-155 ids for every slug in EVM_CHAIN_RPCS, so --chain <slug> alone can
# resolve explorers/Sourcify without a separate --chain-id. Values come from
# chainlist RPC-URL matches (26) and live eth_chainId probes (4).
EVM_CHAIN_IDS: dict[str, int] = {
    "arbitrum": 42161,
    "avalanche": 43114,
    "base": 8453,
    "berachain": 80094,
    "bouncebit": 6001,
    "bsc": 56,
    "celo": 42220,
    "coredao": 1116,
    "core": 1116,
    "cronos": 25,
    "ethereum": 1,
    "etherlink": 42793,
    "fraxtal": 252,
    "gnosis": 100,
    "hedera": 295,
    "hemi": 43111,
    "hyperliquid": 999,
    "injective": 1776,
    "ink": 57073,
    "kava": 2222,
    "linea": 59144,
    "megaeth": 4326,
    "optimism": 10,
    "polygon": 137,
    "robinhood": 4663,
    "scroll": 534352,
    "soneium": 1868,
    "sonic": 146,
    "tac": 239,
    "tempo": 4217,
    "unichain": 130,
}

CHAIN_LCDS: dict[str, str] = {
    "osmosis": "https://rest.cosmos.directory/osmosis",
    "neutron": "https://neutron-api.polkachu.com",
    "injective": "https://lcd.injective.network",
    "cosmoshub": "https://rest.cosmos.directory/cosmoshub",
    "persistence": "https://rest.core.persistence.one",
    "kava": "https://kava-api.polkachu.com",
    "celestia": "https://api.celestia.nodestake.org",
    "stride": "https://rest.lavenderfive.com/stride",
    "dydx": "https://dydx-api.polkachu.com",
    "akash": "https://api.akashnet.net",
}


def resolve_rpc(rpc: str | None, chain: str) -> str:
    """Pick the endpoint: explicit --rpc wins, else the chain table.

    Raises:
        ValueError: If the chain slug is unknown and no explicit RPC given.
    """
    if rpc:
        return rpc
    slug = chain.strip().lower()
    if slug not in EVM_CHAIN_RPCS:
        raise ValueError(
            f"unknown chain {chain!r} (known: "
            f"{', '.join(sorted(EVM_CHAIN_RPCS))}; or pass --rpc)"
        )
    return EVM_CHAIN_RPCS[slug]


def rpc_for(kwargs: Mapping[str, object]) -> str:
    """Resolve the RPC endpoint from parser kwargs (explicit --rpc wins)."""
    rpc = kwargs.get("rpc")
    chain = str(kwargs.get("chain") or "ethereum")
    return resolve_rpc(str(rpc) if rpc else None, chain)
