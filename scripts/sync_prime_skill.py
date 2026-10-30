"""Synchronize the packaged Prime skill with the repository source."""

from __future__ import annotations

import argparse
import filecmp
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILL_ROOT = REPO_ROOT / ".prime" / "agent" / "skills" / "ruin"
FILES = ("SKILL.md", "pyproject.toml")
DIRECTORIES = ("src",)


def sync() -> None:
    """Copy the skill files into the packaged location."""
    SKILL_ROOT.mkdir(parents=True, exist_ok=True)
    for name in FILES:
        shutil.copy2(REPO_ROOT / name, SKILL_ROOT / name)
    for name in DIRECTORIES:
        destination = SKILL_ROOT / name
        if destination.is_symlink():
            continue
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(
            REPO_ROOT / name, destination, ignore=shutil.ignore_patterns("__pycache__")
        )


def _files_match() -> bool:
    """Return True when the governed files match the repository copies."""
    for name in FILES:
        if not filecmp.cmp(REPO_ROOT / name, SKILL_ROOT / name, shallow=False):
            print(f"out of sync: {name}", file=sys.stderr)
            return False
    return True


def _directory_matches(name: str) -> bool:
    """Return True when a governed directory matches, via copy or symlink."""
    left = REPO_ROOT / name
    right = SKILL_ROOT / name
    if right.is_symlink():
        if right.resolve() == left.resolve():
            return True
        print(f"out of sync: {name} (symlink target drift)", file=sys.stderr)
        return False
    if not right.exists():
        print(f"out of sync: {name}", file=sys.stderr)
        return False
    comparison = filecmp.dircmp(left, right, ignore=["__pycache__"])
    if comparison.left_only or comparison.right_only or comparison.diff_files:
        print(f"out of sync: {name}", file=sys.stderr)
        return False
    return True


def check() -> int:
    """Return zero when the packaged skill matches the repository."""
    if not SKILL_ROOT.exists():
        print("packaged skill is missing", file=sys.stderr)
        return 1
    if not _files_match():
        return 1
    for name in DIRECTORIES:
        if not _directory_matches(name):
            return 1
    return 0


def main() -> int:
    """Synchronize the Prime skill."""
    parser = argparse.ArgumentParser(description="Synchronize the Prime skill.")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        return check()
    sync()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
