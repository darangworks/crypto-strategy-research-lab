# Leakage Report — Experiment 001

**Tag audited:** `exp-001-baseline`
**Baseline commit:** `ccf28ac`
**Suite commit:** _(پس از این گزارش کامیت می‌شود)_
**Date:** 2026-09-13

---

## Summary

| Test | Clean pipeline | Intentionally leaky | Detection | Verdict |
|------|----------------|---------------------|-----------|---------|
| Random-walk oracle (B1) | see §B1 | — | — | PASS |
| Future-data oracle (A3) | PASS | FAIL expected | DETECTED | PASS |
| Target-leak invariant (A1) | PASS | intentional perturb | DETECTED | PASS |
| Strict cross semantics (A2) | PASS | — | — | PASS |
| **Step 2 overall** | | | | **PASS** |

---

## Layer A — Invariance / Structural Tests

### A1 — Target-leak invariant (`validation/leakage/target_leak_check.py`)

Method: For cutoffs [500, 1000, 2000, 3000], perturb all `Close` values
after cutoff (multiplicative noise, seed 20260913). Assert that
`target_position()[:cutoff]` is identical between original and perturbed.

Result:
| Cutoff | n_diff | Invariant |
|--------|--------|-----------|
| 500 | 0 | ✅ |
| 1000 | 0 | ✅ |
| 2000 | 0 | ✅ |
| 3000 | 0 | ✅ |

### A2 — Strict cross semantics (`validation/leakage/strict_cross_semantics.py`)

17 deterministic cases (entry, exit, no-event, boundary, NaN warm-up).
All passed (see `tests/leakage/test_cross_semantics.py`).

Boundary and NaN cases explicitly covered:
- 30 → 29 → ENTRY (boundary inclusive)
- 30 → 30 → no event
- 50 → 51 → EXIT (boundary inclusive)
- 50 → 50 → no event
- NaN → 29/30/31/50 → no event
- in-position → NaN → no exit

### A3 — Future-data oracle (`validation/leakage/future_data_oracle.py`)

Two pipelines compared under future perturbation (cutoff = 2000):

| Pipeline | Invariance | n_diff in prefix |
|----------|-----------|------------------|
| Clean (`RSIMeanReversion`) | HOLDS | 0 |
| Leaky (`LeakyRSI`, `close.shift(-1)`) | VIOLATED | > 0 |

Harness verdict: **leak DETECTED**.

Interpretation (locked):
> The test harness passes only if it successfully detects the
> intentional leak.

---

## Layer B — Statistical Oracle

### B1 — Random-walk null (`validation/leakage/random_walk_null.py`)

Null generator: bootstrap-resample log returns from frozen BTC-USD 4H
dataset. No drift. S0 = first close. Independent paths.

Parameters:
- N paths: 1000
- Length: 4334 bars
- Base seed: 20260913 (per-path seed = base + index)

Null distribution:

| Statistic | median | mean | p2.5 | p97.5 | frac > 0 |
|-----------|--------|------|------|-------|----------|
| Sharpe | 0.086 | 0.092 | -1.246 | 1.457 | 0.552 |
| net_pnl | 281 | 225 | -4901 | 5169 | 0.547 |
| trade_count | 33 | 33.1 | 24 | 42 | — |

Baseline (frozen) for reference:

| Metric | Baseline |
|--------|----------|
| Sharpe | 0.3134 |
| net_pnl | 1393.73 |
| trade_count | 31 |

For reference, the baseline Sharpe (0.313) and net P&L (+$1,393.73)
were not extreme relative to the specified null distribution. This
comparison is descriptive only and is not used as a pass/fail criter

Interpretation (locked):
> No systematic performance inflation detected under the
> specified null simulation.

NOT claimed:
- "Strategy has no edge."
- "Strategy has edge."

---

## Test Interpretation

> These tests are designed to detect specified leakage pathways
> and causal violations. Passing this suite does not prove that
> the entire research pipeline is free of all possible leakage.

---

## Caveats

- Random-walk oracle limited to bootstrap-null assumption from frozen
  BTC-USD 4H return sample. Distribution of returns in resampled paths
  inherits any idiosyncrasies of the frozen sample.
- "Tested leakage pathway not detected" ≠ "no leakage exists".
- Structural tests (A1) limited to tested cutoffs [500, 1000, 2000, 3000].
- A3 tests only `close.shift(-1)` style future leakage in features.
- The 55% frac_positive of Sharpe in the null is not interpreted as
  evidence for or against strategy performance.

---

## Step 2 Verdict

**PASS** — under the tested leakage pathways and null specification,
the pipeline satisfies causal invariance and the harness successfully
detects intentional leakage.

**Next step (pending audit approval):** Step 3 — Walk-Forward.

---

## Reproducibility

| Artifact | Path |
|----------|------|
| Null summary | `experiments/001_rsi_btc_4h/leakage_artifacts/random_walk_summary.json` |
| Tests | `tests/leakage/` |
| Implementations | `validation/leakage/` |
| Test command | `pytest tests/leakage/ -v` |
