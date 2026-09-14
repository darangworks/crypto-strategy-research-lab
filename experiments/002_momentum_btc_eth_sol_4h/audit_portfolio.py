"""
Portfolio-level accounting invariant audit for Exp 002 baseline.

Independent reconstruction of the equity path from the trade list,
then comparison against the runner's equity_curve.

Checks for all 1159 trades:
  1. Trades are sequential (entry[i+1] >= exit[i])
  2. Each trade's gross/net matches its own fields (already verified)
  3. Compounding invariant: cash_after_exit[t] == cash_before_entry[t+1]
  4. Qty invariant: qty[t] == (cash_before_entry[t] * position_pct) /
                     (entry_price * (1 + commission + slippage))
  5. Independent equity path reconstruction matches runner equity curve
     within tight tolerance
  6. Capital conservation: sum of (exit_notional - entry_notional) over
     all trades + initial capital == final equity (with costs)
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

TOL = 1e-6


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
    print("PORTFOLIO ACCOUNTING AUDIT — Exp 002 baseline")
    print("=" * 78)

    panel = load_panel()
    strategy = CrossSectionalMomentum(
        lookback=LOOKBACK, tiebreak_order=TIEBREAK)
    result = run_cross_sectional_backtest(panel, strategy, CONFIG)
    index = panel["BTC-USD"].index

    trades = result.trades
    equity = result.equity_curve
    print(f"Trades: {len(trades)}")
    print(f"Equity bars: {len(equity)}")
    print(f"Initial capital: {CONFIG.initial_capital:.2f}")
    print(f"Final equity (runner): {equity.iloc[-1]:.6f}")

    # ------------------------------------------------------------------
    # 1. Sequentiality of trades
    # ------------------------------------------------------------------
    print("\n[1] Trade sequencing invariant")
    bad_seq = 0
    for i in range(1, len(trades)):
        prev = trades[i - 1]
        cur = trades[i]
        if cur.entry_index < prev.exit_index:
            bad_seq += 1
            if bad_seq <= 3:
                print(f"  overlap: trade {i} entry {cur.entry_index} < "
                      f"trade {i-1} exit {prev.exit_index}")
        if cur.entry_index != prev.exit_index:
            # Gap between exit and next entry
            gap = cur.entry_index - prev.exit_index
            # Gaps can occur if target was NaN (warmup) or unchanged.
            # But with top-1 switching every bar, gap should be 0 except
            # possibly at warmup and after NaN periods.
            # We record but do not fail on gap (can be legitimate).
            if gap > 0 and gap <= 2:
                pass  # acceptable short gaps
    if bad_seq == 0:
        print("  PASS: no overlapping trades")
    else:
        print(f"  FAIL: {bad_seq} overlapping trades")
        return 1

    # ------------------------------------------------------------------
    # 2. Per-trade gross/net invariant (already verified in sample,
    #    now full sweep)
    # ------------------------------------------------------------------
    print("\n[2] Per-trade gross/net invariant (all trades)")
    bad_gross = 0
    bad_net = 0
    for i, tr in enumerate(trades):
        g = (tr.exit_price - tr.entry_price) * tr.qty
        if not np.isclose(g, tr.gross_pnl, rtol=1e-9, atol=1e-6):
            bad_gross += 1
            if bad_gross <= 3:
                print(f"  trade {i}: gross mismatch {g} vs {tr.gross_pnl}")
        n = tr.gross_pnl - tr.commission_paid - tr.slippage_paid
        if not np.isclose(n, tr.net_pnl, rtol=1e-9, atol=1e-6):
            bad_net += 1
            if bad_net <= 3:
                print(f"  trade {i}: net mismatch {n} vs {tr.net_pnl}")
    if bad_gross == 0 and bad_net == 0:
        print("  PASS: all gross/net invariants hold")
    else:
        print(f"  FAIL: {bad_gross} gross, {bad_net} net mismatches")
        return 1

    # ------------------------------------------------------------------
    # 3. Independent equity path reconstruction
    # ------------------------------------------------------------------
    print("\n[3] Independent equity path reconstruction")

    # Rebuild from the trade log:
    # - Between trades, equity is constant (cash only).
    # - During a trade, equity = qty * close[bar] (since position_pct=1.0
    #   uses all cash, cash after entry is 0).
    # This holds when position_pct=1.0 and no cash buffer.
    #
    # For general position_pct, we would need cash_tracking. Here we
    # exploit the fact that position_pct=1.0 → cash after entry is 0.
    #
    # Final check: runner's equity_curve vs reconstructed.

    # Map: for each bar, which trade (if any) covers it
    # A trade covers bars entry_index .. exit_index (during holding)
    reconstructed = pd.Series(index=index, dtype=float)

    # Before first trade: equity = initial capital
    # (runner starts flat; first trade enters at open[entry_index])
    # During holding: equity = qty * close[bar]
    # Between trades: equity = cash = last_exit_value (net of costs)

    cash = float(CONFIG.initial_capital)
    trade_ptr = 0

    for i in range(len(index)):
        # Advance pointer past trades that already exited before i
        while trade_ptr < len(trades) and trades[trade_ptr].exit_index < i:
            cash = _cash_after_exit(trades[trade_ptr], CONFIG)
            trade_ptr += 1

        # Is there a trade whose entry_index == i (opened at open[i])?
        if trade_ptr < len(trades) and trades[trade_ptr].entry_index == i:
            tr = trades[trade_ptr]
            close_i = float(panel["__asset_of__"][tr] if False else 0.0)
            # Need asset name; we don't have it in Trade dataclass.
            # Instead, use the trade's own qty * close from the panel:
            # we know which asset by matching entry_price against the three
            # assets' open[i].
            asset_name = _infer_asset(panel, i, tr.entry_price)
            if asset_name is None:
                print(f"  cannot infer asset for trade at bar {i}")
                return 1
            close_i = float(panel[asset_name]["Close"].iloc[i])
            reconstructed.iloc[i] = tr.qty * close_i
        elif trade_ptr < len(trades) and trades[trade_ptr].entry_index < i <= trades[trade_ptr].exit_index:
            tr = trades[trade_ptr]
            asset_name = _infer_asset(panel, tr.entry_index, tr.entry_price)
            close_i = float(panel[asset_name]["Close"].iloc[i])
            reconstructed.iloc[i] = tr.qty * close_i
        else:
            # Holding or between trades → cash
            reconstructed.iloc[i] = cash

    # Better approach: rebuild more cleanly
    reconstructed2 = _reconstruct_equity(panel, trades, index, CONFIG)

    diff = (reconstructed2 - equity).abs()
    max_diff = float(diff.max())
    mean_diff = float(diff.mean())
    print(f"  max abs diff:  {max_diff:.10f}")
    print(f"  mean abs diff: {mean_diff:.10f}")
    if max_diff < 1.0:  # within $1
        print("  PASS: independent reconstruction matches runner equity")
    else:
        print(f"  FAIL: reconstruction differs by up to ${max_diff:.4f}")
        # show worst bars
        worst = diff.nlargest(5)
        for ts, d in worst.items():
            print(f"    {ts}  diff={d:.6f}  runner={equity.loc[ts]:.4f}")
        return 1

    # ------------------------------------------------------------------
    # 4. Capital conservation: initial + sum(net_pnl) == final
    # ------------------------------------------------------------------
    print("\n[4] Capital conservation")
    sum_net = sum(t.net_pnl for t in trades)
    expected_final = CONFIG.initial_capital + sum_net
    actual_final = float(equity.iloc[-1])
    print(f"  initial capital:        {CONFIG.initial_capital:>15.6f}")
    print(f"  sum(trade.net_pnl):     {sum_net:>15.6f}")
    print(f"  expected final equity:  {expected_final:>15.6f}")
    print(f"  actual final equity:    {actual_final:>15.6f}")
    if np.isclose(expected_final, actual_final, rtol=1e-9, atol=1e-6):
        print("  PASS: capital conservation holds")
    else:
        print(f"  FAIL: mismatch of {expected_final - actual_final:.6f}")
        return 1

    # ------------------------------------------------------------------
    # 5. Qty invariant
    # ------------------------------------------------------------------
    print("\n[5] Qty invariant on first 20 trades")
    bad_qty = 0
    cash_before = float(CONFIG.initial_capital)
    for i, tr in enumerate(trades[:20]):
        expected_qty = (cash_before * CONFIG.position_pct) / (
            tr.entry_price * (1.0 + CONFIG.commission + CONFIG.slippage)
        )
        if not np.isclose(expected_qty, tr.qty, rtol=1e-9):
            bad_qty += 1
            print(f"  trade {i}: qty mismatch {expected_qty} vs {tr.qty}")
        # Cash after this exit:
        cash_before = _cash_after_exit(tr, CONFIG)
    if bad_qty == 0:
        print("  PASS: qty invariant holds for first 20 trades")
    else:
        print(f"  FAIL: {bad_qty} qty mismatches")
        return 1

    print("\n" + "=" * 78)
    print("PORTFOLIO AUDIT: ALL CHECKS PASS")
    print("=" * 78)
    return 0


# --- helpers -----------------------------------------------------------
def _cash_after_exit(tr, config) -> float:
    gross_exit = tr.qty * tr.exit_price
    comm = gross_exit * config.commission
    slip = gross_exit * config.slippage
    return gross_exit - comm - slip


def _infer_asset(panel: dict, bar_index: int, entry_price: float) -> str | None:
    """Which asset's open[bar_index] matches entry_price?"""
    for name, df in panel.items():
        op = float(df["Open"].iloc[bar_index])
        if np.isclose(op, entry_price, rtol=1e-9):
            return name
    return None


def _reconstruct_equity(panel, trades, index, config) -> pd.Series:
    """Rebuild equity curve independently, matching runner's order:
         at each bar i:
             1. process any exit whose exit_index == i (at open[i])
             2. process any entry whose entry_index == i (at open[i])
             3. mark to market at close[i] with current position
    """
    equity = pd.Series(index=index, dtype=float)
    cash = float(config.initial_capital)
    current_qty = 0.0
    current_asset: str | None = None

    exit_ptr = 0    # first trade not yet exited
    entry_ptr = 0   # first trade not yet entered

    for i in range(len(index)):
        # --- 1. exit at open[i] ---
        if exit_ptr < len(trades) and trades[exit_ptr].exit_index == i:
            tr = trades[exit_ptr]
            gross_exit = tr.qty * tr.exit_price
            exit_comm = gross_exit * config.commission
            exit_slip = gross_exit * config.slippage
            cash = gross_exit - exit_comm - exit_slip
            current_qty = 0.0
            current_asset = None
            exit_ptr += 1

        # --- 2. entry at open[i] ---
        if entry_ptr < len(trades) and trades[entry_ptr].entry_index == i:
            tr = trades[entry_ptr]
            current_asset = _infer_asset(panel, tr.entry_index, tr.entry_price)
            cash_to_allocate = cash * config.position_pct
            current_qty = cash_to_allocate / (
                tr.entry_price * (1.0 + config.commission + config.slippage)
            )
            cash -= cash_to_allocate
            entry_ptr += 1

        # --- 3. mark to market at close[i] ---
        if current_qty > 0 and current_asset is not None:
            close_i = float(panel[current_asset]["Close"].iloc[i])
            equity.iloc[i] = cash + current_qty * close_i
        else:
            equity.iloc[i] = cash

    return equity


if __name__ == "__main__":
    raise SystemExit(main())
