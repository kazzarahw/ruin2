"""Tests for value objects."""

from ruin.core.ids import ContractId
from ruin.core.value_objects import Amount, ExploitCall


def test_amount() -> None:
    amount = Amount(asset=ContractId.new("0x" + "1" * 40), units=5)
    assert amount.units == 5


def test_exploit_call() -> None:
    call = ExploitCall(target=ContractId.new("0x" + "1" * 40), signature="foo()")
    assert call.signature == "foo()"
