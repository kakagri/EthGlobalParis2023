// SPD-License-Identifier: AGPL-3.0
pragma solidity ^0.8.0;

import { AutomationCompatibleInterface } from "@chainlink/interfaces/automation/AutomationCompatibleInterface.sol";

/**
 * @title IDynamicRateStrategy
 * @author Khaled G. 
 * @notice Defines the interface for the UpkeepContract, the contract keeping track of average utilization.
 */

interface IVariableRateUpdater is AutomationCompatibleInterface {
    /**
     * @notice Returns the interval (frequency) at which the upkeep needs to be performed
     * @return Returns the interval, an integer
     */
    function INTERVAL() external view returns (uint);
    /**
     * @notice Returns the number of intervals to be take into account for the average utilization
     * @return Returns the window, an integer
     */
    function WINDOW() external view returns (uint);
    /**
     * @notice Returns the last upkeep timestamp
     * @return Returns an integer
     */
    function lastTimeStamp() external view returns (uint);

    /**
     * @notice Returns the address provider
     * @return Returns an address
     */
    function ADDRESSES_PROVIDER() external view returns (address);

    /**
     * @notice Returns the address 
     * @return Returns an address
     */
    function POOL() external view returns (address);
    
    /**
     * @notice Returns the asset for which this is the rate strategy
     * @return Returns an address
     */
    function ASSET() external view returns (address);

    /**
     * @notice Returns the utilization for a certain index
     * @param index Index in the list
     * @return Returns an address
     */
    function utilizationHistory(uint256 index) external view returns (uint256);

    /**
     * @notice Returns the counter
     * @return Returns the counter, an integer
     */
    function counter() external view returns(uint256);
    
}