"""Tests for bytecode-based address clustering."""

from __future__ import annotations

from ruin.core.clustering import (
    Cluster,
    cluster_bytecodes,
    minimal_proxy_impl,
    render_clusters,
)

_CLONE = (
    "0x363d3d373d3d3d363d73"
    + "1111111111111111111111111111111111111111"
    + "5af43d82803e903d91602b57fd5bf3"
)
# Real EIP-1167 runtime code captured during a live hunt (/tmp/ruin-hunt).
_REAL_CLONE = (
    "0x363d3d373d3d3d363d730d424072d658e6abd92c36f8fc16fd6479ae15a0"
    "5af43d82803e903d91602b57fd5bf3"
)


def test_minimal_proxy_impl_detected() -> None:
    assert minimal_proxy_impl(_CLONE) == "0x1111111111111111111111111111111111111111"


def test_minimal_proxy_impl_rejects_other() -> None:
    assert minimal_proxy_impl("0x6080604052") is None


def test_real_clone_bytecode_clusters() -> None:
    clusters = cluster_bytecodes(
        [("0xA", _REAL_CLONE), ("0xB", _REAL_CLONE), ("0xC", "0x6080604052")]
    )
    clones = [c for c in clusters if c.kind == "clone"]
    assert len(clones) == 1
    assert clones[0].impl == "0x0d424072d658e6abd92c36f8fc16fd6479ae15a0"
    assert set(clones[0].addresses) == {"0xA", "0xB"}


def test_cluster_groups_clones_and_identical() -> None:
    items = [
        ("0xA", _CLONE),
        ("0xB", _CLONE),
        ("0xC", "0xdeadbeef"),
        ("0xD", "0xdeadbeef"),
        ("0xE", "0xcafebabe"),
    ]
    clusters = cluster_bytecodes(items)
    clones = [c for c in clusters if c.kind == "clone"]
    identical = [c for c in clusters if c.kind == "identical"]
    unique = [c for c in clusters if c.kind == "unique"]
    assert len(clones) == 1
    assert set(clones[0].addresses) == {"0xA", "0xB"}
    assert clones[0].impl == "0x1111111111111111111111111111111111111111"
    assert len(identical) == 1
    assert set(identical[0].addresses) == {"0xC", "0xD"}
    assert len(unique) == 1
    assert unique[0].addresses == ["0xE"]


def test_cluster_separates_no_code() -> None:
    items = [("0xA", "0x"), ("0xB", ""), ("0xC", "0xdeadbeef")]
    clusters = cluster_bytecodes(items)
    no_code = [c for c in clusters if c.kind == "no-code"]
    identical = [c for c in clusters if c.kind == "identical"]
    assert len(no_code) == 1
    assert set(no_code[0].addresses) == {"0xA", "0xB"}
    assert identical == []


def test_render_clusters_reports_groups() -> None:
    clusters = [
        Cluster(key="0x1", kind="clone", addresses=["0xA"], impl="0x1"),
        Cluster(key="k", kind="unique", addresses=["0xB"]),
    ]
    text = render_clusters(clusters)
    assert "shared-code groups: 1" in text
    assert "unique deployments: 1" in text
    assert "0xA" in text
    assert "0xB" not in text.split("unique deployments")[1].split("## ")[-1]
