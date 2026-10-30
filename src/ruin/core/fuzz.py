"""Fuzz result helpers for ``ruin``."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ruin.core.enums import FuzzKind, FuzzOutcome

FUZZ_INVARIANTS: list[str] = [
    "total minted + total burned == total supply (vault)",
    "total collateral >= total debt * minCollateralRatio (CDP)",
    "reserve * price is conserved up to fees (AMM)",
    "after a deposit/withdraw round-trip, balance is unchanged",
    "no negative user balances",
    "the invariant solvers agree with the on-chain state",
]


@dataclass
class Counterexample:
    """A structured fuzz counterexample."""

    summary: str = ""
    inputs: dict[str, Any] = field(default_factory=dict)
    trace: list[str] = field(default_factory=list)
    raw: str = ""

    def render_markdown(self) -> str:
        """Render the counterexample as Markdown."""
        lines: list[str] = []
        if self.summary:
            lines.append(self.summary)
        if self.inputs:
            lines.append(f"inputs: {self.inputs}")
        for entry in self.trace:
            lines.append(f"  - {entry}")
        if self.raw and not self.summary:
            lines.append(self.raw)
        return "\n".join(lines)


@dataclass
class FuzzResult:
    """A fuzz result."""

    target: str
    kind: FuzzKind
    outcome: FuzzOutcome
    detail: str = ""
    counterexample: Counterexample | None = None
    counterexamples: list[Counterexample] = field(default_factory=list)
    skipped: bool = False
    finding: str | None = None
    linked_finding: str | None = None
    finding_id: str | None = None
    vuln: Any = None
    linked_findings: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Sync aliases and aggregate counterexamples."""
        if (
            self.counterexample is not None
            and self.counterexample not in self.counterexamples
        ):
            self.counterexamples.append(self.counterexample)
        resolved = self.finding or self.linked_finding or self.finding_id
        if resolved is not None:
            if self.finding is None:
                self.finding = resolved
            if self.linked_finding is None:
                self.linked_finding = resolved
            if self.finding_id is None:
                self.finding_id = resolved
            if resolved not in self.linked_findings:
                self.linked_findings.append(resolved)

    @property
    def counter_example(self) -> Counterexample | None:
        """Alias for ``counterexample``."""
        return self.counterexample

    def with_detail(self, detail: str) -> FuzzResult:
        """Set the counter-example / error detail."""
        self.detail = detail
        return self

    def with_counterexample(self, counterexample: Counterexample) -> FuzzResult:
        """Attach a structured counterexample."""
        self.counterexample = counterexample
        if counterexample not in self.counterexamples:
            self.counterexamples.append(counterexample)
        return self

    def with_finding(self, finding: str) -> FuzzResult:
        """Link this result to a finding."""
        self.finding = finding
        self.linked_finding = finding
        self.finding_id = finding
        if finding not in self.linked_findings:
            self.linked_findings.append(finding)
        return self

    def with_linked_finding(self, finding: str) -> FuzzResult:
        """Alias for ``with_finding``."""
        return self.with_finding(finding)

    def render_markdown(self) -> str:
        """Render the fuzz result as Markdown."""
        lines: list[str] = []
        lines.append(f"# Fuzz — {self.target}")
        lines.append("")
        lines.append(f"- **Kind:** {self.kind.value}")
        lines.append(f"- **Outcome:** {self.outcome.value}")
        if self.detail:
            lines.append(f"- **Counter-example / detail:** {self.detail}")
        if self.counterexample is not None:
            label = self.counterexample.summary or self.counterexample.raw
            if label:
                lines.append(f"- **Counterexample:** {label}")
            if self.counterexample.inputs:
                lines.append(f"- **Inputs:** {self.counterexample.inputs}")
            for entry in self.counterexample.trace:
                lines.append(f"  - {entry}")
        if self.skipped:
            lines.append("- **Skipped:** true")
        if self.linked_finding is not None or self.finding is not None:
            value = self.linked_finding or self.finding
            lines.append(f"- **Linked finding:** {value}")
        lines.append("")
        lines.append("## Invariants to conserve")
        lines.append("")
        for invariant in FUZZ_INVARIANTS:
            lines.append(f"- [ ] {invariant}")
        lines.append("")
        lines.append(
            "> A `Violated` footprint is a lead: it is the counter-example that "
            "pinpoints the invariant-guarantee / the fund-routing decision the "
            "bespoke math deserves manual review for."
        )
        return "\n".join(lines)


def fuzz_result(target: str, kind: FuzzKind, outcome: FuzzOutcome) -> FuzzResult:
    """Record a fuzz result."""
    return FuzzResult(target=target, kind=kind, outcome=outcome)
