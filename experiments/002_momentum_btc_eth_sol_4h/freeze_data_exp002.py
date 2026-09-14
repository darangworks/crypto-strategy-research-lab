"""
Experiment 002 — Data freeze for BTC / ETH / SOL 4H.

Order (per evaluator approval, 2026-09-14):
    1. RAW FETCH        Binance klines for ETH/SOL
    2. RAW INTEGRITY    spacing / dups / NaN / OHLC sanity on raw data
    3. COVERAGE         every BTC timestamp present in ETH and SOL
    4. INTERSECTION     keep only timestamps in BTC ∩ ETH ∩ SOL
    5. FINAL INTEGRITY  same checks on intersected data
    6. WRITE            CSVs + MANIFEST with exact timestamp ranges

BTC canonical from Exp 001 (yfinance) is loaded from disk, never
re-fetched. Its SHA-256 is verified before use.

If any check fails → exit non-zero, no files written.
"""
from __future__ import annotations

import hashlib
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pandas as pd  # noqa: E402
import requests  # noqa: E402


# --- paths ---------------------------------------------------------------
SRC_DATA_DIR = REPO_ROOT / "data" / "001_btc_4h"
DST_DATA_DIR = REPO_ROOT / "data" / "002_btc_eth_sol_4h"
BTC_SRC = SRC_DATA_DIR / "BTC-USD_4h.csv"

BTC_DST = DST_DATA_DIR / "BTC-USD_4h.csv"
ETH_DST = DST_DATA_DIR / "ETH-USD_4h.csv"
SOL_DST = DST_DATA_DIR / "SOL-USD_4h.csv"
MANIFEST_DST = DST_DATA_DIR / "MANIFEST.md"


# --- config --------------------------------------------------------------
EXPECTED_BTC_SHA256 = "0aaaa726e79c238b74688d58982816a4d263bb2339d9793049bd0764e1cc1296"
EXPECTED_COLUMNS = ["Open", "High", "Low", "Close", "Volume"]
INTERVAL = "4h"
BINANCE_URL = "https://api.binance.com/api/v3/klines"
KLINE_LIMIT = 1000
REQUEST_TIMEOUT = 30
RETRY_ON_HTTP_429 = 3


# --- helpers -------------------------------------------------------------
def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_btc() -> pd.DataFrame:
    if not BTC_SRC.exists():
        raise FileNotFoundError(f"BTC source not found: {BTC_SRC}")
    actual = sha256_file(BTC_SRC)
    if actual != EXPECTED_BTC_SHA256:
        raise RuntimeError(
            f"BTC source SHA-256 mismatch.\n"
            f"  expected: {EXPECTED_BTC_SHA256}\n"
            f"  actual:   {actual}"
        )
    print(f"[BTC] SHA-256 verified: {actual[:16]}...")
    df = pd.read_csv(BTC_SRC, index_col=0, parse_dates=True)
    df.index = pd.to_datetime(df.index, utc=True)
    df.index.name = "Datetime"
    print(f"[BTC] rows={len(df)}")
    print(f"[BTC] start={df.index[0]}  end={df.index[-1]}")
    return df


def _binance_get(params: dict) -> list:
    for attempt in range(RETRY_ON_HTTP_429):
        r = requests.get(BINANCE_URL, params=params, timeout=REQUEST_TIMEOUT)
        if r.status_code == 429:
            wait = 2 ** attempt
            print(f"      [rate limit] sleeping {wait}s")
            time.sleep(wait)
            continue
        r.raise_for_status()
        return r.json()
    raise RuntimeError("Binance rate limit exceeded after retries")


def fetch_binance_klines(symbol: str, start_ms: int, end_ms: int) -> list:
    all_klines: list = []
    cursor = start_ms
    call_count = 0
    while True:
        params = {
            "symbol": symbol,
            "interval": INTERVAL,
            "startTime": cursor,
            "endTime": end_ms,
            "limit": KLINE_LIMIT,
        }
        batch = _binance_get(params)
        call_count += 1
        if not batch:
            break
        all_klines.extend(batch)
        last_open = batch[-1][0]
        if len(batch) < KLINE_LIMIT or last_open >= end_ms:
            break
        cursor = last_open + 1
    print(f"[{symbol}] {call_count} API call(s), {len(all_klines)} klines received")
    return all_klines


def klines_to_df(klines: list) -> pd.DataFrame:
    rows = []
    for k in klines:
        rows.append({
            "Datetime": pd.to_datetime(int(k[0]), unit="ms", utc=True),
            "Open":     float(k[1]),
            "High":     float(k[2]),
            "Low":      float(k[3]),
            "Close":    float(k[4]),
            "Volume":   float(k[5]),
        })
    df = pd.DataFrame(rows).set_index("Datetime")
    df = df[EXPECTED_COLUMNS]
    df = df[~df.index.duplicated(keep="first")]
    df = df.sort_index()
    return df


# --- verification steps --------------------------------------------------
def verify_raw_integrity(symbol: str, df: pd.DataFrame) -> None:
    """Integrity on raw Binance data (before any intersection)."""
    if list(df.columns) != EXPECTED_COLUMNS:
        raise RuntimeError(f"[{symbol}] columns mismatch: {list(df.columns)}")

    if df.index.tz is None:
        raise RuntimeError(f"[{symbol}] index has no timezone")

    if not df.index.is_monotonic_increasing:
        raise RuntimeError(f"[{symbol}] index not monotonic increasing")

    if df.index.has_duplicates:
        raise RuntimeError(f"[{symbol}] duplicate timestamps")

    # Strict 4h spacing across ALL consecutive bars
    diffs = df.index.to_series().diff().dropna()
    bad = diffs[diffs != pd.Timedelta(hours=4)]
    if len(bad) > 0:
        raise RuntimeError(
            f"[{symbol}] RAW spacing not uniform 4H. "
            f"{len(bad)} offending gaps. First 5:\n{bad.head()}"
        )

    if df[EXPECTED_COLUMNS].isna().any().any():
        raise RuntimeError(f"[{symbol}] RAW contains NaN in OHLCV")

    o, h, l, c = df["Open"], df["High"], df["Low"], df["Close"]
    if (h < o).any() or (h < c).any() or (l > o).any() or (l > c).any():
        raise RuntimeError(f"[{symbol}] RAW OHLC sanity violations")

    print(f"[{symbol}] RAW integrity: OK  ({len(df)} rows, uniform 4H)")


def verify_coverage(symbol: str, df: pd.DataFrame,
                    btc_index: pd.DatetimeIndex) -> None:
    """Every BTC timestamp must be present in this asset."""
    missing = btc_index.difference(df.index)
    if len(missing) > 0:
        raise RuntimeError(
            f"[{symbol}] does not cover all BTC timestamps. "
            f"missing={len(missing)}. First 5:\n{list(missing[:5])}"
        )
    print(f"[{symbol}] coverage vs BTC: OK  (0 missing)")


def verify_final_integrity(symbol: str, df: pd.DataFrame,
                           common_index: pd.DatetimeIndex) -> None:
    """Final integrity on intersected data (must match common index exactly)."""
    if not df.index.equals(common_index):
        raise RuntimeError(
            f"[{symbol}] post-intersection index != common grid"
        )

    if df[EXPECTED_COLUMNS].isna().any().any():
        raise RuntimeError(f"[{symbol}] FINAL contains NaN in OHLCV")

    o, h, l, c = df["Open"], df["High"], df["Low"], df["Close"]
    if (h < o).any() or (h < c).any() or (l > o).any() or (l > c).any():
        raise RuntimeError(f"[{symbol}] FINAL OHLC sanity violations")

    print(f"[{symbol}] FINAL integrity: OK  ({len(df)} rows)")


# --- manifest ------------------------------------------------------------
def _fmt_ts(ts) -> str:
    return ts.isoformat() if hasattr(ts, "isoformat") else str(ts)


def write_manifest(btc_df, eth_df, sol_df, hashes: dict,
                   raw_eth_count: int, raw_sol_count: int,
                   excluded_count: int) -> None:
    common_first = btc_df.index[0]
    common_last = btc_df.index[-1]
    common_rows = len(btc_df)

    lines = [
        "# Data Manifest — Experiment 002",
        "",
        "- **data_status:** FROZEN",
        "- **timeframe:** 4h",
        "- **columns:** Open, High, Low, Close, Volume",
        "",
        "## Provenance",
        "",
        "| Symbol | Source | Notes |",
        "|--------|--------|-------|",
        "| BTC-USD | yfinance | canonical byte-exact copy from Exp 001 |",
        "| ETH-USD | Binance public klines API (ETHUSDT) | fetched for exact Exp 001 UTC window |",
        "| SOL-USD | Binance public klines API (SOLUSDT) | fetched for exact Exp 001 UTC window |",
        "",
        "## Raw fetch summary",
        "",
        f"- ETH-USD raw rows: {raw_eth_count}",
        f"- SOL-USD raw rows: {raw_sol_count}",
        f"- BTC canonical rows: {len(btc_df)}",
        "",
        "## Common-grid intersection",
        "",
        "Analysis universe = intersection of timestamps present in all",
        "three frozen asset series (BTC canonical ∩ ETH ∩ SOL).",
        "",
        f"- common_first_timestamp: {_fmt_ts(common_first)}",
        f"- common_last_timestamp:  {_fmt_ts(common_last)}",
        f"- common_row_count:       {common_rows}",
        f"- Binance-only timestamps excluded by construction: {excluded_count}",
        "",
        "The excluded timestamps are NOT dropped silently. They are",
        "excluded by the pre-registered common-grid intersection rule",
        "recorded in Amendment 001 of PRE_REGISTRATION.md.",
        "",
        "## Assets (final frozen)",
        "",
        "| Symbol | File | Rows | First | Last | SHA-256 |",
        "|--------|------|------|-------|------|---------|",
    ]
    for sym, df, path in [
        ("BTC-USD", btc_df, BTC_DST),
        ("ETH-USD", eth_df, ETH_DST),
        ("SOL-USD", sol_df, SOL_DST),
    ]:
        lines.append(
            f"| {sym} | {path.name} | {len(df)} | "
            f"{_fmt_ts(df.index[0])} | {_fmt_ts(df.index[-1])} | `{hashes[sym]}` |"
        )

    lines += [
        "",
        f"- **retrieved_at:** {datetime.now(timezone.utc).isoformat()}",
        "",
        "> FROZEN canonical research snapshot for Experiment 002.",
        "> Reproducibility relies on these CSVs, not on re-downloading.",
        "> All three assets share the exact same timestamp grid.",
    ]
    MANIFEST_DST.write_text("\n".join(lines), encoding="utf-8")
    print(f"[manifest] wrote {MANIFEST_DST}")


# --- main ----------------------------------------------------------------
def main() -> int:
    print("=" * 68)
    print("EXPERIMENT 002 — DATA FREEZE (revision 2)")
    print("=" * 68)

    # 1. Load BTC canonical
    print("\n[1] Load BTC canonical (Exp 001 frozen)")
    btc_df = load_btc()
    btc_start_ms = int(btc_df.index[0].timestamp() * 1000)
    btc_end_ms = int(btc_df.index[-1].timestamp() * 1000)

    # 2. Fetch RAW Binance
    print("\n[2] Fetch RAW Binance")
    eth_raw = klines_to_df(fetch_binance_klines("ETHUSDT", btc_start_ms, btc_end_ms))
    sol_raw = klines_to_df(fetch_binance_klines("SOLUSDT", btc_start_ms, btc_end_ms))
    print(f"[ETH-USD] raw rows={len(eth_raw)}  "
          f"{eth_raw.index[0]} → {eth_raw.index[-1]}")
    print(f"[SOL-USD] raw rows={len(sol_raw)}  "
          f"{sol_raw.index[0]} → {sol_raw.index[-1]}")

    # 3. RAW integrity
    print("\n[3] RAW integrity on Binance data")
    verify_raw_integrity("ETH-USD", eth_raw)
    verify_raw_integrity("SOL-USD", sol_raw)

    # 4. Coverage vs BTC canonical
    print("\n[4] Coverage vs BTC canonical")
    verify_coverage("ETH-USD", eth_raw, btc_df.index)
    verify_coverage("SOL-USD", sol_raw, btc_df.index)

    # 5. Intersection
    print("\n[5] Intersection to common timestamp grid")
    common_index = (
        btc_df.index
        .intersection(eth_raw.index)
        .intersection(sol_raw.index)
    )
    print(f"[common] rows={len(common_index)}")
    print(f"[common] first={common_index[0]}  last={common_index[-1]}")

    excluded_eth = len(eth_raw.index.difference(btc_df.index))
    excluded_sol = len(sol_raw.index.difference(btc_df.index))
    print(f"[common] Binance-only excluded: "
          f"ETH={excluded_eth}  SOL={excluded_sol}")
    if excluded_eth != excluded_sol:
        raise RuntimeError(
            f"ETH and SOL Binance-only counts differ: "
            f"ETH={excluded_eth}  SOL={excluded_sol}"
        )

    btc_final = btc_df.loc[common_index]
    eth_final = eth_raw.loc[common_index]
    sol_final = sol_raw.loc[common_index]

    # 6. Final integrity
    print("\n[6] FINAL integrity on intersected data")
    verify_final_integrity("BTC-USD", btc_final, common_index)
    verify_final_integrity("ETH-USD", eth_final, common_index)
    verify_final_integrity("SOL-USD", sol_final, common_index)

    # 7. Write files
    print("\n[7] Write frozen CSVs")
    DST_DATA_DIR.mkdir(parents=True, exist_ok=True)

    # BTC: byte-exact copy of the canonical file (no rewrite)
    BTC_DST.write_bytes(BTC_SRC.read_bytes())
    print(f"[BTC] byte-exact copy -> {BTC_DST}")

    eth_final.to_csv(ETH_DST, index=True, index_label="Datetime")
    sol_final.to_csv(SOL_DST, index=True, index_label="Datetime")
    print(f"[ETH] wrote {ETH_DST}  ({len(eth_final)} rows)")
    print(f"[SOL] wrote {SOL_DST}  ({len(sol_final)} rows)")

    # 8. Hashes
    hashes = {
        "BTC-USD": sha256_file(BTC_DST),
        "ETH-USD": sha256_file(ETH_DST),
        "SOL-USD": sha256_file(SOL_DST),
    }
    if hashes["BTC-USD"] != EXPECTED_BTC_SHA256:
        raise RuntimeError("[BTC] copied file hash mismatch")

    # 9. Manifest
    print("\n[8] Write MANIFEST")
    write_manifest(
        btc_final, eth_final, sol_final, hashes,
        raw_eth_count=len(eth_raw),
        raw_sol_count=len(sol_raw),
        excluded_count=excluded_eth,
    )

    # 10. Summary
    print("\n" + "-" * 68)
    print("SUMMARY")
    print("-" * 68)
    for sym, df in [("BTC-USD", btc_final),
                    ("ETH-USD", eth_final),
                    ("SOL-USD", sol_final)]:
        print(f"  {sym}: rows={len(df):>4}  sha256={hashes[sym][:16]}...")
    print("-" * 68)
    print("Data freeze complete.")
    print("=" * 68)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())