#!/usr/bin/env python3

"""
Experiment 004 — BTC Intraday Session Effects

Monthly Binance Spot 1H archive extractor.

Scope:
    BTCUSDT Spot
    1H
    2024-01 through 2026-08

This script:
    1. Finds all SHA-256-verified monthly ZIP archives.
    2. Extracts the expected CSV from each archive.
    3. Writes extracted CSVs to data/raw/extracted/.
    4. Refuses to overwrite existing extracted files.
    5. Performs basic archive/schema checks.
    6. Supports a dry-run mode.

This script does NOT:
    - merge CSV files
    - modify raw ZIP archives
    - modify CHECKSUM files
    - perform session analysis
    - calculate statistics
    - perform strategy research
"""

from __future__ import annotations

import argparse
import csv
import sys
import zipfile
from pathlib import Path


# ---------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------

SYMBOL = "BTCUSDT"
INTERVAL = "1h"

START_YEAR = 2024
START_MONTH = 1

END_YEAR = 2026
END_MONTH = 8

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

ARCHIVE_ROOT = (
    ROOT
    / "experiments"
    / "004_btc_intraday_session_effects"
    / "data"
    / "raw"
    / "archives"
)

LEGACY_ARCHIVE_ROOT = (
    ROOT
    / "experiments"
    / "004_btc_intraday_session_effects"
    / "data"
    / "raw"
)

EXTRACTED_ROOT = (
    ROOT
    / "experiments"
    / "004_btc_intraday_session_effects"
    / "data"
    / "raw"
    / "extracted"
)


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------

def iter_months():
    """Yield all (year, month) pairs in the locked period."""

    year = START_YEAR
    month = START_MONTH

    while (year, month) <= (END_YEAR, END_MONTH):

        yield year, month

        month += 1

        if month == 13:
            month = 1
            year += 1


def archive_name(year: int, month: int) -> str:
    """Return the expected Binance ZIP filename."""

    return (
        f"{SYMBOL}-{INTERVAL}-"
        f"{year:04d}-{month:02d}.zip"
    )


def expected_csv_name(year: int, month: int) -> str:
    """Return the expected CSV filename inside the ZIP."""

    return (
        f"{SYMBOL}-{INTERVAL}-"
        f"{year:04d}-{month:02d}.csv"
    )


def archive_paths(year: int, month: int):
    """
    Resolve the archive location.

    First checks the new annual archive structure.
    Then checks the existing frozen August 2026 snapshot.
    """

    name = archive_name(year, month)

    canonical = (
        ARCHIVE_ROOT
        / str(year)
        / name
    )

    if canonical.exists():
        return canonical

    legacy = LEGACY_ARCHIVE_ROOT / name

    if legacy.exists():
        return legacy

    return None


def validate_csv_schema(
    csv_path: Path,
    expected_name: str,
) -> None:
    """
    Validate a Binance Spot Kline CSV.

    Binance Kline CSV files are data-only and do not contain
    a header row. Therefore validation is performed against
    the first data row and the expected 12-field schema.
    """

    with csv_path.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as f:
        reader = csv.reader(f)

        try:
            first_row = next(reader)
        except StopIteration as exc:
            raise RuntimeError(
                f"CSV is empty: {csv_path}"
            ) from exc

    if len(first_row) != len(EXPECTED_COLUMNS):
        raise RuntimeError(
            f"Unexpected column count in {expected_name}.\n"
            f"Expected: {len(EXPECTED_COLUMNS)}\n"
            f"Actual: {len(first_row)}\n"
            f"First row: {first_row}"
        )

    # -------------------------------------------------------------
    # Validate timestamp fields.
    #
    # Do NOT assume milliseconds here.
    # Binance Spot timestamps switched to microseconds
    # from 2025-01-01 onward.
    # -------------------------------------------------------------

    try:
        int(first_row[0])
        int(first_row[6])
    except ValueError as exc:
        raise RuntimeError(
            f"Invalid timestamp field in {expected_name}.\n"
            f"First row: {first_row}"
        ) from exc

    # -------------------------------------------------------------
    # Validate numeric OHLCV fields.
    # -------------------------------------------------------------

    numeric_float_indices = [
        1,  # open
        2,  # high
        3,  # low
        4,  # close
        5,  # volume
        7,  # quote_asset_volume
        9,  # taker_buy_base_asset_volume
        10,  # taker_buy_quote_asset_volume
    ]

    for index in numeric_float_indices:
        try:
            float(first_row[index])
        except ValueError as exc:
            raise RuntimeError(
                f"Invalid numeric field in {expected_name}.\n"
                f"Column: {EXPECTED_COLUMNS[index]}\n"
                f"Value: {first_row[index]!r}\n"
                f"First row: {first_row}"
            ) from exc

    # -------------------------------------------------------------
    # Number of trades must be an integer.
    # -------------------------------------------------------------

    try:
        int(first_row[8])
    except ValueError as exc:
        raise RuntimeError(
            f"Invalid number_of_trades in {expected_name}.\n"
            f"Value: {first_row[8]!r}"
        ) from exc

    # -------------------------------------------------------------
    # Ignore field is retained exactly as supplied.
    # -------------------------------------------------------------

    print(
        f"       Schema validation: "
        f"12 fields / data-row format"
    )


def inspect_archive(
    archive_path: Path,
    expected_csv: str,
) -> None:
    """Check archive contents without extracting."""

    with zipfile.ZipFile(
        archive_path,
        "r",
    ) as archive:

        if archive.testzip() is not None:
            raise RuntimeError(
                f"ZIP integrity check failed: "
                f"{archive_path}"
            )

        members = archive.namelist()

        csv_members = [
            name
            for name in members
            if name.lower().endswith(".csv")
        ]

        if len(csv_members) != 1:
            raise RuntimeError(
                f"Expected exactly one CSV in "
                f"{archive_path}, found "
                f"{len(csv_members)}:\n"
                f"{csv_members}"
            )

        actual_csv = Path(
            csv_members[0]
        ).name

        if actual_csv != expected_csv:
            raise RuntimeError(
                f"Unexpected CSV filename.\n"
                f"Expected: {expected_csv}\n"
                f"Actual:   {actual_csv}"
            )


def extract_archive(
    archive_path: Path,
    output_path: Path,
    expected_csv: str,
) -> None:
    """
    Extract the expected CSV without overwriting
    an existing output file.
    """

    if output_path.exists():
        raise FileExistsError(
            f"Refusing to overwrite existing "
            f"extracted file: {output_path}"
        )

    with zipfile.ZipFile(
        archive_path,
        "r",
    ) as archive:

        csv_members = [
            name
            for name in archive.namelist()
            if name.lower().endswith(".csv")
        ]

        if len(csv_members) != 1:
            raise RuntimeError(
                f"Expected exactly one CSV in "
                f"{archive_path}, found "
                f"{len(csv_members)}."
            )

        member = csv_members[0]

        actual_csv = Path(member).name

        if actual_csv != expected_csv:
            raise RuntimeError(
                f"Unexpected CSV filename.\n"
                f"Expected: {expected_csv}\n"
                f"Actual:   {actual_csv}"
            )

        # Extract to memory-backed bytes first.
        # This prevents creating a partial destination file
        # if extraction fails.
        data = archive.read(member)

    output_path.write_bytes(data)


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------

def main() -> int:

    parser = argparse.ArgumentParser(
        description=(
            "Extract verified Binance BTCUSDT 1H "
            "monthly archives for Experiment 004."
        )
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Show the extraction plan without "
            "extracting anything."
        ),
    )

    args = parser.parse_args()

    print("=" * 72)
    print(
        "Experiment 004 — "
        "BTCUSDT 1H Archive Extractor"
    )
    print("=" * 72)

    print()

    print(f"Symbol:        {SYMBOL}")
    print(f"Interval:      {INTERVAL}")

    print(
        f"Period:        "
        f"{START_YEAR:04d}-{START_MONTH:02d} → "
        f"{END_YEAR:04d}-{END_MONTH:02d}"
    )

    print(
        f"Archive root:  "
        f"{ARCHIVE_ROOT}"
    )

    print(
        f"Extract root:  "
        f"{EXTRACTED_ROOT}"
    )

    print()

    months = list(iter_months())

    print(
        f"Expected archives: {len(months)}"
    )

    print()

    # -----------------------------------------------------------------
    # Dry run
    # -----------------------------------------------------------------

    if args.dry_run:

        print("=" * 72)
        print(
            "DRY RUN — "
            "NO FILES WILL BE EXTRACTED"
        )
        print("=" * 72)

        print()

        for index, (year, month) in enumerate(
            months,
            start=1,
        ):

            archive_path = archive_paths(
                year,
                month,
            )

            expected_csv = expected_csv_name(
                year,
                month,
            )

            output_path = (
                EXTRACTED_ROOT
                / expected_csv
            )

            print(
                f"[{index:02d}/{len(months)}] "
                f"{archive_name(year, month)}"
            )

            if archive_path is None:

                print(
                    "    ARCHIVE: MISSING"
                )

            else:

                print(
                    "    ARCHIVE: FOUND"
                )

                print(
                    f"    SOURCE:  "
                    f"{archive_path}"
                )

            print(
                f"    OUTPUT:  "
                f"{output_path}"
            )

            if output_path.exists():

                print(
                    "    OUTPUT STATUS: EXISTS"
                )

            else:

                print(
                    "    OUTPUT STATUS: MISSING"
                )

            print()

        print("=" * 72)
        print("DRY RUN COMPLETE")
        print("=" * 72)

        print(
            "No files were extracted or modified."
        )

        return 0

    # -----------------------------------------------------------------
    # Normal extraction
    # -----------------------------------------------------------------

    EXTRACTED_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    extracted = 0
    skipped = 0

    for index, (year, month) in enumerate(
        months,
        start=1,
    ):

        name = archive_name(
            year,
            month,
        )

        expected_csv = expected_csv_name(
            year,
            month,
        )

        output_path = (
            EXTRACTED_ROOT
            / expected_csv
        )

        print(
            f"[{index:02d}/{len(months)}] "
            f"{name}"
        )

        # -------------------------------------------------------------
        # Locate archive
        # -------------------------------------------------------------

        archive_path = archive_paths(
            year,
            month,
        )

        if archive_path is None:

            raise FileNotFoundError(
                f"Required archive not found: "
                f"{name}"
            )

        print(
            f"    Source: "
            f"{archive_path}"
        )

        # -------------------------------------------------------------
        # Existing extracted file
        # -------------------------------------------------------------

        if output_path.exists():

            print(
                "    Extracted CSV already exists."
            )

            print(
                "    Status: SKIPPED"
            )

            skipped += 1

            print()

            continue

        # -------------------------------------------------------------
        # Inspect archive
        # -------------------------------------------------------------

        print(
            "    Checking ZIP integrity..."
        )

        inspect_archive(
            archive_path,
            expected_csv,
        )

        print(
            "    ZIP integrity: PASS"
        )

        # -------------------------------------------------------------
        # Extract
        # -------------------------------------------------------------

        print(
            "    Extracting CSV..."
        )

        extract_archive(
            archive_path,
            output_path,
            expected_csv,
        )

        print(
            "    Extraction: PASS"
        )

        # -------------------------------------------------------------
        # Validate schema
        # -------------------------------------------------------------

        print(
            "    Validating CSV schema..."
        )

        validate_csv_schema(
            output_path,
            expected_csv,
        )

        print(
            "    CSV schema: PASS"
        )

        extracted += 1

        print()

    # -----------------------------------------------------------------
    # Final summary
    # -----------------------------------------------------------------

    print("=" * 72)
    print("EXTRACTION COMPLETE")
    print("=" * 72)

    print(
        f"Expected archives : "
        f"{len(months)}"
    )

    print(
        f"Extracted         : "
        f"{extracted}"
    )

    print(
        f"Already present   : "
        f"{skipped}"
    )

    print()

    if extracted + skipped != len(months):

        print(
            "STATUS: FAIL"
        )

        print(
            "Not all expected monthly "
            "CSV files are available."
        )

        return 1

    print(
        "STATUS: PASS"
    )

    print(
        "All expected monthly archives "
        "have corresponding extracted CSVs."
    )

    print()

    print(
        "No merge or analysis was performed."
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
