"""Flash-loan test scaffold for ``ruin``."""

from __future__ import annotations

from dataclasses import dataclass

from ruin.core.oracle import SLUG_ALIASES

DEFAULT_FLASHLOAN_AMOUNT = "10000 ether"

FLASHLOAN_TEST_TEMPLATE = """\
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import {{Test}} from "forge-std/Test.sol";
import {{IPool}} from "forge-std/interfaces/IPool.sol";

/// @notice Flash-loan attack scaffold (Aave V3).
{chain_comment}
{chain_note}
contract FlashLoanTest is Test {{
    IPool constant POOL = IPool({pool});
    address constant TARGET = {target};
    address constant ASSET = {asset};
    uint256 constant AMOUNT = {amount};

    function test_flash_loan_attack() external {{
        vm.createSelectFork("{rpc}");
        POOL.flashLoanSimple(
            address(this),
            ASSET,
            AMOUNT,
            abi.encode(TARGET),
            0
        );
    }}

    function executeOperation(
        address asset,
        uint256 amount,
        uint256 premium,
        address initiator,
        bytes calldata params
    ) external override returns (bool) {{
        // TODO: decode params, perform exploit on TARGET
        // TODO: assert drain
        uint256 totalOwed = amount + premium;
        IERC20(asset).approve(address(POOL), totalOwed);
        return true;
    }}
}}
"""


_POOL_SHARED = "0x794a61358D6845594F94dc1DB02A252b5b4814aD"

FLASHLOAN_DEFAULTS: dict[str, tuple[str, str]] = {
    "ethereum": (
        "0x87870Bca3F3fD6335C3F4Ce8392D69350B4fA4E2",
        "0x98C23e9d8f34fEFb1b7Bd6A91B7fF122F4e16F5C",
    ),
    "arbitrum": (_POOL_SHARED, "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1"),
    "optimism": (_POOL_SHARED, "0x4200000000000000000000000000000000000006"),
    "polygon": (_POOL_SHARED, "0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619"),
    "base": (
        "0xA238Dd80C259a72e81d7e4664a9801593F98d1c5",
        "0x4200000000000000000000000000000000000006",
    ),
}


def flashloan_defaults(chain: str) -> tuple[str, str, bool]:
    """Return (pool, asset, known) for a chain's Aave V3 flash-loan defaults.

    Unknown chains fall back to mainnet with ``known`` False so the scaffold
    can warn instead of silently borrowing mainnet tokens.
    """
    needle = chain.strip().lower()
    needle = SLUG_ALIASES.get(needle, needle)
    pair = FLASHLOAN_DEFAULTS.get(needle)
    if pair is not None:
        return (pair[0], pair[1], True)
    mainnet = FLASHLOAN_DEFAULTS["ethereum"]
    return (mainnet[0], mainnet[1], False)


@dataclass
class FlashLoanScaffold:
    """Parameters for generating a flash-loan forge test."""

    target: str
    rpc: str
    asset: str = "0x98C23e9d8f34fEFb1b7Bd6A91B7fF122F4e16F5C"
    amount: str = DEFAULT_FLASHLOAN_AMOUNT
    pool: str = "0x87870Bca3F3fD6335C3F4Ce8392D69350B4fA4E2"
    chain: str = "ethereum"
    chain_known: bool = True

    def render(self) -> str:
        """Render the forge test source."""
        note = (
            ""
            if self.chain_known
            else (
                f"// WARNING: mainnet Aave defaults used for unknown chain "
                f"'{self.chain}'; pass --pool/--asset"
            )
        )
        return FLASHLOAN_TEST_TEMPLATE.format(
            pool=self.pool,
            target=self.target,
            asset=self.asset,
            amount=self.amount,
            rpc=self.rpc,
            chain_comment=f"// chain: {self.chain}",
            chain_note=note,
        )
