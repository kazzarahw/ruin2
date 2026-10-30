"""Tests for slither_io."""

import json

from ruin.core.domain import Vuln
from ruin.core.enums import Severity, VulnClass
from ruin.core.slither_io import parse_slither, parse_vulns, serialize_vulns


def test_parse_slither() -> None:
    data = {"results": {"detectors": [{"check": "weak-prng", "impact": "High"}]}}
    vulns = parse_slither(json.dumps(data))
    assert len(vulns) == 1


def test_parse_slither_new_list_format() -> None:
    data = [
        {
            "klass": {"Other": "arbitrary-send-eth"},
            "severity": "High",
            "summary": "address.call{value: x}()",
        },
        {"klass": "suicide", "severity": "High", "summary": "selfdestruct"},
        {"klass": {"Other": "timestamp"}, "severity": "Low", "summary": "noise"},
    ]
    vulns = parse_slither(json.dumps(data))
    assert len(vulns) == 3
    assert vulns[0].severity is Severity.HIGH
    assert vulns[0].klass == VulnClass.ACCESS_CONTROL
    assert vulns[1].klass == VulnClass.LOGIC


def test_serialize_parse_vulns() -> None:
    vuln = Vuln(klass=VulnClass.LOGIC, severity=Severity.HIGH, summary="s")
    text = serialize_vulns([vuln])
    parsed = parse_vulns(text)
    assert len(parsed) == 1
