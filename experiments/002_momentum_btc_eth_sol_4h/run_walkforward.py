"""
Experiment 002 — Step 3: Walk-Forward (single 50/50 split).

Pre-registration: experiments/002_momentum_btc_eth_sol_4h/PRE_REGISTRATION.md
Baseline commit: 3506f6a
Leakage commit:  5f48ecd

Design (per evaluator approval 2026-09-14):
- Split index = 2167 (matches Exp 001)
- IS  = bars 0..2166 (2167 bars)
- OOS = bars 2167..4333 (2167 bars)
- Warmup: first 6 bars NaN in IS; OOS uses prior 6 real bars (no cold restart)
- Force flat at split: two independent backtests; IS ends with final
  liquidation; OOS starts fresh from initial capital
- Predictive metric: full valid OOS panel (not restricted to holding bars)
- top/bottom selected at close[t] via momentum[t]; next-bar return t->t+1
- Verdict: independent predictive and strategy layers
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import numpy as np
import pandas as pd

from engine.backtest import BacktestConfig
from engine.cross_sectional_backtest import run_cross_sectional_backtest
from strategies.cross_sectional_momentum.strategy import CrossSectionalMomentum


EXPERIMENT_DIR = Path(__file__).resolve().parent
RESULTS_JSON = EXPERIMENT_DIR / "walkforward.json"
IS_EQUITY_CSV = EXPERIMENT_DIR / "walkforward_is_equity.csv"
OOS_EQUITY_CSV = EXPERIMENT_DIR / "walkforward_oos_equity.csv"
DATA_DIR = REPO_ROOT / "data" / "002_btc_eth_sol_4h"
MANIFEST_FILE = DATA_DIR / "MANIFEST.md"

ASSETS = ["BTC-USD", "ETH-USD", "SOL-USD"]
ASSET_FILES = {a: DATA_DIR / f"{a}_4h.csv" for a in ASSETS}
EXPECTED_COLUMNS = ["Open", "High", "Low", "Close", "Volume"]

SPLIT_INDEX = 2167
WARMUP_BARS = 6
FORCE_FLAT_AT_SPLIT = True

LOOKBACK = 6
TIEBREAK_ORDER = list(ASSETS)
BACKTEST_CONFIG = BacktestConfig(
    initial_capital=100_000.0,
    position_pct=1.0,
    commission=0.0005,
    slippage=0.0002,
)


# --- provenance helpers -------------------------------------------------
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


def _parse_manifest_hashes(manifest_path: Path) -> dict:
    if not manifest_path.exists():
        raise FileNotFoundError(f"MANIFEST not found: {manifest_path}")
    hashes: dict = {}
    for line in manifest_path.read_text(encoding="utf-8").splitlines():
        if not line.strip().startswith("|"):
            continue
        parts = [p.strip() for p in line.strip().strip("|").split("|")]
        if len(parts) < 3 or parts[0] not in ASSET_FILES:
            continue
        cand = parts[-1].strip("`").strip()
        if len(cand) == 64 and all(c in "0123456789abcdef" for c in cand.lower()):
            hashes[parts[0]] = cand.lower()
    missing = [s for s in ASSET_FILES if s not in hashes]
    if missing:
        raise RuntimeError(f"MANIFEST missing SHA-256 for: {missing}")
    return hashes


# --- data loading -------------------------------------------------------
def load_panel() -> dict:
    expected = _parse_manifest_hashes(MANIFEST_FILE)
    panel = {}
    for sym in ASSETS:
        path = ASSET_FILES[sym]
        actual = _sha256_file(path)
        if actual != expected[sym]:
            raise RuntimeError(f"[{sym}] SHA-256 mismatch")
        df = pd.read_csv(path, index_col=0, parse_dates=True)
        df.index = pd.to_datetime(df.index, utc=True)
        df.index.name = "Datetime"
        if list(df.columns) != EXPECTED_COLUMNS:
            raise RuntimeError(f"[{sym}] columns mismatch")
        if df.index.has_duplicates or not df.index.is_monotonic_increasing:
            raise RuntimeError(f"[{sym}] index not clean")
        panel[sym] = df
    base = panel[ASSETS[0]].index
    for sym in ASSETS:
        if not panel[sym].index.equals(base):
            raise RuntimeError(f"[{sym}] grid mismatch")
    return panel


# --- precomputed-targets wrapper ----------------------------------------
class _PrecomputedTargets:
    def __init__(self, targets: pd.Series):
        self._targets = targets

    def target_asset(self, panel: dict) -> pd.Series:
        idx = next(iter(panel.values())).index
        return self._targets.reindex(idx)


# --- predictive metric --------------------------------------------------
def compute_predictive_metric(
    mom: pd.DataFrame,
    closes: dict,
    tiebreak_order: list,
    eval_index: pd.DatetimeIndex,
) -> dict:
    """Full-panel predictive metric.

    For each t in eval_index with valid momentum:
        top    = tiebreak argmax of momentum[t]
        bottom = reverse-tiebreak argmin of momentum[t]
        spread[t] = log(C[top,t+1]/C[top,t]) - log(C[bottom,t+1]/C[bottom,t])
    """
    all_ts = next(iter(closes.values())).index
    pos_map = {ts: i for i, ts in enumerate(all_ts)}
    spreads = []
    for t in eval_index:
        if t not in mom.index:
            continue
        mrow = mom.loc[t]
        if mrow.isna().any():
            continue
        pos_t = pos_map.get(t)
        if pos_t is None or pos_t + 1 >= len(all_ts):
            continue
        t_next = all_ts[pos_t + 1]

        max_mom = mrow.max()
        top = next(a for a in tiebreak_order
                   if a in mrow.index and np.isclose(mrow[a], max_mom))
        min_mom = mrow.min()
        bottom = next(a for a in reversed(tiebreak_order)
                      if a in mrow.index and np.isclose(mrow[a], min_mom))

        ret_top = float(np.log(closes[top].loc[t_next] / closes[top].loc[t]))
        ret_bot = float(np.log(closes[bottom].loc[t_next] / closes[bottom].loc[t]))
        spreads.append(ret_top - ret_bot)

    arr = np.array(spreads, dtype=float)
    if len(arr) == 0:
        return {"n_obs": 0, "mean_spread": 0.0, "std_spread": 0.0,
                "median_spread": 0.0, "frac_positive": 0.0}
    return {
        "n_obs": int(len(arr)),
        "mean_spread": float(arr.mean()),
        "std_spread": float(arr.std(ddof=1)) if len(arr) > 1 else 0.0,
        "median_spread": float(np.median(arr)),
        "frac_positive": float((arr > 0).mean()),
    }


# --- verdicts -----------------------------------------------------------
def _predictive_verdict(mean_spread: float) -> str:
    if mean_spread > 0: return "PASS"
    if mean_spread < 0: return "FAIL"
    return "INCONCLUSIVE"


def _strategy_verdict(sharpe: float) -> str:
    if sharpe > 0: return "PASS"
    if sharpe < 0: return "FAIL"
    return "INCONCLUSIVE"


def _overall_verdict(pv: str, sv: str) -> str:
    if pv == "PASS" and sv == "PASS": return "PROMISING"
    if pv == "FAIL" and sv == "FAIL": return "REJECTED"
    return "INCONCLUSIVE"


# --- main ---------------------------------------------------------------
def main() -> int:
    print("=" * 68)
    print("EXPERIMENT 002 — STEP 3 WALK-FORWARD (50/50)")
    print("=" * 68)

    dirty = _git_is_dirty()
    if dirty:
        raise RuntimeError(
            "WFO requires a clean git working tree. Commit or stash first."
        )

    # 1. Load frozen panel
    print(f"\n[1/7] Load frozen panel (SHA-256 verified)")
    panel_full = load_panel()
    index_full = panel_full[ASSETS[0]].index
    n = len(index_full)
    print(f"      rows = {n}")
    assert SPLIT_INDEX == n // 2, f"split {SPLIT_INDEX} != n//2 ({n//2})"

    # 2. Split
    print(f"\n[2/7] Split: IS = 0..{SPLIT_INDEX-1}, OOS = {SPLIT_INDEX}..{n-1}")
    panel_is = {a: panel_full[a].iloc[:SPLIT_INDEX].copy() for a in ASSETS}
    panel_oos = {a: panel_full[a].iloc[SPLIT_INDEX:].copy() for a in ASSETS}
    print(f"      IS bars: {len(panel_is[ASSETS[0]])}")
    print(f"      OOS bars: {len(panel_oos[ASSETS[0]])}")

    # 3. IS backtest
    print(f"\n[3/7] IS: fresh strategy + backtest")
    strat_is = CrossSectionalMomentum(lookback=LOOKBACK, tiebreak_order=TIEBREAK_ORDER)
    is_result = run_cross_sectional_backtest(panel_is, strat_is, BACKTEST_CONFIG)
    print(f"      IS trades={is_result.trade_count}  "
          f"net_pnl={is_result.net_pnl:+.2f}  sharpe={is_result.sharpe:+.4f}")

    # 4. OOS backtest with warmed targets
    print(f"\n[4/7] OOS: warmed targets + backtest")
    warm_start = SPLIT_INDEX - WARMUP_BARS
    panel_warm = {a: panel_full[a].iloc[warm_start:].copy() for a in ASSETS}
    strat_warm = CrossSectionalMomentum(lookback=LOOKBACK, tiebreak_order=TIEBREAK_ORDER)
    warm_targets = strat_warm.target_asset(panel_warm)
    oos_targets = warm_targets.iloc[WARMUP_BARS:]
    print(f"      warmed panel: {panel_warm[ASSETS[0]].index[0]} → "
          f"{panel_warm[ASSETS[0]].index[-1]}")
    print(f"      OOS targets valid: {int(oos_targets.notna().sum())} / {len(oos_targets)}")

    oos_strategy = _PrecomputedTargets(oos_targets)
    oos_result = run_cross_sectional_backtest(panel_oos, oos_strategy, BACKTEST_CONFIG)
    print(f"      OOS trades={oos_result.trade_count}  "
          f"net_pnl={oos_result.net_pnl:+.2f}  sharpe={oos_result.sharpe:+.4f}")

    # 5. Predictive metrics
    print(f"\n[5/7] Predictive metrics (full valid panel)")
    closes_is = {a: panel_is[a]["Close"] for a in ASSETS}
    is_eval = index_full[WARMUP_BARS:SPLIT_INDEX - 1]   # 6..2165
    mom_is = strat_is.momentum(panel_is)
    pred_is = compute_predictive_metric(mom_is, closes_is, TIEBREAK_ORDER, is_eval)
    print(f"      IS pred:  n_obs={pred_is['n_obs']}  "
          f"mean_spread={pred_is['mean_spread']:+.8f}")

    closes_oos = {a: panel_oos[a]["Close"] for a in ASSETS}
    oos_eval = index_full[SPLIT_INDEX:n - 1]  # 2167..4332
    mom_warm = strat_warm.momentum(panel_warm)
    pred_oos = compute_predictive_metric(mom_warm, closes_oos, TIEBREAK_ORDER, oos_eval)
    print(f"      OOS pred: n_obs={pred_oos['n_obs']}  "
          f"mean_spread={pred_oos['mean_spread']:+.8f}")

    # 6. Verdicts
    print(f"\n[6/7] Verdicts")
    pv = _predictive_verdict(pred_oos["mean_spread"]) if pred_oos["n_obs"] > 0 else "INCONCLUSIVE"
    sv = _strategy_verdict(oos_result.sharpe)
    ov = _overall_verdict(pv, sv)
    print(f"      predictive = {pv}")
    print(f"      strategy   = {sv}")
    print(f"      overall    = {ov}")

    # 7. Save
    print(f"\n[7/7] Writing artifacts")
    data_hashes = {a: _sha256_file(ASSET_FILES[a]) for a in ASSETS}
    summary = {
        "experiment_id": "002_momentum_btc_eth_sol_4h",
        "step": "walk-forward",
        "status": "WFO_COMPLETE",
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
            "split_index": SPLIT_INDEX,
            "lookback": LOOKBACK,
            "tiebreak_order": TIEBREAK_ORDER,
            "warmup_bars": WARMUP_BARS,
            "force_flat_at_split": FORCE_FLAT_AT_SPLIT,
        },
        "config": asdict(BACKTEST_CONFIG),
        "is": {
            "predictive": pred_is,
            "strategy": {
                "net_pnl":       float(is_result.net_pnl),
                "sharpe":        float(is_result.sharpe),
                "profit_factor": float(is_result.profit_factor),
                "win_rate":      float(is_result.win_rate),
                "max_drawdown":  float(is_result.max_drawdown),
                "trade_count":   int(is_result.trade_count),
            },
        },
        "oos": {
            "predictive": pred_oos,
            "strategy": {
                "net_pnl":       float(oos_result.net_pnl),
                "sharpe":        float(oos_result.sharpe),
                "profit_factor": float(oos_result.profit_factor),
                "win_rate":      float(oos_result.win_rate),
                "max_drawdown":  float(oos_result.max_drawdown),
                "trade_count":   int(oos_result.trade_count),
            },
        },
        "decision": {
            "predictive_verdict": pv,
            "strategy_verdict": sv,
            "overall": ov,
            "note": "PROMISING is exploratory, not proof of robustness.",
        },
    }
    RESULTS_JSON.write_text(json.dumps(summary, indent=2, default=str))
    is_result.equity_curve.rename("equity").to_frame().to_csv(IS_EQUITY_CSV, index=True)
    oos_result.equity_curve.rename("equity").to_frame().to_csv(OOS_EQUITY_CSV, index=True)
    print(f"      -> {RESULTS_JSON.name}")
    print(f"      -> {IS_EQUITY_CSV.name}")
    print(f"      -> {OOS_EQUITY_CSV.name}")

    print("\n" + "-" * 68)
    print("WALK-FORWARD RESULT")
    print("-" * 68)
    print(f"  IS   trades={is_result.trade_count:>4}  "
          f"net_pnl={is_result.net_pnl:>12,.2f}  sharpe={is_result.sharpe:>7.3f}")
    print(f"  OOS  trades={oos_result.trade_count:>4}  "
          f"net_pnl={oos_result.net_pnl:>12,.2f}  sharpe={oos_result.sharpe:>7.3f}")
    print(f"  OOS mean_spread = {pred_oos['mean_spread']:+.8f}")
    print(f"  PREDICTIVE = {pv}   STRATEGY = {sv}   OVERALL = {ov}")
    print("-" * 68)
    print("PROMISING != robust edge. Bootstrap is a separate step.")
    print("=" * 68)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())