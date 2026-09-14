"""
Experiment 001 — Step 4: Bootstrap uncertainty of baseline returns.

Pre-registration : experiments/001_rsi_btc_4h/PRE_REGISTRATION.md
Frozen baseline  : tag exp-001-baseline (commit ccf28ac)

Purpose:
    Quantify uncertainty of the observed baseline mean-4H-return
    under a stationary block bootstrap. NOT a rescue attempt
    for the failed walk-forward.

Spec (per evaluator):
  - statistic: mean 4H portfolio return
  - stationary block bootstrap (Politis-Romano)
  - block length estimated from ACF
  - 2000 iterations
  - 95% CI
  - fixed seed 20260913
  - frozen baseline returns (no re-simulation of strategy)

Decision rule (pre-registered):
  CI entirely > 0   -> PASS
  CI includes 0     -> INCONCLUSIVE
  CI entirely < 0   -> FAIL
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from engine.data_loader import load_frozen  # noqa: E402
from engine.backtest import BacktestConfig, run_backtest  # noqa: E402
from strategies.rsi_mean_reversion.strategy import RSIMeanReversion  # noqa: E402


EXPERIMENT_DIR = Path(__file__).resolve().parent
RESULTS_JSON = EXPERIMENT_DIR / "bootstrap.json"
DIST_CSV = EXPERIMENT_DIR / "bootstrap_distribution.csv"
DATA_FILE = REPO_ROOT / "data" / "001_btc_4h" / "BTC-USD_4h.csv"

N_ITER = 2000
CI_LEVEL = 0.95
SEED = 20260913
ACF_MAX_LAG = 200
ACF_THRESHOLD_FACTOR = 2.0   # threshold = factor / sqrt(n)

STRATEGY_ARGS = {"rsi_period": 14, "entry_threshold": 30.0, "exit_threshold": 50.0}
BACKTEST_CONFIG = BacktestConfig(
    initial_capital=100_000.0,
    position_pct=0.10,
    commission=0.0005,
    slippage=0.0002,
)


def _git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=REPO_ROOT, stderr=subprocess.DEVNULL,
        ).decode().strip()
    except Exception:
        return "UNKNOWN"


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def estimate_block_length(returns: np.ndarray, max_lag: int, threshold_factor: float) -> dict:
    """Estimate block length from ACF.

    Rule: first lag at which |ACF| < threshold_factor / sqrt(n).
    Falls back to lag=1 if no such lag exists.
    """
    n = len(returns)
    r = returns - returns.mean()
    var = float(np.dot(r, r) / n)
    if var == 0.0:
        return {"block_length": 1, "acf_first_below": None, "threshold": 0.0}

    acfs = []
    for k in range(1, min(max_lag, n // 2) + 1):
        cov = float(np.dot(r[:-k], r[k:]) / n)
        acfs.append(cov / var)
    acfs = np.asarray(acfs)

    threshold = threshold_factor / np.sqrt(n)
    below = np.where(np.abs(acfs) < threshold)[0]
    if len(below) == 0:
        block_length = 1
        first_below = None
    else:
        block_length = int(below[0] + 1)  # +1 because acfs[0] corresponds to lag 1
        first_below = int(below[0] + 1)

    return {
        "block_length": block_length,
        "acf_first_below": first_below,
        "threshold": float(threshold),
        "acf_lag1": float(acfs[0]) if len(acfs) else None,
    }


def stationary_block_bootstrap(
    returns: np.ndarray,
    n_iter: int,
    block_length: int,
    seed: int,
) -> np.ndarray:
    """Politis-Romano stationary block bootstrap of the mean."""
    n = len(returns)
    rng = np.random.default_rng(seed)
    p = 1.0 / max(block_length, 1)
    means = np.empty(n_iter, dtype=float)

    for it in range(n_iter):
        sample = np.empty(n, dtype=float)
        filled = 0
        while filled < n:
            start = int(rng.integers(0, n))
            # geometric block length with mean = block_length
            length = int(rng.geometric(p))
            length = max(length, 1)
            end = min(start + length, n)
            take = end - start
            remain = n - filled
            if take > remain:
                take = remain
            sample[filled:filled + take] = returns[start:start + take]
            filled += take
        means[it] = sample.mean()
    return means


def _ci(samples: np.ndarray, level: float) -> tuple:
    alpha = 1.0 - level
    lo = float(np.quantile(samples, alpha / 2.0))
    hi = float(np.quantile(samples, 1.0 - alpha / 2.0))
    return lo, hi


def _verdict(lo: float, hi: float) -> str:
    if lo > 0.0:
        return "PASS"
    if hi < 0.0:
        return "FAIL"
    return "INCONCLUSIVE"


def main() -> int:
    print("=" * 68)
    print("EXPERIMENT 001 — STEP 4 BOOTSTRAP (stationary block)")
    print("=" * 68)

    # 1. Load frozen data + run baseline backtest to get returns
    print(f"\n[1/5] load_frozen({DATA_FILE.name})")
    df = load_frozen(DATA_FILE)
    print(f"      rows = {len(df)}")

    print("\n[2/5] run baseline backtest (frozen spec)")
    strategy = RSIMeanReversion(**STRATEGY_ARGS)
    result = run_backtest(df, strategy, BACKTEST_CONFIG)
    returns = result.returns.to_numpy(dtype=float)
    returns = returns[np.isfinite(returns)]
    n_ret = len(returns)
    observed_mean = float(returns.mean())
    print(f"      finite returns = {n_ret}")
    print(f"      observed mean  = {observed_mean:.10f}")

    # 2. Estimate block length from ACF
    print("\n[3/5] estimate block length from ACF")
    bl = estimate_block_length(returns, ACF_MAX_LAG, ACF_THRESHOLD_FACTOR)
    print(f"      block_length = {bl['block_length']}")
    print(f"      acf_lag1     = {bl['acf_lag1']}")
    print(f"      threshold    = {bl['threshold']}")

    # 3. Bootstrap
    print(f"\n[4/5] stationary block bootstrap: {N_ITER} iterations, seed={SEED}")
    boot_means = stationary_block_bootstrap(
        returns, n_iter=N_ITER, block_length=bl["block_length"], seed=SEED,
    )
    lo, hi = _ci(boot_means, CI_LEVEL)
    verdict = _verdict(lo, hi)
    print(f"      observed mean : {observed_mean:.10f}")
    print(f"      95% CI        : [{lo:.10f}, {hi:.10f}]")
    print(f"      verdict       : {verdict}")

    # 4. Save
    print(f"\n[5/5] writing artifacts -> {EXPERIMENT_DIR.name}/")

    summary = {
        "experiment_id": "001_rsi_btc_4h",
        "step": "bootstrap",
        "status": "BOOTSTRAP_COMPLETE",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "schema_version": "1.0",

        "provenance": {
            "git_commit": _git_commit(),
            "python_version": sys.version.split()[0],
            "numpy_version": np.__version__,
            "pandas_version": pd.__version__,
            "data_sha256": _sha256_file(DATA_FILE) if DATA_FILE.exists() else None,
        },

        "spec": {
            "statistic": "mean_4h_portfolio_return",
            "method": "stationary_block_bootstrap",
            "n_iter": N_ITER,
            "ci_level": CI_LEVEL,
            "seed": SEED,
            "acf_max_lag": ACF_MAX_LAG,
            "acf_threshold_factor": ACF_THRESHOLD_FACTOR,
        },

        "inputs": {
            "n_returns": int(n_ret),
            "observed_mean": observed_mean,
        },

        "block_length_estimation": bl,
        "distribution": {
            "mean_of_means": float(boot_means.mean()),
            "std_of_means": float(boot_means.std(ddof=1)),
            "q025": float(np.quantile(boot_means, 0.025)),
            "q975": float(np.quantile(boot_means, 0.975)),
        },

        "decision": {
            "criterion": "CI entirely > 0 PASS; includes 0 INCONCLUSIVE; entirely < 0 FAIL",
            "ci_low": lo,
            "ci_high": hi,
            "verdict": verdict,
            "note": "Bootstrap quantifies uncertainty of baseline; cannot rescue WFO FAIL.",
        },
    }

    RESULTS_JSON.write_text(json.dumps(summary, indent=2, default=str))
    pd.DataFrame({"boot_mean": boot_means}).to_csv(DIST_CSV, index=False)

    print(f"      -> {RESULTS_JSON.name}")
    print(f"      -> {DIST_CSV.name}  ({len(boot_means)} rows)")

    print("\n" + "-" * 68)
    print("BOOTSTRAP RESULT")
    print("-" * 68)
    print(f"  observed mean : {observed_mean:.10f}")
    print(f"  95% CI        : [{lo:.10f}, {hi:.10f}]")
    print(f"  VERDICT       : {verdict}")
    print("-" * 68)
    print("Bootstrap != rescue. WFO FAIL remains frozen.")
    print("=" * 68)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
