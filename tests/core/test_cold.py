"""Tests for cold-target selection scoring."""

from ruin.core.cold import (
    DEFAULT_THRESHOLDS,
    FAME_SCRUTINY_CAP,
    NEW_AGE_WEIGHT,
    NO_AUDIT_WEIGHT,
    UNKNOWN_AGE_DAYS,
    ColdCandidate,
    ColdSignals,
    ColdThresholds,
    cold_score,
    funds_weight,
    rank_cold,
    scrutiny_weight,
    tier_for,
)


def candidate(
    name: str, tvl_usd: int, signals: ColdSignals | None = None
) -> ColdCandidate:
    return ColdCandidate(
        name=name,
        chain="Ethereum",
        tvl_usd=tvl_usd,
        address="0x" + "a" * 40,
        signals=signals or ColdSignals(),
    )


def test_funds_weight_is_zero_below_the_floor() -> None:
    assert funds_weight(49_999) == 0


def test_funds_weight_peaks_in_the_under_radar_band() -> None:
    assert funds_weight(50_000) == 3
    assert funds_weight(4_999_999) == 3


def test_funds_weight_fades_for_battletested_giants() -> None:
    assert funds_weight(5_000_000) == 2
    assert funds_weight(50_000_000) == 1


def test_funds_weight_honors_a_custom_floor() -> None:
    tuned = ColdThresholds(min_tvl_usd=1_000.0)
    assert funds_weight(500, tuned) == 0
    assert funds_weight(1_500, tuned) == 3


def test_scrutiny_weight_is_zero_for_a_live_paid_contest() -> None:
    hot = ColdSignals(live_contest=True)
    assert scrutiny_weight(hot) == 0


def test_scrutiny_weight_is_maximal_for_unverified_unaudited_and_new() -> None:
    cold = ColdSignals(verified=False, audited=False, age_days=10)
    assert scrutiny_weight(cold) == 10


def test_scrutiny_weight_penalizes_verified_audited_and_old() -> None:
    warm = ColdSignals(verified=True, audited=True, age_days=1000)
    assert scrutiny_weight(warm) == 0


def test_unknown_age_scores_neutral() -> None:
    assert scrutiny_weight(ColdSignals(age_days=UNKNOWN_AGE_DAYS)) == 8
    assert scrutiny_weight(ColdSignals(age_days=300)) == 9


def test_cold_score_multiplies_both_axes() -> None:
    cold = candidate("VaultX", 1_000_000, ColdSignals(age_days=10))
    assert cold_score(cold) == 30


def test_cold_score_is_zero_when_either_axis_is_zero() -> None:
    below = candidate("Tiny", 100, ColdSignals())
    hot = candidate("Famous", 1_000_000, ColdSignals(live_contest=True))
    assert cold_score(below) == 0
    assert cold_score(hot) == 0


def test_tier_for_splits_mid_and_high_at_the_mid_bound() -> None:
    assert tier_for(100_000) == "mid"
    assert tier_for(200_000) == "high"
    assert tier_for(10_000) == "below"


def test_rank_cold_prefers_cold_over_battletested() -> None:
    cold = candidate("VaultX", 500_000, ColdSignals(age_days=10))
    warm = candidate(
        "MegaLend", 40_000_000, ColdSignals(verified=True, audited=True, age_days=900)
    )
    assert rank_cold([warm, cold], 10)[0].name == "VaultX"


def test_rank_cold_drops_zero_score_candidates() -> None:
    below = candidate("Tiny", 10_000)
    hot = candidate("Contested", 900_000, ColdSignals(live_contest=True))
    assert rank_cold([below, hot], 10) == []


def test_rank_cold_breaks_score_ties_by_tvl_then_name() -> None:
    small = candidate("alpha", 300_000)
    big = candidate("beta", 900_000)
    equal = candidate("gamma", 900_000)
    ranked = rank_cold([small, equal, big], 10)
    assert [c.name for c in ranked] == ["beta", "gamma", "alpha"]


def test_rank_cold_respects_the_limit() -> None:
    cands = [candidate(f"V{i}", 300_000) for i in range(5)]
    assert len(rank_cold(cands, 2)) == 2


def test_rank_cold_honors_a_custom_floor() -> None:
    tuned = ColdThresholds(min_tvl_usd=25_000.0)
    assert rank_cold([candidate("Small", 30_000)], 10, tuned)
    assert rank_cold([candidate("Small", 30_000)], 10, DEFAULT_THRESHOLDS) == []


def test_unverified_on_unsupported_chain_scores_neutral() -> None:
    blind = ColdSignals(verified=False, chain_supported=False, age_days=10)
    assert scrutiny_weight(blind) == NO_AUDIT_WEIGHT + NEW_AGE_WEIGHT


def test_famous_tvl_caps_scrutiny_absence() -> None:
    giant = ColdSignals(verified=False, audited=False, age_days=10)
    assert scrutiny_weight(giant, 500_000_000.0) == FAME_SCRUTINY_CAP
    assert scrutiny_weight(giant, 5_000_000.0) == 10
