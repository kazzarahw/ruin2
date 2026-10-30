"""Slither and vuln-file I/O helpers for ``ruin``."""

from __future__ import annotations

import json
from typing import cast

from ruin.core.domain import Vuln
from ruin.core.enums import Severity, VulnClass


def _classify(check: str) -> VulnClass:
    """Map a slither check name to a vuln class."""
    mapping = {
        "reentrancy-eth": VulnClass.REENTRANCY,
        "reentrancy-no-eth": VulnClass.REENTRANCY,
        "reentrancy-benign": VulnClass.REENTRANCY,
        "uninitialized-state": VulnClass.LOGIC,
        "suicide": VulnClass.LOGIC,
        "arbitrary-send-eth": VulnClass.ACCESS_CONTROL,
        "unchecked-lowlevel": VulnClass.ACCESS_CONTROL,
        "arithmetic": VulnClass.ASSET_ACCOUNTING,
        "unchecked-transfer": VulnClass.ASSET_ACCOUNTING,
    }
    if check in mapping:
        return mapping[check]
    if check.startswith("signature"):
        return VulnClass.SIGNATURE_TUNNELING
    return VulnClass.other(check)


def _impact_to_severity(impact: str) -> Severity:
    """Map slither impact to severity."""
    if impact == "High":
        return Severity.HIGH
    if impact == "Medium":
        return Severity.MEDIUM
    if impact == "Informational":
        return Severity.INFORMATIONAL
    return Severity.LOW


def detector_fields(item: dict[str, object]) -> tuple[str, str, str]:
    """Read ``(check, description, impact)`` from either slither JSON shape.

    Slither <=0.10 uses ``check``/``description``/``impact``; newer builds
    emit ``klass``/``summary``/``severity`` in a bare list.
    """
    check = item.get("check", "")
    if not isinstance(check, str) or not check:
        klass = item.get("klass", "")
        if isinstance(klass, dict):
            other = klass.get("Other", "")
            check = other if isinstance(other, str) else ""
        elif isinstance(klass, str):
            check = klass
        else:
            check = ""
    description = item.get("description", "")
    if not isinstance(description, str) or not description:
        summary = item.get("summary", "")
        description = summary if isinstance(summary, str) else ""
    impact = item.get("impact", "")
    if not isinstance(impact, str) or not impact:
        severity = item.get("severity", "")
        impact = severity if isinstance(severity, str) else ""
    return check.lower(), description, impact


def detectors_from(doc: object) -> list[object]:
    """Return the detector item list from either slither JSON shape."""
    if isinstance(doc, dict):
        results = doc.get("results")
        if isinstance(results, dict):
            raw = results.get("detectors", [])
            if isinstance(raw, list):
                return cast("list[object]", raw)
        return []
    if isinstance(doc, list):
        return cast("list[object]", doc)
    return []


def parse_slither(json_text: str) -> list[Vuln]:
    """Parse slither JSON output into vuln candidates.

    Accepts both the legacy ``{"results": {"detectors": [...]}}`` document
    and the newer bare-list format emitted by current slither releases.
    """
    try:
        doc = json.loads(json_text)
    except json.JSONDecodeError as error:
        raise ValueError(f"invalid recon document: {error}") from error
    detectors = detectors_from(doc)
    vulns: list[Vuln] = []
    for item in detectors:
        if not isinstance(item, dict):
            continue
        check, description, impact = detector_fields(cast("dict[str, object]", item))
        summary = description or check
        vulns.append(
            Vuln(
                klass=_classify(check),
                severity=_impact_to_severity(impact),
                summary=summary,
                poc=None,
            )
        )
    return vulns


def serialize_vulns(vulns: list[Vuln]) -> str:
    """Serialize vuln candidates to JSON."""
    out: list[dict[str, object]] = []
    for vuln in vulns:
        klass: object
        if vuln.klass.detail is not None:
            klass = {"Other": vuln.klass.detail}
        else:
            klass = vuln.klass.name
        out.append(
            {
                "klass": klass,
                "severity": vuln.severity.value,
                "summary": vuln.summary,
            }
        )
    return json.dumps(out, separators=(",", ":"))


def serialize_review_scaffold(source: str) -> str:
    """Build a review scaffold JSON document."""
    doc = {"source": source, "candidates": []}
    return json.dumps(doc, indent=2)


def parse_vulns(json_text: str) -> list[Vuln]:
    """Parse a vulns JSON file into vuln candidates."""
    try:
        value = json.loads(json_text)
    except json.JSONDecodeError as error:
        raise ValueError(f"invalid recon document: {error}") from error

    candidates: list[object]
    if isinstance(value, list):
        candidates = value
    elif isinstance(value, dict):
        raw_candidates = value.get("candidates", [])
        candidates = raw_candidates if isinstance(raw_candidates, list) else []
    else:
        candidates = []

    vulns: list[Vuln] = []
    for item in candidates:
        if not isinstance(item, dict):
            continue
        klass_raw = item.get("klass")
        klass = _parse_vuln_class(klass_raw)
        severity_raw = item.get("severity", "Low")
        severity = _parse_severity(severity_raw)
        summary = item.get("summary", "")
        if not isinstance(summary, str):
            summary = ""
        vulns.append(Vuln(klass=klass, severity=severity, summary=summary, poc=None))
    return vulns


def _parse_vuln_class(raw: object) -> VulnClass:
    if isinstance(raw, str):
        for variant in (
            VulnClass.REENTRANCY,
            VulnClass.ACCESS_CONTROL,
            VulnClass.SIGNATURE_TUNNELING,
            VulnClass.ASSET_ACCOUNTING,
            VulnClass.FLASH_LOAN,
            VulnClass.LOGIC,
        ):
            if raw == variant.name:
                return variant
        return VulnClass.other(raw)
    if isinstance(raw, dict):
        other = raw.get("Other")
        if isinstance(other, str):
            return VulnClass.other(other)
    return VulnClass.LOGIC


def _parse_severity(raw: object) -> Severity:
    if not isinstance(raw, str):
        return Severity.LOW
    for variant in Severity:
        if raw == variant.value:
            return variant
    return Severity.LOW
