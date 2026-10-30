"""Finding persistence and operations for ``ruin``."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

from ruin.core.finding import Finding, FindingRegistry, FindingState


def load_registry(path: Path) -> FindingRegistry:
    """Load a finding registry from a JSON file."""
    text = path.read_text(encoding="utf-8").strip()
    raw = json.loads(text) if text else {}
    protocol = str(raw.get("protocol", ""))
    findings: list[Finding] = []
    for item in raw.get("findings", []):
        findings.append(
            Finding(
                id=str(item.get("id", "")),
                title=str(item.get("title", "")),
                state=FindingState(str(item.get("state", "open"))),
                severity=str(item.get("severity", "")),
                confidence=int(item.get("confidence", 0)),
                evidence=list(item.get("evidence", [])),
                notes=str(item.get("notes", "")),
                linked_contract=str(item.get("linked_contract", "")),
                linked_finding=str(item.get("linked_finding", "")),
            )
        )
    return FindingRegistry(protocol=protocol, findings=findings)


def save_registry(registry: FindingRegistry, path: Path) -> None:
    """Save a finding registry to a JSON file."""
    data: dict[str, Any] = {
        "protocol": registry.protocol,
        "findings": [
            {
                "id": f.id,
                "title": f.title,
                "state": f.state.value,
                "severity": f.severity,
                "confidence": f.confidence,
                "evidence": f.evidence,
                "notes": f.notes,
                "linked_contract": f.linked_contract,
                "linked_finding": f.linked_finding,
            }
            for f in registry.findings
        ],
    }
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def add_finding(
    path: Path,
    finding: Finding,
) -> FindingRegistry:
    """Add a finding to a registry file."""
    registry = load_registry(path) if path.exists() else FindingRegistry(protocol="")
    registry.add(finding)
    save_registry(registry, path)
    return registry


def update_finding(
    path: Path, fid: str, state: str, evidence: list[str] | None = None
) -> FindingRegistry:
    """Update a finding's state and optionally add evidence."""
    registry = load_registry(path)
    new_state = FindingState(state)
    registry.update_state(fid, new_state)
    if evidence:
        for f in registry.findings:
            if f.id == fid:
                f.evidence.extend(evidence)
    save_registry(registry, path)
    return registry


def dedupe_registry(path: Path) -> tuple[FindingRegistry, int]:
    """Collapse duplicate findings in a registry file.

    Args:
        path: The registry JSON file.

    Returns:
        A ``(registry, removed_count)`` pair after saving.
    """
    registry = load_registry(path)
    removed = registry.dedupe()
    save_registry(registry, path)
    return registry, removed


def merge_into(path: Path, other_path: Path) -> tuple[FindingRegistry, int]:
    """Merge another registry file into this one, skipping duplicates.

    Args:
        path: The target registry JSON file.
        other_path: The source registry JSON file to merge in.

    Returns:
        A ``(registry, added_count)`` pair after saving.
    """
    registry = load_registry(path)
    other = load_registry(other_path)
    added = registry.merge(other)
    save_registry(registry, path)
    return registry, added
