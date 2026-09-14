"""
Read-only audit of B1 null specification.

Answers:
- Are returns centered before resampling?
- What is the mean of source log returns per asset?
- What is the mean of resampled path returns?
"""
from __future__ import annotations
import sys
from pathlib import Path
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import numpy as np
import pandas as pd

from validation.leakage.cross_sectional import (
    _log_return_matrix,
    multivariate_block_bootstrap,
)

DATA_DIR = REPO_ROOT / "data" / "002_btc_eth_sol_4h"
ASSETS = ["BTC-USD", "ETH-USD", "SOL-USD"]

panel = {}
for sym in ASSETS:
    df = pd.read_csv(DATA_DIR / f"{sym}_4h.csv", index_col=0, parse_dates=True)
    df.index = pd.to_datetime(df.index, utc=True)
    panel[sym] = df

rets = _log_return_matrix(panel, ASSETS)

print("Source log-return matrix:")
print(f"  shape: {rets.shape}")
print(f"  per-asset mean: {rets.mean(axis=0)}")
print(f"  per-asset std:  {rets.std(axis=0)}")

paths = multivariate_block_bootstrap(rets, n_iter=1, block_length=1, base_seed=20260913)
print(f"\nResampled path (seed=20260913):")
print(f"  shape: {paths.shape}")
print(f"  per-asset mean: {paths[0].mean(axis=0)}")
print(f"  per-asset std:  {paths[0].std(axis=0)}")

diff_mean = np.abs(paths[0].mean(axis=0) - rets.mean(axis=0))
print(f"\n|resampled mean - source mean| per asset: {diff_mean}")
print(f"\nConclusion: returns {'are NOT centered' if diff_mean.max() > 1e-4 else 'are centered'} before resampling")