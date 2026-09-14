"""A3 — Future-data oracle.

Leaky variant intentionally uses close.shift(-1) in compute_features.
Harness PASS = leak detected (invariance violated in leaky, holds in clean).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from strategies.rsi_mean_reversion.strategy import RSIMeanReversion
from validation.leakage.target_leak_check import _perturb_future


class LeakyRSI(RSIMeanReversion):
    """Same as RSI but compute_features uses close.shift(-1) (leak)."""

    def compute_features(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df["Close"] = df["Close"].shift(-1)  # intentional future leak
        return super().compute_features(df)


def _target_from_strategy(strategy, df: pd.DataFrame) -> pd.Series:
    return strategy.target_position(strategy.compute_features(df.copy()))


def check_leak_detection(
    df: pd.DataFrame,
    cutoff: int = 2000,
    seed: int = 20260913,
) -> dict:
    """Verify harness distinguishes clean vs leaky pipeline.

    Clean pipeline:    invariance HOLDS under future perturbation.
    Leaky pipeline:    invariance VIOLATED under future perturbation.
    Harness PASS       = leak detected in leaky pipeline.
    """
    df_perturbed = _perturb_future(df, cutoff, seed)

    clean = RSIMeanReversion()
    leaky = LeakyRSI()

    clean_orig = _target_from_strategy(clean, df)
    clean_pert = _target_from_strategy(clean, df_perturbed)
    leaky_orig = _target_from_strategy(leaky, df)
    leaky_pert = _target_from_strategy(leaky, df_perturbed)

    clean_diff = int((clean_orig.iloc[:cutoff] != clean_pert.iloc[:cutoff]).sum())
    leaky_diff = int((leaky_orig.iloc[:cutoff] != leaky_pert.iloc[:cutoff]).sum())

    clean_invariant = bool(clean_diff == 0)
    leaky_invariant = bool(leaky_diff == 0)
    leak_detected = bool(clean_invariant and not leaky_invariant)

    return {
        "cutoff": int(cutoff),
        "clean_invariant": clean_invariant,
        "leaky_invariant": leaky_invariant,
        "clean_n_diff": clean_diff,
        "leaky_n_diff": leaky_diff,
        "leak_detected": leak_detected,
    }
