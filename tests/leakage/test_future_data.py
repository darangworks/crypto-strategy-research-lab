from pathlib import Path

import pytest

from engine.data_loader import load_frozen
from validation.leakage.future_data_oracle import check_leak_detection

DATA_FILE = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "001_btc_4h"
    / "BTC-USD_4h.csv"
)


@pytest.fixture(scope="module")
def frozen_df():
    return load_frozen(DATA_FILE)


def test_clean_pipeline_is_invariant(frozen_df):
    result = check_leak_detection(frozen_df, cutoff=2000)
    assert result["clean_invariant"] is True, (
        f"clean pipeline not invariant: {result}"
    )


def test_leaky_pipeline_violates_invariance(frozen_df):
    result = check_leak_detection(frozen_df, cutoff=2000)
    assert result["leaky_invariant"] is False, (
        f"leaky pipeline unexpectedly invariant: {result}"
    )


def test_harness_detects_intentional_leak(frozen_df):
    result = check_leak_detection(frozen_df, cutoff=2000)
    assert result["leak_detected"] is True, (
        f"harness failed to detect intentional leak: {result}"
    )
