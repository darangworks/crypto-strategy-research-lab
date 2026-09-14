# Leakage Report — Experiment 002

**Experiment:** 002_momentum_btc_eth_sol_4h
**Baseline commit:** 3506f6a
**Runner commit:** 08addfa (git_dirty=false at run)
**Suite commit:** (pending)
**Date:** 2026-09-14

---

## Summary

| Test | Clean pipeline | Intentionally leaky | Detection | Verdict |
|------|----------------|---------------------|-----------|---------|
| A1 all-asset perturbation | invariant (3 cutoffs) | — | — | PASS |
| A2 single-asset perturbation | invariant (3 assets) | — | — | PASS |
| A3 future-data oracle | PASS | FAIL expected | DETECTED | PASS |
| A4 specification check | PASS (0 mismatches) | — | — | PASS |
| B1 multivariate empirical-return null | see §B1 | — | — | DESCRIPTIVE |
| **Step 2 overall** | | | | **PASS** |

**Layer separation (kept explicit):**
- Structural / causal validation: PASS (A1–A4)
- Statistical null sanity check: DESCRIPTIVE (B1)

---

## Layer A — Structural / Causality

### A1 — Target invariance under all-asset future perturbation

For cutoffs [100, 200, 300] on synthetic 500-bar panel, perturbed
`Close[t+1..T]` for all three assets (multiplicative noise, seed
20260913). Asserted `target_asset[0..t]` identical between original
and perturbed.

Result: invariant for all cutoffs (n_diff = 0).

### A2 — Target invariance under single-asset future perturbation

For each asset in {BTC-USD, ETH-USD, SOL-USD}, perturbed only that
asset's future `Close`, kept the other two intact. Asserted
`target_asset[0..t]` invariant.

Critical for cross-sectional strategies: leakage could enter via one
asset's future into the ranking of another.

Result: invariant for all three assets (n_diff = 0).

### A3 — Future-data oracle

Two pipelines compared under all-asset future perturbation
(cutoff = 400, synthetic 800-bar panel):

| Pipeline | Invariance | n_diff in prefix |
|----------|-----------|------------------|
| Clean (`CrossSectionalMomentum`) | HOLDS | 0 |
| Leaky (`LeakyCrossSectional`, `close.shift(-1)`) | VIOLATED | > 0 |

Harness verdict: leak **DETECTED**.

Interpretation (locked):
> The test harness passes only if it successfully detects the
> intentional leak.

### A4 — Specification check

For every timestamp with valid momentum, `target_asset[t]` must
equal the explicit-tiebreak argmax of `momentum[t]`.

Result: 0 mismatches on synthetic data (n_valid > 0).

---

## Layer B — Statistical Null

### B1 — Multivariate empirical-return bootstrap null

**Note on naming:** this is NOT a zero-drift random-walk null and NOT
a true temporal block bootstrap. It is a multivariate iid row-wise
bootstrap of empirical log-return vectors. Under the pre-specified
ACF-based block-length rule, block length collapsed to 1 for all
three assets, so no temporal dependence beyond one observation is
preserved. What IS preserved is contemporaneous cross-asset
dependence (BTC/ETH/SOL return correlation at each timestamp).

**Method:** multivariate row-wise resampling of aligned
[BTC, ETH, SOL] log-return vectors.

**Parameters:**
- N paths: 1000
- Source: 4333 aligned log-return rows (from frozen panel)
- Base seed: 20260913 (per-path seed = base + i)
- Block length: estimated per asset from ACF threshold (2 / sqrt(n))

**Block length estimation:**
- Per-asset lengths: [1, 1, 1]
- Max used: 1
- Threshold: 0.030383

---

## Null specification (precise definition)

- Source data: aligned log-return matrix of shape (4333, 3) from
  the frozen 4,334-bar panel (BTC, ETH, SOL).
- Centering: **returns are NOT centered before resampling.** The
  empirical per-asset mean is preserved.
- Resampling: row-wise iid bootstrap (with replacement) of aligned
  [r_BTC, r_ETH, r_SOL] vectors.
- Block length: 1 (per ACF-based rule). No temporal block structure
  beyond one observation.
- Seed: base_seed + i for path i (base = 20260913).

Therefore, this null tests: "what does this strategy produce on data
with the same volatility, same cross-asset correlation, and same
empirical drift, but no cross-asset predictability beyond what is
present in the marginal return vector distribution?"

Audit confirmation: `audit_b1_null.py` confirms returns are NOT
centered. Sample path means differ from source means only by
sampling noise.

---

## B1 null distribution

| Statistic | median | mean | p2.5 | p97.5 | frac > 0 |
|-----------|--------|------|------|-------|----------|
| Sharpe | −0.894 | −0.894 | −2.267 | +0.444 | 0.104 |
| net_pnl | −78,369 | −68,035 | −96,030 | +17,315 | 0.042 |
| trade_count | 1102 | 1102 | 1043 | 1169 | — |

Baseline reference (Exp 002):

| Metric | Baseline |
|--------|----------|
| Sharpe | −0.859 |
| net_pnl | −78,027.73 |
| trade_count | 1159 |

Baseline position in null:
- Sharpe −0.859 lies essentially at the null median (−0.894).
- net_pnl −78,027.73 is essentially at the null median (−78,369).
- trade_count 1159 lies between median (1102) and p97.5 (1169).

---

## Findings

1. **Block length = 1 for all three assets.** Under the ACF-based
   estimator (threshold = 2 / sqrt(n)), no lag-1 serial dependence
   is detected in any of the three assets. This is a finding, not a
   defect.

2. **Baseline net_pnl is essentially at the median of the null
   distribution.** The negative baseline result is fully consistent
   with what this strategy produces under a null with the same
   volatility, same cross-asset structure, and same empirical drift.

3. **No evidence of leakage** in either direction under the tested
   pathways (A1–A4).

4. **No evidence of edge** under the tested null (B1). The
   `frac > 0` for Sharpe in the null is 0.104, and the baseline does
   not lie in a tail of the null distribution.

---

## Test Interpretation

> These tests are designed to detect specified leakage pathways and
> causal violations. Passing this suite does not prove that the
> entire research pipeline is free of all possible leakage.

> This null does not prove the absence of leakage or establish
> statistical significance; it provides a reference distribution
> under the specified resampling model.

---

## Caveats

- Block length = 1 → the multivariate bootstrap is effectively IID
  row resampling, preserving only cross-sectional correlation, not
  temporal structure.
- A1/A2 tested on synthetic 500-bar panel, not on the frozen 4,334-
  bar panel.
- A3 tested on synthetic 800-bar panel (cutoff = 400).
- B1 preserves cross-asset correlation but not temporal dependence
  (due to block length = 1).
- B1 uses uncentered empirical returns; the null is NOT zero-drift.
- Same seed structure as Experiment 001 (20260913 + i).

---

## Step 2 Verdict

**PASS** — under the tested leakage pathways, the cross-sectional
pipeline satisfies causal invariance and the harness successfully
detects intentional leakage. The B1 statistical null is reported as
a descriptive reference distribution, not as evidence of absence of
edge.

**Next step (pending audit approval):** Step 3 — Walk-Forward.

---

## Reproducibility

| Artifact | Path |
|----------|------|
| Implementations | `validation/leakage/cross_sectional.py` |
| Tests | `tests/leakage/test_exp002_cross_sectional.py` |
| B1 runner | `experiments/002_momentum_btc_eth_sol_4h/run_leakage_b1.py` |
| B1 null audit | `experiments/002_momentum_btc_eth_sol_4h/audit_b1_null.py` |
| B1 summary | `experiments/002_momentum_btc_eth_sol_4h/leakage_artifacts/b1_multivariate_null_summary.json` |
| Test command | `pytest tests/leakage/test_exp002_cross_sectional.py -v` |