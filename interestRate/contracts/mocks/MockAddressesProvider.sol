// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;


contract MockAddressesProvider {
    address public POOL;
    address public POOL_CONFIGURATOR;

    constructor() {
    }

    function setPool(address _pool) external {
        POOL = _pool;
    }

    function setPoolConfigurator(address _poolConfigurator) external {
        POOL_CONFIGURATOR = _poolConfigurator;
    }

    function getPool() external view returns (address) {
        return POOL;
    }

    function getPoolConfigurator() external view returns (address) {
        return POOL_CONFIGURATOR;
    }
}