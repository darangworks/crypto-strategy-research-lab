"""
Independent WFO reconstruction audit for Exp 002.

Two independent backtests (IS, OOS) that reproduce the WFO runner's
execution, then bar-by-bar comparison against the frozen WFO CSVs.

Checks:
  1. IS equity reconstruction (bar-by-bar vs walkforward_is_equity.csv)
  2. OOS equity reconstruction (bar-by-bar vs walkforward_oos_equity.csv)
  3. Force-flat isolation at split
  4. OOS warmup: first 6 warm_targets are NaN; first OOS target valid
  5. Capital conservation for IS and OOS
  6. Trade counts and net_pnl match walkforward.json

Read-only. Writes nothing.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import numpy as np
import pandas as pd

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

EXP_DIR = REPO_ROOT / "experiments" / "002_momentum_btc_eth_sol_4h"
IS_CSV = EXP_DIR / "walkforward_is_equity.csv"
OOS_CSV = EXP_DIR / "walkforward_oos_equity.csv"
WF_JSON = EXP_DIR / "walkforward.json"


class _PrecomputedTargets:
    def __init__(self, targets):
        self._t = targets

    def target_asset(self, panel):
        idx = next(iter(panel.values())).index
        return self._t.reindex(idx)


def load_panel() -> dict:
    panel = {}
    for sym in ASSETS:
        df = pd.read_csv(DATA_DIR / f"{sym}_4h.csv", index_col=0, parse_dates=True)
        df.index = pd.to_datetime(df.index, utc=True)
        panel[sym] = df
    return panel


def main() -> int:
    print("=" * 78)
    print("WFO INDEPENDENT RECONSTRUCTION AUDIT — Exp 002")
    print("=" * 78)

    panel_full = load_panel()
    index_full = panel_full[ASSETS[0]].index
    n = len(index_full)
    print(f"Panel rows: {n}")
    print(f"Split index: {SPLIT_INDEX}")

    panel_is = {a: panel_full[a].iloc[:SPLIT_INDEX].copy() for a in ASSETS}
    panel_oos = {a: panel_full[a].iloc[SPLIT_INDEX:].copy() for a in ASSETS}

    # ------------------------------------------------------------------
    # 1. IS reconstruction (fresh strategy)
    # ------------------------------------------------------------------
    print("\n[1] IS independent reconstruction (fresh strategy)")
    strat_is = CrossSectionalMomentum(lookback=LOOKBACK, tiebreak_order=TIEBREAK)
    r_is = run_cross_sectional_backtest(panel_is, strat_is, CONFIG)
    print(f"  IS trades:       {r_is.trade_count}")
    print(f"  IS net_pnl:      {r_is.net_pnl:.6f}")
    print(f"  IS equity first: {r_is.equity_curve.iloc[0]:.6f}")
    print(f"  IS equity last:  {r_is.equity_curve.iloc[-1]:.6f}")

    # ------------------------------------------------------------------
    # 2. OOS reconstruction (warmed targets)
    # ------------------------------------------------------------------
    print("\n[2] OOS independent reconstruction (warmed targets)")
    warm_start = SPLIT_INDEX - WARMUP_BARS
    panel_warm = {a: panel_full[a].iloc[warm_start:].copy() for a in ASSETS}
    strat_warm = CrossSectionalMomentum(lookback=LOOKBACK, tiebreak_order=TIEBREAK)
    warm_targets = strat_warm.target_asset(panel_warm)
    oos_targets = warm_targets.iloc[WARMUP_BARS:]

    first6_nan = bool(warm_targets.iloc[:WARMUP_BARS].isna().all())
    print(f"  first {WARMUP_BARS} warm_targets NaN: {first6_nan}")
    print(f"  first OOS target: {oos_targets.iloc[0]} at {oos_targets.index[0]}")
    print(f"  OOS targets all valid: {bool(oos_targets.notna().all())}")

    oos_strategy = _PrecomputedTargets(oos_targets)
    r_oos = run_cross_sectional_backtest(panel_oos, oos_strategy, CONFIG)
    print(f"  OOS trades:       {r_oos.trade_count}")
    print(f"  OOS net_pnl:      {r_oos.net_pnl:.6f}")
    print(f"  OOS equity first: {r_oos.equity_curve.iloc[0]:.6f}")
    print(f"  OOS equity last:  {r_oos.equity_curve.iloc[-1]:.6f}")

    # ------------------------------------------------------------------
    # 3. Compare with frozen WFO CSVs
    # ------------------------------------------------------------------
    print("\n[3] Compare with frozen WFO CSVs")
    is_frozen = pd.read_csv(IS_CSV, index_col=0, parse_dates=True)
    oos_frozen = pd.read_csv(OOS_CSV, index_col=0, parse_dates=True)
    is_frozen.index = pd.to_datetime(is_frozen.index, utc=True)
    oos_frozen.index = pd.to_datetime(oos_frozen.index, utc=True)

    print(f"  IS CSV rows: {len(is_frozen)}")
    print(f"  OOS CSV rows: {len(oos_frozen)}")

    is_recon = r_is.equity_curve.rename("equity")
    oos_recon = r_oos.equity_curve.rename("equity")

    if not is_recon.index.equals(is_frozen.index):
        print("  IS index mismatch between reconstruction and CSV")
        return 1
    if not oos_recon.index.equals(oos_frozen.index):
        print("  OOS index mismatch between reconstruction and CSV")
        return 1

    is_diff = (is_recon - is_frozen["equity"]).abs()
    oos_diff = (oos_recon - oos_frozen["equity"]).abs()

    print(f"  IS  max abs diff:  {is_diff.max():.10f}")
    print(f"  IS  mean abs diff: {is_diff.mean():.10f}")
    print(f"  OOS max abs diff:  {oos_diff.max():.10f}")
    print(f"  OOS mean abs diff: {oos_diff.mean():.10f}")

    is_ok = is_diff.max() < 1e-6
    oos_ok = oos_diff.max() < 1e-6
    print(f"  IS reconstruction:  {'PASS' if is_ok else 'FAIL'}")
    print(f"  OOS reconstruction: {'PASS' if oos_ok else 'FAIL'}")

    # ------------------------------------------------------------------
    # 4. Force-flat isolation
    # ------------------------------------------------------------------
    print("\n[4] Force-flat isolation at split")
    oos_starts_flat = abs(r_oos.equity_curve.iloc[0] - CONFIG.initial_capital) < 1e-6
    print(f"  OOS first bar equity == initial capital: {oos_starts_flat}")
    print(f"    OOS first bar equity = {r_oos.equity_curve.iloc[0]:.6f}")

    is_ends_flat = (
        len(r_is.trades) > 0
        and r_is.trades[-1].exit_index == SPLIT_INDEX - 1
    )
    print(f"  IS last trade exits at split index: {is_ends_flat}")
    if len(r_is.trades) > 0:
        print(f"    last trade exit_index: {r_is.trades[-1].exit_index}")

    # ------------------------------------------------------------------
    # 5. Capital conservation
    # ------------------------------------------------------------------
    print("\n[5] Capital conservation")
    is_sum = sum(t.net_pnl for t in r_is.trades)
    oos_sum = sum(t.net_pnl for t in r_oos.trades)
    is_exp = CONFIG.initial_capital + is_sum
    oos_exp = CONFIG.initial_capital + oos_sum
    print(f"  IS  expected final = {is_exp:.6f}")
    print(f"  IS  actual final   = {r_is.equity_curve.iloc[-1]:.6f}")
    print(f"  OOS expected final = {oos_exp:.6f}")
    print(f"  OOS actual final   = {r_oos.equity_curve.iloc[-1]:.6f}")
    is_cc = abs(is_exp - r_is.equity_curve.iloc[-1]) < 1e-6
    oos_cc = abs(oos_exp - r_oos.equity_curve.iloc[-1]) < 1e-6
    print(f"  IS capital conservation:  {'PASS' if is_cc else 'FAIL'}")
    print(f"  OOS capital conservation: {'PASS' if oos_cc else 'FAIL'}")

    # ------------------------------------------------------------------
    # 6. Compare with walkforward.json
    # ------------------------------------------------------------------
    print("\n[6] Compare with walkforward.json")
    with open(WF_JSON) as f:
        wf = json.load(f)

    json_is_trades = wf["is"]["strategy"]["trade_count"]
    json_oos_trades = wf["oos"]["strategy"]["trade_count"]
    json_is_pnl = wf["is"]["strategy"]["net_pnl"]
    json_oos_pnl = wf["oos"]["strategy"]["net_pnl"]

    print(f"  IS  trades: JSON={json_is_trades}  recon={r_is.trade_count}  "
          f"{'match' if json_is_trades == r_is.trade_count else 'MISMATCH'}")
    print(f"  OOS trades: JSON={json_oos_trades} recon={r_oos.trade_count} "
          f"{'match' if json_oos_trades == r_oos.trade_count else 'MISMATCH'}")
    print(f"  IS  net_pnl: JSON={json_is_pnl:.6f} recon={r_is.net_pnl:.6f} "
          f"{'match' if abs(json_is_pnl - r_is.net_pnl) < 1e-6 else 'MISMATCH'}")
    print(f"  OOS net_pnl: JSON={json_oos_pnl:.6f} recon={r_oos.net_pnl:.6f} "
          f"{'match' if abs(json_oos_pnl - r_oos.net_pnl) < 1e-6 else 'MISMATCH'}")

    json_ok = (
        json_is_trades == r_is.trade_count
        and json_oos_trades == r_oos.trade_count
        and abs(json_is_pnl - r_is.net_pnl) < 1e-6
        and abs(json_oos_pnl - r_oos.net_pnl) < 1e-6
    )

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    all_ok = (
        is_ok and oos_ok and first6_nan
        and oos_starts_flat and is_ends_flat
        and is_cc and oos_cc and json_ok
    )
    print("\n" + "=" * 78)
    if all_ok:
        print("WFO AUDIT: ALL CHECKS PASS")
        return 0
    else:
        print("WFO AUDIT: SOME CHECKS FAILED")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())