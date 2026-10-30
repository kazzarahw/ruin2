"""Slither service for ``ruin``."""

from __future__ import annotations

import re
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from ruin.core.slither_io import parse_slither
from ruin.core.solc import version_satisfied
from ruin.services.solc import pick_solc
from ruin.services.subprocesses import run_command, slither_command

if TYPE_CHECKING:
    from ruin.core.domain import Vuln

_SOLC_VERSION = re.compile(r"(\d+\.\d+\.\d+)")


def _stage_tree(source: Path, solc: str) -> Path:
    """Copy only pragma-compatible files of a tree into a staging directory.

    Mixed-pragma trees (a stray =0.7.6 library among ^0.8.x contracts) make
    solc abort with no output; staging keeps the analysis running on the
    majority-compatible subset.
    """
    match = _SOLC_VERSION.search(solc)
    stage = Path(tempfile.mkdtemp(prefix="ruin-slither-"))
    for sol in sorted(source.rglob("*.sol")):
        text = sol.read_text(encoding="utf-8", errors="replace")
        if not match or version_satisfied(text, match.group(1)):
            dest = stage / sol.relative_to(source)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(text, encoding="utf-8")
    return stage


def run_slither(source: Path) -> list[Vuln]:
    """Run slither over a source file or tree, pinning the pragma's solc.

    Solc auto-selection is unreliable on hosts without solc-select wired, so
    the compiler is resolved from the source pragma (svm cache, then download).
    """
    solc = pick_solc(source)
    target = _stage_tree(source, solc) if source.is_dir() else source
    process = run_command(slither_command(str(target), solc), timeout=120.0)
    if not process.stdout.strip():
        tail = process.stderr.strip()[-200:]
        raise RuntimeError(
            f"slither produced no JSON on stdout (exit {process.returncode}): {tail}"
        )
    return parse_slither(process.stdout)
