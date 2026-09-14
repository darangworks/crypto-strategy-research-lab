# Assets

This release intentionally contains no generated plots.

- Canonical results live in each experiment's frozen artifacts:
  experiments/001_rsi_btc_4h/ and experiments/002_momentum_btc_eth_sol_4h/.
- Consolidated summary of both experiments is in OVERVIEW.md.
- Interpretation per experiment is in that experiment's VERDICT.md.

The absence of image assets is a scoping decision, not a statement
about the strength of the results. Plot generation was deliberately
deferred; if a later release needs visualizations, they will be
produced from the frozen results.json, walkforward.json, and
bootstrap.json files without re-running any strategy code.