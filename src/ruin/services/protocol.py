"""Protocol resolution: verified sources, proxy follow, compile, call graph.

Turns one on-chain address into a ``Protocol`` fact bundle: fetch verified
source, follow proxies through the existing resolution services, compile
pragma-pinned standard-json with solc, and build the core call graph (or
line-parser facts when solc is unavailable). ``surface``/``model``/
``invariants`` consume a resolved Protocol; scaffold writing lives in
``protocol_scaffold`` and solc staging in ``protocol_compile``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ruin.core.callgraph import CallGraph, build, build_from_facts
from ruin.core.chains import CHAIN_SLUG_BY_ID, resolve_rpc
from ruin.core.enums import Chain
from ruin.core.invariants import InvariantSpec, synthesize
from ruin.core.sol_parse import parse_source
from ruin.services.protocol_compile import compile_asts
from ruin.services.proxy import resolve_proxy_onchain
from ruin.services.sources import fetch_source

if TYPE_CHECKING:
    from ruin.core.proxy import ProxyInfo
    from ruin.core.sol_parse import ParsedFunction

_INITIALIZER_MARKERS = ("init", "initialize", "upgrade", "migrate")
_SET_PREFIX = "set"


@dataclass(frozen=True, slots=True)
class Protocol:
    """One resolved protocol: sources, proxy notes, and call graph."""

    address: str
    chain: str
    rpc: str
    implementation: str
    delegation: str
    name: str
    pragma: str
    verified: bool
    mode: str
    source_units: tuple[tuple[str, str], ...]
    graph: CallGraph

    def render_markdown(self) -> str:
        """Render the protocol model as Markdown."""
        lines = [
            f"# Protocol model: {self.address}",
            "",
            f"- chain: `{self.chain}`  rpc: `{self.rpc}`",
            f"- implementation: `{self.implementation or 'none'}` {self.delegation}",
            f"- compiler pragma: `{self.pragma or 'unknown'}`"
            f"  verified: {'yes' if self.verified else 'no'}",
            self._graph_line(),
            "",
            "## Contracts",
        ]
        for contract in self.graph.contracts:
            lines.append(
                f"- **{contract.name}** ({contract.kind}): "
                f"{len(contract.functions)} functions"
            )
        lines.extend(["", f"- entrypoints: {', '.join(self.graph.entrypoints)}"])
        if self.graph.cycles:
            cycles = "; ".join(" <-> ".join(c) for c in self.graph.cycles)
            lines.append(f"- inheritance cycles: {cycles}")
        return "\n".join(lines)

    def _graph_line(self) -> str:
        """Graph provenance line: AST compile versus line-facts fallback."""
        if self.mode == "ast":
            return "- graph: `ast`"
        return "- graph: `line-facts` (source not compiled)"


@dataclass(frozen=True, slots=True)
class SurfaceRow:
    """One entrypoint with its gate, writes, and risk rank."""

    name: str
    contract: str
    visibility: str
    mutability: str
    modifiers: tuple[str, ...]
    writes: tuple[str, ...]
    rank: int
    tags: tuple[str, ...]


def _chain_id(slug: str) -> int:
    """Reverse-map a chain slug to its id, defaulting to mainnet."""
    for chain_id, known in CHAIN_SLUG_BY_ID.items():
        if known == slug:
            return chain_id
    return 1


def _source_text(
    address: str, slug: str
) -> tuple[str, str, bool, tuple[str, ...], str]:
    """Fetch verified source; return (name, text, verified, remappings, version)."""
    info = fetch_source(address, chain=Chain.EVM, chain_id=_chain_id(slug))
    return (
        info.name,
        info.source_text,
        info.verified,
        info.remappings,
        info.compiler_version,
    )


def _proxy_note(address: str, endpoint: str) -> tuple[str, str]:
    """Resolve the proxy; return (implementation, human note)."""
    info: ProxyInfo = resolve_proxy_onchain(address, endpoint)
    if not info.is_proxy or not info.implementation:
        return "", ""
    if info.delegated_to:
        return info.implementation, f"(EIP-7702 delegation to {info.delegated_to})"
    return info.implementation, "(EIP-1967 implementation)"


def _analyze(
    name: str, text: str, remappings: tuple[str, ...], compiler_version: str = ""
) -> tuple[CallGraph, str, str]:
    """Graph, pragma, and mode: AST compile when possible, facts fallback."""
    facts = parse_source(name or "Main", text)
    asts = compile_asts(name or "Main", text, remappings, compiler_version)
    if asts:
        return build(asts), facts.pragma, "ast"
    return build_from_facts((facts,)), facts.pragma, "line-facts"


def resolve(address: str, chain: str = "ethereum", rpc: str | None = None) -> Protocol:
    """Resolve one address into a full ``Protocol`` fact bundle."""
    slug = chain.strip().lower()
    endpoint = resolve_rpc(rpc, slug)
    name, text, verified, remappings, version = _source_text(address, slug)
    implementation, note = _proxy_note(address, endpoint)
    if implementation:
        impl_name, impl_text, impl_verified, impl_remappings, impl_version = (
            _source_text(implementation, slug)
        )
        if impl_verified:
            name, text, verified = impl_name, impl_text, True
            remappings, version = impl_remappings, impl_version
            note = f"(using verified implementation source) {note}"
    graph, pragma, mode = _analyze(name, text, remappings, version)
    return Protocol(
        address=address,
        chain=slug,
        rpc=endpoint,
        implementation=implementation,
        delegation=note,
        name=name,
        pragma=pragma,
        verified=verified,
        mode=mode,
        source_units=((name or "Main", text),) if text else (),
        graph=graph,
    )


def _tags(fn: ParsedFunction) -> tuple[str, ...]:
    """Risk tags for one entrypoint function fact."""
    tags = []
    lowered = fn.name.lower()
    if any(marker in lowered for marker in _INITIALIZER_MARKERS):
        tags.append("initializer")
    if fn.name.startswith(_SET_PREFIX) and fn.modifiers:
        tags.append("owner-settable")
    if not fn.modifiers and fn.mutability == "payable":
        tags.append("ungated-value")
    return tuple(tags)


def _rank(tags: tuple[str, ...]) -> int:
    """Rank a surface row: highest for gates that can change protocol state."""
    if "initializer" in tags or "owner-settable" in tags:
        return 3
    return 2 if "ungated-value" in tags else 1


def _dedupe(rows: tuple[SurfaceRow, ...]) -> tuple[SurfaceRow, ...]:
    """Collapse public/external twins emitted for one (contract, name).

    Keeps the first row seen; a later row replaces it only when it has
    strictly more modifiers plus writes than the row it replaces.
    """
    best: dict[tuple[str, str], SurfaceRow] = {}
    weight: dict[tuple[str, str], int] = {}
    for row in rows:
        key = (row.contract, row.name)
        score = len(row.modifiers) + len(row.writes)
        if key not in best or score > weight[key]:
            best[key] = row
            weight[key] = score
    return tuple(best.values())


def surface(protocol: Protocol) -> tuple[SurfaceRow, ...]:
    """Rank the externally callable surface: entrypoints x writes x gates."""
    writes = protocol.graph.writes_by_function()
    rows = []
    for contract in protocol.graph.contracts:
        for fn in contract.fn_facts:
            if fn.visibility not in ("public", "external"):
                continue
            tags = _tags(fn)
            rows.append(
                SurfaceRow(
                    name=fn.name,
                    contract=contract.name,
                    visibility=fn.visibility,
                    mutability=fn.mutability,
                    modifiers=fn.modifiers,
                    writes=writes.get(f"{contract.name}.{fn.name}", ()),
                    rank=_rank(tags),
                    tags=tags,
                )
            )
    unique = _dedupe(tuple(rows))
    return tuple(sorted(unique, key=lambda r: (-r.rank, r.contract, r.name)))


def invariants(protocol: Protocol) -> tuple[InvariantSpec, ...]:
    """Candidate invariant specs synthesized from the call graph."""
    return synthesize(protocol.graph)
