// SPD-License-Identifier: AGPL-3.0
pragma solidity ^0.8.0;

import { AutomationCompatibleInterface } from "@chainlink/interfaces/automation/AutomationCompatibleInterface.sol";

interface IVariableRateUpdater is AutomationCompatibleInterface {
    function INTERVAL() external view returns (uint);
    function WINDOW() external view returns (uint);
    function lastTimeStamp() external view returns (uint);

}