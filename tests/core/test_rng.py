"""Tests for rng."""

from ruin.core.domain import Vuln
from ruin.core.enums import Severity, VulnClass
from ruin.core.rng import rng_hack_assessment


def test_rng() -> None:
    vuln = Vuln(klass=VulnClass.LOGIC, severity=Severity.HIGH, summary="s")
    assessment = rng_hack_assessment(vuln, "m", "block.timestamp").with_decision("d")
    assert "RNG-Hack" in assessment.render_markdown()
