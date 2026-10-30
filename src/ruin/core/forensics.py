"""Forensics value objects for ``ruin``."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import cast

_MAX_DISPLAY = 50


@dataclass
class TransactionTrace:
    """A decoded transaction trace."""

    tx_hash: str
    steps: list[str] = field(default_factory=list)
    note: str = ""

    def render_markdown(self) -> str:
        """Render the trace as Markdown (note-aware)."""
        lines: list[str] = [f"# Trace — {self.tx_hash}", ""]
        if self.note:
            lines.append(f"> {self.note}")
            lines.append("")
        lines.extend(f"- {step}" for step in self.steps)
        return "\n".join(lines)


@dataclass
class LogEntry:
    """A single decoded event log."""

    address: str
    block: int
    tx_hash: str
    event_signature: str
    indexed: list[str] = field(default_factory=list)
    data: str = ""


@dataclass
class LogScan:
    """Result of scanning event logs for a contract."""

    address: str
    from_block: int
    to_block: int
    entries: list[LogEntry] = field(default_factory=list)

    def render_markdown(self) -> str:
        """Render the log scan as Markdown."""
        lines: list[str] = [
            f"# Log Scan — {self.address}",
            "",
            f"Blocks: {self.from_block} - {self.to_block}",
            f"Events found: {len(self.entries)}",
            "",
        ]
        for entry in self.entries[:_MAX_DISPLAY]:
            lines.append(
                f"- Block {entry.block}: `{entry.event_signature}`"
                f" tx `{entry.tx_hash[:16]}...`"
            )
        if len(self.entries) > _MAX_DISPLAY:
            lines.append(f"- … and {len(self.entries) - _MAX_DISPLAY} more")
        return "\n".join(lines)


def flatten_call_trace(node: dict[str, object], depth: int = 0) -> list[str]:
    """Flatten a callTracer call tree into indented one-line call steps.

    Args:
        node: A callTracer node (type/from/to/input/error/calls fields).
        depth: Indentation level for nested internal calls.

    Returns:
        One string per call, ordered as the EVM executed them.
    """
    kind = str(node.get("type", "CALL"))
    sender = str(node.get("from", "?"))
    receiver = str(node.get("to", "?"))
    selector = str(node.get("input", ""))[:10] or "0x"
    error = " [reverted]" if node.get("error") else ""
    lines = [f"{'  ' * depth}{kind} {sender} -> {receiver} {selector}{error}"]
    calls = node.get("calls")
    if isinstance(calls, list):
        for call in calls:
            if isinstance(call, dict):
                lines.extend(
                    flatten_call_trace(cast("dict[str, object]", call), depth + 1)
                )
    return lines
