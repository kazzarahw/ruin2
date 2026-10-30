"""Chain adapters for ``ruin``.

``ChainAdapter`` is the service-boundary contract every chain implements:
address validation plus the raw on-chain reads (account, program bytes,
source) that feed a :class:`~ruin.core.onchain.ChainDigest`. ``get_adapter``
returns the adapter for a chain, importing chain modules lazily so importing
``ruin`` stays cheap.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, cast

from ruin.core.enums import Chain
from ruin.core.ids import validate_address
from ruin.core.onchain import AccountInfo, BytecodeInfo, SourceInfo
from ruin.services.rpc import SHARED_TRANSPORT, RpcTransport
from ruin.services.subprocesses import (
    cast_code_command,
    cast_native_balance_command,
    run_command,
)

FAMILY_DEFAULT_RPCS: dict[Chain, str] = {
    Chain.SOLANA: "https://api.mainnet-beta.solana.com",
    Chain.TON: "https://toncenter.com",
}


def rpc_for_family(chain: Chain) -> str:
    """Public default RPC for a chain family, or empty string when none."""
    return FAMILY_DEFAULT_RPCS.get(chain, "")


if TYPE_CHECKING:
    from collections.abc import Callable

    from ruin.core.decode import DecodedBytecode

_ANALYZER_BY_CHAIN: dict[Chain, list[str]] = {
    Chain.EVM: ["slither", "semgrep"],
    Chain.SOLANA: ["anchor-check"],
    Chain.MOVE: [],
    Chain.CAIRO: [],
    Chain.COSMWASM: [],
    Chain.TON: [],
}


class ChainAdapter(Protocol):
    """A chain-specific validator and on-chain read provider."""

    chain: Chain

    def validate_address(self, address: str) -> str:
        """Validate and normalize an address."""

    def fetch_account(self, address: str, rpc: str) -> AccountInfo:
        """Fetch the account or program record for an address."""

    def fetch_bytecode(self, address: str, rpc: str) -> BytecodeInfo:
        """Fetch deployed program bytes for an address."""

    def fetch_source(self, address: str) -> SourceInfo | None:
        """Fetch verified source or an interface definition, if any."""

    def analyzers(self) -> list[str]:
        """Return chain-native analyzer names available to the toolkit."""


class EvmChainAdapter:
    """Adapter for EVM chains, backed by Foundry ``cast``."""

    chain = Chain.EVM

    def validate_address(self, address: str) -> str:
        """Validate and normalize an EVM address."""
        return validate_address(Chain.EVM, address)

    def fetch_account(self, address: str, rpc: str) -> AccountInfo:
        """Fetch the native balance and existence of an address."""
        code = run_command(cast_code_command(rpc, address)).stdout.strip()
        balance = run_command(cast_native_balance_command(rpc, address)).stdout.strip()
        exists = bool(code) and code != "0x"
        return AccountInfo(
            chain=Chain.EVM,
            address=address,
            exists=exists,
            balance_native=balance,
            note="balance in wei",
        )

    def fetch_bytecode(self, address: str, rpc: str) -> BytecodeInfo:
        """Fetch deployed bytecode and decode EVM selectors."""
        from ruin.core.decode import decode_bytecode

        code = run_command(cast_code_command(rpc, address)).stdout.strip()
        hexcode = code or "0x"
        raw = hexcode.removeprefix("0x")
        decoded: DecodedBytecode = decode_bytecode(hexcode)
        return BytecodeInfo(
            chain=Chain.EVM,
            address=address,
            kind="evm",
            hexcode=hexcode,
            size_bytes=len(raw) // 2,
            decoded=decoded,
        )

    def fetch_source(self, address: str) -> SourceInfo | None:
        """Return an unverified placeholder; verified source comes from ingestion."""
        return SourceInfo(
            chain=Chain.EVM,
            address=address,
            language="Solidity",
            verified=False,
        )

    def analyzers(self) -> list[str]:
        """Return EVM analyzers available to the toolkit."""
        return list(_ANALYZER_BY_CHAIN[Chain.EVM])


_ADAPTER_BY_CHAIN: dict[Chain, str] = {
    Chain.SOLANA: "ruin.services.solana:SolanaAdapter",
    Chain.MOVE: "ruin.services.move_chain:MoveAdapter",
    Chain.CAIRO: "ruin.services.cairo:CairoAdapter",
    Chain.COSMWASM: "ruin.services.cosmwasm:CosmwasmAdapter",
    Chain.TON: "ruin.services.ton:TonAdapter",
}


def get_adapter(chain: Chain, transport: RpcTransport | None = None) -> ChainAdapter:
    """Return an adapter for the given chain.

    Args:
        chain: The chain to build an adapter for.
        transport: Optional transport injected into non-EVM adapters.

    Returns:
        A chain adapter implementing the :class:`ChainAdapter` contract.

    Raises:
        ValueError: If no adapter exists for the chain.
    """
    if chain is Chain.EVM:
        return EvmChainAdapter()
    spec = _ADAPTER_BY_CHAIN.get(chain)
    if spec is None:
        raise ValueError(f"no adapter for chain: {chain.value}")
    module_path, class_name = spec.split(":")
    module = __import__(module_path, fromlist=[class_name])
    adapter_class = getattr(module, class_name)
    factory = cast("Callable[[RpcTransport], ChainAdapter]", adapter_class)
    return factory(transport or SHARED_TRANSPORT)


def default_rpc(chain: Chain) -> str:
    """Public default RPC for a chain, or empty string when none is usable."""
    return rpc_for_family(chain)
