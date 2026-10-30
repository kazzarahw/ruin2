"""Hypothesis generation for security triage in ``ruin``.

Turns static-analysis checks and agent-supplied structural signals into ranked,
actionable investigation hypotheses. Pure logic; no network. Reuses the
known-exploit pattern DB so a hypothesis carries the shape of the bug to confirm.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ruin.core.enums import Severity
from ruin.core.exploits import match_patterns

if TYPE_CHECKING:
    from collections.abc import Iterable

    from ruin.core.exploits import ExploitPattern

_SEVERITY_ORDER = {
    Severity.CRITICAL: 0,
    Severity.HIGH: 1,
    Severity.MEDIUM: 2,
    Severity.LOW: 3,
    Severity.INFORMATIONAL: 4,
}

# Actionable next step keyed to a detector check name.
_TEST_BY_CHECK: dict[str, str] = {
    "reentrancy-no-eth": "fork-PoC: re-enter the target during its external call, "
    "before state update; measure drain per re-entry.",
    "reentrancy-balance": "fork-PoC: call the view getter from a malicious token "
    "callback mid-transfer; compare stale vs settled totals.",
    "weak-prng": "fork-PoC: predict/manipulate block attributes that seed "
    "selection; show attacker can force a favorable outcome.",
    "controlled-delegatecall": "fork-PoC: point the delegatecall target at an "
    "attacker contract that overwrites owner/admin slots.",
    "unprotected-initializer": "fork-PoC: call the initializer once on a fresh "
    "proxy from an attacker address and claim ownership.",
    "divide-before-multiply": "property/fuzz: compare accounting under small "
    "amounts; look for truncation that favors the protocol or the attacker.",
    "unchecked-transfer": "fork-PoC: use a non-standard token that returns false "
    "or reverts on transfer; show the path assumes success.",
    "arbitrary-send-eth": "fork-PoC: call the withdraw path with an attacker "
    "recipient and no access check; drain the contract balance.",
    "block-timestamp": "fork-PoC: push spot price in the same block (flash "
    "loan) and read the oracle before the TWAP window; capture the skew.",
}

# Hypotheses triggered by structural signals the agent supplies.
_SIGNAL_HYPOTHESES: dict[str, tuple[str, Severity, str]] = {
    "oracle": (
        "Oracle staleness / price manipulation",
        Severity.HIGH,
        "Confirm the price source and its staleness bound; flash-loan a same-block "
        "price push and read before the TWAP window closes.",
    ),
    "upgradeable": (
        "Upgrade path / initializer takeover",
        Severity.HIGH,
        "Check who can upgrade and whether a fresh implementation exposes a public "
        "initializer; attempt to seize ownership on a new proxy.",
    ),
    "randomness": (
        "Manipulable randomness",
        Severity.MEDIUM,
        "Identify the randomness source; if block-derived, show an attacker can "
        "time or force a favorable draw.",
    ),
    "delegatecall": (
        "Delegatecall into untrusted code",
        Severity.HIGH,
        "Trace every delegatecall target; if user/owner-settable, run attacker code "
        "in context and overwrite storage.",
    ),
    "no-access-control": (
        "Missing access control on value-moving functions",
        Severity.HIGH,
        "Enumerate state-changing functions with no modifier; call each from a "
        "random address and see which move funds or change authority.",
    ),
    "flash-loan": (
        "Flash-loan-amplified imbalance",
        Severity.HIGH,
        "Wrap the target interaction in a flash loan; check whether a large "
        "transient balance flips invariants the contract assumes are durable.",
    ),
}


@dataclass
class Hypothesis:
    """A single ranked investigation hypothesis."""

    title: str
    severity: Severity
    rationale: str
    test: str

    def render_markdown(self) -> str:
        """Render the hypothesis as Markdown."""
        return "\n".join(
            [
                f"## {self.title} ({self.severity.value})",
                "",
                f"- why: {self.rationale}",
                f"- test: {self.test}",
                "",
            ]
        )


@dataclass
class HypothesisSet:
    """A ranked set of hypotheses for one target."""

    name: str
    items: list[Hypothesis] = field(default_factory=list)

    def render_markdown(self) -> str:
        """Render the whole set as a Markdown triage brief."""
        lines: list[str] = [f"# Hypotheses — {self.name}", ""]
        if not self.items:
            lines.append("No hypotheses: no matching checks or signals.")
            return "\n".join(lines)
        for item in self.items:
            lines.append(item.render_markdown())
        return "\n".join(lines)


def _from_patterns(patterns: Iterable[ExploitPattern]) -> list[Hypothesis]:
    out: list[Hypothesis] = []
    for pattern in patterns:
        test = _TEST_BY_CHECK.get(
            pattern.check, "fork-PoC: reproduce the mechanism and measure the drain."
        )
        out.append(
            Hypothesis(
                title=pattern.title,
                severity=pattern.severity,
                rationale=pattern.mechanism,
                test=test,
            )
        )
    return out


def _from_signals(signals: Iterable[str]) -> list[Hypothesis]:
    out: list[Hypothesis] = []
    for signal in signals:
        entry = _SIGNAL_HYPOTHESES.get(signal.strip().lower())
        if entry is not None:
            title, severity, test = entry
            out.append(
                Hypothesis(
                    title=title,
                    severity=severity,
                    rationale=f"agent flagged structural signal: {signal.lower()}",
                    test=test,
                )
            )
    return out


def _rank(items: list[Hypothesis]) -> list[Hypothesis]:
    return sorted(items, key=lambda h: _SEVERITY_ORDER[h.severity])


def build_hypotheses(
    name: str, checks: list[str], signals: Iterable[str] = ()
) -> HypothesisSet:
    """Build a ranked, de-duplicated hypothesis set from checks and signals."""
    items = _from_patterns(match_patterns(checks)) + _from_signals(signals)
    seen: set[str] = set()
    unique: list[Hypothesis] = []
    for item in items:
        if item.title not in seen:
            seen.add(item.title)
            unique.append(item)
    return HypothesisSet(name=name, items=_rank(unique))
