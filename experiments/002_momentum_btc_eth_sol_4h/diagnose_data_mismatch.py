"""
Diagnostic — Binance vs BTC timestamp grid mismatch.

Reads only. Writes nothing. Fetches ETH from Binance and compares
timestamps against the canonical BTC snapshot.

Purpose: understand why Binance returns 4378 bars while BTC has 4334.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pandas as pd  # noqa: E402
import requests  # noqa: E402


BTC_SRC = REPO_ROOT / "data" / "001_btc_4h" / "BTC-USD_4h.csv"
BINANCE_URL = "https://api.binance.com/api/v3/klines"
KLINE_LIMIT = 1000
TIMEOUT = 30


def load_btc_index() -> pd.DatetimeIndex:
    df = pd.read_csv(BTC_SRC, index_col=0, parse_dates=True)
    df.index = pd.to_datetime(df.index, utc=True)
    return df.index


def fetch_binance(symbol: str, start_ms: int, end_ms: int) -> pd.DatetimeIndex:
    all_klines = []
    cursor = start_ms
    while True:
        r = requests.get(BINANCE_URL, params={
            "symbol": symbol,
            "interval": "4h",
            "startTime": cursor,
            "endTime": end_ms,
            "limit": KLINE_LIMIT,
        }, timeout=TIMEOUT)
        r.raise_for_status()
        batch = r.json()
        if not batch:
            break
        all_klines.extend(batch)
        last_open = batch[-1][0]
        if len(batch) < KLINE_LIMIT or last_open >= end_ms:
            break
        cursor = last_open + 1
        time.sleep(0.1)
    ts = pd.to_datetime([int(k[0]) for k in all_klines], unit="ms", utc=True)
    return pd.DatetimeIndex(ts).drop_duplicates().sort_values()


def diff_summary(name: str, idx: pd.DatetimeIndex) -> None:
    print(f"\n[{name}] rows={len(idx)}  {idx[0]} → {idx[-1]}")
    diffs = pd.Series(idx).diff().dropna()
    counts = diffs.value_counts().sort_index()
    print(f"  spacing distribution:")
    for delta, count in counts.items():
        print(f"    {delta}  × {count}")


def main() -> int:
    print("=" * 68)
    print("DIAGNOSTIC — BTC vs Binance timestamp mismatch")
    print("=" * 68)

    btc_idx = load_btc_index()
    print(f"[BTC] {len(btc_idx)} rows  {btc_idx[0]} → {btc_idx[-1]}")

    btc_start_ms = int(btc_idx[0].timestamp() * 1000)
    btc_end_ms = int(btc_idx[-1].timestamp() * 1000)

    eth_idx = fetch_binance("ETHUSDT", btc_start_ms, btc_end_ms)
    print(f"[ETH] {len(eth_idx)} rows  {eth_idx[0]} → {eth_idx[-1]}")
    sol_idx = fetch_binance("SOLUSDT", btc_start_ms, btc_end_ms)
    print(f"[SOL] {len(sol_idx)} rows  {sol_idx[0]} → {sol_idx[-1]}")

    diff_summary("BTC", btc_idx)
    diff_summary("ETH (raw Binance)", eth_idx)
    diff_summary("SOL (raw Binance)", sol_idx)

    # Which timestamps are Binance-only
    binance_only = eth_idx.difference(btc_idx)
    btc_only = btc_idx.difference(eth_idx)

    print(f"\n[Binance-only] {len(binance_only)} timestamps")
    for t in binance_only[:50]:
        print(f"  {t}")

    print(f"\n[BTC-only] {len(btc_only)} timestamps")
    for t in btc_only[:50]:
        print(f"  {t}")

    # BTC gaps around large jumps
    print("\n[BTC context around large gaps]")
    btc_diffs = pd.Series(btc_idx).diff()
    big = btc_diffs[btc_diffs > pd.Timedelta(hours=4)]
    if len(big) == 0:
        print("  (none)")
    else:
        for t, d in big.items():
            print(f"  at {btc_idx[t]}: gap = {d}")

    # ETH raw gaps
    print("\n[ETH raw context around large gaps]")
    eth_diffs = pd.Series(eth_idx).diff()
    big_eth = eth_diffs[eth_diffs > pd.Timedelta(hours=4)]
    if len(big_eth) == 0:
        print("  (none)")
    else:
        for t, d in big_eth.items():
            print(f"  at {eth_idx[t]}: gap = {d}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())