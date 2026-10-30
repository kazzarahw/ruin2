"""Tests for trust."""

from ruin.core.trust import trust_model


def test_trust() -> None:
    model = trust_model("P").custodial(True).with_assumption("operator", "flow", False)
    assert "Trust Model" in model.render_markdown()
