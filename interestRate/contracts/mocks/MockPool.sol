// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;
import { DataTypes } from '@aave-v3/contracts/protocol/libraries/types/DataTypes.sol';


contract MockPool {
    mapping(address => DataTypes.ReserveData) reserves;

    constructor() {

    }

    function setReserveData(
        address asset,
        uint256 configuration,
        uint128 liquidityIndex,
        uint128 currentLiquidityRate,
        uint128 variableBorrowIndex,
        uint128 currentStableBorrowRate,
        uint40 lastUpdateTimestamp
    ) external {
        reserves[asset].configuration = DataTypes.ReserveConfigurationMap({data: configuration});
        reserves[asset].liquidityIndex = liquidityIndex;
        reserves[asset].currentLiquidityRate = currentLiquidityRate;
        reserves[asset].variableBorrowIndex = variableBorrowIndex;
        reserves[asset].currentStableBorrowRate = currentStableBorrowRate;
        reserves[asset].lastUpdateTimestamp = lastUpdateTimestamp;
    }

    function setReserveData2(
        address asset,
        uint16 id,
        address aTokenAddress,
        address stableDebtTokenAddress,
        address variableDebtTokenAddress,
        address interestRateStrategyAddress,
        uint128 accruedToTreasury,
        uint128 unbacked,
        uint128 isolationModeTotalDebt
    ) external {
        reserves[asset].id = id;
        reserves[asset].aTokenAddress = aTokenAddress;
        reserves[asset].stableDebtTokenAddress = stableDebtTokenAddress;
        reserves[asset].variableDebtTokenAddress = variableDebtTokenAddress;
        reserves[asset].interestRateStrategyAddress = interestRateStrategyAddress;
        reserves[asset].accruedToTreasury = accruedToTreasury;
        reserves[asset].unbacked = unbacked;
        reserves[asset].isolationModeTotalDebt = isolationModeTotalDebt;
    }

    function getReserveData(
        address asset
    ) external view returns (DataTypes.ReserveData memory) {
        return reserves[asset];
    }


}