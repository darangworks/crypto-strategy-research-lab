"""A1 — Target-leak perturbation check (multi-cutoff).

Invariant: changes to any FUTURE data must not change PAST signals.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from strategies.rsi_mean_reversion.strategy import RSIMeanReversion


DEFAULT_CUTOFFS = [500, 1000, 2000, 3000]
PERTURB_SEED = 20260913


def _perturb_future(df: pd.DataFrame, cutoff: int, seed: int) -> pd.DataFrame:
    """Multiply Close after `cutoff` by a large random factor."""
    df = df.copy()
    rng = np.random.default_rng(seed)
    n_future = len(df) - cutoff
    factors = rng.uniform(0.5, 1.5, size=n_future)
    df.loc[df.index[cutoff:], "Close"] = (
        df.iloc[cutoff:]["Close"].values * factors
    )
    return df


def check_invariance(
    df: pd.DataFrame,
    cutoff: int,
    seed: int = PERTURB_SEED,
    strategy_factory=RSIMeanReversion,
) -> dict:
    """Check if target prefix [:cutoff] is invariant under future perturbation."""
    strategy = strategy_factory()
    df_perturbed = _perturb_future(df, cutoff, seed)

    target_orig = strategy.target_position(strategy.compute_features(df.copy()))
    target_pert = strategy.target_position(strategy.compute_features(df_perturbed))

    prefix_orig = target_orig.iloc[:cutoff]
    prefix_pert = target_pert.iloc[:cutoff]
    diff = int((prefix_orig != prefix_pert).sum())

    return {
        "cutoff": int(cutoff),
        "invariant": bool(diff == 0),
        "n_diff": diff,
        "n_prefix": int(cutoff),
    }


def run_all_cutoffs(
    df: pd.DataFrame,
    cutoffs=None,
    strategy_factory=RSIMeanReversion,
) -> list:
    if cutoffs is None:
        cutoffs = DEFAULT_CUTOFFS
    return [
        check_invariance(df, c, strategy_factory=strategy_factory)
        for c in cutoffs
    ]
