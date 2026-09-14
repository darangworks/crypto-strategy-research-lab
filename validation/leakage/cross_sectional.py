"""
Leakage / causality checks for cross-sectional strategies.

A1 — target-leak invariant (all assets future-perturbed)
A2 — asset-specific target-leak (one asset future-perturbed)
A3 — future-data oracle (LeakyCrossSectional via close.shift(-1))
A4 — specification check (target == explicit-tiebreak argmax)

B1 — multivariate stationary block bootstrap preserving cross-asset
     correlation and short-range temporal dependence.
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


DEFAULT_TIEBREAK = ["BTC-USD", "ETH-USD", "SOL-USD"]


# -----------------------------------------------------------------------
# Leaky variant for A3
# -----------------------------------------------------------------------
class LeakyCrossSectional(CrossSectionalMomentum):
    """Same as CrossSectionalMomentum but momentum uses close.shift(-1)."""

    def momentum(self, panel: dict) -> pd.DataFrame:
        closes = pd.DataFrame(
            {name: df["Close"] for name, df in panel.items()}
        )
        closes_leaky = closes.shift(-1)  # intentional future leak
        return np.log(closes_leaky / closes_leaky.shift(self.lookback))


# -----------------------------------------------------------------------
# A1 / A2 — target invariance under future perturbation
# -----------------------------------------------------------------------
def _perturb_future(
    panel: dict, cutoff: int, assets: list, seed: int = 20260913
) -> dict:
    """Perturb Close after `cutoff` for the given subset of assets."""
    rng = np.random.default_rng(seed)
    out = {k: v.copy() for k, v in panel.items()}
    for name in assets:
        df = out[name]
        n_future = len(df) - cutoff
        factors = rng.uniform(0.5, 1.5, size=n_future)
        df.loc[df.index[cutoff:], "Close"] = (
            df.iloc[cutoff:]["Close"].values * factors
        )
    return out


def check_target_invariance(
    panel: dict,
    cutoff: int,
    perturb_assets: list | None = None,
    strategy_factory=CrossSectionalMomentum,
    tiebreak_order: list | None = None,
) -> dict:
    """A1 (perturb_assets=None → all) / A2 (subset).

    Returns dict with n_diff over prefix [0:cutoff].
    """
    if tiebreak_order is None:
        tiebreak_order = list(panel.keys())
    if perturb_assets is None:
        perturb_assets = list(panel.keys())

    strategy = strategy_factory(
        lookback=6, tiebreak_order=tiebreak_order
    )
    target_orig = strategy.target_asset(panel)
    panel_pert = _perturb_future(panel, cutoff, perturb_assets)
    target_pert = strategy_factory(
        lookback=6, tiebreak_order=tiebreak_order
    ).target_asset(panel_pert)

    a = target_orig.iloc[:cutoff]
    b = target_pert.iloc[:cutoff]
    # NaN vs NaN counts as equal
    both_nan = a.isna() & b.isna()
    eq = (a == b) | both_nan
    n_diff = int((~eq).sum())
    return {
        "cutoff": int(cutoff),
        "perturbed_assets": list(perturb_assets),
        "n_prefix": int(cutoff),
        "n_diff": n_diff,
        "invariant": bool(n_diff == 0),
    }


# -----------------------------------------------------------------------
# A3 — future-data oracle
# -----------------------------------------------------------------------
def check_leak_detection(panel: dict, cutoff: int = 2000) -> dict:
    """Clean invariant, leaky violated, harness detects."""
    tiebreak = list(panel.keys())

    clean = CrossSectionalMomentum(lookback=6, tiebreak_order=tiebreak)
    leaky = LeakyCrossSectional(lookback=6, tiebreak_order=tiebreak)

    panel_pert = _perturb_future(panel, cutoff, tiebreak)

    clean_orig = clean.target_asset(panel)
    clean_pert = CrossSectionalMomentum(
        lookback=6, tiebreak_order=tiebreak
    ).target_asset(panel_pert)
    leaky_orig = leaky.target_asset(panel)
    leaky_pert = LeakyCrossSectional(
        lookback=6, tiebreak_order=tiebreak
    ).target_asset(panel_pert)

    def _diffs(a, b):
        a = a.iloc[:cutoff]
        b = b.iloc[:cutoff]
        both_nan = a.isna() & b.isna()
        return int((~((a == b) | both_nan)).sum())

    clean_diff = _diffs(clean_orig, clean_pert)
    leaky_diff = _diffs(leaky_orig, leaky_pert)

    clean_invariant = clean_diff == 0
    leaky_invariant = leaky_diff == 0
    leak_detected = bool(clean_invariant and not leaky_invariant)

    return {
        "cutoff": int(cutoff),
        "clean_invariant": bool(clean_invariant),
        "leaky_invariant": bool(leaky_invariant),
        "clean_n_diff": clean_diff,
        "leaky_n_diff": leaky_diff,
        "leak_detected": leak_detected,
    }


# -----------------------------------------------------------------------
# A4 — specification check
# -----------------------------------------------------------------------
def check_specification(panel: dict, tiebreak_order: list) -> dict:
    """target[t] == tiebreak argmax of momentum[t] for every valid t."""
    s = CrossSectionalMomentum(lookback=6, tiebreak_order=tiebreak_order)
    mom = s.momentum(panel)
    targets = s.target_asset(panel)

    valid = mom.notna().all(axis=1)
    mismatches = 0
    n_valid = 0
    for ts in mom.index:
        if not valid.loc[ts]:
            continue
        n_valid += 1
        row = mom.loc[ts]
        max_mom = row.max()
        tied = [a for a in tiebreak_order if np.isclose(row[a], max_mom)]
        expected = tied[0]
        if targets.loc[ts] != expected:
            mismatches += 1

    return {
        "n_valid": n_valid,
        "n_mismatch": mismatches,
        "specification_ok": mismatches == 0,
    }


# -----------------------------------------------------------------------
# B1 — multivariate block bootstrap (cross-asset + temporal dependence)
# -----------------------------------------------------------------------
def _log_return_matrix(panel: dict, assets: list) -> np.ndarray:
    """Return (T-1, n_assets) matrix of aligned log returns."""
    closes = pd.DataFrame({a: panel[a]["Close"] for a in assets})
    log_ret = np.log(closes / closes.shift(1)).dropna()
    return log_ret.values


def estimate_block_length_per_asset(
    returns: np.ndarray, max_lag: int = 200, threshold_factor: float = 2.0
) -> dict:
    """Estimate block length per column via ACF threshold.

    Returns dict: {'BTC-USD': L_b, 'ETH-USD': L_e, 'SOL-USD': L_s, 'used': L}
    where L = max of individual lengths (conservative).
    """
    n = returns.shape[0]
    threshold = threshold_factor / np.sqrt(n)
    lengths = []
    for j in range(returns.shape[1]):
        r = returns[:, j] - returns[:, j].mean()
        var = float(np.dot(r, r) / n)
        if var == 0:
            lengths.append(1)
            continue
        first_below = None
        for k in range(1, min(max_lag, n // 2) + 1):
            cov = float(np.dot(r[:-k], r[k:]) / n)
            acf_k = cov / var
            if abs(acf_k) < threshold:
                first_below = k
                break
        lengths.append(first_below if first_below is not None else 1)
    return {"lengths": lengths, "used": max(lengths), "threshold": threshold}


def multivariate_block_bootstrap(
    returns: np.ndarray, n_iter: int, block_length: int, base_seed: int
) -> np.ndarray:
    """Stationary (geometric) block bootstrap over rows of returns.

    Each resampled row is a vector [r_BTC, r_ETH, r_SOL], preserving
    cross-asset dependence at each timestamp. Blocks preserve
    short-range temporal ordering.
    """
    n, k = returns.shape
    out = np.empty((n_iter, n, k), dtype=float)
    p = 1.0 / max(block_length, 1)

    for it in range(n_iter):
        rng = np.random.default_rng(base_seed + it)
        sample = np.empty((n, k), dtype=float)
        filled = 0
        while filled < n:
            start = int(rng.integers(0, n))
            length = max(int(rng.geometric(p)), 1)
            end = min(start + length, n)
            take = min(end - start, n - filled)
            sample[filled:filled + take] = returns[start:start + take]
            filled += take
        out[it] = sample
    return out


def rebuild_prices_from_log_returns(
    s0: np.ndarray, log_returns: np.ndarray
) -> np.ndarray:
    """Given (T-1, k) log returns and initial prices (k,), return (T, k) prices."""
    T = log_returns.shape[0] + 1
    k = log_returns.shape[1]
    prices = np.empty((T, k), dtype=float)
    prices[0] = s0
    prices[1:] = s0 * np.exp(np.cumsum(log_returns, axis=0))
    return prices


def run_bootstrap_backtests(
    paths_prices: np.ndarray,
    index: pd.DatetimeIndex,
    assets: list,
    config: BacktestConfig,
    tiebreak_order: list,
    lookback: int = 6,
) -> list:
    """Run cross-sectional backtest on each simulated multi-asset panel."""
    results = []
    strategy_template = dict(lookback=lookback, tiebreak_order=tiebreak_order)

    for i in range(paths_prices.shape[0]):
        panel = {}
        for j, name in enumerate(assets):
            prices = paths_prices[i, :, j]
            panel[name] = pd.DataFrame(
                {
                    "Open": prices, "High": prices, "Low": prices,
                    "Close": prices, "Volume": 0.0,
                },
                index=index,
            )
        strategy = CrossSectionalMomentum(**strategy_template)
        r = run_cross_sectional_backtest(panel, strategy, config)
        results.append({
            "net_pnl": float(r.net_pnl),
            "sharpe": float(r.sharpe),
            "profit_factor": float(r.profit_factor),
            "win_rate": float(r.win_rate),
            "max_drawdown": float(r.max_drawdown),
            "trade_count": int(r.trade_count),
        })
    return results


def summarize(results: list) -> dict:
    if not results:
        return {}

    def _arr(k):
        return np.array([r[k] for r in results], dtype=float)

    def _stats(a):
        return {
            "mean": float(np.mean(a)),
            "median": float(np.median(a)),
            "p2_5": float(np.percentile(a, 2.5)),
            "p97_5": float(np.percentile(a, 97.5)),
            "min": float(np.min(a)),
            "max": float(np.max(a)),
        }

    sharpe = _arr("sharpe")
    net_pnl = _arr("net_pnl")
    trades = _arr("trade_count")

    return {
        "n_paths": len(results),
        "sharpe": {**_stats(sharpe), "frac_positive": float(np.mean(sharpe > 0))},
        "net_pnl": {**_stats(net_pnl), "frac_positive": float(np.mean(net_pnl > 0))},
        "trade_count": _stats(trades),
    }