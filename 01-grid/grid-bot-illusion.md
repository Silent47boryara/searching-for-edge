# 01 — The Grid Bot Illusion

**Status:** `Published`

**Formal write-up:** [Grid Trading in Cryptocurrency Markets: A Critical Evaluation of Classical, Dynamic, and Delta-Neutral Implementations](https://ssrn.com/abstract=7376359) — SSRN working paper, August 2026.

**Research question:** Does grid trading generate an independent trading edge, or does its profitability primarily come from market exposure, execution economics, and market-making infrastructure?

## 1. Why Grid Looks So Attractive

Open any bot marketplace on Binance and the first thing you notice is the storefront. Someone posts +$5,000 in a day on a grid bot, a clean green P&L curve, an ROI percentage that makes you think "why am I not just doing this." The idea sounds almost embarrassingly simple: the bot buys when price drops, sells when it rises, and repeats this inside a range — no direction to predict, no analysis, just mechanics.

This is the same bait as the "copy-paste bot" from this series' introduction: a simple, understandable mechanism sold as a ready-made solution. The difference here is that the mechanism isn't secret or hidden behind a polished interface — it's openly documented by Binance itself. So the question isn't "what's really inside," it's "if the mechanism is open to everyone, why doesn't everyone make the same money from it."

## 2. How a Classical Grid Actually Makes Money

The mechanics of a classical grid are simple: set a price range, lay a ladder of levels inside it, place a buy order at every level below and a sell order at every level above. As price oscillates, the bot buys on dips and sells on bounces, earning the spacing between grid levels on every completed cycle.

This works as long as price stays inside the range. If price drops below the lower bound, the bot is left holding the asset it bought on spot, with no way to sell it into the grid (or, depending on settings, it sells everything at a loss). If price breaks above the upper bound, the grid stops participating in further upside — the whole position has already been sold. Either way, a classical grid depends on price moving sideways, not on market direction.

## 3. The Zero-Expectation Problem

This is where the idea first gets tested for rigor. Chen, Chen, and Jang (2025, NTU), in "Dynamic Grid Trading: From Zero Expectation to Market Outperformance," show that within the random-walk model they consider — price moves up or down by a fixed step k with equal probability (50/50), fees are ignored, and the entire position is liquidated once price breaks below the lower bound — the expected profit of a classical grid is zero before costs.

Importantly, this isn't just a backtest observation: the authors derive this result analytically under the stated assumptions — they work out the expected-value formula rather than simply noting a zero outcome on one data run. This isn't a universal law for any grid under any market conditions; it's a proof for one specific, explicitly stated random-walk model.

This distinction matters because marketplaces never show you that model. A green P&L chart shows the outcome of one specific period on one specific asset — not the expected value of the strategy under a random walk.

## 4. Dynamic Grid Trading

So where does DGT's (Dynamic Grid Trading) positive result come from, in the same authors' test on data from January 2021 to July 2024? Mechanically, DGT differs from a classical grid in one important way: instead of stopping at the range boundary, the grid resets — the current price becomes the new center — and if price breaks below the lower bound, the bot holds the asset instead of dumping it.

By the authors' own numbers, for BTC the DGT strategy's IRR clearly beats buy-and-hold, with a noticeably lower MDD. For ETH, the IRR advantage over buy-and-hold is considerably smaller, while MDD is still lower. In other words, the DGT effect isn't uniform across assets: in one case it shows up in both return and drawdown, in the other mostly in drawdown.

The authors themselves state the source of the result directly: "This strong performance is largely due to the significant rise in cryptocurrency prices in recent years, which is highly favorable for spot grid trading." The test period (January 2021 – July 2024) wasn't uniformly bullish — it includes the 2022 crash — so calling the whole period a "bull market" would be inaccurate. What matters is the cumulative rise in BTC/ETH over the full period, which, by the authors' own account, materially drove the result.

Put in the author's own words rather than a quote from the paper: a grid monetizes the path (the oscillations inside the range), while DGT also retains exposure to the destination (the direction price ultimately travels). The conclusion follows: DGT retains substantial beta exposure and should not be read as market-neutral alpha, regardless of how well it smooths the drawdown along the way.

## 5. Delta-Neutral Grid Market Making

There's a version of the mechanism built differently, one that claims a market-neutral return — Nguyen and Bui (2026, Talyxion), in "Delta-Neutral Grid Market Making with Adaptive Hedging." The idea: run grid quoting on spot while hedging directional risk through futures, so profit comes from capturing the bid-ask spread like a classical market maker, not from the asset's appreciation.

The authors break the profit source down by component in their Table 5 (backtest performance summary, Gate.io BTCUSDT, November–December 2025, 52 trading days): spread/grid profit contributes ≈76% of total P&L, funding fee ≈18%, maker rebate ≈6%. The headline result: Total Return ≈37% over 52 days, Sharpe (daily) >3.0, MDD <8% NAV.

One feature of the paper is worth flagging up front: the abstract describes the system as "exemplified on BTCUSDT on Binance," and the architecture section also refers to operating on two Binance venues, but the actual empirical backtest — the data, the methodology behind Table 5 — was run on Gate.io. This isn't an error in itself; the authors never claim the backtest itself was run on Binance. But it's worth stating plainly: what's in front of us is an architecture proposed for Binance-like spot/futures markets, empirically tested on Gate.io, not a Binance validation in the strict sense.

Before treating these numbers as solid confirmation of an edge, the paper is worth a closer look.

### Apparent capital-sizing inconsistency

The authors state an initial capital of 100 USDT-equivalent, split equally between the spot and futures accounts (50 USDT per leg). At the same time, the base order size per grid level is qbase = 0.01 BTC, with N = 5 levels per side, and V-shape sizing that scales individual levels up to 0.035 BTC. Even a single base order of 0.01 BTC, at the prices discussed in the paper, has a notional value in the range of a thousand dollars — substantially more than the stated 50 USDT per leg, before even counting multiple grid levels or the larger V-shape levels. Nothing in the visible text of the paper offers a detailed explanation, through leverage or margin accounting, that would reconcile these numbers.

This isn't grounds to call the paper wrong — it's an unresolved capital-accounting issue, not a demonstrated error by the authors. But it does mean that the reported 37% return on a 100 USDT NAV can't be taken as an independently confirmed, reproducible result until the margin treatment is clarified, or until someone replicates the strategy at the transaction level.

### A note on citations

A separate reason for caution sits not in the results but in the Related Work section. In the text, Leippold, Wang, and Zhou are described as analyzing retail grid strategies on Binance ("Leippold et al. analyse retail grid strategies on Binance and document that profitability is highly sensitive to grid range calibration..."), yet the same citation (Leippold, Wang, Zhou, 2022) appears in the bibliography as "Machine Learning in the Chinese Stock Market," Journal of Financial Economics. A similar pattern appears with Brunnermeier, Sockin, and Xiong, cited in the text for crypto-perpetual funding dynamics ("Brunnermeier et al. document that funding is positively autocorrelated... consistent with the empirical distribution documented in Brunnermeier et al."), while the bibliography entry lists "China's Model of Managing the Financial System," Review of Economic Studies.

This shouldn't be read as an accusation of bad faith — it may simply be a bibliography-compilation mix-up. But it's methodologically honest to note: at least two citations in the Related Work section appear not to correspond to the works listed for them in the bibliography, which is another reason to treat the paper's empirical claims cautiously.

### The fill model problem

The authors list their own backtest's limitations: a sample of only 52 days; no validation over a prolonged bear market; a fill model that doesn't account for partial fills; no accounting for queue position; heuristic, not data-derived, weights for toxic-flow detection.

The queue-position issue deserves a plain explanation, because it isn't a technical footnote — it's a material assumption for this strategy. The fact that market price touched or crossed a limit order's level doesn't guarantee your specific order at that level actually fills — other resting orders at the same price may sit ahead of it in the queue, and in a real order book your order only fills after those (or not at all, if price reverses first). For a strategy reporting roughly 14,000 completed cycles, this isn't a minor caveat — it's effectively an assumption that nearly every theoretical fill becomes a real one, and that assumption is not tested by the backtest.

For that reason, throughout this note, Sharpe >3, MDD <8%, and the +37% figure should be read as reported backtest results — outcomes of one specific backtest under stated assumptions — rather than as established properties of the strategy itself.

### A methodological note on single-sample validation

A broader methodological point applies here, one that isn't specific to this particular paper. Gort, Liu, and coauthors (2022/2023, Columbia/NYU), in "Deep Reinforcement Learning for Cryptocurrency Trading: Practical Approach to Address Backtest Overfitting," show on crypto markets that a conventional walk-forward method with a single validation split easily leads to model overfitting, and that k-fold cross-validation, the common alternative, relies on an assumption that data are independent and identically distributed (IID) — an assumption that does not hold for financial time series.

We did not compute a probability of backtest overfitting for Nguyen & Bui's work — that would be a separate study we haven't run. But the broader thesis from the methodological literature applies directly: a single 52-day sample on one exchange is not a sufficient basis for claims of robustness, and that's consistent with what the backtesting-methodology literature on crypto markets shows more generally.

## 6. The Fee-Tier Experiment

Worth stating the format up front: what follows is a simplified unit-economics illustration of a single spot-leg round trip, built on the parameters stated in Nguyen & Bui's paper — not a reproduction of their backtest, and not a full simulation of the entire delta-neutral strategy. It doesn't account for execution of the hedging futures leg, hedging costs, adverse selection, or slippage.

Take the same δ = 0.10% spread per cycle on the spot leg, and compute the result at three different levels of spot fees, applying the fee to both sides of the cycle (entry and exit). The paper's own assumption (rebate of −0.025%) is a parameter of the Nguyen & Bui model itself. The retail rates of 0.10% (standard) and 0.075% (with a 25% BNB discount) are not academic-paper figures — they're illustrative retail fee assumptions for Binance, current as of August 2026 (see Binance's official "Fee Structure on Binance" page); exchange fee schedules change, so this part of the calculation should be re-checked whenever this note is updated, not treated as fixed forever:

At the paper's assumption — maker rebate −0.025% on both sides: spread +0.10% minus fees of −0.05% (×2 sides) = **+0.15% per cycle** (the fee is negative — the exchange pays you).

At the retail maker rate with a 25% BNB discount, +0.075% on both sides: spread +0.10% minus fees of 0.15% (×2 sides) = **−0.05% per cycle**.

At the standard retail maker rate with no discount, +0.10% on both sides: spread +0.10% minus fees of 0.20% (×2 sides) = **−0.10% per cycle**.

The number of completed cycles in the paper's backtest — roughly 14,000 over 52 days — doesn't carry over into the arithmetic above directly: you can't simply multiply a per-cycle percentage by the cycle count to get a cumulative return, because each cycle executes on a different share of notional, with position and capital carrying over between cycles (and, as noted above, the relationship between the stated capital and order sizes in the paper isn't fully transparent to begin with). The paper's headline result — the reported ≈37% over 52 days — is reported separately by the authors, and it can neither be derived from nor refuted by a single line of per-cycle unit economics.

What can honestly be said: changing only the fee structure — from negative (rebate) to a standard positive retail rate — flips the sign of the unit economics at the level of a single spot-leg cycle. This doesn't prove the whole algorithm is necessarily unprofitable at retail rates (that would require a full replay of the entire strategy, hedge included), and it isn't grounds to claim the reported +37% is fabricated. It shows that the paper's reported result doesn't carry over "as is" to a retail fee tier without a separate recalculation.

## 7. What Grid Sophistication Actually Buys You

It's worth listing, in order, what the Nguyen & Bui architecture is actually built from, beyond the grid itself: volatility-adaptive level spacing; a dynamic, EMA-based grid center; trend skew (tilting quotes with the trend); accounting for order-flow imbalance over the trailing 60 seconds; funding; inventory-aware quoting; ADX-based regime detection; realized spread; fill asymmetry between sides; tracking adverse price movement in the 5 seconds after a fill; toxic-flow detection; circuit breakers; and spot/futures hedging.

This is no longer "a grid of orders" in the everyday sense — it's a full market-making system, plus inventory management, plus microstructure analysis, plus an execution/risk layer, where the grid's order placement is simply a mechanism, not a source of return in itself. This is the important conclusion for this chapter: the more sophisticated and market-neutral the strategy becomes, the less its return can be attributed to the grid structure itself. The economic source of potential edge shifts toward spread capture, fee structure, execution quality, adverse-selection control, inventory management, and market microstructure — territory where "the grid" is, at best, one component among many, not the main character.

## 8. What Binance Bot PnL Actually Tells You

Back to the storefront from the first section: when a marketplace shows "+$5,000 in a day," the number is often missing context — deployed capital, the period it was earned over, the fee tier behind the bot. (This depends on the specific marketplace interface — some do show ROI or invested capital next to P&L; but where that information is absent or not highlighted, the P&L figure in isolation says nothing about reproducibility.) $5,000 on a $10,000 deposit and $5,000 on a $2,000,000 deposit are two fundamentally different stories, but look identical if you're only looking at absolute P&L.

A P&L figure without context — deployed capital, ROI as a percentage of capital, the length of the period, the fee tier — says nothing on its own about whether the result is reproducible on a different account.

## 9. The Benchmark Test

Even if an account has access to a favorable enough fee tier and delta-neutral grid market making comes out positive, the strategy still has to clear one more filter — not "is the return positive," but "is it positive relative to the best available alternative use of the same capital, at the same risk and effort." This is the same filter this series applies to Carry (Part IV).

Worth stating the format here: this note has no quantitative benchmark test of its own for grid trading — not for classical, dynamic, or delta-neutral. This is a decision-making framework applicable to any strategy examined in this project, not an empirical result of this particular chapter.

## 10. Verdict

Grid trading isn't one strategy — it's at least three mechanically distinct approaches with different sources of return, and different levels of evidence behind each.

Classical grid: within the explicitly stated symmetric random-walk model examined by Chen, Chen, and Jang, the grid structure itself does not generate a positive expected value — this is an analytical result under stated assumptions, and fees only worsen the economics further.

Dynamic grid trading: the reported result likely comes from a combination of two sources — harvesting oscillations inside the range, and retained beta exposure to market direction. The published backtest fell within a period where crypto's rise, by the authors' own account, materially drove the outcome.

Delta-neutral grid market making is a different economic mechanism altogether: spread capture / market making, where fee structure and rebates, actual fills, queue position, adverse-selection control, inventory management, and hedge quality are all critical. Nguyen & Bui's reported result carries an unresolved capital-accounting question and an incomplete fill model, so it's more accurate to call it a reported backtest result than an established property of the strategy.

The overall takeaway: grid is not itself a single source of edge. As the strategy moves from a simple grid toward a robust, market-neutral implementation, the economic source of returns moves away from the grid structure and toward market microstructure, execution, and fee economics.

An important boundary on what is and isn't established here: we have not run a full retail replay of either DGT or Nguyen & Bui's delta-neutral implementation — what exists is Chen et al.'s mathematical result under explicit assumptions, a historical DGT backtest, Nguyen & Bui's proposed architecture, and our own fee-based unit-economics illustration. Mixing these levels of evidence to conclude that "retail grid is proven unprofitable" or "delta-neutral grid cannot work for retail" would be incorrect. The accurate statement is closer to this: published evidence does not establish that the reported result is reproducible under standard retail execution and fee conditions.

## 11. What This Means for a Retail Trader

A standard Binance Spot Grid Bot with Trailing Up enabled, and with automatic liquidation on a range breakout turned off, conceptually resembles some elements of Dynamic Grid Trading — the grid reset, holding the asset through a downside breakout — but it isn't an exact match to the paper's algorithm, just a resemblance at the level of general logic. Configured this way, it doesn't create an independent edge, but it can be a tool for disciplined asset accumulation in a rising or sideways market — provided you understand it's a bet on direction, not a source of profit from nothing.

Delta-neutral grid market making in the spirit of Nguyen & Bui isn't really "turn on a bot" — it's building a system out of the components listed in Section 7, one that depends critically on fee structure, execution quality, and capital-accounting questions the paper itself doesn't fully resolve. The practical checkpoint before turning on any grid bot: don't ask "does grid trading work," ask "on what fees, in what market, under what real execution, and against what alternative is this specific version of grid supposed to prove its advantage."

It's worth walking through this chapter's full arc to see the method this series will keep using: first you see the simple "buy low, sell high, repeat" formula on Binance — a great-looking P&L on a storefront; then academic analysis reveals hard limits in the grid mechanics itself; DGT adds directional exposure; the delta-neutral version adds hedging; and then order flow, inventory, toxicity, volatility regimes, and execution quality enter the picture — and in the end, whatever edge might exist, if any, no longer lives in the pretty grid you see in the Binance interface, but in the far less visible engineering built around it. This is the same method the rest of this series will apply to Momentum, Trend, Carry, and Reversal: not "does it work or not," but "how much of the reported result belongs to the mechanism itself, and how much belongs to the conditions under which it was measured."

## References

- Arefev, O. (2026). "Grid Trading in Cryptocurrency Markets: A Critical Evaluation of Classical, Dynamic, and Delta-Neutral Implementations." SSRN 7376359. https://ssrn.com/abstract=7376359 — DOI: 10.2139/ssrn.7376359. *(Formal write-up of this note's argument.)*
- Chen, K.-Y., Chen, K.-H., Jang, J.-S. R. (2025). "Dynamic Grid Trading Strategy: From Zero Expectation to Market Outperformance." arXiv:2506.11921.
- Nguyen, T., Bui, D. (2026). "Delta-Neutral Grid Market Making with Adaptive Hedging." SSRN 6280958.
- Gort, B. J. D., Liu, X.-Y., Gao, J., Chen, S., Wang, C. D. (2022/2023). "Deep Reinforcement Learning for Cryptocurrency Trading: Practical Approach to Address Backtest Overfitting." arXiv:2209.05559. *(Methodological reference only — not a grid trading source.)*
- Binance. "Fee Structure on Binance." Official FAQ, accessed August 2026. Used only as the source for the illustrative retail fee assumptions in Section 6; these change over time and should be re-verified against the current schedule whenever this note is updated.
