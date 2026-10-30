"""Exploit-replay timeline model for ``ruin``."""

from __future__ import annotations

from dataclasses import dataclass, field

_MAX_EVENTS = 50


@dataclass
class Timeline:
    """A fund-flow timeline reconstructed from a transaction and its logs."""

    tx_hash: str
    address: str = ""
    from_block: int = 0
    to_block: int = 0
    steps: list[str] = field(default_factory=list)
    events: list[tuple[int, str, str]] = field(default_factory=list)
    note: str = ""

    def render_markdown(self) -> str:
        """Render the timeline as Markdown for post-mortem analysis."""
        lines: list[str] = [f"# Replay — {self.tx_hash}", ""]
        if self.address:
            lines.append(f"- contract: {self.address}")
        lines.append(f"- blocks: {self.from_block} - {self.to_block}")
        if self.note:
            lines.append(f"- note: {self.note}")
        lines.append("")
        lines.append(f"## Trace steps ({len(self.steps)})")
        lines.append("")
        for step in self.steps[:100]:
            lines.append(f"- {step}")
        lines.append("")
        lines.append(f"## Events ({len(self.events)})")
        lines.append("")
        for block, tx, signature in self.events[:_MAX_EVENTS]:
            lines.append(f"- block {block}: `{signature}` tx `{tx[:16]}...`")
        if len(self.events) > _MAX_EVENTS:
            lines.append(f"- ... and {len(self.events) - _MAX_EVENTS} more")
        return "\n".join(lines)
