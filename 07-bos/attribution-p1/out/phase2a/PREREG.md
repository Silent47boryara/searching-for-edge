# Phase 2A — preregistration (fixed BEFORE calculating outcomes and features)

Date fixed: 2026-10-07. Data: everything available on 2026-10-07 = DISCOVERY. Everything arriving afterward is forward/OOS.

Translation note: this is an English rendering of the original plan. The historical preregistration hash recorded in `FROZEN_CANDIDATES.md` identifies the original Russian file, not this translation.

## Events (units)
- F1: 1H episode starts (17). F2: 4H episode starts (6). F3: multi-timeframe transitions (43, from Phase 1, frozen).
- For the event study: 1H ends, 4H ends (ACTIVE→NONE), 1H starts against the active 1D direction, and loss/restoration of full alignment (all 3 timeframes ACTIVE in the same direction).
- Decision time T = BOS bar close (episodes) / close of the 1H bar where the vector changed (transitions). Features use only timestamps ≤ T.
- Cluster = 1D regime (1D episode #1, 1D NONE pause, 1D episode #2). Always report both N events and N clusters.

## Direction s
- Episodes: episode direction (+1 BULL, −1 BEAR).
- Transitions: active 1D direction; if 1D is inactive, use 4H, then 1H.

## Outcomes (P(T) = close of the bar ending at T; costs are not modeled)
R_h = s·(P(T+h)/P(T) − 1); MFE_h = maximum favorable excursion, MAE_h = maximum adverse excursion (≤0), using the highs/lows of 1H bars in (T, T+h], adjusted for s.
h ∈ {1,4,12,24,48,72} hours; if T+h is beyond the last closed bar, exclude the observation for that h (report N).
continuation: R_h>0; reversal: R_h<0; R_h=0 is neither and is counted separately.
Control: unconditional R_h across all hours in the window for s=+1 and s=−1 (drift).

## Features (before T; maximum age: OI 15 min, funding 60 sec, gamma 20 min; otherwise MISSING)
- OI: ΔOI_w = OI(T)/OI(T−w) − 1, w ∈ {1,4,12,24} hours.
- Funding: f(T); Δf_w = f(T) − f(T−w), w ∈ {4,24} hours.
- Liquidations (window [T−w,T], w ∈ {1,4,12} hours; v2 mask coverage ≥ 90%, otherwise MISSING): L_long, L_short, total, imbalance I = (L_short − L_long)/total (total=0 → NaN, counted separately). Aligned Ia = s·I.
- Gamma (unsigned only, pre-gap segment): G_up/G_dn = Σ gamma_exposure_per_1pct_move over strikes in (spot, 1.05·spot] / [0.95·spot, spot); A = (G_up − G_dn)/(G_up + G_dn); Aa = s·A. Descriptive: distance to the maximum-exposure strike (±15%) above/below spot and its share.
- Tape (window [T−w,T], w ∈ {4,12} hours; outside the exclusion 2026-10-02 00:00→2026-10-06 23:05): notional = amount·index_price, sign from taker direction; flow = (call_net − put_net)/Σ|notional|; aligned Fa = s·flow; IV = notional-weighted mean iv; block/combo are counts only.

## Primary family (Holm across 10)
F1 sample; features: ΔOI_24h, f(T) (s·f), Ia_12h, Aa, Fa_12h; outcomes: R_24h and MAE_24h. 10 tests.
Everything else (other windows/horizons/F2/F3) is secondary and descriptive, ineligible for “INTERESTING CANDIDATE.”

## Statistics
Spearman ρ(feature, outcome), permutation p (10000 permutations; naive, ignoring clusters), sign of ρ within each 1D cluster with n≥4, volatility control: ρ(|return over the 24 hours before T|, outcome). Cluster confidence intervals are not constructed (only 2–3 clusters).

## Statuses
- INSUFFICIENT DATA: n_valid < 8 or features are available in fewer than 2 clusters.
- INTERESTING CANDIDATE (primary family only): naive p < 0.05 AND the same sign of ρ in both 1D regimes (n≥4 in each) AND |ρ| > |ρ_vol| AND n ≥ 10. Always report the Holm-adjusted p alongside it and the expected number of false candidates under the null (10×0.05 = 0.5).
- WEAK / INCONSISTENT: naive p < 0.20 or |ρ| ≥ 0.20, but candidate conditions are not met.
- NO EFFECT: otherwise.
VALIDATED is not used. For a candidate, freeze its exact definition (feature, window, sign, outcome) in the report.

## Excluded
Threshold fitting, composite scores, ML, trading rules, level_lost_5d (undefined), OI backfill, tape 02–06.10, gamma 02.10–06.10.
