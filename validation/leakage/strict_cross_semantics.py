"""A2 — Strict cross semantics verification.

Verify RSIMeanReversion matches pre-registered spec:
  Entry: prev RSI >= 30 AND curr RSI < 30
  Exit:  prev RSI <= 50 AND curr RSI > 50

Deterministic. No performance dependency.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from strategies.rsi_mean_reversion.strategy import RSIMeanReversion


def run_semantics_case(
    rsi_values: list,
    entry_threshold: float = 30.0,
    exit_threshold: float = 50.0,
) -> list:
    """Return target_position result for a given RSI sequence."""
    strategy = RSIMeanReversion(
        rsi_period=14,
        entry_threshold=entry_threshold,
        exit_threshold=exit_threshold,
    )
    df = pd.DataFrame({"RSI": rsi_values})
    target = strategy.target_position(df)
    return [float(x) for x in target.tolist()]


# (rsi_sequence, expected_target, description)
CASES = [
    # --- NaN warm-up ---
    ([np.nan, np.nan], [0.0, 0.0], "NaN -> NaN: no event"),
    ([np.nan, 29.0], [0.0, 0.0], "NaN -> 29: no entry"),
    ([np.nan, 31.0], [0.0, 0.0], "NaN -> 31: no entry"),
    ([np.nan, 50.0], [0.0, 0.0], "NaN -> 50: no exit"),
    ([np.nan, 30.0], [0.0, 0.0], "NaN -> 30: no entry"),

    # --- entry cases ---
    ([31.0, 29.0], [0.0, 1.0], "31 -> 29: ENTRY"),
    ([30.0, 29.0], [0.0, 1.0], "30 -> 29: ENTRY (boundary)"),
    ([29.0, 28.0], [0.0, 0.0], "29 -> 28: no ENTRY (no cross)"),
    ([29.0, 30.0], [0.0, 0.0], "29 -> 30: no ENTRY (reverse cross)"),
    ([30.0, 30.0], [0.0, 0.0], "30 -> 30: no ENTRY (no change)"),

    # --- exit cases (entry first) ---
    ([31.0, 29.0, 51.0], [0.0, 1.0, 0.0], "entry then 29->51: EXIT"),
    ([31.0, 29.0, 50.0], [0.0, 1.0, 1.0], "entry then 29->50: no EXIT (needs >50)"),
    ([31.0, 29.0, 50.0, 51.0], [0.0, 1.0, 1.0, 0.0], "entry then 50->51: EXIT"),
    ([31.0, 29.0, 48.0, 51.0], [0.0, 1.0, 1.0, 0.0], "entry then 48->51: EXIT"),

    # --- no new events after exit ---
    ([31.0, 29.0, 48.0, 51.0, 55.0],
     [0.0, 1.0, 1.0, 0.0, 0.0],
     "after EXIT, 51->55: no new exit (already flat)"),

    # --- NaN after position ---
    ([31.0, 29.0, np.nan], [0.0, 1.0, 1.0], "in position then NaN: no EXIT"),
    ([31.0, 29.0, 48.0, np.nan], [0.0, 1.0, 1.0, 1.0], "in position then NaN: no EXIT"),
]
