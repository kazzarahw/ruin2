"""Ensure a pinned solc binary is available for slither runs."""

from __future__ import annotations

import stat
from pathlib import Path
from typing import TYPE_CHECKING, cast

import httpx

from ruin.core.solc import preference_from_texts, version_preference

if TYPE_CHECKING:
    from collections.abc import Callable

LIST_URL = "https://binaries.soliditylang.org/linux-amd64/list.json"
_MIN_BINARY_SIZE = 1_000_000
_ELF_MAGIC = b"\x7fELF"
BIN_BASE = "https://binaries.soliditylang.org/linux-amd64/"


def ensure_solc(
    version: str,
    *,
    svm_dir: Path | None = None,
    fetch_json: Callable[[str], dict[str, object]] | None = None,
    fetch_bytes: Callable[[str], bytes] | None = None,
) -> str:
    """Return a local path to solc for an exact version, downloading if absent.

    Args:
        version: Exact compiler version like "0.5.16".
        svm_dir: svm root override (defaults to ~/.svm).
        fetch_json: Injected JSON GET (for tests).
        fetch_bytes: Injected binary GET (for tests).

    Returns:
        Path string, or empty string when the version cannot be resolved.
    """
    root = svm_dir or Path.home() / ".svm"
    target = root / version / f"solc-{version}"
    if target.exists():
        return str(target)
    path = _remote_path(version, fetch_json)
    if not path:
        return ""
    blob = (fetch_bytes or _default_bytes)(BIN_BASE + path)
    if len(blob) < _MIN_BINARY_SIZE or blob[:4] != _ELF_MAGIC:
        return ""
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(blob)
    target.chmod(target.stat().st_mode | stat.S_IEXEC)
    return str(target)


def tree_preference(source: Path) -> tuple[str, str]:
    """Pick the compiler preference shared by the majority of a source tree."""
    return preference_from_texts(_tree_texts(source))


def _tree_texts(source: Path) -> list[str]:
    """Read every Solidity file in the tree, sorted for determinism."""
    return [
        sol.read_text(encoding="utf-8", errors="replace")
        for sol in sorted(source.rglob("*.sol"))
    ]


def pick_solc(
    source: Path,
    *,
    svm_dir: Path | None = None,
    fetch_json: Callable[[str], dict[str, object]] | None = None,
    fetch_bytes: Callable[[str], bytes] | None = None,
) -> str:
    """Resolve a solc binary matching the pragma pinned in the source tree/file.

    Returns empty string when no pragma is detectable.
    """
    if source.is_dir():
        kind, want = tree_preference(source)
    else:
        kind, want = version_preference(_read_source(source))
    if kind == "exact":
        return ensure_solc(
            want, svm_dir=svm_dir, fetch_json=fetch_json, fetch_bytes=fetch_bytes
        )
    if kind == "family":
        return _best_for_family(want, svm_dir, fetch_json, fetch_bytes)
    return ""


def _best_for_family(
    family: str,
    svm_dir: Path | None,
    fetch_json: Callable[[str], dict[str, object]] | None,
    fetch_bytes: Callable[[str], bytes] | None,
) -> str:
    """Pick the newest patch release within a pragma family."""
    root = svm_dir or Path.home() / ".svm"
    local = sorted(
        (d.name for d in root.glob(f"{family}.*") if (d / f"solc-{d.name}").exists()),
        key=_version_key,
    )
    if local:
        return str(root / local[-1] / f"solc-{local[-1]}")
    latest = _latest_family_patch(family, fetch_json)
    if not latest:
        return ""
    return ensure_solc(
        latest, svm_dir=svm_dir, fetch_json=fetch_json, fetch_bytes=fetch_bytes
    )


def _read_source(source: Path) -> str:
    """Read pragma text from a file or the first sol file in a directory.

    Missing paths yield "" so slither itself reports the real error.
    """
    try:
        if source.is_dir():
            for sol in sorted(source.rglob("*.sol")):
                return sol.read_text(encoding="utf-8", errors="replace")
            return ""
        return source.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _remote_path(
    version: str, fetch_json: Callable[[str], dict[str, object]] | None
) -> str:
    """Look up the binary filename for an exact version from solc list.json."""
    try:
        doc = (fetch_json or _default_json)(LIST_URL)
    except (httpx.HTTPError, ValueError):
        return ""
    builds = doc.get("builds")
    if not isinstance(builds, list):
        return ""
    for build in builds:
        if isinstance(build, dict) and str(build.get("longVersion", "")).startswith(
            f"{version}+"
        ):
            return str(build.get("path", ""))
    return ""


def _latest_family_patch(
    family: str, fetch_json: Callable[[str], dict[str, object]] | None
) -> str:
    """Find the newest patch version within a family from list.json."""
    try:
        doc = (fetch_json or _default_json)(LIST_URL)
    except (httpx.HTTPError, ValueError):
        return ""
    builds = doc.get("builds")
    if not isinstance(builds, list):
        return ""
    best = ""
    for build in builds:
        if not isinstance(build, dict):
            continue
        long_version = str(build.get("longVersion", ""))
        if long_version.startswith(f"{family}.") and (
            not best or _version_key(long_version) > _version_key(best)
        ):
            best = long_version
    return best.split("+")[0]


def _version_key(version: str) -> tuple[int, int, int]:
    """Numeric sort key for dotted versions (0.8.37 sorts above 0.8.4)."""
    core = version.split("+", 1)[0].split("-", 1)[0]
    parts = [int(p) if p.isdigit() else 0 for p in core.split(".")[:3]]
    parts += [0] * (3 - len(parts))
    return (parts[0], parts[1], parts[2])


def _default_json(url: str) -> dict[str, object]:
    """Fetch JSON over https via httpx."""
    return cast("dict[str, object]", httpx.get(url, timeout=30.0).json())


def _default_bytes(url: str) -> bytes:
    """Fetch raw bytes over https via httpx."""
    return httpx.get(url, timeout=60.0).read()
