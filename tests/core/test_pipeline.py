"""Tests for pipeline."""

from ruin.core.pipeline import PipelineStage, pipeline_status


def test_pipeline() -> None:
    status = pipeline_status("P").with_stage(PipelineStage.SCREEN, "Done", "note")
    assert "Pipeline" in status.render_markdown()
