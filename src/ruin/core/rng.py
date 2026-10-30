"""RNG-hack assessment helpers for ``ruin``."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ruin.core.domain import Vuln

RNG_SOURCE_VALUES: list[str] = [
    "block.timestamp",
    "blockhash",
    "difficulty",
    "gasleft",
    "prevrandao",
]

RNG_MANIPULATORS: list[str] = [
    "attacker (flash loan / front-running)",
    "sequencer (L2 order/timestamp control)",
    "miner/proposer (timestamp ±15s, prevrandao)",
    "none (embedded entropy / off-chain)",
]


@dataclass
class RngHackAssessment:
    """An assessment of a potential RNG-hack."""

    vuln: Vuln
    mechanism: str
    source_value: str
    decision: str = ""
    manipulable_by: str = ""

    def with_decision(self, decision: str) -> RngHackAssessment:
        """Set the decision the value feeds."""
        self.decision = decision
        return self

    def with_manipulator(self, manipulable_by: str) -> RngHackAssessment:
        """Set who can manipulate the source value."""
        self.manipulable_by = manipulable_by
        return self

    def render_markdown(self) -> str:
        """Render the assessment as Markdown."""
        lines: list[str] = []
        lines.append(f"# RNG-Hack Assessment — {self.vuln.summary}")
        lines.append("")
        lines.append(f"- **Mechanism:** `{self.mechanism}`")
        lines.append(f"- **Source value:** `{self.source_value}`")
        lines.append(f"- **Feeds decision:** {self.decision}")
        lines.append(f"- **Manipulable by:** {self.manipulable_by}")
        lines.append("")
        lines.append("## Is it a TWAP / time-accumulator (usually NOT a hack)?")
        lines.append("")
        lines.append("- [ ] cumulative price/time accumulator")
        lines.append("")
        lines.append("## Is it a manipulable decision path?")
        lines.append("")
        for source in RNG_SOURCE_VALUES:
            lines.append(f"- [ ] derives from `{source}`")
        lines.append("")
        for manipulator in RNG_MANIPULATORS:
            lines.append(f"- [ ] {manipulator}")
        lines.append("")
        lines.append(
            "> Verdict: if the value feeds a *winner/order/expiry* decision an "
            "actor can influence, it is a genuine RNG-hack — not the `weak-prng` "
            "false-positive. Document the source value, the decision, and who "
            "can manipulate it."
        )
        return "\n".join(lines)


def rng_hack_assessment(
    vuln: Vuln, mechanism: str, source_value: str
) -> RngHackAssessment:
    """Build an RNG-hack assessment for a finding."""
    return RngHackAssessment(vuln=vuln, mechanism=mechanism, source_value=source_value)
