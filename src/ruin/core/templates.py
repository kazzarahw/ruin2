"""Known contract template families identified by marker selector sets."""

from __future__ import annotations

from functools import lru_cache

from ruin.core.probe import extract_selectors

TEMPLATE_FAMILIES: dict[str, frozenset[str]] = {
    "algebra-npm-vault": frozenset(
        {"0x2c8958f6", "0x3dd657c5", "0x0f35bcac"}  # swap/mint callbacks + limitUpper
    ),
    "gearbox-acl-4626-vault": frozenset(
        {"0x04dbf0ce", "0x0d326b18", "0x20fe8d58"}  # asset/share gates
    ),
    "gnosis-safe-v13": frozenset(
        {"0x6a761202", "0x0dccb0dc"}  # execTransaction + addOwnerWithThreshold
    ),
    "morpho-vault-v2": frozenset(
        {
            "0x21cb4b14",  # lostAssets()
            "0x102f7b6c",  # revokePendingCap(bytes32)
            "0x2acc56f9",  # setSupplyQueue(bytes32[])
        }
    ),
    "tokenized-strategy": frozenset(
        {"0x0952864e"}  # profitMaxUnlockTime() (Yearn V3 strategy shape)
    ),
    "erc4626-share-token": frozenset(
        {"0x01e1d114", "0x07a2d13a", "0x0a28a477"}  # totalAssets/convert/preview
    ),
    "algebra-npm-vault-lite": frozenset(
        {"0x065e5360", "0x0f35bcac", "0x16f0115b"}  # currentTick/limitUpper/pool
    ),
    "bitgo-walletsimple": frozenset(
        {"0x736c0d5b", "0xabe3219c", "0xfc0f392d"}  # signers/safeMode/activateSafeMode
    ),
    "bitgo-walletsimple-legacy": frozenset(
        {"0x19ab453c", "0x3ef13367", "0x6b9f96ea"}  # init/flushTokens/flush
    ),
    "aave-looper-adapter": frozenset(
        {"0x08a01675", "0x1f273c8e", "0x2dd31000"}  # AAVE_POOL/SETTLEMENT/FACTORY
    ),
    "instadapp-account-registry": frozenset(
        {"0x30e9012c"}  # implementations(bytes4) dispatcher table
    ),
    "circle-msca-account": frozenset(
        {"0x36cf06ff", "0x34fcd5be"}  # initializeSingleOwnerMSCA + executeBatch
    ),
}


@lru_cache(maxsize=256)
def template_family(code: str) -> str:
    """Name the template family whose markers all appear in the dispatcher.

    Returns an empty string when no family matches fully.
    """
    selectors = set(extract_selectors(code))
    for name, markers in TEMPLATE_FAMILIES.items():
        if markers <= selectors:
            return name
    return ""
