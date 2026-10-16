# BOS: what the primary sources establish

13.10.2026. A focused review of definitions and evidence, not an exhaustive systematic review. The methodology/conclusion sections of the papers below, exchange pages, and the original ICT video descriptions were read. The full ICT lecture was not watched; no verified transcript was available here. Not finding a paper does not establish that none exists.

## 1. Where the idea comes from

Breaks of previous highs/lows and sequences of rising/falling extremes belong to the broader tradition of technical analysis. The modern BOS/CHoCH/MSS labels are used in price action / SMC / ICT, but do not define one universally accepted computational model. The level, scale, touch versus close, trend before the break, confirmation of the extreme, and event invalidation each require separate rules.

[CME: Support and Resistance](https://www.cmegroup.com/education/courses/technical-analysis/support-and-resistance) explains previous extremes and resistance becoming support after a breakout. This explains the project's intuition; the page does not statistically validate our BTC detector.

[CME: Technical Patterns — Reversals](https://www.cmegroup.com/education/courses/technical-analysis/technical-patterns-reversals) links confirmation of certain reversal patterns to a break of an intermediate extreme. It describes a pattern and its confirmation condition, not guaranteed continuation.

[ICT, 2022 Mentorship Episode 3](https://www.youtube.com/watch?v=nQfHZ2DEJ8c) is on the instructor's original channel and concerns internal range liquidity / market structure shifts. [Another original lesson](https://www.youtube.com/watch?v=Bkt8B3kLATQ) mentions FVG and MSS. Authorship/descriptions were checked, not the complete lectures. These videos must not be presented as peer-reviewed evidence of an edge, or our code as an exact reproduction of the course.

The code adds project-specific rules: a 5-bar extreme, EMA50±0.7ATR, Volume>1.05MA20, a 0.1% breakout tolerance, and the same state machine on 1H/4H/1D. These exact thresholds do not follow from the cited sources. They form an independent specification tested by the replay.

## 2. Research relevant to the question

| Primary source | Subject | Supported conclusions and limits |
|---|---|---|
| [Brock, Lakonishok, LeBaron (1992), Journal of Finance](https://onlinelibrary.wiley.com/doi/abs/10.1111/j.1540-6261.1992.tb04681.x); [authors' SFI working paper](https://sfi-edu.s3.amazonaws.com/sfi-edu/production/uploads/sfi-com/dev/uploads/filer/17/91/1791d085-e000-427d-a5d2-94d20b072bcb/91-01-006.pdf) | Moving averages and trading-range breakouts on the DJIA, 1897–1986 | Breakouts are a testable rule family, not inherently meaningless. The market, period, and algorithm differ; the result cannot be transferred to our BOS. |
| [Sullivan, Timmermann, White (1999), Journal of Finance — full text at LSE](https://eprints.lse.ac.uk/119144/1/dp303.pdf) | A large family of technical rules, Reality Check, and the following 10 years | The original BLL results survived their correction, but the advantage did not recur in 1987–1996. A warning against selecting favourable settings and attractive historical examples, not proof that all breakouts are useless. |
| [Lo, Mamaysky, Wang (2000), Journal of Finance — author's full text at MIT](https://web.mit.edu/wangj/www/pap/LoMamayskyWang00.pdf) | Algorithmic chart-pattern recognition and conditional stock-return distributions | Some patterns contain incremental information. The authors note that this need not imply excess profits. They do not test our 5-bar BTC BOS or validate its thresholds. |
| [Osler (2000), NY Fed, Support for Resistance](https://www.newyorkfed.org/medialibrary/media/research/epr/00v06n2/0007osle.pdf) | Levels from six FX firms and interruptions of intraday trends | Levels could matter, but quality depended on the firm/pair. These are participants' levels, not automatically our local pivots. |
| [Osler (2001/2003), Currency Orders and Exchange-Rate Dynamics](https://www.newyorkfed.org/research/staff_reports/sr125.html) | Stop-loss and take-profit orders at a large FX bank | A microstructure explanation for pauses at levels and acceleration after breakouts. It relies on order placement and round levels; an arbitrary high/low is not thereby a proven liquidity cluster. |
| [Borgards (2021), Dynamic time series momentum of cryptocurrencies — published full text](https://community.portfolio123.com/uploads/short-url/amrMsuqIKzdHcHHyvMud4YNPwZB.pdf), DOI 10.1016/j.najef.2021.101428 | Cycles built from peak/trough sequences, 20 cryptocurrencies; 1D/1H/5m | A conceptually related structural approach, but turning points use a different smoothing algorithm. Not validation of our BOS. The strategy includes a 0.2% fee with simplified slippage; at 5m, fees consume the average gross return. Replication would require checking when turning points become available, not copying the reported result. |

## 3. Corrections to the earlier interpretation

1. **BOS is not automatically validated TSMOM.** The link is conceptual: past movement supports a description or continuation hypothesis. A BOS–EMA correlation of 0.389 proves neither theoretical identity nor an edge.
2. **An academic statistical structural break is a different concept.** A change in distribution/model parameters is not the same as a close above a swing high. Matching terminology does not validate BOS.
3. **Define first, test second.** “Classic BOS” still requires choices about swings, confirmation, invalidation, and availability time. Our EMA/volume filters can remove extremes visible on a chart; this is a limitation of the specific model.
4. **Information, observation, and profit are different claims.** Even an accurate description of past movement guarantees nothing about the remaining move or an executable trade.
5. **The literature does not justify adding gamma to any BOS.** A specific mechanism, observable quantity, and test are required. Unsigned gamma OI does not identify dealer-position signs; taker call-minus-put notional is not an observed dealer delta position/hedge.

## Conclusion

The original intuition about levels and breakouts has a reasonable origin. The belief that a particular set of thresholds and three such timeframes would accurately map the market was the project's own hypothesis. The reviewed literature neither turns it into a fact nor requires rescuing it with another setting. Any new model would need a different testable specification addressing a specific defect, rather than a new BOS label.
