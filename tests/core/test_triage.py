"""Tests for triage."""

import json

from ruin.core.triage import slither_checks, triage_vulns


def test_triage() -> None:
    triage = triage_vulns("P", ["weak-prng", "timestamp"])
    assert "Vuln Triage" in triage.render_markdown()


def test_slither_checks() -> None:
    data = {"results": {"detectors": [{"check": "weak-prng"}, {"check": "timestamp"}]}}
    checks = slither_checks(json.dumps(data))
    assert "weak-prng" in checks


def test_new_format_klass_maps_to_lead() -> None:
    data = [{"klass": "Reentrancy", "severity": "Medium", "summary": "re-entrancy"}]
    checks = slither_checks(json.dumps(data))
    assert checks == ["reentrancy"]
    triage = triage_vulns("P", checks)
    assert "reentrancy" in triage.render_markdown()


def test_unknown_checks_render_in_other_section() -> None:
    triage = triage_vulns("P", ["solc-version"])
    text = triage.render_markdown()
    assert "Other (unclassified)" in text
    assert "solc-version" in text
