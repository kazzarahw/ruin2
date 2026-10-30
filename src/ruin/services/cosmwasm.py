"""CosmWasm chain adapter for ``ruin``."""

from __future__ import annotations

import base64
from typing import TYPE_CHECKING, cast

from ruin.core.enums import Chain
from ruin.core.ids import validate_address
from ruin.core.onchain import AccountInfo, BytecodeInfo, SourceInfo

if TYPE_CHECKING:
    from ruin.services.rpc import RpcTransport


class CosmwasmAdapter:
    """Adapter for CosmWasm contracts, backed by Cosmos SDK REST endpoints."""

    chain = Chain.COSMWASM

    def __init__(self, transport: RpcTransport) -> None:
        """Initialize the adapter with an RPC transport."""
        self.transport = transport

    def validate_address(self, address: str) -> str:
        """Validate and normalize a bech32 CosmWasm address."""
        return validate_address(Chain.COSMWASM, address)

    def fetch_account(self, address: str, rpc: str) -> AccountInfo:
        """Fetch the contract record and the first bank balance for an address."""
        contract = self.transport.get_json(f"{rpc}/cosmwasm/wasm/v1/contract/{address}")
        contract_info = _contract_info(contract)
        balance = _first_balance(
            self.transport.get_json(f"{rpc}/cosmos/bank/v1beta1/balances/{address}")
        )
        label = ""
        if contract_info is not None:
            label = str(contract_info.get("label", ""))
        return AccountInfo(
            chain=Chain.COSMWASM,
            address=address,
            exists=contract_info is not None,
            balance_native=balance,
            raw=contract_info if contract_info is not None else {},
            note=f"label={label}" if label else "",
        )

    def fetch_bytecode(self, address: str, rpc: str) -> BytecodeInfo:
        """Fetch raw contract code bytes (base64) for a contract address."""
        contract = self.transport.get_json(f"{rpc}/cosmwasm/wasm/v1/contract/{address}")
        contract_info = _contract_info(contract)
        code_id = ""
        if contract_info is not None:
            code_id = str(contract_info.get("code_id", ""))
        data = b""
        if code_id:
            code = self.transport.get_json(f"{rpc}/cosmwasm/wasm/v1/code/{code_id}/raw")
            blob = code.get("data") if isinstance(code, dict) else None
            if isinstance(blob, str):
                try:
                    data = base64.b64decode(blob)
                except (ValueError, TypeError):
                    data = b""
        return BytecodeInfo(
            chain=Chain.COSMWASM,
            address=address,
            kind="wasm",
            hexcode=data.hex() if data else "",
            size_bytes=len(data),
            note="contract code bytes (base64-decoded)" if data else "no contract code",
        )

    def fetch_source(self, address: str) -> SourceInfo | None:
        """Return an unverified placeholder; explorer verification is later."""
        return SourceInfo(
            chain=Chain.COSMWASM,
            address=address,
            language="CosmWasm",
            verified=False,
        )

    def analyzers(self) -> list[str]:
        """Return CosmWasm analyzers available to the toolkit."""
        return []


def _contract_info(doc: object) -> dict[str, object] | None:
    """Return the ``contract_info`` record from a REST response, if present."""
    if not isinstance(doc, dict):
        return None
    info = doc.get("contract_info")
    if not isinstance(info, dict):
        return None
    return cast("dict[str, object]", info)


def _first_balance(doc: object) -> str:
    """Return the first bank balance amount, or ``"0"`` when absent."""
    if not isinstance(doc, dict):
        return "0"
    balances = doc.get("balances")
    if not isinstance(balances, list) or not balances:
        return "0"
    first = balances[0]
    if not isinstance(first, dict):
        return "0"
    amount = first.get("amount")
    if isinstance(amount, (str, int)):
        return str(amount)
    return "0"
