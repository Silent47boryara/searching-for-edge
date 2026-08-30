# Replication code — Research Note 02 (Momentum)

This folder contains the actual scripts and result artifacts behind the numbers cited in [Research Note 02 — Momentum](../momentum-evidence-from-binance-replication.md). It is published so the note's claims can be checked against code and output, not just against prose.

## What's here

- `lab_06_momentum_gate.py`, `gate_check_RESULT.md` — the original, cheap 7-month gate-check (28 weeks) that motivated downloading a full multi-year history. Referenced in the note as the starting point, not the headline result.
- `step2_multiyear_klines/` — downloads the full multi-year USDⓈ-M perpetual futures history directly from Binance's public `data.binance.vision` archive (no API key required) and builds the daily open/close/quote-volume panel used by every later step. `download_multiyear_klines.py` does the download; `build_panel.py` assembles the panel; `universe_timeline.py` checks universe-size continuity.
- `step3_full_history_spread/` — the headline J=1/K=1 (1-week formation, 1-week holding) cross-sectional momentum spread on the full history: gross result (`full_history_spread.py`, `RESULT.md`), net-of-costs (`net_of_costs.py`, `RESULT_net_of_costs.md`), and the post-hoc liquidity-bucket exploratory cut (`liquidity_bucket_exploratory.py`, `RESULT_liquidity_exploratory.md`).
- `step4_j2k2_spread/` — the second, pre-committed literature-backed specification, J=2/K=2 (`j2k2_spread.py`, `RESULT.md`).

Each `RESULT*.md` is the actual, unedited write-up produced when that script was run — these are the primary source for every number quoted in the note, not a secondary summary.

## What's deliberately excluded

- The raw downloaded klines cache and the full daily price panels (`panel_open.csv`, `panel_close.csv`, `panel_quote_volume.csv`) — around 100 MB of cached public market data, reproducible by running `step2_multiyear_klines/download_multiyear_klines.py` and `build_panel.py` yourself. Not included for size, not because of any restriction.
- Anything tied to the proprietary Klines signal-detection system. This lab is explicitly independent of it (see the scripts' own docstrings — "не привязана к signal_tier") and none of these files reference its thresholds, scoring, or execution logic.

## Reproducing

1. `cd step2_multiyear_klines && python3 download_multiyear_klines.py` (downloads public Binance archive data — this step takes a while and needs disk space).
2. `python3 build_panel.py` — builds the panel this replication reads from.
3. `cd ../step3_full_history_spread && python3 full_history_spread.py` — gross headline result.
4. `python3 net_of_costs.py` — net-of-costs layer.
5. `cd ../step4_j2k2_spread && python3 j2k2_spread.py` — the second specification.

Local absolute paths from the original research environment have been replaced with relative paths or placeholders; no other line of these scripts has been altered.
