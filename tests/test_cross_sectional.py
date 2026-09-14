"""Specification and causality tests for cross-sectional momentum."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from engine.backtest import BacktestConfig
from engine.cross_sectional_backtest import run_cross_sectional_backtest
from strategies.cross_sectional_momentum.strategy import CrossSectionalMomentum


TIEBREAK = ["BTC-USD", "ETH-USD", "SOL-USD"]


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------
def _make_panel(closes_by_asset: dict, freq: str = "4h") -> dict:
    """Build a panel. Insertion order of dict keys is preserved."""
    n = len(next(iter(closes_by_asset.values())))
    idx = pd.date_range("2024-01-01", periods=n, freq=freq, tz="UTC")
    panel = {}
    for name, closes in closes_by_asset.items():
        closes = np.asarray(closes, dtype=float)
        panel[name] = pd.DataFrame(
            {
                "Open":   closes,
                "High":   closes,
                "Low":    closes,
                "Close":  closes,
                "Volume": 0.0,
            },
            index=idx,
        )
    return panel


# ----------------------------------------------------------------------
# Strategy specification tests
# ----------------------------------------------------------------------
def test_momentum_matches_manual_log_ratio():
    closes = [100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 110.0]
    panel = _make_panel({"BTC-USD": closes, "ETH-USD": closes, "SOL-USD": closes})
    s = CrossSectionalMomentum(lookback=6, tiebreak_order=TIEBREAK)
    mom = s.momentum(panel)
    expected = np.log(110.0 / 100.0)
    assert mom["BTC-USD"].iloc[6] == pytest.approx(expected)


def test_warmup_returns_nan_targets():
    closes = list(range(100, 110))
    panel = _make_panel({"BTC-USD": closes, "ETH-USD": closes, "SOL-USD": closes})
    s = CrossSectionalMomentum(lookback=6, tiebreak_order=TIEBREAK)
    targets = s.target_asset(panel)
    for i in range(6):
        assert pd.isna(targets.iloc[i])
    assert targets.iloc[6] in {"BTC-USD", "ETH-USD", "SOL-USD"}


def test_highest_momentum_wins():
    n = 10
    btc = [100.0] * n
    eth = [100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 110.0, 115.0, 120.0, 125.0]
    sol = [100.0] * n
    panel = _make_panel({"BTC-USD": btc, "ETH-USD": eth, "SOL-USD": sol})
    s = CrossSectionalMomentum(lookback=6, tiebreak_order=TIEBREAK)
    targets = s.target_asset(panel)
    assert targets.iloc[6] == "ETH-USD"
    assert targets.iloc[8] == "ETH-USD"


def test_tiebreak_prefers_btc():
    closes = [100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0]
    panel = _make_panel({"BTC-USD": closes, "ETH-USD": closes, "SOL-USD": closes})
    s = CrossSectionalMomentum(lookback=6, tiebreak_order=TIEBREAK)
    targets = s.target_asset(panel)
    assert targets.iloc[6] == "BTC-USD"
    assert targets.iloc[7] == "BTC-USD"


def test_tiebreak_prefers_eth_when_btc_not_tied():
    n = 8
    btc = [100.0] * n
    eth = [100.0] * 6 + [110.0, 110.0]
    sol = [100.0] * 6 + [110.0, 110.0]
    panel = _make_panel({"BTC-USD": btc, "ETH-USD": eth, "SOL-USD": sol})
    s = CrossSectionalMomentum(lookback=6, tiebreak_order=TIEBREAK)
    targets = s.target_asset(panel)
    assert targets.iloc[6] == "ETH-USD"
    assert targets.iloc[7] == "ETH-USD"


def test_tiebreak_independent_of_column_order():
    """Column insertion order MUST NOT affect the tiebreak result."""
    closes = [100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0]

    permutations = [
        ["BTC-USD", "ETH-USD", "SOL-USD"],
        ["ETH-USD", "SOL-USD", "BTC-USD"],
        ["SOL-USD", "BTC-USD", "ETH-USD"],
        ["ETH-USD", "BTC-USD", "SOL-USD"],
        ["SOL-USD", "ETH-USD", "BTC-USD"],
    ]

    for perm in permutations:
        closes_by_asset = {name: list(closes) for name in perm}
        panel = _make_panel(closes_by_asset)
        s = CrossSectionalMomentum(lookback=6, tiebreak_order=TIEBREAK)
        targets = s.target_asset(panel)
        # All momentums are tied at bar 6, 7 → tiebreak order must win
        assert targets.iloc[6] == "BTC-USD", f"failed for perm {perm}"
        assert targets.iloc[7] == "BTC-USD", f"failed for perm {perm}"


def test_tiebreak_requires_explicit_order():
    with pytest.raises(ValueError, match="tiebreak_order"):
        CrossSectionalMomentum(lookback=6, tiebreak_order=None)

    with pytest.raises(ValueError, match="tiebreak_order"):
        CrossSectionalMomentum(lookback=6, tiebreak_order=[])


def test_tiebreak_ignores_assets_not_in_order():
    """Assets absent from tiebreak_order are appended alphabetically."""
    closes = [100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0]
    panel = _make_panel({
        "BTC-USD": closes,
        "ETH-USD": closes,
        "SOL-USD": closes,
        "XRP-USD": closes,  # not in tiebreak_order
    })
    s = CrossSectionalMomentum(lookback=6, tiebreak_order=TIEBREAK)
    targets = s.target_asset(panel)
    # All tied → BTC still wins (first in tiebreak_order)
    assert targets.iloc[6] == "BTC-USD"


# ----------------------------------------------------------------------
# Causality tests
# ----------------------------------------------------------------------
def test_future_perturbation_does_not_change_past_targets():
    n = 20
    rng = np.random.default_rng(20260913)
    closes = {
        "BTC-USD": 100.0 + np.cumsum(rng.normal(0, 1, n)),
        "ETH-USD": 100.0 + np.cumsum(rng.normal(0, 1, n)),
        "SOL-USD": 100.0 + np.cumsum(rng.normal(0, 1, n)),
    }
    panel = _make_panel(closes)
    s = CrossSectionalMomentum(lookback=6, tiebreak_order=TIEBREAK)
    targets_a = s.target_asset(panel)

    panel_b = {k: v.copy() for k, v in panel.items()}
    for k in panel_b:
        panel_b[k].loc[panel_b[k].index[12:], "Close"] *= 3.0
    targets_b = s.target_asset(panel_b)

    for i in range(12):
        a = targets_a.iloc[i]
        b = targets_b.iloc[i]
        assert (pd.isna(a) and pd.isna(b)) or (a == b), f"mismatch at i={i}"


def test_asset_specific_future_perturbation():
    n = 20
    rng = np.random.default_rng(7)
    closes = {
        "BTC-USD": 100.0 + np.cumsum(rng.normal(0, 1, n)),
        "ETH-USD": 100.0 + np.cumsum(rng.normal(0, 1, n)),
        "SOL-USD": 100.0 + np.cumsum(rng.normal(0, 1, n)),
    }
    panel_a = _make_panel(closes)
    panel_b = {k: v.copy() for k, v in panel_a.items()}
    panel_b["ETH-USD"].loc[panel_b["ETH-USD"].index[12:], "Close"] *= 5.0

    s = CrossSectionalMomentum(lookback=6, tiebreak_order=TIEBREAK)
    mom_a = s.momentum(panel_a)
    mom_b = s.momentum(panel_b)

    for i in range(12):
        a = mom_a["ETH-USD"].iloc[i]
        b = mom_b["ETH-USD"].iloc[i]
        assert (pd.isna(a) and pd.isna(b)) or a == pytest.approx(b)


# ----------------------------------------------------------------------
# Runner tests
# ----------------------------------------------------------------------
def _stub_strategy(targets: list, index: pd.DatetimeIndex):
    class _Stub:
        def target_asset(self, panel):
            return pd.Series(targets, index=index, dtype=object)
    return _Stub()


def test_runner_no_trades_when_target_always_nan():
    closes = [100.0] * 10
    panel = _make_panel({"BTC-USD": closes, "ETH-USD": closes, "SOL-USD": closes})
    index = panel["BTC-USD"].index
    stub = _stub_strategy([np.nan] * len(index), index)
    cfg = BacktestConfig(initial_capital=100_000.0, position_pct=1.0,
                         commission=0.0005, slippage=0.0002)
    r = run_cross_sectional_backtest(panel, stub, cfg)
    assert r.trade_count == 0
    assert r.net_pnl == pytest.approx(0.0)
    assert r.equity_curve.iloc[-1] == pytest.approx(100_000.0)


def test_runner_single_hold_no_transition():
    n = 10
    closes = list(range(100, 100 + n))
    panel = _make_panel({"BTC-USD": closes, "ETH-USD": closes, "SOL-USD": closes})
    index = panel["BTC-USD"].index
    targets = ["BTC-USD"] * n
    stub = _stub_strategy(targets, index)
    cfg = BacktestConfig(initial_capital=100_000.0, position_pct=1.0,
                         commission=0.0, slippage=0.0)
    r = run_cross_sectional_backtest(panel, stub, cfg)
    expected = (100_000.0 / 101.0) * 109.0
    assert r.equity_curve.iloc[-1] == pytest.approx(expected, rel=1e-9)
    assert r.trade_count == 1


def test_runner_transition_charges_cost():
    n = 10
    closes = [100.0] * n
    panel = _make_panel({"BTC-USD": closes, "ETH-USD": closes, "SOL-USD": closes})
    index = panel["BTC-USD"].index
    targets = ["BTC-USD"] * 5 + ["ETH-USD"] * 5
    stub = _stub_strategy(targets, index)
    cfg = BacktestConfig(initial_capital=100_000.0, position_pct=1.0,
                         commission=0.001, slippage=0.001)
    r = run_cross_sectional_backtest(panel, stub, cfg)
    assert r.equity_curve.iloc[-1] < 100_000.0
    assert r.trade_count == 2


def test_runner_100pct_invested_no_cash_left():
    n = 10
    closes = [100.0] * n
    panel = _make_panel({"BTC-USD": closes, "ETH-USD": closes, "SOL-USD": closes})
    index = panel["BTC-USD"].index
    targets = ["BTC-USD"] * n
    stub = _stub_strategy(targets, index)
    cfg = BacktestConfig(initial_capital=100_000.0, position_pct=1.0,
                         commission=0.0, slippage=0.0)
    r = run_cross_sectional_backtest(panel, stub, cfg)
    assert r.equity_curve.iloc[1] == pytest.approx(100_000.0)


def test_runner_last_bar_liquidation_with_costs():
    n = 10
    closes = [100.0] * n
    panel = _make_panel({"BTC-USD": closes, "ETH-USD": closes, "SOL-USD": closes})
    index = panel["BTC-USD"].index
    targets = ["BTC-USD"] * n
    stub = _stub_strategy(targets, index)
    cfg = BacktestConfig(initial_capital=100_000.0, position_pct=1.0,
                         commission=0.001, slippage=0.0)
    r = run_cross_sectional_backtest(panel, stub, cfg)
    assert 99_700.0 < r.equity_curve.iloc[-1] < 100_000.0