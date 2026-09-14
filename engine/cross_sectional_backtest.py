"""
Cross-sectional backtest runner for multi-asset strategies.

Handles a single compounded portfolio with one position at a time
(switching between assets on signal). Position accounting follows the
same Trade dataclass and BacktestConfig fields as engine/backtest.py.

This file is NEW; engine/backtest.py is NOT modified.

Invariants enforced:
- Signal at close of bar t → execution at open of bar t+1.
- No new transition is executed on the last bar (no bar t+1).
- If a position is held on the last bar, it is liquidated at the close
  of that bar with normal costs.
- Costs are charged only when the target asset changes and an actual
  position transition occurs (first entry and final exit charged).
- Equity is single compounded: cash + mark-to-market of held asset.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from engine.backtest import BacktestConfig, Trade


@dataclass
class CrossSectionalResult:
    equity_curve: pd.Series
    trades: list
    returns: pd.Series
    sharpe: float
    net_pnl: float
    profit_factor: float
    win_rate: float
    max_drawdown: float
    trade_count: int


def _annualize_factor(index: pd.DatetimeIndex) -> float:
    """Estimate sqrt(bars per year) from a datetime index."""
    if len(index) < 2:
        return 1.0
    total_seconds = (index[-1] - index[0]).total_seconds()
    if total_seconds <= 0:
        return 1.0
    n_bars = len(index) - 1
    seconds_per_bar = total_seconds / n_bars
    if seconds_per_bar <= 0:
        return 1.0
    bars_per_year = 365.25 * 24.0 * 3600.0 / seconds_per_bar
    return float(np.sqrt(bars_per_year))


def _max_drawdown(equity: pd.Series) -> float:
    if len(equity) == 0:
        return 0.0
    running_max = equity.cummax()
    drawdown = equity / running_max - 1.0
    return float(drawdown.min())


def run_cross_sectional_backtest(
    panel: dict,
    strategy,
    config: BacktestConfig | None = None,
) -> CrossSectionalResult:
    """Run a cross-sectional backtest on a panel of aligned assets.

    Parameters
    ----------
    panel : dict[str, pd.DataFrame]
        Asset name -> DataFrame with Open/High/Low/Close/Volume,
        all sharing the exact same DatetimeIndex.
    strategy : object with method target_asset(panel) -> pd.Series
        Series of asset names (from panel keys), one per timestamp.
        NaN entries mean "no signal yet" (warmup).
    config : BacktestConfig
        Same dataclass as single-asset engine. position_pct controls
        the fraction of available cash used on each entry.

    Returns
    -------
    CrossSectionalResult
    """
    if config is None:
        config = BacktestConfig()

    if len(panel) == 0:
        raise ValueError("panel must contain at least one asset")

    assets = sorted(panel.keys())
    index = panel[assets[0]].index
    n = len(index)

    # All assets must share the same index
    for name, df in panel.items():
        if not df.index.equals(index):
            raise ValueError(f"panel[{name}] index does not match panel[{assets[0]}]")
        for col in ("Open", "High", "Low", "Close", "Volume"):
            if col not in df.columns:
                raise ValueError(f"panel[{name}] missing column: {col}")

    targets = strategy.target_asset(panel)
    if not isinstance(targets, pd.Series):
        raise TypeError("target_asset(panel) must return a pandas Series")
    if not targets.index.equals(index):
        raise ValueError("target_asset index must match panel index")

    valid_assets = set(assets)
    for v in targets.dropna().unique():
        if v not in valid_assets:
            raise ValueError(f"target_asset returned unknown asset: {v!r}")

    # State
    cash = float(config.initial_capital)
    position_qty = 0.0
    current_asset: str | None = None
    entry_price = 0.0
    entry_index = 0
    entry_commission = 0.0
    entry_slippage = 0.0

    equity_curve = pd.Series(index=index, dtype=float, name="equity")
    returns = pd.Series(index=index, dtype=float, name="returns")
    trades: list = []

    prev_equity = float(config.initial_capital)

    for i in range(n):
        # -----------------------------------------------------------
        # 1. Execute transition from prior bar's signal at open[i]
        # -----------------------------------------------------------
        if i > 0:
            target = targets.iloc[i - 1]
            if not pd.isna(target) and target != current_asset:
                # Exit current asset at open[i]
                if current_asset is not None:
                    exit_price = float(panel[current_asset]["Open"].iloc[i])
                    if exit_price <= 0:
                        raise ValueError(f"non-positive exit price for {current_asset} at {index[i]}")

                    gross_exit = position_qty * exit_price
                    exit_comm = gross_exit * config.commission
                    exit_slip = gross_exit * config.slippage
                    net_exit = gross_exit - exit_comm - exit_slip

                    gross_pnl = (exit_price - entry_price) * position_qty
                    total_comm = entry_commission + exit_comm
                    total_slip = entry_slippage + exit_slip
                    net_pnl = gross_pnl - total_comm - total_slip

                    trades.append(Trade(
                        entry_index=int(entry_index),
                        exit_index=int(i),
                        entry_price=float(entry_price),
                        exit_price=float(exit_price),
                        qty=float(position_qty),
                        gross_pnl=float(gross_pnl),
                        commission_paid=float(total_comm),
                        slippage_paid=float(total_slip),
                        net_pnl=float(net_pnl),
                    ))

                    cash = net_exit
                    position_qty = 0.0
                    current_asset = None

                # Enter target at open[i]
                entry_price_exec = float(panel[target]["Open"].iloc[i])
                if entry_price_exec <= 0:
                    raise ValueError(f"non-positive entry price for {target} at {index[i]}")

                cash_to_allocate = cash * config.position_pct
                denom = entry_price_exec * (1.0 + config.commission + config.slippage)
                if denom <= 0:
                    raise ValueError(f"invalid denominator for {target} at {index[i]}")
                qty = cash_to_allocate / denom

                entry_notional = qty * entry_price_exec
                entry_comm = entry_notional * config.commission
                entry_slip = entry_notional * config.slippage

                cash -= cash_to_allocate
                position_qty = qty
                current_asset = target
                entry_price = entry_price_exec
                entry_index = i
                entry_commission = entry_comm
                entry_slippage = entry_slip

        # -----------------------------------------------------------
        # 2. Mark to market at close[i]
        # -----------------------------------------------------------
        if current_asset is not None:
            close_price = float(panel[current_asset]["Close"].iloc[i])
            equity = cash + position_qty * close_price
        else:
            equity = cash

        # -----------------------------------------------------------
        # 3. Final-bar liquidation (if holding at last bar)
        # -----------------------------------------------------------
        if i == n - 1 and current_asset is not None:
            exit_price = float(panel[current_asset]["Close"].iloc[i])
            gross_exit = position_qty * exit_price
            exit_comm = gross_exit * config.commission
            exit_slip = gross_exit * config.slippage
            net_exit = gross_exit - exit_comm - exit_slip

            gross_pnl = (exit_price - entry_price) * position_qty
            total_comm = entry_commission + exit_comm
            total_slip = entry_slippage + exit_slip
            net_pnl = gross_pnl - total_comm - total_slip

            trades.append(Trade(
                entry_index=int(entry_index),
                exit_index=int(i),
                entry_price=float(entry_price),
                exit_price=float(exit_price),
                qty=float(position_qty),
                gross_pnl=float(gross_pnl),
                commission_paid=float(total_comm),
                slippage_paid=float(total_slip),
                net_pnl=float(net_pnl),
            ))

            cash = net_exit
            position_qty = 0.0
            current_asset = None
            equity = cash

        equity_curve.iloc[i] = equity
        returns.iloc[i] = (equity / prev_equity - 1.0) if prev_equity > 0 else 0.0
        prev_equity = equity

    # ---------------------------------------------------------------
    # Metrics
    # ---------------------------------------------------------------
    final_equity = float(equity_curve.iloc[-1])
    net_pnl = final_equity - float(config.initial_capital)

    ann = _annualize_factor(index)
    std = float(returns.std(ddof=1)) if len(returns) > 1 else 0.0
    mean = float(returns.mean()) if len(returns) > 0 else 0.0
    sharpe = (mean / std * ann) if std > 0 else 0.0

    wins = [t.net_pnl for t in trades if t.net_pnl > 0]
    losses = [t.net_pnl for t in trades if t.net_pnl < 0]
    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    if gross_loss > 0:
        profit_factor = gross_profit / gross_loss
    elif gross_profit > 0:
        profit_factor = float("inf")
    else:
        profit_factor = 0.0

    win_rate = (len(wins) / len(trades)) if trades else 0.0
    max_dd = _max_drawdown(equity_curve)

    return CrossSectionalResult(
        equity_curve=equity_curve,
        trades=trades,
        returns=returns,
        sharpe=float(sharpe),
        net_pnl=float(net_pnl),
        profit_factor=float(profit_factor),
        win_rate=float(win_rate),
        max_drawdown=float(max_dd),
        trade_count=int(len(trades)),
    )