"""Runner contracts for ``ruin``."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from ruin.core.domain import DrainProof, Poc, Target, Vuln
    from ruin.core.enums import CredentialsRef
    from ruin.core.ids import ContractId, RpcUrl


@dataclass
class RunConfig:
    """Configuration for a single parametric runner invocation."""

    target: Target
    poc: Poc
    rpc_url: RpcUrl
    credentials: CredentialsRef
    fork_block: int | None = None
    private_key: str | None = None
    measure_native: bool = False
    measure_tokens: list[ContractId] = field(default_factory=list)
    measure_slots: list[str] = field(default_factory=list)


@dataclass
class SlotDiff:
    """A storage-slot before/after pair."""

    slot: str
    before: str
    after: str


@dataclass
class RunOutput:
    """The measured result of a parametric runner invocation."""

    rpc_url: RpcUrl
    succeeded: bool
    drain: DrainProof | None
    summary: str
    all_drains: list[DrainProof] = field(default_factory=list)
    slot_diffs: list[SlotDiff] = field(default_factory=list)


class Runner(Protocol):
    """The parametric runner contract."""

    def run(self, config: RunConfig) -> RunOutput:
        """Run a PoC against its configured endpoint."""


class Analyzer(Protocol):
    """A chain-aware static analyzer."""

    def analyze(self, target: Target) -> list[Vuln]:
        """Analyze a target and return findings."""
