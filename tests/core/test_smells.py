"""Tests for the source smell heuristics."""

from ruin.core.smells import (
    AUTHORITY_UNGUARDED,
    CALLER_EXECUTOR,
    INFLATION_EXPOSED,
    OM_ORACLE_CONSUMER,
    SPOT_PRICE_ORACLE,
    UNPROTECTED_EXEC,
    UNVERIFIED_POOL_CALLBACK,
    WIDE_SHIFT_MATH,
    YUL_DISPATCH,
    source_smells,
)

_VULN_VAULT = """
function convertToShares(uint256 assets) public view returns (uint256) {
    return (assets * totalSupply) / totalAssets();
}
function totalAssets() public view returns (uint256) {
    return asset.balanceOf(address(this));
}
"""

_SAFE_VAULT = """
uint256 private constant OFFERLE = 1000;
function previewDeposit(uint256 assets) public view returns (uint256) {
    return assets * (totalSupply + OFFERLE) / (totalAssets() + assets);
}
function totalAssets() public view returns (uint256) {
    return asset.balanceOf(address(this));
}
"""

_YUL_FILE = """
function dispatch() internal {
    assembly {
        let selector := shr(224, calldataload(0))
        calldatacopy(0, 4, 32)
        switch selector
    }
}
"""

_BUBBLE_FILE = """
function _revert(bytes memory returndata, string memory errorMessage) private pure {
    if (bytes(errorMessage).length > 0) {
        assembly { revert(add(32, returndata), mload(returndata)) }
    } else {
        revert LowLevelCall();
    }
}"""

_SHIFT_FILE = """
function mulWad(uint256 a, uint256 b) internal pure returns (uint256) {
    return (a * b) >> 64;
}
uint256 c = a << 64;
"""

_SAFE_SHIFT_FILE = """
function mulWad(uint256 a, uint256 b) internal pure returns (uint256) {
    return checked_shrl(mul(a, b), 64);
}
uint256 c = a << 64;
"""

_SPOT_FILE = """
function price() external view returns (uint256) {
    (uint112 r0,) = pool.getReserves();
    return r0;
}
"""

_ORACLE_FILE = """
function price() external view returns (uint256) {
    (uint112 r0,) = pool.getReserves();
    return ObservationLibrary.consult(r0);
}
"""

_EXEC_FILE = """
function execute(bytes calldata payload) external {
    (bool ok,) = target.call(payload);
    require(ok);
}
"""

_GUARDED_EXEC_FILE = """
function execute(bytes calldata payload) external onlyOwner {
    require(msg.sender == admin);
    (bool ok,) = target.call(payload);
    require(ok);
}
"""


def test_inflation_flag_on_raw_balance_vault() -> None:
    assert INFLATION_EXPOSED in source_smells(_VULN_VAULT)


def test_inflation_flag_absent_when_hardened() -> None:
    assert INFLATION_EXPOSED not in source_smells(_SAFE_VAULT)


def test_yul_dispatch_flag() -> None:
    assert YUL_DISPATCH in source_smells(_YUL_FILE)
    assert YUL_DISPATCH not in source_smells(_VULN_VAULT)
    assert YUL_DISPATCH not in source_smells(_BUBBLE_FILE)


def test_wide_shift_flag_and_safe_cast_exempt() -> None:
    assert WIDE_SHIFT_MATH in source_smells(_SHIFT_FILE)
    assert WIDE_SHIFT_MATH not in source_smells(_SAFE_SHIFT_FILE)


def test_spot_price_flag_and_oracle_exempt() -> None:
    assert SPOT_PRICE_ORACLE in source_smells(_SPOT_FILE)
    assert SPOT_PRICE_ORACLE not in source_smells(_ORACLE_FILE)


def test_unprotected_exec_flag_and_guard_exempt() -> None:
    assert UNPROTECTED_EXEC in source_smells(_EXEC_FILE)
    assert UNPROTECTED_EXEC not in source_smells(_GUARDED_EXEC_FILE)


_INTERFACE_ONLY = """
interface IERC4626 {
    function convertToShares(uint256 assets) external view returns (uint256 shares);
    function totalAssets() external view returns (uint256 totalManagedAssets);
}
uint256 constant SNAP = 1;
mapping(address => uint256) public balanceOf;
function probe() external view returns (uint256) {
    return balanceOf[address(this)];
}
"""


def test_interface_only_vault_is_not_flagged() -> None:
    assert INFLATION_EXPOSED not in source_smells(_INTERFACE_ONLY)


def test_source_smells_returns_sorted_flags() -> None:
    flags = source_smells(_VULN_VAULT + _YUL_FILE)
    assert flags == sorted(flags)


_VY_VULN = """
@view
@external
def totalAssets() -> uint256:
    return IERC20(self.asset()).balanceOf(self)

@view
@external
def convertToShares(_amount: uint256) -> uint256:
    return _amount * self.totalSupply() // self.totalAssets()
"""


def test_smells_flags_vyper_balance_based_total_assets() -> None:
    assert INFLATION_EXPOSED in source_smells(_VY_VULN)


def test_smells_vyper_hardened_constant_suppresses_flag() -> None:
    hardened = _VY_VULN + "\nVIRTUAL_SHARES: constant(uint256) = 1000\n"
    assert INFLATION_EXPOSED not in source_smells(hardened)


def test_smells_vyper_delegating_vault_is_not_flagged() -> None:
    delegating = """
@view
@external
def totalAssets() -> uint256:
    return self._total_assets()

@view
@external
def convertToShares(_amount: uint256) -> uint256:
    return self._convert_to_shares(_amount)
"""
    assert INFLATION_EXPOSED not in source_smells(delegating)


def test_smells_decimals_offset_counts_as_inflation_hardening() -> None:
    hardened = (
        _VY_VULN + "\nfunction _decimalsOffset() internal view returns (uint256)\n"
    )
    assert INFLATION_EXPOSED not in source_smells(hardened)


def test_smells_bounds_asserted_shift_is_not_flagged() -> None:
    packed = """
    function pack(uint128 a, uint128 b) public pure returns (uint256) {
        assert a < 2**128;
        assert b < 2**128;
        return a | (b << 128);
    }
    """
    assert WIDE_SHIFT_MATH not in source_smells(packed)


def test_smells_modifier_guarded_exec_is_not_flagged() -> None:
    guarded = (
        "function exec(address to, bytes calldata data) external onlyOwner "
        "returns (bytes memory) { (bool ok, bytes memory r) = to.call(data); "
        "require(ok); return r; }"
    )
    assert UNPROTECTED_EXEC not in source_smells(guarded)


def test_smells_signature_array_exec_is_not_flagged() -> None:
    gated = (
        "function execute(bytes32[] calldata sigR, uint8[] calldata sigV, "
        'address dst) external { (bool ok,) = dst.call{value: 1}(""); '
        "require(ok); }"
    )
    assert UNPROTECTED_EXEC not in source_smells(gated)


_RUST_NAIVE = """
fn process_instruction(
    program_id: &Address,
    accounts: &[AccountInfo],
) -> ProgramResult {
    let authority = next_account_info(accounts.iter())?;
    vault.assign(authority)?;
    Ok(())
}
"""

_RUST_GUARDED = """
fn process_instruction(accounts: &[AccountInfo]) -> ProgramResult {
    let authority = next_account_info(accounts.iter())?;
    require_keys_eq!(authority.key, vault.authority);
    Ok(())
}
"""

_RUST_FRAMEWORK = """
use spl_pod::Pod;
fn process_instruction(ctx: Ctx<'info>) -> ProgramResult {
    let authority = ctx.authority.as_ref();
    Ok(())
}
"""


def test_smells_flags_unguarded_rust_authority() -> None:
    assert AUTHORITY_UNGUARDED in source_smells(_RUST_NAIVE)


def test_smells_rust_guarded_authority_not_flagged() -> None:
    assert AUTHORITY_UNGUARDED not in source_smells(_RUST_GUARDED)


def test_smells_rust_framework_typing_suppresses_flag() -> None:
    assert AUTHORITY_UNGUARDED not in source_smells(_RUST_FRAMEWORK)


def test_smells_rust_flag_ignores_solidity_text() -> None:
    sol = (
        "function withdraw(address authority) external "
        "{ payable(authority).transfer(1); }"
    )
    assert AUTHORITY_UNGUARDED not in source_smells(sol)


_SOLVER_POS = """
function solve(uint256 id, address solver, bytes calldata data) public {
    (bool ok, ) = solver.call(data);
    require(ok, "solve failed");
    balances[id] = 0;
}
"""

_SOLVER_GUARDED = """
function solve(uint256 id, address solver, bytes calldata data) public {
    require(allowed[solver], "bad solver");
    (bool ok, ) = solver.call(data);
    require(ok, "solve failed");
}
"""

_CALLBACK_POS = """
function uniswapV3FlashCallback(uint256 fee0, uint256 fee1, bytes calldata) external {
    IERC20(token0).transferFrom(payer, address(this), amount0);
}
"""

_CALLBACK_VERIFIED = """
function uniswapV3FlashCallback(uint256 fee0, uint256 fee1, bytes calldata) external {
    require(
        pool == IUniswapV3Factory(factory).getPool(token0, token1, fee),
        "fake pool",
    );
    IERC20(token0).transferFrom(payer, address(this), amount0);
}
"""

_OM_POS = """
function receiveProposal(uint256 id) external {
    optimisticOracleOptimisticOracleV2.receiveProposal(id);
}
function claim(uint256 id) external {
    payouts[id] = amount;
}
"""


def test_caller_supplied_executor_flagged() -> None:
    assert CALLER_EXECUTOR in source_smells(_SOLVER_POS)


def test_caller_supplied_executor_guarded_clean() -> None:
    assert CALLER_EXECUTOR not in source_smells(_SOLVER_GUARDED)


def test_unverified_pool_callback_flagged() -> None:
    assert UNVERIFIED_POOL_CALLBACK in source_smells(_CALLBACK_POS)


def test_unverified_pool_callback_factory_clean() -> None:
    assert UNVERIFIED_POOL_CALLBACK not in source_smells(_CALLBACK_VERIFIED)


def test_optimistic_oracle_consumer_flagged() -> None:
    assert OM_ORACLE_CONSUMER in source_smells(_OM_POS)
