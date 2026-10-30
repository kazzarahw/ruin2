"""Standard-json compile helpers for the protocol service.

Stages a source bundle on disk, mirrors bundle keys under Sourcify
remapping prefixes, and runs pragma-pinned solc for ASTs. Keeping the solc
plumbing here leaves ``ruin.services.protocol`` free for resolution and
surface ranking.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

from ruin.core.sources import split_bundle
from ruin.services.solc import ensure_solc, pick_solc
from ruin.services.subprocesses import run_command


def alias_files(files: dict[str, str], remappings: tuple[str, ...]) -> dict[str, str]:
    """Duplicate bundle keys so remapped import prefixes resolve in solc.

    For each ``ctx=path`` remapping, every file keyed ``path/<rest>`` is
    mirrored under ``ctx/<rest>``; original keys are always kept.
    """
    out = dict(files)
    for entry in remappings:
        ctx, sep, path = entry.partition("=")
        if not sep or not ctx or not path:
            continue
        prefix = f"{path.rstrip('/')}/"
        alias = f"{ctx.rstrip('/')}/"
        for key, content in files.items():
            if key.startswith(prefix):
                out.setdefault(alias + key[len(prefix) :], content)
    return out


def bundle_files(name: str, text: str, remappings: tuple[str, ...]) -> dict[str, str]:
    """Split a concatenated source bundle, or wrap a lone source by name."""
    files = dict(split_bundle(text))
    if not files:
        entry = name if name.endswith(".sol") else f"{name}.sol"
        files = {entry: text}
    return alias_files(files, remappings)


def compile_asts(
    name: str,
    text: str,
    remappings: tuple[str, ...] = (),
    compiler_version: str = "",
) -> dict[str, dict[str, Any]]:
    """Run standard-json solc; return {source: ast}.

    Prefers the exact compiler version recorded in Sourcify metadata (the
    binary that produced the verified deployment), falling back to pragma
    preference from the entry file.
    """
    files = bundle_files(name, text, remappings)
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        for path, content in files.items():
            target = root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        entry = next((p for p in files if p.endswith(".sol")), None)
        solc = ensure_solc(compiler_version) if compiler_version else ""
        if not solc:
            solc = pick_solc(root / entry) if entry else ""
        if not solc:
            return {}
        payload = {
            "language": "Solidity",
            "sources": {path: {"content": content} for path, content in files.items()},
            "settings": {"outputSelection": {"*": {"": ["ast"]}}},
        }
        input_path = Path(tmp) / "input.json"
        input_path.write_text(json.dumps(payload), encoding="utf-8")
        proc = run_command([solc, "--standard-json", str(input_path)], timeout=120.0)
        return _asts(proc.stdout)


def _asts(stdout: str) -> dict[str, dict[str, Any]]:
    """Extract per-source ASTs from solc standard-json output."""
    try:
        doc = json.loads(stdout)
    except json.JSONDecodeError:
        return {}
    sources = doc.get("sources") if isinstance(doc, dict) else None
    if not isinstance(sources, dict):
        return {}
    return {
        str(key): value["ast"]
        for key, value in sources.items()
        if isinstance(value, dict) and isinstance(value.get("ast"), dict)
    }
