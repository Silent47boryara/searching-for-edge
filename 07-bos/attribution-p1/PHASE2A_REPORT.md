# Phase 2A — BOS × derivatives: exploratory attribution

Date: 2026-10-07. All accompanying tables, charts, and intermediate files are in `out/phase2a/`. Conclusions: **EXPLORATORY / INSUFFICIENT FOR CONFIRMATION**; the term `VALIDATED` is not used. Phase 2B and optimization have not started; `bot_v2.py` has not been changed.

Workflow: the plan was fixed first ([PREREG.md](out/phase2a/PREREG.md): events, definitions, primary family, status rules), followed by calculation of outcomes, features, and tests. Scripts: `scripts/20…26_*.py`.

## 0. Brief findings

| Question | Answer |
|---|---|
| **A.** What happens on average after 1H/4H BOS and transitions? | No stable directional pattern. Median direction-normalized returns over 1–72 h are within ±0.5% (down to −1.2% for 4H starts and alignment restoration, N=6–7); continuation rates are 40–70% without a consistent pattern; typical MFE/MAE24 (+1.0…+1.4% / −0.9…−1.3%) are close to unconditional values (+1.05% / −1.03%). There is a hint of a pullback a day after 4H starts (median −1.18%, N=6, 3 clusters), insufficient for a conclusion. |
| **B.** Does any derivatives layer meaningfully distinguish outcomes within the same BOS context? | **Two candidates, both fragile.** 1) Aggressive options flow (tape) over the 12 h before a 1H start is an `INTERESTING CANDIDATE` under the preregistered rule (n=14, ρ=+0.62 with MAE24, Holm 0.196). 2) Unsigned gamma asymmetry at multi-timeframe transitions is a robust post-hoc result (n=36, ρ=−0.58 with MAE24), but it is secondary and cannot qualify as a candidate under the rule. OI, funding, and liquidations are `NO EFFECT` or `WEAK / INCONSISTENT`. |
| **C.** Is there anything meaningful in the 7 entries into `1D BULL / 4H NONE / 1H BEAR`? | Structurally, yes (see §4); for derivatives, `INSUFFICIENT DATA`: the only actual loss of 1D (15.09) has almost no derivatives data because of machine downtime, and in two cases the outcome is not yet available. |

Essential statistical caveats: the window contains two 1D regimes (both BULL) plus a 3-day pause; all events are nested within these regimes. There were 272 tests in total (204 with n≥8), with 20 naive p<0.05 results at n≥8 versus ~10 expected by chance.

## 1. Data, events, rules

The frozen Phase 1 masks and causal join were used (OI ≤15 min, funding ≤60 sec, gamma ≤20 min; liquidations use the v2 mask with window coverage ≥90%). Exclusions: gamma 02.10 10:10 → 06.10 23:10; tape 02.10 00:00 → 06.10 23:05. OI backfill was not mixed in; `level_lost_5d` was not used.

| Event family | N | 1D clusters (regime #1 / pause / regime #2) | BULL/BEAR |
|---|---|---|---|
| F1: 1H episode starts | 17 | 10 / 1 / 6 | 8 / 9 |
| F2: 4H episode starts | 6 | 4 / 1 / 1 | 4 / 2 |
| F3: multi-timeframe transitions | 43 | 23 / 4 / 16 | 41 / 2 |
| 1H ends / 4H ends | 16 / 6 | 9+1+6 / 3+1+2 | |
| Loss / restoration of full alignment | 7 / 7 | 3 / 4 | 7 / 0 |
| 1H starts against active 1D | 9 of 17 | | |

There are 3 independent 1D clusters across all families (one consists of a single event). Every result below is labeled `EXPLORATORY / INSUFFICIENT FOR CONFIRMATION`.

Direction `s`: episode direction for episodes; active 1D direction for transitions (otherwise 4H, otherwise 1H). For 41 of 43 transitions, `s=+1`, so F3 effectively describes a BULL context; the BEAR side of transitions cannot be analyzed (N=2).

## 2. A — baseline outcomes (tables: `A_baseline_outcomes.csv`, `A_km_durations.csv`)

Direction-normalized return `R_h = s·(P(T+h)/P(T)−1)`, median, % (N with a complete horizon is shown in parentheses). Unconditional drift across all hours of the window: +0.009 / +0.038 / +0.070 / +0.064 / +0.019 / −0.019 % for h = 1/4/12/24/48/72 (with `s=+1`).

| Family (N / clusters) | 1h | 4h | 12h | 24h | 48h | 72h |
|---|---|---|---|---|---|---|
| 1H starts (17 / 3) | +0.02 | −0.03 | +0.07 | −0.10 | −0.17 | −0.47 |
| 4H starts (6 / 3) | +0.11 | +0.45 | −0.07 | −1.18 | −0.84 | −0.35 |
| Transitions (43 / 3) | −0.05 | +0.10 | −0.04 | −0.14 | −0.20 | −0.15 |
| 1H ends (16 / 3) | +0.02 | 0.00 | −0.34 | −0.35 | −0.05 | +0.19 |
| 4H ends (6 / 3) | 0.00 | +0.05 | −0.07 | +0.10 | −0.29 | −0.44 |
| Alignment loss (7 / 2) | −0.05 | +0.01 | −0.13 | −0.21 | −0.12 | −0.25 |
| Alignment restoration (7 / 2) | +0.05 | +0.33 | −0.39 | −0.54 | −1.14 | −0.77 |

Continuation rates (`R>0`): 1H starts 53 / 47 / 69 / 44 / 44 / 47 %; transitions 44 / 60 / 44 / 44 / 40 / 46 %. There are no zero returns.
Median MFE24/MAE24: 1H starts +1.36% / −0.86% (versus unconditional +1.05% / −1.03%); transitions +1.05% / −1.30%.

1H starts by direction (`s` normalized; BEAR spans 2 clusters):

| | N | 4h (median / continuation) | 12h | 24h | 72h |
|---|---|---|---|---|---|
| BULL | 8 | +0.18 / 62% | +0.54 / 62% | −0.29 / 38% | −0.47 / 43% |
| BEAR | 9 (8 at 12–24h) | −0.13 / 33% | +0.05 / 75% | +0.30 / 50% | −0.84 / 50% |

Episode lifetimes (Kaplan–Meier, censored at 2026-10-07): median 32 h for 1H (N=17, 1 episode still active), 96 h for 4H (N=6, all ended). 4H starts: BULL (N=4), median R24 −1.76%; BEAR (N=2), −0.24%.

**Status for A:** no stable average directional effect after BOS/transitions was found in this window; 4H starts and alignment restoration are `INSUFFICIENT DATA` (N=6–7).

## 3. B — derivatives attribution

Method: Spearman ρ(feature, outcome), 10 000 permutations (naive, ignoring clusters and autocorrelation), sign of ρ within each 1D regime with n≥4, and control `ρ_vol = ρ(|return over the 24 h before T|, outcome)`. Cluster confidence intervals were not constructed (only 3 clusters).

### 3.1 Primary family (declared in advance, Holm across 10)

1H starts; one feature per layer; outcomes R24 and MAE24 (MAE ≤ 0; closer to zero means milder).

| Feature | Outcome | n | ρ | p (permutation) | p (Holm) | ρ_vol | Sign in regimes #1 / #2 | Status |
|---|---|---|---|---|---|---|---|---|
| ΔOI 24 h | R24 | 14 | −0.13 | 0.67 | 1.00 | −0.33 | − / − | NO EFFECT |
| ΔOI 24 h | MAE24 | 14 | −0.09 | 0.78 | 1.00 | −0.26 | − / − | NO EFFECT |
| funding×s at T | R24 | 14 | +0.01 | 0.99 | 1.00 | −0.33 | − / − | NO EFFECT |
| funding×s at T | MAE24 | 14 | −0.13 | 0.66 | 1.00 | −0.26 | − / − | NO EFFECT |
| liq imbalance×s 12 h | R24 | 11 | −0.45 | 0.17 | 1.00 | −0.49 | − / − | WEAK / INCONSISTENT |
| liq imbalance×s 12 h | MAE24 | 11 | −0.54 | 0.093 | 0.84 | −0.35 | − / − | WEAK / INCONSISTENT |
| gamma asymmetry×s | R24 | 14 | −0.33 | 0.26 | 1.00 | −0.39 | − / 0 | WEAK / INCONSISTENT |
| gamma asymmetry×s | MAE24 | 14 | −0.20 | 0.50 | 1.00 | −0.26 | − / 0 | NO EFFECT |
| tape flow×s 12 h | R24 | 14 | +0.16 | 0.60 | 1.00 | −0.24 | − / + | NO EFFECT |
| **tape flow×s 12 h** | **MAE24** | **14** | **+0.62** | **0.020** | **0.196** | −0.23 | **+ / +** | **INTERESTING CANDIDATE** |

One candidate from 10 tests, versus 0.5 expected false candidates; Holm-adjusted p=0.196, so **the result does not survive multiple-testing correction**. It is called a candidate because it formally met the predeclared conditions (naive p<0.05, the same sign in both 1D regimes with n≥4, |ρ|>|ρ_vol|, n≥10).

### 3.2 Candidate 1 diagnostics (tape flow → MAE24, 1H starts) — chart [candidates_scatter.png](out/phase2a/candidates_scatter.png)

| Check | Result |
|---|---|
| Leave-one-out ρ | +0.52 to +0.73 |
| By 1D regime | #1: +0.62 (n=9); #2: +0.40 (n=4) |
| By direction | BULL +0.46 (n=7); BEAR +0.71 (n=7) |
| Controlling for volatility and flow size (partial ρ) | +0.64 / +0.61 / +0.72 |
| Overlap of 24h windows between events | None (intervals 28–90 h) |
| Time-shift null (3000 shifts, accounts for autocorrelation) | p=0.011 |
| Same feature on F3 transitions (n=37, includes F1) | ρ=+0.20, time-shift p=0.24 |
| Same feature at 1H episode ends (same episodes, n=14) | ρ=+0.80 (not independent confirmation) |
| **Excluding block/combo trades / block/combo only** | **ρ=+0.35 / +0.28 (all trades: +0.62)** |

Block and combo trades represent around 55% of tape notional over the period (41.6 of 74.9 billion USD), so the effect depends on their treatment; the sign persists, but the magnitude does not. The mechanism interpretation (“flow aligned with BOS accompanies a milder pullback”) remains a hypothesis; the adjacent Fa_4h window gives the same ρ=+0.62.

### 3.3 Secondary results (262 tests; `B_attribution_all.csv`)

Under the preregistration, secondary tests (other windows, F2/F3, 1H ends) cannot receive candidate status. Status counts: F1 — 29 NO EFFECT / 29 WEAK; F3 — 46 / 22; 1H ends — 25 / 43; F2 (4H) — 68 × `INSUFFICIENT DATA`.

One result nevertheless warrants separate description:

| Test | n | ρ | Permutation p | Time-shift p | Notes |
|---|---|---|---|---|---|
| F3 (transitions): gamma Aa → MAE24 | 36 | **−0.58** | <0.001 | <0.001 | Thinned sample (≥24 h), n=20: −0.59; leave-one-out [−0.68; −0.56]; excluding A>0.6: −0.56; before 16.09: −0.64 (n=22), after: −0.28 (n=14); ρ_vol≈0; lower half by Aa: median MAE24 −0.39%, upper half: −1.53% (illustration only) |
| F3: gamma Aa → R24 | 36 | −0.42 | 0.012 | — | |
| F1 (1H starts): same feature → MAE24 | 14 | −0.20 | 0.50 | 0.48 | Same sign, not significant |
| F3: tape IV 12 h → MAE24 | 37 | −0.39 | 0.022 | — | Isolated hit |
| F3: ΔOI 1 h → R24 | 38 | −0.37 | 0.024 | — | Isolated hit among 16 OI tests |

The gamma result on transitions is **post-hoc**: selected from 262 tests, with no correction for selection. It performs well on the robustness checks above but is not confirmed in the F1 subset. Its definition is frozen in [FROZEN_CANDIDATES.md](out/phase2a/FROZEN_CANDIDATES.md), candidate 2.

### 3.4 Status by layer

| Layer | Tested | Status | Basis |
|---|---|---|---|
| OI | ΔOI 1/4/12/24 h (OI level not tested: monotonic trend) | **WEAK / INCONSISTENT** | Primary NO EFFECT; at 1H ends, ρ as low as −0.67, but signs do not agree across regimes in every test; on transitions, 1 of 16 tests |
| Funding | Value×s, Δ4 h, Δ24 h | **NO EFFECT** | max \|ρ\| = 0.26, no p<0.05 |
| Liquidations | imbalance×s 1/4/12 h, 12 h volume | **WEAK / INCONSISTENT** | Primary ρ −0.45/−0.54 (n=11, p 0.17/0.09), same sign across regimes; on transitions, \|ρ\|≤0.25 |
| Gamma (unsigned) | ±5% asymmetry, distances to maximum-exposure strike above/below spot | **INTERESTING CANDIDATE (post-hoc, secondary)** on transitions; **WEAK** at 1H starts | See §3.3 |
| Options flow (tape) | Flow imbalance 4/12 h, IV 12 h | **INTERESTING CANDIDATE (fragile)** for flow at 1H starts; IV is **WEAK / INCONSISTENT** | See §3.1–3.2 |
| Block/combo | No separate test | **INSUFFICIENT DATA** | 6 433 block and 6 026 combo trades outside the exclusion, with 1 843 in 12 h windows before 14 valid 1H starts; too few events, so only candidate 1 sensitivity was checked |
| All layers on 4H (F2) | 68 tests | **INSUFFICIENT DATA** | N=6 |

Not tested separately: raw `call_net`, `put_net` (saved in `events_full.csv`), liquidation activity relative to its recent baseline, and OI level.

## 4. C — seven entries into `1D BULL / 4H NONE / 1H BEAR` (`C_seven_cases.csv`, `C_state_comparison.csv`)

All seven are shown individually, with `s=+1` (1D direction). Derivatives use only data before T.

| # | T (UTC) | Price | Prior state | 1H BEAR | 1H BEAR end (hours after T) | 4H BULL restored ≤72 h | 4H BEAR ≤72 h | 1D after 72 h |
|---|---|---|---|---|---|---|---|---|
| 1 | 01.09 18:00 | 77 266 | 4H NONE / 1H NONE | Since 01.09 17:00 | 03.09 03:00 (33; pivot) | Yes | No | BULL |
| 2 | 07.09 16:00 | 78 822 | 4H BULL / 1H BEAR | Since 07.09 07:00 | 09.09 05:00 (37; pivot) | No | Yes | BULL |
| 3 | 09.09 23:00 | 77 924 | 4H NONE / 1H NONE | Since 09.09 22:00 | 11.09 13:00 (38; pivot) | No | Yes | BULL |
| 4 | 15.09 14:00 | 76 619 | 4H NONE / 1H NONE | Since 15.09 13:00 | 16.09 12:00 (22; pivot) | No | Yes | **NONE (1D BULL lost 16.09 00:00)** |
| 5 | 24.09 10:00 | 83 264 | 4H NONE / 1H NONE | Since 24.09 09:00 | 26.09 23:00 (61; pivot) | No | No | BULL |
| 6 | 28.09 02:00 | 83 694 | 4H NONE / 1H NONE | Since 28.09 01:00 | 28.09 19:00 (17; pivot) | No | No | BULL |
| 7 | 07.10 04:00 | 84 150 | 4H BULL / 1H BEAR | Since 07.10 01:00 | Still active | — | — | No data |

Outcomes after entry (%, `s=+1`):

| # | R1 | R4 | R12 | R24 | MFE24 | MAE24 |
|---|---|---|---|---|---|---|
| 1 | −0.14 | −0.07 | +0.50 | +0.15 | +0.68 | −1.30 |
| 2 | +0.26 | +0.69 | +0.11 | +0.10 | +0.84 | −1.52 |
| 3 | +0.49 | +0.56 | −0.08 | −1.40 | +0.82 | −1.60 |
| 4 | −0.88 | +0.45 | −1.47 | −1.27 | +0.95 | −2.15 |
| 5 | +0.30 | +1.19 | +1.30 | +1.57 | +2.02 | −0.13 |
| 6 | −0.33 | −0.61 | −0.06 | −0.75 | +0.82 | −1.35 |
| 7 | −0.06 | −0.01 | — | — | — | — |

Derivatives before T:

| # | ΔOI 4h, % | ΔOI 24h, % | funding, % | liq imb 4h | liq imb 12h | liq 12h, million | gamma A | tape flow 12h | tape IV 12h |
|---|---|---|---|---|---|---|---|---|---|
| 1 | +0.26 | +1.80 | 0.0048 | −0.68 | −0.73 | 12.8 | +0.04 | −0.011 | 41.8 |
| 2 | +0.62 | +1.41 | 0.0022 | −0.92 | −0.92 | 8.2 | +0.27 | +0.009 | 36.7 |
| 3 | +0.17 | −1.15 | 0.0038 | −0.89 | −0.65 | 22.2 | +0.44 | +0.042 | 44.6 |
| 4 | MISSING | MISSING | MISSING | MISSING | MISSING | MISSING | MISSING | +0.251 | 48.7 |
| 5 | −0.19 | −8.23 | −0.0001 | −0.87 | −0.79 | 19.7 | −0.06 | −0.006 | 57.4 |
| 6 | +0.49 | +0.89 | −0.0016 | −0.43 | −0.41 | 11.9 | +0.24 | −0.088 | 37.9 |
| 7 | +1.06 | +1.98 | −0.0045 | −0.98 | −0.98 | 58.7 | MISSING | MISSING | MISSING |

(`liq imb` = (shorts−longs)/total: negative values mean predominantly long liquidations before entry. MISSING in case 4 reflects the shared machine outage on 15.09 from 10:05 to 14:01 UTC; in case 7, gamma is after the gap and tape is inside the exclusion.)

State comparison (`1D BULL` in all three; N transition entries; 2 clusters each):

| | A: 4H NONE / 1H BEAR | B: 4H BULL / 1H BEAR | C: 4H NONE / 1H NONE |
|---|---|---|---|
| Entries | 7 | 2 (1 additional entry was already present at the window start and is not an event) | 8 |
| R4 / R12 / R24, median % | +0.45 / +0.02 / −0.32 | −0.02 / −0.04 / −1.15 | +0.18 / −0.06 / −0.29 |
| Share with R24>0 | 50% | 0% (only 1 entry has R24) | 38% |
| MAE24 / MFE24, % | −1.44 / +0.83 | −1.53 / +0.31 | −1.42 / +0.90 |

**Observations (not conclusions):**
- 1H BEAR within 1D BULL lasted 17–61 h (median 35 h); all six completed cases ended through a pivot break.
- 4H returned to BULL in only one of six cases; in three of six, 4H became BEAR within 72 h (07.09, 09.09, 15.09); 1D BULL was lost in only one (15.09).
- Typical drawdown after entry was −1.3…−2.2% in five of six cases with an outcome; recovery by +24 h occurred in 3 of 6 (R24>0 for 1, 2, 5).
- “Serious deterioration” under the preregistered definition (1D BULL lost ≤72 h) occurred in 1 of 7 cases, precisely the one with almost all derivatives MISSING; derivatives cannot be compared against the case of `1D lost`.
- Post-hoc (defined **after** examining the data, hence only a hypothesis): if deterioration means the appearance of 4H BEAR ≤72 h, the three such cases (07.09, 09.09, 15.09) have higher tape flow over the 12 h before T (+0.009, +0.042, +0.251) than the other three (−0.011, −0.006, −0.088). With six observations, perfect separation gives exact one-sided p=0.05. Within these six, ρ(tape flow, MAE24)=−0.77. Normalization here differs (by 1D, `s=+1`) from candidate 1 (`s` = 1H episode direction), so the signs are not comparable.

**Status for C:** `INSUFFICIENT DATA` for the question “do derivatives distinguish correction from deterioration?”

## 5. Event study (charts `ES_*.png`, medians `ES_medians.csv`)

Window −24…+24 h, all aligned by `s`; thin lines represent individual events, red is the median, and liquidation/tape axes are clipped at the 95th percentile. Values at `k=0` refer to the hour closing at T and are therefore **contemporaneous with the bar that created the event**; they are not predictors.

| Event (N) | Price, k=−12 / +12 / +24, % | ΔOI over 12 h before T, % | OI after T, k=+12 / +24, % | Direction-aligned liquidations, k=0, million $ | Direction-aligned tape, k=0 / +12 / +24, million $ |
|---|---|---|---|---|---|
| 1H start (17) | −1.39 / +0.07 / −0.10 | +0.11 | −0.12 / −0.50 | +2.92 | +10.1 / +5.9 / +3.1 |
| 1H end (16) | +0.67 / −0.34 / −0.35 | −0.53 | +0.51 / +0.05 | −1.56 | −9.9 / +0.7 / −0.3 |
| 4H start (6) | −1.68 / −0.07 / −1.18 | +2.40 | −0.66 / −1.85 | +0.18 | +11.4 / +14.8 / −2.6 |
| 4H end (6) | +0.88 / −0.07 / +0.10 | +1.06 | +0.13 / −0.02 | −2.02 | −10.8 / +3.3 / +2.0 |
| 1H start against 1D (9) | −1.60 / +0.05 / +0.30 | +0.44 | +0.12 / +0.11 | +4.86 | +8.4 / +2.1 / 0.0 |
| Alignment loss (7) | +0.54 / −0.13 / −0.21 | −1.98 | +0.67 / +0.46 | −6.71 | −19.9 / +8.2 / +3.2 |
| Restoration (7) | −1.55 / −0.39 / −0.54 | +0.11 | −0.56 / −0.75 | +2.26 | −0.2 / +6.6 / −2.3 |

Visible patterns (descriptive, small N): before a BOS start, price had already moved against its direction by roughly 1.4–1.7% over 12 h (a countertrend reversal); direction-aligned liquidations and options flow spike in the event bar and fade in subsequent hours; before 4H starts, OI rose by ~2.4% over 12 h, while before alignment loss it fell by ~2.0% (N=5–7, `INSUFFICIENT DATA`). These observations do not establish predictive power.

## 6. Frozen for forward testing

See [FROZEN_CANDIDATES.md](out/phase2a/FROZEN_CANDIDATES.md): definition, sign, data window, and forward criterion for each of the two candidates. The discovery/forward boundary is **2026-10-07 09:00 UTC** (last closed 1H bar in the data; events with later `T` are forward). Data and code hashes are recorded.

## 7. Limitations and issues

1. **Small sample and nesting:** 3 1D clusters (two BULL regimes and a pause); tests use 14–37 events, permutation p ignores clusters; a time-shift null was calculated for only four tests.
2. **Multiple testing:** 272 tests; Holm was applied only to the 10 primary tests. Secondary results are hypotheses.
3. **Candidate 1 is fragile** (§3.2): it does not transfer to transitions, depends on block/combo trades, and has Holm p=0.196.
4. **Candidate 2 is post-hoc** and weaker in the 1H-start subset; the period after 16.09 gives ρ=−0.28.
5. **MISSING:** events with data by layer — F1: OI 15/17, funding 15/17, liquidations 12/17, gamma 14/17, tape 14/17; F3: 38/43, 41/43, 30/43, 36/43, 37/43. Event #4 in §4 has almost no derivatives data.
6. **Event #7 (07.10)** and some 48–72 h horizons are incomplete; outcomes are truncated (N is reported by horizon).
7. **Liquidations** are a forceOrder sample, not the entire market; the value in the event bar is contemporaneous with the event.
8. **Tape:** `amount·index_price` is used as notional; direction is the taker side; block/combo legs are included as recorded, and combos may distort the balance. Reliability before 02.10 was checked only with the Phase 1 rule.
9. **Gamma:** unsigned, without a dealer model; ±5% and ±15% were specified in advance, not fitted; chain composition is normalized through `(G_up−G_dn)/(G_up+G_dn)`.
10. **Regime:** around 5 weeks, predominantly 1D BULL, BTC in a ~76–86 thousand USD range; the BEAR side of transitions cannot be analyzed (N=2).
11. **Error in my script** (`24b_cases.py`: pandas row attribute `.T`), found and fixed before any results were obtained; it does not affect conclusions.
12. **Security:** the separate Phase 1 P0 remains open (tokens/keys in `bot_v2.py` and `bot_errors.log`); values were not used in Phase 2A materials.

## 8. Next minimal step and owner decisions

| Decision | Enables |
|---|---|
| Accept or change forward criteria for the two candidates (§FROZEN) | Forward testing on new data without fitting; approximately 5 weeks for candidate 1 and 4–5 weeks for candidate 2 |
| Decide whether candidate 2 (post-hoc) should be tested on the same footing as candidate 1 | Determines resources devoted to the gamma branch |
| Fix Deribit routing (VPN) and establish tape/gamma lag monitoring | Otherwise forward testing of both candidates will continue losing data as it does now |
| Define `level_lost_5d` | Enables completion of the baseline under §4 of the specification |

Phase 2A is complete; paused here for review. Phase 2B and optimization will not be started.
