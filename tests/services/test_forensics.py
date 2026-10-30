"""Tests for forensics service."""

from typing import Any, cast

from ruin.core.forensics import TransactionTrace
from ruin.services import forensics as forensics_service


class FakeProcess:
    stdout = "step one\nstep two\n"
    returncode = 0


def test_trace_transaction() -> None:
    cast("Any", forensics_service).run_command = lambda _argv: FakeProcess()
    trace = forensics_service.trace_transaction("0xabc", "http://x")
    assert isinstance(trace, TransactionTrace)
    assert trace.steps == ["step one", "step two"]
