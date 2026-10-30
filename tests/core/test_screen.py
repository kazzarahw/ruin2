"""Tests for screen."""

from ruin.core.protocols import ProtocolSummary
from ruin.core.screen import screen_from_protocol, target_screen


def test_screen() -> None:
    screen = target_screen("Z", "Ethereum", 1).with_bespoke(True)
    assert "Target Screen" in screen.render_markdown()


def test_screen_from_protocol() -> None:
    summary = ProtocolSummary.new("A", "a", 10, ["Ethereum"], "Defi")
    screen = screen_from_protocol(summary)
    assert screen.chain == "Ethereum"
