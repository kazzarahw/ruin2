"""Verified-source namespace: fetch, analyze, and triage Solidity sources."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ruin.api._call import JsonPayload, call

if TYPE_CHECKING:
    from ruin.api._requests import TriageRequest


async def fetch(
    address: str, chain: str = "EVM", chain_id: int = 1, tree: str | None = None
) -> JsonPayload | str:
    """Fetch verified sources for an address (CLI ``source fetch``)."""
    return await call(
        "source",
        {"address": address, "chain": chain, "chain_id": chain_id, "tree": tree},
    )


async def slither(source_path: str) -> JsonPayload | str:
    """Run Slither over a source file (CLI ``ruin source slither``)."""
    return await call("slither", {"source": source_path})


async def review(source_path: str) -> JsonPayload | str:
    """Guided review scaffold for a source file (CLI ``source review``)."""
    return await call("review", {"source": source_path})


async def analyze(source_path: str, name: str = "target") -> JsonPayload | str:
    """Analyze a source tree for structure (CLI ``ruin source analyze``)."""
    return await call("analyze", {"source": source_path, "name": name})


async def triage(req: TriageRequest) -> JsonPayload | str:
    """Triage checks, exploits, hypotheses, or source smells.

    The CLI route is ``ruin source triage NAME --mode MODE``; ``req.mode``
    selects checks (default), exploits, hypotheses, or source.
    """
    return await call(
        "triage",
        {
            "name": req.name,
            "mode": req.mode,
            "check": list(req.checks),
            "file": req.file,
            "source": req.source_path,
            "signal": list(req.signals),
        },
    )


async def research(
    mechanism: str, summary: list[str], sources: list[str] | None = None
) -> JsonPayload | str:
    """File a research card for one mechanism (CLI ``source research``)."""
    return await call(
        "research",
        {"mechanism": mechanism, "summary": summary, "source": sources or []},
    )


async def access_map(source_path: str) -> JsonPayload | str:
    """Build the function-by-modifier access map (CLI ``ruin source accessmap``)."""
    return await call("accessmap", {"source": source_path})


async def infra(name: str) -> JsonPayload | str:
    """Off-chain infrastructure review checklist (CLI ``source infra``)."""
    return await call("infra", {"name": name})


__all__: list[str] = [
    "access_map",
    "analyze",
    "fetch",
    "infra",
    "research",
    "review",
    "slither",
    "triage",
]
