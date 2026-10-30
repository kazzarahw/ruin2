"""Enumerations used across the ``ruin`` domain."""

from __future__ import annotations

from enum import Enum

from ruin.core.chains import EVM_CHAIN_IDS


class TargetMode(Enum):
    """How a target is authorized to be researched and run."""

    OWN = "Own"
    AUTHORIZED = "Authorized"
    RESEARCH = "Research"


class CredentialsRef(Enum):
    """A pure reference to the signing credentials for a run."""

    NONE = "None"
    OWN = "Own"


class Severity(Enum):
    """The severity of a finding."""

    INFORMATIONAL = "Informational"
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


class SourceAccess(Enum):
    """The source accessibility of a target's contracts."""

    PUBLIC = "Public"
    EXPLORER_VERIFIED = "ExplorerVerified"
    NONE = "None"


class FuzzKind(Enum):
    """The kind of fuzz task."""

    FUZZ = "Fuzz"
    INVARIANT = "Invariant"


class FuzzOutcome(Enum):
    """The outcome of a fuzz run."""

    PASSED = "Passed"
    VIOLATED = "Violated"
    ERRORED = "Errored"


FUZZ_KIND_BY_NAME: dict[str, FuzzKind] = {
    "fuzz": FuzzKind.FUZZ,
    "invariant": FuzzKind.INVARIANT,
}
FUZZ_OUTCOME_BY_NAME: dict[str, FuzzOutcome] = {
    "passed": FuzzOutcome.PASSED,
    "violated": FuzzOutcome.VIOLATED,
    "errored": FuzzOutcome.ERRORED,
}
SOURCE_ACCESS_BY_NAME: dict[str, SourceAccess] = {
    "public": SourceAccess.PUBLIC,
    "explorer": SourceAccess.EXPLORER_VERIFIED,
}


class SymbolicOutcome(Enum):
    """The outcome of a symbolic execution run."""

    PROVEN = "Proven"
    UNDECIDED = "Undecided"
    UNSUPPORTED = "Unsupported"
    ERROR = "Error"


class TriageVerdict(Enum):
    """A triaged slither finding verdict."""

    NOISE = "Noise"
    LEAD = "Lead"
    UNKNOWN = "Unknown"


class Chain(Enum):
    """A supported blockchain family."""

    EVM = "EVM"
    SOLANA = "Solana"
    MOVE = "Move"
    CAIRO = "Cairo"
    COSMWASM = "CosmWasm"
    TON = "TON"


_CHAIN_ALIASES: dict[str, str] = {
    "ethereum": "EVM",
    "mainnet": "EVM",
    "eth": "EVM",
    "bsc": "EVM",
    "binance": "EVM",
    "bnb": "EVM",
    "polygon": "EVM",
    "matic": "EVM",
    "optimism": "EVM",
    "op": "EVM",
    "base": "EVM",
    "arbitrum": "EVM",
    "arb": "EVM",
    "avax": "EVM",
    "avalanche": "EVM",
    "cronos": "EVM",
    "blast": "EVM",
    "sol": "SOLANA",
    "cosmwasm": "COSMWASM",
}


def chain_from_name(value: object) -> Chain:
    """Resolve a chain name into a Chain member, case-insensitively.

    Popular chain names (ethereum, polygon, arbitrum, ...) alias to EVM;
    the numeric chain id distinguishes them downstream.

    Raises:
        ValueError: If the name matches no chain or alias.
    """
    needle = str(value or "EVM").strip().lower()
    needle = _CHAIN_ALIASES.get(needle, needle).lower()
    for member in Chain:
        if member.name.lower() == needle or member.value.lower() == needle:
            return member
    if needle in EVM_CHAIN_IDS:
        return Chain.EVM
    raise ValueError(f"unknown chain: {value}")


class Language(Enum):
    """A supported smart-contract language."""

    SOLIDITY = "Solidity"
    VYPER = "Vyper"
    RUST = "Rust"
    MOVE = "Move"
    CAIRO = "Cairo"
    COSMWASM = "CosmWasm"


class VulnClass:
    """The class of a vulnerability."""

    REENTRANCY: VulnClass
    ACCESS_CONTROL: VulnClass
    SIGNATURE_TUNNELING: VulnClass
    ASSET_ACCOUNTING: VulnClass
    FLASH_LOAN: VulnClass
    LOGIC: VulnClass

    def __init__(self, name: str, detail: str | None = None) -> None:
        """Initialize the vuln class."""
        self.name = name
        self.detail = detail

    def __eq__(self, other: object) -> bool:
        """Return equality."""
        if not isinstance(other, VulnClass):
            return False
        return self.name == other.name and self.detail == other.detail

    def __hash__(self) -> int:
        """Return hash."""
        return hash((self.name, self.detail))

    def __str__(self) -> str:
        """Return the string form."""
        if self.detail is None:
            return self.name
        return f'Other("{self.detail}")'

    @classmethod
    def other(cls, value: str) -> VulnClass:
        """Build an ``Other`` vuln class."""
        return cls("Other", value)

    OTHER = other

    def is_other(self) -> bool:
        """Return whether this is an ``Other`` class."""
        return self.detail is not None


VulnClass.REENTRANCY = VulnClass("Reentrancy")
VulnClass.ACCESS_CONTROL = VulnClass("AccessControl")
VulnClass.SIGNATURE_TUNNELING = VulnClass("SignatureTunneling")
VulnClass.ASSET_ACCOUNTING = VulnClass("AssetAccounting")
VulnClass.FLASH_LOAN = VulnClass("FlashLoan")
VulnClass.LOGIC = VulnClass("Logic")


class CallArg:
    """A single argument to an exploit call, by value type."""

    def __init__(self, kind: str, value: object) -> None:
        """Initialize the call arg."""
        self.kind = kind
        self.value = value

    @classmethod
    def address(cls, value: object) -> CallArg:
        """Build an address argument."""
        return cls("Address", value)

    @classmethod
    def uint(cls, value: int) -> CallArg:
        """Build an unsigned-integer argument."""
        return cls("Uint", value)

    @classmethod
    def boolean(cls, value: bool) -> CallArg:
        """Build a boolean argument."""
        return cls("Bool", value)

    @classmethod
    def raw_bytes(cls, value: object) -> CallArg:
        """Build a raw-bytes argument."""
        return cls("Bytes", value)

    @classmethod
    def string(cls, value: str) -> CallArg:
        """Build a string argument."""
        return cls("String", value)

    @classmethod
    def bytes(cls, value: object) -> CallArg:
        """Build a raw-bytes argument."""
        return cls("Bytes", value)
