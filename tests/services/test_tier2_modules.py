"""Tests for serialize, findings, playbook, and finding modules."""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

import pytest

from ruin.core.finding import Finding, FindingRegistry, FindingState
from ruin.core.playbook import Playbook, PlaybookStep
from ruin.services.findings import (
    add_finding,
    load_registry,
    save_registry,
    update_finding,
)
from ruin.services.playbook import BUILTIN_DIR, execute_playbook, load_playbook
from ruin.services.serialize import to_dict

# --- serialize tests ---


class Color(Enum):
    RED = "red"
    BLUE = "blue"


@dataclass
class Point:
    x: int
    y: int


class Stringy:
    def as_str(self) -> str:
        return "stringy_value"


class TestToDict:
    def test_none_becomes_null(self) -> None:
        assert to_dict(None) is None

    def test_int_passthrough(self) -> None:
        assert to_dict(42) == 42

    def test_float_passthrough(self) -> None:
        assert to_dict(3.14) == 3.14

    def test_bool_passthrough(self) -> None:
        assert to_dict(True) is True

    def test_enum(self) -> None:
        assert to_dict(Color.RED) == "red"

    def test_dataclass(self) -> None:
        result = to_dict(Point(1, 2))
        assert result == {"x": 1, "y": 2}

    def test_dict(self) -> None:
        result = to_dict({"a": 1, "b": [1, 2]})
        assert result == {"a": 1, "b": [1, 2]}

    def test_list(self) -> None:
        result = to_dict([1, 2, 3])
        assert result == [1, 2, 3]

    def test_tuple(self) -> None:
        result = to_dict((1, 2))
        assert result == [1, 2]

    def test_as_str_object(self) -> None:
        result = to_dict(Stringy())
        assert result == "stringy_value"

    def test_drop_none_removes_null_keys(self) -> None:
        @dataclass
        class Opt:
            a: int
            b: str | None

        result = to_dict(Opt(1, None), drop_none=True)
        assert result == {"a": 1}

    def test_plain_object(self) -> None:
        result = to_dict(object())
        assert isinstance(result, str)

    def test_nested_dataclass(self) -> None:
        @dataclass
        class Outer:
            inner: Point
            label: str

        result = to_dict(Outer(Point(3, 4), "test"))
        assert result == {"inner": {"x": 3, "y": 4}, "label": "test"}

    def test_enum_in_dataclass(self) -> None:
        @dataclass
        class Colored:
            color: Color

        result = to_dict(Colored(Color.BLUE))
        assert result == {"color": "blue"}


# --- core/finding tests ---


class TestFindingState:
    def test_values(self) -> None:
        assert FindingState.OPEN.value == "open"
        assert FindingState.CONFIRMED.value == "confirmed"
        assert FindingState.FIXED.value == "fixed"
        assert FindingState.ACCEPTED_RISK.value == "accepted_risk"


class TestFinding:
    def test_defaults(self) -> None:
        f = Finding(id="F1", title="Test")
        assert f.state == FindingState.OPEN
        assert f.severity == ""
        assert f.confidence == 0
        assert f.evidence == []

    def test_custom_fields(self) -> None:
        f = Finding(
            id="F2",
            title="High severity",
            state=FindingState.CONFIRMED,
            severity="high",
            confidence=8,
            evidence=["tx:0xabc"],
            notes="reproducible",
            linked_contract="Vault",
            linked_finding="F1",
        )
        assert f.state == FindingState.CONFIRMED
        assert f.severity == "high"
        assert f.confidence == 8
        assert f.evidence == ["tx:0xabc"]


class TestFindingRegistry:
    def test_add(self) -> None:
        reg = FindingRegistry(protocol="TestProto")
        reg.add(Finding(id="A", title="First"))
        reg.add(Finding(id="B", title="Second"))
        assert len(reg.findings) == 2

    def test_update_state(self) -> None:
        reg = FindingRegistry(protocol="P")
        reg.add(Finding(id="X", title="Bug"))
        reg.update_state("X", FindingState.FIXED)
        assert reg.findings[0].state == FindingState.FIXED

    def test_update_state_missing_id(self) -> None:
        reg = FindingRegistry(protocol="P")
        reg.add(Finding(id="X", title="Bug"))
        reg.update_state("NOPE", FindingState.FIXED)
        assert reg.findings[0].state == FindingState.OPEN

    def test_render_markdown_empty(self) -> None:
        reg = FindingRegistry(protocol="Empty")
        text = reg.render_markdown()
        assert "# Findings" in text
        assert "Empty" in text

    def test_render_markdown_with_findings(self) -> None:
        reg = FindingRegistry(protocol="Proto")
        reg.add(Finding(id="F1", title="Open bug", confidence=7))
        reg.add(Finding(id="F2", title="Fixed bug", state=FindingState.FIXED))
        reg.add(Finding(id="F3", title="Risk", state=FindingState.ACCEPTED_RISK))
        text = reg.render_markdown()
        assert "Open (1)" in text
        assert "Fixed (1)" in text
        assert "Accepted Risk (1)" in text
        assert "F1" in text
        assert "confidence=7" in text

    def test_render_markdown_with_evidence(self) -> None:
        reg = FindingRegistry(protocol="P")
        reg.add(Finding(id="E1", title="With evidence", evidence=["log:0x1", "tx:0x2"]))
        text = reg.render_markdown()
        assert "evidence:" in text
        assert "log:0x1" in text


# --- core/playbook tests ---


class TestPlaybookStep:
    def test_defaults(self) -> None:
        step = PlaybookStep(operation="screen")
        assert step.params == {}

    def test_with_params(self) -> None:
        step = PlaybookStep(operation="triage", params={"severity": "high"})
        assert step.params == {"severity": "high"}


class TestPlaybook:
    def test_defaults(self) -> None:
        pb = Playbook(name="test")
        assert pb.description == ""
        assert pb.steps == []
        assert pb.params == []

    def test_render_markdown(self) -> None:
        pb = Playbook(
            name="recon",
            description="Standard recon",
            params=["address"],
            steps=[
                PlaybookStep(operation="screen", params={"target": "addr"}),
                PlaybookStep(operation="triage"),
            ],
        )
        text = pb.render_markdown()
        assert "# Playbook" in text
        assert "recon" in text
        assert "Standard recon" in text
        assert "Parameters:" in text
        assert "screen" in text
        assert "triage" in text

    def test_render_markdown_no_description(self) -> None:
        pb = Playbook(name="minimal", steps=[PlaybookStep(operation="logs")])
        text = pb.render_markdown()
        assert "minimal" in text
        assert "logs" in text


# --- services/findings tests ---


class TestFindingsPersistence:
    def test_save_and_load(self, tmp_path: Path) -> None:
        reg = FindingRegistry(protocol="MyProto")
        reg.add(Finding(id="A", title="Bug A", severity="medium"))
        reg.add(Finding(id="B", title="Bug B", state=FindingState.CONFIRMED))
        path = tmp_path / "findings.json"
        save_registry(reg, path)
        loaded = load_registry(path)
        assert loaded.protocol == "MyProto"
        assert len(loaded.findings) == 2
        assert loaded.findings[0].id == "A"
        assert loaded.findings[1].state == FindingState.CONFIRMED

    def test_load_empty_file(self, tmp_path: Path) -> None:
        path = tmp_path / "empty.json"
        path.write_text("", encoding="utf-8")
        assert load_registry(path).findings == []
        add_finding(path, Finding(id="E", title="From empty"))
        assert len(load_registry(path).findings) == 1

    def test_add_finding_creates_file(self, tmp_path: Path) -> None:
        path = tmp_path / "new.json"
        finding = Finding(id="N1", title="New finding")
        reg = add_finding(path, finding)
        assert path.exists()
        assert len(reg.findings) == 1

    def test_add_finding_appends(self, tmp_path: Path) -> None:
        path = tmp_path / "reg.json"
        add_finding(path, Finding(id="X", title="First"))
        reg = add_finding(path, Finding(id="Y", title="Second"))
        assert len(reg.findings) == 2

    def test_update_finding(self, tmp_path: Path) -> None:
        path = tmp_path / "upd.json"
        add_finding(path, Finding(id="U1", title="Update me"))
        reg = update_finding(path, "U1", "confirmed", evidence=["proof"])
        assert reg.findings[0].state == FindingState.CONFIRMED
        assert "proof" in reg.findings[0].evidence

    def test_update_finding_no_evidence(self, tmp_path: Path) -> None:
        path = tmp_path / "upd2.json"
        add_finding(path, Finding(id="U2", title="Fix"))
        reg = update_finding(path, "U2", "fixed")
        assert reg.findings[0].state == FindingState.FIXED

    def test_load_invalid_state_raises(self, tmp_path: Path) -> None:
        path = tmp_path / "bad.json"
        path.write_text(
            json.dumps(
                {
                    "protocol": "P",
                    "findings": [{"id": "Z", "title": "T", "state": "unknown"}],
                }
            )
        )
        with pytest.raises(ValueError, match="unknown"):
            load_registry(path)


# --- services/playbook tests ---


class TestPlaybookService:
    def test_load_builtin_playbook(self) -> None:
        pb = load_playbook("standard-recon")
        assert pb.name == "standard-recon"
        assert len(pb.steps) > 0

    def test_builtin_playbooks_ship_with_package(self) -> None:
        # Playbooks must live inside the ruin package so they ship in the wheel
        # and the installed skill, not only at the repo root.
        import ruin.services.playbook as pb_mod

        assert (
            Path(pb_mod.__file__).resolve().parent.parent / "playbooks"
        ) == BUILTIN_DIR
        assert BUILTIN_DIR.is_dir()
        assert (BUILTIN_DIR / "standard-recon.json").exists()

    def test_load_custom_playbook(self, tmp_path: Path) -> None:
        data = {
            "name": "custom",
            "schema": 2,
            "description": "My custom flow",
            "params": ["addr"],
            "steps": [{"operation": "logs", "params": {"address": "0x1"}}],
        }
        (tmp_path / "custom.json").write_text(json.dumps(data))
        pb = load_playbook("custom", search_dir=tmp_path)
        assert pb.name == "custom"
        assert pb.steps[0].operation == "logs"

    def test_load_missing_playbook(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            load_playbook("nonexistent", search_dir=tmp_path)

    def test_load_legacy_schema_rejected(self, tmp_path: Path) -> None:
        data = {
            "name": "legacy",
            "description": "pre-v2 playbook",
            "params": [],
            "steps": [{"operation": "logs", "params": {}}],
        }
        (tmp_path / "legacy.json").write_text(json.dumps(data))
        with pytest.raises(ValueError, match="schema"):
            load_playbook("legacy", search_dir=tmp_path)

    def test_execute_playbook(self) -> None:
        calls: list[tuple[str, dict[str, Any]]] = []

        def mock_dispatch(op: str, kwargs: dict[str, Any]) -> str:
            calls.append((op, kwargs))
            return f"## {op}\n\nresult"

        pb = Playbook(
            name="test",
            steps=[
                PlaybookStep(operation="screen", params={"target": "0xabc"}),
                PlaybookStep(operation="triage"),
            ],
        )
        output = execute_playbook(pb, mock_dispatch)
        assert "## screen" in output
        assert "## triage" in output
        assert len(calls) == 2
        assert calls[0][1]["target"] == "0xabc"

    def test_execute_playbook_with_overrides(self) -> None:
        calls: list[tuple[str, dict[str, Any]]] = []

        def mock_dispatch(op: str, kwargs: dict[str, Any]) -> str:
            calls.append((op, kwargs))
            return "ok"

        pb = Playbook(
            name="t", steps=[PlaybookStep(operation="logs", params={"address": "orig"})]
        )
        execute_playbook(pb, mock_dispatch, overrides={"address": "override"})
        assert calls[0][1]["address"] == "override"

    def test_execute_playbook_chains_written_files(self) -> None:
        calls: list[tuple[str, dict[str, Any]]] = []

        def mock_dispatch(op: str, kwargs: dict[str, Any]) -> str:
            calls.append((op, kwargs))
            if op == "source":
                return "wrote pb-source.txt"
            return f"## {op}"

        pb = Playbook(
            name="chain",
            steps=[
                PlaybookStep(operation="source", params={"address": "{source}"}),
                PlaybookStep(operation="slither", params={"source": "{last_file}"}),
                PlaybookStep(operation="triage", params={"name": "{slug}"}),
            ],
        )
        execute_playbook(pb, mock_dispatch, overrides={"source": "0xA", "slug": "t"})
        assert calls[1][1]["source"] == "pb-source.txt"
        assert calls[2][1]["name"] == "t"

    def test_execute_playbook_unknown_token_stays_literal(self) -> None:
        calls: list[tuple[str, dict[str, Any]]] = []

        def mock_dispatch(op: str, kwargs: dict[str, Any]) -> str:
            calls.append((op, kwargs))
            return "ok"

        pb = Playbook(
            name="t",
            steps=[PlaybookStep(operation="logs", params={"address": "{nope}"})],
        )
        execute_playbook(pb, mock_dispatch)
        assert calls[0][1]["address"] == "{nope}"

    def test_execute_playbook_error_handling(self) -> None:
        def failing_dispatch(op: str, kwargs: dict[str, Any]) -> str:
            msg = "boom"
            raise RuntimeError(msg)

        pb = Playbook(name="err", steps=[PlaybookStep(operation="bad")])
        output = execute_playbook(pb, failing_dispatch)
        assert "error:" in output
        assert "boom" in output

    def test_execute_playbook_names_missing_params(self) -> None:
        def keyerror_dispatch(op: str, kwargs: dict[str, Any]) -> str:
            raise KeyError("slug")

        pb = Playbook(name="miss", steps=[PlaybookStep(operation="map")])
        output = execute_playbook(pb, keyerror_dispatch)
        assert "missing param: 'slug'" in output

    def test_playbook_operation_forwards_params(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from ruin.services import operations as ops

        calls: list[tuple[str, dict[str, Any]]] = []

        def fake_dispatch(op: str, kwargs: dict[str, Any]) -> str:
            calls.append((op, dict(kwargs)))
            return f"## {op}"

        real = ops.run_operation
        monkeypatch.setattr(ops, "run_operation", fake_dispatch)
        output = real(
            "playbook",
            {
                "name": "exploit-triage",
                "param": ["tx=0x1", "rpc=http://x", "contract=0x2"],
                "out": None,
            },
        )
        assert "error:" not in output
        assert calls, "playbook steps did not run"
        for _, kw in calls:
            assert kw.get("tx") == "0x1"
            assert kw.get("rpc") == "http://x"
