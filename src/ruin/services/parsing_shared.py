"""Shared plumbing for CLI parser construction."""

from __future__ import annotations

import argparse
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping

    SubActions = Mapping[str, argparse._SubParsersAction[argparse.ArgumentParser]]


def _format_parent() -> argparse.ArgumentParser:
    """Parent parser letting ``--format`` also be given after the subcommand."""
    parent = argparse.ArgumentParser(add_help=False)
    parent.add_argument(
        "--format",
        choices=("markdown", "json"),
        default=argparse.SUPPRESS,
        help="output format (may be placed before or after the subcommand)",
    )
    return parent


def _sp(
    sub: argparse._SubParsersAction[argparse.ArgumentParser],
    name: str,
) -> argparse.ArgumentParser:
    """Create a subparser carrying the global ``--format`` flag."""
    return sub.add_parser(name, parents=[_format_parent()])


def _leaf(
    ns: SubActions,
    namespace: str,
    name: str,
    operation: str | None = None,
) -> argparse.ArgumentParser:
    """Create a namespaced leaf parser bound to its operation name."""
    parser = _sp(ns[namespace], name)
    parser.set_defaults(operation=operation or name)
    return parser
