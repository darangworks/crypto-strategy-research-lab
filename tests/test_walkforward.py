"""Tests for Exp 002 walk-forward split and predictive metric."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from engine.backtest import BacktestConfig
from engine.cross_sectional_backtest import run_cross_sectional_backtest
from strategies.cross_sectional_momentum.strategy import CrossSectionalMomentum


DATA_DIR = REPO_ROOT / "data" / "002_btc_eth_sol_4h"
ASSETS = ["BTC-USD", "ETH-USD", "SOL-USD"]
TIEBREAK = list(ASSETS)
SPLIT_INDEX = 2167
WARMUP_BARS = 6
LOOKBACK = 6

CONFIG = BacktestConfig(
    initial_capital=100_000.0, position_pct=1.0,
    commission=0.0005, slippage=0.0002,
)


def _load_panel() -> dict:
    panel = {}
    for sym in ASSETS:
        df = pd.read_csv(DATA_DIR / f"{sym}_4h.csv", index_col=0, parse_dates=True)
        df.index = pd.to_datetime(df.index, utc=True)
        panel[sym] = df
    return panel


# -----------------------------------------------------------------------
def test_split_index_matches_exp001():
    assert SPLIT_INDEX == 2167


def test_is_oos_lengths_equal():
    panel = _load_panel()
    n = len(panel[ASSETS[0]])
    assert n == 4334
    is_len = SPLIT_INDEX
    oos_len = n - SPLIT_INDEX
    assert is_len == 2167
    assert oos_len == 2167
    assert is_len == oos_len


def test_is_warmup_targets_are_nan():
    panel = _load_panel()
    panel_is = {a: panel[a].iloc[:SPLIT_INDEX].copy() for a in ASSETS}
    s = CrossSectionalMomentum(lookback=LOOKBACK, tiebreak_order=TIEBREAK)
    targets = s.target_asset(panel_is)
    # First 6 must be NaN
    for i in range(WARMUP_BARS):
        assert pd.isna(targets.iloc[i]), f"bar {i} should be NaN"
    # Bar 6 onwards non-NaN
    assert not pd.isna(targets.iloc[WARMUP_BARS])


def test_oos_first_target_is_valid_via_warmed_panel():
    panel = _load_panel()
    warm_start = SPLIT_INDEX - WARMUP_BARS
    panel_warm = {a: panel[a].iloc[warm_start:].copy() for a in ASSETS}
    s = CrossSectionalMomentum(lookback=LOOKBACK, tiebreak_order=TIEBREAK)
    warm_targets = s.target_asset(panel_warm)
    oos_targets = warm_targets.iloc[WARMUP_BARS:]
    # No NaN in OOS targets
    assert oos_targets.notna().all(), (
        f"OOS targets have NaN: {oos_targets[oos_targets.isna()].index.tolist()}"
    )
    # First OOS target is at bar SPLIT_INDEX
    assert oos_targets.index[0] == panel[ASSETS[0]].index[SPLIT_INDEX]


def test_force_flat_isolation_at_split():
    """IS ends flat, OOS starts flat: two independent backtests."""
    panel = _load_panel()
    panel_is = {a: panel[a].iloc[:SPLIT_INDEX].copy() for a in ASSETS}
    panel_oos = {a: panel[a].iloc[SPLIT_INDEX:].copy() for a in ASSETS}

    strat_is = CrossSectionalMomentum(lookback=LOOKBACK, tiebreak_order=TIEBREAK)
    r_is = run_cross_sectional_backtest(panel_is, strat_is, CONFIG)

    warm_start = SPLIT_INDEX - WARMUP_BARS
    panel_warm = {a: panel[a].iloc[warm_start:].copy() for a in ASSETS}
    strat_warm = CrossSectionalMomentum(lookback=LOOKBACK, tiebreak_order=TIEBREAK)
    warm_targets = strat_warm.target_asset(panel_warm)
    oos_targets = warm_targets.iloc[WARMUP_BARS:]

    class _Pre:
        def __init__(self, t): self._t = t
        def target_asset(self, p):
            idx = next(iter(p.values())).index
            return self._t.reindex(idx)

    r_oos = run_cross_sectional_backtest(panel_oos, _Pre(oos_targets), CONFIG)

    # OOS first bar equity should be initial capital (flat, no position)
    assert r_oos.equity_curve.iloc[0] == pytest.approx(CONFIG.initial_capital)
    # Both backtests share the same initial capital (independent)
    assert r_is.equity_curve.iloc[0] == pytest.approx(CONFIG.initial_capital)
    # OOS lengths match panel_oos
    assert len(r_oos.equity_curve) == len(panel_oos[ASSETS[0]])


def test_predictive_metric_causal_selection():
    """Perturbing close[t+1] must NOT change top/bottom at bar t."""
    panel = _load_panel()
    s = CrossSectionalMomentum(lookback=LOOKBACK, tiebreak_order=TIEBREAK)
    mom_orig = s.momentum(panel)

    # Perturb close at a future bar (say bar 100)
    perturb_idx = 100
    panel_pert = {a: panel[a].copy() for a in ASSETS}
    for a in ASSETS:
        panel_pert[a].loc[panel_pert[a].index[perturb_idx], "Close"] *= 5.0

    mom_pert = s.momentum(panel_pert)

    # Momentum at t=99 uses close[99]/close[93], unaffected by close[100]
    for t in range(6, perturb_idx):
        for a in ASSETS:
            assert np.isclose(mom_orig[a].iloc[t], mom_pert[a].iloc[t])

    # But momentum at t=100 (uses close[100]) is affected
    affected = any(
        not np.isclose(mom_orig[a].iloc[perturb_idx], mom_pert[a].iloc[perturb_idx])
        for a in ASSETS
    )
    assert affected, "momentum at bar 100 should change with perturbed close[100]"