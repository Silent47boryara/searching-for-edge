# BOS quality: frozen diagnostic protocol, 2026-10-13

Purpose: discriminate implementation defects, poor descriptive state quality, and absent forward evidence. No production modification, network candle downloads, parameter optimization, trading backtest or claims of profit. Literature uses web primary sources. All local outputs here.

Data: available BTC spot 1H 2022–2026 and Phase1 raw through 2026-10-07; union audited for gaps/conflicting overlaps. 4H/1D aggregate from complete UTC 1H groups, cross-check against exchange raw. Main context window actual gamma timestamps; historical years descriptive robustness, NOT untouched holdout. Old and new data must not be spliced across unexplained inconsistent overlaps without disclosure.

Replay exactly rolling 499 closed candles; EMA50/ATR14 and volume20 reproduce production. Variants fixed before results: original; lag_fixed (inclusive pivot availability i<=t-2); fallback_contract (lag_fixed plus initial BOS level enforced before first opposing post-start local pivot). Last is a specification change, not a proven bugfix. Display-only ENDED and data-error corrections cannot improve historical numeric state by themselves. Return CLOSED bar timestamps, never opening timestamps as decision availability.

Primary descriptive reference: trailing 12 bars close displacement >+1ATR / <-1ATR / otherwise neutral. This is an operational proxy of visible movement, not objective market truth and not predictor; independently computed from BOS. Sensitivity: 6/24 bars and .5/2ATR, all shown, no selecting best. Baselines EMA20 +/- .5ATR, trailing 3-bar displacement +/-1ATR, always neutral. No baseline identical to reference.

Metrics: 3-class balanced accuracy, macro F1; bullish/bearish precision, active-in-neutral and active-opposite proportions, state coverage and switches per year. Score all eligible bars and per year; compute disagreement of variants. Historical exposed sample, report dependence: 7-day block bootstrap for primary paired difference and circular shifts as "broken clock" diagnostic (preserves state occupancy/persistence). Neither test proves deployability.

Forward: report next 12-bar signed return for every active bar separately from descriptive agreement; costs excluded, overlapping observations not independent. Event starts also report next24h for gamma window for comparison with Phase2A, not recreation of all old exploratory tests.

Collectors: reuse frozen Phase2A features/masks and two fixed candidates; never rerun 272-test fishing. For lag_fixed event times, rejoin causal frozen hourly feature values where matching clock grid exists; quantify how many starts change and whether original derivative conclusions can be reused. No reliable features at new event time means missing, not zero/no effect. Full new attribution unnecessary unless corrected events materially differ; original candidates remain discovery, no new validation by rerunning same data.

Validation: optimized replay against exact AST-extracted functions on deterministic sampled windows and peak checkpoints, EMA/ATR equality, no future access via prefix replay, data quality and source hashes. Freeze artifact before running result calculations. Stop/reassess on source conflict or mismatch. No model/threshold tuning to improve numbers.

Pre-results data amendment: 1599 overlapping 1H bars, only last old bar 2026-08-20 14:00 differs (Close/Volume); old downloader included current unfinished candle, file saved within that hour. Use later CLOSED raw row; preserve conflict CSV. No unexplained splice or price tuning.

Pre-results data amendment 2: historical hourly gap detected around 2023-03-24. No interpolation; exclude replay windows crossing gaps, incomplete aggregated 4H/1D bars, forward horizons crossing gaps. Report exact dates and excluded warmup.

Supplement (after primary results, explicitly exploratory, not a new pass/fail gate): reuse historical 8% zigzag threshold for a retrospective wave coverage/lag diagnostic; count pre-existing same-direction states separately from fresh starts, include unmatched waves. This shows why coverage alone can look good. A causal EMA20 held for 24 bars is a frequency sensitivity control, fixed now, not selected to match/best BOS results. Primary comparisons remain as frozen above.
