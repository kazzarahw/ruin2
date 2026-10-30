"""Access-control analysis helpers for ``ruin``."""

from __future__ import annotations

from dataclasses import dataclass, field

KNOWN_MODIFIERS = [
    "onlyOwner",
    "onlyAdmin",
    "onlyRole",
    "onlyGovernance",
    "onlyTimelock",
    "onlyGuardian",
    "onlyPauser",
    "onlyKeeper",
    "whenNotPaused",
    "nonReentrant",
    "onlyProxyAdmin",
    "onlyUUPSAdmin",
]


@dataclass
class FunctionAccess:
    """Access-control classification for one function."""

    name: str
    visibility: str = "external"
    modifiers: list[str] = field(default_factory=list)
    is_guarded: bool = False
    state_changing: bool = False


@dataclass
class AccessMap:
    """A function-level access-control map for a contract."""

    contract: str
    functions: list[FunctionAccess] = field(default_factory=list)

    def render_markdown(self) -> str:
        """Render the access map as Markdown."""
        lines: list[str] = [f"# Access Map — {self.contract}", ""]
        unguarded = [f for f in self.functions if not f.is_guarded and f.state_changing]
        lines.append(f"Functions: {len(self.functions)}")
        lines.append(f"Unguarded state-changing: {len(unguarded)}")
        lines.append("")
        lines.append("| Function | Visibility | Modifiers | Guarded | State-changing |")
        lines.append("|----------|-----------|-----------|---------|----------------|")
        for fn in self.functions:
            guards = ", ".join(fn.modifiers) if fn.modifiers else "—"
            g = "yes" if fn.is_guarded else "**NO**"
            sc = "yes" if fn.state_changing else "no"
            lines.append(f"| {fn.name} | {fn.visibility} | {guards} | {g} | {sc} |")
        lines.append("")
        lines.append("> Unguarded state-changing functions are audit targets.")
        return "\n".join(lines)


def classify_function(
    name: str, visibility: str, modifiers: list[str], state_changing: bool
) -> FunctionAccess:
    """Classify one function's access-control posture."""
    known = [m for m in modifiers if m in KNOWN_MODIFIERS]
    guarded = bool(known) or any(
        m for m in modifiers if m.startswith(("only", "require"))
    )
    return FunctionAccess(
        name=name,
        visibility=visibility,
        modifiers=modifiers,
        is_guarded=guarded,
        state_changing=state_changing,
    )
