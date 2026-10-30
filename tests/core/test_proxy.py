"""Tests for proxy core logic."""

from ruin.core.proxy import (
    EIP1967_ADMIN_SLOT,
    EIP1967_BEACON_SLOT,
    EIP1967_IMPLEMENTATION_SLOT,
    ProxyInfo,
    detect_delegation,
    implementation_from_slot,
    is_zero,
    resolve_proxy,
)


def test_eip1967_slot_constants_match_the_eip() -> None:
    """Pin the EIP-1967 slot constants to the official values."""
    assert EIP1967_IMPLEMENTATION_SLOT == (
        "0x360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc"
    )
    assert EIP1967_ADMIN_SLOT == (
        "0xb53127684a568b3173ae4ea00d355d13724b9923e098f63c5230a8e330732f2c"
    )
    assert EIP1967_BEACON_SLOT == (
        "0xa3f0ad74e5423aebfd80d3ef4346578335a9a72aeaee59ff6cb3582b35133d50"
    )


def test_is_zero_empty() -> None:
    assert is_zero("0x0")
    assert is_zero("0x0000000000000000000000000000000000000000")
    assert is_zero("0x0000000000000000000000000000000000000000000000000000000000000000")


def test_is_zero_nonzero() -> None:
    assert not is_zero("0x0000000000000000000000000000000000000001")
    assert not is_zero("0xabcdef1234567890abcdef1234567890abcdef12")


def test_resolve_proxy_not_proxy() -> None:
    info = resolve_proxy("0x0", "0x0", "0x0")
    assert not info.is_proxy


def test_resolve_proxy_with_impl() -> None:
    impl = (
        "0x0000000000000000000000000000000000000000"
        "000000000000000000000000abcdef1234567890ab"
    )
    admin = (
        "0x0000000000000000000000000000000000000000"
        "0000000000000000000000001234567890abcdef12"
    )
    info = resolve_proxy(impl, admin)
    assert info.is_proxy
    assert info.implementation == "0x0000000000000000000000abcdef1234567890ab"
    assert info.admin == "0x00000000000000000000001234567890abcdef12"
    assert not info.uninitialized_impl


def test_resolve_proxy_uninitialized() -> None:
    zero_impl = "0x0000000000000000000000000000000000000000000000000000000000000000"
    info = resolve_proxy(zero_impl, "0x0")
    assert not info.is_proxy


def test_proxy_info_render() -> None:
    info = ProxyInfo(
        address="0xabc",
        implementation="0xdef",
        admin="0x111",
        is_proxy=True,
    )
    md = info.render_markdown()
    assert "0xdef" in md
    assert "0x111" in md


def test_proxy_info_render_not_proxy() -> None:
    info = ProxyInfo(address="0xabc", is_proxy=False)
    md = info.render_markdown()
    assert "Not a proxy" in md


def test_proxy_info_render_uninitialized() -> None:
    info = ProxyInfo(
        address="0xabc",
        implementation="0x0000000000000000000000000000000000000000",
        is_proxy=True,
        uninitialized_impl=True,
    )
    md = info.render_markdown()
    assert "- **WARNING:** Implementation appears uninitialized." in md


def test_detect_delegation_positive() -> None:
    code = "0xef01001ab62413e0cf2ebeb73da7d40c70e7202ae14467"
    assert detect_delegation(code) == "0x1ab62413e0cf2ebeb73da7d40c70e7202ae14467"


def test_detect_delegation_negatives() -> None:
    assert detect_delegation("0x") == ""
    assert detect_delegation("0xef0100") == ""
    assert detect_delegation("0x6080604052" + "ab" * 20) == ""


def test_render_markdown_shows_delegation() -> None:
    info = ProxyInfo(
        address="0xabc",
        is_proxy=True,
        implementation="0x1ab62413e0cf2ebeb73da7d40c70e7202ae14467",
        delegated_to="0x1ab62413e0cf2ebeb73da7d40c70e7202ae14467",
    )
    text = info.render_markdown()
    assert "EIP-7702 delegation" in text


def test_implementation_from_slot_decodes_trailing_address() -> None:
    raw = "0x0000000000000000000000009c850771b321c6e7aa909413b5cc98c86ccba96f"
    assert implementation_from_slot(raw) == "0x9c850771b321c6e7aa909413b5cc98c86ccba96f"


def test_implementation_from_slot_rejects_empty_and_short() -> None:
    assert implementation_from_slot("0x" + "0" * 64) == ""
    assert implementation_from_slot("0x") == ""
    assert implementation_from_slot("0x1234") == ""
