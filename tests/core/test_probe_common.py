"""Pins the canonical selector table used to override 4byte junk names."""

import re

from ruin.core.probe import COMMON_SELECTORS

_VERIFIED = {
    "0xac9650d8": "multicall(bytes[])",
    "0x6a761202": (
        "execTransaction(address,uint256,bytes,uint8,uint256,uint256,"
        "uint256,address,address,bytes)"
    ),
    "0x715018a6": "renounceOwnership()",
    "0x78e890ba": "domainSeparatorV4()",
    "0xc4d252f5": "cancel(bytes32)",
    "0x38ed1739": (
        "swapExactTokensForTokens(uint256,uint256,address[],address,uint256)"
    ),
}


def test_common_selectors_shape() -> None:
    for selector in COMMON_SELECTORS:
        assert re.fullmatch(r"0x[0-9a-f]{8}", selector)


def test_verified_entries_match_4byte_exactly() -> None:
    for selector, signature in _VERIFIED.items():
        assert COMMON_SELECTORS[selector] == signature


_STALE_LOCK_BYTECODE = "0x608060" + "639343d9e114" + "63a9059cbb14"


def test_stale_lock_selectors_match_known_signatures() -> None:
    from ruin.core.probe import STALE_LOCK_SELECTORS, stale_lock_present

    assert "0x9343d9e1" in STALE_LOCK_SELECTORS  # cooldownShares(uint256)
    assert "0xf2888dbb" in STALE_LOCK_SELECTORS  # unstake(address)
    assert stale_lock_present(_STALE_LOCK_BYTECODE)


def test_stale_lock_absent_in_plain_erc20_dispatch() -> None:
    from ruin.core.probe import stale_lock_present

    assert not stale_lock_present("0x608060" + "63a9059cbb14")
