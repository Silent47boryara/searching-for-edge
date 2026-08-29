# 00 — Can You Trade Crypto Profitably by Formula?

**Status:** `Published`

Yes. But "profitably" is the wrong benchmark.

## Where this started

The question that started all of this was simpler than it sounds: if there are hundreds of ready-made tools for analyzing the market, why can't I just take one and get an edge?

I went through a marketplace of about 200 pre-built trading skills and strategies (a "CMC Skill Hub"), shortlisted around 15, and reverse-engineered the mechanics of each: open interest, funding, flow imbalance, liquidations, ATR, holder concentration. The audit's conclusion was simple and a little deflating: there was almost no unique data underneath. Nearly everything was a combination of the same public metrics anyone can compute. What was useful was different: a taxonomy of market hypotheses and a sense of which variables were even worth testing — all reproducible for free on Binance data, without buying anything.

Behind this sits an idea I want to name plainly: the "copy-paste bot." Take ready-made code from a marketplace, copy it, and you have a bot that signals something and looks, on the inside, like a serious black box. I did a real reverse engineering pass on one of these. It turned out to be almost embarrassingly simple: the same free Binance metrics, just wrapped in a polished interface and sold as proprietary technology.

That led to a sharper question: if almost everyone is looking at the same data and computing roughly the same indicators, where does profit actually come from?

## Klines: the first system of my own

Before this question, I already had a real-time system of my own — Klines: an event-driven detector on Binance that looked for abnormal volume and price acceleration, gathered context around each signal, and tracked what happened next. Months of replay analysis, individual case reviews, and signal-quality classification went into it.

The conclusion it produced became the fork in the road for everything after: detecting an abnormal event turned out to be considerably easier than knowing, at the moment it happens, whether it will continue or end in exhaustion or reversal. Fully automated trading built on this premise did not survive an honest execution audit — that's a separate note. But the failure didn't become a reason to pile on more indicators. It became a reason to go back and ask what the academic literature actually knows about how short-term price moves form.

## What came next — a method, not a single hypothesis

I didn't test one idea. I took four different, independent candidates for a systematic edge — momentum, trend-following, funding carry, reversal — and ran each through the same discipline, without exceptions: literature first, taken at face value, with no reference to my own data; then mechanism reconstruction; then an honest replication on Binance; then — mandatory — subtracting real costs; then testing for statistical significance, not eyeballing a nice-looking chart.

The rule was strict from day one: a maximum of two published, independently sourced implementations per hypothesis class. Not endless parameter sweeps looking for the version that finally turns green. If both implementations fail, the class is closed. Full stop — not "maybe a third filter will save it."

A fifth item stood apart from the start: grid bots. That isn't a market pattern — it's a question of execution economics, and it gets its own treatment outside the four-candidate protocol. Spoiler: the shiny storefront on the marketplaces and the real numbers behind it are two different stories, and the expected value there really is positive. The question is positive for whom — that's its own note.

For the same reason, I deliberately stayed out of scalping and HFT. Not because I didn't consider it — by definition. If your counterparty has millisecond execution latency and you have retail infrastructure, that isn't your environment, and walking in is a structurally losing position. A retail trader doesn't fail there for lack of skill — they fail on the physics of execution.

## Why this never ends

While putting this research together, I noticed something simple: Binance has, for years, kept quantitative researcher positions open continuously — including roles explicitly welcoming fresh STEM PhD graduates ([Binance — Quantitative Researcher, Fresh STEM PhD graduates welcome](https://jobs.lever.co/binance/92d1635d-0a98-4023-b854-b6c7ed07aa35)). And you know what? They'll always be hiring.

Not because something is broken. Because there is no single stable theory or hypothesis that works forever. The market is a living organism: once a pattern is found and capital starts exploiting it, the market adapts, execution changes, and the effect compresses. The people on the other side of the trade will keep adapting indefinitely to keep extracting profit — which is exactly why that position stays open, not as a one-off, but permanently. A paper that proved an edge in 2019 is under no obligation to prove it in 2026 — and this series contains at least one case where exactly that happened.

## Academia — not reading, adapting

From there I went into the academic literature — and that turned out not to be a one-time read. More than 20-30 papers were reviewed: momentum, reversal, carry, market microstructure, pump detection, meta-labeling. The bibliography at the end of this series will be substantial.

But simply reading a paper isn't enough. A significant share of these studies end their sample around 2023 or earlier, and the market has since moved through a regime shift, an ETF-driven liquidity change, and shifting market structure. So every paper read was followed by adaptation: not "the author found X, so I should too," but a re-check against current Binance data — often with a different result than the original study.

## What's deliberately left out

Three topics came up repeatedly but won't be in this series — not because they're unimportant, but because each has its own honest barrier to entry.

Options and futures as a source of structural theories — a separate field with its own mechanisms (variance risk premium, market-maker delta/gamma hedging) — but in practice this is market-maker territory, not retail territory. I'm deliberately not going there.

Liquidations as signal context — an interesting and plausible hypothesis, but the research is still in progress: quality liquidation data (CoinGlass, Coinalyze) costs $30–200/month, and that investment decision hasn't been made yet.

"Insider" trading channels — not researched at all, and I try not to write about what I haven't researched. First impression: this is a field with far more scams than signal, so it stays out of scope here.

## What's coming

Next is a series of notes, one chapter per candidate. Each note is not a literature summary — it's a report: what the literature claims, what a replication on real Binance data showed, and exactly where and why the effect didn't survive the trip from paper to execution — or, in one case, survived mathematically but turned out to be economically not worth taking.

I'll open, appropriately, not with academia but with the most visual example of all.

**The Grid Bot Illusion.** A marketplace storefront that's genuinely impressive: someone posts +$5,000 in a day, and you look at the chart thinking "I should just copy the algorithm." But look closer at the portfolios behind those numbers — an estimated $500k–$1M. Is that a normal reference point for a retail trader? What if you ran your own grid bot with a normal-sized account on the same logic? You can — the mechanism isn't secret. But you run into the same wall every time: fees. The expected value there really is positive — just not for every account size or every fee tier. This gets its own note, outside the four-candidate protocol, because it's not a market pattern — it's a question of execution economics.

Then, four candidates run through one protocol:

**Momentum.** Two different lags, two independently published specifications, both run to completion — and both arriving at the same type of conclusion by different routes.

**Trend / Time-Series Momentum.** A recent academic replication on the current market regime — and what happens to a classic strategy when it's tested not on a 2013-2017 sample, but on today's data.

**Funding / Carry.** The one candidate where the expected value really was positive, and that's not a myth — but the first case in the series where the real question becomes "positive compared to what?"

**Reversal.** A story with two rounds of testing, one caught methodological artifact, and a clean reversal of the result between rounds — a rare case where you can watch a piece of research fool itself.

At the end: a synthesis — the three filters any idea has to pass before it can even be considered tradable, and what Klines itself became after this whole journey.

I've connected the folders holding the original findings and run logs — the numbers in each note will be pulled from there, not from memory.
