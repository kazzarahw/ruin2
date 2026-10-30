"""Chain namespace: live transaction and log reads for forensics."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ruin.api._call import JsonPayload, call
from ruin.services.parsing_ext import DEFAULT_EVM_RPC

if TYPE_CHECKING:
    from ruin.api._requests import BlockWindow


async def trace(tx: str, rpc: str = DEFAULT_EVM_RPC) -> JsonPayload | str:
    """Trace one transaction's call structure (CLI ``ruin chain trace``)."""
    return await call("trace", {"tx": tx, "rpc": rpc})


async def logs(
    address: str,
    window: BlockWindow,
    chain: str = "EVM",
    rpc: str = DEFAULT_EVM_RPC,
) -> JsonPayload | str:
    """Scan an emitter's events over a block window (CLI ``ruin chain logs``)."""
    return await call(
        "logs",
        {
            "address": address,
            "rpc": rpc,
            "from_block": window.from_block,
            "to_block": window.to_block,
            "chain": chain,
        },
    )


async def replay(
    tx: str,
    address: str,
    window: BlockWindow,
    rpc: str,
    chain: str = "EVM",
) -> JsonPayload | str:
    """Rebuild an exploit timeline from logs and traces (CLI ``ruin chain replay``)."""
    return await call(
        "replay",
        {
            "tx": tx,
            "address": address,
            "rpc": rpc,
            "from_block": window.from_block,
            "to_block": window.to_block,
            "chain": chain,
        },
    )


__all__: list[str] = ["logs", "replay", "trace"]
