"""Finding lifecycle for ``ruin``."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class FindingState(Enum):
    """Lifecycle state of a finding."""

    OPEN = "open"
    CONFIRMED = "confirmed"
    FIXED = "fixed"
    ACCEPTED_RISK = "accepted_risk"


@dataclass
class Finding:
    """A tracked security finding."""

    id: str
    title: str
    state: FindingState = FindingState.OPEN
    severity: str = ""
    confidence: int = 0
    evidence: list[str] = field(default_factory=list)
    notes: str = ""
    linked_contract: str = ""
    linked_finding: str = ""


@dataclass
class FindingRegistry:
    """A registry of findings across a session or engagement."""

    protocol: str
    findings: list[Finding] = field(default_factory=list)

    def add(self, finding: Finding) -> None:
        """Add a finding to the registry."""
        self.findings.append(finding)

    @staticmethod
    def dedupe_key(finding: Finding) -> str:
        """Return a normalized key used to collapse duplicate findings."""
        return " ".join(finding.title.lower().split())

    def dedupe(self) -> int:
        """Collapse duplicate findings, merging evidence into the first copy.

        Returns:
            The number of duplicate findings removed.
        """
        seen: dict[str, Finding] = {}
        removed = 0
        kept: list[Finding] = []
        for finding in self.findings:
            key = self.dedupe_key(finding)
            original = seen.get(key)
            if original is None:
                seen[key] = finding
                kept.append(finding)
                continue
            _merge_evidence(original, finding)
            removed += 1
        self.findings = kept
        return removed

    def merge(self, other: FindingRegistry) -> int:
        """Merge another registry in, skipping findings already present.

        Returns:
            The number of findings actually added from ``other``.
        """
        existing = {self.dedupe_key(f) for f in self.findings}
        existing_ids = {f.id for f in self.findings}
        added = 0
        for finding in other.findings:
            key = self.dedupe_key(finding)
            if key in existing or finding.id in existing_ids:
                continue
            self.findings.append(finding)
            existing.add(key)
            existing_ids.add(finding.id)
            added += 1
        return added

    def update_state(self, finding_id: str, state: FindingState) -> None:
        """Update a finding's state."""
        for f in self.findings:
            if f.id == finding_id:
                f.state = state
                return

    def render_markdown(self) -> str:
        """Render the registry as Markdown."""
        lines: list[str] = [f"# Findings — {self.protocol}", ""]
        by_state: dict[str, list[Finding]] = {}
        for f in self.findings:
            by_state.setdefault(f.state.value, []).append(f)
        for state in ("open", "confirmed", "fixed", "accepted_risk"):
            group = by_state.get(state, [])
            if not group:
                continue
            lines.append(f"## {state.replace('_', ' ').title()} ({len(group)})")
            lines.append("")
            for f in group:
                conf = f" confidence={f.confidence}" if f.confidence else ""
                lines.append(f"- **{f.id}** — {f.title}{conf}")
                if f.evidence:
                    lines.append(f"  evidence: {', '.join(f.evidence)}")
            lines.append("")
        return "\n".join(lines)


def _merge_evidence(target: Finding, source: Finding) -> None:
    """Add missing evidence items from source into target, preserving order."""
    for item in source.evidence:
        if item not in target.evidence:
            target.evidence.append(item)
