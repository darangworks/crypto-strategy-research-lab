from __future__ import annotations

import csv
import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path


SYMBOL = "BTCUSDT"
INTERVAL = "1h"

START_MONTH = "2024-01"
END_MONTH = "2026-08"

START_TIME_MS = 1704067200000
END_TIME_MS = 1788217200000  # 2026-08-31 23:00 UTC

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

FROZEN_ROOT = (
    ROOT
    / "experiments"
    / "004_btc_intraday_session_effects"
    / "data"
    / "frozen"
)

MANIFEST_ROOT = (
    ROOT
    / "experiments"
    / "004_btc_intraday_session_effects"
    / "data"
    / "manifests"
)

FROZEN_FILE = (
    FROZEN_ROOT
    / "BTCUSDT_1h_2024-01-01_2026-08-31.csv"
)

MANIFEST_FILE = (
    MANIFEST_ROOT
    / "BTCUSDT_1h_2024-01-01_2026-08-31_manifest.txt"
)


def iter_months(start: str, end: str):
    year, month = map(int, start.split("-"))
    end_year, end_month = map(int, end.split("-"))

    while (year, month) <= (end_year, end_month):
        yield f"{year:04d}-{month:02d}"

        month += 1

        if month == 13:
            month = 1
            year += 1


def expected_filename(month: str) -> str:
    return f"{SYMBOL}-1h-{month}.csv"


def timestamp_unit(timestamp: int) -> str:
    """
    Detect Binance timestamp unit.

    2024 data:
        milliseconds

    2025+ Spot data:
        microseconds
    """

    if timestamp >= 10**15:
        return "microseconds"

    if timestamp >= 10**12:
        return "milliseconds"

    return "invalid"


def to_microseconds(timestamp: int) -> int:
    unit = timestamp_unit(timestamp)

    if unit == "milliseconds":
        return timestamp * 1000

    if unit == "microseconds":
        return timestamp

    raise ValueError(f"Invalid timestamp: {timestamp}")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def main() -> int:

    print("=" * 72)
    print("Experiment 004 — Canonical Dataset Merge & Freeze")
    print("=" * 72)
    print()

    months = list(iter_months(START_MONTH, END_MONTH))

    print(f"Expected monthly files: {len(months)}")
    print(f"Output: {FROZEN_FILE}")
    print()

    # -------------------------------------------------------------
    # Never overwrite an existing frozen dataset
    # -------------------------------------------------------------

    if FROZEN_FILE.exists():

        print("ERROR: Frozen dataset already exists.")
        print()
        print("No overwrite is permitted.")
        print("Remove it only through an explicit research decision.")

        return 1

    FROZEN_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    MANIFEST_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    rows = []

    seen_open_times = set()

    total_rows = 0
    duplicate_count = 0
    global_gap_count = 0
    chronology_error_count = 0

    validation_errors = []

    previous_open_us = None

    # -------------------------------------------------------------
    # Read all monthly files in chronological order
    # -------------------------------------------------------------

    for index, month in enumerate(
        months,
        start=1,
    ):

        filename = expected_filename(month)
        path = EXTRACTED_ROOT / filename

        print(
            f"[{index:02d}/{len(months):02d}] "
            f"{filename}"
        )

        # ---------------------------------------------------------
        # File existence
        # ---------------------------------------------------------

        if not path.exists():

            validation_errors.append(
                f"{filename}: file missing"
            )

            print("    FILE: MISSING")
            continue

        monthly_rows = 0

        with path.open(
            "r",
            encoding="utf-8",
            newline="",
        ) as f:

            reader = csv.reader(f)

            for line_number, row in enumerate(
                reader,
                start=1,
            ):

                # -------------------------------------------------
                # Schema
                # -------------------------------------------------

                if len(row) != 12:

                    validation_errors.append(
                        f"{filename}:{line_number}: "
                        f"expected 12 fields, "
                        f"got {len(row)}"
                    )

                    continue

                # -------------------------------------------------
                # Timestamp parsing
                # -------------------------------------------------

                try:
                    open_time = int(row[0])
                    close_time = int(row[6])

                except ValueError:

                    validation_errors.append(
                        f"{filename}:{line_number}: "
                        f"invalid timestamp"
                    )

                    continue

                try:
                    open_us = to_microseconds(
                        open_time
                    )

                    close_us = to_microseconds(
                        close_time
                    )

                except ValueError as exc:

                    validation_errors.append(
                        f"{filename}:{line_number}: "
                        f"{exc}"
                    )

                    continue

                # -------------------------------------------------
                # Timestamp sanity
                # -------------------------------------------------

                if open_us < START_TIME_MS * 1000:

                    validation_errors.append(
                        f"{filename}:{line_number}: "
                        f"open_time before research start"
                    )

                if open_us > END_TIME_MS * 1000:

                    validation_errors.append(
                        f"{filename}:{line_number}: "
                        f"open_time after research end"
                    )

                # close_time must be a valid timestamp.
                # We intentionally DO NOT impose a fabricated
                # open_time/close_time duration relationship.
                if close_us < open_us:

                    validation_errors.append(
                        f"{filename}:{line_number}: "
                        f"close_time before open_time"
                    )

                # -------------------------------------------------
                # Global duplicate detection
                # -------------------------------------------------

                if open_us in seen_open_times:

                    duplicate_count += 1

                    validation_errors.append(
                        f"{filename}:{line_number}: "
                        f"duplicate global open_time "
                        f"{open_us}"
                    )

                    continue

                seen_open_times.add(open_us)

                # -------------------------------------------------
                # Global chronology + exact 1H spacing
                # -------------------------------------------------

                if previous_open_us is not None:

                    delta = (
                        open_us
                        - previous_open_us
                    )

                    if delta <= 0:

                        chronology_error_count += 1

                        validation_errors.append(
                            f"{filename}:{line_number}: "
                            f"non-increasing open_time; "
                            f"delta={delta}"
                        )

                    elif delta != 3_600_000_000:

                        global_gap_count += 1

                        validation_errors.append(
                            f"{filename}:{line_number}: "
                            f"global spacing {delta} "
                            f"microseconds; expected "
                            f"3600000000"
                        )

                # IMPORTANT:
                # This must execute for EVERY valid row,
                # not only inside the previous_open_us condition.
                previous_open_us = open_us

                # -------------------------------------------------
                # OHLC / volume / trades
                # -------------------------------------------------

                try:

                    open_price = float(row[1])
                    high_price = float(row[2])
                    low_price = float(row[3])
                    close_price = float(row[4])

                    volume = float(row[5])
                    trades = int(row[8])

                except ValueError:

                    validation_errors.append(
                        f"{filename}:{line_number}: "
                        f"invalid numeric field"
                    )

                    continue

                # -------------------------------------------------
                # Price validity
                # -------------------------------------------------

                if open_price <= 0:

                    validation_errors.append(
                        f"{filename}:{line_number}: "
                        f"open <= 0"
                    )

                if high_price <= 0:

                    validation_errors.append(
                        f"{filename}:{line_number}: "
                        f"high <= 0"
                    )

                if low_price <= 0:

                    validation_errors.append(
                        f"{filename}:{line_number}: "
                        f"low <= 0"
                    )

                if close_price <= 0:

                    validation_errors.append(
                        f"{filename}:{line_number}: "
                        f"close <= 0"
                    )

                if high_price < max(
                    open_price,
                    close_price,
                ):

                    validation_errors.append(
                        f"{filename}:{line_number}: "
                        f"high below open/close"
                    )

                if low_price > min(
                    open_price,
                    close_price,
                ):

                    validation_errors.append(
                        f"{filename}:{line_number}: "
                        f"low above open/close"
                    )

                if low_price > high_price:

                    validation_errors.append(
                        f"{filename}:{line_number}: "
                        f"low > high"
                    )

                # -------------------------------------------------
                # Volume / trade count
                # -------------------------------------------------

                if volume < 0:

                    validation_errors.append(
                        f"{filename}:{line_number}: "
                        f"negative volume"
                    )

                if trades < 0:

                    validation_errors.append(
                        f"{filename}:{line_number}: "
                        f"negative trade count"
                    )

                # -------------------------------------------------
                # Preserve original Binance row unchanged
                # -------------------------------------------------

                rows.append(row)

                monthly_rows += 1
                total_rows += 1

        print(
            f"    Rows: {monthly_rows:,}"
        )

    print()

    # -------------------------------------------------------------
    # Expected global row count
    # -------------------------------------------------------------

    expected_total_rows = 23_376

    if total_rows != expected_total_rows:

        validation_errors.append(
            f"unexpected global row count: "
            f"{total_rows}; "
            f"expected {expected_total_rows}"
        )

    # -------------------------------------------------------------
    # Exact first / last timestamps
    # -------------------------------------------------------------

    if rows:

        try:

            first_us = to_microseconds(
                int(rows[0][0])
            )

            last_us = to_microseconds(
                int(rows[-1][0])
            )

        except ValueError as exc:

            validation_errors.append(
                f"boundary timestamp error: {exc}"
            )

        else:

            expected_first_us = (
                START_TIME_MS * 1000
            )

            expected_last_us = (
                END_TIME_MS * 1000
            )

            if first_us != expected_first_us:

                validation_errors.append(
                    f"unexpected first global "
                    f"timestamp: {first_us}; "
                    f"expected {expected_first_us}"
                )

            if last_us != expected_last_us:

                validation_errors.append(
                    f"unexpected last global "
                    f"timestamp: {last_us}; "
                    f"expected {expected_last_us}"
                )

    else:

        validation_errors.append(
            "no rows were loaded"
        )

    # -------------------------------------------------------------
    # Global Audit Summary
    # -------------------------------------------------------------

    print("=" * 72)
    print("GLOBAL AUDIT")
    print("=" * 72)

    print(
        f"Total rows        : {total_rows:,}"
    )

    print(
        f"Unique open_time  : "
        f"{len(seen_open_times):,}"
    )

    print(
        f"Duplicates        : "
        f"{duplicate_count:,}"
    )

    print(
        f"Global gaps       : "
        f"{global_gap_count:,}"
    )

    print(
        f"Chronology errors : "
        f"{chronology_error_count:,}"
    )

    print(
        f"Validation errors : "
        f"{len(validation_errors):,}"
    )

    print()

    # -------------------------------------------------------------
    # HARD STOP
    # -------------------------------------------------------------

    if validation_errors:

        print("STATUS: FAIL")
        print()
        print("NO FROZEN DATASET WAS CREATED.")
        print()

        for error in validation_errors[:25]:

            print(
                f"ERROR: {error}"
            )

        if len(validation_errors) > 25:

            print(
                f"... "
                f"{len(validation_errors) - 25} "
                f"additional errors"
            )

        return 1

    print(
        "Global validation: PASS"
    )

    print()

    # -------------------------------------------------------------
    # Write canonical dataset
    # -------------------------------------------------------------

    print("=" * 72)
    print("WRITING CANONICAL DATASET")
    print("=" * 72)

    temp_file = FROZEN_FILE.with_suffix(
        ".tmp"
    )

    try:

        with temp_file.open(
            "w",
            encoding="utf-8",
            newline="",
        ) as f:

            writer = csv.writer(f)

            # Canonical artifact gets a header.
            # Raw extracted Binance CSVs remain untouched.
            writer.writerow(
                EXPECTED_COLUMNS
            )

            writer.writerows(rows)

        # Atomic rename after successful write.
        temp_file.replace(
            FROZEN_FILE
        )

    except Exception:

        if temp_file.exists():
            temp_file.unlink()

        raise

    print(
        f"Created: {FROZEN_FILE}"
    )

    # -------------------------------------------------------------
    # SHA-256
    # -------------------------------------------------------------

    dataset_sha256 = sha256_file(
        FROZEN_FILE
    )

    print()
    print(
        f"SHA-256: {dataset_sha256}"
    )

    # -------------------------------------------------------------
    # Manifest
    # -------------------------------------------------------------

    now_utc = datetime.now(
        timezone.utc
    ).isoformat()

    manifest_lines = [

        "Experiment 004 — "
        "BTCUSDT 1H Canonical Dataset",

        "",

        f"Symbol: {SYMBOL}",
        f"Interval: {INTERVAL}",
        "Market: Binance Spot",
        "Timezone: UTC",

        "",

        "Research start: "
        "2024-01-01 00:00:00 UTC",

        "Research end: "
        "2026-08-31 23:00:00 UTC",

        "",

        f"Monthly files merged: "
        f"{len(months)}",

        f"Total rows: "
        f"{total_rows}",

        f"Duplicates: "
        f"{duplicate_count}",

        f"Global gaps: "
        f"{global_gap_count}",

        f"Chronology errors: "
        f"{chronology_error_count}",

        "",

        f"Created at UTC: "
        f"{now_utc}",

        "",

        f"Canonical file: "
        f"{FROZEN_FILE.name}",

        f"SHA-256: "
        f"{dataset_sha256}",

        "",

        "Source:",
        "Binance Spot monthly Kline archives",

        "",

        "Timestamp convention:",
        "2024 data: milliseconds",
        "2025-01 onward: microseconds",

        "",

        "Transformation:",
        "Monthly extracted rows merged chronologically.",
        "Original Binance row values preserved.",
        "Canonical CSV adds a descriptive header.",

        "",

        "Validation:",
        "Global duplicate check: PASS",
        "Global chronology check: PASS",
        "Exact 1H spacing check: PASS",
        "Research boundary check: PASS",
        "OHLC validation: PASS",
        "Volume validation: PASS",
        "Trade-count validation: PASS",

        "",

        "Status: FROZEN",

        "",
    ]

    MANIFEST_FILE.write_text(
        "\n".join(manifest_lines),
        encoding="utf-8",
    )

    print(
        f"Manifest: {MANIFEST_FILE}"
    )

    print()

    # -------------------------------------------------------------
    # Final status
    # -------------------------------------------------------------

    print("=" * 72)
    print("FREEZE COMPLETE")
    print("=" * 72)

    print(
        f"Rows      : {total_rows:,}"
    )

    print(
        f"SHA-256   : {dataset_sha256}"
    )

    print(
        "STATUS    : PASS"
    )

    print()

    print(
        "Canonical dataset is now frozen."
    )

    print(
        "No analysis was performed."
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
