"""Symbolic execution adapters for ``ruin``."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ruin.core.enums import SymbolicOutcome
from ruin.core.symbolic import Counterexample, SymbolicResult
from ruin.services.subprocesses import run_command

if TYPE_CHECKING:
    from collections.abc import Sequence


def _target_name(target: object) -> str:
    name = getattr(target, "name", None)
    if name is not None:
        as_str = getattr(name, "as_str", None)
        if callable(as_str):
            return str(as_str())
        return str(name)
    return str(target)


def _extract_counterexample(text: str) -> Counterexample | None:
    lines = text.splitlines()
    start: int | None = None
    for index, line in enumerate(lines):
        if "counterexample" in line.lower():
            start = index
            break
    if start is None:
        for index, line in enumerate(lines):
            if "FAIL" in line or "issue" in line.lower():
                start = index
                break
    if start is None:
        return None
    raw = "\n".join(lines[start:]).strip()
    summary = lines[start].strip()
    trace = [line.strip() for line in lines[start + 1 :] if line.strip()]
    return Counterexample(summary=summary, raw=raw, trace=trace)


def parse_halmos_output(
    stdout: str = "", stderr: str = "", returncode: int = 0
) -> tuple[SymbolicOutcome, str, Counterexample | None]:
    """Parse Halmos output."""
    output = "\n".join(part for part in (stdout, stderr) if part)
    lowered = output.lower()
    if "unsupported" in lowered:
        outcome = SymbolicOutcome.UNSUPPORTED
    elif "error" in lowered or "exception" in lowered or "traceback" in lowered:
        outcome = SymbolicOutcome.ERROR
    elif "counterexample" in lowered or "fail" in lowered or "violation" in lowered:
        outcome = SymbolicOutcome.UNDECIDED
    elif (
        returncode == 0
        or "proven" in lowered
        or "pass" in lowered
        or "verified" in lowered
    ):
        outcome = SymbolicOutcome.PROVEN
    elif returncode != 0 and not lowered.strip():
        outcome = SymbolicOutcome.ERROR
    else:
        outcome = SymbolicOutcome.UNDECIDED
    counterexample = (
        _extract_counterexample(output) if outcome != SymbolicOutcome.PROVEN else None
    )
    return outcome, output.strip(), counterexample


def parse_mythril_output(
    stdout: str = "", stderr: str = "", returncode: int = 0
) -> tuple[SymbolicOutcome, str, Counterexample | None]:
    """Parse Mythril output."""
    output = "\n".join(part for part in (stdout, stderr) if part)
    lowered = output.lower()
    if "unsupported" in lowered:
        outcome = SymbolicOutcome.UNSUPPORTED
    elif "error" in lowered or "exception" in lowered or "traceback" in lowered:
        outcome = SymbolicOutcome.ERROR
    elif (
        returncode == 0
        or "no issues" in lowered
        or "safe" in lowered
        or "proved" in lowered
    ):
        outcome = SymbolicOutcome.PROVEN
    elif (
        "issue" in lowered
        or "warning" in lowered
        or "counterexample" in lowered
        or "violation" in lowered
    ):
        outcome = SymbolicOutcome.UNDECIDED
    elif returncode != 0 and not lowered.strip():
        outcome = SymbolicOutcome.ERROR
    else:
        outcome = SymbolicOutcome.UNDECIDED
    counterexample = (
        _extract_counterexample(output) if outcome != SymbolicOutcome.PROVEN else None
    )
    return outcome, output.strip(), counterexample


class _SymbolicAdapter:
    """Shared adapter logic for symbolic solvers."""

    def __init__(
        self,
        tool: str,
        command: str | Sequence[str] | None = None,
    ) -> None:
        """Initialize the adapter."""
        self.tool = tool
        self.command = command

    def _command_list(self, value: str | Sequence[str] | None) -> list[str] | None:
        if value is None:
            return None
        if isinstance(value, str):
            return value.split()
        if isinstance(value, (list, tuple)):
            return [str(item) for item in value]
        return None

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
        return []

    def _parse_output(
        self, stdout: str, stderr: str, returncode: int
    ) -> tuple[SymbolicOutcome, str, Counterexample | None]:
        return parse_halmos_output(stdout, stderr, returncode)

    def run(
        self,
        target: object,
        command: str | Sequence[str] | None = None,
        finding: str | None = None,
        linked_finding: str | None = None,
    ) -> SymbolicResult:
        """Run the solver and return a result."""
        target_name = _target_name(target)
        cmd = self._build_command(target_name, command=command)
        resolved_finding = finding if finding is not None else linked_finding
        try:
            process = run_command(cmd)
        except (FileNotFoundError, OSError, RuntimeError) as error:
            result = SymbolicResult(
                target=target_name,
                tool=self.tool,
                outcome=SymbolicOutcome.ERROR,
                detail=str(error),
                skipped=True,
            )
            if resolved_finding is not None:
                result = result.with_finding(resolved_finding)
            return result
        stdout = getattr(process, "stdout", "") or ""
        stderr = getattr(process, "stderr", "") or ""
        returncode = getattr(process, "returncode", 0)
        outcome, detail, counterexample = self._parse_output(stdout, stderr, returncode)
        result = SymbolicResult(
            target=target_name,
            tool=self.tool,
            outcome=outcome,
            detail=detail,
            counterexample=counterexample,
            skipped=False,
        )
        if resolved_finding is not None:
            result = result.with_finding(resolved_finding)
        return result


class HalmosAdapter(_SymbolicAdapter):
    """Run Halmos and parse minimal output."""

    def __init__(self, command: str | Sequence[str] | None = None) -> None:
        """Initialize the adapter."""
        super().__init__("halmos", command=command)

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
        return ["halmos"]


class MythrilAdapter(_SymbolicAdapter):
    """Run Mythril and parse minimal output."""

    def __init__(self, command: str | Sequence[str] | None = None) -> None:
        """Initialize the adapter."""
        super().__init__("mythril", command=command)

    def _build_command(
        self,
        target_name: str,
        command: str | Sequence[str] | None = None,
    ) -> list[str]:
        command_value = command if command is not None else self.command
        command_list = self._command_list(command_value)
        if command_list is not None:
            return command_list
        return ["myth", "analyze", str(target_name)]

    def _parse_output(
        self, stdout: str, stderr: str, returncode: int
    ) -> tuple[SymbolicOutcome, str, Counterexample | None]:
        return parse_mythril_output(stdout, stderr, returncode)
