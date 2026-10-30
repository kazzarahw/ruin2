"""Bytecode-based address clustering for attribution in ``ruin``."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ruin.core.probe import minimal_proxy_implementation

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    from ruin.core.onchain import BytecodeInfo


@dataclass
class Cluster:
    """A group of addresses that share deployed code."""

    key: str
    kind: str
    addresses: list[str] = field(default_factory=list)
    impl: str = ""

    def render_markdown(self) -> str:
        """Render the cluster as Markdown."""
        label = f"{self.kind} {self.key}"
        if self.kind == "no-code":
            label = "no-code (EOA or undeployed)"
        if self.impl:
            label = f"clones of {self.impl}"
        lines: list[str] = [f"## {label} ({len(self.addresses)} addresses)", ""]
        for address in self.addresses:
            lines.append(f"- {address}")
        return "\n".join(lines)


def _normalize(hexcode: str) -> str:
    return hexcode.removeprefix("0x").lower()


def minimal_proxy_impl(hexcode: str) -> str | None:
    """Return the implementation address of an EIP-1167 minimal proxy."""
    return minimal_proxy_implementation(hexcode) or None


def _code_key(hexcode: str) -> str:
    raw = _normalize(hexcode)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def cluster_bytecodes(items: Iterable[tuple[str, str]]) -> list[Cluster]:
    """Group (address, hexcode) pairs into code-sharing clusters.

    Minimal proxies are grouped by their implementation address; every other
    deployment is grouped by an exact bytecode hash.
    """
    clones: dict[str, list[str]] = {}
    identical: dict[str, list[str]] = {}
    no_code: list[str] = []
    for address, hexcode in items:
        if not _normalize(hexcode):
            no_code.append(address)
            continue
        impl = minimal_proxy_impl(hexcode)
        if impl is not None:
            clones.setdefault(impl, []).append(address)
        else:
            identical.setdefault(_code_key(hexcode), []).append(address)
    clusters: list[Cluster] = []
    for impl, addrs in sorted(clones.items()):
        clusters.append(Cluster(key=impl, kind="clone", addresses=addrs, impl=impl))
    for key, addrs in sorted(identical.items()):
        kind = "identical" if len(addrs) > 1 else "unique"
        clusters.append(Cluster(key=key, kind=kind, addresses=addrs))
    if no_code:
        clusters.append(Cluster(key="no-code", kind="no-code", addresses=no_code))
    return clusters


def cluster_infos(infos: Sequence[BytecodeInfo]) -> list[Cluster]:
    """Cluster adapter BytecodeInfo records by shared deployed code."""
    return cluster_bytecodes([(info.address, info.hexcode) for info in infos])


def render_clusters(clusters: Sequence[Cluster]) -> str:
    """Render all clusters as a single Markdown report."""
    grouped = [c for c in clusters if c.kind in ("identical", "clone")]
    unique = [c for c in clusters if c.kind == "unique"]
    no_code = [c for c in clusters if c.kind == "no-code"]
    no_code_addresses = sum(len(c.addresses) for c in no_code)
    lines: list[str] = [
        "# Address clusters",
        "",
        f"- shared-code groups: {len(grouped)}",
        f"- unique deployments: {len(unique)}",
        f"- no-code addresses: {no_code_addresses}",
        "",
    ]
    for cluster in grouped:
        lines.append(cluster.render_markdown())
        lines.append("")
    for cluster in no_code:
        lines.append(cluster.render_markdown())
        lines.append("")
    return "\n".join(lines)
