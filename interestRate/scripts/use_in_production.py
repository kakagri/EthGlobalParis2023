import logging
from dataclasses import dataclass
import pytest
import brownie
import time
from eth_abi import decode
from brownie import (
    accounts,
    Contract,
    chain,
    DynamicRateStrategy,
    VariableRateUpdater,
)

SPARK_ADDRESSES_PROVIDER = "0x02C3eA4e34C0cBd694D2adFa2c690EECbC1793eE"
POOL_ADMIN_ADDRESS = "0xBE8E3e3618f7474F8cB1d074A26afFef007E98FB"
SDAI = "0x83F20F44975D03b1b09e64809B757c47f942BEeA"

BIG_SDAI_HOLDER = "0x66B870dDf78c975af5Cd8EDC6De25eca81791DE1"

OPTIMAL_USAGE_RATIO = 800000000000000000000000000
BASE_VARIABLE_BORROW_RATE = 10000000000000000000000000
VARIABLE_RATE_SLOPE_1 = 38000000000000000000000000
VARIABLE_RATE_SLOPE_2 = 800000000000000000000000000
STABLE_RATE_SLOPE_1 = 0
STABLE_RATE_SLOPE_2 = 0
BASE_STABLE_RATE_OFFSET =  38000000000000000000000000 - VARIABLE_RATE_SLOPE_1 
STABLE_RATE_EXCESS_OFFSET = 0
OPTIMAL_STABLE_TO_TOTAL_DEBT_RATIO = 0
EPSILON = 100000000000000000000000000 # 10%
M_PLUS = int(10_000*1.1) # M_PLUS = 1.1
M_MINUS = int(10_000*0.9) # M_MINUS = 0.9

UTILIZATION_HISTORY = [(60-k)*10**25 for k in range(30)] + [(30+k)*10**25 for k in range(30)]

@dataclass
class RateStrategyParameters:
    provider: Contract
    optimalUsageRatio: int
    baseVariableBorrowRate: int
    variableRateSlope1: int
    variableRateSlope2: int
    stableRateSlope1: int
    stableRateSlope2: int
    baseStableRateOffset: int
    stableRateExcessOffset: int
    optimalStableToTotalDebtRatio: int
    epsilon: int # the parameter to 
    mPlus: int
    mMinus: int

def deploy_dynamic_rate_strategy(
    rate_strategy_params: RateStrategyParameters,
    deployer_account
):
    rate_strategy = DynamicRateStrategy.deploy(
        rate_strategy_params.provider,
        rate_strategy_params.optimalUsageRatio,
        rate_strategy_params.baseVariableBorrowRate,
        rate_strategy_params.variableRateSlope1,
        rate_strategy_params.variableRateSlope2,
        rate_strategy_params.stableRateSlope1,
        rate_strategy_params.stableRateSlope2,
        rate_strategy_params.baseStableRateOffset,
        rate_strategy_params.stableRateExcessOffset,
        rate_strategy_params.optimalStableToTotalDebtRatio,
        rate_strategy_params.epsilon,
        {"from": deployer_account}
    )

    # this will work because the deployer is a pool configurator in mock contract
    rate_strategy.setMPlus(rate_strategy_params.mPlus, {"from": deployer_account})
    rate_strategy.setMMinus(rate_strategy_params.mMinus, {"from": deployer_account})
    return rate_strategy

def deploy_rate_strategy(
    addresses_provider,
    deployer_account
):
    rate_strategy_params = RateStrategyParameters(
        addresses_provider,
        OPTIMAL_USAGE_RATIO,
        BASE_VARIABLE_BORROW_RATE,
        VARIABLE_RATE_SLOPE_1,
        VARIABLE_RATE_SLOPE_2,
        STABLE_RATE_SLOPE_1,
        STABLE_RATE_SLOPE_2,
        BASE_STABLE_RATE_OFFSET,
        STABLE_RATE_EXCESS_OFFSET,
        OPTIMAL_STABLE_TO_TOTAL_DEBT_RATIO,
        EPSILON,
        M_PLUS,
        M_MINUS
    )

    dynamic_rate_strategy = deploy_dynamic_rate_strategy(rate_strategy_params, deployer_account)
    return dynamic_rate_strategy




def main():
    deployer_account = accounts[0]
    addresses_provider = Contract.from_explorer(SPARK_ADDRESSES_PROVIDER)
    
    # we get the pool address
    pool_address = addresses_provider.getPool()

    # we get the pool configurator address, this will be useful to unfreeze the sDAI pool
    # and set the interest rate strategy
    pool_configurator_address = addresses_provider.getPoolConfigurator()
    acl_manager_address = addresses_provider.getACLManager()

    # visual checking against the developer docs( https://docs.sparkprotocol.io/developers/deployed-contracts/mainnet-addresses)
    # it checks out !
    print(f"pool address: {pool_address}")
    print(f"pool configurator address: {pool_configurator_address}")

    pool = Contract.from_explorer(pool_address)
    pool_configurator = Contract.from_explorer(pool_configurator_address)
    acl_manager = Contract.from_explorer(acl_manager_address)

    # I found the PoolAdmin address through etherscan: 0xBE8E3e3618f7474F8cB1d074A26afFef007E98FB, you can check that it's the correct one with the acl manager
    is_pool_admin = acl_manager.isPoolAdmin(POOL_ADMIN_ADDRESS)
    assert is_pool_admin
    print(f"{POOL_ADMIN_ADDRESS} is a pool admin: {is_pool_admin}")


    # Impersonating the pool admin
    pool_admin_account = accounts.at(POOL_ADMIN_ADDRESS, force = True)

    # Unfreeze the reserve 
    pool_configurator.setReserveFreeze(SDAI, False, {"from": pool_admin_account})

    # Unpause the reserve
    pool_configurator.setReservePause(SDAI, False, {"from": pool_admin_account})

    # activate the reserve
    pool_configurator.setReserveActive(
        SDAI,
        True,
        {"from": pool_admin_account}
    )

    # for some reason there's a bug with the flashloan premium
    pool_configurator.updateFlashloanPremiumToProtocol(
        5,
        {"from": pool_admin_account}
    )

    print(f"pool flashloan premium: {pool.FLASHLOAN_PREMIUM_TO_PROTOCOL()}")


    # lb is in percentage factor and should be greater than one
    # ltv is in percentage factor 
    # lt is in percentage factor
    lb = int(1.05 * 10_000) # 5% bonus
    ltv = int(0.85 * 10_000) # 85% ltv 
    lt = int(0.9 * 10_000) # 90% ltv
    # lt * lb < 1 there should be no issue with setting this

    pool_configurator.configureReserveAsCollateral(
        SDAI,
        ltv,
        lt,
        lb,
        {"from": pool_admin_account}
    )

    # allow borrowing both variable and stable
    pool_configurator.setReserveStableRateBorrowing(
        SDAI,
        True,
        {"from": pool_admin_account}
    )

    # allow flashloans in SDAI
    pool_configurator.setReserveFlashLoaning(
        SDAI,
        True,
        {"from": pool_admin_account}
    )

    # set the debt ceiling
    pool_configurator.setDebtCeiling(
        SDAI,
        2**255,
        {"from": pool_admin_account}
    )


    # set infinite supply cap so we don't run into issues
    pool_configurator.setSupplyCap(SDAI, 2**255, {"from": pool_admin_account})

    # set infinite borrow cap so we don't run into issues
    pool_configurator.setBorrowCap(SDAI, 2**255 - 1, {"from": pool_admin_account})


    # let's configure the reserve

    time.sleep(1)

    # deploy the dynamic rate strategy
    dynamic_rate_strategy = deploy_rate_strategy(addresses_provider, {"from": deployer_account})

    # deploy the variable rate updater a.k.a the Upkeep Contract
    variable_rate_updater = VariableRateUpdater.deploy(
        addresses_provider,
        SDAI,
        UTILIZATION_HISTORY,
        {"from": deployer_account}
    )

    # allow the keeper to update the variable rate slope
    dynamic_rate_strategy.setVariableRateUpdater(
        variable_rate_updater.address,
        {"from": deployer_account}
    )

    # update the interest rate strategy to be the dynamic one
    pool_configurator.setReserveInterestRateStrategyAddress(
        SDAI,
        dynamic_rate_strategy.address,
        {"from": pool_admin_account}
    )

    # The keeper can start updating the interest rate strategy.