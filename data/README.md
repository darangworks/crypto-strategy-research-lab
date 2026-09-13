# Data

Frozen market-data snapshots for reproducibility.

## Policy

- No live data in backtests.
- Each snapshot has MANIFEST.md with SHA-256 hashes.
- CSVs are gitignored.

## Reproducibility

A SHA-256 hash makes a frozen file verifiable.
Re-downloading is not guaranteed to reproduce the same bytes.

## Manifest Template

source, symbol, timeframe, start, end, retrieved_at, row_count, columns, sha256
