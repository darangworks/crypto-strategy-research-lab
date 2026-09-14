# Experiment 002 — Pre-Registration

**Experiment ID:** 002_momentum_btc_eth_sol_4h
**Type:** Exploratory / Calibration
**Date frozen:** 2026-09-14
**Status:** FROZEN — no modifications after this commit

---

## Research Question

Does cross-sectional relative strength at time t carry predictive
information about future 4H returns across BTC/ETH/SOL?

---

## Hypothesis

Assets with stronger recent relative performance continue to
outperform the weaker ones over the next short horizon.

---

## Economic Mechanism

Information diffusion asymmetry: large-cap crypto (BTC) reacts first,
alt-L1s (ETH, SOL) follow with lag. Persistent order-flow and
attention-driven demand create short-term relative-strength
continuation.

---

## FROZEN SPECIFICATION

### Universe
- BTC-USD, ETH-USD, SOL-USD
- 4H timeframe
- Source: existing frozen CSVs at `data/001_btc_4h/` (BTC) and
  `data/002_btc_eth_sol_4h/` (ETH, SOL) — same time window as Exp 001

### Ranking variable
- Lookback: exactly 6 bars (24h)
- Selected ex ante as a simple short-horizon specification.
- Signal[t] = log(Close[t] / Close[t-6]) for each asset

### Portfolio construction
- Long-only, top-ranked asset only
- Position: 100% in highest-ranked asset
- Target allocation evaluated every bar (4H)
- Execution: signal at close of bar t, fill at open of bar t+1
- Tiebreak: BTC (documented when triggered)

### Costs
- Commission: 0.05% per side
- Slippage: 0.02% per side
- Costs applied only when target asset changes AND actual position
  transition occurs.
- First entry (from initial flat state) and final exit charged as
  normal position transitions.

---

## METRICS

### Primary predictive metric (Layer 1)
For each timestamp t:
    spread[t] = next_bar_return[top-ranked asset at t]
              − next_bar_return[bottom-ranked asset at t]

Reported statistic: time-series mean of spread[t].
Expected sign: positive.

### Secondary strategy metric (Layer 2)
- Annualized Sharpe (4H bars)
- Net PnL (full cost)
- Profit factor
- Win rate
- Max drawdown
- Trade count

---

## VERDICTS (three independent layers)

### Predictive layer (OOS)
- OOS mean spread > 0  → PASS
- OOS mean spread = 0  → INCONCLUSIVE
- OOS mean spread < 0  → FAIL

### Strategy layer (OOS)
- OOS Sharpe > 0  → PASS
- OOS Sharpe = 0  → INCONCLUSIVE
- OOS Sharpe < 0  → FAIL

### Overall (derived, not pre-registered as single criterion)
- Both PASS  → PROMISING
- Both FAIL  → REJECTED
- Mixed      → INCONCLUSIVE

---

## Bootstrap

- Stationary block bootstrap
- 2000 iterations
- Seed: 20260913
- Applied separately to:
  - OOS spread[t] series → CI for mean spread
  - OOS portfolio-return series → CI for mean portfolio return

### Predictive bootstrap criterion
- 95% CI for mean spread entirely above 0 → supporting evidence
- 95% CI includes 0                      → INCONCLUSIVE
- 95% CI entirely below 0                → FAIL

### Strategy bootstrap criterion
- Same rule applied to mean portfolio return.

---

## OOS split

Single 50/50 chronological split on the aligned multi-asset timeline.

---

## Additional validation layers

- Causal / leakage suite (adapted for cross-sectional alignment)
- Walk-forward (single 50/50) — same as above

---

## Falsification Criteria

The hypothesis is falsified if:
1. OOS mean spread < 0 (predictive layer FAIL), OR
2. OOS Sharpe < 0 (strategy layer FAIL), OR
3. Both bootstrap CIs include 0 (both layers INCONCLUSIVE)

These are pre-registered classification rules for evidence.
A single FAIL does not prove "momentum does not exist" — it
classifies evidence against the tested specification.

---

## Why this is not Experiment 001 in disguise

- Signal family: relative strength vs. reversal
- Treatment: cross-sectional vs. single-asset
- Primary metric: spread-based predictive test vs. backtest Sharpe
- Failure mode: momentum crash vs. reversal breakdown

---

## Prohibitions

- No parameter search over lookback
- No filter additions
- No regime conditioning
- No "best of N" selection
- No modification of any value in this document after freeze

---

## Constraints

- Reuse `engine/backtest.py`, `engine/data_loader.py` as-is
- Reuse `validation/leakage` structure
- New strategy file: `strategies/cross_sectional_momentum/`
- New experiment folder: `experiments/002_momentum_btc_eth_sol_4h/`

---

## Data freeze requirement

Before any experiment-specific code is run, ETH-USD and SOL-USD 4H
data must be added to the frozen dataset with SHA-256 manifest
for the same time window as BTC-USD 4H used in Experiment 001.

Data acquisition is a one-time step and must be committed before
any experiment runner is written.

---

## Freeze rule

After this document is committed:
- Specification changes require a NEW experiment.
- Modifications to this file are prohibited.
- Any deviation detected in code or results invalidates the
  experiment.