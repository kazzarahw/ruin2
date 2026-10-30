"""Solidity compiler version detection from source text."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

_EXACT_PRAGMA = re.compile(r"pragma\s+solidity\s*=\s*(\d+\.\d+\.\d+)")
_FAMILY_PRAGMA = re.compile(r"pragma\s+solidity\s*[\^<>]?\s*(\d+\.\d+)\.\d+")


_PRAGMA_LINE = re.compile(r"pragma\s+solidity\s+([^;]+);")
_PART = re.compile(r"(=|>=|>|<=|<|\^)?\s*(\d+\.\d+(?:\.\d+)?)")


_VERSION_PARTS = 3


def _version_tuple(text: str) -> tuple[int, int, int]:
    """Parse ``x.y[.z]`` into a comparable triple."""
    parts = [int(p) for p in text.split(".")[:3]]
    parts += [0] * (_VERSION_PARTS - len(parts))
    return (parts[0], parts[1], parts[2])


def _part_ok(op: str | None, want: str, have: tuple[int, int, int]) -> bool:
    """Check one constraint fragment against a concrete compiler version."""
    ver = _version_tuple(want)
    ok = False
    if op == "=":
        ok = have == ver
    elif op == ">=" or op is None:
        ok = have >= ver
    elif op == ">":
        ok = have > ver
    elif op == "<=":
        ok = have <= ver
    elif op == "<":
        ok = have < ver
    elif op == "^":
        upper = (ver[0], ver[1] + 1, 0) if ver[0] == 0 else (ver[0] + 1, 0, 0)
        ok = ver <= have < upper
    return ok


def version_satisfied(text: str, version: str) -> bool:
    """True when every pragma line in the source admits ``version``."""
    have = _version_tuple(version)
    for line in _PRAGMA_LINE.finditer(text):
        alternatives = line.group(1).split("||")
        if not any(_alternative_ok(part, have) for part in alternatives):
            return False
    return True


def _alternative_ok(constraints: str, have: tuple[int, int, int]) -> bool:
    """Check one ``||`` alternative: every fragment in it must hold (AND)."""
    found = _PART.findall(constraints)
    if not found:
        return False
    return all(_part_ok(op, want, have) for op, want in found)


def preference_from_texts(texts: Iterable[str]) -> tuple[str, str]:
    """Pick the compiler preference shared by the majority of the given sources.

    Returns ("exact", x.y.z) when one exact pin dominates, else ("family", x.y)
    from the most common major.minor across all pragma lines.
    """
    exacts: dict[str, int] = {}
    families: dict[str, int] = {}
    for text in texts:
        kind, want = version_preference(text)
        if kind == "exact":
            exacts[want] = exacts.get(want, 0) + 1
            fam = ".".join(want.split(".")[:2])
            families[fam] = families.get(fam, 0) + 1
        elif kind == "family":
            families[want] = families.get(want, 0) + 1
    if not families:
        return ("none", "")
    top_fam = max(families, key=lambda k: families[k])
    total = sum(families.values())
    best = max(exacts, key=lambda k: exacts[k]) if exacts else ""
    if best and best.startswith(top_fam) and exacts[best] * 2 > total:
        return ("exact", best)
    return ("family", top_fam)


def version_preference(text: str) -> tuple[str, str]:
    """Return how the source pins its compiler: ("exact", x.y.z) or ("family", x.y).

    Returns ("none", "") when no pragma line is present.
    """
    exact = _EXACT_PRAGMA.search(text)
    if exact:
        return ("exact", str(exact.group(1)))
    family = _FAMILY_PRAGMA.search(text)
    if family:
        return ("family", str(family.group(1)))
    return ("none", "")
