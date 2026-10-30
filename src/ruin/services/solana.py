"""Solana chain adapter for ``ruin``."""

from __future__ import annotations

import base64
from typing import TYPE_CHECKING, cast

from ruin.core.enums import Chain
from ruin.core.ids import validate_address
from ruin.core.onchain import AccountInfo, BytecodeInfo, SourceInfo
from ruin.services.rpc import jsonrpc

VERIFY_API = "https://verify.osec.io/status/"

if TYPE_CHECKING:
    from ruin.services.rpc import RpcTransport


class SolanaAdapter:
    """Adapter for Solana, backed by cluster JSON-RPC."""

    chain = Chain.SOLANA

    def __init__(self, transport: RpcTransport) -> None:
        """Initialize the adapter with an RPC transport."""
        self.transport = transport

    def validate_address(self, address: str) -> str:
        """Validate and normalize a base58 Solana address."""
        return validate_address(Chain.SOLANA, address)

    def fetch_account(self, address: str, rpc: str) -> AccountInfo:
        """Fetch the lamport balance and account record for an address.

        Uses jsonParsed encoding so SPL mint accounts expose their
        mint/freeze authorities alongside the raw record.
        """
        balance = jsonrpc(self.transport, rpc, "getBalance", [address])
        info = jsonrpc(
            self.transport, rpc, "getAccountInfo", [address, {"encoding": "jsonParsed"}]
        )
        value = info.get("value") if isinstance(info, dict) else None
        exists = value is not None
        owner = ""
        executable = False
        extra = ""
        if isinstance(value, dict):
            owner = str(value.get("owner", ""))
            executable = bool(value.get("executable", False))
            extra = _mint_note(cast("dict[str, object]", value))
        return AccountInfo(
            chain=Chain.SOLANA,
            address=address,
            exists=exists,
            balance_native=str(balance.get("value", 0))
            if isinstance(balance, dict)
            else "0",
            raw=cast("dict[str, object]", value) if isinstance(value, dict) else {},
            note=f"owner={owner} executable={executable}{extra}",
        )

    def fetch_bytecode(self, address: str, rpc: str) -> BytecodeInfo:
        """Fetch program bytes (base64 BPF) for an executable account."""
        info = jsonrpc(
            self.transport, rpc, "getAccountInfo", [address, {"encoding": "base64"}]
        )
        value = info.get("value") if isinstance(info, dict) else None
        data = _decode_data(value)
        return BytecodeInfo(
            chain=Chain.SOLANA,
            address=address,
            kind="bpf",
            hexcode=data.hex() if data else "",
            size_bytes=len(data),
            note="BPF program bytes (base64-decoded)" if data else "no program data",
        )

    def fetch_source(self, address: str) -> SourceInfo | None:
        """Look up verified-build status from the Osec verification API.

        The keyless ``verify.osec.io/status`` endpoint reports whether the
        on-chain program hash matches a reproducible build of a public
        repository; verified programs get the repository URL attached.
        """
        status = self.transport.get_json(f"{VERIFY_API}{address}")
        verified = bool(isinstance(status, dict) and status.get("is_verified"))
        url = ""
        if verified and isinstance(status, dict):
            repo = str(status.get("repo_url", ""))
            commit = str(status.get("commit", ""))
            if commit in {"", "None"}:
                commit = ""
            url = f"{repo}/commit/{commit}" if repo and commit else repo
        return SourceInfo(
            chain=Chain.SOLANA,
            address=address,
            language="Rust/Anchor",
            url=url,
            verified=verified,
        )

    def analyzers(self) -> list[str]:
        """Return Solana analyzers available to the toolkit."""
        return ["anchor-check"]


def _mint_note(value: dict[str, object]) -> str:
    """Describe SPL mint authorities when the parsed record exposes them."""
    inner = value.get("data")
    if not isinstance(inner, dict):
        return ""
    parsed = inner.get("parsed")
    if not isinstance(parsed, dict) or parsed.get("type") != "mint":
        return ""
    info = parsed.get("info")
    if not isinstance(info, dict):
        return ""
    mint_auth = info.get("mintAuthority") or "NONE"
    freeze_auth = info.get("freezeAuthority") or "NONE"
    supply = str(info.get("supply", "?"))
    flags = []
    if mint_auth != "NONE":
        flags.append("infinite-mint-possible")
    if freeze_auth != "NONE":
        flags.append("transfer-freeze-possible")
    flag_text = f" flags={','.join(flags)}" if flags else " flags=renounced"
    return (
        f" mintAuthority={mint_auth} freezeAuthority={freeze_auth}"
        f" supply={supply}{flag_text}"
    )


def _decode_data(value: object) -> bytes:
    """Decode Solana account data, which may be base64 or base58 framed."""
    if not isinstance(value, dict):
        return b""
    payload = _data_payload(value.get("data"))
    if payload is None:
        return b""
    blob, encoding = payload
    if encoding != "base64":
        return b""
    try:
        return base64.b64decode(blob)
    except (ValueError, TypeError):
        return b""


def _data_payload(data: object) -> tuple[str, str] | None:
    """Return the (blob, encoding) pair for account data, if present."""
    if isinstance(data, list) and data and isinstance(data[0], str):
        encoding = data[1] if len(data) > 1 else "base64"
        return data[0], str(encoding)
    if isinstance(data, str):
        return data, "base64"
    return None
