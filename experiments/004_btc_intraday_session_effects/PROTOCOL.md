# P004 — Protocol (Statistical Protocol Lock)

**Project:** P004 — BTC Intraday Session Effects
**Status:** FROZEN
**Frozen at:** 2026-09-20
**Frozen by:** Researcher (with evaluator approval)
**Preceded by:** Data Provenance Gate PASSED (commit 0b08483)

---

## 0. Purpose of this document

This document locks all methodological decisions for P004 BEFORE any
statistical diagnostic is run.

Once committed and tagged as `p004-protocol-locked`, this protocol is
immutable. Any subsequent change requires a new experiment.

The purpose is to prevent:

- data-driven session selection
- post-hoc metric choice
- test switching after seeing results
- interpretation drift

---

## 1. Research Question (LOCKED)

Do predefined Asia, London, and New York session windows exhibit
measurable differences in BTCUSDT intraday return, volatility, range,
and volume?

Secondary: is there measurable directional persistence within session
classes?

This is a **diagnostic experiment**, not a strategy-optimization
project.

---

## 2. Market & Data (LOCKED)

| Field | Value |
|-------|-------|
| Asset | BTCUSDT |
| Market | Binance Spot |
| Timeframe | 1H |
| Timezone | UTC |
| Period | 2024-01-01 → 2026-08-31 |
| Rows | 23,376 |
| Duplicates | 0 |
| Global gaps | 0 |
| Chronology errors | 0 |
| Validation errors | 0 |
| SHA-256 | fb8f1537a2f054d49841436ec04eb13e06cdad825d96ad62da77dd9c48ea467e |
| Canonical file | data/frozen/BTCUSDT_1h_2024-01-01_2026-08-31.csv |
| Manifest | data/manifests/BTCUSDT_1h_2024-01-01_2026-08-31_manifest.txt |
| Status | FROZEN |

The dataset will not be modified.

---

## 3. Session Boundaries (LOCKED)

**Option C — session-exclusive, no overlap.**

| Session | UTC start | UTC end | Hours |
|---------|-----------|---------|-------|
| Asia | 00:00 | 08:00 | 8 |
| London | 08:00 | 13:00 | 5 |
| New York | 13:00 | 21:00 | 8 |
| Unattributed | 21:00 | 24:00 | 3 |

Boundary rule: start-inclusive, end-exclusive.

- A 1H bar whose open_time is at hour h belongs to session S if
  `start(S) <= h < end(S)`.
- Unattributed hours (21:00, 22:00, 23:00 UTC) are excluded from all
  session analysis.
- No 1H bar belongs to more than one session.

Boundaries are frozen and will not be changed after seeing results.

---

## 4. Unit of Observation (LOCKED)

**One observation per (UTC day, session).**

For each UTC day and each session, all 1H bars within that session's
UTC window are aggregated into a single observation.

Expected observations per day: 3 (Asia, London, NY).

Any day missing one or more required hours within a session will be
**excluded from that session's observations**, and the exclusion will
be documented. No interpolation, no imputation.

---

## 5. Metric Formulas (LOCKED)

Let `bars(session, day)` = the set of 1H bars for the given UTC day
and session, in chronological order.

### 5.1 Session Return
Session Return = ln(Close_last / Close_first)
where `Close_first` is the close of the first bar in the session and
`Close_last` is the close of the last bar.

### 5.2 Absolute Return
Absolute Return = abs(Session Return)

### 5.3 Session Range
Session Range = High_max - Low_min
where `High_max` = maximum High across session bars and
`Low_min` = minimum Low across session bars.

### 5.4 Realized Volatility
Realized Volatility = std(1H log returns within session)
Computed as the sample standard deviation (ddof=1) of consecutive 1H
log returns within the session.

### 5.5 Volume
Volume = sum(1H Volume across session bars)

### 5.6 Directional Persistence (SECONDARY — exploratory)
Persistence_S(d) = 1 if sign(Session Return_S(d)) == sign(Session Return_S(d-1))
                   0 otherwise

For each session class S and each UTC day d:

Where "d-1" is the previous UTC day that has a valid observation for
the same session class S. Ties (Return == 0) will be excluded.

Persistence is **secondary** and is reported for descriptive purposes
only. It is not part of the primary test battery.

---

## 6. Primary Statistical Tests (LOCKED)

### 6.1 Primary comparison

Sessions are compared as a **paired by UTC day** structure:

- Only UTC days that have a valid observation for **all three**
  sessions are included in the primary test.
- Any partial day is excluded and documented.

### 6.2 Omnibus test

For each primary metric (Session Return, Absolute Return, Session
Range, Realized Volatility, Volume), across the three sessions:

**Friedman test** with sessions as repeated measures, blocked by UTC
day.

- Non-parametric.
- No normality assumption.
- Blocked by UTC day to control for market-wide effects.

### 6.3 Pairwise tests

Only if the Friedman test is significant at α = 0.05:

**Wilcoxon signed-rank test** for each of the three session pairs
(Asia-London, London-NY, Asia-NY), separately for each primary metric.

If Friedman is not significant, no pairwise test will be reported as
confirmatory. Pairwise results (if computed for completeness) will be
clearly labeled exploratory.

### 6.4 Multiple comparison control

**Holm correction** applied within each metric family:

- For each primary metric, the 3 pairwise comparisons are corrected
  together.
- Cross-metric multiple testing is reported via raw and adjusted
  p-values, without a global α claim.

---

## 7. Effect Sizes and Confidence Intervals (LOCKED)

### 7.1 Effect size

- **Omnibus:** Kendall's W.
- **Pairwise:** matched-pairs rank-biserial correlation.

### 7.2 Confidence intervals

**95% bootstrap CI** for each reported statistic, based on
**block-bootstrap on UTC-day blocks** to preserve short-range
dependence.

Bootstrap parameters:
- Block structure: UTC-day blocks
- N iterations: 10,000
- Seed: 20260920
- Percentile method for CI

---

## 8. Robustness (LOCKED)

### 8.1 Sub-period stability

The primary test battery is repeated on three sub-periods:

- 2024-01-01 → 2024-12-31
- 2025-01-01 → 2025-12-31
- 2026-01-01 → 2026-08-31

Sub-period results are reported for stability assessment only, not
pooled into the primary conclusion.

### 8.2 Directional persistence

Reported descriptively per session class; not part of the primary
test.

---

## 9. Interpretation Rules (LOCKED)

Predefined allowed conclusions:

- **STRUCTURE DETECTED** — at least one primary metric shows a
  significant omnibus effect (α=0.05, Friedman), and at least one
  pairwise comparison survives Holm correction.
- **WEAK STRUCTURE** — a significant omnibus effect exists, but no
  pairwise comparison survives Holm correction.
- **NO CLEAR STRUCTURE** — no significant omnibus effect on any
  primary metric.
- **INCONCLUSIVE** — the data or test assumptions prevent a reliable
  conclusion.

These labels are research outcomes. They are not trading
recommendations.

---

## 10. Research Integrity Rules (LOCKED)

- No strategy optimization.
- No parameter tuning after seeing results.
- No post-hoc session selection.
- No changing session boundaries after seeing results.
- No favorable subperiod selection.
- No cherry-picking metrics.
- No changing the statistical test because of an unfavorable result.
- No direct conversion of a session difference into a trading claim.
- No claim of a robust trading edge from descriptive session structure
  alone.

---

## 11. What this protocol does NOT do

- Does not optimize a strategy.
- Does not test tradability.
- Does not assume normality.
- Does not use future data.
- Does not modify the frozen dataset.

---

## 12. Deliverables after this protocol

Once committed and tagged `p004-protocol-locked`:

1. Diagnostic script
2. Diagnostic output (metrics per session, tests, effect sizes, CIs)
3. `P004 — Diagnostic Report.md`
4. Interpretation per §9
5. Update P004 Research Handoff
6. Update Recovery Snapshot

No public publication until the diagnostic is complete and the
interpretation is finalized.

---

## 13. Freeze declaration

This protocol is locked.

Any modification requires a new experiment.

**Frozen at:** 2026-09-20
**Data SHA-256:** fb8f1537a2f054d49841436ec04eb13e06cdad825d96ad62da77dd9c48ea467e
**Data commit:** 0b08483
