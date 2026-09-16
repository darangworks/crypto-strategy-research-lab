import pandas as pd
from pathlib import Path

FILE = Path(
    "experiments/004_btc_intraday_session_effects/data/raw/"
    "BTCUSDT-1h-2026-08.csv"
)

COLUMNS = [
    "open_time",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "close_time",
]

# Read everything as strings first.
# This avoids accidental float conversion of large microsecond timestamps.
df = pd.read_csv(
    FILE,
    header=None,
    names=COLUMNS,
    dtype=str,
)

print("=" * 60)
print("BTCUSDT 1H DATA AUDIT — AUGUST 2026")
print("=" * 60)

print(f"Rows: {len(df)}")
print(f"Columns: {len(df.columns)}")

# Convert timestamp columns explicitly from strings to integers.
df["open_time"] = pd.to_numeric(
    df["open_time"],
    errors="raise",
).astype("int64")

df["close_time"] = pd.to_numeric(
    df["close_time"],
    errors="raise",
).astype("int64")

# Convert OHLCV fields explicitly.
for col in ["open", "high", "low", "close", "volume"]:
    df[col] = pd.to_numeric(
        df[col],
        errors="raise",
    )

# Binance Spot archive timestamps from 2025 onward are microseconds.
df["timestamp"] = pd.to_datetime(
    df["open_time"],
    unit="us",
    utc=True,
)

print(f"First timestamp: {df['timestamp'].iloc[0]}")
print(f"Last timestamp:  {df['timestamp'].iloc[-1]}")

# ------------------------------------------------------------
# Basic integrity
# ------------------------------------------------------------

missing_values = int(df.isna().sum().sum())
print(f"Missing values: {missing_values}")

duplicates = int(
    df["open_time"].duplicated().sum()
)
print(f"Duplicate timestamps: {duplicates}")

chronological = bool(
    df["open_time"].is_monotonic_increasing
)
print(f"Chronological order: {chronological}")

# ------------------------------------------------------------
# 1-hour spacing
# ------------------------------------------------------------

expected_delta_us = 60 * 60 * 1_000_000

deltas = df["open_time"].diff()

non_hourly = int(
    (deltas.iloc[1:] != expected_delta_us).sum()
)

print(f"Non-1H intervals: {non_hourly}")

if non_hourly:
    bad = df.loc[
        deltas != expected_delta_us,
        ["timestamp", "open_time"]
    ].copy()

    bad["previous_open_time"] = (
        df["open_time"].shift(1)
    )

    bad["delta_us"] = deltas

    print("\nUnexpected intervals:")
    print(
        bad[
            [
                "timestamp",
                "previous_open_time",
                "delta_us",
            ]
        ]
        .head(20)
        .to_string(index=False)
    )

# ------------------------------------------------------------
# OHLC integrity
# ------------------------------------------------------------

ohlc_violations = int(
    (
        (df["high"] < df["open"]) |
        (df["high"] < df["close"]) |
        (df["high"] < df["low"]) |
        (df["low"] > df["open"]) |
        (df["low"] > df["close"]) |
        (df["low"] > df["high"])
    ).sum()
)

print(f"OHLC violations: {ohlc_violations}")

# ------------------------------------------------------------
# Volume integrity
# ------------------------------------------------------------

negative_volume = int(
    (df["volume"] < 0).sum()
)

zero_volume = int(
    (df["volume"] == 0).sum()
)

print(f"Negative volume: {negative_volume}")
print(f"Zero volume: {zero_volume}")

# ------------------------------------------------------------
# Expected August 2026 coverage
# ------------------------------------------------------------

expected_rows = 31 * 24

print(f"Expected rows: {expected_rows}")
print(
    f"Row-count check: "
    f"{len(df) == expected_rows}"
)

# ------------------------------------------------------------
# Final checks
# ------------------------------------------------------------

checks = {
    "row_count": len(df) == expected_rows,
    "no_missing_values": missing_values == 0,
    "no_duplicates": duplicates == 0,
    "chronological": chronological,
    "hourly_spacing": non_hourly == 0,
    "ohlc_integrity": ohlc_violations == 0,
    "non_negative_volume": negative_volume == 0,
}

print("=" * 60)
print("CHECKS")
print("-" * 60)

for name, result in checks.items():
    print(
        f"{name:25} "
        f"{'PASS' if result else 'FAIL'}"
    )

print("-" * 60)

overall = all(checks.values())

print(
    f"OVERALL DATA GATE: "
    f"{'PASS' if overall else 'FAIL'}"
)
