"""Tests for research."""

from ruin.core.domain import Vuln
from ruin.core.enums import Severity, VulnClass
from ruin.core.research import research_card


def test_research_card() -> None:
    vuln = Vuln(klass=VulnClass.LOGIC, severity=Severity.HIGH, summary="s")
    card = research_card(vuln, "m").with_sources(["src"])
    assert "Research Card" in card.render_markdown()
