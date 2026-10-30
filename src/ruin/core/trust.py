"""Trust model helpers for ``ruin``."""

from __future__ import annotations

from dataclasses import dataclass, field

from ruin.core.ids import ProtocolName

TRUST_ROLES: list[str] = [
    "operator",
    "owner",
    "governor",
    "admin",
    "keeper",
    "pauser",
    "multisig",
]


@dataclass
class TrustAssumption:
    """A trust assumption in a protocol."""

    role: str
    flow: str
    bounded: bool


@dataclass
class TrustModel:
    """A trust assessment."""

    name: ProtocolName
    assumptions: list[TrustAssumption] = field(default_factory=list)
    _custodial: bool = False

    def with_assumption(self, role: str, flow: str, bounded: bool) -> TrustModel:
        """Add a trust assumption."""
        self.assumptions.append(TrustAssumption(role=role, flow=flow, bounded=bounded))
        return self

    def custodial(self, custodial: bool) -> TrustModel:
        """Mark the protocol as custodial."""
        self._custodial = custodial
        return self

    def render_markdown(self) -> str:
        """Render the trust model as Markdown."""
        lines: list[str] = []
        lines.append(f"# Trust Model — {self.name.as_str()}")
        lines.append("")
        lines.append(f"- **Custodial / trusted:** {self._custodial}")
        lines.append("")
        lines.append("## Trust assumptions")
        lines.append("")
        for assumption in self.assumptions:
            bound = "bounded" if assumption.bounded else "UNBOUNDED"
            lines.append(f"- **`{assumption.role}`** — {assumption.flow} ({bound})")
        lines.append("")
        lines.append("## Roles to expose")
        lines.append("")
        for role in TRUST_ROLES:
            lines.append(f"- [ ] {role}")
        lines.append("")
        lines.append(
            "> Verdict: an explicitly custodial protocol (a trusted operator / owner) "
            "has a custodial surface, not a contract-bug surface. A working PoC on a "
            "trusted-operator flow is a trust violation (the operator acts), not a "
            "code defect. Distinguish the bounded delta (a `revert` cap) from an "
            "unbounded flow (a drain)."
        )
        return "\n".join(lines)


def trust_model(name: str) -> TrustModel:
    """Record a trust assessment."""
    return TrustModel(name=ProtocolName.new(name))
