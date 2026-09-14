"""Leakage tests for Experiment 002 cross-sectional momentum."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from validation.leakage.cross_sectional import (
    check_leak_detection,
    check_specification,
    check_target_invariance,
    estimate_block_length_per_asset,
    multivariate_block_bootstrap,
    rebuild_prices_from_log_returns,
)


TIEBREAK = ["BTC-USD", "ETH-USD", "SOL-USD"]


def _make_panel(n: int = 500, seed: int = 42) -> dict:
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2024-01-01", periods=n, freq="4h", tz="UTC")
    # correlated returns: BTC drives ETH & SOL partially
    btc = rng.normal(0, 0.005, n)
    eth = 0.6 * btc + rng.normal(0, 0.004, n)
    sol = 0.5 * btc + rng.normal(0, 0.006, n)
    panel = {}
    for name, ret in [("BTC-USD", btc), ("ETH-USD", eth), ("SOL-USD", sol)]:
        closes = 100.0 * np.exp(np.cumsum(ret))
        panel[name] = pd.DataFrame(
            {
                "Open":   closes, "High": closes, "Low": closes,
                "Close":  closes, "Volume": 0.0,
            },
            index=idx,
        )
    return panel


# -----------------------------------------------------------------------
# A1 — target invariance, all assets perturbed
# -----------------------------------------------------------------------
@pytest.mark.parametrize("cutoff", [100, 200, 300])
def test_a1_all_asset_perturbation_invariant(cutoff):
    panel = _make_panel(500)
    res = check_target_invariance(panel, cutoff, perturb_assets=None,
                                   tiebreak_order=TIEBREAK)
    assert res["invariant"] is True, res


# -----------------------------------------------------------------------
# A2 — target invariance, single asset perturbed
# -----------------------------------------------------------------------
@pytest.mark.parametrize("asset", TIEBREAK)
def test_a2_single_asset_perturbation_invariant(asset):
    panel = _make_panel(500)
    res = check_target_invariance(
        panel, cutoff=250, perturb_assets=[asset], tiebreak_order=TIEBREAK
    )
    assert res["invariant"] is True, res


# -----------------------------------------------------------------------
# A3 — future-data oracle
# -----------------------------------------------------------------------
def test_a3_clean_invariant_leaky_violated():
    panel = _make_panel(800, seed=7)
    res = check_leak_detection(panel, cutoff=400)
    assert res["clean_invariant"] is True, res
    assert res["leaky_invariant"] is False, res
    assert res["leak_detected"] is True, res


# -----------------------------------------------------------------------
# A4 — specification
# -----------------------------------------------------------------------
def test_a4_specification_holds():
    panel = _make_panel(500)
    res = check_specification(panel, tiebreak_order=TIEBREAK)
    assert res["specification_ok"] is True, res
    assert res["n_mismatch"] == 0
    assert res["n_valid"] > 0


# -----------------------------------------------------------------------
# B1 — multivariate block bootstrap core
# -----------------------------------------------------------------------
def test_b1_block_length_estimator_returns_dict():
    rng = np.random.default_rng(0)
    rets = rng.normal(0, 0.01, (1000, 3))
    res = estimate_block_length_per_asset(rets)
    assert "lengths" in res and "used" in res
    assert len(res["lengths"]) == 3
    assert res["used"] >= 1


def test_b1_bootstrap_preserves_shape():
    rng = np.random.default_rng(1)
    rets = rng.normal(0, 0.01, (500, 3))
    paths = multivariate_block_bootstrap(
        rets, n_iter=10, block_length=1, base_seed=20260913
    )
    assert paths.shape == (10, 500, 3)


def test_b1_bootstrap_preserves_cross_asset_correlation():
    """Row-wise resampling must preserve correlation between columns."""
    rng = np.random.default_rng(2)
    n = 3000
    base = rng.normal(0, 0.01, n)
    a = base + rng.normal(0, 0.001, n)
    b = 0.9 * base + rng.normal(0, 0.001, n)
    c = -0.5 * base + rng.normal(0, 0.001, n)
    rets = np.column_stack([a, b, c])
    true_corr = np.corrcoef(rets, rowvar=False)

    paths = multivariate_block_bootstrap(
        rets, n_iter=50, block_length=1, base_seed=20260913
    )
    # Average empirical correlation across simulated paths
    corrs = np.array([np.corrcoef(p, rowvar=False) for p in paths])
    mean_corr = corrs.mean(axis=0)

    # Should be close to the source correlation (within ~0.1)
    assert np.allclose(mean_corr, true_corr, atol=0.15), (
        f"cross-asset correlation not preserved:\n"
        f"true:\n{true_corr}\nmean:\n{mean_corr}"
    )


def test_b1_rebuild_prices_shape():
    s0 = np.array([100.0, 50.0, 20.0])
    lr = np.zeros((10, 3))
    prices = rebuild_prices_from_log_returns(s0, lr)
    assert prices.shape == (11, 3)
    assert np.allclose(prices[0], s0)
    assert np.allclose(prices, s0)  # zero returns → constant