from brownie import network, accounts, Contract
from dataclasses import dataclass

from brownie import (
    MockAddressesProvider,
    MockPool,
    DynamicRateStrategy
)

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

def main():
    deployer = accounts[0]

    deployed = deploy_mocks(deployer)
    pool = deployed["Pool"]
    addresses_provider = deployed["AddressesProvider"]
    print(f"Pool address: {pool.address}, Addresses provider address: {addresses_provider.address}")
    print(f"AddressesProvider.getPool(): {addresses_provider.getPool()}")

