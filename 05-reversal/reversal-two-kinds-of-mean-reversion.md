# 05 — Reversal: Two Kinds of Mean Reversion, One Closed on Sight

**Author:** Oleg Arefev
**Published:** August 2026
**Status:** `Published` · `Open` — Branch A `Closed` (literature-based, no own replication) · Branch B `Open` (own replication not yet run)
**Class:** Literature-based; Branch B requires its own exchange replication before it can be closed with a verdict

**Research question:** the literature offers two completely different strategies that both get called "reversal" in crypto. Neither comes with a ready-made, retail-executable recipe out of the box. This note walks through both, closes one of them at the literature stage, and keeps the other open for its own replication.

---

## Why this note exists

A prior internal experiment in this project tried a shortcut: reversing our own signal-detector's cancelled trades into short positions, hoping to harvest a reversal edge from our own data without reading any external literature. Tested twice, on 60 then 100 trades — it lost money both times, with no stable pattern behind the losses. That result isn't published here as a numbered note: it wasn't testing a published hypothesis, it was our own idea, and it failed. It stays as an internal record, not a "Searching for Edge" entry — the whole point of this series is testing what's been published, not our own guesses.

What *is* published, and worth testing properly, are two genuinely different academic claims that both use the word "reversal." Confusing them would be a mistake, so this note keeps them fully separate.

## Branch A — Dobrynskaya (2021/2023): buy what just crashed, hold for months

**The paper:** Victoria Dobrynskaya, "Cryptocurrency Momentum and Reversal," *Journal of Alternative Investments*, Summer 2023, 26(1), 65–76 (HSE University; first circulated 2021). Sample: ~2,000 cryptocurrencies with market cap above $1 million, CoinMarketCap-aggregated daily data, 2014–2020.

**What it actually found:** sorting coins by trailing return and holding short (1–4 weeks) produces momentum. Sorting by trailing return and holding *long* (10–12 weeks) reverses the sign — the "loser" leg starts outperforming the "winner" leg, and the effect grows the longer you hold. The strongest version: sort by the most recent 1–2 week return, hold the loser basket for 12 weeks. The paper's own headline framing: this behaves like a bubble-and-burst pattern, and the practical version they highlight is long-only — buy the past losers, skip the short leg entirely, since shorting a broad tail of small coins is difficult in practice.

**Why the previous discussion in this series didn't just wave this through.** Two problems, found by re-reading the paper directly rather than trusting the headline number:

1. **No survivorship or delisting treatment anywhere in the methodology.** The only filter is a $1 million market-cap floor at the point a coin enters the sample. There is no discussion of what happens when a "loser" coin keeps falling, delists, or goes to zero — which is exactly what the loser leg, by construction, is most exposed to. This is the same failure mode as the classic De Bondt–Thaler "loser portfolio" critique in equities: a portfolio built from things that just crashed is disproportionately built from things that are dying, not things that are merely oversold. Whether the paper's headline return quietly loses its worst cases (because a delisted coin simply drops out of CoinMarketCap's feed) or honestly marks them as a total loss is not addressed in the text — and it changes the number either way.
2. **The sample ends in 2020 — before the crashes that would test this claim hardest.** Terra/Luna (May 2022), FTX (November 2022), Celsius, and the broader 2022 collapse wave all happened after this paper's data ends. A "buy what just fell, it'll recover in a few months" claim built entirely on a period before the crypto market's largest well-known permanent wipeouts is untested against exactly the scenario a skeptical trader should worry about most.

**What this means in plain terms:** this is not a ready trading recipe. It's an academic finding about the *average* behavior of a large, equal-weighted, mechanically defined basket of losers — not a method for picking which specific coins are worth buying when they crash. Concentrating into a handful of personally trusted names (an appealing large-cap like BNB, for instance) is a fundamentally different bet than the one the paper measured: the published number comes from averaging across dozens-to-hundreds of positions at once, which is precisely what makes idiosyncratic disasters wash out in the aggregate. A five-coin, hand-picked version has no diversification cushion and no support from this paper's numbers — picking by personal preference at that point *is* a hypothesis, not a tested strategy, and should be labeled as one rather than dressed up as "backed by research."

**Status: Closed, without a retail replication.** This is a literature-stage closure, on the same discipline this series applied to Grid and Trend: if the published evidence already answers the practical question, running our own numbers just re-derives what's already visible.

The reasoning here is specific, not a blanket dismissal of the paper's statistics. The instrument the paper actually tested — an equal-weighted basket of dozens-to-hundreds of losers drawn from a ~2,000-coin academic universe, held for months — has no natural, unmodified translation into a retail-sized portfolio. Any attempt to shrink it down (to 30 coins, to 10, to a handful of personally trusted large-caps) stops being a test of this paper's finding and starts being an untested strategy of our own invention, wearing the paper's citation as borrowed credibility. That's a different, weaker failure mode than "the effect isn't statistically real" — the paper's diversified academic result may well be real on its own terms. It just isn't a strategy in the sense this series needs one to be: something one account, with one exchange, at retail size, can execute as specified.

Two things sharpen the closure rather than soften it. First, the sample (2014–2020) predates the market's largest permanent wipeouts — Terra/Luna, FTX, Celsius — so the "losers bounce back in a few months" pattern was never tested against the exact scenario a retail trader building this strategy today should worry about most. Second, the paper's methodology has no delisting or survivorship treatment at all — only a $1 million market-cap floor at entry — meaning the loser leg, the one leg this strategy would concentrate a retail account into, is also the one leg least checked for what happens when a position simply goes to zero.

No candidate-selection scheme, however carefully pre-registered, fixes a mismatch between what was measured and what would be traded. This branch is closed without an own replication.

## Branch B — Bianchi, Babiak, Dickerson (2022): short-term reversal in low-volume pairs

**The paper:** Daniele Bianchi, Mykola Babiak, Alexander Dickerson, "Trading volume and liquidity provision in cryptocurrency markets," *Journal of Banking & Finance*, 142 (2022), 106547. Sample: cryptocurrency pairs traded against USD/USDT, March 2017 – March 2022, aggregated and also broken out by individual exchange (Poloniex, HitBTC, GateIO, BitTrex, Binance).

**What it actually claims — a different, more mechanical bet than Branch A.** Each day, coins are split by de-trended trading volume (relative to their own recent average, not an absolute cutoff). Within the low-volume group specifically, a short-term reversal strategy is applied: buy what fell yesterday, sell/short what rose yesterday, hold one day, rebalance daily. The economic story isn't "this was oversold and will recover over months" — it's a market-making bet: get paid for absorbing temporary panic in a segment where few professional market makers compete for the same spread. Headline numbers: equal-weighted low-volume conditional reversal, 1.26%/day gross (p=0.001) versus 0.54%/day on high-volume pairs; value-weighted, 0.65%/day low-volume versus −0.19%/day (insignificant) high-volume.

**Why this is the branch that stays open.** It's a single-exchange, short-holding-period strategy — no multi-month conviction call on any specific coin's survival, no concentration risk on a handful of favorites, and it comes with the paper's own exchange-by-exchange breakdown (Table 7), which is a rare and useful thing: it tells us in advance where the effect held up net-of-fees and where it didn't, rather than leaving us to guess.

- On Binance specifically, gross returns were already smaller than the other four exchanges, and net of fees the equal-weighted result flips to **−0.213%/day** (significant), value-weighted **−0.341%/day** (significant).
- On the other four — Poloniex, HitBTC, GateIO, BitTrex — the net-of-fees result stayed positive and significant. GateIO specifically: **+0.811%/day** net, equal-weighted.

**Status: Open — concrete and well-specified enough to actually replicate.** This doesn't mean it's already confirmed to work for us; it means the next step is clear rather than requiring us to invent a methodology the paper doesn't provide. A retail replication would need: pick one exchange to start with (Gate is the natural first choice — Oleg has an account there, and it shows the strongest net result in the paper), pull recent OHLCV and volume data (not 2017–2022 — the same regime-aging caution as the Trend note applies here too, since the paper's own sample ends in March 2022 and crypto market structure has moved on since), compute de-trended volume per pair, replicate the low-volume conditional reversal with Gate's actual current fee schedule, and run it through the same significance tests used in the Momentum note (Part II): bootstrap CI, sign-flip, permutation.

## What isn't decided yet

Branch B has no net-of-costs number from our own data yet — it stays `In progress`, not `Published`, until that replication happens, consistent with how this series treats every other hypothesis: a positive-sounding literature number is a starting point for our own test, not a result to publish as-is. Branch A required no such replication to close: the mismatch between what was measured and what a retail account can trade was visible from the paper itself.

---

## References

- Dobrynskaya, V. (2021/2023). "Cryptocurrency Momentum and Reversal." *Journal of Alternative Investments*, 26(1), 65–76.
- Bianchi, D., Babiak, M., Dickerson, A. (2022). "Trading volume and liquidity provision in cryptocurrency markets." *Journal of Banking & Finance*, 142, 106547.

---

**Author:** Oleg Arefev
**Project:** [Searching for Edge](https://github.com/Silent47boryara/searching-for-edge)
**Repository:** [Silent47boryara/searching-for-edge](https://github.com/Silent47boryara/searching-for-edge)
