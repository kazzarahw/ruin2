"""Tests for ``python_llm_template.cli``."""

import pytest

from python_llm_template.cli import main


def test_main_prints_the_greeting(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["ada"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out == "Hello, Ada!\n"


def test_main_reports_invalid_names(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main([""])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert captured.err.startswith("error:")
