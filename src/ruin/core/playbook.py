"""Playbook data model for ``ruin``."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PlaybookStep:
    """One step in a playbook."""

    operation: str
    params: dict[str, str] = field(default_factory=dict)


@dataclass
class Playbook:
    """A named, reusable research workflow."""

    name: str
    description: str = ""
    steps: list[PlaybookStep] = field(default_factory=list)
    params: list[str] = field(default_factory=list)

    def render_markdown(self) -> str:
        """Render the playbook as Markdown."""
        lines: list[str] = [f"# Playbook — {self.name}", ""]
        if self.description:
            lines.append(self.description)
            lines.append("")
        if self.params:
            lines.append(f"Parameters: {', '.join(self.params)}")
            lines.append("")
        lines.append("## Steps")
        lines.append("")
        for i, step in enumerate(self.steps, 1):
            param_str = ""
            if step.params:
                items = ", ".join(f"{k}={v}" for k, v in step.params.items())
                param_str = f" ({items})"
            lines.append(f"{i}. operation `{step.operation}`{param_str}")
        return "\n".join(lines)
