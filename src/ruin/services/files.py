"""File helpers for ``ruin``."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from ruin.core.recon import ReconEntry, parse_recon
from ruin.core.slither_io import parse_vulns

if TYPE_CHECKING:
    from ruin.core.domain import Vuln


def read_recon(path: Path) -> list[ReconEntry]:
    """Read a recon JSON file into entries."""
    raw = path.read_text(encoding="utf-8")
    return parse_recon(raw)


def read_vulns(path: Path) -> list[Vuln]:
    """Read a vulns JSON file into vuln candidates."""
    raw = path.read_text(encoding="utf-8")
    return parse_vulns(raw)


def write_text(path: Path, content: str) -> None:
    """Write text to a file."""
    path.write_text(content, encoding="utf-8")


def write_or_render(out: object, content: str) -> str:
    """Write ``content`` to ``out`` when given, else return the content."""
    if out is None:
        return content
    write_text(Path(str(out)), content)
    return f"wrote {out}"
