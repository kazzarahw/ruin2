"""Second-batch CLI parser definitions for ``ruin``.

Split out of :mod:`ruin.services.parsing_ext` so each parser module stays
inside the 300-line reading budget (AGENTS.md rule 5).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ruin.services.parsing_shared import _leaf

if TYPE_CHECKING:
    from ruin.services.parsing_shared import SubActions


def _add_thin_collateral_parser(
    ns: SubActions,
) -> None:
    tc = _leaf(ns, "classes", "thin-collateral")
    tc.add_argument("token", help="collateral ERC20 address")
    tc.add_argument(
        "--market",
        required=True,
        metavar="ADDRESS",
        help="market contract holding the collateral",
    )
    tc.add_argument(
        "--factory",
        required=True,
        metavar="ADDRESS",
        help="UniV2-style pair factory to scan for pools",
    )
    tc.add_argument(
        "--rpc", default=None, help="JSON-RPC endpoint (default: --chain table)"
    )
    tc.add_argument(
        "--chain",
        default="ethereum",
        help="chain slug for the default RPC (ethereum, base, arbitrum, ...)",
    )
    tc.add_argument(
        "--blocks",
        type=int,
        default=3000,
        help="PairCreated scan window in blocks (default 3000)",
    )
    tc.add_argument(
        "--price-usd",
        type=float,
        required=True,
        dest="price_usd",
        metavar="PRICE",
        help="USD price of one TOKEN (required; no oracle plumbing)",
    )
    tc.add_argument(
        "--min-usd",
        type=float,
        default=50000.0,
        dest="min_usd",
        metavar="FLOOR",
        help="pools shallower than this USD are dropped from the depth sum",
    )
    tc.add_argument("--out", default=None)
