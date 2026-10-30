"""Cairo (Starknet JSON-RPC) chain adapter for ``ruin``."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from ruin.core.decode import DecodedBytecode
from ruin.core.enums import Chain
from ruin.core.ids import validate_address
from ruin.core.onchain import AccountInfo, BytecodeInfo, SourceInfo
from ruin.services.rpc import jsonrpc

if TYPE_CHECKING:
    from ruin.services.rpc import RpcTransport

_LATEST_BLOCK = "latest"
_ETH_FEE_CONTRACT = "0x049d36570d4e46f48e99674bd3fcc84644ddd6b96f7c741b1562b82f9e004dc7"


class CairoAdapter:
    """Adapter for Cairo contracts, backed by Starknet JSON-RPC."""

    chain = Chain.CAIRO

    def __init__(self, transport: RpcTransport) -> None:
        """Initialize the adapter with an RPC transport."""
        self.transport = transport

    def validate_address(self, address: str) -> str:
        """Validate and normalize a 0x-prefixed Starknet contract address."""
        return validate_address(Chain.CAIRO, address)

    def fetch_account(self, address: str, rpc: str) -> AccountInfo:
        """Fetch the account nonce and ETH fee-token balance for an address."""
        nonce = jsonrpc(
            self.transport, rpc, "starknet_getNonce", [_LATEST_BLOCK, address]
        )
        balance = jsonrpc(
            self.transport,
            rpc,
            "starknet_getBalance",
            [_LATEST_BLOCK, address, _ETH_FEE_CONTRACT],
        )
        raw: dict[str, object] = {}
        note = ""
        if nonce is not None:
            raw = {"nonce": nonce}
            note = f"nonce={nonce}"
        return AccountInfo(
            chain=Chain.CAIRO,
            address=address,
            exists=nonce is not None,
            balance_native=_balance_str(balance),
            raw=raw,
            note=note,
        )

    def fetch_bytecode(self, address: str, rpc: str) -> BytecodeInfo:
        """Fetch entry-point selectors for the class deployed at an address."""
        class_at = jsonrpc(
            self.transport, rpc, "starknet_getClassAt", [_LATEST_BLOCK, address]
        )
        record = _class_record(class_at)
        if record is None:
            return BytecodeInfo(
                chain=Chain.CAIRO,
                address=address,
                kind="cairo",
                note="no class at address",
            )
        selectors = _entry_point_selectors(record)
        return BytecodeInfo(
            chain=Chain.CAIRO,
            address=address,
            kind="cairo",
            decoded=DecodedBytecode(selectors=selectors, strings=[]),
            note="class program is compressed; entry-point selectors only",
        )

    def fetch_source(self, address: str) -> SourceInfo | None:
        """Return an unverified placeholder; explorer verification is later."""
        return SourceInfo(
            chain=Chain.CAIRO,
            address=address,
            language="Cairo",
            verified=False,
        )

    def analyzers(self) -> list[str]:
        """Return Cairo analyzers available to the toolkit."""
        return []


def _class_record(doc: object) -> dict[str, object] | None:
    """Return the Starknet class record from a RPC result, if present."""
    if not isinstance(doc, dict):
        return None
    return cast("dict[str, object]", doc)


def _entry_point_selectors(record: dict[str, object]) -> list[str]:
    """Collect unique entry-point selectors from a class record."""
    grouped = record.get("entry_points_by_type")
    if not isinstance(grouped, dict):
        return []
    selectors: list[str] = []
    seen: set[str] = set()
    for group in grouped.values():
        if not isinstance(group, list):
            continue
        for point in group:
            if not isinstance(point, dict):
                continue
            selector = point.get("selector")
            if isinstance(selector, str) and selector and selector not in seen:
                seen.add(selector)
                selectors.append(selector)
    return selectors


def _balance_str(doc: object) -> str:
    """Return the fee-token balance as decimal text, ``"0"`` when absent."""
    amount: object = doc
    if isinstance(doc, dict):
        amount = doc.get("amount")
    if isinstance(amount, int):
        return str(amount)
    if isinstance(amount, str):
        return _to_decimal(amount)
    return "0"


def _to_decimal(value: str) -> str:
    """Convert a hex or decimal amount string to decimal text."""
    try:
        number = int(value, 16) if value.startswith("0x") else int(value)
    except ValueError:
        return "0"
    return str(number)
