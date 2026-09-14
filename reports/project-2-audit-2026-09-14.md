# Project 2 — Research Lab Audit (2026-09-14)

**Scope:** Crypto Strategy Research Lab — from initial commit to Experiment 001 close.
**Status:** Research Core + Validation Core operational; first experiment closed.
**Purpose:** Snapshot of state, deliverables, readiness. Zero code, zero architecture change.

---

## 1. What has been built

### Research Core
- `engine/data_loader.py` — frozen snapshot loader with SHA-256 manifest
- `engine/backtest.py` — next-open fill, 10% sizing, no leverage, costs
- `strategies/_template/strategy.py` — Strategy API
- `strategies/rsi_mean_reversion/strategy.py` — RSI reference strategy
- `data/001_btc_4h/` — frozen BTC-USD 4H, SHA-256 verified
- 17 unit tests (11 backtest + 6 RSI), all passing

### Validation Core
- `validation/leakage/` — A1 target-leak, A2 cross semantics,
  A3 future-data oracle, B1 random-walk null
- `tests/leakage/` — 28 pytest tests, all passing
- `run_walkforward.py` — pre-registered 50/50 runner
- `run_bootstrap.py` — stationary block bootstrap (2000 iter)

### Experiment 001 (CLOSED)
- Tags: `exp-001-baseline`, `exp-001-wfo`, `exp-001-bootstrap`
- Full artifact chain: pre-registration → baseline → leakage → WFO
  → bootstrap → verdict → lessons

### Knowledge Layer
- `knowledge/lessons/exp-001.md` — 7 process lessons
- `experiments/001_rsi_btc_4h/VERDICT.md` — consolidated verdict

---

## 2. What was actually tested

### Specification (fixed, pre-registered)
- **Strategy:** RSI(14), entry threshold = 30, exit threshold = 50
- **Semantics:** strict cross (prev >= 30 & curr < 30 → entry;
  prev <= 50 & curr > 50 → exit)
- **Market:** BTC-USD 4H, 2024-09-14 → 2026-09-13 (4334 bars, frozen)
- **Execution:** next-open fill, 10% position, long-only, no leverage
- **Costs:** 0.05% commission + 0.02% slippage per side
- **Tuning:** none

### Experiment status
- **Type:** exploratory / calibration
- **Purpose:** validate Research Lab infrastructure end-to-end,
  not to promote RSI(14/30/50) as a strategy
- **Parameters 14/30/50 are not optimized values** — they are the
  frozen pre-registered values chosen for this experiment only.

### Layers exercised
baseline → leakage → single 50/50 WFO → bootstrap

---

## 3. What we learned

Seven findings, outcome-based:

1. **Causal correctness ≠ predictive validity.**
   Passing the leakage suite did not imply out-of-sample performance.

2. **Baseline profitability ≠ OOS evidence.**
   The baseline produced +$1,393.73 with Sharpe 0.313, yet OOS Sharpe
   was −0.757.

3. **WFO failure must be accepted literally per pre-registration.**
   The pre-registered criterion (sign of OOS Sharpe) yielded FAIL.
   No adjustment or reinterpretation was applied.

4. **Bootstrap INCONCLUSIVE means uncertainty remains.**
   95% CI = [−1.14e-5, +1.83e-5] includes zero. The bootstrap did not
   establish a positive mean return, nor did it establish a negative one.

5. **Provenance is part of research validity.**
   Every stage required a clean-tree rerun with float-point exact
   reproduction before results could be frozen.

6. **Validation layers must not be used to rescue a hypothesis.**
   A WFO FAIL was not treated as rescuable by the bootstrap, and the
   bootstrap was not used to override the WFO.

7. **A negative result is a valid research output.**
   Experiment 001 closes with verdict REJECTED / NOT PROMOTED — not
   with a claim that RSI has no edge in general, but with the
   conclusion that this pre-registered specification, on this dataset,
   did not produce robust evidence of predictive performance.

---

## 4. What has NOT been built (intentionally deferred)

- Parameter optimization framework
- Multiple-testing correction framework
- Regime analysis tools
- Cross-asset experiment scaffolding
- ML / feature-engineering layer
- Distribution layer (dashboards, publications)

Deferred by design. Architecture serves experiments.

---

## 5. Readiness for Experiment 002

### Required before starting
- New pre-registration document (hypothesis + spec + decision rules)
- New experiment folder under `experiments/`
- Fresh frozen data snapshot (if market or timeframe differs)

### Prohibited
- Tuning RSI(14/30/50) in response to Experiment 001 results.
- Reusing Experiment 001 pre-registration.
- Modifying any frozen artifact from Experiment 001.
- Treating any RSI re-examination as continuation of Experiment 001.

If RSI is revisited, it enters as a new hypothesis with its own
pre-registration — not as a hidden continuation.

### Reusable infrastructure (as-is)
- Data loader, backtest engine, leakage suite, WFO runner, bootstrap runner.

---

## 6. Closing statement

Research Core and Validation Core are operational and have been exercised
end-to-end on one real experiment. The pipeline produced a rejection —
the intended behavior of a validation-first system.

Experiment 001 is **CLOSED**. No reopening, no tuning, no rescue.

The next experiment will begin with its own pre-registration.

---

**Zero new code. Zero architecture change. Zero Experiment 001 change.**
**Snapshot, not a plan.**