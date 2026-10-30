"""Request value objects for API functions beyond the five-argument ceiling."""

from __future__ import annotations

from dataclasses import dataclass, field

from ruin.core.flashloan import DEFAULT_FLASHLOAN_AMOUNT
from ruin.core.oracle import DEFAULT_SWAP_AMOUNT


@dataclass(frozen=True)
class ScreenRequest:
    """Inputs for ``ruin.target.screen``."""

    name: str
    chain: str
    tvl: str = "0"
    source: str = "none"
    bespoke: bool = False
    custodial: bool = False
    listed: str | None = None


@dataclass(frozen=True)
class HuntRequest:
    """Inputs for ``ruin.target.hunt``: funded-holder sweep windowing.

    ``also`` adds extra tokens to scan; ``from_block``/``to_block`` pin a
    block window (``to_block=0`` means ``from_block + blocks``).
    """

    token: str
    chain: str = "ethereum"
    blocks: int = 1500
    min_usd: float = 2000.0
    limit: int = 40
    rpc: str | None = None
    also: tuple[str, ...] = ()
    from_block: int | None = None
    to_block: int = 0


@dataclass(frozen=True)
class PocRequest:
    """Inputs for ``ruin.verify.poc``: the fork PoC pipeline."""

    recon_file: str
    name: str
    forge_test: str
    method: str
    rpc: str
    mode: str = "research"
    fork_block: int | None = None
    private_key: str | None = None
    min_tvl: int | None = None
    vulns: str | None = None


@dataclass(frozen=True)
class RunnerRequest:
    """Inputs for the fuzz and symbolic recorders and executors.

    ``run`` switches ``ruin.verify.fuzz`` / ``ruin.verify.symbolic`` from
    recording a result to executing the runner with the tool-shaped fields.
    An empty ``tool`` resolves per operation: ``foundry`` for fuzz,
    ``halmos`` for symbolic (the CLI defaults).
    """

    target: str
    tool: str = ""
    kind: str = "invariant"
    match_test: str | None = None
    tool_command: list[str] | None = None
    outcome: str | None = None
    detail: str = ""
    finding: str | None = None
    linked_finding: str | None = None
    run: bool = False


@dataclass(frozen=True)
class TriageRequest:
    """Inputs for ``ruin.source.triage`` (CLI ``source triage --mode``)."""

    name: str
    mode: str = "checks"
    checks: list[str] = field(default_factory=list)
    file: str | None = None
    source_path: str | None = None
    signals: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ThinRequest:
    """Inputs for ``ruin.classes.thin_collateral``."""

    token: str
    market: str
    factory: str
    price_usd: float
    blocks: int = 3000
    min_usd: float = 50000.0


@dataclass(frozen=True)
class BlockWindow:
    """Inclusive block range used by chain-log reads."""

    from_block: int
    to_block: int


@dataclass(frozen=True)
class FindingDraft:
    """Inputs for ``ruin.finding.create``."""

    finding_id: str
    title: str
    file: str
    severity: str = ""
    confidence: int = 0
    evidence: list[str] = field(default_factory=list)
    contract: str = ""


@dataclass(frozen=True)
class OracleRequest:
    """Inputs for ``ruin.verify.oracle`` scaffold generation."""

    target: str
    rpc: str
    chain: str | None = None
    router: str | None = None
    reserve_a: str | None = None
    reserve_b: str | None = None
    oracle: str | None = None
    swap_amount: str = DEFAULT_SWAP_AMOUNT
    min_deviation: str = "1 ether"


@dataclass(frozen=True)
class FlashloanRequest:
    """Inputs for ``ruin.verify.flashloan`` scaffold generation."""

    target: str
    rpc: str
    chain: str | None = None
    asset: str | None = None
    amount: str = DEFAULT_FLASHLOAN_AMOUNT
    pool: str | None = None


@dataclass(frozen=True)
class ProtocolRequest:
    """Inputs for the ``ruin.protocol`` namespace (CLI ``protocol *``)."""

    address: str
    chain: str = "ethereum"
    rpc: str | None = None
