# P004 — Diagnostic Report

Generated at UTC: 2026-09-20T13:52:16.513748+00:00

Protocol: p004-protocol-locked (a393aad)

Data SHA-256: `fb8f1537a2f054d49841436ec04eb13e06cdad825d96ad62da77dd9c48ea467e`

Data rows: 23376


## Sessions

- Asia: 00:00 – 08:00 UTC (8h)
- London: 08:00 – 13:00 UTC (5h)
- NewYork: 13:00 – 21:00 UTC (8h)

## Observations

- Total session-day observations: 2922
- Complete UTC days: 974

## Metric summary per session

### session_return

| Session | n | median | mean | std |
|---------|---|--------|------|-----|
| Asia | 974 | 0.000461993 | 5.38176e-05 | 0.0113027 |
| London | 974 | 0.000220817 | 0.000184905 | 0.00798873 |
| NewYork | 974 | 0.000280052 | 3.88573e-05 | 0.01684 |

### abs_return

| Session | n | median | mean | std |
|---------|---|--------|------|-----|
| Asia | 974 | 0.00507804 | 0.00765569 | 0.00831162 |
| London | 974 | 0.00367507 | 0.00544437 | 0.00584657 |
| NewYork | 974 | 0.00708866 | 0.0112471 | 0.0125283 |

### session_range

| Session | n | median | mean | std |
|---------|---|--------|------|-----|
| Asia | 974 | 1150.86 | 1421.36 | 1017.53 |
| London | 974 | 877.36 | 1034.37 | 659.663 |
| NewYork | 974 | 1672.92 | 2000.35 | 1361.95 |

### realized_volatility

| Session | n | median | mean | std |
|---------|---|--------|------|-----|
| Asia | 974 | 0.00307342 | 0.00366189 | 0.00257262 |
| London | 974 | 0.00264262 | 0.00323091 | 0.00226475 |
| NewYork | 974 | 0.00448857 | 0.00517164 | 0.00336651 |

### volume

| Session | n | median | mean | std |
|---------|---|--------|------|-----|
| Asia | 974 | 5666.69 | 7139.3 | 6089.27 |
| London | 974 | 3747.41 | 4733.53 | 3834.14 |
| NewYork | 974 | 9249.44 | 11447.2 | 8881.03 |

## Friedman tests

| Metric | n_days | chi-square | p-value | Kendall's W |
|--------|--------|------------|---------|-------------|
| session_return | 974 | 0.3963 | 0.820245 | 0.0002034 |
| abs_return | 974 | 155.4 | 1.8128e-34 | 0.07977 |
| session_range | 974 | 647.8 | 2.1251e-141 | 0.3326 |
| realized_volatility | 974 | 352.1 | 3.41511e-77 | 0.1808 |
| volume | 974 | 1194 | 5.76139e-260 | 0.6129 |

## Wilcoxon + Holm (only if Friedman significant)

### session_return

Not run: not_run (omnibus not significant)

### abs_return

| Pair | n | n_nonzero | statistic | p-value | p-Holm | rank-biserial |
|------|---|-----------|-----------|---------|--------|----------------|
| Asia_vs_London | 974 | 974 | 1.69e+05 | 6.67977e-15 | 1.33595e-14 | 0.2882 |
| London_vs_NewYork | 974 | 974 | 1.126e+05 | 7.28018e-46 | 2.18405e-45 | -0.5258 |
| Asia_vs_NewYork | 974 | 974 | 1.698e+05 | 1.41649e-14 | 1.41649e-14 | -0.2846 |

### session_range

| Pair | n | n_nonzero | statistic | p-value | p-Holm | rank-biserial |
|------|---|-----------|-----------|---------|--------|----------------|
| Asia_vs_London | 974 | 974 | 1.054e+05 | 4.57873e-51 | 9.15746e-51 | 0.556 |
| London_vs_NewYork | 974 | 974 | 3.61e+04 | 2.69433e-116 | 8.08298e-116 | -0.8479 |
| Asia_vs_NewYork | 974 | 974 | 1.099e+05 | 9.12361e-48 | 9.12361e-48 | -0.5371 |

### realized_volatility

| Pair | n | n_nonzero | statistic | p-value | p-Holm | rank-biserial |
|------|---|-----------|-----------|---------|--------|----------------|
| Asia_vs_London | 974 | 974 | 1.902e+05 | 7.72396e-08 | 7.72396e-08 | 0.1988 |
| London_vs_NewYork | 974 | 974 | 8.239e+04 | 9.7685e-70 | 2.93055e-69 | -0.653 |
| Asia_vs_NewYork | 974 | 974 | 1.005e+05 | 8.20497e-55 | 1.64099e-54 | -0.5768 |

### volume

| Pair | n | n_nonzero | statistic | p-value | p-Holm | rank-biserial |
|------|---|-----------|-----------|---------|--------|----------------|
| Asia_vs_London | 974 | 974 | 4.87e+04 | 1.98269e-102 | 3.96539e-102 | 0.7949 |
| London_vs_NewYork | 974 | 974 | 6301 | 1.21934e-152 | 3.65801e-152 | -0.9735 |
| Asia_vs_NewYork | 974 | 974 | 6.056e+04 | 3.36499e-90 | 3.36499e-90 | -0.7449 |

## Bootstrap (95%, UTC-day blocks, 10,000 iterations)

### session_return

#### Session medians (percentile bootstrap CI)

| Session | Observed median | CI low | CI high |
|---------|-----------------|--------|---------|
| Asia | 0.000461993 | -6.86208e-05 | 0.00104606 |
| London | 0.000220817 | -0.000183239 | 0.000669015 |
| NewYork | 0.000280052 | -0.000164976 | 0.00108618 |

#### Friedman chi-square bootstrap distribution (not a confidence interval)

- Observed chi-square: 0.3963
- Bootstrap 2.5th percentile:  0.05749
- Bootstrap 97.5th percentile: 8.83
- Valid iterations: 10000
- Note: Distribution of Friedman chi-square under UTC-day block resampling. Not a confidence interval for a population parameter.

### abs_return

#### Session medians (percentile bootstrap CI)

| Session | Observed median | CI low | CI high |
|---------|-----------------|--------|---------|
| Asia | 0.00507804 | 0.00456222 | 0.00559457 |
| London | 0.00367507 | 0.00335446 | 0.00393209 |
| NewYork | 0.00708866 | 0.00651351 | 0.00802187 |

#### Friedman chi-square bootstrap distribution (not a confidence interval)

- Observed chi-square: 155.4
- Bootstrap 2.5th percentile:  113.4
- Bootstrap 97.5th percentile: 205.9
- Valid iterations: 10000
- Note: Distribution of Friedman chi-square under UTC-day block resampling. Not a confidence interval for a population parameter.

### session_range

#### Session medians (percentile bootstrap CI)

| Session | Observed median | CI low | CI high |
|---------|-----------------|--------|---------|
| Asia | 1150.86 | 1102.53 | 1187.13 |
| London | 877.36 | 827.13 | 916.695 |
| NewYork | 1672.92 | 1584.31 | 1772.21 |

#### Friedman chi-square bootstrap distribution (not a confidence interval)

- Observed chi-square: 647.8
- Bootstrap 2.5th percentile:  576
- Bootstrap 97.5th percentile: 724.8
- Valid iterations: 10000
- Note: Distribution of Friedman chi-square under UTC-day block resampling. Not a confidence interval for a population parameter.

### realized_volatility

#### Session medians (percentile bootstrap CI)

| Session | Observed median | CI low | CI high |
|---------|-----------------|--------|---------|
| Asia | 0.00307342 | 0.00294438 | 0.00321752 |
| London | 0.00264262 | 0.00251783 | 0.00279351 |
| NewYork | 0.00448857 | 0.00425353 | 0.00473243 |

#### Friedman chi-square bootstrap distribution (not a confidence interval)

- Observed chi-square: 352.1
- Bootstrap 2.5th percentile:  291.9
- Bootstrap 97.5th percentile: 419.3
- Valid iterations: 10000
- Note: Distribution of Friedman chi-square under UTC-day block resampling. Not a confidence interval for a population parameter.

### volume

#### Session medians (percentile bootstrap CI)

| Session | Observed median | CI low | CI high |
|---------|-----------------|--------|---------|
| Asia | 5666.69 | 5390.34 | 5924.23 |
| London | 3747.41 | 3564.15 | 3911.55 |
| NewYork | 9249.44 | 8735.07 | 9680.26 |

#### Friedman chi-square bootstrap distribution (not a confidence interval)

- Observed chi-square: 1194
- Bootstrap 2.5th percentile:  1122
- Bootstrap 97.5th percentile: 1264
- Valid iterations: 10000
- Note: Distribution of Friedman chi-square under UTC-day block resampling. Not a confidence interval for a population parameter.

## Sub-period stability

### session_return

- 2024: Friedman p=0.738393, n_days=366
- 2025: Friedman p=0.584507, n_days=365
- 2026_Jan_Aug: Friedman p=0.129879, n_days=243

### abs_return

- 2024: Friedman p=4.16787e-18, n_days=366
- 2025: Friedman p=2.23022e-13, n_days=365
- 2026_Jan_Aug: Friedman p=9.5433e-06, n_days=243

### session_range

- 2024: Friedman p=7.8208e-56, n_days=366
- 2025: Friedman p=1.2377e-56, n_days=365
- 2026_Jan_Aug: Friedman p=5.59404e-31, n_days=243

### realized_volatility

- 2024: Friedman p=7.46256e-33, n_days=366
- 2025: Friedman p=4.96619e-36, n_days=365
- 2026_Jan_Aug: Friedman p=1.66447e-11, n_days=243

### volume

- 2024: Friedman p=3.08724e-108, n_days=366
- 2025: Friedman p=5.71875e-98, n_days=365
- 2026_Jan_Aug: Friedman p=2.29226e-56, n_days=243

## Interpretation (per §9)

**STRUCTURE DETECTED**

- Significant metrics: abs_return, session_range, realized_volatility, volume
- Pairs surviving Holm: abs_return:Asia_vs_London, abs_return:London_vs_NewYork, abs_return:Asia_vs_NewYork, session_range:Asia_vs_London, session_range:London_vs_NewYork, session_range:Asia_vs_NewYork, realized_volatility:Asia_vs_London, realized_volatility:London_vs_NewYork, realized_volatility:Asia_vs_NewYork, volume:Asia_vs_London, volume:London_vs_NewYork, volume:Asia_vs_NewYork

---

This is a diagnostic result. Not a trading recommendation.