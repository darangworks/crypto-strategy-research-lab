"""
Experiment 002 — Step 4: Bootstrap (stationary block).

Pre-registration : PRE_REGISTRATION.md
WFO runner commit: c8eb699
WFO artifacts:     64cab28

Purpose:
  Quantify uncertainty of the observed OOS statistics under a
  stationary block bootstrap. NOT a rescue attempt for WFO.

Two independent layers:
  Strategy layer:    OOS portfolio-return series -> mean return + Sharpe
  Predictive layer:  OOS spread series -> mean spread

Pre-registered bootstrap criterion (per PRE_REGISTRATION.md):
  CI entirely > 0 -> PASS; includes 0 -> INCONCLUSIVE; entirely < 0 -> FAIL

Block length: ACF-based rule (2 / sqrt(n)); no tuning.
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

import numpy as np
import pandas as pd

from strategies.cross_sectional_momentum.strategy import CrossSectionalMomentum


EXPERIMENT_DIR = Path(__file__).resolve().parent
DATA_DIR = REPO_ROOT / "data" / "002_btc_eth_sol_4h"
MANIFEST_FILE = DATA_DIR / "MANIFEST.md"

WF_JSON = EXPERIMENT_DIR / "walkforward.json"
OOS_EQUITY_CSV = EXPERIMENT_DIR / "walkforward_oos_equity.csv"

RESULTS_JSON = EXPERIMENT_DIR / "bootstrap.json"
RETURNS_CSV = EXPERIMENT_DIR / "bootstrap_returns.csv"
SPREAD_CSV = EXPERIMENT_DIR / "bootstrap_spread.csv"

ASSETS = ["BTC-USD", "ETH-USD", "SOL-USD"]
ASSET_FILES = {a: DATA_DIR / f"{a}_4h.csv" for a in ASSETS}
TIEBREAK = list(ASSETS)

SPLIT_INDEX = 2167
WARMUP_BARS = 6
LOOKBACK = 6

N_ITER = 2000
CI_LEVEL = 0.95
BASE_SEED = 20260913
ACF_MAX_LAG = 200
ACF_THRESHOLD_FACTOR = 2.0


# --- provenance ---------------------------------------------------------
def _git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=REPO_ROOT, stderr=subprocess.DEVNULL,
        ).decode().strip()
    except Exception:
        return "UNKNOWN"


def _git_is_dirty() -> bool:
    try:
        out = subprocess.check_output(
            ["git", "status", "--porcelain"],
            cwd=REPO_ROOT, stderr=subprocess.DEVNULL,
        )
        return bool(out.decode().strip())
    except Exception:
        return True


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# --- data loading -------------------------------------------------------
def load_manifest_hashes() -> dict:
    hashes = {}
    for line in MANIFEST_FILE.read_text(encoding="utf-8").splitlines():
        if not line.strip().startswith("|"):
            continue
        parts = [p.strip() for p in line.strip().strip("|").split("|")]
        if len(parts) < 3 or parts[0] not in ASSET_FILES:
            continue
        cand = parts[-1].strip("`").strip()
        if len(cand) == 64 and all(c in "0123456789abcdef" for c in cand.lower()):
            hashes[parts[0]] = cand.lower()
    return hashes


def load_panel() -> dict:
    expected = load_manifest_hashes()
    panel = {}
    for sym in ASSETS:
        path = ASSET_FILES[sym]
        actual = _sha256_file(path)
        if actual != expected.get(sym):
            raise RuntimeError(f"[{sym}] SHA-256 mismatch")
        df = pd.read_csv(path, index_col=0, parse_dates=True)
        df.index = pd.to_datetime(df.index, utc=True)
        panel[sym] = df
    return panel


# --- block length estimation (1D) ---------------------------------------
def estimate_block_length_1d(series: np.ndarray,
                              max_lag: int = ACF_MAX_LAG,
                              threshold_factor: float = ACF_THRESHOLD_FACTOR) -> dict:
    n = len(series)
    r = series - series.mean()
    var = float(np.dot(r, r) / n)
    if var == 0.0:
        return {"block_length": 1, "first_below": None, "threshold": 0.0}
    threshold = threshold_factor / np.sqrt(n)
    first_below = None
    for k in range(1, min(max_lag, n // 2) + 1):
        cov = float(np.dot(r[:-k], r[k:]) / n)
        if abs(cov / var) < threshold:
            first_below = k
            break
    return {
        "block_length": int(first_below) if first_below else 1,
        "first_below": first_below,
        "threshold": float(threshold),
    }


# --- stationary block bootstrap (1D mean) ------------------------------
def block_bootstrap_means(series: np.ndarray, n_iter: int,
                           block_length: int, base_seed: int) -> np.ndarray:
    n = len(series)
    p = 1.0 / max(block_length, 1)
    out = np.empty(n_iter, dtype=float)
    for it in range(n_iter):
        rng = np.random.default_rng(base_seed + it)
        sample = np.empty(n, dtype=float)
        filled = 0
        while filled < n:
            start = int(rng.integers(0, n))
            length = max(int(rng.geometric(p)), 1)
            end = min(start + length, n)
            take = min(end - start, n - filled)
            sample[filled:filled + take] = series[start:start + take]
            filled += take
        out[it] = sample.mean()
    return out


def block_bootstrap_sharpe(series: np.ndarray, n_iter: int,
                            block_length: int, base_seed: int,
                            ann_factor: float) -> np.ndarray:
    n = len(series)
    p = 1.0 / max(block_length, 1)
    out = np.empty(n_iter, dtype=float)
    for it in range(n_iter):
        rng = np.random.default_rng(base_seed + it)
        sample = np.empty(n, dtype=float)
        filled = 0
        while filled < n:
            start = int(rng.integers(0, n))
            length = max(int(rng.geometric(p)), 1)
            end = min(start + length, n)
            take = min(end - start, n - filled)
            sample[filled:filled + take] = series[start:start + take]
            filled += take
        s = sample.std(ddof=1)
        out[it] = (sample.mean() / s * ann_factor) if s > 0 else 0.0
    return out


def ann_factor_from_index(index: pd.DatetimeIndex) -> float:
    if len(index) < 2:
        return 1.0
    secs = (index[-1] - index[0]).total_seconds()
    if secs <= 0:
        return 1.0
    sec_per_bar = secs / (len(index) - 1)
    bars_per_year = 365.25 * 24 * 3600 / sec_per_bar
    return float(np.sqrt(bars_per_year))


# --- spread series reconstruction --------------------------------------
class _PrecomputedTargets:
    def __init__(self, targets):
        self._t = targets

    def target_asset(self, panel):
        idx = next(iter(panel.values())).index
        return self._t.reindex(idx)


def reconstruct_oos_spread_series(panel_full: dict) -> pd.Series:
    """Reproduce the OOS spread series: top/bottom at close[t] -> next-bar
    log return difference."""
    index_full = panel_full[ASSETS[0]].index
    warm_start = SPLIT_INDEX - WARMUP_BARS
    panel_warm = {a: panel_full[a].iloc[warm_start:].copy() for a in ASSETS}
    strat_warm = CrossSectionalMomentum(lookback=LOOKBACK, tiebreak_order=TIEBREAK)
    mom = strat_warm.momentum(panel_warm)

    closes = {a: panel_full[a]["Close"] for a in ASSETS}
    all_ts = index_full
    pos_map = {ts: i for i, ts in enumerate(all_ts)}

    spreads = {}
    for t in index_full[SPLIT_INDEX:len(index_full) - 1]:
        if t not in mom.index:
            continue
        mrow = mom.loc[t]
        if mrow.isna().any():
            continue
        pos_t = pos_map.get(t)
        if pos_t is None or pos_t + 1 >= len(all_ts):
            continue
        t_next = all_ts[pos_t + 1]

        top = next(a for a in TIEBREAK
                   if np.isclose(mrow[a], mrow.max()))
        bottom = next(a for a in reversed(TIEBREAK)
                      if np.isclose(mrow[a], mrow.min()))
        r_top = float(np.log(closes[top].loc[t_next] / closes[top].loc[t]))
        r_bot = float(np.log(closes[bottom].loc[t_next] / closes[bottom].loc[t]))
        spreads[t] = r_top - r_bot
    s = pd.Series(spreads)
    s.index = pd.to_datetime(s.index, utc=True)
    s = s.sort_index()
    s.name = "spread"
    return s


# --- CI / p-value helpers ----------------------------------------------
def _ci(samples: np.ndarray, level: float) -> tuple:
    a = (1.0 - level) / 2.0
    return float(np.quantile(samples, a)), float(np.quantile(samples, 1.0 - a))


def _verdict(lo: float, hi: float) -> str:
    if lo > 0.0:
        return "PASS"
    if hi < 0.0:
        return "FAIL"
    return "INCONCLUSIVE"


def _p_value_opposite_sign(samples: np.ndarray, observed: float) -> float:
    """Fraction of bootstrap draws whose sign is opposite to observed
    (including zero). Small value = observed statistic is robust."""
    if observed < 0:
        return float((samples >= 0.0).mean())
    if observed > 0:
        return float((samples <= 0.0).mean())
    return 1.0


def _percentile_of_zero(samples: np.ndarray) -> float:
    return float((samples <= 0.0).mean())


# --- main ---------------------------------------------------------------
def main() -> int:
    print("=" * 78)
    print("EXPERIMENT 002 — STEP 4 BOOTSTRAP (stationary block, 2 layers)")
    print("=" * 78)

    dirty = _git_is_dirty()
    if dirty:
        raise RuntimeError("Bootstrap requires a clean git working tree.")

    # Load frozen OOS equity curve
    print(f"\n[1/6] Load frozen OOS equity")
    oos_eq = pd.read_csv(OOS_EQUITY_CSV, index_col=0, parse_dates=True)
    oos_eq.index = pd.to_datetime(oos_eq.index, utc=True)
    equity = oos_eq["equity"]
    returns = equity.pct_change().dropna().to_numpy(dtype=float)
    n_ret = len(returns)
    print(f"      OOS bars: {len(equity)}  finite returns: {n_ret}")

    ann = ann_factor_from_index(oos_eq.index)
    observed_oos_sharpe = float(returns.mean() / returns.std(ddof=1) * ann) if returns.std(ddof=1) > 0 else 0.0
    observed_oos_mean_return = float(returns.mean())
    observed_oos_pnl = float(equity.iloc[-1] - equity.iloc[0])
    print(f"      observed OOS mean return: {observed_oos_mean_return:.10f}")
    print(f"      observed OOS Sharpe:      {observed_oos_sharpe:.6f}")
    print(f"      observed OOS net_pnl:     {observed_oos_pnl:.6f}")

    # Reconstruct OOS spread series
    print(f"\n[2/6] Reconstruct OOS spread series")
    panel_full = load_panel()
    spreads = reconstruct_oos_spread_series(panel_full)
    spread_arr = spreads.to_numpy(dtype=float)
    observed_mean_spread = float(spread_arr.mean())
    print(f"      OOS spread obs: n={len(spread_arr)}  "
          f"mean={observed_mean_spread:.10f}")

    # Block length estimation
    print(f"\n[3/6] Estimate block length (ACF, threshold 2/sqrt(n))")
    bl_ret = estimate_block_length_1d(returns)
    bl_spr = estimate_block_length_1d(spread_arr)
    print(f"      returns block_length = {bl_ret['block_length']}")
    print(f"      spread  block_length = {bl_spr['block_length']}")

    # Bootstrap strategy layer
    print(f"\n[4/6] Bootstrap strategy layer ({N_ITER} iterations)")
    boot_mean_ret = block_bootstrap_means(returns, N_ITER, bl_ret["block_length"], BASE_SEED)
    boot_sharpe = block_bootstrap_sharpe(returns, N_ITER, bl_ret["block_length"], BASE_SEED, ann)
    ret_lo, ret_hi = _ci(boot_mean_ret, CI_LEVEL)
    sharpe_lo, sharpe_hi = _ci(boot_sharpe, CI_LEVEL)
    strategy_verdict = _verdict(ret_lo, ret_hi)
    print(f"      mean_return  CI95 = [{ret_lo:.10f}, {ret_hi:.10f}]")
    print(f"      sharpe       CI95 = [{sharpe_lo:.4f}, {sharpe_hi:.4f}]")
    print(f"      strategy verdict (per pre-reg, mean_return CI) = {strategy_verdict}")

    # Bootstrap predictive layer
    print(f"\n[5/6] Bootstrap predictive layer ({N_ITER} iterations)")
    boot_mean_spr = block_bootstrap_means(spread_arr, N_ITER, bl_spr["block_length"], BASE_SEED)
    spr_lo, spr_hi = _ci(boot_mean_spr, CI_LEVEL)
    predictive_verdict = _verdict(spr_lo, spr_hi)
    print(f"      mean_spread  CI95 = [{spr_lo:.10f}, {spr_hi:.10f}]")
    print(f"      predictive verdict (per pre-reg) = {predictive_verdict}")

    # Overall
    if predictive_verdict == "PASS" and strategy_verdict == "PASS":
        overall = "PROMISING"
    elif predictive_verdict == "FAIL" and strategy_verdict == "FAIL":
        overall = "REJECTED"
    else:
        overall = "INCONCLUSIVE"
    print(f"      overall (derived) = {overall}")

    # Save
    print(f"\n[6/6] Writing artifacts")
    data_hashes = {a: _sha256_file(ASSET_FILES[a]) for a in ASSETS}
    summary = {
        "experiment_id": "002_momentum_btc_eth_sol_4h",
        "step": "bootstrap",
        "status": "BOOTSTRAP_COMPLETE",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "schema_version": "1.0",
        "provenance": {
            "git_commit": _git_commit(),
            "git_dirty": dirty,
            "python_version": sys.version.split()[0],
            "pandas_version": pd.__version__,
            "numpy_version": np.__version__,
            "data_hashes": data_hashes,
        },
        "spec": {
            "method": "stationary_block_bootstrap",
            "n_iter": N_ITER,
            "ci_level": CI_LEVEL,
            "seed": BASE_SEED,
            "acf_max_lag": ACF_MAX_LAG,
            "acf_threshold_factor": ACF_THRESHOLD_FACTOR,
            "split_index": SPLIT_INDEX,
            "warmup_bars": WARMUP_BARS,
            "lookback": LOOKBACK,
            "tiebreak_order": TIEBREAK,
        },
        "block_length_estimation": {
            "returns": bl_ret,
            "spread":  bl_spr,
        },
        "strategy": {
            "observed_mean_return": observed_oos_mean_return,
            "observed_sharpe":      observed_oos_sharpe,
            "observed_net_pnl":     observed_oos_pnl,
            "bootstrap_mean_return": {
                "mean":      float(boot_mean_ret.mean()),
                "std":       float(boot_mean_ret.std(ddof=1)),
                "ci_2_5":    ret_lo,
                "ci_97_5":   ret_hi,
                "p_value_opposite_sign": _p_value_opposite_sign(boot_mean_ret, observed_oos_mean_return),
                "percentile_of_zero":    _percentile_of_zero(boot_mean_ret),
            },
            "bootstrap_sharpe": {
                "mean":      float(boot_sharpe.mean()),
                "std":       float(boot_sharpe.std(ddof=1)),
                "ci_2_5":    sharpe_lo,
                "ci_97_5":   sharpe_hi,
                "p_value_opposite_sign": _p_value_opposite_sign(boot_sharpe, observed_oos_sharpe),
                "percentile_of_zero":    _percentile_of_zero(boot_sharpe),
            },
            "verdict": strategy_verdict,
        },
        "predictive": {
            "observed_mean_spread": observed_mean_spread,
            "bootstrap_mean_spread": {
                "mean":      float(boot_mean_spr.mean()),
                "std":       float(boot_mean_spr.std(ddof=1)),
                "ci_2_5":    spr_lo,
                "ci_97_5":   spr_hi,
                "p_value_opposite_sign": _p_value_opposite_sign(boot_mean_spr, observed_mean_spread),
                "percentile_of_zero":    _percentile_of_zero(boot_mean_spr),
            },
            "verdict": predictive_verdict,
        },
        "decision": {
            "predictive_verdict": predictive_verdict,
            "strategy_verdict":   strategy_verdict,
            "overall":            overall,
            "note": "Bootstrap is additional validation, not a rescue for WFO FAIL.",
        },
    }
    RESULTS_JSON.write_text(json.dumps(summary, indent=2, default=str))
    pd.DataFrame({
        "iteration": np.arange(N_ITER),
        "mean_return": boot_mean_ret,
        "sharpe": boot_sharpe,
    }).to_csv(RETURNS_CSV, index=False)
    pd.DataFrame({
        "iteration": np.arange(N_ITER),
        "mean_spread": boot_mean_spr,
    }).to_csv(SPREAD_CSV, index=False)
    print(f"      -> {RESULTS_JSON.name}")
    print(f"      -> {RETURNS_CSV.name}")
    print(f"      -> {SPREAD_CSV.name}")

    print("\n" + "-" * 78)
    print("BOOTSTRAP RESULT")
    print("-" * 78)
    print(f"  Strategy   : mean_return CI95 = [{ret_lo:.10f}, {ret_hi:.10f}]  -> {strategy_verdict}")
    print(f"  Predictive : mean_spread CI95 = [{spr_lo:.10f}, {spr_hi:.10f}]  -> {predictive_verdict}")
    print(f"  Overall    : {overall}")
    print("-" * 78)
    print("Bootstrap != rescue. WFO REJECTED remains frozen.")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())