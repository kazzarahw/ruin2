"""Tests for oracle scaffold."""

from ruin.core.oracle import OracleScaffold


def test_oracle_scaffold_render() -> None:
    s = OracleScaffold(target="0xTarget", rpc="http://localhost:8545")
    code = s.render()
    assert "0xTarget" in code
    assert "http://localhost:8545" in code
    assert "test_oracle_manipulation" in code
    assert "getReserves" in code


def test_oracle_scaffold_custom_params() -> None:
    s = OracleScaffold(
        target="0xA",
        rpc="http://rpc",
        reserve_a="0xB",
        reserve_b="0xC",
        oracle="0xD",
        swap_amount="500 ether",
        min_deviation="2 ether",
    )
    code = s.render()
    assert "0xB" in code
    assert "0xC" in code
    assert "0xD" in code
    assert "500 ether" in code
