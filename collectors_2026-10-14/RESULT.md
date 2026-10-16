# Collectors without BOS: individual feeds and combinations

**14.10.2026 · Codex. First bounded test completed. BOS was not used as a feature, filter, or event time. Production was unchanged.**

## Answer to the research question

**Useful information can be extracted, but its type must be named precisely.** Liquidations + OI describe current contraction/growth in open positions; funding defines perpetual holding conditions; option flow and liquidations reflect current stress. These are observable facts, not established profitability of trading decisions.

In tests of incremental forecasting value beyond price/volatility over the next 4 hours, **neither an individual feed nor a selected combination showed stable improvement**. Some small positive numbers exist, but intervals include zero and results differ by week. This concerns the chosen definitions, sample, and simple diagnostic regression; it does not prove that the data have no possible use.

The most useful immediate application is an explicit map of observable regimes, without BUY/SELL labels. The two predictive leads below remain questions for testing, not reasons to rebuild everything or stop collecting data.

## 1. Tests and data

`PROTOCOL.md` was saved before calculating results. Five feeds: OI, funding/mark, liquidations, gamma, and option tape. Full mark-data period: **29.08.2026 11:28 — 14.10.2026 00:00 UTC**, approximately 45.5 days. All times below are UTC; add 3 hours for Moscow.

Price is **Binance mark price** from the collector itself, consistently sourced throughout. It was not mixed with the shorter spot-candle series from earlier laboratories. 3 690 373 messages were reduced to minute closes. Of 65 552 minutes, 61 333 passed the completeness criterion. Initial incomplete windows and gaps were excluded.

Fixed features:

| Feed | Features available by T |
|---|---|
| OI | log(OI(T)/OI(T−4h)); both endpoints no older than 15 minutes |
| Funding | Last rate received before T, age ≤60 seconds |
| Liquidations | log(1+USD over 4h), imbalance (short_liq−long_liq)/total |
| Gamma | Unsigned asymmetry within ±5% of spot; log(1+total gamma in the band) |
| Tape | log(1+option notional over 4h); (signed call notional−signed put notional)/total notional |

Predefined combinations: OI+funding, OI+liquidations, OI+tape, funding+liquidations, gamma+tape, liquidations+tape, all five. Pairs include individual features and predefined products, without searching optimal thresholds.

Primary outcomes: next-4-hour return and next-4-hour realised volatility from minute mark-price changes. Decisions occur every 4 hours, making primary future windows non-overlapping. Future information is used only in evaluation, not features.

**Controls:** past 1h/4h returns and past 4h/24h volatility. Each combination is compared against price on **the same rows and dates**, preventing more complete data from giving a model an artificial advantage.

The diagnostic model is standardised Ridge(alpha=10), without parameter tuning. The first 14 calendar days initialise training, followed by weekly tests with expanding training. Training outcomes must already be known at the test week's start. At least 36 training rows and 8 test rows per weekly block are required. There are 24 primary tests (12 feature sets × 2 outcomes), with paired daily block bootstrap and sign-flip tests, and Holm correction across all 24.

**This is neither a trading strategy nor untouched OOS:** historical data were already inspected in other studies. It tests transfer of a fixed way of using data to subsequent weeks within the available period. A linear model with interactions does not exhaust all possible applications.

## 2. Availability time and quality: important differences from earlier laboratories

1. **Tape:** trades must have both exchange time ≤T and receive time ≤T. A late backfill is not treated as known in the past. Raw tape median delay is about 9 seconds, 90th percentile about 24 minutes, and 99th about 15 hours. Some reflects known problems/backfills; these quantiles do not imply a constant delay across the entire tape.
2. **Gamma:** snapshot timestamps precede requests. Availability was reconstructed from collector-log `snapshot ok` messages after CSV writes, matching timestamp and rounded spot. Raw data yielded 6654 snapshot group-parts; confirmation of successful completion retained 5275 observable snapshots. Unmatched observations were excluded. Median completion delay is 17 seconds, p99 about 159 seconds, maximum matched delay about 17.6 minutes. This avoids taking an unfinished snapshot at an hourly boundary.
3. **Liquidations:** new masks use disconnect/reconnect and heartbeat gaps >15 minutes, yielding 207 merged windows. Silence with a live heartbeat means zero events, not an error. Feature windows require ≥90% valid time.
4. **Tape:** the 02.10 00:00 — 06.10 23:05 exclusion remains; heartbeat gaps are used after retained logs begin. Rotations before 14.09 13:59 are no longer available: earlier audits and conservative shared funding outages were used. This limits verification of delivery in early tape history, rather than proving its complete reliability.
5. **Gamma:** the major gap 02.10 10:10 — 06.10 23:10 remains; after recovery, only actually completed, fresh snapshots are allowed. The old unconditional exclusion of all post-gap data was not extended forever.
6. **Mark:** missing minutes were not filled; volatility was not calculated across a gap. Past/future windows require ≥90% valid minute returns; missing does not become zero volatility.

On the hourly grid: 977 OI values, 1029 funding, 953 liquidations, 778 gamma, and 895 tape. Requiring complete price, past volatility, future outcome, and chronological training leaves **51–119 test four-hour windows**, covering 14–25 distinct days. This is the main confidence limit.

## 3. What the feeds already show

### Liquidations: measuring current forced closures

On non-overlapping 4h observations:

- Liquidation activity ↔ volatility already realised within those 4h: Spearman **0.82**.
- Liquidation imbalance ↔ price direction within those 4h: **0.64**.

This is a meaningful contemporaneous relationship. It **does not mean** liquidations were known before the decline/rise. Price itself already contains much of this information. The raw relationship between activity and future volatility, 0.46, falls to approximately 0.04 after controlling for past price/volatility in a partial-rank diagnostic.

Compared with a price chart alone, the feed directly shows forced-closure events and their side. Binance forceOrder does not represent every market liquidation: the exchange limits snapshot delivery. [Binance documentation](https://developers.binance.info/docs/derivatives/usds-margined-futures/websocket-market-streams/All-Market-Mini-Tickers-Stream).

### OI + price + liquidations: four distinct states

| Observation | What is known | What does not follow |
|---|---|---|
| Price down, OI down, long liquidations dominate | Net reduction in open contracts and observed forced long closures | Sellers are exhausted or a rebound starts now |
| Price down, OI up | Net growth in open contracts alongside a decline | Specifically shorts were opened: each contract has two sides |
| Price up, OI down | Rising price with net contraction of contracts; short liquidations may add context | The entire rise is explained by a short squeeze |
| Price up, OI up | Rising price and open-contract count | The move must continue |

All four regimes appear: 51 / 56 / 66 / 55 complete observations for price_down/OI_down, price_down/OI_up, price_up/OI_down, price_up/OI_up respectively. These are descriptive Ns, not independent confirmations or equal denominators for future outcomes.

**Illustration selected after inspection, not strategy evidence:** on 08.10 at 16:00, mark price fell approximately **1.77%** over the preceding 4h and OI **2.38%**; the feed recorded about **$51.4 million** in liquidations, imbalance −0.90 (about 95% of notional from long liquidations). Price rose approximately 0.89% over the next 4h. In another case, 07.10 at 04:00, price fell 1.65% while OI **rose** about 1.06%, with long liquidations dominant. The next 4h were almost unchanged. The combination distinguishes observed positioning states; it gives no universal conclusion about the next move.

### Funding: holding conditions, not a discovered direction forecast

Funding helps account for the potential cost/income of holding perpetuals and observe changing premiums. Positive rates are paid by longs; negative rates by shorts. The live rate may change before settlement. [Binance: funding fees](https://www.binance.com/en/academy/glossary/funding-fees).

In our forecasting comparison, adding funding to price did not improve direction forecasts in subsequent weeks. This does not make the rate useless for cost accounting. “High funding means it is time to short” was not confirmed.

### Option tape: stress activity, with caution about sign

Tape activity ↔ current volatility: **0.76**; flow imbalance ↔ current direction: **0.28**. Controlling for price leaves activity's association with future volatility around 0.28 in a descriptive partial correlation, but no stable weekly forecasting improvement emerged.

**53.3% of notional** is block/combo/RFQ. The public endpoint defines direction as the taker side, not observed dealer inventory or hedge. Individual legs of complex trades are not independent directional bets. [Deribit API](https://docs.deribit.com/api-reference/market-data/public-get_last_trades_by_currency). Amberdata's research published by Deribit separately discusses aggressor-direction interpretation and the “taker=trader, maker=dealer” assumption. [Primary source](https://insights.deribit.com/industry/decoding-option-flows-q2-2023/).

### Gamma: an unsigned concentration map, not a hedging sign

Snapshots describe sensitivity across strikes. This may provide context for observing levels, but executable trading at individual gamma walls was not tested here. Gamma×OI does not reveal dealer-position signs. Neither movement direction nor magnitude follows unambiguously from “large gamma”. Only fixed asymmetry/total within ±5% were tested, not every use of the option chain.

## 4. Primary forecasting results in subsequent weeks

Figures are **percentage changes in forecast MSE relative to the price/volatility-only model**, expressed as improvement: positive is better, negative worse. They are not returns or increases in win rate. Each feature set has its own complete available observations, so the ranking is not an identical-sample tournament.

| Addition to price | Next-4h return: error improvement | Next-4h volatility: error improvement | Test N: return / volatility |
|---|---:|---:|---:|
| OI | +0.3% | −0.9% | 118 / 119 |
| Funding | −2.0% | −1.1% | 118 / 119 |
| Liquidations | −1.9% | −2.0% | 117 / 118 |
| Gamma | −3.9% | +2.2% | 52 / 53 |
| Tape | −0.4% | −2.9% | 92 / 93 |
| OI + funding | −2.0% | −2.0% | 118 / 119 |
| OI + liquidations | +1.8% | −3.5% | 117 / 118 |
| OI + tape | −0.4% | −8.0% | 92 / 93 |
| Funding + liquidations | −5.9% | −2.7% | 117 / 118 |
| Gamma + tape | −3.8% | **+9.8%** | 52 / 53 |
| Liquidations + tape | −1.3% | −7.1% | 91 / 92 |
| All five | −3.3% | −8.5% | 51 / 52 |

**None of the 24 primary tests is significant even under the naive one-sided daily sign-flip before correction; all Holm-adjusted p-values are 1.** This is not the probability that no effect exists, nor a conclusion of a truly zero association. Positive results have wide intervals and vary across weeks.

The two most notable positive results:

- **OI + liquidations, future return:** +1.8%, interval approximately **[−5.3%; +6.8%]**, better than baseline in **2 of 5** weekly blocks. On the same complete sample, the pair beats OI alone by about 1.5% and liquidations alone by 3.6%, but those intervals also include zero.
- **Gamma + tape, future volatility:** +9.8%, interval **[−9.0%; +24.7%]**, **53 observations / 14 days / 3 blocks**, better than baseline in 2 of 3. Excluding block/combo/RFQ changes the result to **−1.2%**. This cannot be called “aggressive flow predicts risk”: it depends on tape composition and did not pass the stability check.

The joint all-five model does not beat price. This does not mean “more data always makes things worse”; it shows that mechanically combining features does not automatically add information in a small sample.

## 5. Threshold events and comparisons with similar market moments

Thresholds use only the first 14 days and then remain fixed. High liquidations means the initial activity's upper decile, about $11.8 million/4h. High tape is about $503 million/4h. These are relative discovery thresholds, not recommended signal settings.

| Event after the initial period | N / days | Median absolute next-4h move | Price/volatility-matched controls |
|---|---:|---:|---:|
| Large liquidations | 16 / 10 | 0.52% | 0.37% |
| Large liquidations + OI decline | 12 / 7 | 0.52% | 0.37% |
| High tape activity | 21 / 12 | 0.42% | 0.35% |
| Large unsigned gamma in the band | 14 / 6 | 0.25% | 0.37% |

These are descriptive hints, not independent confirmations: few days, potentially reused controls, and no strict matching-quality caliper. For example, median future RV after large liquidations is 0.67% versus 0.65% for matched controls—almost identical. OI-down+liquidations gives 0.67% versus 0.67%. Selecting one convenient metric does not establish an edge.

Another predefined regime—price down / OI up / funding below the initial bottom decile—occurred 19 times across 11 days. Median next-4h return was −0.12% versus +0.16% for controls. But the funding threshold is **+0.0027244%** (positive!), not universally “extremely negative funding”; it reflects the initial period and regime change. This is not a discovered short rule. The opposite regime, high funding with price/OI rising, occurred only once; it cannot be evaluated.

24h correlation diagnostics are also saved (`descriptive_correlations.csv`), but their windows overlap, and they were not used to select a favourable horizon after the negative 4h result.

## 6. What can be extracted, and what cannot be promised

**An observation card can already be built from the existing fields: price/volatility + OI change + actual liquidation side + funding conditions + tape activity/composition.** It distinguishes measured processes and helps formulate questions: is leverage closing, are new contracts appearing, are forced closures occurring, how reliable is option flow, and what does holding cost?

Its decision value has not been measured. It cannot automatically be called a profitable radar or proven advance warning. Strong contemporaneous relationships do not themselves add early detection.

**Justified focused research directions, not another queue of searches:**

1. OI/liquidation descriptive regimes: test whether they add information about recovery/continuation after comparable price moves. The current 12–19 events define the question, not a rule.
2. Option-risk context: first distinguish ordinary and structured trade interpretation and respect actual receive times. Do not add every leg into a supposedly dealer-specific flow. Changing the interpretation does not authorise changes to collectors.
3. Keep protocols/definitions frozen while collecting new events. Subsequent weeks are not independent confirmation if rules change again after inspection.

This work does not recommend shutting down the feeds. It maps what they already measure and the boundary between current context and an unestablished predictive edge.

## 7. Checks and preservation

`checks.py`: PASS — year/time uniqueness, imbalance bounds, gamma completion before T, independent future-RV recalculation, independent tape join on exchange+receive times, 24 tests, unique predictions, MSE recalculation, and unchanged bot_v2.py.

Artifacts: `PROTOCOL.md`, `build.py`, `analyze.py`, `checks.py`; `hourly_features.csv`, `model_results.csv`, `pair_vs_components.csv`, `screen_tape_sensitivity.csv`, `descriptive_correlations.csv`, `event_summary.csv`, `event_cases.csv`, `data_qa.json`, `forward_comparison.png`, `unwind_example.png`, `manifest.json`.

Collector code, processes, and original CSVs were unchanged. No new market-data downloads, orders, or messages. Financial-mechanics checks used official documentation; calculations used local data only. No independent audit by another AI has yet been conducted.
