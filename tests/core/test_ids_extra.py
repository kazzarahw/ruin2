"""Extra id tests."""

import pytest

from ruin.core.enums import Chain
from ruin.core.ids import validate_address


def test_validate_address() -> None:
    assert validate_address(Chain.EVM, "0x" + "1" * 40) == "0x" + "1" * 40
    assert validate_address(Chain.SOLANA, "1" * 32) == "1" * 32
    assert validate_address(Chain.MOVE, "0x" + "1" * 64) == "0x" + "1" * 64
    assert validate_address(Chain.CAIRO, "0x1") == "0x1"
    assert validate_address(Chain.COSMWASM, "cosmos1qqqqqq") == "cosmos1qqqqqq"
    with pytest.raises(ValueError, match=r".*"):
        validate_address(Chain.EVM, "bad")
