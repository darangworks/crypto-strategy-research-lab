"""
RSI Mean Reversion Strategy — Experiment 001

Pre-registered in experiments/001_rsi_btc_4h/PRE_REGISTRATION.md

Parameters (fixed, no tuning):
    RSI period:        14
    Entry threshold:   30 (cross below)
    Exit threshold:    50 (cross above)

Cross semantics (strict):
    Entry: previous_rsi >= 30 and current_rsi < 30  -> +1
    Exit:  previous_rsi <= 50 and current_rsi > 50  ->  0

Signal at close of bar t. Execution at open of bar t+1
(enforced by backtest engine).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from strategies._template.strategy import Strategy, StrategyConfig


class RSIMeanReversion(Strategy):
    """RSI(14) mean reversion — flat or long only."""

    def __init__(
        self,
        rsi_period: int = 14,
        entry_threshold: float = 30.0,
        exit_threshold: float = 50.0,
    ):
        config = StrategyConfig(
            name="rsi_mean_reversion",
            version="0.1",
            params={
                "rsi_period": rsi_period,
                "entry_threshold": entry_threshold,
                "exit_threshold": exit_threshold,
            },
            experiment_type="exploratory",
        )
        super().__init__(config)

        self.rsi_period = rsi_period
        self.entry_threshold = entry_threshold
        self.exit_threshold = exit_threshold

    def hypothesis(self) -> str:
        return (
            "Extreme short-term selling (low RSI) may be followed by "
            "short-term mean reversion at the 4H timeframe on BTC-USD."
        )

    def compute_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add RSI(rsi_period) — causal, Wilder-style smoothing."""
        df = df.copy()

        delta = df["Close"].diff()
        gain = delta.clip(lower=0.0)
        loss = -delta.clip(upper=0.0)

        avg_gain = gain.ewm(
            alpha=1.0 / self.rsi_period,
            adjust=False,
            min_periods=self.rsi_period,
        ).mean()
        avg_loss = loss.ewm(
            alpha=1.0 / self.rsi_period,
            adjust=False,
            min_periods=self.rsi_period,
        ).mean()

        # Use np.nan (float) instead of pd.NA (object dtype)
        avg_loss_safe = avg_loss.where(avg_loss != 0.0, np.nan)
        rs = avg_gain / avg_loss_safe
        df["RSI"] = 100.0 - 100.0 / (1.0 + rs)

        return df

    def target_position(self, df: pd.DataFrame) -> pd.Series:
        """Return +1 when long, 0 when flat. Strict cross semantics."""
        rsi = df["RSI"].astype(float)
        prev = rsi.shift(1)

        entry = (prev >= self.entry_threshold) & (rsi < self.entry_threshold)
        exit_ = (prev <= self.exit_threshold) & (rsi > self.exit_threshold)

        target = pd.Series(index=df.index, dtype=float)
        in_position = False

        for i in range(len(df)):
            if not in_position:
                if entry.iloc[i]:
                    in_position = True
                    target.iloc[i] = 1.0
                else:
                    target.iloc[i] = 0.0
            else:
                if exit_.iloc[i]:
                    in_position = False
                    target.iloc[i] = 0.0
                else:
                    target.iloc[i] = 1.0

        return target