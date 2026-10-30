"""Bytecode namespace: live-address analysis and offline bytecode decode."""

from __future__ import annotations

from ruin.api._call import JsonPayload, call
from ruin.services.parsing_ext import DEFAULT_EVM_RPC
from ruin.services.subprocesses import ANVIL_DEV_ADDRESS


async def inspect(
    address: str,
    chain: str = "EVM",
    chain_id: int = 1,
    fetch_source: bool = False,
    rpc: str = "",
) -> JsonPayload | str:
    """Inspect an address's code and storage shape (CLI ``ruin bytecode inspect``)."""
    return await call(
        "inspect",
        {
            "address": address,
            "chain": chain,
            "chain_id": chain_id,
            "rpc": rpc,
            "source": fetch_source,
        },
    )


async def probe(
    address: str,
    chain: str = "ethereum",
    rpc: str | None = None,
    probe_from: str = ANVIL_DEV_ADDRESS,
    extra_selectors: list[str] | None = None,
) -> JsonPayload | str:
    """Smoke-test drain selectors from an outsider (CLI ``bytecode probe``)."""
    return await call(
        "probe",
        {
            "address": address,
            "rpc": rpc,
            "chain": chain,
            "probe_from": probe_from,
            "extra_selectors": extra_selectors or [],
        },
    )


async def selectors(
    target: str, chain: str = "ethereum", rpc: str | None = None, resolve: bool = False
) -> JsonPayload | str:
    """Selector surface of an address, or offline decode of a file/0x literal.

    CLI route ``ruin bytecode selectors``: a 40-hex address reads the on-chain
    dispatcher surface; anything else decodes offline (the former ``decode``).
    """
    return await call(
        "selectors",
        {"target": target, "rpc": rpc, "chain": chain, "resolve": resolve},
    )


async def decompile(
    address: str, chain: str = "ethereum", rpc: str | None = None
) -> JsonPayload | str:
    """Scan runtime code for review signals (CLI ``ruin bytecode decompile``)."""
    return await call("decompile", {"address": address, "rpc": rpc, "chain": chain})


async def cluster(
    addresses: list[str], chain: str = "EVM", rpc: str = DEFAULT_EVM_RPC
) -> JsonPayload | str:
    """Group addresses by bytecode and EIP-1167 clones (CLI ``bytecode cluster``)."""
    return await call("cluster", {"addresses": addresses, "rpc": rpc, "chain": chain})


async def proxy(address: str, rpc: str = DEFAULT_EVM_RPC) -> JsonPayload | str:
    """Resolve a proxy's implementation (CLI ``ruin bytecode proxy``)."""
    return await call("proxy", {"address": address, "rpc": rpc})


async def impl_diff(
    new_impl: str,
    old_impl: str,
    chain: str = "ethereum",
    rpc: str | None = None,
    old_rpc: str = "",
) -> JsonPayload | str:
    """Diff two implementation bytecodes (CLI ``ruin bytecode impl-diff``)."""
    return await call(
        "impl-diff",
        {
            "new_impl": new_impl,
            "old_impl": old_impl,
            "rpc": rpc,
            "chain": chain,
            "old_rpc": old_rpc,
        },
    )


async def slot_hunt(
    token: str,
    account: str | None = None,
    chain: str = "ethereum",
    rpc: str | None = None,
) -> JsonPayload | str:
    """Find an ERC-20 balances base slot (CLI ``ruin bytecode slot-hunt``)."""
    return await call(
        "slot-hunt",
        {"token": token, "account": account, "rpc": rpc, "chain": chain},
    )


__all__: list[str] = [
    "cluster",
    "decompile",
    "impl_diff",
    "inspect",
    "probe",
    "proxy",
    "selectors",
    "slot_hunt",
]
