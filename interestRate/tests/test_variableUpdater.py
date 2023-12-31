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
    MockAddressesProvider,
    MockPool,
    MockERC20,
    DynamicRateStrategy,
    VariableRateUpdater
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


# Copying current WETH reserve data, can be used for sDAI later on.

CONFIGURATION =379853409927534986586068957228306619304257013817152
LIQUIDITY_INDEX = 1004278376717578583172650619
CURRENT_LIQUIDITY_RATE = 20061017668802092313940498
VARIABLE_BORROW_INDEX = 1008489934007315513484719002
CURRENT_VARIABLE_BORROW_RATE = 38853461709656454968418359
CURRENT_STABLE_BORROW_RATE = 38000000000000000000000000

LAST_UPDATE_TIMESTAMP = int(time.time())
ID = 3
A_TOKEN_ADDRESS = "0x59cD1C87501baa753d0B5B5Ab5D8416A45cD71DB"
STABLE_DEBT_TOKEN_ADDRESS = "0x3c6b93D38ffA15ea995D1BC950d5D0Fa6b22bD05"
VARIABLE_DEBT_TOKEN_ADDRESS = "0x2e7576042566f8D6990e07A1B61Ad1efd86Ae70d"
INTEREST_RATE_STRATEGY_ADDRESS = "0x764b4AB9bCA18eB633d92368F725765Ebb8f047C"
ACCRUED_TO_TREASURY = 642974246913988945
UNBACKED = 0
ISOLATION_MODE_DEBT = 0

# utilization history that's pyramid shaped, the average utilization is 45%

UTILIZATION_HISTORY = [(60-k)*10**25 for k in range(30)] + [(30+k)*10**25 for k in range(30)]
UTILIZATION_HISTORY_2 = [80*10**25]*60

def deploy_mock_addresses_provider(
    deployer_account
):
    return MockAddressesProvider.deploy({"from": deployer_account})

def deploy_mock_pool(
    deployer_account
):
    return MockPool.deploy({"from": deployer_account})

def deploy_mock_erc20(
    deployer_account
):
    return MockERC20.deploy({"from": deployer_account})


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

def deploy_rate_strategy(
    mocks: dict,
    deployer_account
):
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

    dynamic_rate_strategy = deploy_dynamic_rate_strategy(rate_strategy_params, deployer_account)
    return dynamic_rate_strategy

@dataclass
class ReserveDataParams:
    configuration: int
    liquidityIndex: int
    currentLiquidityRate: int
    variableBorrowIndex: int
    currentVariableBorrowRate: int
    currentStableBorrowRate: int
    lastUpdateTimestamp: int
    id: int
    aTokenAddress: str
    stableDebtTokenAddress: str
    variableDebtTokenAddress: str
    interestRateStrategyAddress: str
    accruedToTreasury: int
    unbacked: int
    isolationModeTotalDebt: int



#is_utilization_history_1 -> so we can test both cases, when the average is over and under

@pytest.fixture
def env_dynamic_rate_1():
    deployer_account = accounts[0]

    mocks = deploy_mocks(deployer_account)

    pool = mocks["Pool"]
    addresses_provider = mocks["AddressesProvider"]

    dynamic_rate_strategy = deploy_rate_strategy(
        mocks,
        deployer_account
    )

    token = deploy_mock_erc20(deployer_account)

    a_token = deploy_mock_erc20(deployer_account)
    variable_debt_token = deploy_mock_erc20(deployer_account)
    stable_debt_token = deploy_mock_erc20(deployer_account)

    # set the placeholder variables for the reserve data

    reserve_data_params = ReserveDataParams(
        CONFIGURATION,
        LIQUIDITY_INDEX,
        CURRENT_LIQUIDITY_RATE,
        VARIABLE_BORROW_INDEX,
        CURRENT_VARIABLE_BORROW_RATE,
        CURRENT_STABLE_BORROW_RATE,
        LAST_UPDATE_TIMESTAMP,
        ID,
        a_token.address,
        stable_debt_token.address,
        variable_debt_token.address,
        dynamic_rate_strategy.address,
        ACCRUED_TO_TREASURY,
        UNBACKED,
        ISOLATION_MODE_DEBT
    )

    pool.setReserveData(
        token.address,
        reserve_data_params.configuration,
        reserve_data_params.liquidityIndex,
        reserve_data_params.currentLiquidityRate,
        reserve_data_params.variableBorrowIndex,
        reserve_data_params.currentStableBorrowRate,
        reserve_data_params.lastUpdateTimestamp,
        {"from": deployer_account}
    )
    pool.setReserveData2(
        token.address,
        reserve_data_params.id,
        reserve_data_params.aTokenAddress,
        reserve_data_params.stableDebtTokenAddress,
        reserve_data_params.variableDebtTokenAddress,
        reserve_data_params.interestRateStrategyAddress,
        reserve_data_params.accruedToTreasury,
        reserve_data_params.unbacked,
        reserve_data_params.isolationModeTotalDebt,
        {"from": deployer_account}
    )

    variable_rate_updater = VariableRateUpdater.deploy(
        addresses_provider,
        token,
        UTILIZATION_HISTORY,
        {"from": deployer_account}
    )

    dynamic_rate_strategy.setVariableRateUpdater(
        variable_rate_updater.address,
        {"from": deployer_account}
    )

    return {
        "AddressesProvider": addresses_provider,
        "Pool": pool,
        "DynamicRateStrategy": dynamic_rate_strategy,
        "Token": token,
        "AToken": a_token,
        "VariableDebtToken": variable_debt_token,
        "StableDebtToken": stable_debt_token,
        "VariableRateUpdater": variable_rate_updater
    }


@pytest.fixture
def env_dynamic_rate_2():
    deployer_account = accounts[0]

    mocks = deploy_mocks(deployer_account)

    pool = mocks["Pool"]
    addresses_provider = mocks["AddressesProvider"]

    dynamic_rate_strategy = deploy_rate_strategy(
        mocks,
        deployer_account
    )

    token = deploy_mock_erc20(deployer_account)

    a_token = deploy_mock_erc20(deployer_account)
    variable_debt_token = deploy_mock_erc20(deployer_account)
    stable_debt_token = deploy_mock_erc20(deployer_account)

    # set the placeholder variables for the reserve data

    reserve_data_params = ReserveDataParams(
        CONFIGURATION,
        LIQUIDITY_INDEX,
        CURRENT_LIQUIDITY_RATE,
        VARIABLE_BORROW_INDEX,
        CURRENT_VARIABLE_BORROW_RATE,
        CURRENT_STABLE_BORROW_RATE,
        LAST_UPDATE_TIMESTAMP,
        ID,
        a_token.address,
        stable_debt_token.address,
        variable_debt_token.address,
        dynamic_rate_strategy.address,
        ACCRUED_TO_TREASURY,
        UNBACKED,
        ISOLATION_MODE_DEBT
    )

    pool.setReserveData(
        token.address,
        reserve_data_params.configuration,
        reserve_data_params.liquidityIndex,
        reserve_data_params.currentLiquidityRate,
        reserve_data_params.variableBorrowIndex,
        reserve_data_params.currentStableBorrowRate,
        reserve_data_params.lastUpdateTimestamp,
        {"from": deployer_account}
    )
    pool.setReserveData2(
        token.address,
        reserve_data_params.id,
        reserve_data_params.aTokenAddress,
        reserve_data_params.stableDebtTokenAddress,
        reserve_data_params.variableDebtTokenAddress,
        reserve_data_params.interestRateStrategyAddress,
        reserve_data_params.accruedToTreasury,
        reserve_data_params.unbacked,
        reserve_data_params.isolationModeTotalDebt,
        {"from": deployer_account}
    )

    variable_rate_updater = VariableRateUpdater.deploy(
        addresses_provider,
        token,
        UTILIZATION_HISTORY_2,
        {"from": deployer_account}
    )

    dynamic_rate_strategy.setVariableRateUpdater(
        variable_rate_updater.address,
        {"from": deployer_account}
    )

    return {
        "AddressesProvider": addresses_provider,
        "Pool": pool,
        "DynamicRateStrategy": dynamic_rate_strategy,
        "Token": token,
        "AToken": a_token,
        "VariableDebtToken": variable_debt_token,
        "StableDebtToken": stable_debt_token,
        "VariableRateUpdater": variable_rate_updater
    }



def test_constants(env_dynamic_rate_1):
    deployer_account = accounts[0]
    addresses_provider = env_dynamic_rate_1["AddressesProvider"]
    pool = env_dynamic_rate_1["Pool"]
    dynamic_rate_strategy = env_dynamic_rate_1["DynamicRateStrategy"]
    token = env_dynamic_rate_1["Token"]
    a_token = env_dynamic_rate_1["AToken"]
    variable_debt_token = env_dynamic_rate_1["VariableDebtToken"]
    stable_debt_token = env_dynamic_rate_1["StableDebtToken"]
    variable_rate_updater = env_dynamic_rate_1["VariableRateUpdater"]

    assert variable_rate_updater.INTERVAL() == 12*60*60 # 12 hours expressed in seconds
    assert variable_rate_updater.WINDOW() == 60 # the length on which we look at the utilization rates -> 30 days measured with an upkeep every 12 hours
    assert variable_rate_updater.ADDRESSES_PROVIDER() == addresses_provider.address
    assert variable_rate_updater.POOL() == pool.address
    assert variable_rate_updater.ASSET() == token.address
    assert variable_rate_updater.counter() == 0
    assert dynamic_rate_strategy.getVariableRateUpdater() == variable_rate_updater.address
    assert dynamic_rate_strategy.wards(variable_rate_updater.address)
    for k in range(60):
        assert variable_rate_updater.utilizationHistory(k) == UTILIZATION_HISTORY[k]


def test_mock_erc_manip(
    env_dynamic_rate_1
):
    deployer_account = accounts[0]
    addresses_provider = env_dynamic_rate_1["AddressesProvider"]
    pool = env_dynamic_rate_1["Pool"]
    dynamic_rate_strategy = env_dynamic_rate_1["DynamicRateStrategy"]
    token = env_dynamic_rate_1["Token"]
    a_token = env_dynamic_rate_1["AToken"]
    variable_debt_token = env_dynamic_rate_1["VariableDebtToken"]
    stable_debt_token = env_dynamic_rate_1["StableDebtToken"]
    variable_rate_updater = env_dynamic_rate_1["VariableRateUpdater"]

    token.setTotalSupply(109_030_318, {"from": deployer_account})

    assert token.totalSupply() == 109_030_318

def test_time_manipulation():
    chain_time = chain.time()
    chain.sleep(12_000)
    chain.mine(1)
    new_time = chain.time()
    assert new_time - chain_time == 12_000

def test_check_upkeep_1(env_dynamic_rate_1):
    deployer_account = accounts[0]
    addresses_provider = env_dynamic_rate_1["AddressesProvider"]
    pool = env_dynamic_rate_1["Pool"]
    dynamic_rate_strategy = env_dynamic_rate_1["DynamicRateStrategy"]
    token = env_dynamic_rate_1["Token"]
    a_token = env_dynamic_rate_1["AToken"]
    variable_debt_token = env_dynamic_rate_1["VariableDebtToken"]
    stable_debt_token = env_dynamic_rate_1["StableDebtToken"]
    variable_rate_updater = env_dynamic_rate_1["VariableRateUpdater"]


    upkeep_needed, data = variable_rate_updater.checkUpkeep("", {"from": deployer_account})
    assert not(upkeep_needed)
    chain.sleep(12*60*60 - 2)
    chain.mine(1)
    upkeep_needed, data = variable_rate_updater.checkUpkeep("", {"from": deployer_account})
    assert not(upkeep_needed)
    chain.sleep(3)
    chain.mine(1)
    upkeep_needed, data = variable_rate_updater.checkUpkeep("", {"from": deployer_account})
    assert upkeep_needed

    new_slope = decode(['uint256'], data)[0]

    # The average utilization is 0.45 which is under the lower bound of the sweet spot
    expected_slope = int(dynamic_rate_strategy.getVariableRateSlope1())*int(dynamic_rate_strategy.getMMinus())//10_000
    assert new_slope == expected_slope

def test_check_upkeep_2(env_dynamic_rate_2):
    deployer_account = accounts[0]
    addresses_provider = env_dynamic_rate_2["AddressesProvider"]
    pool = env_dynamic_rate_2["Pool"]
    dynamic_rate_strategy = env_dynamic_rate_2["DynamicRateStrategy"]
    token = env_dynamic_rate_2["Token"]
    a_token = env_dynamic_rate_2["AToken"]
    variable_debt_token = env_dynamic_rate_2["VariableDebtToken"]
    stable_debt_token = env_dynamic_rate_2["StableDebtToken"]
    variable_rate_updater = env_dynamic_rate_2["VariableRateUpdater"]


    upkeep_needed, data = variable_rate_updater.checkUpkeep("", {"from": deployer_account})
    assert not(upkeep_needed)
    chain.sleep(12*60*60 - 2)
    chain.mine(1)
    upkeep_needed, data = variable_rate_updater.checkUpkeep("", {"from": deployer_account})
    assert not(upkeep_needed)
    chain.sleep(3)
    chain.mine(1)
    
    upkeep_needed, data = variable_rate_updater.checkUpkeep("", {"from": deployer_account})
    assert upkeep_needed

    new_slope = decode(['uint256'], data)[0]

    # The average utilization in this scenario is 80% which is close to our optimal utilization and well into the sweet spot, the slope1 should increase by:
    # slope1 = slope1 * mPlus* (1 + avg(Utilization) - (UOptimal - Epsilon)) see the notion page for the formula
    avg_utilization = sum(UTILIZATION_HISTORY_2)//60
    multiple = 10**27 + avg_utilization + EPSILON - OPTIMAL_USAGE_RATIO
    # This is the expected new slope 
    expected_slope = int(dynamic_rate_strategy.getVariableRateSlope1())*int(dynamic_rate_strategy.getMPlus())//10_000*multiple // 10**27
    
    assert new_slope == expected_slope

def test_perform_upkeep(env_dynamic_rate_1):
    deployer_account = accounts[0]
    addresses_provider = env_dynamic_rate_1["AddressesProvider"]
    pool = env_dynamic_rate_1["Pool"]
    dynamic_rate_strategy = env_dynamic_rate_1["DynamicRateStrategy"]
    token = env_dynamic_rate_1["Token"]
    a_token = env_dynamic_rate_1["AToken"]
    variable_debt_token = env_dynamic_rate_1["VariableDebtToken"]
    stable_debt_token = env_dynamic_rate_1["StableDebtToken"]
    variable_rate_updater = env_dynamic_rate_1["VariableRateUpdater"]

    # we're going to manipulate the total supplies of the yield bearing tokens

    # 100 a tokens expressed in ray
    a_token.setTotalSupply(100* 10**27, {"from": deployer_account})

    # 30 variable debt tokens expressed in ray
    variable_debt_token.setTotalSupply(30 * 10**27, {"from": deployer_account})
    
    # 0 stable debt
    stable_debt_token.setTotalSupply(0, {"from": deployer_account})

    # The artificial usage as a result of these fake balances should be 30%


    # move time so upkeep is needed 
    chain.sleep(12*60*61)
    chain.mine(1)

    # This is the slope that we expect, in this scenario the average utilization is under the sweet pot so we are going
    # to reduce the slope of the variable rate slope1 = slope1 * mMinus
    expected_slope = int(dynamic_rate_strategy.getVariableRateSlope1())*int(dynamic_rate_strategy.getMMinus())//10_000
    
    # This is the result from the UpkeepContract, it should return a boolean saying whether an upkeep is needed
    # and the resulting slope1

    upkeep_needed, data = variable_rate_updater.checkUpkeep("", {"from": deployer_account})

    # Since we moved the chain forward an upkeep should be needed
    assert upkeep_needed

    # Get the slope recommended by the upkeep by decoding the bytes
    new_slope_recommended_by_upkeep = decode(['uint256'], data)[0]

    # Perform the Upkeep with the data resulting from checkUpkeep
    variable_rate_updater.performUpkeep(data, {"from": deployer_account})

    # Get the new slope 1 of the dynamicRateStrategy
    dynamic_rate_slope_1 = dynamic_rate_strategy.getVariableRateSlope1()

    # Check that the slop given by checkUpkeep corresponds with what we expect
    assert expected_slope == new_slope_recommended_by_upkeep

    # Check that the UpkeepContract has updated the slope of the dynamicRateStrategy
    assert dynamic_rate_slope_1 == new_slope_recommended_by_upkeep

    # Now we check that the utilization rate of 30% has been cached in the variableRateUpdater A.K.A the UpkeepContract
    # the counter when the Upkeep was performed was 0
    assert variable_rate_updater.utilizationHistory(0) == 30*10**25

    # Check that the counter has been incremented
    assert variable_rate_updater.counter() == 1


def test_perform_upkeep_2(env_dynamic_rate_2):
    deployer_account = accounts[0]
    addresses_provider = env_dynamic_rate_2["AddressesProvider"]
    pool = env_dynamic_rate_2["Pool"]
    dynamic_rate_strategy = env_dynamic_rate_2["DynamicRateStrategy"]
    token = env_dynamic_rate_2["Token"]
    a_token = env_dynamic_rate_2["AToken"]
    variable_debt_token = env_dynamic_rate_2["VariableDebtToken"]
    stable_debt_token = env_dynamic_rate_2["StableDebtToken"]
    variable_rate_updater = env_dynamic_rate_2["VariableRateUpdater"]

    # we're going to manipulate the total supplies of the yield bearing tokens

    # 100 a tokens expressed in ray
    a_token.setTotalSupply(100* 10**27, {"from": deployer_account})

    # 30 variable debt tokens expressed in ray
    variable_debt_token.setTotalSupply(30 * 10**27, {"from": deployer_account})
    
    # 0 stable debt
    stable_debt_token.setTotalSupply(0, {"from": deployer_account})

    # the artificial usage should now be 30%
    # move time so upkeep is needed 
    chain.sleep(12*60*61)
    chain.mine(1)

    avg_utilization = sum(UTILIZATION_HISTORY_2)//60
    multiple = 10**27 + avg_utilization + EPSILON - OPTIMAL_USAGE_RATIO
    expected_slope = int(dynamic_rate_strategy.getVariableRateSlope1())*int(dynamic_rate_strategy.getMPlus())//10_000*multiple // 10**27
    
    upkeep_needed, data = variable_rate_updater.checkUpkeep("", {"from": deployer_account})
    assert upkeep_needed
    new_slope_recommended_by_upkeep = decode(['uint256'], data)[0]
    variable_rate_updater.performUpkeep(data, {"from": deployer_account})

    dynamic_rate_slope_1 = dynamic_rate_strategy.getVariableRateSlope1()
    assert expected_slope == new_slope_recommended_by_upkeep

    assert dynamic_rate_slope_1 == new_slope_recommended_by_upkeep




    



    