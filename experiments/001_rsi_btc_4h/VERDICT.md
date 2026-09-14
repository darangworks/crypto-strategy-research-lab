# VERDICT — Experiment 001

**Experiment:** 001_rsi_btc_4h
**Strategy:** RSI(14, 30, 50) mean reversion on BTC-USD 4H
**Data:** BTC-USD 4H, 2024-09-14 → 2026-09-13 (4334 rows, frozen SHA-256 `0aaaa726…1296`)
**Completed:** 2026-09-14
**Tags:** `exp-001-baseline`, `exp-001-wfo`, `exp-001-bootstrap`

---

## Layer verdicts (per pre-registration)

| Layer | Verdict |
|-------|---------|
| Baseline (Step 1) | 🟢 FROZEN |
| Causal / Leakage (Step 2) | 🟢 PASS |
| Walk-Forward (Step 3) | 🔴 FAIL |
| Bootstrap (Step 4) | 🟡 INCONCLUSIVE |
| **Overall** | **🔴 REJECTED / NOT PROMOTED** |

"REJECTED" here means: *the pre-registered strategy specification is
rejected for promotion based on the current evidence.* It does NOT mean
"the strategy was proven to have no edge."
---

## Final statement

> **The strategy passed the specified causal/leakage checks, but failed the
> pre-registered walk-forward criterion, while bootstrap inference was
> inconclusive. Therefore, the experiment does not provide sufficient
> evidence to promote the strategy beyond the exploratory stage.**

Equivalent shorter form:

> **No robust evidence of predictive performance was established for the
> pre-registered RSI(14) mean-reversion specification on BTC-USD 4H data.**

---

## Three-concept separation

### 1. Causal validity

Under the tested leakage pathways (A1 target-leak invariant, A2 strict
cross semantics, A3 future-data oracle), no causal violation was detected.
The random-walk null (B1, 1000 paths) did not show systematic performance
inflation.

This is a statement about the **tested** pathways, not about all possible
leakage. See `LEAKAGE_REPORT.md`.

### 2. Predictive / out-of-sample evidence

Pre-registered walk-forward (single 50/50 split):

| Segment | trades | net_pnl | sharpe |
|---------|--------|---------|--------|
| IS  (bars 0..2166)   | 15 | +3,328.68 | +1.558 |
| OOS (bars 2167..4333) | 16 | −1,872.61 | **−0.757** |

Verdict per pre-registration (sign of OOS Sharpe): **FAIL**.

No persistence of in-sample performance was observed in the held-out
sample under this split.

### 3. Statistical uncertainty

Stationary block bootstrap on baseline mean 4H portfolio return
(2000 iterations, seed 20260913):

- observed mean: **3.3163 × 10⁻⁶**
- 95% CI:        **[−1.1440 × 10⁻⁵, +1.8262 × 10⁻⁵]**
- verdict:       **INCONCLUSIVE** (CI includes 0)

**Finding (not advantage):** the estimated block length was 1 because the
lag-1 ACF of the observed portfolio returns was effectively zero. The
stationary block bootstrap was therefore effectively close to an IID
resampling scheme under the specified block-length estimator.

Bootstrap quantifies uncertainty of the baseline only; it does not
modify, rescue, or override the walk-forward FAIL.

---

## What this experiment does NOT claim

- Does not claim RSI has no edge in general.
- Does not claim the strategy is invalid.
- Does not claim causal correctness of the entire pipeline — only that
  the tested leakage pathways were not detected.
- Does not promote the strategy beyond the exploratory stage.

---

## What this experiment does claim

1. The research pipeline is causally correct under the tested pathways.
2. The pre-registered specification fails its pre-registered
   walk-forward criterion.
3. Under pre-registered bootstrap, the observed baseline mean return
   is indistinguishable from zero at the 95% level.
4. Therefore, **no robust evidence of predictive performance was
   established**.

---

## Artifacts (frozen in git)

| Artifact | Path |
|----------|------|
| Baseline | `results.json`, `equity_curve.csv`, `trades.csv` |
| Leakage report | `LEAKAGE_REPORT.md` |
| Null summary | `leakage_artifacts/random_walk_summary.json` |
| Walk-forward | `walkforward.json`, `walkforward_is_equity.csv`, `walkforward_oos_equity.csv` |
| Bootstrap | `bootstrap.json`, `bootstrap_distribution.csv` |
| Runners | `run_experiment.py`, `run_walkforward.py`, `run_bootstrap.py` |
| Pre-registration | `PRE_REGISTRATION.md` |

---

## Reproducibility

| Run | Source tree | Rerun from clean tree | Match |
|-----|-------------|------------------------|-------|
| Baseline | dirty | exact | ✅ |
| Walk-forward | dirty | exact | ✅ |
| Bootstrap | dirty | exact | ✅ |

All reruns from clean trees produced float-point exact reproductions
of the original (dirty) runs. This is documented per-step in each
`*.json` provenance block.

Environment: Python 3.13.3, numpy 2.2.1, pandas 2.3.3.

---

## Caveats

- Single walk-forward split (50/50), per pre-registration. No multiple
  splits, no purging, no embargo.
- Bootstrap block-length estimator reduced to length 1 on this dataset;
  inference is therefore close to IID under this specification.
- 31 baseline trades in total. Sample size is small.
- The random-walk null inherits any idiosyncrasies of the frozen
  BTC-USD 4H return sample used for bootstrap resampling.

---

## Closing statement

This experiment is a **negative result**, produced under the
pre-registered protocol. The Research Lab infrastructure
(Data Loader, Backtest Engine, Leakage Suite, Walk-Forward runner,
Bootstrap runner) functioned as designed and produced reproducible,
auditable artifacts. The strategy itself is not promoted beyond
exploratory status.

Per program rules: **negative results are first-class outputs.**
