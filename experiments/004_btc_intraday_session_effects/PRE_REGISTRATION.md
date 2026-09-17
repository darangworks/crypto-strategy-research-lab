# Experiment 004 — BTC Intraday Session Effects

**Status:** PRE-REGISTERED
**Experiment:** 004
**Market:** BTCUSDT Spot
**Base timeframe:** 1H
**Research branch:** `experiment-004`

---

## 1. Research Question

آیا رفتار درون‌روزی BTCUSDT در پنجره‌های زمانی از پیش‌تعریف‌شده‌ی مرتبط با Asia، London و New York از نظر بازده، نوسان، دامنه و حجم با یکدیگر تفاوت قابل‌توجهی دارد؟

The primary objective is descriptive and diagnostic.

This experiment does **not** initially test a trading strategy.

The purpose is to determine whether a sufficiently stable intraday session structure exists to justify a later, separately registered strategy hypothesis.

---

## 2. Hypothesis

### Primary research hypothesis

BTCUSDT may exhibit systematic differences in intraday market behavior across predefined Asia, London and New York session windows.

The experiment does not assume:

* that any session is superior;
* that any session effect is predictive;
* that an observed difference is economically exploitable;
* that a session-based strategy will be profitable.

The null interpretation is that the observed differences are weak, unstable, or insufficient to justify a session-based trading hypothesis.

---

## 3. Market and Data

### Instrument

`BTCUSDT`

### Market type

Binance Spot.

### Base timeframe

1-hour candles (`1h`).

### Data source

Binance Public Data / Binance Spot market data.

### Raw timestamp convention

All raw timestamps are retained and interpreted as UTC.

Timezone conversion is performed only during session classification.

No modification of raw timestamps is permitted.

### Data fields

The primary analysis may use:

* Open
* High
* Low
* Close
* Volume
* Quote asset volume
* Number of trades

The following fields are not required for the primary session-effect analysis unless explicitly registered later:

* Taker buy base asset volume
* Taker buy quote asset volume

---

# 4. Research Period

## Locked period

**2024-01-01 00:00:00 UTC through 2026-08-31 23:00:00 UTC**

This period is fixed before full-period session analysis.

The August 2026 endpoint is chosen because the first frozen Experiment 004 data snapshot currently available is August 2026 and the full research dataset will terminate at the same calendar endpoint.

No observations after 2026-08-31 may be added to the primary analysis.

No earlier observations may be removed because of their observed performance characteristics.

If additional historical data become available later, they may be used only in a separately documented robustness or future experiment.

---

# 5. Timezone Framework

## Base timezone

All raw market timestamps are UTC.

UTC is the canonical time representation throughout the data pipeline.

## Session timezone principle

Session windows are defined using the local civil time of the corresponding financial center.

The local timezone is converted to UTC for each timestamp using the applicable historical timezone rules.

This prevents daylight-saving changes from silently changing the meaning of a session.

---

# 6. Session Definitions

## 6.1 Asia Session

The Asia session is operationally represented by the Tokyo financial-center window:

**09:00–17:00 Asia/Tokyo**

Tokyo does not observe daylight saving time.

Therefore the corresponding UTC window is:

**00:00–08:00 UTC**

---

## 6.2 London Session

The London session is operationally represented by:

**08:00–16:00 Europe/London**

The UTC representation changes according to the historical daylight-saving status of Europe/London.

Therefore:

* GMT period: 08:00–16:00 UTC
* BST period: 07:00–15:00 UTC

The local-time definition remains fixed.

---

## 6.3 New York Session

The New York session is operationally represented by:

**08:00–16:00 America/New_York**

The UTC representation changes according to the historical daylight-saving status of America/New_York.

Therefore:

* EST period: 13:00–21:00 UTC
* EDT period: 12:00–20:00 UTC

The local-time definition remains fixed.

---

# 7. Session Overlap

Session windows are intentionally allowed to overlap.

This experiment does not partition the 24-hour BTC market into three mutually exclusive blocks.

The objective is to measure the behavior associated with predefined financial-center windows.

Therefore a single 1H candle may belong to more than one session.

No observation will be duplicated within a session-specific metric calculation, but the same market observation may legitimately contribute to multiple session analyses.

This overlap is a property of the research design and must not be removed after observing results.

---

# 8. Day Definition

The primary calendar date is based on UTC.

Each 1H candle is assigned to its UTC calendar date before session-level aggregation.

Weekday information is derived from the UTC timestamp.

Weekend observations are retained.

No weekday is removed from the primary sample.

---

# 9. Primary Metrics

The following metrics are pre-registered.

## 9.1 Session Return

For each session-day:

`session_return = session_close / session_open - 1`

This measures the directional price change across the predefined session window.

---

## 9.2 Absolute Return

For each session-day:

`absolute_return = abs(session_return)`

This measures movement magnitude independently of direction.

---

## 9.3 Session Range

For each session-day:

`range = session_high / session_low - 1`

This measures the total high-low price range observed during the session.

---

## 9.4 Realized Volatility

Hourly log returns within each session are used to estimate realized volatility.

The primary measure is the square root of the sum of squared hourly log returns:

`RV = sqrt(sum(r_t²))`

where:

`r_t = ln(C_t / C_(t-1))`

No annualization is required for the primary comparison.

---

## 9.5 Volume

Session volume is calculated as the sum of BTC base-asset volume across the hourly observations belonging to the session.

Because BTC trades continuously, volume is interpreted as activity rather than exchange-opening volume.

---

# 10. Secondary Metric

## Directional Persistence

Directional persistence measures whether the direction of hourly price movement within a session tends to continue rather than immediately reverse.

The exact estimator must be implemented once and documented in the analysis script before results are reviewed.

The primary conclusions must not depend solely on this secondary metric.

---

# 11. Normalization

Because session windows may differ in their number of observations under edge cases involving data completeness, all primary comparisons must be performed on complete session windows.

Raw volume is reported in addition to any normalized activity measure.

Where distributions are strongly scale-dependent, effect sizes may additionally be expressed using:

* percentage differences;
* log ratios;
* standardized differences.

The transformation used must be documented before interpretation.

---

# 12. Completeness Gate

BTC trades continuously, therefore a complete 1H dataset should contain one observation per hour.

For the locked research period, the expected hourly spacing is one hour.

The following checks are mandatory:

1. Duplicate timestamps = 0
2. Timestamps strictly increasing
3. Expected hourly spacing preserved
4. No unexplained missing candles
5. OHLC relationships valid
6. Volume non-negative
7. Research-period boundaries correct

No forward-fill is permitted.

No interpolation is permitted.

No synthetic candle may be created.

Missing observations are not silently reconstructed.

If missing data are discovered, the affected session/day is flagged according to the completeness rules rather than repaired.

---

# 13. Session Completeness

A session-day is considered complete only when all expected hourly observations for that local session are present.

Incomplete session-days are excluded from the primary session-level comparison.

The number and percentage of excluded session-days must be reported.

No exclusion threshold may be changed after inspecting session performance.

---

# 14. Statistical Framework

This experiment is primarily an effect-size and uncertainty analysis.

The objective is not to produce a binary declaration of statistical significance.

For each primary metric, the analysis will report:

* sample size;
* mean;
* median;
* dispersion;
* effect size;
* uncertainty interval;
* distributional information where useful.

---

# 15. Primary Comparison

The primary comparison is pairwise between session windows:

* Asia vs London
* Asia vs New York
* London vs New York

No overall ranking of sessions will be produced as a research conclusion.

The question is whether the observed differences are sufficiently large and stable to justify further research.

---

# 16. Confidence Intervals

The primary uncertainty measure will be a two-sided 95% confidence interval for the relevant session difference.

For example:

`Δ = mean(London metric) - mean(Asia metric)`

The same paired framework will be applied to the other session comparisons where observations can be naturally paired by calendar date.

Bootstrap resampling may be used when distributional assumptions are inappropriate.

If bootstrap is used:

* resampling must preserve the observational unit;
* the same resampling scheme must be applied consistently;
* the number of replications must be fixed before analysis;
* the seed must be fixed;
* percentile 95% confidence intervals will be reported.

---

# 17. Multiple Comparisons

Because multiple session pairs and multiple metrics are examined, raw p-values must not be interpreted independently.

Where formal hypothesis-test p-values are reported, the Holm correction will be applied within the pre-defined primary comparison family.

Effect sizes and confidence intervals remain primary reporting objects.

A statistically detectable difference with negligible economic magnitude will not automatically justify a strategy hypothesis.

---

# 18. Economic Relevance

Statistical evidence alone is insufficient.

Observed session differences will be evaluated in terms of magnitude and stability.

The analysis will distinguish:

1. statistically detectable difference;
2. economically meaningful difference;
3. stable difference across time;
4. potentially actionable trading structure.

These are separate concepts.

This experiment does not assume that evidence for one implies evidence for the others.

---

# 19. Time Stability

The full-period result must not be treated as sufficient evidence of stability.

Secondary analysis will examine whether observed session differences are reasonably consistent across chronological subperiods.

The subperiod definitions must be fixed before inspecting their individual results.

No favorable subperiod may be selected post hoc.

---

# 20. Weekday Effects

Weekday composition may influence session statistics.

Therefore weekday information will be retained.

Secondary analysis may examine whether session effects remain visible after accounting for weekday structure.

No weekday will be excluded from the primary analysis based on observed results.

---

# 21. Regime Analysis

Market-regime analysis is secondary.

Potential regime dimensions may include:

* volatility regime;
* trend/range regime;
* high/low activity regime.

Regime definitions must be specified before they are used for confirmatory interpretation.

No regime filter may be introduced solely because it improves an observed session result.

---

# 22. Prohibited Researcher Degrees of Freedom

After this document is committed, the following actions are prohibited for the primary experiment:

* changing the research period because of results;
* changing session hours because of results;
* removing an unfavorable session;
* removing unfavorable days;
* changing timezone definitions;
* changing DST treatment;
* changing primary metrics;
* adding a new metric and declaring it primary after seeing results;
* selecting favorable subperiods;
* tuning session boundaries for performance;
* introducing technical indicators to rescue weak session effects;
* optimizing entry/exit rules;
* optimizing transaction costs;
* optimizing parameters;
* changing the market from Spot to Futures;
* replacing BTCUSDT with another asset as the primary market.

Such changes require a new experiment or explicitly labeled exploratory analysis.

---

# 23. Strategy Separation

Experiment 004 is a diagnostic experiment.

It does not contain a trading strategy.

No strategy will be designed, optimized, or evaluated until the session-effect diagnostic is complete.

If evidence supports a session-based hypothesis, the resulting strategy idea will become a separately registered experiment.

If evidence does not support a session-based hypothesis, the session strategy branch will not be forced.

---

# 24. Decision Framework

The diagnostic will produce one of four research interpretations:

### STRUCTURE DETECTED

Session differences are sufficiently large, reasonably stable, and economically interpretable to justify a new strategy hypothesis.

This does not imply profitability.

### WEAK STRUCTURE

Some differences are observed, but their magnitude or stability is insufficient for immediate strategy development.

Further diagnostic work may be considered.

### NO CLEAR STRUCTURE

The observed differences are small, unstable, or inconsistent across the tested period.

A session-based strategy will not be promoted.

### INCONCLUSIVE

Data quality, completeness, uncertainty, or sample limitations prevent a reliable interpretation.

No strategy will be promoted from an inconclusive result.

---

# 25. Reproducibility

The following artifacts must be frozen before final interpretation:

* raw Binance archives;
* extracted CSV data;
* SHA-256 checksums;
* data manifest;
* analysis scripts;
* protocol version;
* statistical seed where applicable;
* final diagnostic outputs.

All derived results must be reproducible from the frozen data snapshot.

---

# 26. Research Integrity Rule

The purpose of this experiment is to discover whether a session structure survives predefined measurement and validation.

The experiment is not designed to prove that session trading works.

A positive result is evidence for a hypothesis.

It is not evidence of profitability.

A negative result is not a failure of the research process.

It is a valid research outcome.

---

# 27. Locked Status

Once committed to Git, this document is considered frozen for the primary Experiment 004 analysis.

Any substantive modification requires:

1. a new protocol version;
2. an explicit explanation of the change;
3. a new Git commit;
4. clear separation between the original and revised research specification.

The primary analysis must remain reproducible under the original specification.

---

## Protocol Summary

```text
EXPERIMENT 004
BTCUSDT Spot
1H
2024-01-01 → 2026-08-31 UTC
        │
        ↓
Raw timestamps = UTC
        │
        ↓
Local financial-center session definitions
        │
 ┌──────┼──────────┐
 ↓      ↓          ↓
Tokyo  London    New York
09–17  08–16     08–16
 JST    London    New York
        │
        ↓
DST handled by timezone database
        │
        ↓
Primary metrics
Return
Absolute Return
Range
Realized Volatility
Volume
        │
        ↓
Secondary
Directional Persistence
        │
        ↓
Pairwise effect sizes
+ 95% CI
+ Holm correction where formal tests are used
        │
        ↓
Chronological stability
        │
        ↓
Evidence
        │
 ┌──────┼──────────────┐
 ↓      ↓              ↓
Structure Weak      No clear
detected structure   structure
        │
        ↓
Only then:
separate strategy experiment
```

**Protocol status: READY FOR REVIEW — NOT YET COMMITTED**
