"""Research card helpers for ``ruin``."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ruin.core.domain import Vuln

FALSE_POSITIVE_CATEGORIES: list[str] = [
    "a `call` to a known/user address with the return checked",
    "an assembly XOR (`^`) or shift flagged as `incorrect-exp` / `incorrect-shift`",
    "standard ERC20 (`transfer` / `transferFrom`) that always returns `true`",
    "a `block.timestamp` feeding a TWAP accumulator: the `uint32` wrap is a "
    "documented feature and the `MAX_TIME` guard lives in the external consumer "
    "(as in Uniswap V2)",
    "a `divide-before-multiply` in a display/string utility (base64, "
    "`toLocaleString`), not financial math",
    "an `uninitialized-local` that is set inside an assembly block",
    "a `weak-prng` that is a wall-clock time for an expiry, not a random selection",
]

REAL_BUG_CATEGORIES: list[str] = [
    "an unguarded reentrancy: an external call to an unknown contract "
    "before/after a state update, with no reentrancy guard",
    "a TWAP/oracle consumer with a missing `MAX_TIME` / `skipIfTimestampExceeded` cap",
    "a precision loss in financial math (LTV, leverage, fee, interest): "
    "divide-before-multiply",
    "an unsafe/unchecked transfer on a path that assumes it succeeded",
    "a missing access control on a state-changing function",
    "an RNG (`blockhash`, `difficulty`, `timestamp`) used for a decision an attacker "
    "or sequencer can manipulate",
]


@dataclass
class ResearchCard:
    """A research card for a finding."""

    vuln: Vuln
    mechanism: str
    sources: list[str] = field(default_factory=list)

    def with_sources(self, sources: list[str]) -> ResearchCard:
        """Set the consulted sources."""
        self.sources = sources
        return self

    def render_markdown(self) -> str:
        """Render the card as Markdown."""
        lines: list[str] = []
        lines.append(f"# Research Card — {self.vuln.summary}")
        lines.append("")
        lines.append(f"- **Mechanism:** `{self.mechanism}`")
        lines.append(f"- **Class:** `{self.vuln.klass}`")
        lines.append(f"- **Severity:** `{self.vuln.severity.value}`")
        lines.append("")
        lines.append("## Sources to consult")
        lines.append("")
        if not self.sources:
            lines.append("- (not researched yet)")
        for source in self.sources:
            lines.append(f"- {source}")
        lines.append("")
        lines.append("## Rule out (false-positive patterns)")
        lines.append("")
        for category in FALSE_POSITIVE_CATEGORIES:
            lines.append(f"- [ ] {category}")
        lines.append("")
        lines.append("## Confirm (real-bug patterns)")
        lines.append("")
        for category in REAL_BUG_CATEGORIES:
            lines.append(f"- [ ] {category}")
        lines.append("")
        lines.append(
            "> Verdict: record which pattern matched and why. Do not dismiss a "
            "finding without checking the sources and both category lists."
        )
        return "\n".join(lines)


def research_card(vuln: Vuln, mechanism: str) -> ResearchCard:
    """Build a research card for a finding."""
    return ResearchCard(vuln=vuln, mechanism=mechanism)
