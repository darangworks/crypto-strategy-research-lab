# Research Protocol

Every strategy follows this protocol.

---

## 1. Hypothesis

Before any code:
- Economic rationale
- Why would it persist?
- What would falsify it?

---

## 2. Causal Specification

- Signal timestamp
- Execution timestamp
- Label horizon
- Feature availability

---

## 3. Pre-registration

### Confirmatory
- Pre-registered parameters
- Single configuration

### Exploratory
- Declared search space
- Full search space recorded

---

## 4. Data Snapshot

MANIFEST.md must include:
source, symbol, timeframe, start, end, retrieved_at, row_count, columns, sha256

---

## 5. Cost Model

- Commission: explicit per-side
- Slippage: explicit per-side
- Position sizing: explicit notional
- Execution: next-open fill

---

## 6. Validation

Leakage, Walk-forward, Bootstrap, Parameter stability, Multiple testing, Regime, Cross-asset

Each returns PASS / WEAK / FAIL / INCONCLUSIVE

---

## 7. Verdict

Research Status: REJECTED / INCONCLUSIVE / PROMISING / ROBUST

---

## 8. Documentation

results/promising/  - PROMISING or ROBUST
results/rejected/   - REJECTED
results/inconclusive/ - INCONCLUSIVE

Negative results are not deleted.
