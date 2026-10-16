# BTC BOS × derivatives: research (Phases 1 and 2A)

Question: do derivatives data (OI, funding, liquidations, gamma, options flow) add information about BTC price movements conditional on the BOS state already known from `bot_v2`?

**Finding as of 2026-10-07:** no convincing relationship was found. The dataset is small (around 5 weeks, two independent 1D regimes). Two tentative leads have been frozen for testing on new data.

## Reading guide
| File | Contents |
|---|---|
| [PHASE1_REPORT.md](PHASE1_REPORT.md) | Data audit, BOS episodes, observation units, causal joins |
| [PHASE2A_REPORT.md](PHASE2A_REPORT.md) | Baseline outcomes, derivatives attribution, 7 cases, event study |
| [out/phase2a/PREREG.md](out/phase2a/PREREG.md) | Analysis plan fixed before calculation |
| [out/phase2a/FROZEN_CANDIDATES.md](out/phase2a/FROZEN_CANDIDATES.md) | Frozen definitions of two candidates for forward testing |
| [docs/phase0_protocol_collectors_vs_BOS.md](docs/phase0_protocol_collectors_vs_BOS.md) | Original testing protocol |

## Structure
- `scripts/` — sequential scripts (`01…26`), run in order; `bot_v2_extracted.py` is a verbatim copy of the BOS functions from `bot_v2.py` (source hash in its header).
- `raw/` — Binance BTCUSDT candles (1d/4h/1h), downloaded on 2026-10-07; closed candles only.
- `out/` — intermediate Phase 1 tables and charts; `out/phase2a/` contains Phase 2A outputs.

## Not included
- Original collector data (`oi_raw`, `funding_markprice_raw`, `liquidations_raw`, gamma, tape): these are large and remain local. Without them, scripts `05…26` cannot be rerun, but the resulting tables are provided in `out/`.
- The original `bot_v2` code and logs: secrets were found in those source files and logs, so they are not published.
- Scripts use absolute paths under `/Users/arefevoleg/…`; these must be replaced to run on another machine.

## Status and caveats
The results are exploratory: `EXPLORATORY / INSUFFICIENT FOR CONFIRMATION`. These are neither trading rules nor a recommendation. The discovery/forward boundary is the 1H bar close at 2026-10-07 09:00 UTC.

## Translation and provenance
These English translations preserve the historical reports, proposed criteria, and status statements as written at the time. The original Russian documents remain available in Git history. Historical source hashes refer to the original files, including the Russian preregistration, rather than to these translations. Research code, datasets, and numerical outputs are unchanged.
