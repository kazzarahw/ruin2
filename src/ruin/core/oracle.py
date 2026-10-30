"""Oracle manipulation test scaffold for ``ruin``."""

from __future__ import annotations

from dataclasses import dataclass

DEFAULT_SWAP_AMOUNT = "1000000 ether"

ORACLE_TEST_TEMPLATE = """// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import {{Test}} from "forge-std/Test.sol";
import {{IUniswapV2Router02}} from "forge-std/interfaces/IUniswapV2Router02.sol";
import {{IUniswapV2Pair}} from "forge-std/interfaces/IUniswapV2Pair.sol";

/// @notice Oracle manipulation PoC scaffold.
/// Swap on AMM -> read oracle -> check deviation -> assert drain.
{chain_comment}
{chain_note}
contract OracleManipulationTest is Test {{
    IUniswapV2Router02 constant ROUTER =
        IUniswapV2Router02({router});
    address constant TARGET = {target};
    address constant TOKEN_A = {reserve_a};
    address constant TOKEN_B = {reserve_b};
    address constant ORACLE = {oracle};

    function test_oracle_manipulation() external {{
        vm.createSelectFork("{rpc}");

        uint256 priceBefore = _readOracle();
        console2.log("Price before swap:", priceBefore);

        // --- Swap to move the spot price ---
        uint256 swapAmount = {swap_amount};
        _swap(TOKEN_A, TOKEN_B, swapAmount);

        uint256 priceAfter = _readOracle();
        console2.log("Price after swap:", priceAfter);

        // --- Assert oracle deviation ---
        uint256 deviation = priceAfter > priceBefore
            ? priceAfter - priceBefore
            : priceBefore - priceAfter;
        assertGt(deviation, {min_deviation}, "Oracle deviation too small");

        // --- Target reads manipulated price ---
        // TODO: call TARGET function that reads the oracle
        // TODO: assert drain amount
    }}

    function _readOracle() internal view returns (uint256) {{
        // TODO: replace with actual oracle call (e.g. IUniswapV2Pair.getReserves)
        (uint112 r0, uint112 r1, ) = IUniswapV2Pair(ORACLE).getReserves();
        return (uint256(r1) * 1e18) / uint256(r0);
    }}

    function _swap(address from, address to, uint256 amount) internal {{
        // TODO: approve + swapExactTokensForTokens
    }}
}}
"""


UNIVERSAL_ROUTER = "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D"
_WETH_ETHEREUM = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
_USDC_ETHEREUM = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"

AMM_DEFAULTS: dict[str, tuple[str, str]] = {
    "ethereum": (_WETH_ETHEREUM, _USDC_ETHEREUM),
    "base": (
        "0x4200000000000000000000000000000000000006",
        "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
    ),
    "bsc": (
        "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c",
        "0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56",
    ),
    "arbitrum": (
        "0x82aF49447D8a07e3bd95BD0d56f35241523fBab1",
        "0xaf88d065e77c8cC2239327C5EDb3A432268e5831",
    ),
    "polygon": (
        "0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270",
        "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359",
    ),
}


SLUG_ALIASES: dict[str, str] = {
    "mainnet": "ethereum",
    "eth": "ethereum",
    "bnb": "bsc",
    "binance": "bsc",
    "matic": "polygon",
    "arb": "arbitrum",
}


def amm_defaults(chain: str) -> tuple[str, str, str, bool]:
    """Return (router, token_a, token_b, known) for a chain's UniV2 defaults.

    Unknown chains fall back to mainnet pairs with ``known`` False so the
    scaffold can warn instead of silently using mainnet addresses.
    """
    needle = chain.strip().lower()
    needle = SLUG_ALIASES.get(needle, needle)
    pair = AMM_DEFAULTS.get(needle)
    if pair is not None:
        return (UNIVERSAL_ROUTER, pair[0], pair[1], True)
    return (UNIVERSAL_ROUTER, _WETH_ETHEREUM, _USDC_ETHEREUM, False)


@dataclass
class OracleScaffold:
    """Parameters for generating an oracle-manipulation forge test."""

    target: str
    rpc: str
    router: str = "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D"
    reserve_a: str = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
    reserve_b: str = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
    oracle: str = ""
    swap_amount: str = DEFAULT_SWAP_AMOUNT
    min_deviation: str = "1 ether"
    chain: str = "ethereum"
    chain_known: bool = True

    def render(self) -> str:
        """Render the forge test source."""
        oracle_addr = self.oracle or self.reserve_a
        note = (
            ""
            if self.chain_known
            else (
                f"// WARNING: mainnet AMM defaults used for unknown chain "
                f"'{self.chain}'; pass --router/--token-a/--token-b"
            )
        )
        return ORACLE_TEST_TEMPLATE.format(
            router=self.router,
            target=self.target,
            reserve_a=self.reserve_a,
            reserve_b=self.reserve_b,
            oracle=oracle_addr,
            rpc=self.rpc,
            swap_amount=self.swap_amount,
            min_deviation=self.min_deviation,
            chain_comment=f"// chain: {self.chain}",
            chain_note=note,
        )
