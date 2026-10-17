"""Repository policy tests: mechanical enforcement for two AGENTS.md rules.

No linter covers these, so they live here:

- rule 1: checks may never be silenced with suppression comments;
- rule 5: source files stay small enough for a small model to hold in context.
"""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
POLICY_DIRS = ("src", "scripts", "tests")
LINE_LIMIT = 300
SUPPRESSION_RE = re.compile(
    r"#\s*noqa|#\s*type:\s*ignore|#\s*ty:\s*ignore|#\s*pragma:\s*no\s?cover",
    re.IGNORECASE,
)


def iter_python_files(directories: tuple[str, ...]) -> list[Path]:
    """List every Python file under ``directories``, sorted by path."""
    files: list[Path] = []
    for name in directories:
        files.extend(sorted((REPO_ROOT / name).rglob("*.py")))
    return files


def test_no_suppression_comments_in_python_sources() -> None:
    offenders: list[str] = []
    for path in iter_python_files(POLICY_DIRS):
        if path.resolve() == Path(__file__).resolve():
            continue  # this file must spell out the patterns it forbids
        text = path.read_text(encoding="utf-8")
        for number, line in enumerate(text.splitlines(), start=1):
            if SUPPRESSION_RE.search(line):
                relative = path.relative_to(REPO_ROOT)
                offenders.append(f"{relative}:{number}: {line.strip()}")
    assert not offenders, (
        "suppression comments weaken the gate (AGENTS.md rule 1); fix the code "
        "or ask a human instead:\n" + "\n".join(offenders)
    )


def test_src_files_stay_within_the_line_limit() -> None:
    offenders: list[str] = []
    for path in iter_python_files(("src",)):
        line_count = len(path.read_text(encoding="utf-8").splitlines())
        if line_count > LINE_LIMIT:
            offenders.append(f"{path.relative_to(REPO_ROOT)}: {line_count} lines")
    assert not offenders, (
        f"source files must stay at or under {LINE_LIMIT} lines "
        "(AGENTS.md rule 5); split the file:\n" + "\n".join(offenders)
    )
