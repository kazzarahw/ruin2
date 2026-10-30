"""Screen verdict value objects shared by text and JSON output."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ruin.core.probe import SelectorRow


@dataclass(frozen=True)
class CtokenScreen:
    """cToken donation-inflation screen verdict with its rate evidence.

    ``rate_bump_pct`` and the cycle fields stay ``None`` when the screen
    ended before measuring exposure (fork down, market unreadable).
    """

    address: str
    verdict: str
    signals: tuple[str, ...] = ()
    rate_bump_pct: float | None = None
    cycle_profitable: bool | None = None
    cycle_net_raw: int | None = None

    def render_markdown(self) -> str:
        """Render the screen verdict exactly as the CLI text output does."""
        lines: list[str] = [
            f"# cToken inflation — {self.address}",
            "",
            f"- verdict: {self.verdict}",
        ]
        if self.rate_bump_pct is not None:
            lines.append(f"- rate bump pct: {self.rate_bump_pct}")
            lines.append(f"- cycle profitable: {self.cycle_profitable}")
        if self.signals:
            lines.append("- signals: " + ", ".join(self.signals))
        return "\n".join(lines)


@dataclass(frozen=True)
class MintSigReport:
    """Signature-gated mint surface screen verdict and its flags."""

    address: str
    rpc: str
    sig_mint: tuple[SelectorRow, ...] = ()
    owner: str = ""
    owner_eoa: bool = False
    cap_getter_present: bool = False
    cap_saturated: bool = False
    verdict: str = "clean"
    flags: tuple[str, ...] = ()

    def render_markdown(self) -> str:
        """Render the screen as Markdown."""
        lines: list[str] = [
            f"# Sig-mint screen — {self.address}",
            "",
            f"- rpc: {self.rpc}",
            f"- verdict: {self.verdict}",
        ]
        lines += ["", "## Flags", ""]
        lines += [f"- {flag}" for flag in self.flags] or ["- (none)"]
        lines += ["", "## Sig-gated mint surface", ""]
        lines += [
            f"- `{row.selector}` {row.signature}".rstrip() for row in self.sig_mint
        ] or ["- (none)"]
        lines.append(f"- owner: {self.owner or '(unreadable)'} (EOA: {self.owner_eoa})")
        lines.append(
            f"- cap getter present: {self.cap_getter_present} "
            f"(saturated: {self.cap_saturated})"
        )
        return "\n".join(lines)
