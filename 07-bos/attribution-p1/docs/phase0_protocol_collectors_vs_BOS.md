# PROTOCOL: do collector data help predict BOS outcomes?

Status: **draft; calculations have not started; awaiting Oleg's approval.** Written on 2026-10-07.
All thresholds marked ⚑ are proposals, not established facts; Oleg must approve them before calculation.

## 1. Question and mechanism

**Question.** Do funding / OI / liquidation streams (Binance BTCUSDT) and gamma (Deribit) add information about the outcome of a causal BOS beyond the BOS itself and simple volatility?

**Use only previously established targets** (HANDOFF §4.2–4.3), without inventing new ones:
- **Y1 (primary):** the BOS level is *lost* by a horizon of 5 days (the close has moved back across the breakout level). The same horizon of 5 calendar days applies to all timeframes.
- **Y2 (secondary):** MAE over the first 24 hours, as a percentage of the BOS bar close.

**Mechanism (hypotheses, not facts).**
- Funding and OI indicate crowded positioning: a breakout with inflated OI and high funding aligned with the breakout direction is more likely to retrace.
- Liquidations aligned with the breakout may provide fuel (a short squeeze during BOS↑) or indicate exhaustion.
- Gamma is secondary; see §3.

We do not predict BOS direction (HANDOFF §4.1), including in this study. The objective is early observation, not a directional forecast.

## 2. Measurement contract (shared across the lab)

- **BOS:** causal `find_all_bos` from `bot_v2.py`, SWING_LAG=2; an event is the first bar in a sequence, with no parameter changes. ⚠ Correct operation on 1H/4H has not been verified (HANDOFF describes it on 1D). Check this in Step 0 before anything else.
- **Timeframes:** 1H and 4H are primary. 1D is descriptive only (there are 1–3 events over ~5 weeks, insufficient for statistical inference).
- **Time.** A feature is available if `recv_ts_utc ≤ BOS bar close time`. Neither `event_time` nor the candle open time is used. Logs are in Moscow time, CSV files in UTC: normalize to UTC.
- **Data window:** intersection of clean periods, starting at 2026-08-29 11:28 UTC (funding/liq start). Gamma is used only until 2026-10-02 10:10 UTC. Events whose feature window overlaps a data gap are excluded and recounted in the report; gaps are not filled.

## 3. Features: specified in advance, one per family, rank based

Fix these before calculation; do not fit thresholds (use value rankings and AUC):
- **F1 funding:** latest value at t × BOS direction sign.
- **F2 OI:** OI change over the 24 hours before t, %.
- **F3 liquidations:** notional liquidated *in the breakout direction* over the 24 hours before t, USD.
- **Baseline screen:** |return over the 24 hours before t|. Any feature must outperform this; otherwise it merely captures volatility.
- **Gamma and trade tape: exploratory, ineligible for a verdict of “helps.”** The gamma aggregate stores absolute values; its sign depends on an assumption about dealer positioning that we do not have. The window has a gap starting on October 2. For tape, there is no mechanism hypothesis represented by a single feature.

Test family: 3 features × 2 timeframes = 6, with Holm correction.

## 4. Statistics

- Feature AUC against Y1 (and Spearman correlation with Y2).
- Events are dependent (overlapping 5-day windows): use BOS clusters and a block bootstrap over clusters for CIs; placebo: randomly shift the feature cyclically in time by ≥5 days.
- Split the period into chronological halves only to check sign consistency. **This is not an independent holdout:** the period has already been examined.
- For each timeframe, show **all** events in a table and chart (candle + level + feature), rather than selecting attractive examples.

## 5. Step 0: statistical power gate (before testing features)

Count only causal BOS events and clusters by timeframe in the clean window, and calculate the **minimum detectable AUC**. Roughly: SE ≈ √((n₁+n₂+1)/(12·n₁·n₂)); with ~15 + 15 events, SE ≈ 0.11, so only AUC ≳ 0.71 is detectable.
- If MDE-AUC > 0.65 ⚑ → do not treat feature analysis as hypothesis testing; the verdict is “insufficient data.” Report how much longer collection is needed at the current BOS frequency.

## 6. Criteria for resolving the question in either direction ⚑

- **Helps (partially):** on ≥1 timeframe, AUC>0.5, Holm-adjusted p < 0.05, the feature outperforms the baseline (AUC difference with CI > 0), and the sign agrees across both halves of the period.
- **Does not help at this sample size:** MDE ≤ 0.65 and the AUC CI for every feature lies within [0.40, 0.60]. This negative result applies to these three features and this horizon, not to the entire family of methods.
- **Insufficient data:** everything else.

In all cases, report the available event count, the required count, and the number of weeks needed at the current frequency.

## 7. Conditions and limitations

- **~5 weeks mostly represent a single price regime**; findings cannot be generalized to other regimes without additional data.
- **Data are not yet clean:** Deribit streams (gamma, tape) are affected by VPN routing (`utun8`); funding/liq/OI are running, but gaps (OI on September 3: 286 minutes; DNS failures on September 9–12; today's outage) must be recalculated rather than assumed.
- For 1H/4H, BTCUSDT klines are needed for the full window plus 500 warm-up bars; it has not been verified that `BTCUSDT_1h_history_full.csv` extends into October.
- Prohibited: changing bot thresholds, adding indicators/ML, or turning the result into a trading rule. New hypotheses go into the journal, not into this calculation.

## 8. Decisions needed from Oleg

1. Approve Y1/Y2, the 5-day horizon, the three features and baseline, and the ⚑ thresholds.
2. Authorize Step 0 (event counts and power only, without features).
3. Decide whether to fix Deribit routing before calculation (affects only the gamma/tape component).
