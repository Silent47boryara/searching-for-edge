# Interactive BTC market-flow map

Open `market_map.html` in a browser. The file is self-contained: Chart.js 4.5.1 and 1093 hourly observations are embedded; no external requests are made. Data cover 29.08–14.10.2026 00:00 UTC. This is a historical snapshot, not a live feed.

Features: date selection and preset periods; a synchronised cursor across 6 charts; click to lock a time; a slider and table rows to select an hour; Moscow/UTC time; all tape trades or tape excluding block/combo/RFQ; a filter for the 4 price/OI regimes; CSV export. Gaps and “no data” preserve missing values. The map uses only information available at T, without future outcomes. Large raw feeds are not embedded in the HTML.

Source: ../collectors_2026-10-14/hourly_features.csv. Generation: build.py (Python 3.9 with pandas), using template.html and the local chart.umd.min.js library. Research results: ../collectors_2026-10-14/RESULT.md.

The original interface was checked in a browser: full period of 1093 hours, tape switching, a preset period, selection of 08.10 19:00 Moscow time (price −1.77%, OI −2.38%, liquidations $51.43M, 95% long), and no console errors. preview.png records that original interface; the English translation changes labels only.

Original local Codex preview: http://127.0.0.1:8766/market_map.html, listening only on 127.0.0.1. The self-contained file does not require that server. Production and collectors were not changed.
