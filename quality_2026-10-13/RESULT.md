# BOS: state quality, unmet expectations, corrections, and replay

**13.10.2026 · Codex. Status: diagnostic research complete; a corrected research version is prepared but has not been deployed to production.**

## Main answer

**Code errors exist, but they do not explain the entire failure to meet expectations.** A targeted correction to the confirmation boundary hardly improves BOS accuracy. It is not completely chaotic: its states relate to recent movement more strongly than a randomly time-shifted version of the same state sequence. But it is a coarse, delayed map of selected levels, often remaining active during a neutral local net move. A convincing trading contribution or reliable improvement from collectors has not been established.

This does not mean “all BOS is useless”. A specific author-defined implementation and three separately specified variants were tested. **Rebuilding it to rescue previous results is not recommended now.** Set this branch aside as the basis of a trading decision; retain the tool only for explicit confirmed levels/statuses with honest limitations.

## 1. Why BOS seemed promising

The basis is saved project documentation, not speculation about Oleg's motives. `BTC_RESEARCH_HANDOFF.md`, §0, records the original task as detecting a potential pump/dump and subsequently monitoring its development. §1 describes the transition to SMC structure, three timeframes, and a human layer.

What made the idea attractive:

1. A previous extreme and its break look more concrete than a generic RSI/MACD/OBV score. The intuition: price has left its former structure, creating an observable invalidation level.
2. On selected large waves, lower timeframes detected movement before the daily layer. The old handoff reported 93% 1H coverage and a median lag of 35 hours. This is an attractive observational property.
3. Strong “PROVEN” language appeared around level held/lost, MAE, and stops. This could suggest that the entire system's usefulness had been established.
4. When prediction was not confirmed, the goal shifted to a “descriptive scanner”, then derivatives context. BUY/SELL, quality scores, and Stop-Loss/Take-Profit levels nevertheless remained in the interface.

Where the reasoning broke down:

- **Coverage of large waves is not accuracy across all displays.** A system producing many states can appear in nearly every large wave while also producing many uninformative displays. The handoff itself acknowledges frequent events and whipsaw.
- **An advantage over daily BOS is not an advantage over simple price or a moving average.** The daily layer is inherently slow.
- **A level holding on day 5 is day-5 information, not an entry edge on the BOS day.** Without an exact condition time and control group, conditional outcome separation cannot be transferred to an early signal.
- **A Quality–future-move correlation of 0.009 does not by itself prove BOS direction is a coin toss.** It concerns that specific score. The lack of a stable BOS effect in Phase2A is a separate observation.
- Negative trading tests, flawed methods, and insufficient samples are different outcomes. They cannot be merged into proof that “the entire family does not work”; nor can the system be rescued by calling it a “scanner” without measuring usefulness.

The initial idea was not absurd. The overstatement was the leap from reasonable structural intuition to a promise of useful decisions.

## 2. What was tested

`PROTOCOL.md` was created before the main calculations. BOS thresholds were not tuned. Only existing local Binance spot data were used; no new candles were downloaded.

| Timeframe | Closed replay bars | Result-availability range |
|---|---:|---|
| 1H | 40 771 | 21.01.2022 20:00 — 07.10.2026 09:00 UTC |
| 4H | 9 444 | 25.03.2022 08:00 — 07.10.2026 08:00 UTC |
| 1D | 794 | 05.08.2024 — 07.10.2026 UTC |

Each tick reproduces the production window of **499 closed candles**. 4H/1D use only complete UTC groups of 1H candles. Overlapping OHLCV matched 1136 original 4H and 644 original 1D candles, with volume differences limited to floating-point precision.

Two source-data quality issues were identified and saved:

- Among 1599 overlapping hours, the old final candle at 20.08.2026 14:00 had been saved before close: mtime 17:43 Moscow time, hourly close 18:00 Moscow time. Its Close/Volume were replaced **in the research assembly**, not the source, using the later closed Binance record. The discrepancy is saved in `overlap_last_partial.csv`.
- The 1H candle at 24.03.2023 13:00 is missing. No interpolation. Incomplete aggregates and 499-bar windows crossing the gap were excluded. Hence 1D contains only 794 bars: a conservative daily-history subsample, not a complete multiyear daily replay. Separate original daily data could extend the period, but current conclusions cannot be called a test of every day in 2022–2026.

Gamma calendar: 24.08.2026 19:44 — 07.10.2026 18:20. Actual candles end earlier, so the common window evaluates 1046 hourly, 262 four-hour, and 44 daily closes. Gamma gaps were not filled and remained excluded in derivatives checks. Historical years had been inspected in earlier laboratories: **this is not a new independent holdout**.

## 3. Errors and three distinct variants

| Variant | Change | Interpretation |
|---|---|---|
| `original` | Exact historical core | Comparison baseline |
| `lag_fixed` | Swings become available at i≤t−2 instead of i<t−2 | Corrects the mismatch between code and stated lag |
| `fallback_contract` | Same, plus mandatory termination at the initial BOS level before a new opposing pivot | **A specification change**, not automatically the correct BOS |

Separately corrected in the research interface: ENDED is not active; no fictitious operative break is displayed before a real pivot exists; closed candles are selected by time; insufficient/error data produce DATA_UNAVAILABLE rather than NONE. These changes remove misleading messages but do not by themselves create a different historical edge.

`candidate_core.py` and `candidate_helpers.py` are isolated modules without networking/keys/Telegram; **not files for directly replacing bot_v2.py**. Mandatory initial-level exit is implemented separately in the replay kernel to distinguish it from corrections.

### How much the corrections change states

| Timeframe | ACTIVE direction changed after the lag correction, full sample | Gamma window |
|---|---:|---:|
| 1H | 0.62% of bars | 1.91% |
| 4H | 0.15% | 0% |
| 1D | 0% | 0% |

The stricter initial-level variant changes about 17% of hourly/four-hour states and 14% of daily states. This is substantial new logic; historical conclusions require recalculation, performed here within a limited, predefined scope.

## 4. How closely states describe observed price

There is no single objective “true BULL” label. The primary **operational** label here is the close change over the past 12 bars: above +1ATR is up, below −1ATR is down, otherwise a neutral **net move**. Neutral does not necessarily mean calm: intrawindow volatility can be high. The label is known at decision time, uses no future price, and does not depend on BOS.

All 9 combinations were checked: 6/12/24-bar horizon × 0.5/1/2ATR. The primary combination was not selected for the best result. Balanced accuracy is mean recall over represented classes, not trade win rate. With three classes, a constant neutral response gives 33.3%. The daily gamma window contains no down class under this label, so full three-class accuracy cannot be evaluated there.

### Historical primary-criterion results

| Timeframe | Original BOS | Lag corrected | Initial-level exit* | Simple EMA20±0.5ATR |
|---|---:|---:|---:|---:|
| 1H | 52.45% | 52.41% | 54.86% | 74.70% |
| 4H | 53.38% | 53.41% | 56.11% | 73.88% |
| 1D | 48.28% | 48.28% | 50.15% | 73.68% |

\*Specification change. Improvement must not be described as discovered profitability.

EMA is better under all 9 definitions in each timeframe's historical sample. The gap also persists by year for 1H/4H. But there is a **material comparison cost**: EMA switches approximately 6 times as often. 1H BOS: 0.90 changes/day; EMA20: 5.67. This does not prove EMA superiority at equal switching load.

An explicitly exploratory control followed the main check: update EMA only once every 24 bars. 1H frequency falls to 0.63/day and the score to 45.42%, below BOS. Corresponding scores are 42.80% on 4H and 47.38% on 1D. This is **not a perfectly matched comparison**, but demonstrates the speed/persistence trade-off. It is not valid to conclude that every simple method always beats BOS.

A paired 7-day block bootstrap gives lag_fixed−original on 1H of −0.04 percentage points, with an interval approximately [−0.13; +0.04] points; on 4H, +0.03 points [−0.03; +0.14]. Improvement from the lag fix is not established. EMA's faster descriptive response has a large advantage, but its interval does not remove the difference in switching frequency. Blocks/shifts are diagnostic approximations, especially limited by long daily states and only 7 weekly blocks in the gamma period.

### What ACTIVE accompanies during the gamma window

Percentages are of **active bars**, not all candles or losing trades:

| Timeframe | Net move aligned with state | Neutral net move | Opposite to state |
|---|---:|---:|---:|
| 1H | 50.4% | 42.0% | 7.6% |
| 4H | 50.3% | 35.9% | 13.7% |
| 1D | 56.1% | 43.9% | 0%* |

\*No BEAR class under the selected 12-day criterion in this short window. Not evidence of flawless 1D performance.

Example: on 19.09 03:00–11:00 UTC, hourly BULL remains active while price changes approximately from $81 305 to $81 217 and the local 12-hour net move remains neutral under the criterion. The user's observation of “BULL during neutrality” is real. Calling every such bar a false signal is nevertheless inaccurate: the original state means “the structural termination rule has not yet been met”.

**The broken-clock question:** random circular shifts preserve BULL/BEAR proportions and state durations but remove temporal alignment. Over the long history, the actual 1H/4H descriptive score is substantially above such shifts; this also occurs in the gamma period. Daily states during gamma are almost constant, and no advantage over shifts is established. Lower timeframes are therefore not pure randomness, but their temporal association with past movement is not a forecast.

## 5. Why the earlier 93% coverage looked convincing

Supplement after the primary check: a separate retrospective labelling of 8% waves using hourly closes, taking the threshold from the earlier branch. Not an exact reproduction of the old 134 waves: the data cutoff, closes, conservative exclusions, and warmup differ. Extremes are used **only for evaluation**, never passed to the detector.

- 1H: 138 completed available waves, coverage by at least one direction-matching ACTIVE state **93.5%**, median lag among detected waves **35 hours**.
- 4H: 127 waves, coverage **74.0%**, lag **93.5 hours**.
- 1D: 61 waves, coverage **45.9%**, lag **88.5 hours**; its sample differs from 1H and the old handoff, so these medians cannot be compared directly.

A matching state already active at wave onset was counted separately: 2.2% on 1H, 5.5% on 4H, 23.0% on 1D. The initial-level variant neither increases hourly coverage nor reduces hourly lag.

Being “present inside most large waves” thus reproduces. But it does not answer how many extra states occur, what was known before a substantial move, or how much movement remains after the display. This is where expectations became overstated.

## 6. Future movement after a signal is a separate question

To distinguish description from prediction, the next 12-bar direction-aligned move was measured from **every active bar**, not merely a favourable first entry.

During gamma, original/lag-fixed 1H median next-12-hour moves were approximately **−0.11% / −0.09%**, with positive outcomes **44.7% / 45.4%**. Initial-level variant: **−0.21%**, positive outcomes **40.7%**. On 4H the next horizon is **48 hours**; on 1D it is **12 days**, so these figures cannot be pooled as 12-hour forecasts. Full table: `forward_active.csv`.

Long-history results differ across timeframes/horizons; some mean moves are positive. This does not claim that every continuation is ruled out. Windows overlap, costs/execution are absent, and no strategy is validated. The new test **did not show that correcting errors turns BOS into a reliable forecast**. It agrees with the cautious Phase2A conclusion without replacing it with a new trading backtest.

## 7. Collector relationships after corrections

**Only the two fixed candidates** were repeated, without searching 272 variants. Original gamma/tape definitions/masks, causal windows, and MAE24 outcomes were retained. On original events, features and MAE reproduced numerically within floating-point errors of approximately 10⁻¹³. This is not new independent validation.

| Variant | Tape before 1H starts: valid N / rho with MAE24 | Gamma at transitions: N / rho |
|---|---:|---:|
| Original | 14 / +0.618 | 36 / −0.580 |
| Lag corrected | 14 / +0.618 | 35 / −0.562 |
| Initial-level exit* | 19 / +0.289 | 49 / −0.221 |

Multitimeframe transition counts: 43 → 42 → 55. New actual 1H starts within the common window: 16 original/lag-fixed, 22 initial-level; 4H: 5 / 5 / 6. Phase2A reported 17/6, including one 1H and one 4H start before the common 29.08 boundary. This is a left-censoring difference, not missing events or a new BOS error. All 16/5 common original starts match in time and direction.

**Implication:** a small code fix neither rescues nor refutes the earlier derivatives findings. A substantial new specification weakens the leads on the same discovery sample. New OI/funding/liquidation settings were not searched: their earlier negative/weak result remains a result for the earlier specification, not proof that no relationship could exist after any redesign.

It is not valid to say “collectors definitely have no relationship with BOS”: few independent regimes, gaps, unsigned gamma without dealer positions, option flow not equal to dealer hedging, and sampled forceOrder data limit inference. But there is currently no practical basis for building a new BOS around these two leads. Data after 07.10 were not downloaded; no forward confirmation is claimed.

## 8. What the literature contributes

Full focused review: `LITERATURE.md`, including primary sources and limits of reading.

- [CME](https://www.cmegroup.com/education/courses/technical-analysis/support-and-resistance): previous extremes and breaks are reasonable educational intuition, not validation of our thresholds.
- [Lo–Mamaysky–Wang](https://web.mit.edu/wangj/www/pap/LoMamayskyWang00.pdf): some recognised patterns may contain information; this need not imply trading profit.
- [Sullivan–Timmermann–White](https://eprints.lse.ac.uk/119144/1/dp303.pdf): good historical breakout rules may not repeat their advantage in later years.
- [Osler](https://www.newyorkfed.org/research/staff_reports/sr125.html): order placement provides a mechanism for levels, but our filtered swing is not itself observed liquidity.
- [Borgards](https://community.portfolio123.com/uploads/short-url/amrMsuqIKzdHcHHyvMud4YNPwZB.pdf): a related structural momentum-cycle idea, with a different algorithm, sample, and trading assumptions; not ready validation of this implementation.

The reviewed primary sources did not establish that 5-bar swings + EMA/ATR/volume + three timeframes should accurately label BTC or predict continuation. Modern SMC vocabulary, classical levels, statistical structural breaks, and TSMOM must not be pooled as one body of validating evidence.

## 9. Decision on this branch

**Worth doing now:** adopt semantic corrections for trustworthy observation if the tool stays in use. Deployment is a separate decision; the running bot_v2.py was not touched here.

**Not justified:** treating bugs as the explanation for every negative laboratory, launching another filter search, rebuilding BOS solely around weak gamma/tape correlations, presenting 93% coverage as accuracy, or treating the EMA comparison as a profitable ready replacement.

**Recommendation:** freeze the current BOS branch as a trading-decision foundation. Retain an observational tool only if confirmed levels and infrequent state changes are personally useful to Oleg. An accurate current up/sideways/down display requires a separate specification with an explicit horizon and acceptable delay. Current BOS does not fulfil that role accurately enough, and the literature does not require continued attempts to rescue it. No entirely new detector/strategy was built in this work.

## 10. Checks and artifacts

- 75 deterministic windows: optimised original replay matched exact AST functions on state/direction/start, operative break, and EMA/ATR.
- 30 windows: lag-fixed matched the separate candidate_core. 7 closed-candle/ENDED/DATA_UNAVAILABLE contract checks — PASS.
- Earlier frozen features and MAE reproduced on 43 original multitimeframe transitions and 16 common 1H starts.
- No production imports, network candles, messages, orders, collector changes, or restarts.
- `replay.py`, `quality.py`, `collectors.py`, `supplement.py`, `figures.py` — calculations; `candidate_core.py`, `candidate_helpers.py`, `test_candidate.py` — candidate and checks; `metrics.csv`, `variant_changes.csv`, `fixed_collectors_summary.csv`, `waves_8pct_summary.csv`, `shift_null.csv`, `block_ci.csv` — results; `manifest.json` — source/output hashes.

Limitations: a new code audit is not an independent audit by another AI; 75/30 windows sample-check the accelerated implementation, rather than independently proving every line of each of 51 009 ticks; the neutral proxy is conditional; baselines update at different rates; the long history was already inspected; the derivatives sample is small. Within these checks, the conclusion that a targeted fix does not rescue the earlier idea is robust.
