"""
Unit tests for engine/backtest.py.

These tests validate ENGINE CORRECTNESS — not strategy profitability.
"""

import numpy as np
import pandas as pd
import pytest

from engine.backtest import BacktestConfig, run_backtest


class FixedTargetStrategy:
    """Returns a fixed target direction array (0 or +1)."""
    def __init__(self, targets):
        self._targets = targets

    def compute_features(self, df):
        return df

    def target_position(self, df):
        return pd.Series(self._targets, index=df.index, dtype=float)


def make_df(opens, closes=None):
    n = len(opens)
    if closes is None:
        closes = opens
    idx = pd.date_range(start="2024-01-01", periods=n, freq="4h", tz="UTC")
    return pd.DataFrame({
        "Open": opens,
        "High": np.maximum(opens, closes),
        "Low": np.minimum(opens, closes),
        "Close": closes,
        "Volume": [1000.0] * n,
    }, index=idx)


def test_no_signal_no_trade():
    df = make_df([100.0] * 10)
    strategy = FixedTargetStrategy([0.0] * 10)
    result = run_backtest(df, strategy)
    assert result.trade_count == 0
    assert result.net_pnl == 0.0


def test_entry_signal_fills_at_next_open():
    opens = [100.0, 100.0, 105.0, 105.0, 105.0]
    df = make_df(opens)

    targets = [0.0, 1.0, 1.0, 1.0, 0.0]
    strategy = FixedTargetStrategy(targets)

    config = BacktestConfig(
        initial_capital=100_000,
        position_pct=1.0,
        commission=0.0,
        slippage=0.0,
    )
    result = run_backtest(df, strategy, config)

    assert result.trade_count == 1
    trade = result.trades[0]
    assert trade.entry_index == 2
    assert trade.entry_price == pytest.approx(105.0)


def test_exit_signal_fills_at_next_open():
    opens = [100.0, 100.0, 100.0, 110.0, 110.0, 110.0]
    df = make_df(opens)

    targets = [0.0, 1.0, 1.0, 0.0, 0.0, 0.0]
    strategy = FixedTargetStrategy(targets)

    config = BacktestConfig(
        initial_capital=100_000,
        position_pct=1.0,
        commission=0.0,
        slippage=0.0,
    )
    result = run_backtest(df, strategy, config)

    assert result.trade_count == 1
    trade = result.trades[0]
    assert trade.entry_index == 2
    assert trade.exit_index == 4
    assert trade.exit_price == pytest.approx(110.0)


def test_no_entry_on_last_bar():
    opens = [100.0] * 5
    df = make_df(opens)

    targets = [0.0, 0.0, 0.0, 0.0, 1.0]
    strategy = FixedTargetStrategy(targets)

    result = run_backtest(df, strategy)
    assert result.trade_count == 0


def test_open_position_liquidated_at_final_close():
    opens = [100.0] * 5
    closes = [100.0, 100.0, 100.0, 100.0, 110.0]
    df = make_df(opens, closes=closes)

    targets = [0.0, 1.0, 1.0, 1.0, 1.0]
    strategy = FixedTargetStrategy(targets)

    config = BacktestConfig(
        initial_capital=100_000,
        position_pct=1.0,
        commission=0.0,
        slippage=0.0,
    )
    result = run_backtest(df, strategy, config)

    assert result.trade_count == 1
    trade = result.trades[0]
    assert trade.exit_index == 4
    assert trade.exit_price == pytest.approx(110.0)


def test_commission_reduces_net_pnl():
    opens = [100.0] * 5
    df = make_df(opens)

    targets = [0.0, 1.0, 1.0, 1.0, 0.0]
    strategy = FixedTargetStrategy(targets)

    r_no = run_backtest(df, strategy, BacktestConfig(
        initial_capital=100_000, position_pct=1.0,
        commission=0.0, slippage=0.0,
    ))
    r_yes = run_backtest(df, strategy, BacktestConfig(
        initial_capital=100_000, position_pct=1.0,
        commission=0.001, slippage=0.0,
    ))

    assert r_yes.net_pnl < r_no.net_pnl


def test_slippage_reduces_net_pnl():
    opens = [100.0] * 5
    df = make_df(opens)

    targets = [0.0, 1.0, 1.0, 1.0, 0.0]
    strategy = FixedTargetStrategy(targets)

    r_no = run_backtest(df, strategy, BacktestConfig(
        initial_capital=100_000, position_pct=1.0,
        commission=0.0, slippage=0.0,
    ))
    r_slip = run_backtest(df, strategy, BacktestConfig(
        initial_capital=100_000, position_pct=1.0,
        commission=0.0, slippage=0.001,
    ))

    assert r_slip.net_pnl < r_no.net_pnl


def test_position_pct_controls_sizing():
    opens = [100.0] * 5
    df = make_df(opens)

    targets = [0.0, 1.0, 1.0, 1.0, 0.0]
    strategy = FixedTargetStrategy(targets)

    config = BacktestConfig(
        initial_capital=100_000,
        position_pct=0.10,
        commission=0.0,
        slippage=0.0,
    )
    result = run_backtest(df, strategy, config)

    assert result.trade_count == 1
    trade = result.trades[0]
    assert trade.entry_price == pytest.approx(100.0)
    assert trade.qty == pytest.approx(100.0)


def test_returns_are_bar_to_bar_equity_pct_change():
    opens = [100.0] * 5
    df = make_df(opens)

    targets = [0.0, 0.0, 0.0, 0.0, 0.0]
    strategy = FixedTargetStrategy(targets)

    result = run_backtest(df, strategy)

    assert (result.returns == 0.0).all()
    assert len(result.returns) == len(df)