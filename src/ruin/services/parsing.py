"""CLI parsing for ``ruin``."""

from __future__ import annotations

import argparse
from typing import TYPE_CHECKING

from ruin.core.flashloan import DEFAULT_FLASHLOAN_AMOUNT
from ruin.core.oracle import DEFAULT_SWAP_AMOUNT
from ruin.services.parsing_ext import (
    DEFAULT_EVM_RPC,
    _add_agent_parsers,
    _add_cosmos_gov_parser,
    _add_decompile_parser,
    _add_finding_parsers,
    _add_mintsig_parser,
    _add_reasoning_parsers,
)
from ruin.services.parsing_ext2 import _add_thin_collateral_parser
from ruin.services.parsing_shared import _leaf

if TYPE_CHECKING:
    from ruin.services.parsing_shared import SubActions


def _add_first_parsers(
    ns: SubActions,
) -> None:
    run_parser = _leaf(ns, "verify", "poc", "pipeline")
    run_parser.add_argument("recon_file")
    run_parser.add_argument("--name", required=True)
    run_parser.add_argument("--forge-test", required=True, dest="forge_test")
    run_parser.add_argument("--method", required=True)
    run_parser.add_argument("--rpc", required=True)
    run_parser.add_argument("--mode", default="research")
    run_parser.add_argument("--min-tvl", type=int, default=None, dest="min_tvl")
    run_parser.add_argument("--vulns", default=None)
    run_parser.add_argument("--out", default=None)
    run_parser.add_argument("--fork-block", type=int, default=None, dest="fork_block")
    run_parser.add_argument("--private-key", default=None, dest="private_key")

    status = _leaf(ns, "flow", "status", "pipeline-status")
    status.add_argument("name")
    status.add_argument("--stage", nargs=3, action="append", default=[])

    rank = _leaf(ns, "target", "rank")
    rank.add_argument("--limit", type=int, default=10)
    rank.add_argument("--chain", action="append", default=[])
    rank.add_argument(
        "--exclude-chain", action="append", default=[], dest="exclude_chain"
    )
    rank.add_argument("--screen", default=None)

    mapper = _leaf(ns, "target", "map")
    mapper.add_argument("slug")
    mapper.add_argument("--asset", required=True)
    mapper.add_argument("--out", default=None)

    slither = _leaf(ns, "source", "slither")
    slither.add_argument("source")
    slither.add_argument("--out", default=None)

    review = _leaf(ns, "source", "review")
    review.add_argument("source")
    review.add_argument("--out", default=None)

    research = _leaf(ns, "source", "research")
    research.add_argument("mechanism")
    research.add_argument("summary", nargs="+")
    research.add_argument(
        "--source",
        action="append",
        default=[],
        help="reference source to consult (repeatable)",
    )


def _add_second_parsers(
    ns: SubActions,
) -> None:
    rng = _leaf(ns, "classes", "rng", "rng-hack")
    rng.add_argument("mechanism")
    rng.add_argument("summary", nargs="+")
    rng.add_argument(
        "--source",
        action="append",
        required=True,
        help="RNG source value the game reads, e.g. block.timestamp "
        "or blockhash (repeatable)",
    )
    rng.add_argument("--decision", default=None)
    rng.add_argument("--manipulator", default=None)

    trust = _leaf(ns, "target", "trust")
    trust.add_argument("name")
    trust.add_argument("--custodial", action="store_true")
    trust.add_argument("--assume", nargs=3, action="append", default=[])

    screen = _leaf(ns, "target", "screen")
    screen.add_argument("name")
    screen.add_argument("--chain", required=True)
    screen.add_argument("--tvl", default="0")
    screen.add_argument("--source", default="none")
    screen.add_argument("--bespoke", action="store_true")
    screen.add_argument("--custodial", action="store_true")
    screen.add_argument("--listed", default=None)

    bundle = _leaf(ns, "target", "bundle")
    bundle.add_argument("name")
    bundle.add_argument("--screen", action="store_true")
    bundle.add_argument("--pipeline", action="store_true")

    triage = _leaf(ns, "source", "triage")
    triage.add_argument("name")
    triage.add_argument(
        "--mode",
        choices=("checks", "exploits", "hypotheses", "source"),
        default="checks",
        help="triage mode: lead/noise checks, known-exploit matches, "
        "ranked hypotheses, or raw source smells",
    )
    triage.add_argument("--check", action="append", default=[])
    triage.add_argument("--file", default=None)
    triage.add_argument(
        "--source",
        default=None,
        help="source file to scan for bug-class smells (mergeable with --file)",
    )
    triage.add_argument(
        "--signal",
        action="append",
        default=[],
        help="structural signal for hypotheses mode, e.g. oracle (repeatable)",
    )
    triage.add_argument("--out", default=None)


NAMESPACES: dict[str, str] = {
    "target": "pick and size hunt targets",
    "source": "analyze verified sources",
    "bytecode": "inspect live bytecode and proxies",
    "classes": "screen for known bug classes",
    "chain": "read chains and replay exploits",
    "verify": "run or scaffold verification",
    "flow": "pipeline status and playbooks",
    "finding": "manage the finding registry",
    "protocol": "enumerate and model deployed protocols",
}


def build_parser() -> argparse.ArgumentParser:
    """Create the namespaced argument parser for the CLI."""
    parser = argparse.ArgumentParser(prog="ruin", description="ruin research pipeline")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    top = parser.add_subparsers(dest="command")
    ns: SubActions = {
        name: top.add_parser(name, help=blurb).add_subparsers(dest="action")
        for name, blurb in NAMESPACES.items()
    }
    _add_first_parsers(ns)
    _add_second_parsers(ns)
    _add_third_parsers(ns)
    return parser


def _add_third_parsers(
    ns: SubActions,
) -> None:
    _add_fuzz_symbolic(ns)
    _add_new_ops(ns)


def _add_fuzz_symbolic(
    ns: SubActions,
) -> None:
    fuzz = _leaf(ns, "verify", "fuzz")
    fuzz.add_argument("target")
    fuzz.add_argument(
        "--run",
        action="store_true",
        help="execute the fuzz runner instead of recording a result",
    )
    fuzz.add_argument("--kind", default="invariant")
    fuzz.add_argument("--outcome", default="passed")
    fuzz.add_argument("--detail", default="")
    fuzz.add_argument("--tool", default="foundry")
    fuzz.add_argument("--match-test", dest="match_test", default=None)
    fuzz.add_argument("--command", nargs="+", dest="tool_command", default=None)
    fuzz.add_argument("--finding", default=None)
    fuzz.add_argument("--linked-finding", dest="linked_finding", default=None)

    symbolic = _leaf(ns, "verify", "symbolic")
    symbolic.add_argument("target")
    symbolic.add_argument(
        "--run",
        action="store_true",
        help="force the runner even when --outcome records a result",
    )
    symbolic.add_argument("--tool", default="halmos")
    symbolic.add_argument("--command", nargs="+", dest="tool_command", default=None)
    symbolic.add_argument("--outcome", default=None)
    symbolic.add_argument("--detail", default="")
    symbolic.add_argument("--finding", default=None)
    symbolic.add_argument("--linked-finding", dest="linked_finding", default=None)

    analyze = _leaf(ns, "source", "analyze")
    analyze.add_argument("source")
    analyze.add_argument("--name", default="target")

    trace = _leaf(ns, "chain", "trace")
    trace.add_argument("tx")
    trace.add_argument("--rpc", default=DEFAULT_EVM_RPC)

    proxy = _leaf(ns, "bytecode", "proxy")
    proxy.add_argument("address")
    proxy.add_argument("--rpc", default=DEFAULT_EVM_RPC)


def _add_new_ops(
    ns: SubActions,
) -> None:
    logs = _leaf(ns, "chain", "logs")
    logs.add_argument("address")
    logs.add_argument("--rpc", default=DEFAULT_EVM_RPC)
    logs.add_argument("--from-block", type=int, required=True, dest="from_block")
    logs.add_argument("--to-block", type=int, required=True, dest="to_block")
    logs.add_argument("--chain", default="EVM")

    accessmap = _leaf(ns, "source", "accessmap")
    accessmap.add_argument("source")

    oracle = _leaf(ns, "verify", "oracle")
    oracle.add_argument("target")
    oracle.add_argument("--rpc", required=True)
    oracle.add_argument("--chain", default=None)
    oracle.add_argument("--router", default=None)
    oracle.add_argument("--token-a", dest="reserve_a", default=None)
    oracle.add_argument("--token-b", dest="reserve_b", default=None)
    oracle.add_argument("--oracle", default=None)
    oracle.add_argument(
        "--swap-amount", dest="swap_amount", default=DEFAULT_SWAP_AMOUNT
    )
    oracle.add_argument("--min-deviation", dest="min_deviation", default="1 ether")
    oracle.add_argument("--out", default=None)

    flashloan = _leaf(ns, "verify", "flashloan")
    flashloan.add_argument("target")
    flashloan.add_argument("--rpc", required=True)
    flashloan.add_argument("--chain", default=None)
    flashloan.add_argument("--asset", default=None)
    flashloan.add_argument("--amount", default=DEFAULT_FLASHLOAN_AMOUNT)
    flashloan.add_argument("--pool", default=None)
    flashloan.add_argument("--out", default=None)

    _add_finding_parsers(ns)
    _add_agent_parsers(ns)
    _add_cosmos_gov_parser(ns)
    _add_mintsig_parser(ns)
    _add_decompile_parser(ns)
    _add_reasoning_parsers(ns)
    _add_thin_collateral_parser(ns)
    _add_protocol_parsers(ns)


def _add_protocol_parsers(ns: SubActions) -> None:
    """Protocol namespace: resolve/enumerate/model/invariants on one address."""
    for leaf in ("resolve", "enumerate", "model", "invariants"):
        parser = _leaf(ns, "protocol", leaf)
        parser.add_argument("address")
        parser.add_argument("--chain", default="ethereum", help="chain slug")
        parser.add_argument("--rpc", default=None, help="explicit RPC endpoint")
        if leaf == "invariants":
            parser.add_argument(
                "--scaffold", default=None, help="directory for invariant stubs"
            )
