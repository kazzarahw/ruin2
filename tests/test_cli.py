"""Tests for the CLI."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from ruin.cli import _MOVED, _known_commands, build_parser, main
from ruin.services.parsing_ext import DEFAULT_EVM_RPC

FIXTURES = Path(__file__).parent / "fixtures"


def test_build_parser() -> None:
    parser = build_parser()
    assert parser.prog == "ruin"


def test_playbook_param_flag_accumulates() -> None:
    parser = build_parser()
    args = parser.parse_args(
        [
            "flow",
            "playbook",
            "standard-recon",
            "--param",
            "slug=x",
            "--param",
            "chain=ethereum",
        ]
    )
    assert args.param == ["slug=x", "chain=ethereum"]


def test_format_flag_works_before_and_after_subcommand() -> None:
    parser = build_parser()
    before = parser.parse_args(["--format", "json", "target", "rank"])
    after = parser.parse_args(["target", "rank", "--format", "json"])
    plain = parser.parse_args(["target", "rank"])
    assert before.format == "json"
    assert after.format == "json"
    assert plain.format == "markdown"


def test_evm_commands_default_to_public_rpc() -> None:
    parser = build_parser()
    cases = [
        ["bytecode", "probe", "0xABC"],
        ["bytecode", "selectors", "0xABC"],
        ["bytecode", "impl-diff", "0xA", "0xB"],
        ["classes", "honeypot-evm", "0xT"],
        ["target", "hunt", "0xT"],
        ["bytecode", "decompile", "0xABC"],
        [
            "classes",
            "thin-collateral",
            "0xT",
            "--market",
            "0xM",
            "--factory",
            "0xF",
            "--price-usd",
            "1",
        ],
    ]
    for argv in cases:
        ns = vars(parser.parse_args(argv))
        assert ns["rpc"] is None
        assert ns["chain"] == "ethereum"
    for argv in [
        ["bytecode", "proxy", "0xABC"],
        ["chain", "trace", "0xTX"],
        ["chain", "logs", "0xABC", "--from-block", "1", "--to-block", "2"],
    ]:
        ns = vars(parser.parse_args(argv))
        assert ns["rpc"] == DEFAULT_EVM_RPC


def test_new_commands_are_known_to_the_cli() -> None:
    parser = build_parser()
    parser.parse_args(["bytecode", "probe", "0x1", "--rpc", "http://x"])
    parser.parse_args(["bytecode", "selectors", "0x1", "--rpc", "http://x"])
    parser.parse_args(["classes", "honeypot", "MINT"])
    parser.parse_args(["bytecode", "decompile", "0x1", "--rpc", "http://x"])
    parser.parse_args(["bytecode", "impl-diff", "0x1", "0x2", "--rpc", "http://x"])
    parser.parse_args(["classes", "erc4626", "0x1", "--underlying", "0x2"])
    parser.parse_args(
        [
            "classes",
            "thin-collateral",
            "0x1",
            "--market",
            "0x2",
            "--factory",
            "0x3",
            "--price-usd",
            "1.5",
        ]
    )


def _parser_choices(parser: argparse.ArgumentParser) -> set[str]:
    action = next(
        a for a in parser._actions if isinstance(a, argparse._SubParsersAction)
    )
    return set(action.choices)


def test_known_commands_cover_every_advertised_command() -> None:
    parser = build_parser()
    assert _known_commands(parser) == _parser_choices(parser)


def test_known_command_missing_args_reports_its_own_usage(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exit_info:
        main(["classes", "ctoken"])
    assert exit_info.value.code == 2
    assert "usage: ruin classes ctoken" in capsys.readouterr().err


def test_json_format_does_not_run_the_markdown_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def fake_markdown(operation: str, kwargs: dict[str, object]) -> str:
        calls.append("markdown")
        return "text"

    def fake_json(operation: str, kwargs: dict[str, object]) -> dict[str, bool]:
        calls.append("json")
        return {"ok": True}

    monkeypatch.setattr("ruin.cli.run_operation", fake_markdown)
    monkeypatch.setattr("ruin.cli.run_operation_json", fake_json)
    assert main(["--format", "json", "target", "trust", "Example"]) == 0
    assert calls == ["json"]


def test_moved_command_prints_new_path(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["rank"]) == 2
    assert "moved to 'ruin target rank'" in capsys.readouterr().err


def test_moved_decode_points_at_selectors(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["decode", "p"]) == 2
    assert "moved to 'ruin bytecode selectors'" in capsys.readouterr().err


def test_moved_hypotheses_points_at_triage_mode(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["hypotheses", "T"]) == 2
    hint = "moved to 'ruin source triage --mode hypotheses'"
    assert hint in capsys.readouterr().err


def test_every_operation_name_has_a_move_hint() -> None:
    """A flat canonical operation call must print the namespaced hint."""
    fixture = json.loads((FIXTURES / "cli_argv.json").read_text())
    for op, argv in fixture.items():
        assert op in _MOVED, f"{op} missing from _MOVED"
        parts = _MOVED[op].split()
        if op == "pipeline":
            assert parts == ["flow", "status"]
            continue
        assert parts[:2] == argv[:2]
        assert all(token in argv for token in parts)
        if "--mode" in argv:
            assert "--mode" in parts
            assert parts[parts.index("--mode") + 1] == argv[argv.index("--mode") + 1]
        if "--run" in argv:
            assert "--run" in parts
