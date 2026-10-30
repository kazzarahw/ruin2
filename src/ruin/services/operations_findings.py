"""Finding-lifecycle operation handlers for ``ruin``."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ruin.core.finding import Finding
from ruin.services.findings import (
    add_finding,
    dedupe_registry,
    load_registry,
    merge_into,
    update_finding,
)


def _finding_new(kwargs: dict[str, Any]) -> str:
    path = Path(str(kwargs["file"]))
    finding = Finding(
        id=str(kwargs["id"]),
        title=" ".join(kwargs["title"])
        if isinstance(kwargs["title"], list)
        else str(kwargs["title"]),
        severity=str(kwargs.get("severity", "")),
        confidence=int(kwargs.get("confidence", 0)),
        evidence=list(kwargs.get("evidence", [])),
        linked_contract=str(kwargs.get("contract", "")),
    )
    registry = add_finding(path, finding)
    return registry.render_markdown()


def _finding_update(kwargs: dict[str, Any]) -> str:
    path = Path(str(kwargs["file"]))
    registry = update_finding(
        path,
        str(kwargs["id"]),
        str(kwargs["state"]),
        evidence=list(kwargs.get("evidence", [])) or None,
    )
    return registry.render_markdown()


def _finding_list(kwargs: dict[str, Any]) -> str:
    path = Path(str(kwargs["file"]))
    registry = load_registry(path)
    return registry.render_markdown()


def _finding_dedupe(kwargs: dict[str, Any]) -> str:
    path = Path(str(kwargs["file"]))
    registry, removed = dedupe_registry(path)
    header = f"removed {removed} duplicate finding(s)\n\n"
    return header + registry.render_markdown()


def _finding_merge(kwargs: dict[str, Any]) -> str:
    path = Path(str(kwargs["file"]))
    other = Path(str(kwargs["other"]))
    registry, added = merge_into(path, other)
    header = f"merged {added} new finding(s)\n\n"
    return header + registry.render_markdown()


FINDING_OPERATIONS: dict[str, Any] = {
    "finding-new": _finding_new,
    "finding-update": _finding_update,
    "finding-list": _finding_list,
    "finding-dedupe": _finding_dedupe,
    "finding-merge": _finding_merge,
}
