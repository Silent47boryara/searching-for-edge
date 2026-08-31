# Searching for Edge

*Independent Research into Systematic Crypto Trading & Market Microstructure*

**Author: Oleg Arefev**

Can a retail trader systematically extract an edge from cryptocurrency markets — and does that edge remain worth trading after costs, infrastructure constraints, and a simple investment benchmark?

This repository is a research log, not a trading signal service and not an academic publication. Each note follows the same pipeline: **literature → reverse engineering → replication on Binance data → gross → net-of-costs → significance testing → verdict**. Negative and inconclusive results are published alongside positive ones — a closed hypothesis is still a result.

## Research Notes

| # | Note | Status |
|---|------|--------|
| 00 | [Can You Trade Crypto Profitably by Formula?](00-introduction/can-you-trade-crypto-profitably.md) | `Published` |
| 01 | [The Grid Bot Illusion](01-grid/grid-bot-illusion.md) | `Published` · `Literature-based` |
| 02 | [Momentum: Evidence from a Binance Replication](02-momentum/momentum-evidence-from-binance-replication.md) | `Published` · `Empirically tested` |
| 03 | [Trend: When Published Edge Ages](03-trend/trend-when-published-edge-ages.md) | `Published` · `Literature-based` |
| 04 | [Carry: A Real Edge I Wouldn't Trade](04-carry/carry-a-real-edge-i-wouldnt-trade.md) | `Published` · `Empirically tested` |
| 05 | Reversal: How a Backtest Fooled Me | `Planned` |
| 06 | What Is Left for a Retail Trader? | `Planned` |

Each note, once published, is tagged with how it was established:
`Literature-based` (summarizes published findings, no own backtest) · `Empirically tested` (own replication with gross/net numbers and significance tests) · `In progress` (partial results, not yet closed).

## Methodology

Every candidate strategy is checked against the same discipline before it is allowed into a note:

1. **Statistically real?** — does the effect exist in the published literature and in an independent replication, not just in a chart that looks convincing.
2. **Reachable by retail?** — even where a published number is positive, does capturing it require a universe, a fee tier, or a market regime that a retail trader can actually access today — not just on paper, and not just in a market that no longer exists.
3. **Tradable net-of-costs?** — does it survive realistic fees, spread, slippage, funding, and execution — not the gross number from the paper.
4. **Worth trading versus the benchmark?** — does it beat the best available alternative use of the same capital, given the risk and effort involved.

Any one of these four failing is sufficient to close a hypothesis — they aren't ranked, and a strategy doesn't need to fail all four to be closed. Part I (Grid) found separate failures across its three mechanically distinct variants — a zero-expected-value result for the classical form, retained market-beta exposure for the dynamic form, and, for the delta-neutral form specifically, a reported result resting on gate 2 (an institutional-only fee tier, plus an incomplete fill model). Part II (Momentum) closed on gate 3 (costs, after an own replication). Part III (Trend) closed on gates 1 and 2 together, without needing a replication, because gate 1 already failed in the regime that matters and gate 2 failed on both candidate universes in the literature itself.

A maximum of two independently published implementations is tested per hypothesis class. If both fail, the class is closed — no third variant is tried "to save it."

Full protocol notes will be published in `methodology/` as each research note is finalized.

## What this repository does not contain

The underlying event-detection system (Klines) referenced in some notes is proprietary and not published here. This repository publishes research methodology, literature review, and aggregate empirical results — not production thresholds, scoring logic, or execution rules.

## References

Literature is organized into two reference lists, published in `references/`: [reference-1-strategy-literature.md](references/reference-1-strategy-literature.md) covers strategy and factor literature tested against the Binance universe (momentum, trend, carry, reversal, grid, VRP); [reference-2-microstructure-literature.md](references/reference-2-microstructure-literature.md) covers the market microstructure and event literature. Both are updated as the series progresses.
