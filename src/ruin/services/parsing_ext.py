"""Extra CLI parser definitions for ``ruin`` (agent-facing commands).

These subcommand parsers live beside the core ones in
:mod:`ruin.services.parsing`; they are merged by ``build_parser``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ruin.core.chains import DEFAULT_EVM_RPC
from ruin.services.parsing_shared import _leaf
from ruin.services.subprocesses import ANVIL_DEV_ADDRESS

if TYPE_CHECKING:
    from ruin.services.parsing_shared import SubActions


def _add_solvency_parser(
    ns: SubActions,
) -> None:
    sv = _leaf(ns, "classes", "erc4626", "solvency")
    sv.add_argument("vault", help="ERC-4626 vault address")
    sv.add_argument(
        "--rpc", default=DEFAULT_EVM_RPC, help="JSON-RPC endpoint (default mainnet)"
    )
    sv.add_argument("--underlying", default="", help="underlying token (else probe)")
    sv.add_argument("--out", default=None)


def _add_ctoken_parser(
    ns: SubActions,
) -> None:
    ci = _leaf(ns, "classes", "ctoken", "ctoken-inflation")
    ci.add_argument("ctoken", help="cToken market address (Compound v2 fork)")
    ci.add_argument(
        "--rpc", default=None, help="JSON-RPC endpoint (default: --chain table)"
    )
    ci.add_argument(
        "--chain",
        default="ethereum",
        help="chain slug for the default RPC (ethereum, base, arbitrum, ...)",
    )
    ci.add_argument("--out", default=None)


def _add_cosmos_gov_parser(
    ns: SubActions,
) -> None:
    cg = _leaf(ns, "classes", "cosmos-gov")
    cg.add_argument("--lcd", default=None, help="LCD base URL (overrides --chain)")
    cg.add_argument(
        "--chain",
        default="neutron",
        help="chain slug for the default LCD (neutron, osmosis, cosmoshub, ...)",
    )


def _add_decompile_parser(
    ns: SubActions,
) -> None:
    dc = _leaf(ns, "bytecode", "decompile")
    dc.add_argument("address", help="contract address to review (verified or not)")
    dc.add_argument(
        "--rpc", default=None, help="JSON-RPC endpoint (default: --chain table)"
    )
    dc.add_argument(
        "--chain",
        default="ethereum",
        help="chain slug for the default RPC (ethereum, base, arbitrum, ...)",
    )
    dc.add_argument("--out", default=None)


def _add_mintsig_parser(
    ns: SubActions,
) -> None:
    mi = _leaf(ns, "classes", "mintsig")
    mi.add_argument("address", help="token/vault address to screen")
    mi.add_argument(
        "--rpc", default=None, help="JSON-RPC endpoint (default: --chain table)"
    )
    mi.add_argument(
        "--chain",
        default="ethereum",
        help="chain slug for the default RPC (ethereum, base, arbitrum, ...)",
    )


def _add_hunt_parser(
    ns: SubActions,
) -> None:
    ht = _leaf(ns, "target", "hunt")
    ht.add_argument("token", help="ERC20 address to trace recipients of")
    ht.add_argument(
        "--rpc", default=None, help="JSON-RPC endpoint (default: --chain table)"
    )
    ht.add_argument(
        "--chain",
        default="ethereum",
        help="chain slug for the default RPC (ethereum, base, arbitrum, ...)",
    )
    ht.add_argument(
        "--also",
        action="append",
        default=[],
        metavar="ADDRESS",
        help="extra ERC20 address to track recipient inflows for (repeatable)",
    )
    ht.add_argument("--blocks", type=int, default=1500)
    ht.add_argument(
        "--from-block",
        type=int,
        default=None,
        metavar="N",
        help="explicit start block (wide sweeps; bypasses the recent-window cap)",
    )
    ht.add_argument(
        "--to-block", type=int, default=0, metavar="N", help="end block (0 = latest)"
    )
    ht.add_argument("--min-usd", type=float, default=2000.0)
    ht.add_argument("--limit", type=int, default=40)
    ht.add_argument("--out", default=None)


def _add_honeypot_parsers(
    ns: SubActions,
) -> None:
    hp = _leaf(ns, "classes", "honeypot")
    hp.add_argument("mint")
    hp.add_argument("--rpc", default="", help="Solana RPC (default mainnet-beta)")
    hp.add_argument("--out", default=None)

    he = _leaf(ns, "classes", "honeypot-evm")
    he.add_argument("token")
    he.add_argument(
        "--rpc", default=None, help="fork source RPC (default: --chain table)"
    )
    he.add_argument("--chain", default="ethereum", help="chain slug for default RPC")
    he.add_argument("--out", default=None)

    sh = _leaf(ns, "bytecode", "slot-hunt")
    sh.add_argument("token", help="ERC20 token whose balances slot to find")
    sh.add_argument(
        "--account", default=None, help="holder to probe (default: anvil dev key)"
    )
    sh.add_argument(
        "--rpc", default=None, help="fork source RPC (default: --chain table)"
    )
    sh.add_argument("--chain", default="ethereum", help="chain slug for default RPC")
    sh.add_argument("--out", default=None)


def _add_diff_parser(
    ns: SubActions,
) -> None:
    df = _leaf(ns, "bytecode", "impl-diff")
    df.add_argument("new_impl")
    df.add_argument("old_impl")
    df.add_argument("--rpc", default=None)
    df.add_argument("--chain", default="ethereum", help="chain slug for default RPC")
    df.add_argument(
        "--old-rpc", default="", help="RPC for the old side (cross-chain diffs)"
    )
    df.add_argument("--out", default=None)


def _add_agent_parsers(
    ns: SubActions,
) -> None:
    pb = _leaf(ns, "flow", "playbook")
    pb.add_argument("name")
    pb.add_argument(
        "--param",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="step parameter overrides, repeatable, e.g. --param slug=yearn",
    )
    pb.add_argument("--out", default=None)

    ins = _leaf(ns, "bytecode", "inspect")
    ins.add_argument("address")
    ins.add_argument("--chain", default="EVM")
    ins.add_argument("--rpc", default="")
    ins.add_argument("--out", default=None)
    ins.add_argument("--source", action="store_true")
    ins.add_argument("--chain-id", type=int, default=1, dest="chain_id")

    src = _leaf(ns, "source", "fetch", "source")
    src.add_argument("address")
    src.add_argument("--chain", default="EVM")
    src.add_argument("--chain-id", type=int, default=1, dest="chain_id")
    src.add_argument("--out", default=None)
    src.add_argument(
        "--tree",
        default=None,
        help="write each verified source file into this directory",
    )

    pr = _leaf(ns, "bytecode", "probe")
    pr.add_argument("address")
    pr.add_argument("--rpc", default=None)
    pr.add_argument("--chain", default="ethereum", help="chain slug for default RPC")
    pr.add_argument(
        "--from",
        default=ANVIL_DEV_ADDRESS,
        dest="probe_from",
        help="address the outsider calls are sent from",
    )
    pr.add_argument(
        "--selector",
        action="append",
        default=[],
        dest="extra_selectors",
        help="extra 0x + 8-hex selector to smoke-test from the outsider (repeatable)",
    )
    pr.add_argument("--out", default=None)

    _add_ctoken_parser(ns)
    _add_diff_parser(ns)
    _add_honeypot_parsers(ns)
    _add_hunt_parser(ns)
    _add_solvency_parser(ns)
    se = _leaf(ns, "bytecode", "selectors")
    se.add_argument(
        "target",
        help="contract address, or a bytecode/calldata file path "
        "or bare 0x literal for offline decode",
    )
    se.add_argument("--rpc", default=None)
    se.add_argument("--chain", default="ethereum", help="chain slug for default RPC")
    se.add_argument(
        "--resolve",
        action="store_true",
        help="query 4byte.directory for unknown selector signatures",
    )
    se.add_argument("--out", default=None)


def _add_finding_parsers(
    ns: SubActions,
) -> None:
    fn = _leaf(ns, "finding", "new", "finding-new")
    fn.add_argument("id")
    fn.add_argument("title", nargs="+")
    fn.add_argument("--file", required=True)
    fn.add_argument("--severity", default="")
    fn.add_argument("--confidence", type=int, default=0)
    fn.add_argument("--evidence", action="append", default=[])
    fn.add_argument("--contract", default="")

    fu = _leaf(ns, "finding", "update", "finding-update")
    fu.add_argument("id")
    fu.add_argument("state")
    fu.add_argument("--file", required=True)
    fu.add_argument("--evidence", action="append", default=[])

    fl = _leaf(ns, "finding", "list", "finding-list")
    fl.add_argument("--file", required=True)

    fd = _leaf(ns, "finding", "dedupe", "finding-dedupe")
    fd.add_argument("--file", required=True)

    fm = _leaf(ns, "finding", "merge", "finding-merge")
    fm.add_argument("--file", required=True)
    fm.add_argument("--other", required=True)


def _add_reasoning_parsers(
    ns: SubActions,
) -> None:
    rp = _leaf(ns, "chain", "replay")
    rp.add_argument("tx")
    rp.add_argument("--address", required=True)
    rp.add_argument("--rpc", required=True)
    rp.add_argument("--from-block", type=int, required=True, dest="from_block")
    rp.add_argument("--to-block", type=int, required=True, dest="to_block")
    rp.add_argument("--chain", default="EVM")
    rp.add_argument("--out", default=None)

    cl = _leaf(ns, "bytecode", "cluster")
    cl.add_argument("addresses", nargs="+")
    cl.add_argument(
        "--rpc", default=DEFAULT_EVM_RPC, help="JSON-RPC endpoint (default mainnet)"
    )
    cl.add_argument("--chain", default="EVM")
    cl.add_argument("--out", default=None)

    infra = _leaf(ns, "source", "infra")
    infra.add_argument("name")
    infra.add_argument("--out", default=None)
