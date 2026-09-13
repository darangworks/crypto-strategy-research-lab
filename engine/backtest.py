"""
Backtest engine for Project 2.

Strategy API contract (frozen):

  - target_position(df) returns a direction series:
        0  = flat
        +1 = long
        -1 = short  (not supported in Experiment 001)

  - position_pct in BacktestConfig controls the fraction of equity
    allocated to each position. Direction and sizing are separate.

Execution model (frozen by Experiment 001 pre-registration):

  - Signal generated at close of bar t
  - Fill at open of bar t+1
  - No leverage
  - One position at a time (flat or long only in Exp 001)

Cost model (frozen):

  - Slippage applied to execution price:
      Long entry: fill = open[t+1] * (1 + slippage)
      Long exit:  fill = exit_price * (1 - slippage)

  - Commission applied to the ACTUAL execution notional:
      commission_paid = fill * qty * commission_rate

  - Entry commission is deducted from equity immediately at entry.
  - Exit commission is deducted from equity at exit.

Returns definition (frozen):

  - returns = bar-to-bar percentage change of the total equity curve.

Sharpe (frozen by pre-registration):

  - sharpe = mean(returns) / std(returns) * sqrt(6 * 365)

Edge cases:

  - A signal on the last bar has no open[t+1] and is therefore not
    executed. Any open position is liquidated at the last bar's close.
  - Short positions (-1) are not supported in Experiment 001 and
    raise ValueError.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd


@dataclass
class BacktestConfig:
    initial_capital: float = 100_000.0
    position_pct: float = 0.10
    commission: float = 0.0005
    slippage: float = 0.0002


@dataclass
class Trade:
    entry_index: int
    exit_index: int
    entry_price: float
    exit_price: float
    qty: float
    gross_pnl: float
    commission_paid: float
    slippage_paid: float
    net_pnl: float


@dataclass
class BacktestResult:
    equity_curve: pd.Series
    trades: list
    returns: pd.Series
    sharpe: float
    net_pnl: float
    profit_factor: float
    win_rate: float
    max_drawdown: float
    trade_count: int


def run_backtest(df, strategy, config: Optional[BacktestConfig] = None) -> BacktestResult:
    if config is None:
        config = BacktestConfig()

    df = strategy.compute_features(df.copy())

    target = strategy.target_position(df)
    if not isinstance(target, pd.Series):
        raise TypeError("target_position(df) must return a pandas Series")
    if not target.index.equals(df.index):
        raise ValueError("target_position index must match df.index")

    target = target.fillna(0.0)

    if (target < 0).any():
        raise ValueError(
            "Short positions are not supported in Experiment 001. "
            "target_position must be 0 or +1."
        )

    target = (target > 0).astype(float)

    open_ = df["Open"].values
    close = df["Close"].values
    target_arr = target.values
    n = len(df)

    equity = config.initial_capital
    qty = 0.0

    entry_index: Optional[int] = None
    entry_price: float = 0.0
    entry_comm: float = 0.0
    entry_slip: float = 0.0

    equity_curve = np.zeros(n)
    trades: list = []

    for i in range(n):
        if i > 0:
            desired = target_arr[i - 1]

            # CLOSE
            if qty != 0.0 and desired == 0.0:
                fill = open_[i] * (1 - config.slippage)
                gross = (fill - entry_price) * qty
                exit_comm = fill * qty * config.commission
                exit_slip = (open_[i] - fill) * qty
                equity += gross - exit_comm

                trades.append(Trade(
                    entry_index=entry_index,
                    exit_index=i,
                    entry_price=entry_price,
                    exit_price=fill,
                    qty=qty,
                    gross_pnl=gross,
                    commission_paid=entry_comm + exit_comm,
                    slippage_paid=entry_slip + exit_slip,
                    net_pnl=gross - exit_comm - entry_comm,
                ))

                qty = 0.0
                entry_index = None
                entry_price = 0.0
                entry_comm = 0.0
                entry_slip = 0.0

            # OPEN
            elif qty == 0.0 and desired > 0.0:
                fill = open_[i] * (1 + config.slippage)
                notional = equity * config.position_pct
                qty = notional / fill
                entry_price = fill
                entry_index = i
                entry_comm = fill * qty * config.commission
                entry_slip = (fill - open_[i]) * qty
                equity -= entry_comm

        unrealized = (close[i] - entry_price) * qty if qty > 0 else 0.0
        equity_curve[i] = equity + unrealized

    if qty > 0:
        i = n - 1
        fill = close[i] * (1 - config.slippage)
        gross = (fill - entry_price) * qty
        exit_comm = fill * qty * config.commission
        exit_slip = (close[i] - fill) * qty
        equity += gross - exit_comm

        trades.append(Trade(
            entry_index=entry_index,
            exit_index=i,
            entry_price=entry_price,
            exit_price=fill,
            qty=qty,
            gross_pnl=gross,
            commission_paid=entry_comm + exit_comm,
            slippage_paid=entry_slip + exit_slip,
            net_pnl=gross - exit_comm - entry_comm,
        ))
        equity_curve[-1] = equity

    equity_series = pd.Series(equity_curve, index=df.index, name="equity")
    returns = equity_series.pct_change().fillna(0.0)

    std = returns.std()
    sharpe = float(returns.mean() / std * np.sqrt(6 * 365)) if std > 0 else 0.0

    net_pnl = float(equity_series.iloc[-1] - config.initial_capital)

    wins = [t.net_pnl for t in trades if t.net_pnl > 0]
    losses = [t.net_pnl for t in trades if t.net_pnl <= 0]

    gross_win = sum(wins)
    gross_loss = abs(sum(losses))
    profit_factor = float(gross_win / gross_loss) if gross_loss > 0 else float("inf")

    win_rate = float(len(wins) / len(trades)) if trades else 0.0

    running_max = equity_series.cummax()
    drawdown = (equity_series / running_max - 1.0)
    max_drawdown = float(drawdown.min())

    return BacktestResult(
        equity_curve=equity_series,
        trades=trades,
        returns=returns,
        sharpe=sharpe,
        net_pnl=net_pnl,
        profit_factor=profit_factor,
        win_rate=win_rate,
        max_drawdown=max_drawdown,
        trade_count=len(trades),
    )