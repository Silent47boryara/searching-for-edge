# Frozen candidate definitions (Phase 2A)

Fixed: 2026-10-07 (after calculations). Data boundary: the last closed Binance 1H bar in the data closes at **2026-10-07 09:00 UTC**; everything observed up to it is DISCOVERY. Events with decision time `T` strictly later than **2026-10-07 09:00 UTC** are forward/OOS (events between 09:00 and the time of fixation were not analyzed). The definitions below do not change after fixation; any change means a new candidate and a new fixation.

Provenance: `events_full.csv` sha256 `111e83c9376cdbf12648b047e661d0df09d1372e0c2db3ac2470a0ae78f47652`, `PREREG.md` sha256 `4fdfa832b11fd9567764f2563a72a53bb821abd417a40fb52bd7c0b1b7410cec`, BOS code `bot_v2.py` sha256 `b1f4eaa37187cb2917b92471c4dff9f71ecd88e6e3c4d0e539b8cf7abaa996c8` (changing this file invalidates comparability). These are historical source hashes; the preregistration hash refers to the original Russian document, not its English translation.

## Candidate 1 — aggressive options flow before a 1H episode start (from the preregistered family)

- **Event:** 1H BOS episode start (`compute_impulse`, `tf=1h`, replay using closed Binance candles); `T` is the BOS bar close; `s = +1` for BULL, `−1` for BEAR.
- **Feature:** `Fa_12h = s · (C_net − P_net) / Σ|N|`, across all Deribit BTC options trades with `T−12h < trade_time ≤ T`: `N = amount · index_price` (USD), sign from taker `direction` (`buy` = +1, `sell` = −1); `C_net` is the sum of signed `N` for calls, `P_net` for puts. Block and combo trades are **included**.
- **Validity:** window `[T−12h, T]` must lie outside the exclusion 2026-10-02 00:00 → 2026-10-06 23:05 UTC and outside tape collector outages; otherwise `MISSING`.
- **Outcome:** `MAE24` is the maximum adverse excursion over the 24 hours after `T`, using 1H bar lows/highs and direction normalization (`≤ 0`; closer to zero means milder).
- **Predicted sign:** `Spearman ρ(Fa_12h, MAE24) > 0`.
- **Observed in discovery:** n=14, ρ=+0.618, naive p=0.020, Holm (10 tests) 0.196, time-shift p=0.011, leave-one-out ρ ∈ [0.52; 0.73]; positive for BULL and BEAR and in both 1D regimes. **Fragility:** excluding block/combo trades gives ρ=+0.35, block/combo only gives ρ=+0.28; on transitions (n=37), ρ=+0.20.
- **Forward criterion (proposal, subject to owner approval):** collect at least 14 new valid 1H starts (at the current frequency of ~0.4 events/day, around 5 weeks), with ρ>0 and one-sided permutation p<0.05 under the time-shift null; otherwise close the candidate as not replicated.

## Candidate 2 — unsigned gamma asymmetry at multi-timeframe transitions (post-hoc, secondary family; does not satisfy the preregistration rule)

- **Event:** transition of the multi-timeframe vector `(1D, 4H, 1H)` on the 1H close grid (Phase 1 definition); `s` is the active 1D direction (if 1D is inactive, use 4H, then 1H).
- **Feature:** `Aa = s · (G_up − G_dn)/(G_up + G_dn)`, using the latest Deribit gamma snapshot with `ts ≤ T` (no older than 20 minutes): `G_up = Σ gamma_exposure_per_1pct_move` over strikes in `(spot, 1.05·spot]`, `G_dn` over `[0.95·spot, spot)`; sum across calls/puts and all expirations; **dealer positioning sign is not inferred**.
- **Validity:** snapshot before 2026-10-02 10:10 UTC (after the gap, `MISSING` until the continuous segment reaches sufficient length).
- **Outcome:** `MAE24`, as above.
- **Predicted sign:** `Spearman ρ(Aa, MAE24) < 0`.
- **Observed in discovery:** n=36, ρ=−0.580, naive p<0.001, time-shift p<0.001; thinned sample (≥24 hours between events): n=20, ρ=−0.586; leave-one-out ρ ∈ [−0.68; −0.56]; excluding the point A>0.6: ρ=−0.555; by period: before 16.09, ρ=−0.64 (n=22), after 16.09, ρ=−0.28 (n=14). **At 1H starts (n=14), the same feature gives ρ=−0.20 (not significant).**
- **Selection status:** selected AFTER examining 262 secondary tests (naive p<0.05 with n≥8: 20 of 204, versus ~10 expected by chance). It is ineligible to be called a candidate under the preregistration rule; frozen at the owner's request to “record the effect before new data arrive.”
- **Forward criterion (proposal):** at least 30 new valid transitions (around 4–5 weeks; requires a working gamma collector), with ρ<0 and one-sided time-shift p<0.05.

## Not frozen
Everything else (OI, funding, liquidations, other windows, 4H, event study) is descriptive and ineligible for a forward-test verdict.
