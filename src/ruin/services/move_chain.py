"""Move (Aptos-style REST) chain adapter for ``ruin``."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from ruin.core.enums import Chain
from ruin.core.ids import validate_address
from ruin.core.onchain import AccountInfo, BytecodeInfo, SourceInfo

if TYPE_CHECKING:
    from ruin.services.rpc import RpcTransport


class MoveAdapter:
    """Adapter for Move chains, backed by Aptos-style REST endpoints."""

    chain = Chain.MOVE

    def __init__(self, transport: RpcTransport) -> None:
        """Initialize the adapter with an RPC transport."""
        self.transport = transport

    def validate_address(self, address: str) -> str:
        """Validate and normalize a 0x-prefixed Move account address."""
        return validate_address(Chain.MOVE, address)

    def fetch_account(self, address: str, rpc: str) -> AccountInfo:
        """Fetch the account record from the REST accounts endpoint."""
        doc = self.transport.get_json(f"{rpc}/accounts/{address}")
        data = doc.get("data") if isinstance(doc, dict) else None
        exists = isinstance(data, dict) and bool(data)
        balance = "0"
        sequence = ""
        raw: dict[str, object] = {}
        if isinstance(data, dict):
            raw = cast("dict[str, object]", data)
            balance = str(data.get("amount", "0"))
            sequence = str(data.get("sequence_number", ""))
        return AccountInfo(
            chain=Chain.MOVE,
            address=address,
            exists=exists,
            balance_native=balance,
            raw=raw,
            note=f"sequence_number={sequence}",
        )

    def fetch_bytecode(self, address: str, rpc: str) -> BytecodeInfo:
        """Fetch the first published module bytecode for an account."""
        doc = self.transport.get_json(f"{rpc}/accounts/{address}/modules")
        hexcode = _first_bytecode(doc)
        size_bytes = len(hexcode.removeprefix("0x")) // 2
        return BytecodeInfo(
            chain=Chain.MOVE,
            address=address,
            kind="move",
            hexcode=hexcode,
            size_bytes=size_bytes,
            note="first module bytecode" if hexcode else "no modules",
        )

    def fetch_source(self, address: str) -> SourceInfo | None:
        """Return a Move source placeholder; verified source is a later step."""
        return SourceInfo(
            chain=Chain.MOVE,
            address=address,
            language="Move",
            verified=False,
        )

    def analyzers(self) -> list[str]:
        """Return Move analyzers available to the toolkit."""
        return []


def _first_bytecode(doc: object) -> str:
    """Return the bytecode hex of the first module carrying one, if any."""
    if not isinstance(doc, list):
        return ""
    for module in doc:
        if isinstance(module, dict):
            code = module.get("bytecode")
            if isinstance(code, str) and code:
                return code
    return ""
