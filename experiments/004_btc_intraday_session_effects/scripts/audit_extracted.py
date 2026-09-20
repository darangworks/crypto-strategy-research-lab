from __future__ import annotations

import csv
import sys
from datetime import datetime, timezone
from pathlib import Path


SYMBOL = "BTCUSDT"
INTERVAL = "1h"

START_MONTH = "2024-01"
END_MONTH = "2026-08"

EXPECTED_COLUMNS = [
    "open_time",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "close_time",
    "quote_asset_volume",
    "number_of_trades",
    "taker_buy_base_asset_volume",
    "taker_buy_quote_asset_volume",
    "ignore",
]

ROOT = Path(__file__).resolve().parents[3]

EXTRACTED_ROOT = (
    ROOT
    / "experiments"
    / "004_btc_intraday_session_effects"
    / "data"
    / "raw"
    / "extracted"
)

EXPECTED_MONTHS = []


def iter_months(start: str, end: str):
    year, month = map(int, start.split("-"))
    end_year, end_month = map(int, end.split("-"))

    while (year, month) <= (end_year, end_month):
        yield f"{year:04d}-{month:02d}"

        month += 1
        if month == 13:
            month = 1
            year += 1


EXPECTED_MONTHS = list(iter_months(START_MONTH, END_MONTH))


def expected_filename(month: str) -> str:
    return f"{SYMBOL}-1h-{month}.csv"


def timestamp_unit(timestamp: int) -> str:
    """
    Determine timestamp unit from magnitude.

    BTCUSDT Spot:
      2024 data -> milliseconds
      2025+ data -> microseconds
    """

    if timestamp >= 10**15:
        return "microseconds"

    if timestamp >= 10**12:
        return "milliseconds"

    return "invalid"


def timestamp_to_datetime(timestamp: int) -> datetime:
    unit = timestamp_unit(timestamp)

    if unit == "microseconds":
        return datetime.fromtimestamp(
            timestamp / 1_000_000,
            tz=timezone.utc,
        )

    if unit == "milliseconds":
        return datetime.fromtimestamp(
            timestamp / 1_000,
            tz=timezone.utc,
        )

    raise ValueError(f"Invalid timestamp magnitude: {timestamp}")


def expected_timestamp_unit(month: str) -> str:
    year = int(month[:4])

    if year >= 2025:
        return "microseconds"

    return "milliseconds"


def audit_file(path: Path, month: str) -> dict:
    result = {
        "file": path.name,
        "month": month,
        "rows": 0,
        "status": "PASS",
        "errors": [],
        "first_open_time": None,
        "last_open_time": None,
        "timestamp_unit": None,
        "duplicates": 0,
        "gaps": 0,
        "invalid_ohlc": 0,
        "invalid_volume": 0,
        "invalid_trades": 0,
    }

    previous_open_time = None
    expected_unit = expected_timestamp_unit(month)

    with path.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as f:
        reader = csv.reader(f)

        for line_number, row in enumerate(reader, start=1):

            if len(row) != 12:
                result["errors"].append(
                    f"line {line_number}: expected 12 fields, got {len(row)}"
                )
                continue

            # -----------------------------------------------------
            # Header detection
            # -----------------------------------------------------

            if line_number == 1 and row == EXPECTED_COLUMNS:
                result["errors"].append(
                    "header row detected; Spot CSV must remain data-only"
                )
                continue

            # -----------------------------------------------------
            # Parse timestamps
            # -----------------------------------------------------

            try:
                open_time = int(row[0])
                close_time = int(row[6])
            except ValueError:
                result["errors"].append(
                    f"line {line_number}: invalid timestamp"
                )
                continue

            unit = timestamp_unit(open_time)

            if unit == "invalid":
                result["errors"].append(
                    f"line {line_number}: invalid timestamp magnitude"
                )

            if result["timestamp_unit"] is None:
                result["timestamp_unit"] = unit
            elif result["timestamp_unit"] != unit:
                result["errors"].append(
                    f"line {line_number}: mixed timestamp units"
                )

            if unit != expected_unit:
                result["errors"].append(
                    f"line {line_number}: expected {expected_unit}, "
                    f"found {unit}"
                )

            # -----------------------------------------------------
            # Convert timestamp for boundary validation
            # -----------------------------------------------------

            try:
                open_dt = timestamp_to_datetime(open_time)
                close_dt = timestamp_to_datetime(close_time)
            except ValueError:
                continue

            # -----------------------------------------------------
            # Row count
            # -----------------------------------------------------

            result["rows"] += 1

            if result["first_open_time"] is None:
                result["first_open_time"] = open_dt

            result["last_open_time"] = open_dt

            # -----------------------------------------------------
            # Chronology / duplicates / gaps
            # -----------------------------------------------------

            if previous_open_time is not None:

                delta = open_time - previous_open_time

                expected_delta = (
                    3_600_000_000
                    if unit == "microseconds"
                    else 3_600_000
                )

                if delta == 0:
                    result["duplicates"] += 1
                    result["errors"].append(
                        f"line {line_number}: duplicate open_time"
                    )

                elif delta != expected_delta:
                    result["gaps"] += 1

                    result["errors"].append(
                        f"line {line_number}: timestamp spacing "
                        f"{delta} != expected {expected_delta}"
                    )

            previous_open_time = open_time

            # -----------------------------------------------------
            # Close-time relationship
            # -----------------------------------------------------

            expected_close_delta = (
                3_599_999_999
                if unit == "microseconds"
                else 3_599_999
            )

            if close_time - open_time != expected_close_delta:
                result["errors"].append(
                    f"line {line_number}: invalid 1h close_time"
                )

            # -----------------------------------------------------
            # OHLC
            # -----------------------------------------------------

            try:
                open_price = float(row[1])
                high_price = float(row[2])
                low_price = float(row[3])
                close_price = float(row[4])
                volume = float(row[5])
                trades = int(row[8])
            except ValueError:
                result["errors"].append(
                    f"line {line_number}: invalid numeric field"
                )
                continue

            if (
                open_price <= 0
                or high_price <= 0
                or low_price <= 0
                or close_price <= 0
            ):
                result["invalid_ohlc"] += 1
                result["errors"].append(
                    f"line {line_number}: non-positive price"
                )

            if high_price < max(open_price, close_price):
                result["invalid_ohlc"] += 1
                result["errors"].append(
                    f"line {line_number}: high below open/close"
                )

            if low_price > min(open_price, close_price):
                result["invalid_ohlc"] += 1
                result["errors"].append(
                    f"line {line_number}: low above open/close"
                )

            if low_price > high_price:
                result["invalid_ohlc"] += 1
                result["errors"].append(
                    f"line {line_number}: low > high"
                )

            # -----------------------------------------------------
            # Volume
            # -----------------------------------------------------

            if volume < 0:
                result["invalid_volume"] += 1
                result["errors"].append(
                    f"line {line_number}: negative volume"
                )

            # -----------------------------------------------------
            # Trades
            # -----------------------------------------------------

            if trades < 0:
                result["invalid_trades"] += 1
                result["errors"].append(
                    f"line {line_number}: negative trade count"
                )

    # -------------------------------------------------------------
    # Monthly boundary checks
    # -------------------------------------------------------------

    if result["first_open_time"] is not None:
        expected_start = datetime.strptime(
            f"{month}-01",
            "%Y-%m-%d",
        ).replace(tzinfo=timezone.utc)

        if result["first_open_time"] != expected_start:
            result["errors"].append(
                f"unexpected first timestamp: "
                f"{result['first_open_time'].isoformat()} "
                f"(expected {expected_start.isoformat()})"
            )

    # Determine next month boundary.
    year = int(month[:4])
    m = int(month[5:7])

    if m == 12:
        next_month = datetime(
            year + 1,
            1,
            1,
            tzinfo=timezone.utc,
        )
    else:
        next_month = datetime(
            year,
            m + 1,
            1,
            tzinfo=timezone.utc,
        )

    expected_last = next_month.timestamp()

    if result["last_open_time"] is not None:
        actual_last = result["last_open_time"].timestamp()

        if actual_last != expected_last - 3600:
            result["errors"].append(
                f"unexpected last timestamp: "
                f"{result['last_open_time'].isoformat()} "
                f"(expected {(next_month.timestamp() - 3600):.0f} UTC)"
            )

    if result["errors"]:
        result["status"] = "FAIL"

    return result


def main() -> int:

    print("=" * 72)
    print("Experiment 004 — BTCUSDT 1H Extracted CSV Audit")
    print("=" * 72)
    print()
    print(f"Extract root: {EXTRACTED_ROOT}")
    print(f"Expected CSVs: {len(EXPECTED_MONTHS)}")
    print()

    results = []

    for index, month in enumerate(EXPECTED_MONTHS, start=1):

        filename = expected_filename(month)
        path = EXTRACTED_ROOT / filename

        print(
            f"[{index:02d}/{len(EXPECTED_MONTHS):02d}] "
            f"{filename}"
        )

        if not path.exists():
            print("    FILE: MISSING")
            print("    STATUS: FAIL")
            print()
            results.append(
                {
                    "file": filename,
                    "month": month,
                    "status": "FAIL",
                    "errors": ["file missing"],
                    "rows": 0,
                }
            )
            continue

        print("    FILE: FOUND")

        result = audit_file(path, month)

        print(f"    Rows: {result['rows']:,}")
        print(
            f"    Timestamp unit: "
            f"{result['timestamp_unit']}"
        )
        print(
            f"    Duplicates: "
            f"{result['duplicates']}"
        )
        print(
            f"    Gaps: "
            f"{result['gaps']}"
        )
        print(
            f"    Invalid OHLC: "
            f"{result['invalid_ohlc']}"
        )
        print(
            f"    Invalid volume: "
            f"{result['invalid_volume']}"
        )
        print(
            f"    Invalid trades: "
            f"{result['invalid_trades']}"
        )

        if result["status"] == "PASS":
            print("    STATUS: PASS")
        else:
            print("    STATUS: FAIL")

            for error in result["errors"][:10]:
                print(f"       ERROR: {error}")

            if len(result["errors"]) > 10:
                print(
                    f"       ... "
                    f"{len(result['errors']) - 10} more errors"
                )

        print()

        results.append(result)

    # -------------------------------------------------------------
    # Summary
    # -------------------------------------------------------------

    passed = sum(
        1 for r in results
        if r["status"] == "PASS"
    )

    failed = len(results) - passed

    total_rows = sum(
        r.get("rows", 0)
        for r in results
    )

    total_duplicates = sum(
        r.get("duplicates", 0)
        for r in results
    )

    total_gaps = sum(
        r.get("gaps", 0)
        for r in results
    )

    print("=" * 72)
    print("AUDIT SUMMARY")
    print("=" * 72)
    print(f"Expected CSVs : {len(EXPECTED_MONTHS)}")
    print(f"Passed        : {passed}")
    print(f"Failed        : {failed}")
    print(f"Total rows    : {total_rows:,}")
    print(f"Duplicates    : {total_duplicates:,}")
    print(f"Gaps          : {total_gaps:,}")
    print()

    if failed == 0:
        print("STATUS: PASS")
        print("All extracted monthly CSVs passed the audit.")
        return 0

    print("STATUS: FAIL")
    print("Do NOT merge or freeze the dataset.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
