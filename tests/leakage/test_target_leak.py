from pathlib import Path

import pytest

from engine.data_loader import load_frozen
from validation.leakage.target_leak_check import DEFAULT_CUTOFFS, check_invariance

DATA_FILE = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "001_btc_4h"
    / "BTC-USD_4h.csv"
)


@pytest.fixture(scope="module")
def frozen_df():
    return load_frozen(DATA_FILE)


@pytest.mark.parametrize("cutoff", DEFAULT_CUTOFFS)
def test_target_prefix_invariant(frozen_df, cutoff):
    result = check_invariance(frozen_df, cutoff)
    assert result["invariant"] is True, (
        f"prefix[:{cutoff}] changed under future perturbation: "
        f"{result['n_diff']} diffs"
    )
