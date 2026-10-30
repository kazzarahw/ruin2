"""Tests for CLI entry points and async wrappers."""

from __future__ import annotations

import asyncio
import json
from typing import TYPE_CHECKING
from unittest.mock import patch

if TYPE_CHECKING:
    import pytest

from ruin import run, run_json
from ruin.cli import main


class TestRunAsync:
    def test_run_returns_string(self) -> None:
        result = asyncio.run(run("screen", name="TestProto", chain="ethereum"))
        assert isinstance(result, str)

    def test_run_json_returns_object(self) -> None:
        result = asyncio.run(run_json("screen", name="TestProto", chain="ethereum"))
        assert isinstance(result, dict)


class TestMain:
    def test_no_command_prints_help(self, capsys: pytest.CaptureFixture[str]) -> None:
        code = main([])
        assert code == 0
        captured = capsys.readouterr()
        assert "usage: ruin" in captured.out

    def test_run_screen(self, capsys: pytest.CaptureFixture[str]) -> None:
        code = main(["target", "screen", "MyProto", "--chain", "ethereum"])
        assert code == 0
        captured = capsys.readouterr()
        assert "# Target Screen — MyProto" in captured.out

    def test_run_json_format(self, capsys: pytest.CaptureFixture[str]) -> None:
        code = main(
            ["--format", "json", "target", "screen", "JsonProto", "--chain", "polygon"]
        )
        assert code == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert isinstance(data, dict)

    def test_error_returns_2(self) -> None:
        with patch("ruin.cli.run_operation", side_effect=RuntimeError("fail")):
            code = main(["target", "screen", "X", "--chain", "eth"])
        assert code == 2

    def test_rng_hack_summary_join(self) -> None:
        code = main(
            ["classes", "rng", "blockhash", "predictable", "--source", "Chainlink"]
        )
        assert code == 0


class TestMainModule:
    def test_main_module_importable(self) -> None:
        import importlib

        importlib.import_module("ruin.__main__")
