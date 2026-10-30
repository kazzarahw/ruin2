"""Extended operation handlers for ``ruin``."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

    from ruin.core.forensics import LogScan
    from ruin.core.onchain import SourceInfo
    from ruin.core.proxy import ProxyInfo
    from ruin.core.replay import Timeline

from ruin.core.chains import EVM_CHAIN_IDS
from ruin.core.domain import Target, Vuln
from ruin.core.enums import (
    Chain,
    Severity,
    TargetMode,
    VulnClass,
    chain_from_name,
)
from ruin.core.onchain import AccountInfo, BytecodeInfo, ChainDigest
from ruin.core.sources import split_bundle
from ruin.services import forensics as forensics_svc
from ruin.services.access_control import build_access_map
from ruin.services.analyzers import SemgrepAnalyzer, SlitherAnalyzer
from ruin.services.chains import default_rpc, get_adapter
from ruin.services.clustering import cluster_addresses
from ruin.services.files import write_or_render
from ruin.services.http import ranked_text
from ruin.services.operations_builders_cosmos import COSMOS_OPERATIONS
from ruin.services.operations_builders_mintsig import MINTSIG_OPERATIONS
from ruin.services.operations_builders_thin import THIN_OPERATIONS
from ruin.services.operations_ext_scaffold import SCAFFOLD_OPERATIONS
from ruin.services.operations_ext_selectors import SELECTOR_OPERATIONS
from ruin.services.operations_findings import FINDING_OPERATIONS
from ruin.services.playbook import execute_playbook, load_playbook
from ruin.services.proxy import resolve_proxy_onchain
from ruin.services.sources import fetch_source


def _parse_chain(value: object) -> Chain:
    """Resolve a chain name into a ``Chain`` enum member (see core.enums)."""
    return chain_from_name(value)


def replay_timeline(kwargs: dict[str, Any]) -> Timeline | str:
    """Replay a transaction, or return the non-EVM skip note (shared)."""
    note = _evm_only_note(kwargs)
    if note:
        return note
    return forensics_svc.replay_transaction(
        str(kwargs["tx"]),
        str(kwargs["address"]),
        str(kwargs["rpc"]),
        int(kwargs["from_block"]),
        int(kwargs["to_block"]),
    )


def _replay(kwargs: dict[str, Any]) -> str:
    timeline = replay_timeline(kwargs)
    if isinstance(timeline, str):
        return timeline
    return write_or_render(kwargs.get("out"), timeline.render_markdown())


def _chain_id_for(kwargs: dict[str, Any]) -> int:
    """Explorer chain id: explicit --chain-id wins, else derive from --chain.

    The parsers default ``chain_id`` to 1; a slug like ``polygon`` must not
    silently keep querying mainnet explorers, so the slug table wins unless
    the caller pinned a non-default id.
    """
    chain_id = int(kwargs.get("chain_id", 1))
    slug = str(kwargs.get("chain", "")).strip().lower()
    if chain_id == 1 and slug in EVM_CHAIN_IDS:
        return EVM_CHAIN_IDS[slug]
    return chain_id


def source_info(kwargs: dict[str, Any]) -> SourceInfo:
    """Fetch verified source for the CLI-selected chain and address."""
    return fetch_source(
        str(kwargs["address"]),
        chain=_parse_chain(kwargs.get("chain", "EVM")),
        chain_id=_chain_id_for(kwargs),
    )


def _source(kwargs: dict[str, Any]) -> str:
    info = source_info(kwargs)
    out = kwargs.get("out")
    if out is not None:
        return write_or_render(out, info.render_markdown(full=True))
    tree = kwargs.get("tree")
    if tree is not None:
        base = Path(str(tree))
        pairs = split_bundle(info.source_text)
        for path, body in pairs:
            target = base / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(body, encoding="utf-8")
        return f"wrote {len(pairs)} files under {base}"
    return info.render_markdown()


def cluster_targets(kwargs: dict[str, Any]) -> tuple[list[str], Chain, str]:
    """Coerce cluster CLI flags into (addresses, chain, rpc)."""
    return (
        list(kwargs.get("addresses", [])),
        _parse_chain(kwargs.get("chain", "EVM")),
        str(kwargs["rpc"]),
    )


def _cluster(kwargs: dict[str, Any]) -> str:
    addresses, chain, rpc = cluster_targets(kwargs)
    text = cluster_addresses(addresses, chain, rpc)
    return write_or_render(kwargs.get("out"), text)


def _evm_only_note(kwargs: dict[str, Any]) -> str:
    """Return a skip note when a cast-backed op is asked to run off EVM."""
    chain = _parse_chain(kwargs.get("chain", "EVM"))
    if chain is Chain.EVM:
        return ""
    return f"{chain.value} not supported by cast-backed op; use `inspect` instead."


def inspect_digest(kwargs: dict[str, Any]) -> ChainDigest:
    """Build the chain digest shared by text and JSON output."""
    chain = _parse_chain(kwargs.get("chain", "EVM"))
    address = str(kwargs["address"])
    rpc = str(kwargs.get("rpc", "")) or default_rpc(chain)
    adapter = get_adapter(chain)
    if rpc:
        account = adapter.fetch_account(address, rpc)
        bytecode = adapter.fetch_bytecode(address, rpc)
    else:
        account = AccountInfo(chain=chain, address=address, note="no rpc provided")
        bytecode = BytecodeInfo(chain=chain, address=address)
    if kwargs.get("source"):
        source = fetch_source(address, chain=chain, chain_id=_chain_id_for(kwargs))
    else:
        source = adapter.fetch_source(address)
    return ChainDigest(
        chain=chain,
        address=address,
        account=account,
        bytecode=bytecode,
        source=source,
        analyzers=adapter.analyzers(),
    )


def _inspect(kwargs: dict[str, Any]) -> str:
    return write_or_render(kwargs.get("out"), inspect_digest(kwargs).render_markdown())


def _analyze(kwargs: dict[str, Any]) -> str:
    source = Path(str(kwargs["source"]))
    target = Target.new(
        str(kwargs.get("name", "target")), [], None, TargetMode.RESEARCH
    )
    analyzers = [SlitherAnalyzer(source), SemgrepAnalyzer(source)]
    findings: list[Vuln] = []
    for analyzer in analyzers:
        try:
            findings.extend(analyzer.analyze(target))
        except (RuntimeError, ValueError, OSError) as error:
            findings.append(
                Vuln(
                    klass=VulnClass.LOGIC,
                    severity=Severity.LOW,
                    summary=f"analyzer failed: {error}",
                    poc=None,
                )
            )
    return "\n".join(f"[{v.severity.value}] {v.klass}: {v.summary}" for v in findings)


def _trace(kwargs: dict[str, Any]) -> str:
    note = _evm_only_note(kwargs)
    if note:
        return note
    trace = forensics_svc.trace_transaction(str(kwargs["tx"]), str(kwargs["rpc"]))
    return trace.render_markdown()


def logs_scan(kwargs: dict[str, Any]) -> LogScan | str:
    """Scan EVM logs, or return the non-EVM skip note (shared)."""
    note = _evm_only_note(kwargs)
    if note:
        return note
    return forensics_svc.scan_logs(
        str(kwargs["address"]),
        str(kwargs["rpc"]),
        int(kwargs["from_block"]),
        int(kwargs["to_block"]),
    )


def _logs(kwargs: dict[str, Any]) -> str:
    scan = logs_scan(kwargs)
    if isinstance(scan, str):
        return scan
    return scan.render_markdown()


def proxy_resolution(kwargs: dict[str, Any]) -> ProxyInfo | str:
    """Resolve a proxy on-chain, or return the non-EVM skip note (shared)."""
    note = _evm_only_note(kwargs)
    if note:
        return note
    return resolve_proxy_onchain(str(kwargs["address"]), str(kwargs["rpc"]))


def _proxy(kwargs: dict[str, Any]) -> str:
    info = proxy_resolution(kwargs)
    if isinstance(info, str):
        return info
    return info.render_markdown()


def _accessmap(kwargs: dict[str, Any]) -> str:
    amap = build_access_map(Path(str(kwargs["source"])))
    return amap.render_markdown()


def _playbook(kwargs: dict[str, Any]) -> str:
    name = str(kwargs["name"])
    pb = load_playbook(name)
    overrides: dict[str, str] = {}
    for item in kwargs.get("param", []):
        key, sep, value = str(item).partition("=")
        if sep and key:
            overrides[key] = value
    from ruin.services.operations import run_operation

    output = execute_playbook(pb, run_operation, overrides)
    return write_or_render(kwargs.get("out"), output)


def _chain_list(value: object) -> list[str]:
    """Coerce a chain flag value into a list of names."""
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    return [str(v) for v in cast("Iterable[object]", value)]


def _rank(kwargs: dict[str, Any]) -> str:
    return ranked_text(
        int(kwargs.get("limit", 10)),
        _chain_list(kwargs.get("chain")),
        _chain_list(kwargs.get("exclude_chain")),
        kwargs.get("screen"),
    )


EXT_OPERATIONS: dict[str, Callable[[dict[str, Any]], str]] = {
    "analyze": _analyze,
    "rank": _rank,
    "trace": _trace,
    "logs": _logs,
    "proxy": _proxy,
    "accessmap": _accessmap,
    "playbook": _playbook,
    "inspect": _inspect,
    "source": _source,
    "replay": _replay,
    "cluster": _cluster,
}

EXT_OPERATIONS.update(SCAFFOLD_OPERATIONS)
EXT_OPERATIONS.update(SELECTOR_OPERATIONS)
EXT_OPERATIONS.update(FINDING_OPERATIONS)
EXT_OPERATIONS.update(COSMOS_OPERATIONS)
EXT_OPERATIONS.update(MINTSIG_OPERATIONS)
EXT_OPERATIONS.update(THIN_OPERATIONS)
