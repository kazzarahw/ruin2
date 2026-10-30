"""More slither_io tests."""

import json

from ruin.core.slither_io import _parse_vuln_class, parse_vulns


def test_parse_vuln_class_other() -> None:
    assert _parse_vuln_class({"Other": "x"}).detail == "x"


def test_parse_vulns_review() -> None:
    doc = {
        "source": "s",
        "candidates": [{"klass": "Logic", "severity": "High", "summary": "s"}],
    }
    assert len(parse_vulns(json.dumps(doc))) == 1
