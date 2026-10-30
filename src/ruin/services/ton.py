"""TON chain adapter for ``ruin``."""

from __future__ import annotations

import base64
from typing import TYPE_CHECKING, cast

from ruin.core.enums import Chain
from ruin.core.ids import validate_address
from ruin.core.onchain import AccountInfo, BytecodeInfo, SourceInfo

if TYPE_CHECKING:
    from ruin.services.rpc import RpcTransport

_ACCOUNT_STATE_PATH = "/api/v2/getAccountState?address="


class TonAdapter:
    """Adapter for TON, backed by toncenter-style REST endpoints."""

    chain = Chain.TON

    def __init__(self, transport: RpcTransport) -> None:
        """Initialize the adapter with an RPC transport."""
        self.transport = transport

    def validate_address(self, address: str) -> str:
        """Validate and normalize a raw or base64url TON address."""
        return validate_address(Chain.TON, address)

    def fetch_account(self, address: str, rpc: str) -> AccountInfo:
        """Fetch the account state and native balance for an address."""
        doc = self._account_state_doc(address, rpc)
        state = str(doc.get("accountState", ""))
        account = doc.get("account")
        exists = state != "accNotExists" and isinstance(account, dict)
        return AccountInfo(
            chain=Chain.TON,
            address=address,
            exists=exists,
            balance_native=str(doc.get("balance", "0")),
            raw=doc,
            note=f"accountState={state}",
        )

    def fetch_bytecode(self, address: str, rpc: str) -> BytecodeInfo:
        """Fetch deployed contract code (base64 BOC) for an address."""
        doc = self._account_state_doc(address, rpc)
        code = _decode_code(doc)
        return BytecodeInfo(
            chain=Chain.TON,
            address=address,
            kind="ton",
            hexcode=code.hex() if code else "",
            size_bytes=len(code),
            note="TON contract code (base64 BOC decoded)" if code else "no code",
        )

    def fetch_source(self, address: str) -> SourceInfo | None:
        """Return an unverified placeholder; TON source lookup is external."""
        return SourceInfo(
            chain=Chain.TON,
            address=address,
            language="FunC/Tact",
            verified=False,
        )

    def analyzers(self) -> list[str]:
        """Return TON analyzers available to the toolkit."""
        return []

    def _account_state_doc(self, address: str, rpc: str) -> dict[str, object]:
        """GET the toncenter account-state document for an address."""
        doc = self.transport.get_json(f"{rpc}{_ACCOUNT_STATE_PATH}{address}")
        return cast("dict[str, object]", doc) if isinstance(doc, dict) else {}


def _decode_code(doc: dict[str, object]) -> bytes:
    """Decode the base64 BOC code cell from an account-state document."""
    account = doc.get("account")
    if not isinstance(account, dict):
        return b""
    state = account.get("state")
    if not isinstance(state, dict):
        return b""
    code = state.get("code")
    if not isinstance(code, str):
        return b""
    try:
        return base64.b64decode(code)
    except (ValueError, TypeError):
        return b""
