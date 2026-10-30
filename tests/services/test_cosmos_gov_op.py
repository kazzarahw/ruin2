"""Tests for the Cosmos governance-capture screen (core + LCD wiring)."""

import pytest

from ruin.core import cosmos as cx
from ruin.services import operations_builders_cosmos as cg_bh
from ruin.services import operations_ext_cosmos as cg

_TARGET = "neutron1tgt"
_UPDATE_ADMIN = {
    "@type": "/cosmwasm.wasm.v1.MsgUpdateAdmin",
    "contract": _TARGET,
    "new_admin": "neutron1attacker",
}
_STORE_CODE = {"@type": "/cosmwasm.wasm.v1.MsgStoreCode"}
_PROPOSAL = {
    "id": "42",
    "status": "3",
    "messages": [_UPDATE_ADMIN],
    "total_deposit": [{"denom": "untrn", "amount": "1000000"}],
    "voting_start_time": "2026-09-22T06:00:00Z",
}
_BALANCES = {
    "balances": [
        {"denom": "untrn", "amount": "5"},
        {"denom": "uatom", "amount": "120"},
    ]
}


class _FakeTransport:
    """Canned LCD document transport (no network)."""

    def __init__(self, docs: dict[str, object]) -> None:
        self.docs = docs

    def get_json(self, url: str) -> object:
        return self.docs[url]


def _wire(monkeypatch: pytest.MonkeyPatch, lcd: str, docs: dict[str, object]) -> None:
    """Install a canned transport that answers every URL in ``docs``."""
    monkeypatch.setattr(cg, "_UNIVERSAL", _FakeTransport(docs))


def _voting_docs(lcd: str) -> dict[str, object]:
    """Canned voting-period proposal list plus the target's balances."""
    return {
        f"{lcd}{cg._PROPOSALS_ROUTE}": {"proposals": [_PROPOSAL]},
        f"{lcd}{cg._BALANCES_ROUTE}{_TARGET}": _BALANCES,
    }


def test_empty_messages_yield_no_flags() -> None:
    assert cx.gov_capture_flags([]) == []


def test_update_admin_flag_carries_contract_address() -> None:
    flags = cx.gov_capture_flags([_UPDATE_ADMIN])
    assert flags == [f"update-admin:{_TARGET}"]


def test_store_and_instantiate_flag_by_type() -> None:
    messages = [_STORE_CODE, {"@type": "/cosmwasm.wasm.v1.MsgInstantiateContract"}]
    assert cx.gov_capture_flags(messages) == ["store-code", "instantiate"]


def test_unknown_and_non_dict_messages_are_ignored() -> None:
    messages: list[object] = [
        {"@type": "/cosmos.bank.v1beta1.MsgSend"},
        "not-a-message",
        7,
    ]
    assert cx.gov_capture_flags(messages) == []


def test_repeated_messages_flag_only_once() -> None:
    flags = cx.gov_capture_flags([_UPDATE_ADMIN, dict(_UPDATE_ADMIN)])
    assert flags == [f"update-admin:{_TARGET}"]


def test_targets_list_names_contract_addresses() -> None:
    messages: list[object] = [_UPDATE_ADMIN, _STORE_CODE]
    assert cx.gov_capture_targets(messages) == [_TARGET]


def test_custody_total_sums_string_amounts() -> None:
    assert cx.custody_total(_BALANCES) == 125


def test_custody_total_zero_on_garbage_document() -> None:
    garbage = {"balances": [{"amount": "abc"}, {"amount": -3}, 42, {"amount": None}]}
    assert cx.custody_total(garbage) == 0
    assert cx.custody_total(None) == 0
    assert cx.custody_total({"balances": "nope"}) == 0


def test_custody_excluding_skips_gov_denom() -> None:
    assert cx.custody_excluding(_BALANCES, "untrn") == 120


def test_proposal_summary_reads_id_deposit_and_flags() -> None:
    summary = cx.proposal_summary(_PROPOSAL)
    assert summary["id"] == "42"
    assert summary["deposit_denom"] == "untrn"
    assert summary["deposit_amount"] == 1000000
    assert summary["messages"] == [f"update-admin:{_TARGET}"]
    assert summary["targets"] == [_TARGET]


def test_proposal_summary_empty_for_non_mapping() -> None:
    assert cx.proposal_summary("junk") == {}


def test_resolve_lcd_returns_registered_endpoint() -> None:
    assert cx.resolve_lcd(" Neutron ") == cx.CHAIN_LCDS["neutron"]


def test_resolve_lcd_rejects_unknown_slug() -> None:
    with pytest.raises(ValueError, match="unknown chain"):
        cx.resolve_lcd("dogecoin")


def test_screen_flags_funded_target_capture_risk(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lcd = "http://lcd.test"
    _wire(monkeypatch, lcd, _voting_docs(lcd))

    report = cg.cosmos_gov_data(lcd)

    row = report.rows[0]
    assert row.proposal == "42"
    assert row.target == _TARGET
    assert row.custody_total == 125
    assert row.non_gov_custody == 120
    assert row.capture_risk is True


def test_screen_skips_text_proposals(monkeypatch: pytest.MonkeyPatch) -> None:
    lcd = "http://lcd.test"
    _wire(
        monkeypatch,
        lcd,
        {f"{lcd}{cg._PROPOSALS_ROUTE}": {"proposals": [{"id": "1", "messages": []}]}},
    )

    assert cg.cosmos_gov_data(lcd).rows == ()


def test_screen_reports_code_only_proposal(monkeypatch: pytest.MonkeyPatch) -> None:
    lcd = "http://lcd.test"
    proposal = {
        "id": "7",
        "messages": [
            _STORE_CODE,
            {"@type": "/cosmwasm.wasm.v1.MsgInstantiateContract"},
        ],
        "total_deposit": [{"denom": "untrn", "amount": "1000000"}],
    }
    _wire(
        monkeypatch,
        lcd,
        {f"{lcd}{cg._PROPOSALS_ROUTE}": {"proposals": [proposal]}},
    )

    rows = cg.cosmos_gov_data(lcd).rows

    assert rows[0].target == ""
    assert rows[0].flags == ("store-code", "instantiate")
    assert rows[0].capture_risk is False


@pytest.mark.parametrize(
    "doc",
    [None, {"proposals": "junk"}, {"proposals": ["junk"]}],
)
def test_screen_tolerates_malformed_gov_docs(
    monkeypatch: pytest.MonkeyPatch, doc: object
) -> None:
    lcd = "http://lcd.test"
    _wire(monkeypatch, lcd, {f"{lcd}{cg._PROPOSALS_ROUTE}": doc})

    assert cg.cosmos_gov_data(lcd).rows == ()


def test_markdown_and_json_wiring(monkeypatch: pytest.MonkeyPatch) -> None:
    lcd = "http://lcd.test"
    _wire(monkeypatch, lcd, _voting_docs(lcd))
    kwargs = {"lcd": lcd, "chain": "neutron"}

    out = cg_bh.COSMOS_OPERATIONS["cosmos-gov"](kwargs)
    payload = cg_bh.COSMOS_BUILDERS["cosmos-gov"](kwargs)

    assert "# Cosmos gov capture" in out
    assert "capture-risk" in out
    assert f"update-admin:{_TARGET}" in out
    assert payload["lcd"] == lcd


def test_markdown_notes_empty_screen(monkeypatch: pytest.MonkeyPatch) -> None:
    lcd = "http://lcd.test"
    _wire(
        monkeypatch,
        lcd,
        {f"{lcd}{cg._PROPOSALS_ROUTE}": {"proposals": []}},
    )

    out = cg_bh.COSMOS_OPERATIONS["cosmos-gov"]({"lcd": lcd, "chain": "neutron"})

    assert "no voting proposals" in out


def test_screen_uses_chain_table_when_lcd_omitted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lcd = cx.CHAIN_LCDS["neutron"]
    _wire(monkeypatch, lcd, _voting_docs(lcd))

    payload = cg_bh.COSMOS_BUILDERS["cosmos-gov"]({"lcd": None, "chain": "neutron"})

    assert payload["lcd"] == lcd


def test_unknown_chain_raises_before_any_fetch(monkeypatch: pytest.MonkeyPatch) -> None:
    _wire(monkeypatch, "http://lcd.test", {})

    with pytest.raises(ValueError, match="unknown chain"):
        cg_bh.COSMOS_OPERATIONS["cosmos-gov"]({"lcd": None, "chain": "dogecoin"})


def test_legacy_exec_wrapping_is_unwrapped() -> None:
    """MsgExecLegacyContent carrying a wasmx batch still flags targets."""
    msg = {
        "@type": "/cosmos.gov.v1.MsgExecLegacyContent",
        "content": {
            "@type": "/injective.wasmx.v1.BatchExecuteContract",
            "msgs": [{"contract_address": "inj1abc"}, {"contract_address": "inj1def"}],
        },
    }
    flags = cx.gov_capture_flags([msg])
    assert "execute:inj1abc" in flags
    assert "execute:inj1def" in flags
    assert cx.gov_capture_targets([msg]) == ["inj1abc", "inj1def"]
