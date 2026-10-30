"""Validated identifier value objects for ``ruin``."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from ruin.core.enums import Chain
from ruin.core.errors import (
    invalid_address,
    invalid_protocol_name,
    invalid_rpc_url,
)

if TYPE_CHECKING:
    from collections.abc import Callable

_EVM_ADDRESS_LENGTH = 40
_MAX_RPC_URL_LENGTH = 512
_MAX_PROTOCOL_NAME_LENGTH = 120
_MIN_SOLANA_ADDRESS_LENGTH = 32
_MAX_SOLANA_ADDRESS_LENGTH = 44
_MOVE_ADDRESS_LENGTH = 64
_MAX_CAIRO_ADDRESS_LENGTH = 64
_TON_RAW_HEX_LENGTH = 64
_TON_B64_LENGTH = 48
_TON_B64_PREFIXES = ("EQ", "UQ", "kQ", "0Q")


@dataclass(frozen=True)
class ContractId:
    """A validated, lowercased EVM contract address."""

    value: str

    @classmethod
    def new(cls, address: str) -> ContractId:
        """Validate and normalize an EVM contract address.

        Args:
            address: The raw address string.

        Returns:
            A normalized ``ContractId``.

        Raises:
            ValueError: If the address is not ``0x`` plus 40 hex digits.
        """
        raw = address
        if not raw.startswith("0x"):
            raise invalid_address(raw)
        rest = raw[2:]
        if len(rest) != _EVM_ADDRESS_LENGTH or not all(
            c in "0123456789abcdefABCDEF" for c in rest
        ):
            raise invalid_address(raw)
        return cls(f"0x{rest.lower()}")

    def as_str(self) -> str:
        """Return the normalized address."""
        return self.value

    def __str__(self) -> str:
        """Return the string value."""
        return self.value


@dataclass(frozen=True)
class RpcUrl:
    """A validated RPC endpoint URL."""

    value: str

    @classmethod
    def new(cls, url: str) -> RpcUrl:
        """Validate an RPC endpoint URL.

        Args:
            url: The raw URL string.

        Returns:
            A validated ``RpcUrl``.

        Raises:
            ValueError: If the URL is blank, too long, or contains whitespace.
        """
        raw = url
        trimmed = raw.strip()
        if (
            not trimmed
            or len(trimmed) > _MAX_RPC_URL_LENGTH
            or "\n" in trimmed
            or any(c.isspace() for c in trimmed)
        ):
            raise invalid_rpc_url(raw)
        return cls(trimmed)

    def as_str(self) -> str:
        """Return the validated URL."""
        return self.value

    def __str__(self) -> str:
        """Return the string value."""
        return self.value


@dataclass(frozen=True)
class ProtocolName:
    """A validated, single-line protocol name."""

    value: str

    @classmethod
    def new(cls, name: str) -> ProtocolName:
        """Validate a protocol name.

        Args:
            name: The raw name string.

        Returns:
            A validated ``ProtocolName``.

        Raises:
            ValueError: If the name is blank, too long, or multiline.
        """
        raw = name
        trimmed = raw.strip()
        if not trimmed or len(trimmed) > _MAX_PROTOCOL_NAME_LENGTH or "\n" in trimmed:
            raise invalid_protocol_name(raw)
        return cls(trimmed)

    def as_str(self) -> str:
        """Return the validated name."""
        return self.value

    def __str__(self) -> str:
        """Return the string value."""
        return self.value


def _is_base58(value: str) -> bool:
    alphabet = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
    return bool(value) and all(char in alphabet for char in value)


def _validate_evm(address: str) -> str:
    return ContractId.new(address).as_str()


def _validate_solana(address: str) -> str:
    if (
        not _is_base58(address)
        or len(address) < _MIN_SOLANA_ADDRESS_LENGTH
        or len(address) > _MAX_SOLANA_ADDRESS_LENGTH
    ):
        raise invalid_address(address)
    return address


def _validate_move(address: str) -> str:
    raw = address
    if not raw.startswith("0x"):
        raise invalid_address(raw)
    rest = raw[2:]
    if len(rest) != _MOVE_ADDRESS_LENGTH or not all(
        c in "0123456789abcdefABCDEF" for c in rest
    ):
        raise invalid_address(raw)
    return f"0x{rest.lower()}"


def _validate_cairo(address: str) -> str:
    raw = address
    if not raw.startswith("0x"):
        raise invalid_address(raw)
    rest = raw[2:]
    if (
        not rest
        or len(rest) > _MAX_CAIRO_ADDRESS_LENGTH
        or not all(c in "0123456789abcdefABCDEF" for c in rest)
    ):
        raise invalid_address(raw)
    return f"0x{rest.lower()}"


def _validate_cosmwasm(address: str) -> str:
    if not re.fullmatch(
        r"[a-z0-9]{1,83}1[023456789acdefghjklmnpqrstuvwxyz]{6,100}", address
    ):
        raise invalid_address(address)
    return address


def _validate_ton(address: str) -> str:
    raw = address
    if raw.startswith(("0:", "-1:")):
        raw = raw.split(":", 1)[1]
    hex_part = raw.removeprefix("0x")
    if len(hex_part) == _TON_RAW_HEX_LENGTH and all(
        c in "0123456789abcdefABCDEF" for c in hex_part
    ):
        return f"0:{hex_part.lower()}"
    if len(raw) == _TON_B64_LENGTH and raw.startswith(_TON_B64_PREFIXES):
        return raw
    raise invalid_address(address)


_VALIDATOR_BY_CHAIN: dict[Chain, Callable[[str], str]] = {
    Chain.EVM: _validate_evm,
    Chain.SOLANA: _validate_solana,
    Chain.MOVE: _validate_move,
    Chain.CAIRO: _validate_cairo,
    Chain.COSMWASM: _validate_cosmwasm,
    Chain.TON: _validate_ton,
}


def validate_address(chain: Chain, address: str) -> str:
    """Validate an address for the given chain."""
    validator = _VALIDATOR_BY_CHAIN.get(chain)
    if validator is None:
        raise ValueError(f"unsupported chain: {chain.value}")
    return validator(address)
