"""Symbolic execution result helpers for ``ruin``."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ruin.core.enums import SymbolicOutcome
from ruin.core.fuzz import Counterexample

__all__ = ["Counterexample", "SymbolicOutcome", "SymbolicResult", "symbolic_result"]


@dataclass
class SymbolicResult:
    """A symbolic execution result."""

    target: str
    tool: str
    outcome: SymbolicOutcome
    detail: str = ""
    counterexample: Counterexample | None = None
    counterexamples: list[Counterexample] = field(default_factory=list)
    skipped: bool = False
    finding: str | None = None
    linked_finding: str | None = None
    finding_id: str | None = None
    linked_findings: list[str] = field(default_factory=list)
    vuln: Any = None

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

    def with_detail(self, detail: str) -> SymbolicResult:
        """Set the detail."""
        self.detail = detail
        return self

    def with_counterexample(self, counterexample: Counterexample) -> SymbolicResult:
        """Attach a structured counterexample."""
        self.counterexample = counterexample
        if counterexample not in self.counterexamples:
            self.counterexamples.append(counterexample)
        return self

    def with_finding(self, finding: str) -> SymbolicResult:
        """Link this result to a finding."""
        self.finding = finding
        self.linked_finding = finding
        self.finding_id = finding
        if finding not in self.linked_findings:
            self.linked_findings.append(finding)
        return self

    def with_linked_finding(self, finding: str) -> SymbolicResult:
        """Alias for ``with_finding``."""
        return self.with_finding(finding)

    def render_markdown(self) -> str:
        """Render the symbolic result as Markdown."""
        lines: list[str] = []
        lines.append(f"# Symbolic — {self.target}")
        lines.append("")
        lines.append(f"- **Tool:** {self.tool}")
        lines.append(f"- **Outcome:** {self.outcome.value}")
        if self.detail:
            lines.append(f"- **Detail:** {self.detail}")
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
        return "\n".join(lines)


def symbolic_result(target: str, tool: str, outcome: SymbolicOutcome) -> SymbolicResult:
    """Record a symbolic result."""
    return SymbolicResult(target=target, tool=tool, outcome=outcome)
