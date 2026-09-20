# P004 — Diagnostic Verdict

**Project:** P004 — BTC Intraday Session Effects
**Frozen at:** 2026-09-20
**Diagnostic commit:** `3fe7469`
**Protocol:** `p004-protocol-locked` (commit `a393aad`)
**Dataset commit:** `0b08483`
**Dataset SHA-256:** `fb8f1537a2f054d49841436ec04eb13e06cdad825d96ad62da77dd9c48ea467e`
**Type:** Frozen research artifact (chat-only version finalized 2026-09-20)

---

## 1. What Was Found

Under the preregistered specification, four of the five primary metrics
show statistically detectable differences across sessions:

| Metric | Friedman p | Significant |
|--------|-----------:|:-----------:|
| Absolute Return | 1.8e-34 | yes |
| Session Range | 2.1e-141 | yes |
| Realized Volatility | 3.4e-77 | yes |
| Volume | 5.8e-260 | yes |

Common ordering across all four metrics:

> **New York > Asia > London**

For each of these four metrics, all three pairwise comparisons
(Asia vs London, Asia vs New York, London vs New York) survive
Holm correction.

---

## 2. What Was Not Found

- **Session Return:** Friedman p = 0.82 — no statistically detectable
  session differences.
- **No predictive structure** was established by this diagnostic.
  The test battery was not designed to evaluate predictive performance.

---

## 3. Effect Sizes (Raw)

Effect sizes are reported separately from p-values. Small p-values do
not imply large effects.

**Kendall's W (omnibus):**

| Metric | W |
|--------|---:|
| Session Return | 0.0002 |
| Absolute Return | 0.0798 |
| Realized Volatility | 0.1808 |
| Session Range | 0.3326 |
| Volume | 0.6129 |

**Matched-pairs rank-biserial (individual values; canonical source is
`diagnostic.json`):**

| Metric | Asia/London | London/NY | Asia/NY |
|--------|-------------|-----------|---------|
| Absolute Return | +0.288 | −0.526 | −0.285 |
| Session Range | +0.556 | −0.848 | −0.537 |
| Realized Volatility | +0.199 | −0.653 | −0.577 |
| Volume | +0.795 | −0.974 | −0.745 |

---

## 4. Temporal Stability

Sub-period Friedman results:

> For the four non-directional metrics (Absolute Return, Session Range,
> Realized Volatility, Volume), the Friedman test was significant in
> all three periods (2024, 2025, 2026 Jan–Aug). Session Return was
> not significant in any period.

The New York > Asia > London ordering is consistent across all three
sub-periods at the omnibus level.

---

## 5. Out of Scope for This Diagnostic

The following were not tested or established by this diagnostic:

- Economic significance
- Tradability or trading edge
- Transaction costs and capital allocation
- Predictive performance
- Mechanism or causality
- Future persistence of the observed ordering

Three-level separation:

| Level | Status |
|-------|--------|
| Statistical detection | performed |
| Economic significance | not tested |
| Trading edge | not tested |

---

## Mechanical Diagnostic Verdict

> **Mechanical diagnostic verdict: `STRUCTURE DETECTED`.**
>
> This denotes statistically detectable session differences under the
> preregistered specification; it is **not** a claim of economic
> significance, predictability, or trading edge.

---

## Provenance Chain

Research Question
↓
Data Acquisition + Validation
↓
Data Freeze + SHA-256 (0b08483)
↓
Protocol Lock (a393aad, tag: p004-protocol-locked)
↓
Diagnostic Execution
↓
Governance Audit
↓
Interpretation Audit
↓
Diagnostic Verdict (3fe7469, this file)



---

*This is a diagnostic result. Not a trading recommendation.*