"""Guard against CLI / operation / builder wiring drift (namespaced CLI).

The registries must agree: every namespaced leaf maps to a registered
operation, every operation is reachable from some leaf, every JSON builder
names a reachable operation, and every moved-command hint points at a live
leaf. This catches the class of bug where a handler or builder is added but
not wired end to end.
"""

from __future__ import annotations

import argparse
from typing import cast

from ruin.cli import _MOVED
from ruin.services.operations import _OPERATIONS
from ruin.services.operations_builders import BUILDERS
from ruin.services.parsing import NAMESPACES, build_parser


def _leaves() -> dict[tuple[str, str], str]:
    parser = build_parser()
    top = next(a for a in parser._actions if isinstance(a, argparse._SubParsersAction))
    leaves: dict[tuple[str, str], str] = {}
    for ns_name, ns_parser in top.choices.items():
        action = next(
            a
            for a in cast("argparse.ArgumentParser", ns_parser)._actions
            if isinstance(a, argparse._SubParsersAction)
        )
        for leaf_name, leaf_parser in action.choices.items():
            parser_for = cast("argparse.ArgumentParser", leaf_parser)
            operation = parser_for.get_default("operation")
            assert isinstance(operation, str), f"{ns_name} {leaf_name} lacks default"
            leaves[(ns_name, leaf_name)] = operation
    return leaves


def test_every_leaf_maps_to_a_registered_operation() -> None:
    for (ns_name, leaf), operation in _leaves().items():
        assert operation in _OPERATIONS, f"{ns_name} {leaf} -> {operation} missing"


def test_every_operation_is_reachable_from_a_leaf() -> None:
    reachable = set(_leaves().values())
    for operation in _OPERATIONS:
        assert operation in reachable, f"{operation} has no CLI route"


def test_builders_name_reachable_operations() -> None:
    reachable = set(_leaves().values())
    for builder_name in BUILDERS:
        assert builder_name in reachable, f"builder {builder_name} unreachable"


def test_moved_hints_point_at_live_leaves() -> None:
    leaves = set(_leaves())
    for old, target in _MOVED.items():
        ns_name, leaf = target.split()[:2]
        assert (ns_name, leaf) in leaves, f"{old} -> {target} is not a live leaf"


def test_namespaces_all_have_leaves() -> None:
    assert set(NAMESPACES) == {ns for ns, _ in _leaves()}
