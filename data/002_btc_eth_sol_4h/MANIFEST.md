# Data Manifest — Experiment 002

- **data_status:** FROZEN
- **timeframe:** 4h
- **columns:** Open, High, Low, Close, Volume

## Provenance

| Symbol | Source | Notes |
|--------|--------|-------|
| BTC-USD | yfinance | canonical byte-exact copy from Exp 001 |
| ETH-USD | Binance public klines API (ETHUSDT) | fetched for exact Exp 001 UTC window |
| SOL-USD | Binance public klines API (SOLUSDT) | fetched for exact Exp 001 UTC window |

## Raw fetch summary

- ETH-USD raw rows: 4378
- SOL-USD raw rows: 4378
- BTC canonical rows: 4334

## Common-grid intersection

Analysis universe = intersection of timestamps present in all
three frozen asset series (BTC canonical ∩ ETH ∩ SOL).

- common_first_timestamp: 2024-09-14T00:00:00+00:00
- common_last_timestamp:  2026-09-13T12:00:00+00:00
- common_row_count:       4334
- Binance-only timestamps excluded by construction: 44

The excluded timestamps are NOT dropped silently. They are
excluded by the pre-registered common-grid intersection rule
recorded in Amendment 001 of PRE_REGISTRATION.md.

## Assets (final frozen)

| Symbol | File | Rows | First | Last | SHA-256 |
|--------|------|------|-------|------|---------|
| BTC-USD | BTC-USD_4h.csv | 4334 | 2024-09-14T00:00:00+00:00 | 2026-09-13T12:00:00+00:00 | `0aaaa726e79c238b74688d58982816a4d263bb2339d9793049bd0764e1cc1296` |
| ETH-USD | ETH-USD_4h.csv | 4334 | 2024-09-14T00:00:00+00:00 | 2026-09-13T12:00:00+00:00 | `6c52a771499fcc23603ee4dedebafdd04072609b3654d7b03c220648f8d7ed3e` |
| SOL-USD | SOL-USD_4h.csv | 4334 | 2024-09-14T00:00:00+00:00 | 2026-09-13T12:00:00+00:00 | `3781a99f3cd4d191f5bdbceb16ab9dbbd0440f97260293c4754fcbfb284eca1b` |

- **retrieved_at:** 2026-09-14T14:20:09.817521+00:00

> FROZEN canonical research snapshot for Experiment 002.
> Reproducibility relies on these CSVs, not on re-downloading.
> All three assets share the exact same timestamp grid.