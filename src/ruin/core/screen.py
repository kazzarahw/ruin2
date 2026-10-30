"""Target screen helpers for ``ruin``."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ruin.core.enums import SourceAccess
from ruin.core.ids import ProtocolName

if TYPE_CHECKING:
    from ruin.core.protocols import ProtocolSummary


@dataclass
class TargetScreen:
    """A clean target screen."""

    name: ProtocolName
    chain: str
    tvl: int
    listed_unix: int | None = None
    source: SourceAccess = SourceAccess.NONE
    bespoke_layer: bool = False
    custodial: bool = False

    def with_source(self, source: SourceAccess) -> TargetScreen:
        """Set the source accessibility."""
        self.source = source
        return self

    def with_bespoke(self, bespoke_layer: bool) -> TargetScreen:
        """Set the bespoke-layer flag."""
        self.bespoke_layer = bespoke_layer
        return self

    def with_custodial(self, custodial: bool) -> TargetScreen:
        """Set the custodial flag."""
        self.custodial = custodial
        return self

    def with_listed(self, listed_unix: int) -> TargetScreen:
        """Set the listing date."""
        self.listed_unix = listed_unix
        return self

    def render_markdown(self) -> str:
        """Render the screen as Markdown."""
        lines: list[str] = []
        lines.append(f"# Target Screen — {self.name.as_str()}")
        lines.append("")
        lines.append(f"- **Chain:** {self.chain}")
        lines.append(f"- **TVL:** ${self.tvl}")
        lines.append(f"- **Source:** {self.source.value}")
        lines.append(f"- **Bespoke layer (real-bug surface):** {self.bespoke_layer}")
        lines.append(f"- **Custodial / trusted:** {self.custodial}")
        lines.append("")
        lines.append("## Screen axes")
        lines.append("")
        lines.append("- [ ] smaller TVL (the smaller-protocol preference)")
        lines.append("- [ ] new / live (recently listed)")
        lines.append("- [ ] public source (the SAST path)")
        lines.append("- [ ] bespoke layer (not a canonical, audited core)")
        lines.append("- [ ] trustless (not an explicitly custodial / trusted role)")
        lines.append("")
        lines.append(
            "> Verdict: a candidate scores highest when it is small + new + "
            "public-source + bespoke-layer + trustless. A canonical / audited core, a "
            "private / no source, a non-Solidity routing, or an explicitly custodial "
            "/ trusted role each pull the screen down — the realistic exposure then "
            "is the trust assumption, a RUG vector, a self-inflicted fund-loss flaw, "
            "or a documented not-exploitable."
        )
        return "\n".join(lines)


def target_screen(name: str, chain: str, tvl: int) -> TargetScreen:
    """Build a target screen."""
    return TargetScreen(name=ProtocolName.new(name), chain=chain, tvl=tvl)


def screen_from_protocol(summary: ProtocolSummary) -> TargetScreen:
    """Bridge a protocol summary into a target screen."""
    chain = summary.chains[0] if summary.chains else ""
    return target_screen(summary.slug, chain, summary.tvl_usd)
