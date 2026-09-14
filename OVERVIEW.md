# Research Overview

Program-level map of the Crypto Strategy Research Lab.

For the front door, see README.md.
For reproduction, see REPRODUCE.md.

---

## Central experiment matrix

| # | Hypothesis | Assets | TF | Bars | Data Frozen? | Spec Frozen? | Leakage | WFO | Bootstrap | Final |
|---|------------|--------|----|------|--------------|--------------|---------|-----|-----------|-------|
| 001 | RSI mean reversion (14/30/50) | BTC-USD | 4H | 4,334 | YES (SHA-256) | YES | PASS | FAIL | INCONCLUSIVE | REJECTED |
| 002 | Cross-sectional momentum (lookback=6, top-1, BTC>ETH>SOL) | BTC/ETH/SOL | 4H | 4,334 (common) | YES (SHA-256) | YES | PASS | REJECTED | INCONCLUSIVE | REJECTED |

---

## Validation layers (applied to both experiments)

| Layer | Question | Criterion |
|-------|----------|-----------|
| Pre-registration | Was the specification fixed before results? | Documented + committed before run |
| Baseline | What does the spec produce on frozen data? | Observation only |
| Leakage | Does the pipeline use future information? | Structural invariants + oracle detection |
| Walk-Forward | Does in-sample behavior persist OOS? | Pre-registered criterion |
| Bootstrap | What is the sampling uncertainty? | CI-based criterion |
| Independent audit | Is the accounting correct? | Bar-by-bar reconstruction, max abs diff = 0 |
| Frozen verdict | What is the overall conclusion? | Derived from layer verdicts |

### Walk-forward criterion (Exp 001)

OOS Sharpe greater than 0 means PASS. Equal to 0 means INCONCLUSIVE. Less than 0 means FAIL.

### Walk-forward criterion (Exp 002, two independent layers)

Predictive: OOS mean_spread greater than 0 means PASS. Equal to 0 means INCONCLUSIVE. Less than 0 means FAIL.

Strategy: OOS Sharpe greater than 0 means PASS. Equal to 0 means INCONCLUSIVE. Less than 0 means FAIL.

Overall: both PASS means PROMISING. Both FAIL means REJECTED. Mixed means INCONCLUSIVE.

### Bootstrap criterion (both)

95 percent CI of the relevant OOS statistic entirely above 0 means PASS. Includes 0 means INCONCLUSIVE. Entirely below 0 means FAIL.

---

## Data construction

### Experiment 001 — single asset

BTC-USD 4H from yfinance. Frozen snapshot with SHA-256 manifest in data/001_btc_4h/. 4,334 bars, 2024-09-14 to 2026-09-13 UTC.

### Experiment 002 — multi asset, cross-source

BTC-USD from yfinance (same canonical snapshot as Exp 001, byte-exact copy). ETH-USD and SOL-USD from Binance public klines API.

Sources did not share identical timestamp grids: BTC had 5 gaps vs Binance's uniform 4H.

Amendment 001 (pre-results): analysis universe equals intersection of timestamps present in all three assets. No interpolation, no forward-fill, no silent dropping. Recorded before any momentum computation.

Result: common 4,334-bar grid. Frozen snapshot with SHA-256 manifest in data/002_btc_eth_sol_4h/.

---

## Experiment 001 — RSI mean reversion

| Segment | Trades | Net PnL | Sharpe |
|---------|--------|---------|--------|
| Full baseline | 31 | +1,393.73 | 0.313 |
| Walk-forward IS | 15 | +3,328.68 | +1.558 |
| Walk-forward OOS | 16 | -1,872.61 | -0.757 |

Leakage suite: PASS (4 tests, incl. random-walk oracle).

Bootstrap (mean 4H return): CI includes 0, INCONCLUSIVE.

Verdict: REJECTED / NOT PROMOTED.

## Experiment 002 — Cross-sectional momentum

| Segment | Trades | Net PnL | Sharpe |
|---------|--------|---------|--------|
| Full baseline | 1,159 | -78,027.73 | -0.859 |
| Walk-forward IS | 554 | +879.84 | +0.361 |
| Walk-forward OOS | 606 | -78,548.32 | -2.344 |

Leakage suite: PASS (7 tests, incl. cross-asset-specific invariants).

Walk-forward predictive: OOS mean_spread equals -0.00011845, FAIL.

Walk-forward strategy: OOS Sharpe less than 0, FAIL.

Overall WFO: REJECTED.

Bootstrap strategy layer: CI95 equals [-0.00115, -0.00011], FAIL.

Bootstrap predictive layer: CI95 equals [-0.00042, +0.00020], INCONCLUSIVE.

Verdict: REJECTED / NOT PROMOTED.

### Note on WFO vs Bootstrap predictive divergence (Exp 002)

The pre-registered WFO criterion for the predictive layer was sign-based (mean_spread greater than 0). The pre-registered bootstrap criterion was CI-based (95 percent CI greater than 0). These answered different questions:

- Sign: is the point estimate positive?
- CI: is zero within sampling uncertainty?

Both criteria were applied literally. Their divergence (FAIL vs INCONCLUSIVE) is documented, not reconciled post-hoc.

---

## What this pipeline does NOT claim

- Does not claim either strategy family is inherently unprofitable.
- Does not claim the crypto markets are unpredictable.
- Does not prove that no edge exists anywhere.
- Does not generalize beyond the tested specifications, data windows, and validation protocols.

## What it does claim

1. Both specifications were frozen before execution.
2. Both were exercised through the same validation protocol.
3. Both were rejected under pre-registered criteria.
4. The pipeline itself is reproducible and auditable.

---

## Limitations

- Single walk-forward split per experiment. No rolling WFO, no purging, no embargo.
- Bootstrap block length collapsed to 1 under the ACF rule in both experiments. Cross-sectional and contemporaneous correlations preserved; temporal dependence beyond one observation not preserved.
- Experiment 002's cross-source data construction required a documented analysis-universe rule (Amendment 001); the frozen BTC canonical from Experiment 001 is byte-exact, but the common grid drops 44 Binance-only timestamps.
- Sample sizes are small: 31 baseline trades (Exp 001), 1,159 (Exp 002). Neither is sufficient to establish robust statistical significance.

---

## Program roadmap

See reports/program-roadmap-v1.md for the frozen roadmap. Current state:

- Phase 0 (Foundations): Projects 1 and 2 complete.
- Phase 1 (Public release): in progress.
- Phases 2-7: subsequent experiments, when justified by evidence.

---

## Lessons index

- Experiment 001 lessons: knowledge/lessons/exp-001.md, 7 lessons.
- Experiment 002 lessons: knowledge/lessons/exp-002.md, 7 lessons.

Key recurring themes:

- Provenance is part of research validity.
- Independent audit is a two-way discipline.
- Negative results are first-class outputs.
- Pre-registered criteria must be applied literally.
- A research system should make it easier to reject a hypothesis than to rationalize it.

---

## License

Code: MIT (see LICENSE).
Documentation: CC BY 4.0 (see LICENSE-DOCS).