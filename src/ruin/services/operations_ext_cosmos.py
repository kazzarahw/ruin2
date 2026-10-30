"""Cosmos governance-capture screen over public LCD endpoints.

While a proposal is in voting period this reads its messages straight from
chain state and checks whether the contracts they target still hold bank
balances: the Neutron "AIATO" class (buy stake, pass MsgUpdateAdmin, drain
the funded contracts).
"""

from __future__ import annotations

from typing import cast

from ruin.core.cosmos import (
    CosmosGovReport,
    GovRow,
    custody_excluding,
    custody_total,
    proposal_summary,
)
from ruin.services.rpc import SHARED_TRANSPORT

_PROPOSALS_ROUTE = "/cosmos/gov/v1/proposals?proposal_status=2&pagination.limit=50"
_BALANCES_ROUTE = "/cosmos/bank/v1beta1/balances/"
_UNIVERSAL = SHARED_TRANSPORT


def _proposals(doc: object) -> list[object]:
    """The ``proposals`` list of a gov response; anything else is empty."""
    if not isinstance(doc, dict):
        return []
    proposals = doc.get("proposals")
    return list(proposals) if isinstance(proposals, list) else []


def _balances_for(lcd: str, address: str) -> object:
    """Fetch one address's bank balances document from the LCD."""
    return _UNIVERSAL.get_json(f"{lcd}{_BALANCES_ROUTE}{address}")


def _target_row(lcd: str, summary: dict[str, object], target: str) -> GovRow:
    """Screen one proposal target: its message flags plus custody readings."""
    messages = cast("list[str]", summary["messages"])
    balances = _balances_for(lcd, target)
    risk = custody_excluding(balances, str(summary["deposit_denom"]))
    return GovRow(
        proposal=str(summary["id"]),
        target=target,
        flags=tuple(f for f in messages if f.endswith(f":{target}")),
        custody_total=custody_total(balances),
        non_gov_custody=risk,
        capture_risk=risk > 0,
    )


def _code_only_row(summary: dict[str, object]) -> GovRow:
    """Row for store/instantiate proposals that name no contract address yet."""
    messages = cast("list[str]", summary["messages"])
    return GovRow(
        proposal=str(summary["id"]),
        flags=tuple(f for f in messages if ":" not in f),
    )


def _proposal_rows(lcd: str, summary: dict[str, object]) -> list[GovRow]:
    """Rows for one proposal: per target, or one code-only row, or none."""
    if not summary:
        return []
    targets = cast("list[str]", summary["targets"])
    if targets:
        return [_target_row(lcd, summary, target) for target in targets]
    if cast("list[str]", summary["messages"]):
        return [_code_only_row(summary)]
    return []


def cosmos_gov_data(lcd: str) -> CosmosGovReport:
    """Fetch voting proposals and screen their contract targets for custody.

    Args:
        lcd: Base URL of a Cosmos SDK LCD endpoint (no trailing slash needed).

    Returns:
        A report keyed by the LCD endpoint; each row carries the proposal
        id, target address, message flags, custody sums, and the
        capture-risk verdict (true when the target holds funds outside the
        proposal's gov denom).
    """
    doc = _UNIVERSAL.get_json(f"{lcd}{_PROPOSALS_ROUTE}")
    rows: list[GovRow] = []
    for proposal in _proposals(doc):
        rows.extend(_proposal_rows(lcd, proposal_summary(proposal)))
    return CosmosGovReport(lcd=lcd, rows=tuple(rows))
