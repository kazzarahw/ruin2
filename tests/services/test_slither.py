"""Tests for slither service."""

from pathlib import Path
from typing import Any, cast

from ruin.services import slither as slither_service


class FakeProcess:
    def __init__(self) -> None:
        self.stdout = '{"results": {"detectors": []}}'
        self.returncode = 0


def test_run_slither() -> None:
    def fake_run(_argv: list[str], *, timeout: float = 30.0) -> FakeProcess:
        return FakeProcess()

    cast("Any", slither_service).run_command = fake_run
    assert slither_service.run_slither(Path("x.py")) == []
