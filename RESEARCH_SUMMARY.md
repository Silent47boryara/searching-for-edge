# Findings from BOS and the collector laboratories

Prepared on 16.10.2026 from the completed studies of 13–14.10. This document contains no new calculations.

## Main conclusion

BOS implementation errors exist, but a targeted correction neither explains nor eliminates the negative results. The lower timeframes are associated with movement that has already occurred; a reliable predictive edge has not been established. Derivatives feeds describe measurable market processes; a stable forecasting improvement beyond price and volatility has not been found.

## Why BOS seemed promising

The project documents record an initial aim of detecting large movements and monitoring their development. A retrospective relabelling found 93.5% coverage of 138 available completed hourly 8% waves, with a median lag of 35 hours among detected waves. This is a meaningful coverage result, but it is not accuracy across all signals, an early entry, or profit. A state can appear in almost every large wave while also appearing frequently without useful continuation.

## What was established

| Question | Result | Limit of the conclusion |
|---|---|---|
| Is the code correct? | Discrepancies involve displayed versus operative break levels, ENDED summaries, closed candles, NONE on data errors, and the swing-confirmation boundary | Interface errors must be distinguished from changes to the exit specification |
| Does correcting the BOS lag rescue it? | 0.62% of hourly states change over the long history; descriptive balanced accuracy 52.45% → 52.41% | Agreement with the past 12-bar net move, not a win rate |
| Is BOS pure randomness? | The 1H/4H descriptive score exceeds random circular shifts of the state sequence | Association with past movement does not forecast the future |
| Does a stricter exit help? | Some descriptive metrics improve, but the model changes substantially and the old gamma/tape leads weaken | A new specification, not a simple bug fix |
| What do collectors provide without BOS? | Liquidations correlate with current volatility: Spearman 0.82; tape activity: 0.76 | A contemporaneous relationship is not an early warning |
| Do they improve the next 4h forecast? | None of the 24 primary comparisons is significant; all Holm-adjusted p-values are 1 | Small sample and wide intervals; not proof of a zero effect |

A simple EMA20±0.5ATR agreed better with the chosen descriptive label than BOS (1H: 74.70% versus 52.45%). Its construction is closer to the label itself; this is neither evidence of EMA profitability nor a ready replacement.

## Interesting but unconfirmed results

- **OI + liquidations:** a 1.8% reduction in MSE for future 4h returns relative to price; interval approximately [−5.3%; +6.8%], with improvement in 2 of 5 weeks. The substantive question is whether shrinking contract counts and growing OI distinguish outcomes after comparable price movements.
- **Gamma + tape:** a 9.8% reduction in MSE for future 4h volatility; interval [−9.0%; +24.7%], 53 observations / 14 days / 3 blocks. Excluding block/combo/RFQ trades: −1.2%. The effect is sensitive to tape composition.
- **Tape before 1H BOS starts:** N=14, rho with MAE24 +0.618; unchanged after the lag correction. The old candidate did not survive multiple-testing correction.
- **Gamma at timeframe transitions:** N=36, rho −0.580; after the lag correction N=35, rho −0.562. Selected after examining many tests; requires new data.

MSE improvements are not returns. MAE correlations are not trading rules. Model sets have different available observations, limiting absolute comparisons between them.

## What remains useful

Price + changes in OI + liquidation side + funding + tape composition/activity provide an observational map: are contracts shrinking, are forced closures occurring, what are the holding conditions, and what kind of option activity is taking place? Its incremental value for a specific decision has not been measured. Unsigned gamma does not reveal dealer positions; call-minus-put taker flow is not their hedge.

The literature supports studying levels and breakouts, but does not validate our particular swing/EMA/ATR/volume filters and three timeframes. Correcting what the displays mean is justified; promising accurate BOS afterwards is not.

Full definitions, checks, limitations, and sources are in the laboratory reports linked from README.
