# 07 — BOS: A Structural Scanner, Not a Predictor

**Author:** Oleg Arefev
**Published:** September 2026
**Status:** `Open` — core structural detection (swing / BOS / impulse) is closed and in production use; an options/gamma overlay on top of it is still being tested, with a decision point at the end of September 2026
**Class:** Author's own system, described conceptually, not literature-tested — like Note 06, this is an account of a system built first and checked against the literature after, not a review of someone else's paper. A standalone lab within the *Searching for Edge* project, sitting alongside Klines rather than inside it — distinct from *System 2 — Trend Catcher* (the not-yet-started trend component of Klines itself, tested on grind-style pairs such as BNB, TON, ACE), which remains on the horizon.

**Research question:** Note 06 (Klines) catches one specific shape of event — a sudden, detectable volume spike — and is structurally blind to a slow, grinding continuation move in an already-liquid name, the exact gap Note 06 names in its closing section. This note is the system built to cover that gap: can a change in price structure (a break of a prior confirmed swing high/low) be detected causally, tracked while it persists, and separated early enough from noise to be useful — even without a proven directional predictive edge? *Detection is not prediction*, and this note does not blur that line to make the result sound better than it is.

---

## 1. Built first, checked against the literature after

The starting point was classic technical-analysis vocabulary: RSI, a weighted bull/bear state index. That was dropped quickly for a specific reason, not a vague one — it only ever described what had *already* happened. Useful as a snapshot, useless as anything forward-looking.

The next step was structure itself: swings, break of structure (BOS), change of character (CHoCH) — the Smart Money Concepts / price-action vocabulary associated with Murphy, Elder, and ICT-style structural trading. This is also, honestly, descriptive rather than predictive: a BOS is confirmed *after* the break happens, not before. What it does give is an earlier, more mechanical read on structure than eyeballing a chart — a scanner, not an oracle. Everything that didn't survive a direct empirical check (see §6 below) was removed; what's left is a single BOS core, applied identically across three timeframes, plus an active search for something — anything, empirically shown, not assumed — that can sit on top of that descriptive core as a leading signal.

## 2. What BOS actually is

Three definitions, not a vague description of "structure." These are the literal formulas the system runs, not a paraphrase of them.

**Swing (structural extreme)** — not any local peak, but one filtered by volatility and volume:

```python
# bar i is a swing high if all of the following hold:
High[i] >= max(High[i-2 : i+3])
(High[i] - EMA50[i]) > 0.7 * ATR[i]
Volume[i] > 1.05 * VolumeMA20[i]
# swing low — mirrored on Low/EMA50
```

**Causal BOS** — a break of the last *confirmed* swing, with a confirmation lag (`SWING_LAG = 2` bars) so the detector never looks into the future relative to its own confirmation rule:

```python
cutoff = t - SWING_LAG
BOS_up   = Close[t] > last_confirmed_high * 1.001
BOS_down = Close[t] < last_confirmed_low  * 0.999
# the event is the first bar of a run, not every bar the flag stays set
```

**Impulse state machine** — a state persists between its start and its structural break; nothing here votes or averages across timeframes. 1D/4H/1H are each computed independently by the same function:

```python
# BOS                        -> impulse STARTS
# same-direction BOS         -> extends it, anchor is not reset
# close beyond the last
# confirmed opposing pivot   -> impulse ENDS
# opposite-direction BOS     -> impulse ENDS, a new one starts
```

The full implementations (`_detect_swings`, `find_all_bos`, `compute_impulse`) aren't published in full — see §11 — but these are the actual definitions the system runs, not a marketing description of them.

## 3. The methodology discipline applied

Nothing here was accepted just because it produced a chart that looked convincing. Early 30m/1H/4H structural detector candidates were measured against four honest metrics before anything was kept: **lead time** (how much earlier a layer catches the start of a move), **coverage** (what fraction of real waves it catches at all), **false positive rate** (how often it fires outside a real wave), and **drawdown-to-confirmation** (how far price runs against the signal before it's even confirmed). Some candidates survived as *observational tools* — useful for watching what's happening — but were rejected as *trading rules*, because signal quality for a mechanical entry/exit wasn't there.

Measured against 134 real BTC waves of 8%+ (2022–2026, hourly grid) and against the full causal history of the BOS detector:

| Layer | coverage | detection lag (median) | remaining move at detection | events/year | −4% stop triggers before structural break |
|---|---|---|---|---|---|
| 1H | 93% | 35h | 65% | 361 | 5% |
| 4H | 72% | 101h | 46% | 102 | 19% |
| 1D | 26% | 262h | 28% | 16 | **58%** |
| 30m (candidate detector) | 100% | 13h (median from wave start) | 77% | ~172 | — |

The 30m candidate gives a median **15-hour** lead over 1H BOS (105 of 135 waves, sign-test p≈6×10⁻¹¹) — at the cost of a **44.8% false-positive rate** (a firing outside any real 8%+ wave in the same direction). That's why it stays a supplementary line in the output, not a standalone trading rule: the signal is real, but too noisy for a mechanical decision on its own.

## 4. What this was tested on

No paid or closed datasets — ordinary Binance historical candles, pulled through the free public REST endpoint (`GET /klines`), paginated 1000 bars at a time. Anyone can re-pull the same data.

- **`BTCUSDT_1d_history_full.csv`** — 1,693 daily bars, 2022-01-01 → 2026-08-20. Main series for the 1D layer and most of the internal lab history.
- **`BTCUSDT_1h_history_full.csv`** — ~40,622 hourly bars, same period. Base for the 134 reference waves (8%+, hourly zigzag) and for the causal 1H BOS series.
- **`BTCUSDT_1h_history_2025_2026.csv`** — a narrower 7,023-bar slice, used in an early lead-time measurement before the full 4.5-year run existed — kept separate so it isn't confused with the full history when reproducing results.
- **`BTCUSDT_30m_2022.csv` / `_2023.csv` / `_2024_2026.csv`** — 30-minute bars, joined into one continuous series 2021-12-31 → 2026-08-28 (81,644 bars), built specifically to test the 30-minute detector against real wave starts and 1H BOS (the table above).
- **`BTCUSDT_1d_2022_trend_cross.csv`** — an older daily slice from an early trend-cross experiment; historical, not used in current conclusions, kept as-is without retroactive cleanup.

Thresholds (the 8% wave definition, the 30m detector's +3.1%/−2.8%/±1.5% levels, `SWING_LAG = 2`) were fixed **before** looking at the result and never adjusted afterward to improve a number — the same non-negotiable discipline applied everywhere else in this repository.

## 5. What's actually proven and in use — not just "nothing found"

- **Level held / lost** — the cleanest separator found so far: whether a structural level is still held by day 5 splits outcomes 38% vs. 94%. No parameters, no fitting.
- **Stop-loss** — introducing a −4% stop moves expectancy from 2.53x to 12.63x.
- **MAE** (Maximum Adverse Excursion) separates outcomes early; MFE does not.

## 6. What's rejected — stated plainly, not buried

- Predicting BOS direction from prior bars — correlation 0.009, a genuine negative result.
- The 30-minute detector as a standalone core — real early warning (~15h median lead on 1H BOS), but ~45% false positives; not enough for a signal on its own.
- Max pain (the popular options-positioning heuristic) — mixed on a preliminary check, not built in.
- Timeframe divergence (1H vs. 4H vs. 1D) as a predictor — did not hold up.
- Time-to-confirmation, exhaustion (reverse-sign), the "RUN" concept, a "method 3" entry (identified as post-hoc and specifically removed for that reason), and Path Quality as a separate layer.

## 7. What's still open — neither rejected nor built in as a rule

- **Path continuity** — sign-test 21/24, p=0.0001. Status: promising, not validated. Needs an honest out-of-sample check before it becomes anything more.
- **The BOS → 1H-confirm → 4H-align chain** — a small but statistically real effect (p=0.012 on move magnitude, p=0.077 on remaining MFE). Too small to build an entry/exit rule on, but not noise either.

Both are exactly the kind of candidate this series is built to name honestly as "we don't know yet," rather than force to a premature yes or no.

## 8. The literature check — named, not gestured at

The same check Note 06 ran against its own volume-spike detector was run here, on a different question: does the shape of a price path — not just its magnitude — carry information about what happens next, and can an observable "trend broke" state ever be told apart from noise? Fourteen papers were screened; the ones that changed how this system's own open questions (§7) are read are named below, split by what they actually establish.

**Whether the internal shape of a price path — not just its size — predicts continuation:**

- Da, Gurun & Warachka (2014), *The Review of Financial Studies*, 27(7) — "Frog in the Pan." Two stocks with the same 12-month cumulative return show very different subsequent momentum depending on whether that return arrived smoothly (many small days) or in a few large jumps: momentum stays significant for ~8 months after a continuous path, and disappears after ~2 months following a discrete one. U.S. equities, 1976–2007 (extended sample from 1927). Does not define a formation start or a real-time termination rule for an individual trend — it's a cross-sectional conditioning result — but it's the foundational academic result behind the idea that path shape matters at all. Independently arrived at the same conclusion this system's own path-continuity hypothesis (§7) is testing on BTC specifically.
- Kim (2026), SSRN — "Price Path Continuity and the Cross-Section of Cryptocurrency Returns." The direct crypto-native follow-up to Da/Gurun/Warachka: broad crypto cross-section, Jan 2020–Apr 2026, survivorship-bias-mitigated via historical CoinMarketCap snapshots. A 14-day Rank-Weighted Price Path Continuity (PPC) measure interacts positively and significantly with past return — the winner-minus-loser spread nearly disappears among discrete-path coins and becomes large and significant among continuous-path coins (~1.16%/week difference-in-differences). A 2026 preprint, not peer-reviewed; cross-sectional, not a single-asset time-series or real-time episode model, and doesn't resolve formation/termination of an individual trend — but it's the closest published match to what §7's path-continuity result is actually asking about BTC specifically.
- Borgards (2021) — "Dynamic Time Series Momentum of Cryptocurrencies." Directly relevant to the impulse state machine in §2: after a first directional price cycle, additional cycles in the same direction often follow — more so in crypto than in the S&P 500 benchmark, across 1D/1H/5m. Formation → continuation → termination is modeled explicitly (a cycle ends when the higher-high/higher-low, or lower-high/lower-low, sequence breaks), and the paper separately shows the probability of another continuation cycle *declines* as more cycles pass — momentum isn't modeled as an infinitely stable state, which matches this project's own refusal to treat an active impulse as guaranteed to continue. 20 cryptocurrencies on Bitfinex, mostly 2014–2019; turning points depend on a smoothing-filter sensitivity parameter, so "no arbitrary threshold" doesn't mean "no parameterization."

**Whether a trend's end can be told apart from noise while it's happening:**

- Goulding, Harvey & Mazzoleni — "Momentum Turning Points" and "Breaking Bad Trends" (companion papers). Define an established trend as agreement between a slow and a fast trailing-return signal (both positive = bull, both negative = bear), and a turning point as *disagreement* between them (Correction / Rebound). This is the closest published analogue to this project's own impulse-ends logic — an observable intermediate state between "trend confirmed" and "opposite trend confirmed." The authors are explicit, and this matters directly for §7: *observing* a turning point does not mean the trend has actually broken — it can just as easily be noise the fast signal overreacted to. U.S. equities 1969–2018 plus 20 international markets (first paper); 43 futures markets 1990–2022 (second paper), which also shows deterioration in static trend-following performance is linked to the frequency of these disagreement states rising after 2009. Neither paper resolves "is this a temporary correction or the real end of the trend" — which is exactly the open question this project's own path-continuity work is circling from a different angle.

**Whether momentum/trend continuation is a stable phenomenon at all, or something narrower:**

- Liu & Tsyvinski, "Risks and Returns of Cryptocurrency" (NBER WP 24877, 2018; *Review of Financial Studies*, 2021) — the foundational time-series momentum result in crypto: Bitcoin's own current return predicts its own future return at short (1–7 day, 1–4 week) horizons, strongest around 1–3 weeks. The authors' own limitations matter here: the effect is irregular across horizons (not monotonic day-to-day), weakens under bootstrap inference at several lags, explains very little variance (R² typically 0–5%), and — most relevant to this note — the paper does not build a turning-point detector, a deterioration state, or an episode-level definition of when momentum ends. It establishes *that* short-horizon predictability existed in 2011–2018, not *how* an individual trend develops or breaks.
- Dobrynskaya (2021/2023), *Journal of Alternative Investments* — shows the sign of the effect flips with horizon: momentum is strongest under ~2 weeks, and reverses into a statistically significant, growing reversal effect beyond ~4–6 weeks. Directly cautions against treating "crypto has momentum" as a single stable fact independent of horizon specification — consistent with this project's own closed result that BOS direction has no proven predictive edge on its own (§6).
- Grobys, Kolari, Sandretto, Shahzad & Äijö (2025), *Financial Markets and Portfolio Management* (Springer) — shows plain cross-sectional crypto momentum on a top-30 large-cap universe is highly sample- and tail-sensitive: positive and weakly significant in 2016–2020, insignificant afterward, and a single idiosyncratic coin crash in one week accounts for roughly 37% of the full-sample return swing. Reinforces, from a completely different data cut, why this project treats a raw directional signal as unproven rather than assumed.

**Deterioration and forced-flow events, and why a universal early-warning signal shouldn't be assumed:**

- Garcia Seuma (2026), arXiv:2607.27070 — already cited in Note 06 — finds no single early-warning variable precedes all seven studied BTC perpetual liquidation cascades (2022–2025); price shows the expected pre-cascade signature in five of seven, but is silent ahead of two sudden-news shocks. The one regularity that does hold across events (a compression in taker order-flow variance) works at the population level, not as a reliable per-event alarm. Cited again here because it's the direct caution against assuming this project's own liquidation and forced-flow data collection (§9) will produce a clean, universal deterioration signal just because the theory sounds plausible.
- Gervais, Kaniel & Mingelgrin (2001), *The Journal of Finance* — also cited in Note 06 — abnormal trading volume carries return-relevant information distinct from the contemporaneous price move itself. Cited here as background for why volume/leverage data (§9) is worth collecting at all, not as validation of any specific BOS-adjacent rule.

**The honest summary of this check:** none of the above validates that a BOS predicts direction — the project's own §6 result on that stands. What the literature does support, independently and repeatedly, is that the *shape* of a price path and the *persistence* of a directional signal carry information beyond raw magnitude — and that telling a real structural break apart from noise, in real time, is an open problem nobody in this literature has fully solved either. That's the actual reason this system stays a scanner rather than an autonomous predictor, and why §7's open questions are being tested rather than assumed either way.

The full reference list, with status tags for every paper reviewed (including the ones that didn't change anything above), is in [reference-3-price-structure-momentum-literature.md](reference-3-price-structure-momentum-literature.md).

## 9. What's being collected now

Four independent raw data streams, each recorded without interpretation at collection time. All sources are public and free (Binance, Deribit) — no API keys or tokens live in this repository.

**Price / BOS structure** — Binance 30m/1H/1D candles, the swing/BOS detector from §2 running on top. The core of the system, the only part that's completed the full validation cycle above.

**Forced flow (liquidations)** — Binance Futures forced-liquidation stream, recorded as-is: side, price, quantity, notional, without any derived "strength" signal.

**Leverage (funding + OI)** — Binance Futures funding rate and open interest, on a fixed polling grid.

**Options (gamma + trade tape)** — Deribit BTC options: gamma-exposure snapshots across the near-the-money chain (call/put kept separate, no artificial net sign), and a trade-tape stream with taker direction, raw IV, strike, and expiry — the columns exist to avoid losing free data, without implying any of it has been validated as predictive yet.

## 10. Open question right now

Does positioning in the options market (gamma concentration, funding, liquidations) provide a leading signal on top of the already-validated BOS core — a "gas pedal" on continuation, or a "brake" on exhaustion?

Unresolved. Data has been accumulating since late August 2026. A test date is fixed in advance: **end of September 2026**, with two joint criteria — at least ~3 weeks of continuous history across every layer, and at least one real episode of price breaking out of the current range, not elapsed time alone.

The result gets published either way, including a negative one. If no "pedal" is found, the BOS scanner stays exactly what it already is: something that shows structure, not something that predicts the future.

## 11. Why not the full code

The collectors above are simple REST/WebSocket plumbing — nothing hidden in the logic. They aren't published in full for two reasons: part is configured against personal infrastructure (paths, environment), and part is a working hypothesis still being checked, not something that should be shown as a finished method prematurely. The actual content of this project — the lab methodology, the sign-tests, the frozen thresholds, and the honestly-listed failures above — is what gets published alongside the test result in §10, regardless of outcome.

## 12. Verdict

On the same bars this series applies to published strategies — a plausible mechanism, independent convergence with unrelated literature, and metrics measured before being trusted rather than after — the BOS core clears them as a *descriptive, causal structural scanner*. It does not clear the bar for a standalone predictive trading signal, and it isn't presented as one. The open question in §10 is exactly that: whether something else, layered on top, can turn a working scanner into something with a leading edge. That question has a fixed test date, not an indefinite one.

---

## References

- Da, Z., Gurun, U. G., Warachka, M. (2014). "Frog in the Pan: Continuous Information and Momentum." *The Review of Financial Studies*, 27(7).
- Kim, S. (2026). "Price Path Continuity and the Cross-Section of Cryptocurrency Returns." SSRN.
- Borgards, O. (2021). "Dynamic Time Series Momentum of Cryptocurrencies."
- Goulding, C., Harvey, C. R., Mazzoleni, I. "Momentum Turning Points." SSRN.
- Goulding, C., Harvey, C. R., Mazzoleni, I. "Breaking Bad Trends." SSRN.
- Liu, Y., Tsyvinski, A. (2018/2021). "Risks and Returns of Cryptocurrency." NBER Working Paper 25882; *The Review of Financial Studies*, 34(6).
- Dobrynskaya, V. (2021/2023). "Cryptocurrency Momentum and Reversal." *Journal of Alternative Investments*, 26(1), 65–76.
- Grobys, K., Kolari, J., Sandretto, R., Shahzad, S., Äijö, J. (2025). "Cryptocurrency Momentum Has (Not) Its Moments." *Financial Markets and Portfolio Management* (Springer).
- Garcia Seuma, R. M. (2026). "Where Does the Criticality Live? Early-Warning Signals Are Event-Heterogeneous Across Seven Crypto-Perpetual Liquidation Cascades." arXiv:2607.27070.
- Gervais, S., Kaniel, R., Mingelgrin, D. (2001). "The High-Volume Return Premium." *The Journal of Finance*, 56(3).

**Note on abstracts vs. this note's use of them:** each summary above reflects the paper's own stated finding and horizon, not a claim that the paper validates this system directly. Where a paper's asset class, universe, or holding horizon differs materially from this system's (equities vs. crypto, weeks vs. hours, cross-sectional vs. single-asset time series), that difference is stated explicitly rather than glossed over. The full screening — including papers that didn't change any conclusion above — is in [reference-3-price-structure-momentum-literature.md](reference-3-price-structure-momentum-literature.md).

---

**Author:** Oleg Arefev
**Project:** [Searching for Edge](https://github.com/Silent47boryara/searching-for-edge)
**Repository:** [Silent47boryara/searching-for-edge](https://github.com/Silent47boryara/searching-for-edge)
