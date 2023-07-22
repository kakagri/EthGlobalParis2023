from brownie import network, accounts

from brownie import (
    MockAddressesProvider,
    MockPool
)

def deploy_mock_addresses_provider(
    deployer_account = accounts[0]
):
    return MockAddressesProvider.deploy({"from": deployer_account})

def deploy_mock_pool(
    deployer_account = accounts[0]
):
    return MockPool.deploy({"from": deployer_account})


def deploy_mocks(
    deployer_account = accounts[0],
    
):
    addresses_provider = deploy_mock_addresses_provider(deployer_account)
    pool = deploy_mock_pool(deployer_account)

    addresses_provider.setPool(pool.address, {"from": deployer_account})
    addresses_provider.setPoolConfigurator(deployer_account.address, {"from": deployer_account})


