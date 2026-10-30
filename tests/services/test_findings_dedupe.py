"""Tests for finding dedup and cross-run merge."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

from ruin.core.finding import Finding, FindingRegistry
from ruin.services.findings import dedupe_registry, merge_into


def _write(path: Path, *findings: Finding) -> None:
    reg = FindingRegistry(protocol="P", findings=list(findings))
    from ruin.services.findings import save_registry

    save_registry(reg, path)


def test_registry_dedupe_merges_evidence() -> None:
    reg = FindingRegistry(protocol="P")
    reg.add(Finding(id="A", title="Reentrancy in Vault", evidence=["tx:1"]))
    reg.add(Finding(id="A2", title="reentrancy in vault", evidence=["tx:2"]))
    removed = reg.dedupe()
    assert removed == 1
    assert len(reg.findings) == 1
    assert "tx:2" in reg.findings[0].evidence


def test_registry_merge_skips_dupes() -> None:
    target = FindingRegistry(protocol="P", findings=[Finding(id="A", title="X")])
    other = FindingRegistry(
        protocol="P",
        findings=[Finding(id="A", title="X"), Finding(id="B", title="Y")],
    )
    added = target.merge(other)
    assert added == 1
    assert [f.id for f in target.findings] == ["A", "B"]


def test_dedupe_registry_file(tmp_path: Path) -> None:
    path = tmp_path / "r.json"
    _write(path, Finding(id="A", title="Dup"), Finding(id="B", title="dup"))
    registry, removed = dedupe_registry(path)
    assert removed == 1
    assert len(registry.findings) == 1


def test_merge_into_file(tmp_path: Path) -> None:
    target = tmp_path / "t.json"
    other = tmp_path / "o.json"
    _write(target, Finding(id="A", title="X"))
    _write(other, Finding(id="A", title="X"), Finding(id="B", title="Y"))
    registry, added = merge_into(target, other)
    assert added == 1
    assert len(registry.findings) == 2
