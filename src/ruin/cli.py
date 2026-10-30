"""Command-line interface (the ``cli`` layer)."""

from __future__ import annotations

import argparse
import json
import sys
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from collections.abc import Sequence

from ruin.services.operations import run_operation, run_operation_json
from ruin.services.parsing import NAMESPACES, build_parser

_MOVED = {
    "accessmap": "source accessmap",
    "analyze": "source analyze",
    "bundle": "target bundle",
    "cluster": "bytecode cluster",
    "cosmos-gov": "classes cosmos-gov",
    "ctoken-inflation": "classes ctoken",
    "decode": "bytecode selectors",
    "decompile": "bytecode decompile",
    "exploits": "source triage --mode exploits",
    "finding-dedupe": "finding dedupe",
    "finding-list": "finding list",
    "finding-merge": "finding merge",
    "finding-new": "finding new",
    "finding-update": "finding update",
    "flashloan": "verify flashloan",
    "fuzz": "verify fuzz",
    "fuzz-run": "verify fuzz --run",
    "honeypot": "classes honeypot",
    "honeypot-evm": "classes honeypot-evm",
    "hunt": "target hunt",
    "hypotheses": "source triage --mode hypotheses",
    "impl-diff": "bytecode impl-diff",
    "infra": "source infra",
    "inspect": "bytecode inspect",
    "logs": "chain logs",
    "map": "target map",
    "mintsig": "classes mintsig",
    "oracle": "verify oracle",
    "enumerate": "protocol enumerate",
    "invariants": "protocol invariants",
    "model": "protocol model",
    "pipeline": "flow status",
    "pipeline-status": "flow status",
    "playbook": "flow playbook",
    "probe": "bytecode probe",
    "proxy": "bytecode proxy",
    "rank": "target rank",
    "replay": "chain replay",
    "research": "source research",
    "review": "source review",
    "rng-hack": "classes rng",
    "run": "verify poc",
    "screen": "target screen",
    "selectors": "bytecode selectors",
    "slither": "source slither",
    "slot-hunt": "bytecode slot-hunt",
    "solvency": "classes erc4626",
    "source": "source fetch",
    "symbolic": "verify symbolic",
    "symbolic-run": "verify symbolic --run",
    "thin-collateral": "classes thin-collateral",
    "trace": "chain trace",
    "triage": "source triage",
    "resolve": "protocol resolve",
    "trust": "target trust",
}


def _moved_token(raw: Sequence[str]) -> str:
    """First flat command token that moved, scanning before any namespace.

    Stops at the first namespace token: ``ruin target screen`` is a real
    call whose parse error must surface, while ``ruin --format json hunt``
    still deserves the moved hint for ``hunt``.
    """
    for token in raw:
        if token in NAMESPACES:
            return ""
        if token in _MOVED:
            return token
    return ""


def _known_commands(parser: argparse.ArgumentParser) -> set[str]:
    """Return the advertised subcommand names taken straight from the parser."""
    action = next(
        a for a in parser._actions if isinstance(a, argparse._SubParsersAction)
    )
    return set(action.choices)


def _dispatch(operation: str, kwargs: dict[str, object], fmt: str) -> int:
    """Run one operation in the requested format."""
    try:
        if fmt == "json":
            try:
                data = run_operation_json(operation, kwargs)
            except ValueError:
                result = run_operation(operation, kwargs)
                data = {"operation": operation, "output": result}
            print(json.dumps(data, separators=(",", ":")))
        else:
            result = run_operation(operation, kwargs)
            if result:
                print(result)
    except (ValueError, TypeError, RuntimeError, OSError, KeyError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI and return the process exit code."""
    parser = build_parser()
    raw = list(argv) if argv is not None else sys.argv[1:]
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        moved = _moved_token(raw)
        if moved:
            print(f"error: '{moved}' moved to 'ruin {_MOVED[moved]}'", file=sys.stderr)
            return 2
        if raw and raw[0] not in _known_commands(parser):
            raw = ["verify", "poc", *raw]
            args = parser.parse_args(raw)
        else:
            raise
    if args.command is None:
        parser.print_help()
        return 0
    if getattr(args, "action", None) is None:
        _namespace_help(parser, str(args.command))
        return 0
    kwargs = {
        key: value
        for key, value in vars(args).items()
        if key not in ("command", "action", "format", "operation")
    }
    return _dispatch(str(args.operation), kwargs, str(args.format))


def _namespace_help(parser: argparse.ArgumentParser, command: str) -> None:
    """Print the help of one namespace when its action is omitted."""
    top = next(a for a in parser._actions if isinstance(a, argparse._SubParsersAction))
    cast("argparse.ArgumentParser", top.choices[command]).print_help()


if __name__ == "__main__":
    raise SystemExit(main())
