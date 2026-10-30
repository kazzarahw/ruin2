// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Script.sol";
import "../src/Vault.sol";

contract DrainScript is Script {
    function run() external {
        Vault vault = Vault(vm.envAddress("VAULT"));
        vm.startBroadcast();
        vault.withdraw(1000);
        vm.stopBroadcast();
    }
}
