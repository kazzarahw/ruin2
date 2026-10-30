"""Tests for access-control core logic."""

from ruin.core.access_control import AccessMap, FunctionAccess, classify_function


def test_classify_guarded() -> None:
    fn = classify_function("withdraw", "external", ["onlyOwner"], True)
    assert fn.is_guarded
    assert fn.state_changing


def test_classify_unguarded() -> None:
    fn = classify_function("claim", "external", [], True)
    assert not fn.is_guarded
    assert fn.state_changing


def test_classify_view() -> None:
    fn = classify_function("getTotal", "view", [], False)
    assert not fn.state_changing


def test_access_map_render() -> None:
    amap = AccessMap(
        contract="Vault",
        functions=[
            FunctionAccess("withdraw", "external", ["onlyOwner"], True, True),
            FunctionAccess("claim", "external", [], False, True),
        ],
    )
    md = amap.render_markdown()
    assert "withdraw" in md
    assert "claim" in md
    assert "Unguarded" in md
