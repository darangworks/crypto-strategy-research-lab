"""
Audit script for Exp 002 baseline.

Read-only. Does not modify frozen data, runner, or artifacts.

Runs three audits requested by evaluator (2026-09-14):
  1. Signal audit — momentum / ranks / target_asset / executed_asset,
     focused on transitions.
  2. Transition accounting audit — full breakdown for first N transitions.
  3. Trade-count sanity test — synthetic ranking with known transitions.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import numpy as np
import pandas as pd

from engine.backtest import BacktestConfig
from engine.cross_sectional_backtest import run_cross_sectional_backtest
from strategies.cross_sectional_momentum.strategy import (
    CrossSectionalMomentum,
)


DATA_DIR = REPO_ROOT / "data" / "002_btc_eth_sol_4h"
ASSETS = ["BTC-USD", "ETH-USD", "SOL-USD"]
TIEBREAK = ASSETS
LOOKBACK = 6
CONFIG = BacktestConfig(
    initial_capital=100_000.0,
    position_pct=1.0,
    commission=0.0005,
    slippage=0.0002,
)


def load_panel() -> dict:
    panel = {}
    for sym in ASSETS:
        path = DATA_DIR / f"{sym}_4h.csv"
        df = pd.read_csv(path, index_col=0, parse_dates=True)
        df.index = pd.to_datetime(df.index, utc=True)
        panel[sym] = df
    return panel


# -----------------------------------------------------------------------
# AUDIT 1 — Signal sequence and rank transitions
# -----------------------------------------------------------------------
def audit_signal_sequence(panel: dict, n_head: int = 30) -> None:
    print("\n" + "=" * 78)
    print("AUDIT 1 — Signal sequence (first 30 bars with valid momentum)")
    print("=" * 78)

    strategy = CrossSectionalMomentum(lookback=LOOKBACK, tiebreak_order=TIEBREAK)
    mom = strategy.momentum(panel)
    ranks = strategy.ranks(panel)
    targets = strategy.target_asset(panel)

    # Find first valid bar
    valid = mom.notna().all(axis=1)
    first_valid = valid.idxmax()

    print(f"First bar with valid momentum: {first_valid}")
    print(f"Total bars with valid momentum: {valid.sum()}")

    # Show first n valid bars
    print(f"\n{'timestamp':<26} | {'mom_BTC':>9} {'mom_ETH':>9} {'mom_SOL':>9} | "
          f"{'r_BTC':>5} {'r_ETH':>5} {'r_SOL':>5} | target")
    shown = 0
    for i, ts in enumerate(mom.index):
        if not valid.iloc[i]:
            continue
        if shown >= n_head:
            break
        m = mom.loc[ts]
        r = ranks.loc[ts]
        t = targets.loc[ts]
        print(f"{str(ts):<26} | "
              f"{m['BTC-USD']:>9.5f} {m['ETH-USD']:>9.5f} {m['SOL-USD']:>9.5f} | "
              f"{int(r['BTC-USD']):>5} {int(r['ETH-USD']):>5} {int(r['SOL-USD']):>5} | "
              f"{t}")
        shown += 1

    # Verify target = argmax with tiebreak
    print("\nVerifying target_asset[t] == tiebreak argmax of momentum[t]:")
    n_mismatch = 0
    for ts in mom.index:
        if not valid.loc[ts]:
            continue
        row = mom.loc[ts]
        expected = max(
            [a for a in TIEBREAK],
            key=lambda a: (row[a], -TIEBREAK.index(a)),
        )
        # Careful: we want max momentum, and among ties, earliest in TIEBREAK
        max_mom = row.max()
        tied = [a for a in TIEBREAK if np.isclose(row[a], max_mom)]
        expected = tied[0]  # TIEBREAK is already in priority order
        if targets.loc[ts] != expected:
            n_mismatch += 1
            if n_mismatch <= 5:
                print(f"  MISMATCH at {ts}: target={targets.loc[ts]}, expected={expected}")
    print(f"  Total mismatches: {n_mismatch}")

    # Transitions: count how many times target changes
    t_series = targets.dropna()
    changes = (t_series != t_series.shift(1)).sum() - 1  # -1 for first
    print(f"\nTotal target_asset changes: {changes}")
    print(f"Expected trade_count from runner (holding episodes ending): "
          f"{changes if changes > 0 else 0} "
          f"(+1 if final position non-empty)")

    # Show first 10 transition points
    print("\nFirst 10 transition points (where target[t] != target[t-1]):")
    prev = None
    shown = 0
    for ts, t in t_series.items():
        if prev is not None and t != prev and shown < 10:
            print(f"  {ts}:  {prev}  ->  {t}")
            shown += 1
        prev = t


# -----------------------------------------------------------------------
# AUDIT 2 — Transition accounting
# -----------------------------------------------------------------------
def audit_transition_accounting(panel: dict, n_transitions: int = 5) -> None:
    print("\n" + "=" * 78)
    print("AUDIT 2 — Transition accounting (first N transitions)")
    print("=" * 78)

    strategy = CrossSectionalMomentum(lookback=LOOKBACK, tiebreak_order=TIEBREAK)
    result = run_cross_sectional_backtest(panel, strategy, CONFIG)

    index = panel["BTC-USD"].index

    print(f"Total trades recorded: {result.trade_count}")
    print(f"First {n_transitions} trades with full accounting:\n")

    for i, tr in enumerate(result.trades[:n_transitions]):
        entry_ts = index[tr.entry_index]
        exit_ts = index[tr.exit_index]
        holding_bars = tr.exit_index - tr.entry_index

        print(f"--- Trade {i+1} ---")
        print(f"  entry_index: {tr.entry_index}  ({entry_ts})")
        print(f"  exit_index:  {tr.exit_index}   ({exit_ts})")
        print(f"  holding bars: {holding_bars}")
        print(f"  entry_price: {tr.entry_price:.4f}")
        print(f"  exit_price:  {tr.exit_price:.4f}")
        print(f"  qty:         {tr.qty:.6f}")
        print(f"  gross_pnl:   {tr.gross_pnl:.4f}")
        print(f"  commission:  {tr.commission_paid:.4f}")
        print(f"  slippage:    {tr.slippage_paid:.4f}")
        print(f"  net_pnl:     {tr.net_pnl:.4f}")

        # Sanity checks
        expected_gross = (tr.exit_price - tr.entry_price) * tr.qty
        if not np.isclose(expected_gross, tr.gross_pnl, rtol=1e-9):
            print(f"  ⚠️ gross_pnl mismatch: {expected_gross} vs {tr.gross_pnl}")

        expected_net = tr.gross_pnl - tr.commission_paid - tr.slippage_paid
        if not np.isclose(expected_net, tr.net_pnl, rtol=1e-9):
            print(f"  ⚠️ net_pnl mismatch: {expected_net} vs {tr.net_pnl}")

        print()


# -----------------------------------------------------------------------
# AUDIT 3 — Trade-count sanity test on synthetic ranking
# -----------------------------------------------------------------------
def audit_trade_count_synthetic() -> None:
    print("\n" + "=" * 78)
    print("AUDIT 3 — Trade-count sanity on synthetic price panel")
    print("=" * 78)

    n = 30
    idx = pd.date_range("2024-01-01", periods=n, freq="4h", tz="UTC")

    # Construct synthetic prices so that each asset dominates in distinct segments
    # BTC strongest bars 6-11, ETH 12-17, SOL 18-23, BTC 24-29
    # With lookback=6, target should switch at the segment boundaries.
    def make_closes(dominance_windows):
        closes = np.ones(n) * 100.0
        for start, end, slope in dominance_windows:
            for j in range(start, min(end, n)):
                closes[j] = closes[j - 1] * (1.0 + slope)
        return closes

    btc = make_closes([(6, 12, +0.02), (24, 30, +0.02)])
    eth = make_closes([(12, 18, +0.02)])
    sol = make_closes([(18, 24, +0.02)])

    panel = {}
    for name, closes in [("BTC-USD", btc), ("ETH-USD", eth), ("SOL-USD", sol)]:
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

    strategy = CrossSectionalMomentum(lookback=LOOKBACK, tiebreak_order=TIEBREAK)
    targets = strategy.target_asset(panel)
    print("Target sequence:")
    for ts, t in targets.items():
        print(f"  {ts}  {t}")

    # Count target changes
    valid_targets = targets.dropna()
    changes = (valid_targets != valid_targets.shift(1)).sum() - 1
    print(f"\nTarget changes: {changes}")

    cfg = BacktestConfig(initial_capital=100_000.0, position_pct=1.0,
                         commission=0.0005, slippage=0.0002)
    result = run_cross_sectional_backtest(panel, strategy, cfg)
    print(f"Runner trade_count: {result.trade_count}")
    print(f"\nExpected relationship:")
    print(f"  trade_count = number of holding episodes that ENDED")
    print(f"  = (target changes) + (1 if final position held)")
    print(f"  Actual: {result.trade_count}")


# -----------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------
def main() -> int:
    panel = load_panel()
    audit_signal_sequence(panel, n_head=30)
    audit_transition_accounting(panel, n_transitions=5)
    audit_trade_count_synthetic()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())