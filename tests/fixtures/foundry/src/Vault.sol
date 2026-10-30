// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface IERC20 {
    function transfer(address to, uint256 amount) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
}

contract Vault {
    IERC20 public token;

    constructor(address _token) {
        token = IERC20(_token);
    }

    function withdraw(uint256 amount) external {
        token.transfer(msg.sender, amount);
    }
}
