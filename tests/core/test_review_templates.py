"""Tests for off-chain infra review templates."""

from __future__ import annotations

import pytest

from ruin.core.review_templates import get_template, list_templates


def test_list_templates() -> None:
    names = list_templates()
    assert "keeper" in names
    assert "oracle-backend" in names
    assert "multisig" in names
    assert "bridge-relayer" in names


def test_get_template_case_insensitive() -> None:
    template = get_template("  Keeper ")
    assert template.name == "keeper"


def test_get_template_unknown_raises() -> None:
    with pytest.raises(ValueError, match="unknown infra template"):
        get_template("zorp")


def test_render_contains_sections() -> None:
    text = get_template("multisig").render_markdown()
    assert "# Infra Review" in text
    assert "## Checks" in text
    assert "## Look-fors" in text
    assert "timelock" in text.lower()
