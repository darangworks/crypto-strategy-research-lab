"""B1 — Random-walk null distribution.

Bootstrap-resample log returns from frozen BTC-USD 4H data.
Defaults: N=1000 paths, 4334 bars, base_seed=20260913.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# --- add repo root to sys.path BEFORE importing engine/strategies ---
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import numpy as np
import pandas as pd

from engine.backtest import BacktestConfig, run_backtest
from engine.data_loader import load_frozen
from strategies.rsi_mean_reversion.strategy import RSIMeanReversion


N_PATHS = 1000
N_BARS = 4334
BASE_SEED = 20260913
FREQ = "4h"


def generate_null_paths(
    source_df: pd.DataFrame,
    n_paths: int = N_PATHS,
    n_bars: int = N_BARS,
    base_seed: int = BASE_SEED,
) -> list:
    """Bootstrap-resample log returns; return list of price arrays."""
    close = source_df["Close"].astype(float)
    log_returns = np.log(close / close.shift(1)).dropna().values
    s0 = float(close.iloc[0])

    paths = []
    for i in range(n_paths):
        rng = np.random.default_rng(base_seed + i)
        sampled = rng.choice(log_returns, size=n_bars - 1, replace=True)
        prices = s0 * np.exp(np.concatenate([[0.0], np.cumsum(sampled)]))
        paths.append(prices)
    return paths


def make_ohlcv_df(prices: np.ndarray, start: pd.Timestamp) -> pd.DataFrame:
    idx = pd.date_range(start=start, periods=len(prices), freq=FREQ, tz="UTC")
    return pd.DataFrame(
        {
            "Open": prices,
            "High": prices,
            "Low": prices,
            "Close": prices,
            "Volume": 0.0,
        },
        index=idx,
    )


def run_null_backtests(
    paths: list,
    start: pd.Timestamp,
    config: BacktestConfig | None = None,
) -> list:
    if config is None:
        config = BacktestConfig()
    strategy = RSIMeanReversion(14, 30.0, 50.0)

    results = []
    for prices in paths:
        df = make_ohlcv_df(prices, start)
        r = run_backtest(df, strategy, config)
        results.append(
            {
                "net_pnl": float(r.net_pnl),
                "sharpe": float(r.sharpe),
                "profit_factor": float(r.profit_factor),
                "win_rate": float(r.win_rate),
                "max_drawdown": float(r.max_drawdown),
                "trade_count": int(r.trade_count),
            }
        )
    return results


def summarize(results: list) -> dict:
    if not results:
        return {}

    def _arr(k):
        return np.array([r[k] for r in results], dtype=float)

    def _stats(a):
        return {
            "mean": float(np.mean(a)),
            "median": float(np.median(a)),
            "p2_5": float(np.percentile(a, 2.5)),
            "p97_5": float(np.percentile(a, 97.5)),
            "min": float(np.min(a)),
            "max": float(np.max(a)),
        }

    sharpe = _arr("sharpe")
    net_pnl = _arr("net_pnl")
    trades = _arr("trade_count")

    return {
        "n_paths": len(results),
        "sharpe": {**_stats(sharpe), "frac_positive": float(np.mean(sharpe > 0))},
        "net_pnl": {**_stats(net_pnl), "frac_positive": float(np.mean(net_pnl > 0))},
        "trade_count": _stats(trades),
    }


if __name__ == "__main__":
    DATA_FILE = REPO_ROOT / "data" / "001_btc_4h" / "BTC-USD_4h.csv"
    OUT_FILE = (
        REPO_ROOT
        / "experiments"
        / "001_rsi_btc_4h"
        / "leakage_artifacts"
        / "random_walk_summary.json"
    )
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    df = load_frozen(DATA_FILE)
    print(f"source rows = {len(df)}")
    print(f"generating {N_PATHS} null paths...")
    paths = generate_null_paths(df)
    print("running backtests...")
    results = run_null_backtests(paths, start=df.index[0])
    summary = summarize(results)
    OUT_FILE.write_text(json.dumps(summary, indent=2))
    print(f"wrote {OUT_FILE}")
    print(json.dumps(summary, indent=2))
