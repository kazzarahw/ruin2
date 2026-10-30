"""Pipeline status helpers for ``ruin``."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum

from ruin.core.ids import ProtocolName


class PipelineStage(IntEnum):
    """A stage in the hunting pipeline."""

    SCREEN = 0
    SOURCE = 1
    SAST = 2
    REVIEW = 3
    REPORT = 4


class StageStatus:
    """A stage's status."""

    DONE = "Done"
    IN_PROGRESS = "InProgress"
    BLOCKED = "Blocked"


_STAGE_NAMES: dict[PipelineStage, str] = {
    PipelineStage.SCREEN: "Screen",
    PipelineStage.SOURCE: "Source",
    PipelineStage.SAST: "SAST",
    PipelineStage.REVIEW: "Review",
    PipelineStage.REPORT: "Report",
}

STAGE_BY_NAME: dict[str, PipelineStage] = {
    "screen": PipelineStage.SCREEN,
    "source": PipelineStage.SOURCE,
    "sast": PipelineStage.SAST,
    "review": PipelineStage.REVIEW,
    "report": PipelineStage.REPORT,
}

STATUS_BY_NAME: dict[str, str] = {
    "done": StageStatus.DONE,
    "inprogress": StageStatus.IN_PROGRESS,
    "blocked": StageStatus.BLOCKED,
}


def _stage_name(stage: PipelineStage) -> str:
    return _STAGE_NAMES[stage]


@dataclass
class PipelineStatus:
    """The pipeline status for a target."""

    name: ProtocolName
    stages: list[tuple[PipelineStage, str, str]] = field(default_factory=list)

    def with_stage(
        self, stage: PipelineStage, status: str, note: str
    ) -> PipelineStatus:
        """Set a stage's status and note."""
        for index, (existing, _status, _note) in enumerate(self.stages):
            if existing == stage:
                self.stages[index] = (stage, status, note)
                return self
        self.stages.append((stage, status, note))
        return self

    def render_markdown(self) -> str:
        """Render the pipeline status as Markdown."""
        lookup: dict[PipelineStage, tuple[str, str]] = {}
        for stage, status, note in self.stages:
            lookup[stage] = (status, note)
        lines: list[str] = []
        lines.append(f"# Pipeline — {self.name.as_str()}")
        lines.append("")
        for stage in PipelineStage:
            if stage in lookup:
                status, note = lookup[stage]
                box = (
                    "x" if status == "Done" else "…" if status == "InProgress" else "!"
                )
                lines.append(f"- [{box}] {_stage_name(stage)} — {note}")
            else:
                lines.append(f"- [ ] {_stage_name(stage)} — (not started)")
        lines.append("")
        lines.append(
            "> The pipeline is: screen → source → SAST → review → report. The "
            "`x`/`…`/`!` marks are done / in-flight / blocked. A blocked stage is a "
            "reason, not a door-close — the researcher discriminates (a canonical / "
            "audited core ships here; a bespoke / public-source / new / small / "
            "trustless target is a full-audit target)."
        )
        return "\n".join(lines)


def pipeline_status(name: str) -> PipelineStatus:
    """Record a pipeline status."""
    return PipelineStatus(name=ProtocolName.new(name))
