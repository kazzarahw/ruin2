"""Analyzer adapters for ``ruin``."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Protocol

from ruin.core.domain import Vuln
from ruin.core.enums import Severity, VulnClass
from ruin.services.slither import run_slither
from ruin.services.subprocesses import run_command

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from ruin.core.runs import Target


class _HasStdout(Protocol):
    """Result of a semgrep run: anything exposing a text stdout."""

    stdout: str


class SlitherAnalyzer:
    """Analyzer backed by Slither."""

    def __init__(
        self,
        source: Path,
        runner: Callable[[Path], list[Vuln]] | None = None,
    ) -> None:
        """Initialize the analyzer with an optional injectable runner."""
        self.source = source
        self.runner = runner

    def analyze(self, _target: Target) -> list[Vuln]:
        """Analyze a target with Slither."""
        call = self.runner or run_slither
        return call(self.source)


class SemgrepAnalyzer:
    """Analyzer backed by Semgrep."""

    def __init__(
        self,
        source: Path,
        runner: Callable[[list[str]], _HasStdout] | None = None,
    ) -> None:
        """Initialize the analyzer with an optional injectable runner."""
        self.source = source
        self.runner = runner

    def analyze(self, _target: Target) -> list[Vuln]:
        """Analyze a target with Semgrep."""
        call = self.runner or run_command
        process = call(["semgrep", "scan", "--json", str(self.source)])
        try:
            doc = json.loads(process.stdout)
        except (json.JSONDecodeError, TypeError):
            return []
        results = doc.get("results", []) if isinstance(doc, dict) else []
        vulns: list[Vuln] = []
        if isinstance(results, list):
            for result in results:
                if not isinstance(result, dict):
                    continue
                extra = result.get("extra", {})
                message = extra.get("message", "") if isinstance(extra, dict) else ""
                if not isinstance(message, str) or not message:
                    message = str(result.get("check_id", "semgrep finding"))
                vulns.append(
                    Vuln(
                        klass=VulnClass.OTHER("semgrep"),
                        severity=Severity.LOW,
                        summary=message,
                        poc=None,
                    )
                )
        return vulns
