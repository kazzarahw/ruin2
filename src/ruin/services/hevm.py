"""hevm symbolic-execution adapter for ``ruin``."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ruin.core.enums import SymbolicOutcome
from ruin.services.symbolic import _extract_counterexample, _SymbolicAdapter

if TYPE_CHECKING:
    from collections.abc import Sequence

    from ruin.core.symbolic import Counterexample


def parse_hevm_output(
    stdout: str = "", stderr: str = "", returncode: int = 0
) -> tuple[SymbolicOutcome, str, Counterexample | None]:
    """Parse hevm symbolic-execution output."""
    output = "\n".join(part for part in (stdout, stderr) if part)
    lowered = output.lower()
    counterexample = _extract_counterexample(output)
    if "qed" in lowered and counterexample is None:
        return SymbolicOutcome.PROVEN, "hevm proved the property", None
    if counterexample is not None:
        return SymbolicOutcome.UNDECIDED, "hevm found a counterexample", counterexample
    if "error" in lowered or "exception" in lowered:
        return SymbolicOutcome.ERROR, "hevm reported an error", None
    if returncode != 0:
        return SymbolicOutcome.ERROR, "hevm exited non-zero", None
    return SymbolicOutcome.UNDECIDED, "hevm returned no verdict", None


class HevmAdapter(_SymbolicAdapter):
    """Run hevm symbolic execution and parse minimal output."""

    def __init__(self, command: str | Sequence[str] | None = None) -> None:
        """Initialize the adapter."""
        super().__init__("hevm", command=command)

    def _build_command(
        self,
        target_name: str,
        command: str | Sequence[str] | None = None,
    ) -> list[str]:
        _ = target_name
        command_value = command if command is not None else self.command
        command_list = self._command_list(command_value)
        if command_list is not None:
            return command_list
        return ["hevm", "symbolic", "exec"]

    def _parse_output(
        self, stdout: str, stderr: str, returncode: int
    ) -> tuple[SymbolicOutcome, str, Counterexample | None]:
        return parse_hevm_output(stdout, stderr, returncode)
