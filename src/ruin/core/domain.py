"""Core domain types for the ``ruin`` research pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING

from ruin.core.enums import Chain, Language
from ruin.core.ids import ContractId, ProtocolName

if TYPE_CHECKING:
    from ruin.core.enums import Severity, TargetMode, VulnClass
    from ruin.core.forensics import TransactionTrace
    from ruin.core.fuzz import FuzzResult
    from ruin.core.symbolic import SymbolicResult
    from ruin.core.value_objects import Amount, ExploitCall


@dataclass
class Target:
    """A protocol under research."""

    name: ProtocolName
    contracts: list[ContractId]
    tvl: Amount | None
    mode: TargetMode
    chain: Chain = field(default=Chain.EVM)
    language: Language = field(default=Language.SOLIDITY)
    kind: str = "contract"

    @classmethod
    def new(
        cls,
        name: str,
        contracts: list[ContractId],
        tvl: Amount | None,
        mode: TargetMode,
    ) -> Target:
        """Construct a target, validating the protocol name."""
        return cls(ProtocolName.new(name), contracts, tvl, mode)

    def with_ecosystem(self, chain: Chain, language: Language) -> Target:
        """Return a copy of this target scoped to a chain and language."""
        return replace(self, chain=chain, language=language)

    def is_well_formed(self) -> bool:
        """Return whether the target is well-formed."""
        return True


@dataclass
class Poc:
    """A proof-of-concept."""

    method: str
    calls: list[ExploitCall] = field(default_factory=list)
    expected_drain: Amount | None = None
    forge_test: str = ""

    def is_well_formed(self) -> bool:
        """Return whether the PoC is well-formed."""
        if not self.method.strip() or not self.forge_test.strip():
            return False
        return all(call.signature.strip() != "" for call in self.calls)


@dataclass
class DrainProof:
    """A measured drain on a fork."""

    method: str
    asset: ContractId
    amount: int

    @staticmethod
    def measure(
        method: str, asset: ContractId, before: int, after: int
    ) -> DrainProof | None:
        """Measure a drain from before/after balances."""
        delta = before - after if before >= after else 0
        if delta == 0:
            return None
        return DrainProof(method=method, asset=asset, amount=delta)


@dataclass
class Vuln:
    """A single vulnerability finding."""

    klass: VulnClass
    severity: Severity
    summary: str
    poc: Poc | None = None
    confidence: int = 0
    status: str = "open"

    def is_well_formed(self) -> bool:
        """Return whether the finding is well-formed."""
        if not self.summary.strip():
            return False
        if self.poc is None:
            return True
        return self.poc.is_well_formed()


@dataclass
class Report:
    """A deliverable report bundle."""

    protocol: Target
    vulns: list[Vuln] = field(default_factory=list)
    proofs: list[DrainProof] = field(default_factory=list)
    fuzz_results: list[FuzzResult] = field(default_factory=list)
    symbolic_results: list[SymbolicResult] = field(default_factory=list)
    transaction_traces: list[TransactionTrace] = field(default_factory=list)

    def render_markdown(self) -> str:
        """Render the report as Markdown."""
        lines: list[str] = []
        lines.append(f"# Security Research Report — {self.protocol.name.as_str()}")
        lines.append("")
        lines.append("## Scope")
        lines.append("")
        for contract in self.protocol.contracts:
            lines.append(f"- {contract.as_str()}")
        lines.append("")
        lines.append(f"Mode: {self.protocol.mode.value}")
        lines.append("")
        lines.append("## Findings")
        lines.append("")
        for number, vuln in enumerate(self.vulns):
            lines.append(f"### {number}. {vuln.klass} — {vuln.severity.value}")
            lines.append("")
            lines.append(vuln.summary)
            lines.append("")
            lines.append(f"Status: {vuln.status}")
            if vuln.confidence:
                lines.append(f"Confidence: {vuln.confidence}")
            lines.append("")
            if vuln.poc is not None:
                lines.append(
                    f"**PoC** (`{vuln.poc.method}`): fork test `{vuln.poc.forge_test}`"
                )
                for call in vuln.poc.calls:
                    lines.append(f"- `{call.signature}` on {call.target.as_str()}")
                lines.append("")
        if self.proofs:
            lines.append("## Proof of Drain (fork)")
            lines.append("")
            for proof in self.proofs:
                entry = (
                    f"- `{proof.method}`: {proof.amount} units of "
                    f"{proof.asset.as_str()}"
                )
                lines.append(entry)
            lines.append("")
        if self.fuzz_results:
            lines.append("## Fuzz Results")
            lines.append("")
            for fuzz in self.fuzz_results:
                lines.extend(_fuzz_result_lines(fuzz))
            lines.append("")
        _append_symbolic_results(lines, self.symbolic_results)
        _append_transaction_traces(lines, self.transaction_traces)
        return "\n".join(lines)


def _fuzz_result_lines(fuzz: FuzzResult) -> list[str]:
    """Render one fuzz result as report lines."""
    lines: list[str] = []
    lines.append(f"- **{fuzz.target}** — {fuzz.kind.value} — {fuzz.outcome.value}")
    if fuzz.detail:
        lines.append(f"  - Counter-example / detail: {fuzz.detail}")
    if fuzz.counterexample is not None:
        label = fuzz.counterexample.summary or fuzz.counterexample.raw
        if label:
            lines.append(f"  - Counterexample: {label}")
    if fuzz.linked_finding is not None or fuzz.finding is not None:
        value = fuzz.linked_finding or fuzz.finding
        lines.append(f"  - Linked finding: {value}")
    return lines


def _symbolic_result_lines(symbolic: SymbolicResult) -> list[str]:
    """Render one symbolic result as report lines."""
    lines: list[str] = []
    lines.append(
        f"- **{symbolic.target}** — {symbolic.tool} — {symbolic.outcome.value}"
    )
    if symbolic.detail:
        lines.append(f"  - Detail: {symbolic.detail}")
    if symbolic.counterexample is not None:
        label = symbolic.counterexample.summary or symbolic.counterexample.raw
        if label:
            lines.append(f"  - Counterexample: {label}")
    if symbolic.linked_finding is not None or symbolic.finding is not None:
        value = symbolic.linked_finding or symbolic.finding
        lines.append(f"  - Linked finding: {value}")
    return lines


def _append_symbolic_results(lines: list[str], results: list[SymbolicResult]) -> None:
    """Append symbolic result section when present."""
    if not results:
        return
    lines.append("## Symbolic Results")
    lines.append("")
    for symbolic in results:
        lines.extend(_symbolic_result_lines(symbolic))
    lines.append("")


def _append_transaction_traces(
    lines: list[str], traces: list[TransactionTrace]
) -> None:
    """Append transaction trace section when present."""
    if not traces:
        return
    lines.append("## Transaction Traces")
    lines.append("")
    for trace in traces:
        lines.append(f"- `{trace.tx_hash}`")
        for step in trace.steps:
            lines.append(f"  - {step}")
    lines.append("")
