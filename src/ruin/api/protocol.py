"""Protocol namespace: enumeration and modeling of deployed protocols."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ruin.api._call import JsonPayload, call

if TYPE_CHECKING:
    from ruin.api._requests import ProtocolRequest


async def resolve(req: ProtocolRequest) -> JsonPayload | str:
    """Resolve sources, proxy, and call graph (CLI ``ruin protocol resolve``)."""
    return await call(
        "resolve", {"address": req.address, "chain": req.chain, "rpc": req.rpc}
    )


async def enumerate_(req: ProtocolRequest) -> JsonPayload | str:
    """Rank the external surface (CLI ``ruin protocol enumerate``)."""
    return await call(
        "enumerate", {"address": req.address, "chain": req.chain, "rpc": req.rpc}
    )


async def model(req: ProtocolRequest) -> JsonPayload | str:
    """Render the protocol model (CLI ``ruin protocol model``)."""
    return await call(
        "model", {"address": req.address, "chain": req.chain, "rpc": req.rpc}
    )


async def invariants(
    req: ProtocolRequest, scaffold: str | None = None
) -> JsonPayload | str:
    """List candidate invariants, optionally scaffolding stubs.

    CLI equivalent: ``ruin protocol invariants [--scaffold DIR]``.
    """
    return await call(
        "invariants",
        {
            "address": req.address,
            "chain": req.chain,
            "rpc": req.rpc,
            "scaffold": scaffold,
        },
    )


__all__: list[str] = ["enumerate_", "invariants", "model", "resolve"]
