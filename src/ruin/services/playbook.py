"""Playbook loading and execution for ``ruin``."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ruin.core.playbook import Playbook, PlaybookStep

if TYPE_CHECKING:
    from collections.abc import Callable

BUILTIN_DIR = Path(__file__).resolve().parent.parent / "playbooks"
SCHEMA_VERSION = 2
_WRITE_LINE = re.compile(r"^wrote (?:\d+ files under )?(\S+)$", re.MULTILINE)
_TOKEN = re.compile(r"\{(\w+)\}")


def _require_schema(name: str, raw: dict[str, Any]) -> None:
    """Reject playbooks that are not on the current schema version."""
    schema = int(raw.get("schema", 1))
    if schema != SCHEMA_VERSION:
        raise ValueError(
            f"playbook {name} uses schema {schema}; expected {SCHEMA_VERSION}"
        )


def load_playbook(name: str, search_dir: Path | None = None) -> Playbook:
    """Load a playbook by name from the built-in or custom directory.

    Args:
        name: Playbook name (without .json extension).
        search_dir: Optional custom directory to search first.

    Returns:
        The loaded Playbook.

    Raises:
        FileNotFoundError: If the playbook is not found.
    """
    filename = f"{name}.json"
    candidates: list[Path] = []
    if search_dir:
        candidates.append(search_dir / filename)
    candidates.append(BUILTIN_DIR / filename)
    for path in candidates:
        if path.exists():
            raw = json.loads(path.read_text(encoding="utf-8"))
            _require_schema(name, raw)
            steps = [
                PlaybookStep(
                    operation=str(s.get("operation", "")),
                    params=dict(s.get("params", {})),
                )
                for s in raw.get("steps", [])
            ]
            return Playbook(
                name=str(raw.get("name", name)),
                description=str(raw.get("description", "")),
                steps=steps,
                params=list(raw.get("params", [])),
            )
    raise FileNotFoundError(f"playbook not found: {name}")


def execute_playbook(
    playbook: Playbook,
    dispatch: Callable[[str, dict[str, Any]], str],
    overrides: dict[str, str] | None = None,
) -> str:
    """Execute a playbook's steps in sequence and collect output.

    Args:
        playbook: The playbook to run.
        dispatch: Callable that runs a single operation by name.
        overrides: Parameter overrides applied to every step.

    Step params equal to "{last_file}" are substituted with the path from the
    most recent "wrote <path>" step output, chaining source dumps into SAST.

    Returns:
        Concatenated markdown output from all steps.
    """
    results: list[str] = []
    ctx: dict[str, str] = {}
    for step in playbook.steps:
        kwargs: dict[str, Any] = {
            k: _resolve(v, ctx, overrides or {}) for k, v in step.params.items()
        }
        if overrides:
            for key, value in overrides.items():
                current = step.params.get(key)
                if key not in step.params or not _has_token(current):
                    kwargs[key] = value
        try:
            output = dispatch(step.operation, kwargs)
            written = _WRITE_LINE.search(output)
            if written:
                ctx["last_file"] = written.group(1)
            results.append(output)
        except (ValueError, TypeError, RuntimeError, OSError) as error:
            results.append(f"## {step.operation}\n\nerror: {error}")
        except KeyError as error:
            results.append(f"## {step.operation}\n\nerror: missing param: {error}")
    return "\n\n---\n\n".join(results)


def _has_token(value: object) -> bool:
    """Return whether a param value contains a {token} placeholder."""
    return isinstance(value, str) and bool(_TOKEN.search(value))


def _resolve(value: object, ctx: dict[str, str], overrides: dict[str, str]) -> object:
    """Substitute {token} params from step outputs and CLI overrides.

    {last_file} resolves to the most recent "wrote <path>" output; any other
    {word} resolves to the matching CLI override when one was provided.
    """
    if not isinstance(value, str):
        return value

    def replace(match: re.Match[str]) -> str:
        word = match.group(1)
        if word == "last_file":
            return ctx.get("last_file", match.group(0))
        return overrides.get(word, match.group(0))

    return _TOKEN.sub(replace, value)
