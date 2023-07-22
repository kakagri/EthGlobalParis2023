import logging
from dataclasses import dataclass
import pytest
import brownie

from brownie import (
    accounts,
    Contract,
    MockAddressesProvider,
    MockPool,
    DynamicRateStrategy
)


'''
The interest rate strategy is the same as the default interest rate strategy on Aave V3 with a couple differences
it has a few additional parameters:
epsilon, mPlus, mMinus
See notion page to refer to what those are. 

The only things that need to be tested are whether for the new variables the setters and getters work properly.
'''

# Copying current WETH interest rate strategy's parameters on Spark Protocol
# See https://etherscan.io/address/0x764b4AB9bCA18eB633d92368F725765Ebb8f047C#readContract

OPTIMAL_USAGE_RATIO = 800000000000000000000000000
BASE_VARIABLE_BORROW_RATE = 10000000000000000000000000
VARIABLE_RATE_SLOPE_1 = 38000000000000000000000000
VARIABLE_RATE_SLOPE_2 = 800000000000000000000000000
STABLE_RATE_SLOPE_1 = 0
STABLE_RATE_SLOPE_2 = 0
BASE_STABLE_RATE_OFFSET =  38000000000000000000000000 - VARIABLE_RATE_SLOPE_1 
STABLE_RATE_EXCESS_OFFSET = 0
OPTIMAL_STABLE_TO_TOTAL_DEBT_RATIO = 0
EPSILON = 1_000_000_000_000_000_000_000_000_00 # 10%
M_PLUS = int(10_000*1.1) # M_PLUS = 1.1
M_MINUS = int(10_000*0.9) # M_MINUS = 0.9



def deploy_mock_addresses_provider(
    deployer_account
):
    return MockAddressesProvider.deploy({"from": deployer_account})

def deploy_mock_pool(
    deployer_account
):
    return MockPool.deploy({"from": deployer_account})

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

def deploy_mocks(
    deployer_account
):
    addresses_provider = deploy_mock_addresses_provider(deployer_account)
    pool = deploy_mock_pool(deployer_account)

    addresses_provider.setPool(pool.address, {"from": deployer_account})
    addresses_provider.setPoolConfigurator(deployer_account.address, {"from": deployer_account})

    return {"Pool": pool, "AddressesProvider": addresses_provider}


@pytest.fixture
def rate_strategy():
    mocks = deploy_mocks(
        accounts[0]
    )
    rate_strategy_params = RateStrategyParameters(
        mocks['AddressesProvider'],
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

    dynamic_rate_strategy = deploy_dynamic_rate_strategy(rate_strategy_params, accounts[0])
    mocks["DynamicRateStrategy"] = dynamic_rate_strategy
    return dynamic_rate_strategy

def test_constants(rate_strategy):
    assert rate_strategy.EPSILON() == EPSILON
    assert rate_strategy.getMPlus() == M_PLUS
    assert rate_strategy.getMMinus() == M_MINUS
    assert rate_strategy.wards(accounts[0].address) == True
    assert rate_strategy.getVariableRateUpdater() == accounts[0].address

def test_changes_and_authorizations(rate_strategy):
    second_account = accounts[1]
    rate_strategy.setMPlus(int(1.23*10_000), {"from": accounts[0]})
    assert rate_strategy.getMPlus() == int(1.23*10_000)
    rate_strategy.setMMinus(int(0.9325*10_000), {"from": accounts[0]})
    assert rate_strategy.getMMinus() == int(0.9325*10_000)
    rate_strategy.setVariableRateSlope1(int(0.5*38000000000000000000000000), {"from": accounts[0]})
    assert rate_strategy.getVariableRateSlope1() == int(0.5*38000000000000000000000000)

    with brownie.reverts('10'): # corresponds to Errors.CALLER_NOT_CONFIGURATOR
        rate_strategy.setMPlus(0, {"from": second_account})
    with brownie.reverts('10'): # corresponds to Errors.CALLER_NOT_CONFIGURATOR
        rate_strategy.setMMinus(0, {"from": second_account})
    with brownie.reverts('DRS/mPlus'):
        rate_strategy.setMPlus(9_999, {"from": accounts[0]})
    with brownie.reverts('DRS/mMinus'):
        rate_strategy.setMMinus(10_001, {"from": accounts[0]})
    with brownie.reverts('DRS/not-authorized'):
        rate_strategy.setVariableRateSlope1(0, {"from": second_account})




