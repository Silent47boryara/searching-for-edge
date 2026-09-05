# 06 — What Is Left for a Retail Trader?

**Author:** Oleg Arefev
**Published:** August 2026
**Status:** `Open` — current research note; paper results are walk-forward stable, while execution validation and deeper robustness testing remain ongoing
**Class:** Author's own system, described conceptually, not literature-tested — this note is not a review of someone else's paper, it's an account of what survived after checking a system built independently against the literature it turned out to resemble

**Research question:** Parts I–V of this series went hypothesis first: read a published strategy, check whether it's statistically real, check whether it's reachable and tradable by a retail account, verdict. This note goes the other way. A detector had already been running for months — built from manual replay and case-by-case review of Binance volume spikes, not from a paper — before any of this series' literature was read carefully. Only after it had a stable shape did it become worth checking against academic work. This note is that check: what the system turned out to be built on, what the numbers say, and what's still honestly open.

---

## 1. Built first, checked against the literature after

Nothing here started as "let's implement paper X." It started as watching Binance volume spikes by hand, week after week, across different months and market conditions, and building up a set of filters by trial and error — which spikes tend to continue, which ones are already over by the time they're visible, which ones are pure noise. The filters, the tiers, the exit logic all came out of that process before any of the papers below were opened.

Once that process had produced something stable, it got checked against the literature — not to borrow credibility, but to find out honestly whether it had converged on something known or on something already shown to be a dead end. That check turned up eleven papers worth naming directly, split across three questions: why does this phenomenon exist, how should an exit actually be managed, and what's still an open door.

## 2. The literature base — named, not gestured at

**Why an anomalous volume spike predicts anything at all:**

- Gervais, Kaniel & Mingelgrin (2001), *The Journal of Finance* — evidence that abnormal trading activity can contain information about subsequent returns, plausibly through visibility and investor attention: stocks with abnormally high volume outperform afterward, abnormally low volume underperform, and the effect is stronger precisely when there's no abnormal price move yet. Different asset class, different holding horizon (weeks, not minutes) — this paper doesn't validate this system's own volume-spike detector, it's cited here as evidence the underlying phenomenon (volume carrying return-relevant information) has independent academic grounding.
- Kamps & Kleinberg (2018), *Crime Science* — formal criteria for defining and detecting a crypto pump from candle-level price and volume anomalies. Establishes an academic precedent for defining and detecting crypto pump-and-dump events from abnormal market activity, separate from any claim about what happens after detection.
- Xu & Livshits (2019), USENIX Security — pre-pump features predict *which* coin gets targeted; small-cap, low-liquidity names are disproportionately the targets. Confirms the universe this system watches (small, thinly-traded pairs) is exactly where this kind of signal concentrates.
- Dhawan & Putniņš (2023), *Review of Finance*, 27(3), 935–975 — the load-bearing paper for timing. Average peak arrives around 8 minutes after the signal (median 1.54 minutes), retracement back toward the pre-move level typically within an hour, and — critically — a late entry carries **negative expected value**, proven both theoretically and empirically. This is the direct academic backing for a "don't chase" rule.
- La Morgia, Mei, Sassi & Stefa (2020), ICCCN — real-time pump detection from a spike in aggressive market-buy orders, achieving F1 up to 92% at a 25-second/7-hour window. Architecturally close to what this system's early stage does — flag the anomaly fast — but the paper's own honest limit is that it detects that a pump is *happening*, not whether it will continue with a profitable move. That distinction matters below.

**How an exit should actually be managed, once a position is open:**

- López de Prado, *Advances in Financial Machine Learning* (2018) — the triple-barrier method: an upper barrier, a lower barrier, and a time-out, with the label determined by whichever is hit first, plus meta-labeling as a second layer that decides *whether to take* a signal rather than inventing new ones. This system's exit structure — a confirm/cancel decision after a short monitoring window, then a trailing exit, then a hard timeout — is structurally the same three-way race, arrived at independently before this book was read.
- Sweeney (1997), *Maximum Adverse Excursion* — the method of separating winning and losing trades by how far each one moves against the entry before recovering, and placing a stop at the point the two distributions diverge, rather than picking a stop from theory. This system logs exactly the inputs that method needs.
- Han, Zhou & Zhu (2014) — a stop-loss overlay on momentum more than doubles the Sharpe ratio and sharply caps the worst monthly drawdowns, on a monthly-stock momentum strategy with a 10% stop (maximum monthly losses cut from −49.79% to −11.36% equal-weighted, from −64.97% to −23.28% value-weighted). The percentage doesn't transfer to a five-minute crypto signal — and hasn't been imported here — but the underlying principle (a rule-based exit beats holding to a fixed horizon) is the same one this system's own comparisons landed on independently.
- Dai, Marshall, Nguyen & Visaltanachoti (2021), *International Review of Finance* — trailing stop-loss rules reduce total and downside risk, particularly in declining markets, while sacrificing some expected return relative to a mean-variance benchmark; tighter rules are also more sensitive to transaction costs. That risk/return trade-off — protection against the tail, at a cost to average return — resembles what shows up in this system's own trailing-versus-fixed-versus-partial comparison below.

**What's an open door, not yet resolved — by the literature or by this system:**

- Cont, Kukanov & Stoikov (2014) — order-flow imbalance is approximately linearly related to short-horizon price changes, with price impact inversely related to market depth. The relationship is defined from order-book events rather than candle-level volume, so the paper does not establish that the same signal survives aggregation into this system's five-minute candle framework — treated here as a dead end for this system's timeframe until shown otherwise, not disproven, but not usable as-is.
- Garcia Seuma (2026, arXiv:2607.27070) — finds no event-invariant early-warning variable across seven major BTC liquidation cascades (2022–2025). Price carries a critical-slowing-down signature in five of seven events but is silent in the two sudden-news shocks; the one regularity that survives across all events is a compression in taker order-flow variance, but it works as a population-level precursor, not a reliable alarm for any individual event. Named here as the one genuinely open frontier this system hasn't touched — and a caution against adding a plausible-looking liquidation indicator without its own test, exactly the discipline this system already applies to itself.

The honest summary of this check: four separate threads of independent, unrelated literature — volume premium, pump anatomy and timing, triple-barrier exit design, and stop-overlay behavior — turned out to already describe a system built without reading any of them first. That's not proof the system works. It's a sanity check that it isn't standing on something the literature has already shown to be false.

## 3. What actually gets filtered — the funnel, described, not coded

What follows is a compressed description of a much longer process, and that compression is worth naming before describing the result. The small structure below is what survived repeated historical replays, case-by-case failure review, feature rejection, proxy testing, data-integrity checks, exit-method comparisons, and several rounds of rebuilding and retesting the same hypotheses on new samples. Most candidate ideas along the way did not survive that process. None of the intermediate thresholds or implementation details are reproduced here — what follows is only the shape that remained after most of it was thrown away.

No thresholds, no scoring formulas, no exact filter definitions — those stay unpublished, same disclosure boundary as the rest of this repository. What can be described honestly is the shape of the funnel, because the shape is the actual finding.

The starting point is raw: a continuous scan across Binance pairs for abnormal volume, producing a large number of raw candidate rows every day — the great majority of which are exactly what the literature above predicts they'd be: noise, dead flat ranges, or moves that already peaked before they were even visible. That raw stream is not a source of signal by itself; it's a haystack.

Filtering happens in stages, cutting hard at each one — a system of filters and proxy search, in the sense that follows. A candidate first has to clear a set of hard rules before it's actioned at all (the core-filters layer). What passes gets tiered by signal quality — from the strongest, most complete pattern down to the tier that means "skip." Only the top tiers get a few minutes of live monitoring before a hold/cancel decision, and only what survives *that* — confirmed continuation, no early failure — becomes a position at all. From a large raw stream, this leaves a small number of tradeable signals per day. That ratio — brutal, not gentle — is the entire point of the funnel: it exists specifically to throw away everything the literature above says is structurally unprofitable to chase (a pump already past its 8-minute peak, a late entry with negative expected value, a spike that's just noise).

**A representative month — August 2026.** The shape above is easier to see with one month's actual counts. The detector has been collecting and testing continuously for about four months (signal detection since early May 2026; the raw Stage-0 scan longer still), so August is shown here as a representative sample, not a hand-picked one:

- **Collected:** 143,118 raw volume anomalies over the month — about 4,090 per day.
- **Cleared into a signal of any tier:** 326 — that is 0.23% of the raw stream. Of those: BRONZE 191, WATCH 112 (alert-only, never traded standalone), GOLD 23.
- **Routed to execution:** 214 candidates (0.15% of raw) — GOLD reviewed by hand, BRONZE-with-impulse handled by the engine.
- **Net:** roughly six tradeable signals a day out of ~4,000 raw anomalies.

These are aggregate counts taken directly from the system's own logs, not thresholds or formulas — the filtering logic that produces the cut stays unpublished, the same disclosure boundary as the rest of this repository. The point of showing them is the funnel's brutality, which is the actual finding: the overwhelming majority of what the scan collects is thrown away on purpose.

What survives the funnel splits again, cleanly, into two tiers with separate track records — described next.

## 4. The statistics — what actually gets measured

Two versions of the log exist, and both are reported here rather than only the more flattering one. The larger walk-forward sample below comes from the log format that ran through mid-August: it hardcoded the entry timestamp to a fixed offset after signal detection, rather than logging the actual time the monitoring decision was made. A patch since then replaced that hardcoded offset with a real timestamp and reference price, which is more honest but has only been accumulating trades for about two weeks — too short a window on its own for a walk-forward claim. Both are shown below, not just the larger one.

**The core surviving tier ("ALIVE"), large sample, pre-patch log** — trades that clear the early-failure filters and show genuine follow-through in the monitoring window — shows, across 93 tracked trades over roughly two months: an 85% win rate, mean return +5.58% per trade, median +4.08%. Every one of eleven consecutive weekly cohorts was positive on average — not one losing week. Split into an early half and a late half of that period, the later half performs at least as well as the earlier half (82% win / +4.59% mean early, versus 88% win / +7.00% mean late) — the direction that matters, since a result that only holds in the first half and decays in the second is the warning sign, not the confirmation.

**A narrower, higher-conviction tier ("ROCKET")** inside that same ALIVE population — trades that additionally show a stronger continuation move within the first five minutes — shows, across 46 tracked trades: 100% win rate, mean +9.68%, median +7.18%. All eleven weekly cohorts again positive, and a split-half comparison (23 early / 23 late) lands within a fraction of a percent of itself in both directions (+9.48% early, +9.88% late) — about as stable as a walk-forward check on this sample size gets. The remainder of ALIVE, outside that rocket tier, still shows a real edge on its own (70% win, +1.56% mean) — smaller, but not zero, meaning the rocket label isn't the only source of edge inside ALIVE, just the strongest one.

**The same definitions, on the newer, more honestly timed log** — 67 signals logged since the patch, spanning roughly two weeks: 22 qualify as ALIVE (63.6% win rate, mean +4.86%), and 10 of those qualify as ROCKET (100% win rate, mean +10.57%). The rocket number holds up; the broader ALIVE win rate is meaningfully lower than the 85% on the older, larger sample. Twenty-two trades over two weeks is too small a sample to treat as its own walk-forward verdict, and it isn't presented as one — but it's the first data point measured with real detection timing instead of a hardcoded offset, and the fact that it points weaker rather than stronger is exactly the kind of thing this note isn't going to smooth over. It's watched, not yet concluded from.

Two honest qualifications, stated directly rather than left for someone else to find:

**The rocket tier's definition is partly circular.** It's defined in part using the same short-term price movement that determines the outcome being measured, so some of that 100% win rate is mechanical overlap between predictor and label, not pure prediction. That doesn't make the number false — the effect is real and separates cleanly from the non-rocket ALIVE population — but it should be read as "this tier is the strongest part of a real signal," not "this feature achieves 100% accuracy with no overlap."

**Every number above assumes a paper fill.** The reference price used to price every trade is recorded at the moment a signal is confirmed — which, mechanically, is already after the coin has moved from wherever it was when the underlying spike started. That's the subject of the next section.

## 5. Execution reality — what these numbers don't cover

The filtering and exit logic have already been checked, several times, against realistic constraints rather than left as a hopeful backtest:

**Trailing versus alternatives, tested on an earlier 80-trade ALIVE sample (mid-August internal comparison, same pre-patch log family as the larger walk-forward numbers above).** A pure trailing exit produced +5.64% expected value per trade ($45 total on $10-per-trade stakes); a partial take-profit (banking half the position at +5%, trailing the rest) produced +4.51% ($36); a fixed +5% take-profit produced +3.38% ($27). Win rate was identical across all three (81%) — the difference is entirely in how much of the tail (the rare large win) each method keeps. Trailing keeps the most tail and wins on money; partial exits trade some of that money for smoother, easier-to-hold outcomes — a real, named trade-off, not an oversight. This comparison hasn't been re-run on the newer, honestly-timed log yet; it's reported here as the finding that shaped the current exit design, not as a claim re-verified on today's data.

**Slippage has a specific, tested form of protection: the trailing exit itself.** Because the exit is a trailing stop rather than a fixed target, it doesn't require picking an exact price in advance — it gives back a bounded, measured amount from the peak (empirically, roughly 4–4.5% of the peak-to-exit move, and flat across low, medium, and high realized-volatility buckets, meaning the trailing distance doesn't need to be widened for more volatile tokens). That's a real mechanism against one specific risk — being caught by a fixed order that a fast move blows straight through — but it is not the same thing as measured, live execution slippage, and it doesn't cover fees.

**Commissions are known and small on paper, not yet stress-tested live.** On the 80-trade sample used for the trailing comparison, total commissions came to roughly a dollar against $800 in stakes — a rounding error against the trailing exit's own $45 total expected value. That ratio should hold at retail size; it hasn't been checked against a live fill that includes real slippage on top of the fee.

**Fill risk is the one gap that cannot be closed on paper, and it is named plainly.** Every statistic in Section 4 is priced at a reference price recorded after signal confirmation — a price already reached *after* the move that makes the signal look good has partly happened. An earlier, more pessimistic version of this same system's own backtesting — one that assumed a materially worse, more realistic fill — flipped the same trade population from a large paper gain to a large paper loss purely by changing that one assumption. The newer, honestly-timed log in Section 4 points the same direction, in a smaller and less conclusive way: the ALIVE win rate on real detection timing (63.6%, N=22) came in lower than on the older, hardcoded-offset log (85%, N=93). Two weeks is not enough data to call that a settled result, but it's consistent with the concern rather than against it, and it's reported here rather than waited out quietly. That's the entire reason this note carries an `Open` status instead of a closed verdict either way. The walk-forward stability in Section 4 answers "does this hold up over time" — it does not answer "does this hold up once real slippage, real order latency, and real reaction time are included." That second question has exactly one honest way to answer it: trade small, real size, and measure the actual fill. No further replay closes this gap.

## 6. The other open question — this system doesn't see everything

Everything above is built to catch one specific shape of event: a sudden, detectable spike in volume. That's a deliberate, narrow target, and it's also a blind spot, and this is the first place that blind spot is being written down directly.

A slow, grinding, low-drama continuation move in an already-liquid, already well-known name — the kind of multi-day or multi-week climb a token like BNB or TON can produce without ever throwing off the sharp volume anomaly this system is tuned to detect — doesn't register as a signal here at all. It isn't filtered out for being low-quality; it's simply never the shape of thing this detector is looking for. Three separate reference cases inside this project's own history point at exactly the same gap, independently.

That gap is not being closed by tuning this system further — a detector built for sudden anomalies can't be widened into a trend-continuation detector without becoming something else. It's reserved for a second, separate system (referenced elsewhere as "System 2 — a trend-continuation catcher") with its own literature groundwork already done — six papers reviewed as engineering specs on price-path continuity and intraday predictability — but no replay, no backtest, and no validated feature list yet. It is explicitly not allowed to borrow this system's own thresholds or trailing-stop logic; it needs its own validation from zero, the same discipline every hypothesis in this series has been held to. Until that system exists, this note's honest scope is anomaly detection only — not "catches momentum," but "catches sudden spikes," which is a narrower and different claim.

## 7. Verdict

On the same bars this series has applied to other people's published strategies — plausible mechanism, independent convergence with unrelated literature, and a walk-forward-stable paper track record rather than a single lucky window — this system clears them. What it does not have is a resolved answer on execution reality, and, separately, a named and currently uncovered class of moves it isn't built to catch at all.

Both of those stay stated here rather than smoothed over. Nothing in this note should be read as a claim that the system is fully automated, or that its profitability is proven. It is not run unattended, and its replay and paper-trade findings are not a guaranteed live edge — they're paper results, walk-forward-stable on paper, with live execution still unverified and the broader robustness analysis still ongoing.

So — can a retail trader actually run something like this? On paper, in essence, yes. Live, with the one open variable still open: yes, with a manual check sitting on top of it, not without one.

## 8. How this is actually traded — machine plus human, not machine instead of human

The honest shape of this is semi-automatic, not automatic. Detection, tiering, and the monitoring window are automated — that part runs without a person watching every candle. The decision on a specific trade is not: whether the liquidity actually looks real at the size being traded, whether the money is visibly leaving the token right now rather than arriving, whether this specific setup matches or diverges from the patterns that have burned this system before — that stays a short, disciplined manual check layered on top of the automated signal, every time, before size goes on.

That manual layer is not where the edge comes from. The automated signal and its filters are the primary decision; the manual check exists to catch the more obvious garbage the automated layer can't see (a token with a wall between the last trade and any real depth, a coin that's dying rather than dipping) and to keep the trader honest about what "real" liquidity looks like at their own size. Priority, in order: the engine's signal first, the tier label second, the manual eye-check last — a sanity filter, not a source of conviction.

If there's one thing worth taking from this note by anyone building something similar, it's this: a stable-looking paper track record is not the same claim as a proven live edge until real fill has been measured on real size, and a detector tuned for one shape of price movement will be structurally blind to a different, equally real shape — no amount of tuning the first system fixes that; it needs a second, separately validated one.

---

## References

- Gervais, S., Kaniel, R., Mingelgrin, D. (2001). "The High-Volume Return Premium." *The Journal of Finance*, 56(3), 877–919.
- Kamps, J., Kleinberg, B. (2018). "To the moon: defining and detecting cryptocurrency pump-and-dumps." *Crime Science*, 7:18.
- Xu, J., Livshits, B. (2019). "The Anatomy of a Cryptocurrency Pump-and-Dump Scheme." *USENIX Security Symposium* (arXiv:1811.10109).
- Dhawan, A., Putniņš, T. J. (2023). "A New Wolf in Town? Pump-and-Dump Manipulation in Cryptocurrency Markets." *Review of Finance*, 27(3), 935–975.
- La Morgia, M., Mei, A., Sassi, F., Stefa, J. (2020). "Pump and Dumps in the Bitcoin Era: Real Time Detection of Cryptocurrency Market Manipulations." *ICCCN 2020* (arXiv:2005.06610).
- López de Prado, M. (2018). *Advances in Financial Machine Learning.* Wiley.
- Sweeney, J. (1997). *Maximum Adverse Excursion: Analyzing Price Fluctuations for Trading Management.* Wiley.
- Han, Y., Zhou, G., Zhu, Y. (2014). "Taming Momentum Crashes: A Simple Stop-Loss Strategy." (SSRN 2407199)
- Dai, B., Marshall, B. R., Nguyen, N. H., Visaltanachoti, N. (2021). "Risk Reduction Using Trailing Stop-Loss Rules." *International Review of Finance.*
- Cont, R., Kukanov, A., Stoikov, S. (2014). "The Price Impact of Order Book Events." *Journal of Financial Econometrics*, 12(1), 47–88.
- Garcia Seuma, R. M. (2026). "Where does the criticality live? Early-warning signals are event-heterogeneous across seven crypto-perpetual liquidation cascades." (arXiv:2607.27070)

**Note on abstracts vs. this note's use of them:** each summary above reflects the paper's own stated finding and horizon, not a claim that the paper validates this system directly. Where a paper's asset class or holding horizon differs materially from this system's (weeks vs. minutes, equities vs. crypto), that difference is stated explicitly rather than glossed over.

---

**Author:** Oleg Arefev
**Project:** [Searching for Edge](https://github.com/Silent47boryara/searching-for-edge)
**Repository:** [Silent47boryara/searching-for-edge](https://github.com/Silent47boryara/searching-for-edge)
