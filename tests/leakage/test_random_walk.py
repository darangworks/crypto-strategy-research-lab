from pathlib import Path

import numpy as np
import pandas as pd

from engine.data_loader import load_frozen
from validation.leakage.random_walk_null import (
    N_BARS,
    generate_null_paths,
    make_ohlcv_df,
    run_null_backtests,
    summarize,
)

DATA_FILE = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "001_btc_4h"
    / "BTC-USD_4h.csv"
)


def test_generator_returns_n_paths():
    df = load_frozen(DATA_FILE)
    paths = generate_null_paths(df, n_paths=5)
    assert len(paths) == 5
    assert all(len(p) == N_BARS for p in paths)
    assert all(p[0] == df["Close"].iloc[0] for p in paths)
    assert all((p > 0).all() for p in paths)


def test_make_ohlcv_df_shape():
    prices = np.linspace(100.0, 110.0, 10)
    idx_start = pd.Timestamp("2024-09-14", tz="UTC")
    df = make_ohlcv_df(prices, idx_start)
    assert len(df) == 10
    assert list(df.columns) == ["Open", "High", "Low", "Close", "Volume"]
    assert df["Close"].iloc[0] == 100.0


def test_null_backtests_runs_few_paths():
    df = load_frozen(DATA_FILE)
    paths = generate_null_paths(df, n_paths=3)
    results = run_null_backtests(paths, start=df.index[0])
    assert len(results) == 3
    for r in results:
        assert np.isfinite(r["sharpe"])
        assert np.isfinite(r["net_pnl"])
        assert r["trade_count"] >= 0


def test_summary_keys():
    df = load_frozen(DATA_FILE)
    paths = generate_null_paths(df, n_paths=3)
    results = run_null_backtests(paths, start=df.index[0])
    s = summarize(results)
    assert "n_paths" in s
    assert "sharpe" in s
    assert "net_pnl" in s
    assert "frac_positive" in s["sharpe"]
    assert "frac_positive" in s["net_pnl"]
