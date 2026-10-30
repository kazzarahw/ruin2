"""Tests for analyzers."""

from pathlib import Path

from ruin.core.domain import Target
from ruin.core.enums import TargetMode
from ruin.core.ids import ContractId
from ruin.services import analyzers as analyzer_service


def _target() -> Target:
    return Target.new("P", [ContractId.new("0x" + "1" * 40)], None, TargetMode.RESEARCH)


class _Process:
    def __init__(self, stdout: str) -> None:
        """Store canned command output."""
        self.stdout = stdout
        self.returncode = 0


def test_slither_analyzer_empty() -> None:
    analyzer = analyzer_service.SlitherAnalyzer(Path("x.sol"), runner=lambda _p: [])
    assert analyzer.analyze(_target()) == []


def test_slither_analyzer_finding() -> None:
    from ruin.core.domain import Vuln
    from ruin.core.enums import Severity, VulnClass

    def fake(_p: Path) -> list[Vuln]:
        return [
            Vuln(
                klass=VulnClass.REENTRANCY,
                severity=Severity.HIGH,
                summary="reentrant",
                poc=None,
            )
        ]

    analyzer = analyzer_service.SlitherAnalyzer(Path("x.sol"), runner=fake)
    assert len(analyzer.analyze(_target())) == 1


def test_semgrep_analyzer_empty() -> None:
    def runner(_argv: list[str]) -> _Process:
        return _Process('{"results": []}')

    analyzer = analyzer_service.SemgrepAnalyzer(Path("x.sol"), runner=runner)
    assert analyzer.analyze(_target()) == []


def test_semgrep_analyzer_finding() -> None:
    def runner(_argv: list[str]) -> _Process:
        return _Process('{"results": [{"extra": {"message": "bad"}}]}')

    analyzer = analyzer_service.SemgrepAnalyzer(Path("x.sol"), runner=runner)
    result = analyzer.analyze(_target())
    assert len(result) == 1
    assert result[0].summary == "bad"


def test_semgrep_analyzer_bad_json() -> None:
    def runner(_argv: list[str]) -> _Process:
        return _Process("not json")

    analyzer = analyzer_service.SemgrepAnalyzer(Path("x.sol"), runner=runner)
    assert analyzer.analyze(_target()) == []


def test_module_still_exports_runners() -> None:
    # default (no runner) still resolves to the real subprocess helpers
    assert analyzer_service.run_command is not None
    assert analyzer_service.run_slither is not None
