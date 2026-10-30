"""Tests for SPL mint honeypot signals."""

from ruin.core.honeypot import (
    evm_verdict,
    is_mint,
    mint_signals,
    tax_gate_flags,
    verdict,
)


def _mint(
    mint_auth: object,
    freeze_auth: object,
    extensions: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    info: dict[str, object] = {
        "mintAuthority": mint_auth,
        "freezeAuthority": freeze_auth,
        "supply": "1000",
    }
    if extensions:
        info["extensions"] = extensions
    return {"data": {"parsed": {"type": "mint", "info": info}}}


def test_renounced_mint_is_clean() -> None:
    raw = _mint(None, None)
    assert is_mint(raw)
    assert mint_signals(raw) == []
    assert verdict([]) == "clean"


def test_active_authorities_grade_medium() -> None:
    raw = _mint("SomeAuth", "SomeAuth")
    signals = mint_signals(raw)
    assert "mint-authority-active" in signals
    assert "freeze-authority-set" in signals
    assert verdict(signals) == "medium"


def test_only_mint_authority_is_low() -> None:
    raw = _mint("SomeAuth", None)
    assert verdict(mint_signals(raw)) == "low"


def test_frozen_default_account_state_is_high() -> None:
    raw = _mint(None, None, [{"extension": "defaultAccountState", "state": "frozen"}])
    signals = mint_signals(raw)
    assert "accounts-start-frozen" in signals
    assert verdict(signals) == "high"


def test_non_transferable_is_high() -> None:
    raw = _mint(None, None, [{"extension": "nonTransferable"}])
    assert verdict(mint_signals(raw)) == "high"


def test_transfer_hook_and_delegate_are_medium() -> None:
    raw = _mint(
        None,
        None,
        [
            {"extension": "transferHook"},
            {"extension": "permanentDelegate", "permanentDelegate": {"address": "X"}},
        ],
    )
    assert verdict(mint_signals(raw)) == "medium"


def test_non_mint_record_has_no_signals() -> None:
    raw: dict[str, object] = {"data": {"parsed": {"type": "account", "info": {}}}}
    assert not is_mint(raw)
    assert mint_signals(raw) == []


def test_evm_verdict_fork_unavailable_is_unknown() -> None:
    assert evm_verdict(["fork-unavailable"], 0.0) == "unknown"


def test_tax_gate_flags_shape() -> None:
    gate = {
        "0x8a8c523c",
        "0x751039fc",
        "0x7d1db4a5",
        "0x8f9a55c0",
        "0x06fdde03",
    }
    assert tax_gate_flags(gate) == ["tax-gate-shape-detected"]
    assert tax_gate_flags({"0x06fdde03", "0x095ea7b3"}) == []
