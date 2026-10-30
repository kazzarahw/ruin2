"""Verify namespace: PoC pipelines, fuzzers, symbolic runs, and scaffolds."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ruin.api._call import JsonPayload, call

if TYPE_CHECKING:
    from ruin.api._requests import (
        FlashloanRequest,
        OracleRequest,
        PocRequest,
        RunnerRequest,
    )


async def poc(req: PocRequest) -> JsonPayload | str:
    """Run the fork PoC pipeline (CLI ``ruin verify poc``)."""
    return await call(
        "pipeline",
        {
            "recon_file": req.recon_file,
            "name": req.name,
            "forge_test": req.forge_test,
            "method": req.method,
            "rpc": req.rpc,
            "mode": req.mode,
            "min_tvl": req.min_tvl,
            "vulns": req.vulns,
            "fork_block": req.fork_block,
            "private_key": req.private_key,
        },
    )


async def fuzz(req: RunnerRequest) -> JsonPayload | str:
    """Record a fuzz result, or run the fuzzer when ``req.run`` is set.

    CLI route ``ruin verify fuzz``; an omitted ``req.outcome`` records as
    ``passed``, matching the CLI default.
    """
    return await call(
        "fuzz",
        {
            "target": req.target,
            "kind": req.kind,
            "outcome": req.outcome or "passed",
            "detail": req.detail,
            "run": req.run,
            "tool": req.tool or "foundry",
            "match_test": req.match_test,
            "tool_command": req.tool_command,
            "finding": req.finding,
            "linked_finding": req.linked_finding,
        },
    )


async def symbolic(req: RunnerRequest) -> JsonPayload | str:
    """Record when ``req.outcome`` is set; run the tool otherwise.

    CLI route ``ruin verify symbolic``; ``req.run`` forces the runner even
    with an outcome present.
    """
    return await call(
        "symbolic",
        {
            "target": req.target,
            "tool": req.tool or "halmos",
            "tool_command": req.tool_command,
            "outcome": req.outcome,
            "detail": req.detail,
            "finding": req.finding,
            "linked_finding": req.linked_finding,
            "run": req.run,
        },
    )


async def oracle(req: OracleRequest) -> JsonPayload | str:
    """Generate the oracle-manipulation scaffold (CLI ``ruin verify oracle``)."""
    return await call(
        "oracle",
        {
            "target": req.target,
            "rpc": req.rpc,
            "chain": req.chain,
            "router": req.router,
            "reserve_a": req.reserve_a,
            "reserve_b": req.reserve_b,
            "oracle": req.oracle,
            "swap_amount": req.swap_amount,
            "min_deviation": req.min_deviation,
        },
    )


async def flashloan(req: FlashloanRequest) -> JsonPayload | str:
    """Generate the flash-loan test scaffold (CLI ``ruin verify flashloan``)."""
    return await call(
        "flashloan",
        {
            "target": req.target,
            "rpc": req.rpc,
            "chain": req.chain,
            "asset": req.asset,
            "amount": req.amount,
            "pool": req.pool,
        },
    )


__all__: list[str] = [
    "flashloan",
    "fuzz",
    "oracle",
    "poc",
    "symbolic",
]
