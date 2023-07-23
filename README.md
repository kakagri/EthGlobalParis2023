# Dynamo Rates: a dynamic interest rate strategy for Spark Protocol applied to sDAI using Chainlink Automation

**Author:** Khaled G.

**Description:** This is an implementation  of a dynamic interest rate strategy, an experiment towards reducing the spreads in CDPs, it’s applied to **sDAI** on ****************************Spark Protocol**************************** and uses **Chainlink Automation** to permissionlessly and automatically update the rates.

**********************Motivation:**********************

The overwhelming majority of assets borrowed in CDPs are borrowed at a variable rate today, and in the majority of cases the interest that a borrower pays is solely based on utilization of the liquidity. 

We believe that this is an inefficient system for rate discovery, the low utilisation of the liqudity on most lending platforms shows so. Updating interest rate strategies based on the market is too high a burden on Governance and the mismatch between what borrowers are willing to pay and the rate induced by these utilization based strategies leads to inefficiencies and can be improved upon.

Low utilization means that the interest rate curve is not fine tuned to the current market demand, what the borrowers are willing to pay for. On the other hand low utilization means that the marginal share of the rate that each supplier gets is smaller, there’s a large spread between what the borrowers pay and the suppliers earn.

$$
r_s = U\cdot (1-r_f)\cdot r_b
$$

- $U$ the utilization of the reserve
- $r_s$ the supplier’s rate
- $r_f$ the reserve factor
- $r_b$ the borrowers rate

Let’s forget about the reserve factor for a second, the spread, i.e. the difference between what the borrowers pay and the suppliers earn is then $r_b(1-U)$ meaning the higher the utilization rate the lower this spread which means that for the same borrowing rate suppliers could be earning more ! 

Intuitively **everybody** is better of at 2% borrow rate with 80% utilization than 4% borrow rate with only 30% utilization.

**********************************************************This is purely an experiment, there is a lot to consider beyond what is discussed here when you put a rate discovery mechanism, how it can be gamed, what are the safe guards and so on, what the edge cases are (like if a reserve is frozen and so on and so on).**********************************************************

****************Implementation****************

The contribution consists of two smart contracts: an interest rate strategy for **Spark Protocol** and a ******************Chainlink****************** Upkeep Contract with testing and an example of how to put it in production for **sDAI** on **Spark Protocol**.

- DynamicRateStrategy.sol
    - This is the interest rate strategy, it’s an extension of the DefaultReserveInterestRateStrategy.sol
    - It has a few added parameters namely:
        - VariableRateUpdater [A.K.A the Upkeep Contract]
        - mPlus [ A multiplier for variableRateSlope1 when average utilization is high, which is signaling that the rate is too cheap, mPlus > 1 is expressed in PercentageFactor  ]
        - mMinus [ A multiplier for variableRateSlope1 when average utilization is low, which is signaling that the rate is too expensive, mMinus < 1 is expressed in PercentageFactor  ]
        - Epsilon the window that defines the sweet spot for our rates
    - Can be used in production in **************************************Spark Protocol************************************** with any asset.
- VariableRateUpdater.sol
    - This is an Upkeep Contract, it implements **Chainlink**’s AutomationCompatibleInterface
    - This contract keeps in memory the utilization history of the reserve on **********Spark**********, and computes the average utilization over that period.
    - Here I have hardcoded that Upkeep is ********************Time Based********************, available to be performed every **12 hours**, we keep track of ****60**** of these measurements which corresponds to **************30 days**************.
    - checkUpkeep: computes the average Utilization and the resulting slope change
    - performUpkeep: commits the slope change computed by checkUpkeep and puts the current utilization rate in the memory

************Why use Chainlink Automation instead of natively in the rate strategy ?************

The interface for rate strategies forces the calculateInterestRates to be a ****view**** function, it can’t update the state anytime someone interacts with ************Spark.************ So we need to automate this and the best and most straightforward way to do it is with ******************************************Chainlink Automation.****************************************** 

****************************How to update the rates:****************************

Here we will only be acting on *variableRateSlope1* the reason being that: variableRateSlope2 should not be lowered, it is on purpose high to **strongly** discentivize close to 100% utilization of the reserve. We will adjust *variableRateSlope1* based on the past month’s average utilization of the pool. 

Intuitively if the average utilization is under the optimal utilization it means that the rates are too expensive so we will lower them by reducing the variableRateSlope1. And if the average utilization is close to the optimal utilization ratio up to a governance defined parameter $\epsilon$ it means that we are close to the fair value rate that borrowers are willing to pay and we will marginally increase the rate.

****************************************************************************************************************note: this does create a little instability around the optimalUtilization but choosing mPlus, mMinus and Epsilon conservatively dampens that very effectively. The Epsilon parameter is used so that we can define a “sweet spot” area that comes before variableRateSlope2 kicks which without it would create a lot of instability.****************************************************************************************************************

Let’s denote:

- $\epsilon$ a governance set parameter, that we will use to consider a utilization within range.
- $m_s^-$ and $m_s^+$ governance set parameters that are used to adjust the first slope of the interest rate strategy.
- $U_o$ the optimal utilization rate
- $s_{1,v}$ the variableRateSlope1

Make sure that $m_s^- < 1$ and $m_s^+ > 1$

Every 12 hours:

- Compute the average utilization rate $\bar{U} = \frac{U_t -U_{t-1}\cdots-U_{t-k}}{k}$
- if $\bar{U} < U_o - \epsilon$:
    - $s_{1,v} = s_{1,v}\cdot m_s^-$
- else:
    - $s_{1,v} = s_{1,v} \cdot m_s^+ \cdot (1+ \bar{U}- (U_o -\epsilon))$
    - [ the further you are in the zone the more agressive the rate increase ]
- Replace the oldest utilization rate with the current one

************************************Extensive testing:************************************

- DynamicRateStrategy
    - This is an extension of DefaultReserveInterestRateStrategy.sol from Spark’s code base, we’ve only added some permissions and the variables mentioned above
    - In interestRate/tests/test_dynamicRateStrategy.py we test those new features
- VariableRateUpdater
    - Here we check the base stuff, the getters, the setters, whether the variables are initialized correctly
    - We check that CheckUpkeep works correctly for a given utilizationHistory and by manipulating block.timestamp in eth-brownie, check that the resulting variableRateSlope1 outputed corresponds to the one that is described above in both cases when the average utilization is in the sweet spot and not.
    - Further we check that PerformUpkeep works correctly for a given utilizationHistory, that the variableRateSlope1 is indeed updated according the expected recommendation and the on that’s given by checkUpkeep, again we do this in both cases and also by manipulating the block timestamp.
    - In both tests we make sure that the counter that keeps track of where the oldest utilizationRatio is incremented and that the oldest utilization is indeed replaced with the corresponding one by using MockContracts.

**********Why sDAI ?**********

Currently the **sDAI** reserve on ************Spark************ is frozen after a community decision, however I still take it as the first use case for this DynamicRateStrategy.

The focus on ********sDAI******** is coming from the fact that it is entranched in the Maker ecosystem and a good tool to transfer value.

We fork main net, unfreeze the **sDAI** reserve on **********Spark**********, change the interest rate strategy to our DynamicRateStrategy and deploy a VariableRateUpdater. We make ********sDAI******** collateral but also **********************borrowable**********************, the reason we make ************************sDAI************************ borrowable is twofold: the first, sure if it’s not borrowable it doesn’t make sense to have an interest rate strategy, but second is that **********sDAI********** being borrowable is **good and healthy** for the Maker ecosystem. 

**Depositors can earn extra yield on their sDAI’s yield and operators can hedge their incoming cash flows in a decentralized and permissionless way by borrowing sDAI and exchanging it directly against DAI on Spark.**