"""
Unit tests for strategies/rsi_mean_reversion/strategy.py.

These tests validate STRATEGY CORRECTNESS — not profitability.
"""

import numpy as np
import pandas as pd
import pytest

from strategies.rsi_mean_reversion.strategy import RSIMeanReversion


def make_df(closes):
    n = len(closes)
    idx = pd.date_range(start="2024-01-01", periods=n, freq="4h", tz="UTC")
    return pd.DataFrame({
        "Open": closes,
        "High": closes,
        "Low": closes,
        "Close": closes,
        "Volume": [1000.0] * n,
    }, index=idx)


def test_hypothesis_is_documented():
    s = RSIMeanReversion()
    assert "mean reversion" in s.hypothesis().lower()


def test_rsi_column_is_added():
    closes = list(range(100, 150))
    df = make_df(closes)
    s = RSIMeanReversion()
    out = s.compute_features(df)
    assert "RSI" in out.columns


def test_no_signal_in_boring_market():
    closes = [100.0] * 100
    df = make_df(closes)
    s = RSIMeanReversion()
    df = s.compute_features(df)
    target = s.target_position(df)
    assert (target == 0.0).all()


def test_entry_requires_strict_cross_below_30():
    # Phase 1: rise (RSI goes above 30)
    closes = [100.0]
    for _ in range(20):
        closes.append(closes[-1] * 1.02)

    # Phase 2: sharp decline (RSI crosses below 30)
    for _ in range(30):
        closes.append(closes[-1] * 0.97)

    df = make_df(closes)
    s = RSIMeanReversion()
    df = s.compute_features(df)
    target = s.target_position(df)

    assert (target == 1.0).any(), "Strategy never entered long"


def test_target_is_binary():
    rng = np.random.default_rng(42)
    rets = rng.normal(0, 0.02, 300)
    closes = [100.0]
    for r in rets:
        closes.append(closes[-1] * (1 + r))

    df = make_df(closes)
    s = RSIMeanReversion()
    df = s.compute_features(df)
    target = s.target_position(df)

    unique = set(target.unique())
    assert unique.issubset({0.0, 1.0})


def test_exit_requires_strict_cross_above_50():
    # Phase 1: rise (RSI > 30)
    closes = [100.0]
    for _ in range(20):
        closes.append(closes[-1] * 1.02)

    # Phase 2: sharp decline (RSI crosses below 30 → entry)
    for _ in range(30):
        closes.append(closes[-1] * 0.97)

    # Phase 3: strong recovery (RSI crosses above 50 → exit)
    for _ in range(30):
        closes.append(closes[-1] * 1.03)

    # Phase 4: hold
    for _ in range(10):
        closes.append(closes[-1])

    df = make_df(closes)
    s = RSIMeanReversion()
    df = s.compute_features(df)
    target = s.target_position(df)

    assert (target == 1.0).any(), "Strategy never entered long"

    first_entry_idx = target[target == 1.0].index[0]
    after_entry = target.loc[first_entry_idx:]
    assert (after_entry == 0.0).any(), "Strategy never exited after entry"

    assert target.iloc[-1] == 0.0, "Strategy did not exit by end of test"
