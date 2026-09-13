# Pre-Registration — Experiment 001

**Date:** 2026-09-13
**Status:** PRE-REGISTERED (before data freeze)
**Experiment type:** Exploratory / Calibration

---

## Experiment Type

Exploratory / Calibration.

This experiment is primarily intended to calibrate the research
lab and establish a reproducible baseline workflow.

It is **not** treated as confirmatory evidence for a trading edge.

Any subsequent parameter search or strategy modification will be
recorded as a separate exploratory experiment.

---

## Research Question

Can the research lab execute a complete, reproducible pipeline
from pre-registration to data freeze, backtest, and layer-level
validation?

Secondary question: does a fixed RSI mean-reversion baseline
produce any preliminary signal on BTC-USD 4H under realistic costs?

---

## Hypothesis

Extreme short-term selling (low RSI) may be followed by short-term
mean reversion at the 4H timeframe on BTC-USD.

This hypothesis is exploratory. It is not required to be confirmed
for Experiment 001 to be considered successful.

---

## Falsification Criterion

The experiment produces a **layer-level verdict** for each
pre-registered validation test.

A causal/leakage failure results in REJECTED.

Failure of an individual robustness layer does **not** automatically
invalidate the entire experiment.

---

## Market

BTC-USD (Yahoo Finance via yfinance)

---

## Timeframe

4H

---

## Data

- Source: yfinance
- Requested period: 730d
- Frozen snapshot: `data/001_btc_4h/`
- Frozen CSV is the canonical reference

---

## Signal Definition

- Indicator: RSI(14)
- Entry long: RSI crosses below 30 at close `t`
- Execution: open `t+1`
- Exit long: RSI crosses above 50 at close `t`
- Execution: open `t+1`
- No short side in Experiment 001

**Cross semantics (strict):**

Entry:
    previous_rsi >= 30 and current_rsi < 30

Exit:
    previous_rsi <= 50 and current_rsi > 50

**Causal correctness requirement:**

RSI is computed using only data up to and including close `t`.
No future OHLC is used in signal generation.
The engine must enforce this semantics exactly.

---

## Position Sizing

- Notional: 10% of equity per trade
- No leverage
- One position at a time

---

## Costs

- Commission: 0.05% per side
- Slippage: 0.02% per side
- Execution: next-open fill

---

## Primary Metric

**Frozen before backtest results are inspected.**

- Return series: bar-to-bar portfolio equity returns at 4H frequency
- Annualization factor: sqrt(6 * 365)
- Risk-free rate: 0
- Sharpe = mean(returns) / std(returns) * sqrt(6 * 365)

This definition is frozen.

---

## Secondary Metrics

- Net PnL
- Profit factor
- Win rate
- Max drawdown
- Trade count

---

## Validation Plan

**Required layers:**

1. Causal correctness
2. Walk-forward
3. Bootstrap CI

### Walk-forward Specification

- One chronological 50/50 IS/OOS split
- No parameter tuning on IS
- OOS evaluated exactly once

### Walk-forward Decision Rule

    OOS Sharpe > 0 -> PASS
    OOS Sharpe = 0 -> INCONCLUSIVE
    OOS Sharpe < 0 -> FAIL

### Bootstrap Specification

- Statistic: mean 4H bar-to-bar portfolio return
- Method: stationary block bootstrap
- Block length: estimated from ACF
- Iterations: 2000
- Confidence level: 95%

### Bootstrap Decision Rule

    CI entirely above zero -> PASS
    CI includes zero      -> INCONCLUSIVE
    CI entirely below zero -> FAIL

---

## Not Applicable to Experiment 001

### Parameter Stability
NOT APPLICABLE.

Reason: Only one pre-registered configuration is evaluated.

### Cross-Asset Validation
NOT APPLICABLE.

### Multiple Testing
NOT APPLICABLE.

N/A layers do not count as failures.

---

## Validation Interpretation

Each validation layer receives an independent verdict:
PASS / WEAK / FAIL / INCONCLUSIVE

### Decision Rules

| Layer | Result | Overall Status |
|-------|--------|----------------|
| Causal correctness | FAIL | REJECTED |
| Walk-forward | FAIL | REJECTED |
| Bootstrap | FAIL | REJECTED |
| Bootstrap | INCONCLUSIVE | INCONCLUSIVE |
| Walk-forward | INCONCLUSIVE | INCONCLUSIVE |
| All required layers PASS | - | PROMISING (exploratory only) |

A strategy cannot receive PROMISING or ROBUST status unless
causal correctness passes.

---

## Pre-Registered Parameters

    rsi_period: 14
    entry_threshold: 30
    exit_threshold: 50
    stop_loss_pct: null
    take_profit_pct: null
    holding_period_max: null

These parameters are fixed. No tuning will be performed under
Experiment 001.

---

## Specification Freeze Rule

After data freeze, specification changes require a new experiment.

If RSI(14) fails, testing RSI(7) or RSI(21) is allowed — but as
Experiment 002, not as a modification of Experiment 001.

---

## Notes

This is the first experiment in Project 2. Its primary purpose is
to calibrate the research lab, not to find a profitable strategy.
