"""Tests for enums."""

import pytest

from ruin.core.enums import (
    CallArg,
    Chain,
    Severity,
    TargetMode,
    VulnClass,
    chain_from_name,
)


def test_vuln_class_other() -> None:
    value = VulnClass.other("foo")
    assert str(value) == 'Other("foo")'
    assert str(VulnClass.OTHER("foo")) == 'Other("foo")'


def test_call_arg_factories() -> None:
    assert CallArg.address("x").kind == "Address"
    assert CallArg.uint(1).kind == "Uint"
    assert CallArg.boolean(True).kind == "Bool"
    assert CallArg.raw_bytes(b"x").kind == "Bytes"
    assert CallArg.bytes(b"x").kind == "Bytes"
    assert CallArg.string("x").kind == "String"


def test_severity_value() -> None:
    assert Severity.HIGH.value == "High"


def test_target_mode_value() -> None:
    assert TargetMode.RESEARCH.value == "Research"


def test_registry_slugs_resolve_to_evm() -> None:
    from ruin.core.chains import EVM_CHAIN_IDS

    for slug in EVM_CHAIN_IDS:
        assert chain_from_name(slug) is Chain.EVM


def test_popular_aliases_still_resolve() -> None:
    assert chain_from_name("matic") is Chain.EVM
    assert chain_from_name("sol") is Chain.SOLANA


def test_unknown_chain_still_raises() -> None:
    with pytest.raises(ValueError, match="unknown chain"):
        chain_from_name("definitely-not-a-chain")
