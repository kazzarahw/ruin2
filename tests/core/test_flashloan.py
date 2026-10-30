"""Tests for flash-loan scaffold."""

from ruin.core.flashloan import FlashLoanScaffold


def test_flashloan_scaffold_render() -> None:
    s = FlashLoanScaffold(target="0xTarget", rpc="http://localhost:8545")
    code = s.render()
    assert "0xTarget" in code
    assert "http://localhost:8545" in code
    assert "flashLoanSimple" in code
    assert "executeOperation" in code


def test_flashloan_scaffold_custom() -> None:
    s = FlashLoanScaffold(
        target="0xA",
        rpc="http://rpc",
        asset="0xB",
        amount="999 ether",
        pool="0xC",
    )
    code = s.render()
    assert "0xB" in code
    assert "999 ether" in code
    assert "0xC" in code
