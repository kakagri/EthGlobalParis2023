// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import { IDefaultInterestRateStrategy } from '@aave-v3/contracts/interfaces/IDefaultInterestRateStrategy.sol';


/**
 * @title IDynamicRateStrategy
 * @author Khaled G. 
 * @notice Defines the interface of the DynamicRateStrategy
 */
interface IDynamicRateStrategy is IDefaultInterestRateStrategy {
    
    /**
     * @notice Returns the VariableRateUpdater in charge of adjusting the variable rate slope 1
     * @return Returns an address
     */
    function getVariableRateUpdater() external view returns (address);

    /**
     * @notice Sets the variable rate updater address
     * @dev Only callable by pool configurator
     * @param variableRateUpdater Variable rate updater address
     */
    function setVariableRateUpdater(address variableRateUpdater) external;

    /**
     * @notice Returns whether an address is a ward, i.e. has permissions
     * @return Returns a boolean
     */
    function wards(address) external view returns (bool);

    /**
     * @notice Returns the epsilon parameter expressed in RAY, a governance set parameter that defines the sweet spot for the rate, this should be << U_optimal
     * @return Returns an integer
     */
    function EPSILON() external view returns (uint256);

    /**
     * @notice Returns the multiplier used when average utilization is too low
     * @return The m- parameter, expressed in percentage
     */
    function getMMinus() external view returns (uint256);

    /**
     * @notice Returns the multiplier used when average utilization is in the sweet spot
     * @return The m+ parameter, expressed in percentage
     */
    function getMPlus() external view returns (uint256);

    /**
     * @notice Updates the variable rate slope below optimal usage ratio
     * @dev Only callable by the keeper contract 
     * @param variableRateSlope1 The variable rate slope
     */
    function setVariableRateSlope1(
        uint256 variableRateSlope1
    ) external;

    /**
     * @notice Updates the mPlus parameter
     * @dev Only callable by pool configurator
     * @param mPlus The mPlus parameter
     */
    function setMPlus(
        uint256 mPlus
    ) external;

    /**
     * @notice Update the mMinus parameter
     * @dev Only callable by pool configurator
     * @param mMinus The mMinus parameter
     */
    function setMMinus(
        uint256 mMinus
    ) external;
}