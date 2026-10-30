"""Report bundle helpers for ``ruin``."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ruin.core.ids import ProtocolName

if TYPE_CHECKING:
    from ruin.core.domain import DrainProof, Poc, Report
    from ruin.core.pipeline import PipelineStatus
    from ruin.core.research import ResearchCard
    from ruin.core.screen import TargetScreen
    from ruin.core.trust import TrustModel


@dataclass
class ReportBundle:
    """A final report bundle."""

    name: ProtocolName
    report: Report | None = None
    poc: Poc | None = None
    drain: DrainProof | None = None
    research: ResearchCard | None = None
    trust: TrustModel | None = None
    screen: TargetScreen | None = None
    pipeline: PipelineStatus | None = None

    def with_report(self, report: Report) -> ReportBundle:
        """Attach a report."""
        self.report = report
        return self

    def with_poc(self, poc: Poc) -> ReportBundle:
        """Attach a PoC."""
        self.poc = poc
        return self

    def with_drain(self, drain: DrainProof) -> ReportBundle:
        """Attach a drain proof."""
        self.drain = drain
        return self

    def with_research(self, research: ResearchCard) -> ReportBundle:
        """Attach a research card."""
        self.research = research
        return self

    def with_trust(self, trust: TrustModel) -> ReportBundle:
        """Attach a trust model."""
        self.trust = trust
        return self

    def with_screen(self, screen: TargetScreen) -> ReportBundle:
        """Attach a target screen."""
        self.screen = screen
        return self

    def with_pipeline(self, pipeline: PipelineStatus) -> ReportBundle:
        """Attach a pipeline status."""
        self.pipeline = pipeline
        return self

    def render_markdown(self) -> str:
        """Render the report bundle as Markdown."""
        parts: list[str] = [f"# Report Bundle — {self.name.as_str()}", ""]
        if self.pipeline is not None:
            parts.append(self.pipeline.render_markdown())
            parts.append("---")
        if self.screen is not None:
            parts.append(self.screen.render_markdown())
            parts.append("---")
        if self.report is not None:
            parts.append(self.report.render_markdown())
            parts.append("---")
        if self.research is not None:
            parts.append(self.research.render_markdown())
            parts.append("---")
        if self.trust is not None:
            parts.append(self.trust.render_markdown())
            parts.append("---")
        if self.drain is not None:
            parts.append(
                "## Drain Proof\n\n"
                f"method: {self.drain.method}\n"
                f"asset: {self.drain.asset.as_str()}\n"
                f"amount: {self.drain.amount} whole tokens"
            )
            parts.append("---")
        if self.poc is not None:
            drain = (
                f"{self.poc.expected_drain.units} of "
                f"{self.poc.expected_drain.asset.as_str()}"
                if self.poc.expected_drain is not None
                else "unknown"
            )
            parts.append(
                "## `PoC`\n\n"
                f"method: {self.poc.method}\n"
                f"forge test: {self.poc.forge_test}\n"
                f"expected drain: {drain}"
            )
        return "\n".join(parts)


def report_bundle(name: str) -> ReportBundle:
    """Record a report bundle."""
    return ReportBundle(name=ProtocolName.new(name))
