"""Tests for template-family fingerprinting."""

from ruin.core.templates import template_family

_ALGEBRA = "0x60806040632c8958f614633dd657c514630f35bcac1463a9059cbb14"
_NEAR_MISS = "0x60806040632c8958f614633dd657c514"
_GEARBOX = "0x608060406304dbf0ce14630d326b18146320fe8d5814"


def test_template_family_matches_full_marker_set() -> None:
    assert template_family(_ALGEBRA) == "algebra-npm-vault"
    assert template_family(_GEARBOX) == "gearbox-acl-4626-vault"


def test_template_family_requires_all_markers() -> None:
    assert template_family(_NEAR_MISS) == ""
    assert template_family("0x") == ""


def test_morpho_vault_v2_marker_beats_generic_4626() -> None:
    morpho = (
        "0x608060406321cb4b141463102f7b6c14632acc56f9146301e1d11414"
        "6307a2d13a14630a28a47714"
    )
    assert template_family(morpho) == "morpho-vault-v2"


def test_template_family_names_bitgo_walletsimple() -> None:
    code = "0x608063736c0d5b1463abe3219c1463fc0f392d1463a9059cbb14"
    assert template_family(code) == "bitgo-walletsimple"


def test_template_family_names_bitgo_legacy_variant() -> None:
    code = "0x60806319ab453c14633ef1336714636b9f96ea14"
    assert template_family(code) == "bitgo-walletsimple-legacy"


def test_template_family_names_aave_looper_adapter() -> None:
    code = "0x60806308a0167514631f273c8e14632dd3100014"
    assert template_family(code) == "aave-looper-adapter"


def test_template_family_names_instadapp_registry() -> None:
    code = "0x60806330e9012c14"
    assert template_family(code) == "instadapp-account-registry"


def test_template_family_names_circle_msca_account() -> None:
    code = "0x60806336cf06ff146334fcd5be14"
    assert template_family(code) == "circle-msca-account"


def test_tokenized_strategy_wins_over_generic_erc4626() -> None:
    code = "0x6080630952864e146301e1d114146307a2d13a14630a28a47714"
    assert template_family(code) == "tokenized-strategy"


def test_template_family_names_algebra_lite_variant() -> None:
    code = "0x608063065e536014630f35bcac146316f0115b14"
    assert template_family(code) == "algebra-npm-vault-lite"
