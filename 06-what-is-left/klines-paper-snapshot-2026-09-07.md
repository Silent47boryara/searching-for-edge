# Klines — Paper Snapshot, 7 September 2026

**Author:** Oleg Arefev
**Status:** `Open` — a point-in-time paper measurement, published as-is; live execution still unverified
**Scope:** the post-patch paper log only — 83 signals over 19 days (2026-08-19 → 2026-09-07), on the honestly-timed log (real detection timestamp and reference price, the format described in [Note 06](what-is-left-for-a-retail-trader.md) §4).

This is a raw progress snapshot, not a result. It is published because the series commits to showing numbers as they stand — including when they are inconclusive or unflattering — rather than only when they look finished.

---

## 1. The full population is negative — but it is not what gets traded

Taken across **every** candidate the monitor produced, including the ones the system is built to reject, the log is net negative:

| metric | value |
|---|---|
| trades (full population) | 83 |
| sum PnL | −46.64% |
| mean | −0.562% |
| median | −1.020% |
| win rate | 39.8% (33/83) |

This number describes "enter everything the scanner flags." That is explicitly **not** how the system is used: the Stage-3 gate exists precisely to throw most of this away, and the discretionary layer never enters a cancelled signal. So the −46.64% is the cost of the haystack, not the P&L of the strategy — reported here for honesty, not as the headline.

## 2. The Stage-3 gate separates cleanly

| Stage-3 status | n | mean | median | win rate | sum |
|---|---|---|---|---|---|
| CONFIRMED | 33 | +4.56% | +2.20% | 69.7% | +150.34% |
| CANCEL | 41 | −3.69% | −2.73% | 19.5% | −151.23% |
| WARNING | 9 | −5.08% | −3.38% | 22.2% | −45.75% |

The separation is strong: the confirmed side is clearly positive, the cancelled/warning side clearly negative. The gate is doing its job. The uncomfortable symmetry is that the loss avoided on the cancelled side is almost exactly the size of the gain on the confirmed side — which is only a problem if you trade both, and the point of the system is that you don't.

## 3. What a human actually trades — the confirmed ("ALIVE") side

Filtering to the labels a discretionary trader would actually act on (the 🟢/🟡 ALIVE tiers, never CANCEL or WARNING):

| metric | value |
|---|---|
| trades | 31 |
| sum PnL | +153.59% |
| mean | +4.95% |
| median | +2.97% |
| win rate | 74.2% |

On paper, the side that actually gets traded is positive. That is the honest counterweight to Section 1. But it rests on three props that have to be named, or the number is misleading in the other direction.

**Prop 1 — the strongest tier is partly mechanical.** The top label (internally "STRONG_CLEAN": 15 trades, +143.56% sum, 100% win rate) is defined partly by a strong upward move in the first minutes, while the exit is a trailing stop. That combination creates an arithmetic floor — a non-negative result is close to guaranteed *by construction* for that label, so the 100% win rate proves little on its own. Measured **above** that floor, the added edge is a modest **+1.42 pp median**, and **4 of the 15 exited exactly at the floor** — i.e. contributed nothing beyond the mechanic. The effect above the floor is real but small at this sample size.

**Prop 2 — one outlier carries much of the total.** A single +43.16% trade drives a large share of the sum. Remove it and the traded set falls from +153.59% to **+110.43%** — still positive, but the average roughly halves.

**Prop 3 — the ordinary signal is flat.** Outside the mechanical top tier, the plain confirmed signal ("GOOD_FLOW": 14 trades) is essentially break-even on paper: **mean +0.37%, median −0.15%, win rate 42.9%**. The current paper edge concentrates in the strong-move tier; the everyday signal is not, right now, carrying weight.

## 4. What cannot be measured here

All 41 cancelled trades stop being monitored at the moment of cancellation (exit at minute 5; their 60-minute path equals their 5-minute path in the log). So whether each cancel **saved** money or **exited too early** is unknowable from this data. The −151% attributed to the cancel rule has no measured counterfactual. Closing that gap requires logging the full 60-minute path even after a cancel (marking the position closed without stopping the measurement) — an engine change, not a re-analysis.

## 5. The decisive open question — fills

Every number above is priced at a reference price recorded **after** Stage-3 confirmation — already after part of the move that makes a signal look good. An earlier, more pessimistic fill assumption has, in this project's own history, flipped the same population from a paper gain to a paper loss by changing that one input. Nothing here is net of real slippage and real order latency. This is the same unresolved variable that keeps [Note 06](what-is-left-for-a-retail-trader.md) at `Open`, and it is the reason this snapshot is a measurement, not a claim.

## 6. Trend over the 19 days

| week | n | sum | win rate |
|---|---|---|---|
| 19–23 Aug | 31 | −29.59% | 35% |
| 24–30 Aug | 32 | −26.47% | 41% |
| 31 Aug – 6 Sep | 18 | +17.58% | 50% |
| 7 Sep (partial) | 2 | −8.17% | 0% |

The first full net-positive week is the most recent complete one — on 18 trades, far too small to call a turn. Cadence: about 4.6 signals a day overall; the strong-move tier appears roughly 5–6 times a week.

## 7. Bottom line

The detector runs and the Stage-3 gate cleanly separates a positive side from a negative one — that much is demonstrated. The side a human actually trades is positive on paper. But that positive is currently carried by a partly mechanical top tier and one outlier; the ordinary confirmed signal is roughly break-even; the value of the cancel rule is unmeasured; and none of it is net of real fills. Direction confirmed, edge real but thin, profitability **not** established on live execution. Status: `Open`.

---

**Author:** Oleg Arefev
**Project:** [Searching for Edge](https://github.com/Silent47boryara/searching-for-edge) · companion to [Note 06 — What Is Left for a Retail Trader?](what-is-left-for-a-retail-trader.md)
