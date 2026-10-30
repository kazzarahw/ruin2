"""Pin the full parser contract: every operation's exact argument surface.

The fixtures were captured before the namespaced regrouping. Regenerating
them from the current parser and comparing is the strongest guard against
accidental flag drift while commands moved namespaces.
"""

from __future__ import annotations

import json
from pathlib import Path

from ruin.services.parsing import build_parser

FIXTURES = Path(__file__).parent / "fixtures"


def _surfaces() -> dict[str, dict[str, object]]:
    argv = json.loads((FIXTURES / "cli_argv.json").read_text())
    parser = build_parser()
    surfaces: dict[str, dict[str, object]] = {}
    for operation, args in argv.items():
        ns = parser.parse_args(args)
        surfaces[operation] = {
            key: value
            for key, value in vars(ns).items()
            if key not in ("command", "action", "format", "operation")
        }
    return surfaces


def test_parser_contract_matches_the_recorded_snapshot() -> None:
    expected = json.loads((FIXTURES / "parser_dests.json").read_text())
    assert _surfaces() == expected


def test_snapshot_covers_every_operation() -> None:
    from ruin.services.operations import _OPERATIONS

    expected = json.loads((FIXTURES / "parser_dests.json").read_text())
    assert set(expected) == set(_OPERATIONS)
