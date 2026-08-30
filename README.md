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
| 02 | Momentum: Evidence from a Binance Replication | `Planned` |
| 03 | Trend: When Published Edge Ages | `Planned` |
| 04 | Carry: A Real Edge I Wouldn't Trade | `Planned` |
| 05 | Reversal: How a Backtest Fooled Me | `Planned` |
| 06 | What Is Left for a Retail Trader? | `Planned` |

Each note, once published, is tagged with how it was established:
`Literature-based` (summarizes published findings, no own backtest) · `Empirically tested` (own replication with gross/net numbers and significance tests) · `In progress` (partial results, not yet closed).

## Methodology

Every candidate strategy is checked against the same discipline before it is allowed into a note:

1. **Statistically real?** — does the effect exist in the published literature and in an independent replication, not just in a chart that looks convincing.
2. **Tradable net-of-costs?** — does it survive realistic fees, spread, slippage, funding, and execution — not the gross number from the paper.
3. **Worth trading versus the benchmark?** — does it beat the best available alternative use of the same capital, given the risk and effort involved.

A maximum of two independently published implementations is tested per hypothesis class. If both fail, the class is closed — no third variant is tried "to save it."

Full protocol notes will be published in `methodology/` as each research note is finalized.

## What this repository does not contain

The underlying event-detection system (Klines) referenced in some notes is proprietary and not published here. This repository publishes research methodology, literature review, and aggregate empirical results — not production thresholds, scoring logic, or execution rules.

## References

Literature is organized into two reference lists, published in `references/`: [reference-1-strategy-literature.md](references/reference-1-strategy-literature.md) covers strategy and factor literature tested against the Binance universe (momentum, trend, carry, reversal, grid, VRP); [reference-2-microstructure-literature.md](references/reference-2-microstructure-literature.md) covers the market microstructure and event literature. Both are updated as the series progresses.
