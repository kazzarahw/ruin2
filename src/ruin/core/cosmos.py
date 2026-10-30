"""Pure checks over Cosmos SDK gov and bank LCD payloads (no network)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

from ruin.core.chains import CHAIN_LCDS

if TYPE_CHECKING:
    from collections.abc import Sequence

_UPDATE_ADMIN_TYPE = "/cosmwasm.wasm.v1.MsgUpdateAdmin"
_MIGRATE_TYPE = "/cosmwasm.wasm.v1.MsgMigrateContract"
_EXECUTE_TYPE = "/cosmwasm.wasm.v1.MsgExecuteContract"
_STORE_CODE_TYPE = "/cosmwasm.wasm.v1.MsgStoreCode"
_INSTANTIATE_TYPE = "/cosmwasm.wasm.v1.MsgInstantiateContract"

_FLAG_BY_TYPE: dict[str, str] = {
    _UPDATE_ADMIN_TYPE: "update-admin",
    _MIGRATE_TYPE: "migrate",
    _EXECUTE_TYPE: "execute",
    _STORE_CODE_TYPE: "store-code",
    _INSTANTIATE_TYPE: "instantiate",
}
_TARGETLESS_TYPES = (_STORE_CODE_TYPE, _INSTANTIATE_TYPE)


def resolve_lcd(chain: str) -> str:
    """Pick the LCD endpoint for a chain slug (see CHAIN_LCDS).

    Args:
        chain: Chain slug, e.g. ``"neutron"``. Surrounding space is ignored.

    Returns:
        The base LCD URL registered for that slug.

    Raises:
        ValueError: If the slug is not in the table.
    """
    slug = chain.strip().lower()
    if slug not in CHAIN_LCDS:
        raise ValueError(
            f"unknown chain {chain!r} (known: "
            f"{', '.join(sorted(CHAIN_LCDS))}; or pass --lcd URL)"
        )
    return CHAIN_LCDS[slug]


_LEGACY_TYPE = "/cosmos.gov.v1.MsgExecLegacyContent"
_WASMX_BATCH_STORE = "/injective.wasmx.v1.BatchStoreCode"
_WASMX_BATCH_EXEC = "/injective.wasmx.v1.BatchExecuteContract"


def _legacy_inner(message: dict[str, object]) -> list[object]:
    """Messages wrapped by MsgExecLegacyContent (legacy param/wasmx forms)."""
    content = message.get("content")
    if not isinstance(content, dict):
        return []
    inner = content.get("messages")
    if isinstance(inner, list):
        return list(inner)
    return [content]


def _wasmx_batch(message: dict[str, object]) -> list[str]:
    """Flags for Injective wasmx batch-execute messages (address per item)."""
    items = message.get("msgs")
    rows = items if isinstance(items, list) else []
    flags: list[str] = []
    for item in rows:
        if isinstance(item, dict):
            addr = str(item.get("contract_address", ""))
            flags.append(f"execute:{addr}" if addr else "execute")
    return flags


def _message_flag(message: object) -> list[str]:
    """Flag one gov message; contract-carrying types embed the address."""
    flags: list[str] = []
    if isinstance(message, dict):
        body = cast("dict[str, object]", message)
        kind = str(body.get("@type", ""))
        prefix = _FLAG_BY_TYPE.get(kind)
        if kind == _LEGACY_TYPE:
            flags = [f for inner in _legacy_inner(body) for f in _message_flag(inner)]
        elif kind == _WASMX_BATCH_STORE:
            flags = ["store-code-wasmx"]
        elif kind == _WASMX_BATCH_EXEC:
            flags = _wasmx_batch(body)
        elif prefix is not None:
            contract = str(body.get("contract", ""))
            if kind in _TARGETLESS_TYPES or not contract:
                flags = [prefix]
            else:
                flags = [f"{prefix}:{contract}"]
    return flags


def gov_capture_flags(messages: Sequence[object]) -> list[str]:
    """Flag admin-transfer / migrate / execute / store / instantiate messages.

    Args:
        messages: The ``messages`` list of a gov proposal (plain dicts).

    Returns:
        Ordered unique flags. Contract-carrying types embed the address,
        e.g. ``"update-admin:neutron1abcd"``; store/instantiate flag by type.
    """
    flags: list[str] = []
    for message in messages:
        for flag in _message_flag(message):
            if flag not in flags:
                flags.append(flag)
    return flags


def gov_capture_targets(messages: Sequence[object]) -> list[str]:
    """Contract addresses named by update-admin / migrate / execute messages."""
    targets: list[str] = []
    for flag in gov_capture_flags(messages):
        _kind, sep, address = flag.partition(":")
        if sep and address and address not in targets:
            targets.append(address)
    return targets


def _amount(entry: object) -> int:
    """Bank entry amount as an int; garbage and negatives read as zero."""
    if not isinstance(entry, dict):
        return 0
    amount = entry.get("amount")
    if isinstance(amount, int):
        return max(amount, 0)
    if isinstance(amount, str) and amount.isdecimal():
        return int(amount)
    return 0


def _entries(balances: object) -> list[object]:
    """The ``balances`` list of a bank response; anything else is empty."""
    if not isinstance(balances, dict):
        return []
    entries = balances.get("balances")
    return list(entries) if isinstance(entries, list) else []


def custody_total(balances: object) -> int:
    """Sum every bank balance amount (string-safe; garbage counts as zero)."""
    return sum(_amount(entry) for entry in _entries(balances))


def custody_excluding(balances: object, gov_denom: str) -> int:
    """Sum bank balances outside the governance denom (the capture stake)."""
    total = 0
    for entry in _entries(balances):
        if isinstance(entry, dict) and str(entry.get("denom", "")) != gov_denom:
            total += _amount(entry)
    return total


def _deposit(deposits: object) -> tuple[str, int]:
    """First (denom, amount) pair of a proposal's ``total_deposit`` list."""
    if not isinstance(deposits, list) or not deposits:
        return "", 0
    first = deposits[0]
    if not isinstance(first, dict):
        return "", 0
    return str(first.get("denom", "")), _amount(first)


def proposal_summary(proposal: object) -> dict[str, object]:
    """Reduce one gov proposal record to id, deposit, flags, and targets.

    Args:
        proposal: One record from a ``/cosmos/gov/v1/proposals`` response.

    Returns:
        ``{"id", "deposit_denom", "deposit_amount", "messages", "targets"}``;
        an empty dict when the record is not a mapping.
    """
    if not isinstance(proposal, dict):
        return {}
    raw = proposal.get("messages")
    messages = list(raw) if isinstance(raw, list) else []
    denom, amount = _deposit(proposal.get("total_deposit"))
    return {
        "id": str(proposal.get("id", "")),
        "deposit_denom": denom,
        "deposit_amount": amount,
        "messages": gov_capture_flags(messages),
        "targets": gov_capture_targets(messages),
    }


@dataclass(frozen=True)
class GovRow:
    """One governance proposal target with its custody readings."""

    proposal: str
    target: str = ""
    flags: tuple[str, ...] = ()
    custody_total: int = 0
    non_gov_custody: int = 0
    capture_risk: bool = False


@dataclass(frozen=True)
class CosmosGovReport:
    """Governance-capture screen over one Cosmos LCD endpoint."""

    lcd: str
    rows: tuple[GovRow, ...] = ()

    def render_markdown(self) -> str:
        """Render the screen exactly as the CLI text output does."""
        lines: list[str] = [f"# Cosmos gov capture - {self.lcd}", ""]
        if not self.rows:
            lines.append("- no voting proposals carry wasm admin/migrate/exec messages")
        for row in self.rows:
            verdict = "capture-risk" if row.capture_risk else "no-risk"
            target = row.target or "(code-only)"
            lines.append(
                f"- proposal {row.proposal} target {target}: {verdict}; "
                f"custody {row.custody_total}, non-gov {row.non_gov_custody}"
            )
            if row.flags:
                lines.append("  flags: " + ", ".join(row.flags))
        return "\n".join(lines)
