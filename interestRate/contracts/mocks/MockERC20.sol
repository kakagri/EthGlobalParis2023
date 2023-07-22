// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract MockERC20 {
    uint256 internal _totalSupply;

    function totalSupply() external view returns (uint256) {
        return _totalSupply;
    }

    function setTotalSupply(
        uint256 totalSupply_
    ) external {
        _totalSupply = totalSupply_;
    }
}