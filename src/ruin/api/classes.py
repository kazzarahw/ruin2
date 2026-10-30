"""Bug-class namespace: screens for specific exploit classes."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ruin.api._call import JsonPayload, call
from ruin.services.parsing_ext import DEFAULT_EVM_RPC

if TYPE_CHECKING:
    from ruin.api._requests import ThinRequest


async def erc4626_solvency(
    vault: str, underlying: str = "", rpc: str = DEFAULT_EVM_RPC
) -> JsonPayload | str:
    """Check ERC-4626 accounting on a live vault (CLI ``classes erc4626``)."""
    return await call(
        "solvency", {"vault": vault, "rpc": rpc, "underlying": underlying}
    )


async def ctoken_inflation(
    ctoken: str, chain: str = "ethereum", rpc: str | None = None
) -> JsonPayload | str:
    """Probe a cToken for inflation-attack exposure (CLI ``ruin classes ctoken``)."""
    return await call(
        "ctoken-inflation", {"ctoken": ctoken, "rpc": rpc, "chain": chain}
    )


async def honeypot(mint: str, rpc: str = "") -> JsonPayload | str:
    """Score a Solana mint for honeypot risk (CLI ``classes honeypot``)."""
    return await call("honeypot", {"mint": mint, "rpc": rpc})


async def honeypot_evm(
    token: str, chain: str = "ethereum", rpc: str | None = None
) -> JsonPayload | str:
    """Fork-probe an EVM token for gating (CLI ``classes honeypot-evm``)."""
    return await call("honeypot-evm", {"token": token, "rpc": rpc, "chain": chain})


async def thin_collateral(
    req: ThinRequest, chain: str = "ethereum", rpc: str | None = None
) -> JsonPayload | str:
    """Thin-collateral depth screen (CLI ``classes thin-collateral``)."""
    return await call(
        "thin-collateral",
        {
            "token": req.token,
            "market": req.market,
            "factory": req.factory,
            "rpc": rpc,
            "chain": chain,
            "blocks": req.blocks,
            "price_usd": req.price_usd,
            "min_usd": req.min_usd,
        },
    )


async def rng_hack(
    mechanism: str,
    summary: list[str],
    source: list[str],
    decision: str | None = None,
    manipulator: str | None = None,
) -> JsonPayload | str:
    """Assess RNG-source manipulability (CLI ``ruin classes rng``)."""
    return await call(
        "rng-hack",
        {
            "mechanism": mechanism,
            "summary": summary,
            "source": source,
            "decision": decision,
            "manipulator": manipulator,
        },
    )


async def mintsig(
    address: str, chain: str = "ethereum", rpc: str | None = None
) -> JsonPayload | str:
    """Check mint/signature authority signals (CLI ``ruin classes mintsig``)."""
    return await call("mintsig", {"address": address, "rpc": rpc, "chain": chain})


async def cosmos_gov(
    chain: str = "neutron", lcd: str | None = None
) -> JsonPayload | str:
    """Read Cosmos governance parameters (CLI ``ruin classes cosmos-gov``)."""
    return await call("cosmos-gov", {"lcd": lcd, "chain": chain})


__all__: list[str] = [
    "cosmos_gov",
    "ctoken_inflation",
    "erc4626_solvency",
    "honeypot",
    "honeypot_evm",
    "mintsig",
    "rng_hack",
    "thin_collateral",
]
