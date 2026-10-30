"""Triage helpers for ``ruin``."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import cast

from ruin.core.enums import TriageVerdict
from ruin.core.ids import ProtocolName as ProtocolNameId
from ruin.core.slither_io import detector_fields, detectors_from
from ruin.core.smells import source_smells

SAST_NOISE_CHECKS: list[str] = [
    "unchecked-transfer",
    "arbitrary-send-erc20",
    "incorrect-exp",
    "timestamp",
    "reentrancy-balance",
    "divide-before-multiply",
    "erc20-interface",
    "unsafe-erc20",
    "used-before-initialized",
    "uninitialized-local",
    "reentrancy-events",
]

SAST_LEAD_CHECKS: list[str] = [
    "weak-prng",
    "reentrancy",
    "unprotected-initializer",
    "arbitrary-send-eth",
    "reentrancy-no-eth",
    "controlled-delegatecall",
    "suicidal",
    "lock-in-variants",
    "block-timestamp",
    "state-override-caller",
    "invariant-violation",
    "erc4626-inflation-exposed",
    "yul-calldata-dispatch",
    "wide-shift-math",
    "spot-price-oracle",
    "unprotected-exec",
]


@dataclass
class VulnTriage:
    """A triage report."""

    name: ProtocolNameId
    counts: list[tuple[str, int, TriageVerdict]] = field(default_factory=list)

    def render_markdown(self) -> str:
        """Render the triage report as Markdown."""
        lines: list[str] = []
        lines.append(f"# Vuln Triage — {self.name.as_str()}")
        lines.append("")
        lines.append("## Leads (usually real signals)")
        lines.append("")
        for check, count, verdict in self.counts:
            if verdict == TriageVerdict.LEAD:
                lines.append(f"- [ ] `{check}` x{count}")
        lines.append("")
        lines.append("## Noise (usually false-positives)")
        lines.append("")
        for check, count, verdict in self.counts:
            if verdict == TriageVerdict.NOISE:
                lines.append(f"- [ ] `{check}` x{count}")
        lines.append("")
        other = [
            (check, count)
            for check, count, verdict in self.counts
            if verdict == TriageVerdict.UNKNOWN
        ]
        if other:
            lines.append("## Other (unclassified)")
            lines.append("")
            for check, count in other:
                lines.append(f"- [ ] `{check}` x{count}")
            lines.append("")
        lines.append(
            "> The triage is the first pass: it surfaces the leads (weak-prng, "
            "unprotected-init, arbitrary-send-eth, reentrancy, "
            "controlled-delegatecall) and flags the noise (invMod Newton-Raphson, "
            "safeTransferFrom into address(this), block.timestamp rate-limits, "
            "attached-protocol reentrancies) for cross-check. A noise flag is NOT a "
            "dismiss — it is the researcher's job to confirm the specific mechanism "
            "before shipping a finding."
        )
        return "\n".join(lines)


def triage_vulns(name: str, checks: list[str]) -> VulnTriage:
    """Triages a target's slither checks."""
    counts_map: dict[str, int] = {}
    for check in checks:
        counts_map[check] = counts_map.get(check, 0) + 1
    counts: list[tuple[str, int, TriageVerdict]] = []
    for check, count in counts_map.items():
        if check in SAST_LEAD_CHECKS:
            verdict = TriageVerdict.LEAD
        elif check in SAST_NOISE_CHECKS:
            verdict = TriageVerdict.NOISE
        else:
            verdict = TriageVerdict.UNKNOWN
        counts.append((check, count, verdict))
    counts.sort(key=lambda item: (_verdict_rank(item[2]), -item[1], item[0]))
    return VulnTriage(name=ProtocolNameId.new(name), counts=counts)


def _verdict_rank(verdict: TriageVerdict) -> int:
    if verdict == TriageVerdict.LEAD:
        return 0
    if verdict == TriageVerdict.NOISE:
        return 1
    return 2


def slither_checks(json_text: str) -> list[str]:
    """Extract distinct slither check names from JSON text."""
    try:
        doc = json.loads(json_text)
    except (json.JSONDecodeError, TypeError):
        return []
    seen: set[str] = set()
    for detector in detectors_from(doc):
        if isinstance(detector, dict):
            check, _description, _impact = detector_fields(
                cast("dict[str, object]", detector)
            )
            if check:
                seen.add(check)
    return sorted(seen)


def triage_from_source(name: str, text: str) -> VulnTriage:
    """Triages a target from raw source text using smell heuristics."""
    return triage_vulns(name, source_smells(text))
