"""
Cross-sectional momentum strategy.

For each bar t:
    momentum[t, asset] = log( Close[t, asset] / Close[t-6, asset] )
    top asset at t = argmax over assets (descending momentum)
    tiebreak by explicit tiebreak_order list

The signal at close of bar t determines the target asset to be held
during bar t+1 (executed at open of t+1 by the runner).

Causality invariant:
    target_asset[t] depends only on closes up to and including bar t.

Tiebreak invariant:
    The winning asset when momentums are tied follows tiebreak_order
    ONLY, independent of the column order of the input panel.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class StrategyConfig:
    name: str
    version: str
    params: dict
    experiment_type: str


class CrossSectionalMomentum:
    """Cross-sectional momentum over a fixed universe."""

    def __init__(
        self,
        lookback: int = 6,
        tiebreak_order: list | None = None,
    ):
        if tiebreak_order is None or len(tiebreak_order) == 0:
            raise ValueError(
                "tiebreak_order is required and must be explicit, "
                "e.g. ['BTC-USD', 'ETH-USD', 'SOL-USD']. "
                "Implicit column-order tiebreaks are not permitted."
            )

        self.lookback = int(lookback)
        self.tiebreak_order = list(tiebreak_order)

        self.config = StrategyConfig(
            name="cross_sectional_momentum",
            version="0.1",
            params={
                "lookback": self.lookback,
                "tiebreak_order": self.tiebreak_order,
            },
            experiment_type="exploratory",
        )

    def hypothesis(self) -> str:
        return (
            "Assets with stronger recent relative performance continue "
            "to outperform the weaker ones over the next short horizon."
        )

    # ------------------------------------------------------------------
    # Cross-sectional primitives
    # ------------------------------------------------------------------
    def momentum(self, panel: dict) -> pd.DataFrame:
        """Return DataFrame (index=time, columns=assets) of log momentum."""
        closes = self._closes(panel)
        return np.log(closes / closes.shift(self.lookback))

    def ranks(self, panel: dict) -> pd.DataFrame:
        """Return descending ranks per bar (1 = highest momentum)."""
        mom = self.momentum(panel)
        return mom.rank(axis=1, ascending=False, method="min")

    def target_asset(self, panel: dict) -> pd.Series:
        """Return Series of asset names (or NaN during warmup).

        Tiebreak is resolved by tiebreak_order only. Column order of
        the input panel does not affect the result.
        """
        mom = self.momentum(panel)
        ordered_cols = self._ordered_columns(mom.columns)
        mom = mom[ordered_cols]

        valid_mask = mom.notna().all(axis=1)
        mom_valid = mom[valid_mask]

        if len(mom_valid) == 0:
            return pd.Series(index=mom.index, dtype=object)

        # idxmax returns the first occurrence of the maximum.
        # After column reordering above, "first occurrence" is exactly
        # the earliest asset in tiebreak_order that shares the max.
        targets = mom_valid.idxmax(axis=1)
        targets = targets.reindex(mom.index)
        return targets

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _closes(panel: dict) -> pd.DataFrame:
        return pd.DataFrame({name: df["Close"] for name, df in panel.items()})

    def _ordered_columns(self, columns) -> list:
        """Order columns strictly by tiebreak_order.

        Assets not present in tiebreak_order are appended at the end in
        alphabetical order. This makes the tiebreak independent of the
        input panel's column order.
        """
        present = list(columns)
        ordered = [c for c in self.tiebreak_order if c in present]
        extra = sorted(c for c in present if c not in ordered)
        return ordered + extra