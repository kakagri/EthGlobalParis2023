// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;
import { DataTypes } from '@aave-v3/contracts/protocol/libraries/types/DataTypes.sol';


contract MockPool {
    mapping(address => DataTypes.ReserveData) reserves;

    constructor() {

    }

    function setReserveData(
        address asset,
        DataTypes.ReserveData memory params
    ) external {
        reserves[asset] = params;
    }

    function getReserveData(
        address asset
    ) external view returns (DataTypes.ReserveData memory) {
        return reserves[asset];
    }


}