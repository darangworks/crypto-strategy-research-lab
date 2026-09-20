#!/usr/bin/env python3

"""
Experiment 004 — BTC Intraday Session Effects

Monthly Binance Spot 1H archive downloader.

Scope:
    BTCUSDT Spot
    1H
    2024-01 through 2026-08

This script:
    1. Downloads monthly Binance Spot Kline ZIP archives.
    2. Downloads the corresponding CHECKSUM files.
    3. Verifies SHA-256.
    4. Never overwrites an existing verified archive.
    5. Preserves the already-frozen August 2026 snapshot.
    6. Supports a dry-run mode.

It does NOT:
    - extract CSVs
    - merge datasets
    - modify existing data
    - perform research analysis
"""

from __future__ import annotations

import argparse
import hashlib
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


# ---------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------

SYMBOL = "BTCUSDT"
INTERVAL = "1h"

START_YEAR = 2024
START_MONTH = 1

END_YEAR = 2026
END_MONTH = 8

BASE_URL = "https://data.binance.vision/data/spot/monthly/klines"

# Repository root
ROOT = Path(__file__).resolve().parents[3]

# New canonical archive structure
ARCHIVE_ROOT = (
    ROOT
    / "experiments"
    / "004_btc_intraday_session_effects"
    / "data"
    / "raw"
    / "archives"
)

# Existing frozen August 2026 snapshot.
# This file must NOT be moved or downloaded again.
LEGACY_ARCHIVE_ROOT = (
    ROOT
    / "experiments"
    / "004_btc_intraday_session_effects"
    / "data"
    / "raw"
)

CHUNK_SIZE = 1024 * 1024
TIMEOUT_SECONDS = 60
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 3


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------

def iter_months():
    """Yield (year, month) from the locked research period."""

    year = START_YEAR
    month = START_MONTH

    while (year, month) <= (END_YEAR, END_MONTH):
        yield year, month

        month += 1

        if month == 13:
            month = 1
            year += 1


def archive_name(year: int, month: int) -> str:
    """Return the Binance monthly archive filename."""

    return f"{SYMBOL}-{INTERVAL}-{year:04d}-{month:02d}.zip"


def archive_url(year: int, month: int) -> str:
    """Return the Binance monthly archive URL."""

    return (
        f"{BASE_URL}/{SYMBOL}/{INTERVAL}/"
        f"{archive_name(year, month)}"
    )


def checksum_url(year: int, month: int) -> str:
    """Return the Binance CHECKSUM URL."""

    return archive_url(year, month) + ".CHECKSUM"


def legacy_paths(year: int, month: int):
    """
    Return the paths for an already-frozen legacy snapshot.

    This is intentionally limited to the existing archive layout.
    It does not move, copy, or modify the files.

    If both archive and CHECKSUM exist, return their paths.
    Otherwise return (None, None).
    """

    name = archive_name(year, month)

    archive_path = LEGACY_ARCHIVE_ROOT / name
    checksum_path = LEGACY_ARCHIVE_ROOT / f"{name}.CHECKSUM"

    if archive_path.exists() and checksum_path.exists():
        return archive_path, checksum_path

    return None, None


def sha256_file(path: Path) -> str:
    """Calculate SHA-256 for a local file."""

    digest = hashlib.sha256()

    with path.open("rb") as f:
        while True:
            chunk = f.read(CHUNK_SIZE)

            if not chunk:
                break

            digest.update(chunk)

    return digest.hexdigest()


def download_bytes(url: str) -> bytes:
    """Download a small text resource such as CHECKSUM."""

    request = Request(
        url,
        headers={
            "User-Agent": "Experiment-004-Research-Downloader/1.0"
        },
    )

    last_error = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with urlopen(
                request,
                timeout=TIMEOUT_SECONDS,
            ) as response:
                return response.read()

        except (
            HTTPError,
            URLError,
            TimeoutError,
        ) as exc:

            last_error = exc

            if attempt < MAX_RETRIES:
                print(
                    f"    Retry {attempt}/{MAX_RETRIES - 1} "
                    f"after error: {exc}"
                )

                time.sleep(RETRY_DELAY_SECONDS)

    raise RuntimeError(
        f"Failed to download {url}: {last_error}"
    )


def download_file(
    url: str,
    destination: Path,
) -> None:
    """
    Download a binary file without overwriting
    an existing file.
    """

    if destination.exists():
        raise FileExistsError(
            f"Refusing to overwrite existing file: {destination}"
        )

    request = Request(
        url,
        headers={
            "User-Agent": "Experiment-004-Research-Downloader/1.0"
        },
    )

    last_error = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with urlopen(
                request,
                timeout=TIMEOUT_SECONDS,
            ) as response:

                with destination.open("wb") as output:

                    while True:
                        chunk = response.read(CHUNK_SIZE)

                        if not chunk:
                            break

                        output.write(chunk)

            return

        except (
            HTTPError,
            URLError,
            TimeoutError,
        ) as exc:

            last_error = exc

            if destination.exists():
                destination.unlink()

            if attempt < MAX_RETRIES:
                print(
                    f"    Retry {attempt}/{MAX_RETRIES - 1} "
                    f"after error: {exc}"
                )

                time.sleep(RETRY_DELAY_SECONDS)

    raise RuntimeError(
        f"Failed to download {url}: {last_error}"
    )


def parse_checksum(
    checksum_text: str,
    expected_filename: str,
) -> str:
    """
    Parse Binance CHECKSUM content.

    Expected format is generally:

        <sha256>  <filename>
    """

    lines = [
        line.strip()
        for line in checksum_text.splitlines()
        if line.strip()
    ]

    if not lines:
        raise ValueError(
            "CHECKSUM file is empty."
        )

    for line in lines:

        parts = line.split()

        if len(parts) >= 2:

            candidate_hash = parts[0].lower()
            candidate_name = parts[-1]

            if candidate_name == expected_filename:

                if len(candidate_hash) != 64:
                    raise ValueError(
                        f"Invalid SHA-256 value: "
                        f"{candidate_hash}"
                    )

                return candidate_hash

    # If Binance returns a single hash without filename.
    parts = lines[0].split()

    if len(parts) == 1 and len(parts[0]) == 64:
        return parts[0].lower()

    raise ValueError(
        f"Could not find checksum for "
        f"{expected_filename}"
    )


def verify_checksum(
    archive_path: Path,
    checksum_path: Path,
    expected_filename: str,
) -> str:
    """Verify archive SHA-256 against Binance CHECKSUM."""

    checksum_text = checksum_path.read_text(
        encoding="utf-8",
        errors="strict",
    )

    expected_hash = parse_checksum(
        checksum_text,
        expected_filename,
    )

    actual_hash = sha256_file(archive_path)

    if actual_hash != expected_hash:

        raise RuntimeError(
            "SHA-256 mismatch!\n"
            f"    Expected: {expected_hash}\n"
            f"    Actual:   {actual_hash}"
        )

    return actual_hash


# ---------------------------------------------------------------------
# Main acquisition
# ---------------------------------------------------------------------

def main() -> int:

    parser = argparse.ArgumentParser(
        description=(
            "Download and verify Binance BTCUSDT 1H "
            "monthly Spot archives for Experiment 004."
        )
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Show the acquisition plan without "
            "downloading anything."
        ),
    )

    args = parser.parse_args()

    print("=" * 72)
    print(
        "Experiment 004 — "
        "Binance BTCUSDT 1H Archive Downloader"
    )
    print("=" * 72)

    print()

    print(f"Symbol:       {SYMBOL}")
    print(f"Interval:     {INTERVAL}")

    print(
        f"Period:       "
        f"{START_YEAR:04d}-{START_MONTH:02d} → "
        f"{END_YEAR:04d}-{END_MONTH:02d}"
    )

    print(f"Archive root: {ARCHIVE_ROOT}")

    print()

    months = list(iter_months())

    print(
        f"Expected monthly archives: "
        f"{len(months)}"
    )

    print()

    # -----------------------------------------------------------------
    # Dry run
    # -----------------------------------------------------------------

    if args.dry_run:

        print("=" * 72)
        print(
            "DRY RUN — "
            "NO FILES WILL BE DOWNLOADED"
        )
        print("=" * 72)

        print()

        for index, (year, month) in enumerate(
            months,
            start=1,
        ):

            name = archive_name(
                year,
                month,
            )

            year_dir = (
                ARCHIVE_ROOT / str(year)
            )

            archive_path = (
                year_dir / name
            )

            checksum_path = (
                year_dir / f"{name}.CHECKSUM"
            )

            print(
                f"[{index:02d}/{len(months)}] "
                f"{name}"
            )

            print(
                f"    URL:      "
                f"{archive_url(year, month)}"
            )

            print(
                f"    CHECKSUM: "
                f"{checksum_url(year, month)}"
            )

            print(
                f"    DEST:     "
                f"{archive_path}"
            )

            # ---------------------------------------------------------
            # Check legacy frozen snapshot first.
            # ---------------------------------------------------------

            (
                legacy_archive_path,
                legacy_checksum_path,
            ) = legacy_paths(
                year,
                month,
            )

            if legacy_archive_path is not None:

                print(
                    "    STATUS:   "
                    "EXISTS (legacy frozen snapshot)"
                )

                print(
                    f"    SOURCE:   "
                    f"{legacy_archive_path}"
                )

                print(
                    "    CHECKSUM FILE: "
                    "EXISTS (legacy)"
                )

                print()

                continue

            # ---------------------------------------------------------
            # Check new archive structure.
            # ---------------------------------------------------------

            if archive_path.exists():

                print(
                    "    STATUS:   EXISTS"
                )

            else:

                print(
                    "    STATUS:   MISSING"
                )

            if checksum_path.exists():

                print(
                    "    CHECKSUM FILE: EXISTS"
                )

            else:

                print(
                    "    CHECKSUM FILE: MISSING"
                )

            print()

        print("=" * 72)
        print("DRY RUN COMPLETE")
        print("=" * 72)

        print(
            "No files were downloaded or modified."
        )

        return 0

    # -----------------------------------------------------------------
    # Normal acquisition
    # -----------------------------------------------------------------

    downloaded = 0
    skipped = 0
    verified = 0

    for index, (year, month) in enumerate(
        months,
        start=1,
    ):

        name = archive_name(
            year,
            month,
        )

        year_dir = (
            ARCHIVE_ROOT / str(year)
        )

        year_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        archive_path = (
            year_dir / name
        )

        checksum_path = (
            year_dir / f"{name}.CHECKSUM"
        )

        print(
            f"[{index:02d}/{len(months)}] "
            f"{name}"
        )

        # -------------------------------------------------------------
        # Existing frozen legacy snapshot
        # -------------------------------------------------------------

        (
            legacy_archive_path,
            legacy_checksum_path,
        ) = legacy_paths(
            year,
            month,
        )

        if legacy_archive_path is not None:

            print(
                "    Legacy frozen archive detected."
            )

            print(
                f"    Source: "
                f"{legacy_archive_path}"
            )

            actual_hash = verify_checksum(
                legacy_archive_path,
                legacy_checksum_path,
                name,
            )

            print(
                "    Legacy SHA-256: PASS"
            )

            print(
                f"    SHA-256: "
                f"{actual_hash}"
            )

            print(
                "    Download: SKIPPED"
            )

            print()

            verified += 1
            skipped += 1

            continue

        # -------------------------------------------------------------
        # Existing archive in the new structure
        # -------------------------------------------------------------

        if archive_path.exists():

            print(
                "    Archive already exists."
            )

            if not checksum_path.exists():

                raise RuntimeError(
                    "Archive exists but "
                    "CHECKSUM file is missing. "
                    f"Refusing to continue: "
                    f"{archive_path}"
                )

            actual_hash = verify_checksum(
                archive_path,
                checksum_path,
                name,
            )

            print(
                "    Existing archive "
                "SHA-256: PASS"
            )

            print(
                f"    SHA-256: "
                f"{actual_hash}"
            )

            verified += 1
            skipped += 1

            print()

            continue

        # -------------------------------------------------------------
        # Download archive
        # -------------------------------------------------------------

        print(
            "    Downloading archive..."
        )

        download_file(
            archive_url(year, month),
            archive_path,
        )

        downloaded += 1

        print(
            "    Archive download: PASS"
        )

        # -------------------------------------------------------------
        # Download CHECKSUM
        # -------------------------------------------------------------

        print(
            "    Downloading CHECKSUM..."
        )

        checksum_bytes = download_bytes(
            checksum_url(year, month)
        )

        checksum_path.write_bytes(
            checksum_bytes
        )

        print(
            "    CHECKSUM download: PASS"
        )

        # -------------------------------------------------------------
        # Verify SHA-256
        # -------------------------------------------------------------

        print(
            "    Verifying SHA-256..."
        )

        actual_hash = verify_checksum(
            archive_path,
            checksum_path,
            name,
        )

        verified += 1

        print(
            "    SHA-256: PASS"
        )

        print(
            f"    SHA-256: "
            f"{actual_hash}"
        )

        print()

    # -----------------------------------------------------------------
    # Final summary
    # -----------------------------------------------------------------

    print("=" * 72)
    print("ACQUISITION COMPLETE")
    print("=" * 72)

    print(
        f"Expected archives : "
        f"{len(months)}"
    )

    print(
        f"Downloaded        : "
        f"{downloaded}"
    )

    print(
        f"Already present   : "
        f"{skipped}"
    )

    print(
        f"SHA-256 verified  : "
        f"{verified}"
    )

    print()

    if verified != len(months):

        print("STATUS: FAIL")

        print(
            "Not all expected archives "
            "were verified."
        )

        return 1

    print("STATUS: PASS")

    print(
        "All expected monthly archives "
        "are SHA-256 verified."
    )

    print()

    print(
        "No extraction or analysis "
        "was performed."
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
