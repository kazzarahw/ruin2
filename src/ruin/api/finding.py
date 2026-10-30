"""Finding namespace: the local finding registry."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ruin.api._call import JsonPayload, call

if TYPE_CHECKING:
    from ruin.api._requests import FindingDraft


async def create(draft: FindingDraft) -> JsonPayload | str:
    """Register a new finding (CLI ``ruin finding new``)."""
    return await call(
        "finding-new",
        {
            "id": draft.finding_id,
            "title": [draft.title],
            "file": draft.file,
            "severity": draft.severity,
            "confidence": draft.confidence,
            "evidence": list(draft.evidence),
            "contract": draft.contract,
        },
    )


async def update(
    finding_id: str, state: str, file: str, evidence: list[str] | None = None
) -> JsonPayload | str:
    """Move a finding to a new state (CLI ``ruin finding update``)."""
    return await call(
        "finding-update",
        {
            "id": finding_id,
            "state": state,
            "file": file,
            "evidence": list(evidence or []),
        },
    )


async def list_findings(file: str) -> JsonPayload | str:
    """List the registry (CLI ``ruin finding list``)."""
    return await call("finding-list", {"file": file})


async def dedupe(file: str) -> JsonPayload | str:
    """Collapse duplicate findings (CLI ``ruin finding dedupe``)."""
    return await call("finding-dedupe", {"file": file})


async def merge(file: str, other: str) -> JsonPayload | str:
    """Merge two finding registries (CLI ``ruin finding merge``)."""
    return await call("finding-merge", {"file": file, "other": other})


__all__: list[str] = ["create", "dedupe", "list_findings", "merge", "update"]
