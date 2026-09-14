# VERDICT — Experiment 002

**Experiment:** 002_momentum_btc_eth_sol_4h
**Strategy:** Cross-sectional momentum (BTC/ETH/SOL 4H, lookback=6, top-1)
**Data:** common 4,334-bar grid, 2024-09-14 → 2026-09-13 UTC
**Completed:** 2026-09-14
**Tags:** `exp-002-baseline`, `exp-002-wfo`, `exp-002-bootstrap`, `exp-002-frozen`

---

## Layer verdicts (per pre-registration)

| Layer | Verdict | Commit |
|-------|---------|--------|
| Baseline | observation (strongly negative) | 3506f6a |
| Causal / Leakage | 🟢 PASS | 5f48ecd |
| Walk-Forward | 🔴 REJECTED | 64cab28 |
| Bootstrap | 🟡 INCONCLUSIVE | 2211d76 |
| **Overall** | **🔴 REJECTED / NOT PROMOTED** | — |

---

## Final statement

> **Experiment 002 — REJECTED**
>
> Under the pre-registered specification, the BTC/ETH/SOL
> cross-sectional momentum strategy did not demonstrate robust
> out-of-sample predictive or trading performance.
>
> The 50/50 chronological walk-forward evaluation failed both the
> predictive and strategy criteria. The subsequent bootstrap
> analysis found statistically negative OOS strategy returns,
> while the predictive spread remained inconclusive under its
> confidence-interval criterion.
>
> These results do not prove that cross-sectional momentum cannot
> work in cryptocurrency markets. They show that this specific
> specification did not produce sufficient evidence of a robust
> edge under the tested protocol.

---

## Three-concept separation

### 1. Causal validity

Under the tested leakage pathways (A1 all-asset perturbation,
A2 single-asset perturbation, A3 future-data oracle, A4
specification check), no causal violation was detected. The
harness successfully detects an intentional `close.shift(-1)`
leak.

B1 (multivariate empirical-return bootstrap) is a descriptive
reference null, not a proof of absence of edge.

### 2. Predictive / out-of-sample evidence

Pre-registered single 50/50 walk-forward:

| Segment | trades | net_pnl | sharpe | mean_spread |
|---------|--------|---------|--------|-------------|
| IS  | 554 | +879.84 | +0.361 | +0.00015583 (n=2160) |
| OOS | 606 | −78,548.32 | −2.344 | −0.00011845 (n=2166) |

Pre-registered criteria:
- Predictive layer: OOS mean_spread > 0 → PASS
    OOS mean_spread = −0.00011845 < 0  → **FAIL**
- Strategy layer: OOS Sharpe > 0 → PASS
    OOS Sharpe = −2.344 < 0  → **FAIL**
- Overall: both FAIL → **REJECTED**

### 3. Statistical uncertainty (Bootstrap)

Stationary block bootstrap on OOS series, N=2000, seed=20260913:

| Layer | Observed | CI95 | Verdict |
|-------|----------|------|---------|
| Strategy (mean return) | −0.00063183 | [−0.00115, −0.00011] | FAIL |
| Predictive (mean spread) | −0.00011845 | [−0.00042, +0.00020] | INCONCLUSIVE |

Block length = 1 for both series (ACF-based rule).

**Divergence between WFO and Bootstrap on the predictive layer:**

- WFO criterion: sign of OOS mean_spread → FAIL
- Bootstrap criterion: 95% CI of mean_spread → INCONCLUSIVE

This is a legitimate difference between sign-based and CI-based
criteria, not a contradiction. The negative point estimate is
real; sampling uncertainty spans zero. Bootstrap does not
override WFO, and WFO does not invalidate bootstrap.

---

## What this experiment does NOT claim

- Does not claim cross-sectional momentum has no edge in crypto.
- Does not claim the specification is invalid for all markets.
- Does not claim the null proved no-edge.
- Does not promote the strategy beyond exploratory status.

## What this experiment does claim

1. The cross-sectional pipeline is causally correct under the
   tested leakage pathways.
2. The pre-registered specification fails both its pre-registered
   WFO criteria (predictive + strategy).
3. Under bootstrap, strategy returns are statistically negative
   OOS; the predictive spread is inconclusive.
4. Therefore, **no robust evidence of predictive or trading edge
   was established for this specification on this data.**

---

## Artifacts (frozen)

| Artifact | Path |
|----------|------|
| Baseline | `results.json`, `equity_curve.csv`, `trades.csv` |
| Leakage report | `LEAKAGE_REPORT.md` |
| B1 null summary | `leakage_artifacts/b1_multivariate_null_summary.json` |
| Walk-forward | `walkforward.json`, `walkforward_is_equity.csv`, `walkforward_oos_equity.csv` |
| Bootstrap | `bootstrap.json`, `bootstrap_returns.csv`, `bootstrap_spread.csv` |
| Runners | `run_experiment.py`, `run_walkforward.py`, `run_bootstrap.py` |
| Audits | `audit_signals.py`, `audit_portfolio.py`, `audit_walkforward.py`, `audit_b1_null.py` |
| Pre-registration | `PRE_REGISTRATION.md` (with Amendment 001) |

---

## Reproducibility

| Run | Clean-tree rerun | Match |
|-----|------------------|-------|
| Baseline | exact | ✅ |
| Walk-forward | exact | ✅ |
| Bootstrap | exact | ✅ |
| WFO independent audit | max abs diff 0.0 | ✅ |

Environment: Python 3.13.3, numpy 2.2.1, pandas 2.3.3.

---

## Caveats

- Single walk-forward split (50/50), per pre-registration.
- Bootstrap block length = 1 (ACF-based rule) → effectively IID
  row resampling for the strategy layer and IID resampling for
  the predictive spread layer.
- trade_count = 1159 in baseline; ~1 transition every 3.7 bars.
  Cost drag is substantial.
- BTC canonical (yfinance) has 5 gaps vs Binance; analysis
  universe = intersection of timestamps present in all three
  assets (Amendment 001).
- The B1 null is an empirical-return multivariate bootstrap, not
  a zero-drift random walk.

---

## Process lesson (specific to Exp 002)

A first audit of the baseline portfolio accounting reported a
$10,764 discrepancy between the runner and an independent
reconstruction. The discrepancy was traced to a bug in the audit
script itself (transition-bar mark-to-market used the OLD
position instead of the NEW one). After fixing the audit script,
the discrepancy went to exactly 0.0.

This validates the value of **independent reconstruction as a
discipline**: without it, neither the runner's correctness nor
the audit's own correctness could have been established.

---

## Closing statement

This experiment is a **negative result**, produced under the
pre-registered protocol. The Research Lab infrastructure
(Data Loader, Cross-Sectional Runner, Leakage Suite, WFO Runner,
Bootstrap Runner) functioned as designed and produced
reproducible, auditable artifacts. The strategy itself is not
promoted beyond exploratory status.

Per program rules: **negative results are first-class outputs.**