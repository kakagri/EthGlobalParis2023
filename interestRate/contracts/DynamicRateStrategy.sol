// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import {IERC20} from '@aave-v3/contracts/dependencies/openzeppelin/contracts/IERC20.sol';
import {WadRayMath} from '@aave-v3/contracts/protocol/libraries/math/WadRayMath.sol';
import {PercentageMath} from '@aave-v3/contracts/protocol/libraries/math/PercentageMath.sol';
import {DataTypes} from '@aave-v3/contracts/protocol/libraries/types/DataTypes.sol';
import {Errors} from '@aave-v3/contracts/protocol/libraries/helpers/Errors.sol';
import {IDefaultInterestRateStrategy} from '@aave-v3/contracts/interfaces/IDefaultInterestRateStrategy.sol';
import {IReserveInterestRateStrategy} from '@aave-v3/contracts/interfaces/IReserveInterestRateStrategy.sol';
import {IPoolAddressesProvider} from '@aave-v3/contracts/interfaces/IPoolAddressesProvider.sol';
import { IDynamicRateStrategy } from '../interfaces/IDynamicRateStrategy.sol';

/**
 * @title DynamicRateStrategy
 * @author Khaled G. 
 * @notice Defines the interface of the DynamicRateStrategy, it's an extension of the DefaultReserveInterestRateStrategy, 
 * adding a few parameters that are used to update the variable rate slope 1 and some authorization for the keeper.
 */
contract DynamicRateStrategy is IDynamicRateStrategy {
  using WadRayMath for uint256;
  using PercentageMath for uint256;

  /// @inheritdoc IDynamicRateStrategy
  mapping(address => bool) public wards;

  /// @inheritdoc IDynamicRateStrategy
  uint256 public immutable EPSILON;

  /// @inheritdoc IDefaultInterestRateStrategy
  uint256 public immutable OPTIMAL_USAGE_RATIO;

  /// @inheritdoc IDefaultInterestRateStrategy
  uint256 public immutable OPTIMAL_STABLE_TO_TOTAL_DEBT_RATIO;

  /// @inheritdoc IDefaultInterestRateStrategy
  uint256 public immutable MAX_EXCESS_USAGE_RATIO;

  /// @inheritdoc IDefaultInterestRateStrategy
  uint256 public immutable MAX_EXCESS_STABLE_TO_TOTAL_DEBT_RATIO;

  IPoolAddressesProvider public immutable ADDRESSES_PROVIDER;

  /// Multiplier when average utilization in the sweet spot, this is expressed in percentage factor
  uint256 internal _mPlus;

  /// Multiplier when average utilization is not in the sweet spot, this is exepressed in percentage factor
  uint256 internal _mMinus;

  /// Variable rate updater address 
  address internal _variableRateUpdater;

  // Base variable borrow rate when usage rate = 0. Expressed in ray
  uint256 internal immutable _baseVariableBorrowRate;

  // Slope of the variable interest curve when usage ratio > 0 and <= OPTIMAL_USAGE_RATIO. Expressed in ray
  uint256 internal _variableRateSlope1;

  // Slope of the variable interest curve when usage ratio > OPTIMAL_USAGE_RATIO. Expressed in ray
  uint256 internal immutable _variableRateSlope2;

  // Slope of the stable interest curve when usage ratio > 0 and <= OPTIMAL_USAGE_RATIO. Expressed in ray
  uint256 internal immutable _stableRateSlope1;

  // Slope of the stable interest curve when usage ratio > OPTIMAL_USAGE_RATIO. Expressed in ray
  uint256 internal immutable _stableRateSlope2;

  // Premium on top of `_variableRateSlope1` for base stable borrowing rate
  uint256 internal immutable _baseStableRateOffset;

  // Additional premium applied to stable rate when stable debt surpass `OPTIMAL_STABLE_TO_TOTAL_DEBT_RATIO`
  uint256 internal immutable _stableRateExcessOffset;


  
  modifier auth {
    require(wards[msg.sender], "DRS/not-authorized");
    _;
  }

  /**
   * @dev Only pool configurator can call functions marked by this modifier.
   */
  modifier onlyPoolConfigurator() {
    _onlyPoolConfigurator();
    _;
  }

  /**
   * @dev Constructor.
   * @param provider The address of the PoolAddressesProvider contract
   * @param optimalUsageRatio The optimal usage ratio
   * @param baseVariableBorrowRate The base variable borrow rate
   * @param variableRateSlope1 The variable rate slope below optimal usage ratio
   * @param variableRateSlope2 The variable rate slope above optimal usage ratio
   * @param stableRateSlope1 The stable rate slope below optimal usage ratio
   * @param stableRateSlope2 The stable rate slope above optimal usage ratio
   * @param baseStableRateOffset The premium on top of variable rate for base stable borrowing rate
   * @param stableRateExcessOffset The premium on top of stable rate when there stable debt surpass the threshold
   * @param optimalStableToTotalDebtRatio The optimal stable debt to total debt ratio of the reserve
   */
  constructor(
    IPoolAddressesProvider provider,
    uint256 optimalUsageRatio,
    uint256 baseVariableBorrowRate,
    uint256 variableRateSlope1,
    uint256 variableRateSlope2,
    uint256 stableRateSlope1,
    uint256 stableRateSlope2,
    uint256 baseStableRateOffset,
    uint256 stableRateExcessOffset,
    uint256 optimalStableToTotalDebtRatio,
    uint256 epsilon
  ) {
    require(WadRayMath.RAY >= optimalUsageRatio, Errors.INVALID_OPTIMAL_USAGE_RATIO);
    require(
      WadRayMath.RAY >= optimalStableToTotalDebtRatio,
      Errors.INVALID_OPTIMAL_STABLE_TO_TOTAL_DEBT_RATIO
    );
    OPTIMAL_USAGE_RATIO = optimalUsageRatio;
    MAX_EXCESS_USAGE_RATIO = WadRayMath.RAY - optimalUsageRatio;
    OPTIMAL_STABLE_TO_TOTAL_DEBT_RATIO = optimalStableToTotalDebtRatio;
    MAX_EXCESS_STABLE_TO_TOTAL_DEBT_RATIO = WadRayMath.RAY - optimalStableToTotalDebtRatio;
    ADDRESSES_PROVIDER = provider;
    _baseVariableBorrowRate = baseVariableBorrowRate;
    _variableRateSlope1 = variableRateSlope1;
    _variableRateSlope2 = variableRateSlope2;
    _stableRateSlope1 = stableRateSlope1;
    _stableRateSlope2 = stableRateSlope2;
    _baseStableRateOffset = baseStableRateOffset;
    _stableRateExcessOffset = stableRateExcessOffset;
    EPSILON = epsilon;
    wards[msg.sender] = true;
    _variableRateUpdater = msg.sender;
  }

  /// @inheritdoc IDynamicRateStrategy
  function getMPlus() external view returns (uint256) {
    return _mPlus;
  }

  /// @inheritdoc IDynamicRateStrategy
  function getMMinus() external view returns (uint256) {
    return _mMinus;
  }

  /// @inheritdoc IDynamicRateStrategy
  function getVariableRateUpdater() external view returns (address) {
    return _variableRateUpdater;
  }

  /// @inheritdoc IDynamicRateStrategy
  function setVariableRateUpdater(address variableRateUpdater) external onlyPoolConfigurator {
    wards[_variableRateUpdater] = false;
    wards[variableRateUpdater] = true;
    _variableRateUpdater = variableRateUpdater;
  }

  /// @inheritdoc IDynamicRateStrategy
  function setVariableRateSlope1(
    uint256 variableRateSlope1
  ) external auth {
    _variableRateSlope1 = variableRateSlope1;
  }

  /// @inheritdoc IDynamicRateStrategy
  function setMPlus(
    uint256 mPlus
  ) external onlyPoolConfigurator {
    require(mPlus > PercentageMath.PERCENTAGE_FACTOR, "DRS/mPlus");
    _mPlus = mPlus;
  }

  /// @inheritdoc IDynamicRateStrategy
  function setMMinus(
    uint256 mMinus
  ) external onlyPoolConfigurator {
    require(mMinus < PercentageMath.PERCENTAGE_FACTOR, "DRS/mMinus");
    _mMinus = mMinus;
  }

  /// @inheritdoc IDefaultInterestRateStrategy
  function getVariableRateSlope1() external view returns (uint256) {
    return _variableRateSlope1;
  }

  /// @inheritdoc IDefaultInterestRateStrategy
  function getVariableRateSlope2() external view returns (uint256) {
    return _variableRateSlope2;
  }

  /// @inheritdoc IDefaultInterestRateStrategy
  function getStableRateSlope1() external view returns (uint256) {
    return _stableRateSlope1;
  }

  /// @inheritdoc IDefaultInterestRateStrategy
  function getStableRateSlope2() external view returns (uint256) {
    return _stableRateSlope2;
  }

  /// @inheritdoc IDefaultInterestRateStrategy
  function getStableRateExcessOffset() external view returns (uint256) {
    return _stableRateExcessOffset;
  }

  /// @inheritdoc IDefaultInterestRateStrategy
  function getBaseStableBorrowRate() public view returns (uint256) {
    return _variableRateSlope1 + _baseStableRateOffset;
  }

  /// @inheritdoc IDefaultInterestRateStrategy
  function getBaseVariableBorrowRate() external view override returns (uint256) {
    return _baseVariableBorrowRate;
  }

  /// @inheritdoc IDefaultInterestRateStrategy
  function getMaxVariableBorrowRate() external view override returns (uint256) {
    return _baseVariableBorrowRate + _variableRateSlope1 + _variableRateSlope2;
  }

  struct CalcInterestRatesLocalVars {
    uint256 availableLiquidity;
    uint256 totalDebt;
    uint256 currentVariableBorrowRate;
    uint256 currentStableBorrowRate;
    uint256 currentLiquidityRate;
    uint256 borrowUsageRatio;
    uint256 supplyUsageRatio;
    uint256 stableToTotalDebtRatio;
    uint256 availableLiquidityPlusDebt;
  }

  /// @inheritdoc IReserveInterestRateStrategy
  function calculateInterestRates(
    DataTypes.CalculateInterestRatesParams memory params
  ) public view override returns (uint256, uint256, uint256) {
    CalcInterestRatesLocalVars memory vars;

    vars.totalDebt = params.totalStableDebt + params.totalVariableDebt;

    vars.currentLiquidityRate = 0;
    vars.currentVariableBorrowRate = _baseVariableBorrowRate;
    vars.currentStableBorrowRate = getBaseStableBorrowRate();

    if (vars.totalDebt != 0) {
      vars.stableToTotalDebtRatio = params.totalStableDebt.rayDiv(vars.totalDebt);
      vars.availableLiquidity =
        IERC20(params.reserve).balanceOf(params.aToken) +
        params.liquidityAdded -
        params.liquidityTaken;

      vars.availableLiquidityPlusDebt = vars.availableLiquidity + vars.totalDebt;
      vars.borrowUsageRatio = vars.totalDebt.rayDiv(vars.availableLiquidityPlusDebt);
      vars.supplyUsageRatio = vars.totalDebt.rayDiv(
        vars.availableLiquidityPlusDebt + params.unbacked
      );
    }

    if (vars.borrowUsageRatio > OPTIMAL_USAGE_RATIO) {
      uint256 excessBorrowUsageRatio = (vars.borrowUsageRatio - OPTIMAL_USAGE_RATIO).rayDiv(
        MAX_EXCESS_USAGE_RATIO
      );

      vars.currentStableBorrowRate +=
        _stableRateSlope1 +
        _stableRateSlope2.rayMul(excessBorrowUsageRatio);

      vars.currentVariableBorrowRate +=
        _variableRateSlope1 +
        _variableRateSlope2.rayMul(excessBorrowUsageRatio);
    } else {
      vars.currentStableBorrowRate += _stableRateSlope1.rayMul(vars.borrowUsageRatio).rayDiv(
        OPTIMAL_USAGE_RATIO
      );

      vars.currentVariableBorrowRate += _variableRateSlope1.rayMul(vars.borrowUsageRatio).rayDiv(
        OPTIMAL_USAGE_RATIO
      );
    }

    if (vars.stableToTotalDebtRatio > OPTIMAL_STABLE_TO_TOTAL_DEBT_RATIO) {
      uint256 excessStableDebtRatio = (vars.stableToTotalDebtRatio -
        OPTIMAL_STABLE_TO_TOTAL_DEBT_RATIO).rayDiv(MAX_EXCESS_STABLE_TO_TOTAL_DEBT_RATIO);
      vars.currentStableBorrowRate += _stableRateExcessOffset.rayMul(excessStableDebtRatio);
    }

    vars.currentLiquidityRate = _getOverallBorrowRate(
      params.totalStableDebt,
      params.totalVariableDebt,
      vars.currentVariableBorrowRate,
      params.averageStableBorrowRate
    ).rayMul(vars.supplyUsageRatio).percentMul(
        PercentageMath.PERCENTAGE_FACTOR - params.reserveFactor
      );

    return (
      vars.currentLiquidityRate,
      vars.currentStableBorrowRate,
      vars.currentVariableBorrowRate
    );
  }

  /**
   * @dev Calculates the overall borrow rate as the weighted average between the total variable debt and total stable
   * debt
   * @param totalStableDebt The total borrowed from the reserve at a stable rate
   * @param totalVariableDebt The total borrowed from the reserve at a variable rate
   * @param currentVariableBorrowRate The current variable borrow rate of the reserve
   * @param currentAverageStableBorrowRate The current weighted average of all the stable rate loans
   * @return The weighted averaged borrow rate
   */
  function _getOverallBorrowRate(
    uint256 totalStableDebt,
    uint256 totalVariableDebt,
    uint256 currentVariableBorrowRate,
    uint256 currentAverageStableBorrowRate
  ) internal pure returns (uint256) {
    uint256 totalDebt = totalStableDebt + totalVariableDebt;

    if (totalDebt == 0) return 0;

    uint256 weightedVariableRate = totalVariableDebt.wadToRay().rayMul(currentVariableBorrowRate);

    uint256 weightedStableRate = totalStableDebt.wadToRay().rayMul(currentAverageStableBorrowRate);

    uint256 overallBorrowRate = (weightedVariableRate + weightedStableRate).rayDiv(
      totalDebt.wadToRay()
    );

    return overallBorrowRate;
  }

  function _onlyPoolConfigurator() internal view virtual {
    require(
      ADDRESSES_PROVIDER.getPoolConfigurator() == msg.sender,
      Errors.CALLER_NOT_POOL_CONFIGURATOR
    );
  }
}
