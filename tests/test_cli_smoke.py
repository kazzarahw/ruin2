"""In-process smoke tests for the ``ruin`` CLI dispatch and JSON output."""

from __future__ import annotations

import json

import pytest

from ruin.cli import main


def test_triage_hypotheses_mode_signals(capsys: pytest.CaptureFixture[str]) -> None:
    code = main(
        [
            "--format",
            "json",
            "source",
            "triage",
            "T",
            "--mode",
            "hypotheses",
            "--signal",
            "oracle",
        ]
    )
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    titles = [item["title"] for item in data["items"]]
    assert any("Oracle" in title for title in titles)


def test_screen_json_null_for_none(capsys: pytest.CaptureFixture[str]) -> None:
    code = main(
        ["--format", "json", "target", "screen", "Example", "--chain", "ethereum"]
    )
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    # optional fields that are absent serialize as JSON null, not "None"
    assert data["listed_unix"] is None


def test_bare_token_routes_to_pipeline(capsys: pytest.CaptureFixture[str]) -> None:
    # a bare, unknown first token is routed to the pipeline op; it then exits 2
    # because pipeline requires --name/--forge-test/--method/--rpc
    with pytest.raises(SystemExit) as excinfo:
        main(["myprotocol"])
    assert excinfo.value.code == 2
    assert "required" in capsys.readouterr().err


def test_unknown_infra_template_exits_2(capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["source", "infra", "zorp"])
    assert code == 2
    assert "unknown infra template" in capsys.readouterr().err


def test_known_command_missing_args_exits_2(capsys: pytest.CaptureFixture[str]) -> None:
    # a known command with missing required args must error on that command,
    # not get re-routed to the pipeline fallback
    with pytest.raises(SystemExit) as excinfo:
        main(["target", "screen"])
    assert excinfo.value.code == 2
    assert "screen" in capsys.readouterr().err
