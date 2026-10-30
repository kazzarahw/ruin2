"""Bytecode and uint decoding for ``ruin``."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache

_MIN_STRING_LENGTH = 4
_SELECTOR_LENGTH = 8
_WORD_HEX_LENGTH = 64
_MAX_UINT_HEX_LENGTH = 32
_HEX_DIGITS = "0123456789abcdefABCDEF"


@dataclass
class DecodedBytecode:
    """A decoded view of deployed contract bytecode or calldata."""

    selectors: list[str] = field(default_factory=list)
    strings: list[str] = field(default_factory=list)
    format: str = "evm"
    args: list[str] = field(default_factory=list)


def decode_uint(word: str) -> int:
    """Decode a 0x-prefixed 256-bit hex word into a u128 (low 128 bits)."""
    if not word.startswith("0x"):
        raise ValueError(f"invalid uint word {word!r}")
    hex_part = word[2:]
    trimmed = hex_part.lstrip("0")
    if not trimmed:
        return 0
    if len(trimmed) > _MAX_UINT_HEX_LENGTH:
        raise ValueError(f"invalid uint word {word!r}")
    try:
        return int(trimmed, 16)
    except ValueError as error:
        raise ValueError(f"invalid uint word {word!r}") from error


def _extract_selectors(hexc: str) -> list[str]:
    selectors: list[str] = []
    seen: set[str] = set()
    i = 0
    while i < len(hexc):
        if i + 10 <= len(hexc) and hexc[i] == "6" and hexc[i + 1] == "3":
            chunk = hexc[i + 2 : i + 10]
            if len(chunk) == _SELECTOR_LENGTH and all(
                c in "0123456789abcdefABCDEF" for c in chunk
            ):
                sel = chunk.lower()
                if sel not in seen:
                    seen.add(sel)
                    selectors.append(sel)
        i += 1
    return selectors


def _extract_strings(code: str) -> list[str]:
    strings: list[str] = []
    seen_strings: set[str] = set()
    run: list[str] = []
    for char in code:
        if char.isalnum() and char.isascii():
            run.append(char)
            continue
        if len(run) >= _MIN_STRING_LENGTH:
            candidate = "".join(run)
            if candidate not in seen_strings:
                seen_strings.add(candidate)
                strings.append(candidate)
        run = []
    if len(run) >= _MIN_STRING_LENGTH:
        candidate = "".join(run)
        if candidate not in seen_strings:
            seen_strings.add(candidate)
            strings.append(candidate)
    strings.sort(key=lambda item: -len(item))
    return strings


_FORMAT_MAGICS = {
    "0061736d": "wasm",
    "7f454c46": "elf",
    "a55c": "move",
}


def _looks_like_calldata(hexc: str) -> bool:
    """True when the hex is a 4-byte selector plus whole 32-byte words."""
    if len(hexc) <= _SELECTOR_LENGTH + _WORD_HEX_LENGTH:
        return False
    if (len(hexc) - _SELECTOR_LENGTH) % _WORD_HEX_LENGTH != 0:
        return False
    return all(c in _HEX_DIGITS for c in hexc)


def sniff_format(code: str) -> str:
    """Identify a program format from leading magic bytes.

    Returns ``wasm``, ``elf`` (BPF), ``move``, ``cairo`` (JSON), or ``evm``.
    """
    raw = code.removeprefix("0x").strip()
    if not raw:
        return "unknown"
    text = code.strip()
    if text.startswith(("{", "[")):
        return "cairo"
    lowered = raw.lower()
    for magic, fmt in _FORMAT_MAGICS.items():
        if lowered.startswith(magic):
            return fmt
    if _looks_like_calldata(lowered):
        return "calldata"
    return "evm"


def _calldata_parts(hexc: str) -> tuple[str, list[str]]:
    """Split calldata hex into its selector and 32-byte argument words."""
    selector = hexc[:_SELECTOR_LENGTH].lower()
    body = hexc[_SELECTOR_LENGTH:]
    words = [
        body[i : i + _WORD_HEX_LENGTH] for i in range(0, len(body), _WORD_HEX_LENGTH)
    ]
    return selector, words


@lru_cache(maxsize=256)
def decode_bytecode(code: str) -> DecodedBytecode:
    """Decode deployed bytecode or calldata into a structured view."""
    hexc = code.removeprefix("0x")
    fmt = sniff_format(code)
    if fmt == "calldata":
        selector, words = _calldata_parts(hexc)
        return DecodedBytecode(selectors=[selector], strings=[], format=fmt, args=words)
    selectors = _extract_selectors(hexc) if fmt == "evm" else []
    strings = [s for s in _extract_strings(code) if s.removeprefix("0x") != hexc]
    return DecodedBytecode(selectors=selectors, strings=strings, format=fmt)
