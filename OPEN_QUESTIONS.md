# Open questions

These are research directions, not discovered strategies. Rules for a new test must be fixed before inspecting its outcomes. Data up to the laboratory cutoff have already been used for discovery; subsequent data cannot automatically be called independent confirmation if the rules were adjusted after inspecting them.

| Question | Why it remains interesting | What is needed |
|---|---|---|
| Can OI + liquidation side distinguish recovery from continuation after a similar decline? | Different processes are measured; a weak positive predictive result for the pair | Predefined regimes and outcome, controls for past price/volatility, new events, and feed-health checks |
| Does option-trade composition contain information about future risk? | Gamma+tape produced a positive result that depended on block/combo/RFQ trades | Separate ordinary from structured trades; respect exchange and receive times; new data without selecting a favourable composition |
| Do the old tape/BOS and gamma/transition relationships replicate? | The small lag fix preserved them | Frozen definitions, the original event specification, a separate new sample, and correction for the test family |
| Does the state map help a decision? | Current liquidations and tape activity measure stress in a meaningful way | Choose a specific decision and loss function; compare against contemporaneously available price, without future information |
| What should the BOS contract be? | The interface mixes active states, completed impulses, invalidation levels, and trading labels | Specify the operative break, closed-candle rules, DATA_UNAVAILABLE, and availability time separately, then run a targeted replay |

## What remains unresolved

- The corrected research candidate has not been deployed to production.
- No complete independent audit by another researcher has been conducted.
- The multiyear daily replay is limited to a conservative subsample of 794 bars.
- An executable strategy after costs and slippage has not been established.
- There is no basis for claiming that all uses of BOS or derivatives data are useless.
- There is no basis for continuing arbitrary filter searches to obtain a positive number.

Practical priorities: reliable continuous collection, correct interpretation of measured quantities, and a small number of predefined questions. Operational checks after the Mac wakes from sleep are not new validation of research hypotheses.
