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
    VariableRateUpdater
)





SPARK_ADDRESSES_PROVIDER = "0x02C3eA4e34C0cBd694D2adFa2c690EECbC1793eE"
SDAI = "0x83F20F44975D03b1b09e64809B757c47f942BEeA"

BIG_SDAI_HOLDER = "0x66B870dDf78c975af5Cd8EDC6De25eca81791DE1"

def main():
    pass