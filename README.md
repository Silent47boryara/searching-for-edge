# Searching for Edge

*Independent Research into Systematic Crypto Trading & Market Microstructure*

**Author: Oleg Arefev**

**Website: [karaptic.com](https://karaptic.com/)**

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
| 05 | [Reversal: Two Kinds of Mean Reversion, One Closed on Sight](05-reversal/reversal-two-kinds-of-mean-reversion.md) | `Published` · `Open` (Branch A closed, Branch B awaiting its own Gate replication) |
| 06 | [What Is Left for a Retail Trader?](06-what-is-left/what-is-left-for-a-retail-trader.md) | `Published` · `Open` |
| 07 | [BOS: A Structural Scanner, Not a Predictor](07-bos/bos-a-structural-scanner-not-a-predictor.md) | `Published` · `Open` (core structural detection in production; options/gamma overlay under test, decision end of Sep 2026) |

Each note, once published, is tagged with how it was established:
`Literature-based` (summarizes published findings, no own backtest) · `Empirically tested` (own replication with gross/net numbers and significance tests) · `In progress` (partial results, not yet closed) · `Open` (published with an honest verdict on part of the hypothesis, while another part is explicitly left for a future replication rather than forced to a premature close).

Note 06 is not another literature-tested hypothesis — it's Oleg's own synthesis, presenting Klines (the event-detection system referenced elsewhere in this repository, not published in full — see below) and the discretion built around it as one candidate answer to the series' opening question, in the author's own voice. It's held to the same disclosure standard as every other note: no automation claims, no guaranteed profitability, findings framed as what was observed, not what's proven.

## Publications

Work from this series formally written up and deposited where it can be cited. A paper here is not a separate research result — it is one of the notes above, restated to academic standards and made citable.

- **Grid Trading in Cryptocurrency Markets: A Critical Evaluation of Classical, Dynamic, and Delta-Neutral Implementations** (August 2026) — the formal write-up of [Note 01](01-grid/grid-bot-illusion.md). SSRN working paper: [ssrn.com/abstract=7376359](https://ssrn.com/abstract=7376359) · DOI: [10.2139/ssrn.7376359](https://doi.org/10.2139/ssrn.7376359)

## On the Horizon

Candidates identified but not yet active, kept visible rather than quietly dropped. Two different reasons keep something here rather than in the numbered series above: it needs infrastructure this project doesn't have, or it's genuinely too new to have a verdict yet.

**Excluded from the strategy-selection process (decided 06.08, before any of these were tested — not forgotten, deliberately out):**

| Candidate | Why it's out |
|---|---|
| On-chain factors (Sakkas & Urquhart, 2024) | A real, published finding — but it requires external infrastructure (a node, or a paid service like Glassnode/Dune) that doesn't compute directly from Binance data, and isn't reproducible by a single developer without that dependency. |
| Size | Redundant with the liquidity gate already used elsewhere in this series — the underlying literature itself documents a strong size↔liquidity↔age correlation, and independent evidence shows the size effect weakening since 2023. |
| Value | No agreed fundamental valuation model exists for crypto assets — no earnings or book-value analogue — making this the weakest-grounded candidate across the board. |
| Downside risk (as a standalone factor) | Support specific to crypto is thin — it hasn't survived multiple independent studies the way the tested classes above have. Demoted to a position-sizing input inside surviving strategies, not a hypothesis of its own. |

**Researched under a separate, adjacent project (System 2 — Trend Catcher), not yet started:**

| Candidate | Status |
|---|---|
| Trend-continuation component of Klines — whether the detector's logic extends to the slow, grinding continuation moves on already-liquid pairs (BNB, TON, ACE) that the spike detector structurally misses (the gap Note 06 names in its closing section) | Not started. A separate validation path from Klines' spike logic — EDA and walk-forward testing not yet begun; explicitly not permitted to borrow Klines' own thresholds or trailing-stop rules. |
| Options-flow data (gamma concentration, IV skew, open-interest expansion) as a confirming signal alongside BOS | Data collection in progress, not yet analysis-ready — early days, single price regime observed so far. Framed as a three-tier test before it could become a strategy of its own: (A) does options positioning carry predictive information on its own; (B) does it add anything on top of price-structure signals; (C) only if A or B hold up, a standalone options strategy. Currently pre-(A) — this is the newest, least-validated item on this list, flagged here specifically so it isn't mistaken for something further along than it is. |

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

Literature is organized into two reference lists, published in `references/`: [reference-1-strategy-literature.md](references/reference-1-strategy-literature.md) covers strategy and factor literature tested against the Binance universe (momentum, trend, carry, reversal, grid, VRP); [reference-2-microstructure-literature.md](references/reference-2-microstructure-literature.md) covers the market microstructure and event literature; [reference-3-price-structure-momentum-literature.md](references/reference-3-price-structure-momentum-literature.md) covers price-structure and intraday-predictability literature (Note 07). All are updated as the series progresses.
