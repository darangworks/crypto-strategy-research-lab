"""
B1 — Multivariate stationary block bootstrap null.

1000 simulated 3-asset panels, preserving cross-asset correlation
and short-range temporal dependence. Run the same cross-sectional
momentum strategy on each. Report distribution of net_pnl, sharpe,
trade_count.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import numpy as np
import pandas as pd

from engine.backtest import BacktestConfig
from validation.leakage.cross_sectional import (
    _log_return_matrix,
    estimate_block_length_per_asset,
    multivariate_block_bootstrap,
    rebuild_prices_from_log_returns,
    run_bootstrap_backtests,
    summarize,
)


DATA_DIR = REPO_ROOT / "data" / "002_btc_eth_sol_4h"
ASSETS = ["BTC-USD", "ETH-USD", "SOL-USD"]
TIEBREAK = ASSETS
LOOKBACK = 6
N_ITER = 1000
BASE_SEED = 20260913

CONFIG = BacktestConfig(
    initial_capital=100_000.0,
    position_pct=1.0,
    commission=0.0005,
    slippage=0.0002,
)

OUT_DIR = REPO_ROOT / "experiments" / "002_momentum_btc_eth_sol_4h" / "leakage_artifacts"
OUT_JSON = OUT_DIR / "b1_multivariate_null_summary.json"


def load_panel() -> dict:
    panel = {}
    for sym in ASSETS:
        path = DATA_DIR / f"{sym}_4h.csv"
        df = pd.read_csv(path, index_col=0, parse_dates=True)
        df.index = pd.to_datetime(df.index, utc=True)
        panel[sym] = df
    return panel


def main() -> int:
    print("=" * 78)
    print("B1 — MULTIVARIATE BLOCK BOOTSTRAP NULL (Exp 002)")
    print("=" * 78)

    panel = load_panel()
    index = panel[ASSETS[0]].index
    rows = len(index)
    print(f"Source panel rows: {rows}")
    print(f"Window: {index[0]} → {index[-1]}")

    log_returns = _log_return_matrix(panel, ASSETS)
    print(f"Log-return matrix shape: {log_returns.shape}")

    bl = estimate_block_length_per_asset(log_returns)
    print(f"Block length estimation:")
    print(f"  per-asset lengths: {bl['lengths']}")
    print(f"  used (max):        {bl['used']}")
    print(f"  threshold:         {bl['threshold']:.6f}")

    print(f"\nBootstrapping {N_ITER} paths (seed {BASE_SEED} + i)...")
    paths_log_ret = multivariate_block_bootstrap(
        log_returns, n_iter=N_ITER, block_length=bl["used"], base_seed=BASE_SEED
    )
    print(f"  bootstrap returns shape: {paths_log_ret.shape}")

    # Rebuild prices
    s0 = np.array([float(panel[a]["Close"].iloc[0]) for a in ASSETS])
    print(f"  initial prices: {s0}")
    T = rows
    paths_prices = np.empty((N_ITER, T, len(ASSETS)), dtype=float)
    for i in range(N_ITER):
        paths_prices[i] = rebuild_prices_from_log_returns(s0, paths_log_ret[i])
    print(f"  bootstrap prices shape: {paths_prices.shape}")

    print(f"\nRunning cross-sectional strategy on {N_ITER} paths...")
    results = run_bootstrap_backtests(
        paths_prices=paths_prices,
        index=index,
        assets=ASSETS,
        config=CONFIG,
        tiebreak_order=TIEBREAK,
        lookback=LOOKBACK,
    )

    summary = summarize(results)
    summary["block_length"] = bl

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(summary, indent=2))
    print(f"\nWrote {OUT_JSON}")

    print("\n" + "-" * 78)
    print("B1 NULL DISTRIBUTION")
    print("-" * 78)
    s = summary["sharpe"]
    p = summary["net_pnl"]
    t = summary["trade_count"]
    print(f"  Sharpe:      median={s['median']:+.4f}  "
          f"p2.5={s['p2_5']:+.4f}  p97.5={s['p97_5']:+.4f}  "
          f"frac>0={s['frac_positive']:.3f}")
    print(f"  net_pnl:     median={p['median']:+.2f}  "
          f"p2.5={p['p2_5']:+.2f}  p97.5={p['p97_5']:+.2f}  "
          f"frac>0={p['frac_positive']:.3f}")
    print(f"  trade_count: median={t['median']:.0f}  "
          f"p2.5={t['p2_5']:.0f}  p97.5={t['p97_5']:.0f}")
    print("-" * 78)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())