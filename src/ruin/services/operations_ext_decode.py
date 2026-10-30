"""Offline decode helpers for the ``bytecode selectors`` positional.

Bytecode, calldata, or a bare 4-byte selector given as a file path or a
literal ``0x`` string is decoded here without touching the chain. The former
standalone ``decode`` operation now lives behind ``bytecode selectors``.
"""

from __future__ import annotations

import re
from pathlib import Path

from ruin.core.decode import decode_bytecode
from ruin.services.http import resolve_selectors
from ruin.services.serialize import to_dict

_SELECTOR_RE = re.compile(r"^0x[0-9a-fA-F]{8}$")


def read_code(raw: str) -> str:
    """Return the code a positional points at: file content, else the literal."""
    path = Path(raw)
    return path.read_text(encoding="utf-8").strip() if path.exists() else raw


def _selector_text(selector: str) -> str:
    """Render possible signatures for a bare 4-byte selector."""
    clean = selector[2:].lower()
    lines = ["format: selector", "selectors: 1", f"  0x{clean}"]
    sig = resolve_selectors([clean]).get(clean, "")
    lines.append(f"  match: {sig}" if sig else "  match: unknown")
    return "\n".join(lines)


def decode_text(raw: str, resolve: bool) -> str:
    """Render an offline decode of bytecode, calldata, or a bare selector."""
    code = read_code(raw)
    if _SELECTOR_RE.match(code):
        return _selector_text(code)
    decoded = decode_bytecode(code)
    lines = [f"format: {decoded.format}", f"selectors: {len(decoded.selectors)}"]
    resolved: dict[str, str] = {}
    if resolve and decoded.selectors:
        resolved = resolve_selectors(decoded.selectors[:40])
    for selector in decoded.selectors[:40]:
        sig = resolved.get(selector, "")
        suffix = f"  {sig}" if sig else ""
        lines.append(f"  0x{selector}{suffix}")
    for index, word in enumerate(decoded.args[:8]):
        lines.append(f"  arg{index}: 0x{word}")
    lines.append(f"strings: {len(decoded.strings)}")
    lines.extend(f"  {s}" for s in decoded.strings[:15])
    return "\n".join(lines)


def decode_data(raw: str) -> object:
    """Build the decode JSON payload for a file path or literal."""
    code = read_code(raw)
    if _SELECTOR_RE.match(code):
        clean = code[2:].lower()
        return {"format": "selector", "selectors": [clean], "strings": [], "args": []}
    return to_dict(decode_bytecode(code))
