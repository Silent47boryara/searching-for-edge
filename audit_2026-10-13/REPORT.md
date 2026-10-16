# BOS audit: BTC price surges during the gamma collection period and implementation correctness

Date: 13.10.2026. Author: Codex. Local audit and targeted replay only; no downloads, optimisation, orders, bot changes, or restarts.

## Conclusion

BOS detected the September rise but did not predict its peak. Higher-timeframe delays follow from their definitions and candle closes. The implementation cannot nevertheless be called wholly correct: the displayed break level is not always an operative termination condition; the current summary includes completed impulses; and a separate algorithm computes the trading label using an unclosed daily bar. These are real implementation/interface limitations, not evidence that correcting them will produce profit.

## Sources and scope

- Actual `bot_v2.py`, SHA256 `85c427e78766fa1548cdcd2a43433ee849ea6beeb1f052da9fd54ecf547f620c`. Rechecked after the audit; unchanged.
- Saved AST core copy from 07.10 in `LAB_attrib_p1/scripts/bot_v2_extracted.py`, original SHA256 `b1f4eaa37187cb2917b92471c4dff9f71ecd88e6e3c4d0e539b8cf7abaa996c8`.
- ASTs of `add_indicators`, `_detect_swings`, `find_all_bos`, `_local_pivots`, and `compute_impulse` match the saved version. The entire file differs. Current human-layer logic cannot automatically be attributed to September.
- Gamma: 6576 rows, 24.08.2026 19:44:06 — 07.10.2026 18:20:00 UTC. Within this range there are 1858 unique BOS production-log records. Data after the gamma cutoff were not used to select peaks or draw conclusions about this period.
- Peak prices are the saved Binance spot `Price` in the log, not exact exchange intrabar highs or Deribit spot. Existing Binance 1H/4H/1D candles in `LAB_attrib_p1/raw` end on 07.10 / 06.10.
- The code writes `Time` in UTC. All times below are UTC; add 3 hours for Moscow.
- The production module was not imported: only calculation functions were extracted through AST. No network, Telegram, or production logging setup ran. Original project code, data, and processes were unchanged; new files were confined to this audit folder.
- The version loaded by the live process was not established. Claims about current code refer to the file on disk; historical behaviour is checked against the saved log.

## Price movement and BOS observations

The highest saved price in the gamma period was **$87 194.34 on 23.09 at 04:59:20**. The preceding local low in this wave was **$75 459.64 on 15.09 at 22:07:25**, a **15.55%** rise between observations. This episode was selected retrospectively for diagnosis, not to estimate strategy quality.

| First actual display / event | Logged price | State |
|---|---:|---|
| 15.09 22:07 | 75 460 | 1D BULL ACTIVE, 4H BEAR ACTIVE, 1H BEAR ACTIVE; daily bar still open |
| 18.09 04:17 | 77 324 | First 1H BULL ACTIVE after the low; 4H and 1D inactive |
| 18.09 16:19 | 81 042 | 4H BULL ACTIVE, 1H BULL ACTIVE |
| 19.09 00:20 | 81 034 | 1D BULL ACTIVE; all three timeframes up |
| 23.09 04:59, logged maximum | 87 194 | All three BULL ACTIVE; separate Main_Direction = NEUTRAL, SMC = Bullish Range |
| 23.09 10:18 | 85 803 | 1H ENDED; 4H and 1D still ACTIVE |
| 23.09 22:54 | 84 587 | 4H and 1H ENDED; 1D BULL ACTIVE |
| 24.09 10:26 | 83 306 | 1H BEAR ACTIVE, 4H inactive, 1D still BULL ACTIVE |

The claim that “BOS did not respond to the rise at all” is therefore unsupported. The hourly layer showed the rise before higher timeframes; the daily layer activated after a substantial increase. By definition, it could not warn of reversal in advance at the exact peak. Daily BULL persistence after the peak follows from the distant daily break level ($79 600), not a claim that price must rise without corrections. The peak-to-level distance is about 8.71%; this is a distance, not a realised loss or tested stop.

Important: `Start_Time` is the signal candle's OPEN time. 1H “18.09 03:00” becomes available only after 04:00, 4H “18.09 12:00” after 16:00, and 1D “18.09” after 19.09 00:00. These timestamps must not be treated as available entry times.

A second relevant peak was **02.10 13:36, $86 964**; at 19:38 price was $84 218 (−3.16%). Again, all three were ACTIVE BULL at the peak, with Main_Direction NEUTRAL. At 19:38 the hourly BULL was ENDED, while the four-hour BULL remained ACTIVE. This episode clearly illustrates the displayed-break issue below. Gamma has a gap from 02.10 10:10 to 06.10 23:10: the episode falls within the collection calendar, but gamma at the peak is missing. It cannot be used to explain the peak.

## Code findings

### 1. Material: the displayed break level is not always tested

`compute_impulse`, lines 628–638: level-based termination is checked only when a local pivot exists AFTER the start. Without one, the level is not checked. Yet lines 677–682 display `x['level']`—the original BOS level—as `break_level`, along with its distance. The user sees a “break” that is not operative.

Actual example: 4H, **02.10 candle 12:00–16:00**, close **$85 326**, displayed level **$85 649.95**. The close is below the level even with the 0.1% tolerance, but the state remains **BULL ACTIVE**. The 19:38 record has the same ACTIVE state and level. This is not merely a difference between live price and candle close.

Targeted replay found 6 such 1H bars in the inspected 18.09–07.10 tail and 10 4H bars in 24.08–07.10. These are bars, not independent episodes. None were found for 1D in the inspected period. An isolated synthetic check returns ACTIVE BULL at close=90, displayed break=100, and no new pivot.

The specification must choose: either the initial BOS level really terminates the impulse, or the message must show no operative structural stop until a new pivot exists. An exit rule must not be added silently.

### 2. Material in the current file: ENDED is presented as an active direction

`_imp_dir`, lines 701–706, returns direction for both ACTIVE **and ENDED**. `describe_layers` then produces conclusions such as “structure aligned” and “the higher timeframe still holds” without checking activity.

Reproduction: three `{state: ENDED, direction: BULL}` dictionaries produce “All three layers point up — structure aligned.” Yet `_layer_line` correctly says “no impulse” for each ENDED layer: the message contradicts itself.

**Historical caveat:** no such false “alignment” was found in the inspected saved log; September `Layers_Head` excludes ENDED. This is a finding in the current file, not an explanation of the September peak.

### 3. Material: two different structure definitions in one message

`compute_impulse` excludes the unclosed bar (614). But `compute_market_structure` receives the full df and uses `iloc[-1]` (227–233), including current High/Low/Volume. Its pivot confirmation can also depend on a forming right-hand candle. This separate calculation feeds `build_main_decision`, producing BUY/SELL/WATCH/NEUTRAL (998 and 1152).

Simultaneous “ACTIVE BULL” and “NEUTRAL” are therefore not an arithmetic error: the first is a persistent impulse based on closed candles; the second is a current flag from another detector on an unclosed daily candle. To a reader, however, it looks like a contradictory trading decision. Intraday labels can disappear by the close. In the current file `decision_block` is included in Telegram; historical Main_Direction values are confirmed by CSV, but delivery of individual Telegram texts was not checked.

### 4. Moderate: stated lag and actual swing selection differ

`find_all_bos`, lines 559–561: `bisect_left(..., t-2)` selects indices **strictly below** t−2. Documentation says “visible from i+2”; `_local_pivots` in termination actually uses `i <= t-2`. BOS and termination therefore use different availability boundaries.

This is delayed access, not look-ahead, but an outdated swing may be used at the boundary. Isolated check: lows (30,90), (40,80), t=42, Close=85 produce a BEAR BOS through the old level 90, although the new low 80 is already confirmed under the stated rule. The check isolates index selection; market-wide frequency was not measured. It is not valid to declare every BOS exactly one bar late: under the OHLC swing definition, breaking a new high on its own confirmation bar is generally impossible.

### 5. Moderate: a network failure is labelled absence of structure

`analyze_symbol`, lines 797–818: a layer calculation/download exception is replaced with `{state: NONE}`. The message reads as “no structural event”, whereas the correct meaning is “data could not be obtained/calculated”. Around 24–27.09, the actual log briefly switches layers to NONE and back to the previous episode. This audit did not attribute each disappearance to a specific exception; they cannot all be called network failures.

### 6. Methodological limitations, not automatic errors

- Swings are filtered by EMA50, ATR, and volume. This is a particular author-defined detector, not the only BOS definition. No event does not imply no visible movement on a chart.
- Each layer is rebuilt from 500 bars, without persistent episode memory. A very old start can leave the window; EMA/ATR have limited warmup. This mechanism does not explain the identified peak: selected points match the actual logs.
- Confirmations count new runs of the BOS flag, not necessarily distinct broken levels. Recrossing the same level after a return may count; these must not be presented as independent confirmations.
- `ret3d/5d/14d` are windows in each timeframe's bars, not days on every layer. The current message calls `_ret` for 1D; no display error treating 1H bars as days was found here.
- ENDED metrics freeze at termination. They summarise a past episode, not current price.

## Checks and delivery

- 8 selected ticks × 3 TF = **24 comparisons** using the exact production rolling window: State, Direction, Start_Time, and Break_Level matched, with NaN treated as absence of a level. Points cover layer activation, the September peak/pullback, and 2 October. A targeted check, not a complete recalculation of all laboratories.
- **180 current BOS-event checks:** 60 prefixes per TF, indicators on shared history; the event on the selected bar matches a truncated-history calculation. No look-ahead was found in these checks. This does not check every candle/field in the entire codebase.
- Synthetic checks reproduced the ENDED summary, unused fallback level, and bisect boundary.
- **No records on 23.09 between 10:18:52 and 22:54:50: 12:35:58.** The 4H episode ends on the candle opening at 12:00, available after its 16:00 close. The first saved ENDED message is at 22:54, 6:54 after availability. The 1H ending on the 08:00 candle is available after 09:00 and appears in the log at 10:18. This delay must not be attributed solely to the BOS algorithm.
- Charts use price and ACTIVE states at saved ticks. Grey spans mark log gaps >75 minutes; lines are not interpolated across them. Charts combine NONE and ENDED as inactive; CSVs distinguish them.

## Practical decision

Stop adding filters and first agree the existing system's contract: what is active, which level really terminates an episode, which data are closed and when they became known, and how missing data differ from no event. This audit did NOT implement the corrections.

The defects justify targeted corrections and rechecking affected results. They neither automatically invalidate all negative laboratories nor establish a hidden edge. In particular, a human-layer error does not change the historical core; the fallback issue changes behaviour only if the initial level is adopted as a mandatory exit condition.

After semantic inconsistencies are corrected, a separate question remains: does BOS improve decisions beyond simply observing price? This audit did not establish that. There is no basis for exploring new features before resolving the listed issues.

## Artifacts

`audit.py`, `checks.py`, `plot.py` — reproducible local scripts; `results.txt`, `checks.txt` — outputs; `point_replay.csv` — 24 comparisons; `peak_log.csv`, `peak_transitions.csv` — actual records around the September peak; `peak_bos.png`, `oct2_bos.png` — charts.
