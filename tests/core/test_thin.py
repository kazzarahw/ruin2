"""Tests for the constant-product depth model behind thin-collateral."""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st

from ruin.core.thin import MAX_DECIMALS, ScreenParams, depth_model

_TEN_PCT_NUM = 11
_TEN_PCT_DEN = 10


def _clears_bar(reserves1: int, q: int) -> bool:
    """True when buying ``q`` lifts the token1 spot price by >= 10%."""
    return _TEN_PCT_DEN * reserves1 * reserves1 >= _TEN_PCT_NUM * (reserves1 - q) ** 2


def _brute_force_depth(reserves0: int, reserves1: int) -> int:
    """Simulate buys unit by unit; first q whose swap lifts price >= 10%."""
    k = reserves0 * reserves1
    price_before = reserves0 / reserves1
    for q in range(1, reserves1 + 1):
        remaining = reserves1 - q
        if remaining <= 0:
            return q
        price_after = k / remaining / remaining
        if price_after >= 1.1 * price_before - 1e-9:
            return q
    return reserves1


@pytest.mark.parametrize(
    ("reserves0", "reserves1"),
    [
        (10**6, 10**5),
        (5 * 10**6, 2 * 10**4),
        (999_983, 34_567),
        (10**6, 1),
    ],
)
def test_depth_model_matches_brute_force_simulation(
    reserves0: int, reserves1: int
) -> None:
    q = depth_model(reserves0, reserves1, 18, 18)
    brute = _brute_force_depth(reserves0, reserves1)
    assert abs(q - brute) <= 1


@pytest.mark.parametrize(
    ("reserves0", "reserves1"),
    [(10**12, 7 * 10**11), (2**100, 2**90), (10**24, 10**23)],
)
def test_depth_model_clears_the_ten_percent_bar_exactly(
    reserves0: int, reserves1: int
) -> None:
    q = depth_model(reserves0, reserves1, 18, 6)
    assert _clears_bar(reserves1, q)


@pytest.mark.parametrize(
    ("reserves0", "reserves1"),
    [(10**12, 7 * 10**11), (2**100, 2**90), (10**24, 10**23)],
)
def test_depth_model_is_minimal(reserves0: int, reserves1: int) -> None:
    q = depth_model(reserves0, reserves1, 18, 6)
    assert q > 0
    assert not _clears_bar(reserves1, q - 1)


def test_depth_model_ignores_decimals_scaling() -> None:
    base = depth_model(10**21, 4 * 10**17, 18, 18)
    for decimals in range(MAX_DECIMALS + 1):
        assert depth_model(10**21, 4 * 10**17, decimals, decimals) == base


def test_zero_token_reserve_needs_no_purchase() -> None:
    assert depth_model(10**18, 0, 18, 18) == 0


def test_single_unit_pool_requires_the_whole_reserve() -> None:
    assert depth_model(10**18, 1, 18, 18) == 1


@pytest.mark.parametrize(("reserves0", "reserves1"), [(-1, 5), (5, -1)])
def test_depth_model_rejects_negative_reserves(reserves0: int, reserves1: int) -> None:
    with pytest.raises(ValueError, match="reserves must be non-negative"):
        depth_model(reserves0, reserves1, 18, 18)


@pytest.mark.parametrize(
    ("decimals0", "decimals1"), [(-1, 18), (18, -1), (37, 18), (18, 37)]
)
def test_depth_model_rejects_out_of_range_decimals(
    decimals0: int, decimals1: int
) -> None:
    with pytest.raises(ValueError, match=r"decimals must be within 0\.\.36"):
        depth_model(10**18, 10**17, decimals0, decimals1)


def test_screen_params_carries_the_operator_knobs() -> None:
    params = ScreenParams(price_usd=1.25, blocks=3000, min_usd=50000.0)
    assert params.price_usd == 1.25
    assert params.blocks == 3000
    assert params.min_usd == 50000.0


@given(
    st.integers(min_value=0, max_value=10**9),
    st.integers(min_value=0, max_value=10**9),
    st.integers(min_value=0, max_value=MAX_DECIMALS),
    st.integers(min_value=0, max_value=MAX_DECIMALS),
)
def test_depth_model_is_always_exact_and_minimal(
    reserves0: int, reserves1: int, decimals0: int, decimals1: int
) -> None:
    q = depth_model(reserves0, reserves1, decimals0, decimals1)
    assert 0 <= q <= reserves1
    assert _clears_bar(reserves1, q)
    if q > 0:
        assert not _clears_bar(reserves1, q - 1)
