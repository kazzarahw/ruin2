"""Access-control analysis service for ``ruin``."""

from __future__ import annotations

import ast
import json
from typing import TYPE_CHECKING

from ruin.core.access_control import AccessMap, FunctionAccess, classify_function
from ruin.services.subprocesses import run_command

if TYPE_CHECKING:
    from pathlib import Path

_MIN_ROW = 3


def _row_list(value: object) -> list[str]:
    """Parse a printer cell holding a Python-style list literal."""
    try:
        parsed = ast.literal_eval(str(value))
    except (ValueError, SyntaxError):
        return []
    if isinstance(parsed, list):
        return [str(item) for item in parsed]
    return []


def build_access_map(source: Path) -> AccessMap:
    """Build an access-control map from slither's vars-and-auth printer.

    Args:
        source: Path to a Solidity source file or project directory.

    Returns:
        An AccessMap for the contract.
    """
    process = run_command(
        ["slither", str(source), "--print", "vars-and-auth", "--json", "-"],
        timeout=120.0,
    )
    if not process.stdout.strip():
        tail = process.stderr.strip()[-200:]
        raise RuntimeError(
            "slither produced no JSON for access map "
            f"(exit {process.returncode}): {tail}"
        )
    try:
        doc = json.loads(process.stdout)
    except (json.JSONDecodeError, TypeError):
        return AccessMap(contract=str(source))

    printers = doc.get("results", {}).get("printers", [])
    functions: list[FunctionAccess] = []
    contract_name = str(source)
    for entry in printers if isinstance(printers, list) else []:
        if not isinstance(entry, dict):
            continue
        for element in entry.get("elements", []):
            if not isinstance(element, dict):
                continue
            table = element.get("name")
            if not isinstance(table, dict) or element.get("type") != "pretty_table":
                continue
            contract_name = str(table.get("name", contract_name))
            content = table.get("content")
            rows = content.get("rows", []) if isinstance(content, dict) else []
            for row in rows if isinstance(rows, list) else []:
                if not isinstance(row, list) or len(row) < _MIN_ROW:
                    continue
                name = str(row[0])
                auth = _row_list(row[2])
                state_changing = bool(_row_list(row[1]))
                functions.append(
                    classify_function(name, "external", auth, state_changing)
                )
    return AccessMap(contract=contract_name, functions=functions)
