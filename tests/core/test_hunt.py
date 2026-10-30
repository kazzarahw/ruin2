"""Tests for the pure hunt filtering helpers."""

from ruin.core.hunt import candidate, rank, render_hunt_markdown

_ERC20_BODY = "63a9059cbb146370a08231146323b872dd1463095ea7b314"


def _code(extra: str = "") -> str:
    return "0x60016001" + _ERC20_BODY + extra


def test_candidate_requires_full_core_and_mint_or_owner() -> None:
    assert candidate("0xA", 1.0, "0x6001600163a9059cbb14") is None
    assert candidate("0xA", 10.0, _code()) is None
    with_owner = candidate("0xA", 10.0, _code("638da5cb5b14"))
    assert with_owner is not None
    assert with_owner.ownered
    with_mint = candidate("0xB", 5.0, _code("6340c10f1914"))
    assert with_mint is not None
    assert with_mint.mintable


def test_rank_prefers_mintable_then_value() -> None:
    a = candidate("0xA", 100.0, _code("638da5cb5b14"))
    b = candidate("0xB", 10.0, _code("6340c10f1914"))
    c = candidate("0xC", 90.0, _code("6340c10f1914"))
    assert a is not None
    assert b is not None
    assert c is not None
    assert [x.address for x in rank([a, b, c], 2)] == ["0xC", "0xB"]


def test_render_hunt_markdown_empty_and_full() -> None:
    empty = render_hunt_markdown("0XT", [], 10)
    assert "(none)" in empty
    a = candidate("0xA", 100.0, _code("638da5cb5b14"))
    assert a is not None
    full = render_hunt_markdown("0XT", [a], 10)
    assert "0xA" in full
    assert "honeypot-evm" in full


def test_candidate_records_template_family() -> None:
    code = (
        "0x6080"
        "63a9059cbb14"  # transfer
        "6306fdde0314"  # name
        "6395d89b4114"  # symbol
        "6318160ddd14"  # totalSupply
        "6370a0823114"  # balanceOf
        "63dd62ed3e14"  # allowance
        "63095ea7b314"  # approve
        "6323b872dd14"  # transferFrom
        "638da5cb5b14"  # owner
        "632c8958f614"  # algebra swap callback
        "633dd657c514"
        "630f35bcac14"
    )
    cand = candidate("0xA", 100.0, code)
    assert cand is not None
    assert cand.family == "algebra-npm-vault"


def test_render_markdown_flags_failed_windows() -> None:
    out = render_hunt_markdown("0XT", [], 10, failed=3, total=5)
    assert "3 of 5 log windows failed" in out
    clean = render_hunt_markdown("0XT", [], 10)
    assert "failed" not in clean
