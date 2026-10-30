"""Fuzzing adapters for ``ruin``."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ruin.core.enums import FuzzKind, FuzzOutcome

if TYPE_CHECKING:
    from collections.abc import Sequence
from ruin.core.fuzz import Counterexample, FuzzResult
from ruin.services.subprocesses import run_command


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
            if "FAIL" in line:
                start = index
                break
    if start is None:
        return None
    raw = "\n".join(lines[start:]).strip()
    summary = lines[start].strip()
    trace = [line.strip() for line in lines[start + 1 :] if line.strip()]
    return Counterexample(summary=summary, raw=raw, trace=trace)


def parse_foundry_output(
    stdout: str = "", stderr: str = "", returncode: int = 0
) -> tuple[FuzzOutcome, str, Counterexample | None]:
    """Parse Foundry fuzz output."""
    output = "\n".join(part for part in (stdout, stderr) if part)
    if returncode == 0 and "FAIL" not in output:
        outcome = FuzzOutcome.PASSED
    elif (
        "FAIL" in output
        or "counterexample" in output.lower()
        or "violat" in output.lower()
    ):
        outcome = FuzzOutcome.VIOLATED
    else:
        outcome = FuzzOutcome.ERRORED
    counterexample = (
        _extract_counterexample(output) if outcome != FuzzOutcome.PASSED else None
    )
    return outcome, output.strip(), counterexample


def parse_echidna_output(
    stdout: str = "", stderr: str = "", returncode: int = 0
) -> tuple[FuzzOutcome, str, Counterexample | None]:
    """Parse Echidna output."""
    output = "\n".join(part for part in (stdout, stderr) if part)
    lowered = output.lower()
    if "failed" in lowered or "falsified" in lowered:
        outcome = FuzzOutcome.VIOLATED
    elif returncode == 0 or "passed" in lowered or "no failures" in lowered:
        outcome = FuzzOutcome.PASSED
    else:
        outcome = FuzzOutcome.ERRORED
    counterexample = (
        _extract_counterexample(output) if outcome != FuzzOutcome.PASSED else None
    )
    return outcome, output.strip(), counterexample


def parse_medusa_output(
    stdout: str = "", stderr: str = "", returncode: int = 0
) -> tuple[FuzzOutcome, str, Counterexample | None]:
    """Parse Medusa output."""
    output = "\n".join(part for part in (stdout, stderr) if part)
    lowered = output.lower()
    if "failed" in lowered or "broken" in lowered or "violation" in lowered:
        outcome = FuzzOutcome.VIOLATED
    elif returncode == 0 or "passed" in lowered or "no failures" in lowered:
        outcome = FuzzOutcome.PASSED
    else:
        outcome = FuzzOutcome.ERRORED
    counterexample = (
        _extract_counterexample(output) if outcome != FuzzOutcome.PASSED else None
    )
    return outcome, output.strip(), counterexample


class FoundryFuzzer:
    """Run Foundry fuzz/invariant tests."""

    def __init__(
        self,
        command: str | Sequence[str] | None = None,
        match_test: str | None = None,
        kind: FuzzKind | str = FuzzKind.INVARIANT,
    ) -> None:
        """Initialize the fuzzer."""
        self.command = command
        self.match_test = match_test
        if isinstance(kind, str):
            mapping = {
                "fuzz": FuzzKind.FUZZ,
                "invariant": FuzzKind.INVARIANT,
            }
            self.kind = mapping.get(kind.lower(), FuzzKind.INVARIANT)
        else:
            self.kind = kind

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
        match_test: str | None = None,
        command: str | Sequence[str] | None = None,
    ) -> list[str]:
        _ = target_name
        command_value = command if command is not None else self.command
        command_list = self._command_list(command_value)
        if command_list is not None:
            return command_list
        effective_match = match_test if match_test is not None else self.match_test
        if effective_match is not None and effective_match.strip() != "":
            return ["forge", "test", "--match-test", effective_match]
        return ["forge", "test"]

    def _parse_output(
        self, stdout: str, stderr: str, returncode: int
    ) -> tuple[FuzzOutcome, str, Counterexample | None]:
        return parse_foundry_output(stdout, stderr, returncode)

    def fuzz(
        self,
        target: object,
        match_test: str | None = None,
        command: str | Sequence[str] | None = None,
        kind: FuzzKind | str | None = None,
        finding: str | None = None,
    ) -> FuzzResult:
        """Run the fuzzer and return a result."""
        target_name = _target_name(target)
        kind_value = self.kind if kind is None else kind
        if isinstance(kind_value, str):
            mapping = {
                "fuzz": FuzzKind.FUZZ,
                "invariant": FuzzKind.INVARIANT,
            }
            kind_value = mapping.get(kind_value.lower(), FuzzKind.INVARIANT)
        resolved_finding = finding
        cmd = self._build_command(target_name, match_test=match_test, command=command)
        try:
            process = run_command(cmd)
        except (FileNotFoundError, OSError, RuntimeError) as error:
            result = FuzzResult(
                target=target_name,
                kind=kind_value,
                outcome=FuzzOutcome.ERRORED,
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
        result = FuzzResult(
            target=target_name,
            kind=kind_value,
            outcome=outcome,
            detail=detail,
            counterexample=counterexample,
            skipped=False,
        )
        if resolved_finding is not None:
            result = result.with_finding(resolved_finding)
        return result


class EchidnaAdapter(FoundryFuzzer):
    """Run Echidna and parse minimal output."""

    def _build_command(
        self,
        target_name: str,
        match_test: str | None = None,
        command: str | Sequence[str] | None = None,
    ) -> list[str]:
        command_value = command if command is not None else self.command
        _ = match_test
        command_list = self._command_list(command_value)
        if command_list is not None:
            return command_list
        return ["echidna", str(target_name)]

    def _parse_output(
        self, stdout: str, stderr: str, returncode: int
    ) -> tuple[FuzzOutcome, str, Counterexample | None]:
        return parse_echidna_output(stdout, stderr, returncode)


class MedusaAdapter(FoundryFuzzer):
    """Run Medusa and parse minimal output."""

    def _build_command(
        self,
        target_name: str,
        match_test: str | None = None,
        command: str | Sequence[str] | None = None,
    ) -> list[str]:
        command_value = command if command is not None else self.command
        _ = match_test
        command_list = self._command_list(command_value)
        if command_list is not None:
            return command_list
        return ["medusa", "fuzz", str(target_name)]

    def _parse_output(
        self, stdout: str, stderr: str, returncode: int
    ) -> tuple[FuzzOutcome, str, Counterexample | None]:
        return parse_medusa_output(stdout, stderr, returncode)
