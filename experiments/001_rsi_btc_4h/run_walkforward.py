"""
Experiment 001 — Step 3: Walk-Forward (single 50/50 split).

Pre-registration : experiments/001_rsi_btc_4h/PRE_REGISTRATION.md
Frozen baseline  : tag exp-001-baseline (commit ccf28ac)

Rules:
  - No parameter tuning
  - No architecture changes
  - RSI state carries over from IS to OOS (no recompute at split)
  - Force flat at end of IS
  - Same costs as baseline
  - OOS Sharpe criterion per pre-registration:
      OOS sharpe > 0  -> PASS
      OOS sharpe = 0  -> INCONCLUSIVE
      OOS sharpe < 0  -> FAIL
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

import pandas as pd  # noqa: E402

from engine.data_loader import load_frozen  # noqa: E402
from engine.backtest import BacktestConfig, run_backtest  # noqa: E402
from strategies.rsi_mean_reversion.strategy import RSIMeanReversion  # noqa: E402


EXPERIMENT_DIR = Path(__file__).resolve().parent
RESULTS_JSON = EXPERIMENT_DIR / "walkforward.json"
IS_EQUITY_CSV = EXPERIMENT_DIR / "walkforward_is_equity.csv"
OOS_EQUITY_CSV = EXPERIMENT_DIR / "walkforward_oos_equity.csv"
DATA_FILE = REPO_ROOT / "data" / "001_btc_4h" / "BTC-USD_4h.csv"

SPLIT_INDEX = 2167        # IS = 0..2166 (2167 rows), OOS = 2167..4333 (2167 rows)
WARMUP_BARS = 14          # RSI period; last 14 IS bars are OOS warm-up only
FORCE_FLAT_AT_SPLIT = True

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


class _PrecomputedRSI(RSIMeanReversion):
    """RSI wrapper that uses pre-computed RSI + target (state carry-over)."""

    def __init__(self, rsi: pd.Series, target: pd.Series):
        super().__init__(**STRATEGY_ARGS)
        self._rsi = rsi
        self._target = target

    def compute_features(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df["RSI"] = self._rsi.reindex(df.index).values
        return df

    def target_position(self, df: pd.DataFrame) -> pd.Series:
        return self._target.reindex(df.index).fillna(0.0)


def _result_metrics(r) -> dict:
    return {
        "net_pnl":       float(r.net_pnl),
        "sharpe":        float(r.sharpe),
        "profit_factor": float(r.profit_factor),
        "win_rate":      float(r.win_rate),
        "max_drawdown":  float(r.max_drawdown),
        "trade_count":   int(r.trade_count),
    }


def _verdict(oos_sharpe: float) -> str:
    if oos_sharpe > 0.0:
        return "PASS"
    if oos_sharpe == 0.0:
        return "INCONCLUSIVE"
    return "FAIL"


def main() -> int:
    print("=" * 68)
    print("EXPERIMENT 001 — STEP 3 WALK-FORWARD (50/50)")
    print("=" * 68)

    # 1. Load frozen data
    print(f"\n[1/6] load_frozen({DATA_FILE.name})")
    df = load_frozen(DATA_FILE)
    n = len(df)
    print(f"      rows = {n}")
    assert SPLIT_INDEX == n // 2, f"split {SPLIT_INDEX} != n//2 ({n // 2})"

    # 2. Precompute RSI on FULL series (state carry-over across split)
    print("\n[2/6] precompute RSI on full series (state carry-over)")
    base = RSIMeanReversion(**STRATEGY_ARGS)
    df_full = base.compute_features(df.copy())
    rsi_full = df_full["RSI"].copy()
    target_full = base.target_position(df_full).copy()
    first_valid = rsi_full.first_valid_index()
    first_valid_pos = int(df.index.get_loc(first_valid)) if first_valid is not None else -1
    print(f"      RSI first valid bar: {first_valid_pos}")

    # 3. Force flat at end of IS
    if FORCE_FLAT_AT_SPLIT:
        target_full.iloc[SPLIT_INDEX - 1] = 0.0

    # 4. Slice
    print(f"\n[3/6] split: IS = 0..{SPLIT_INDEX - 1}, OOS = {SPLIT_INDEX}..{n - 1}")
    is_df = df.iloc[:SPLIT_INDEX].copy()
    is_rsi = rsi_full.iloc[:SPLIT_INDEX].copy()
    is_target = target_full.iloc[:SPLIT_INDEX].copy()

    oos_df = df.iloc[SPLIT_INDEX:].copy()
    oos_rsi = rsi_full.iloc[SPLIT_INDEX:].copy()
    oos_target = target_full.iloc[SPLIT_INDEX:].copy()

    # 5. Backtest IS then OOS
    print("\n[4/6] backtest IS ...")
    is_result = run_backtest(is_df, _PrecomputedRSI(is_rsi, is_target), BACKTEST_CONFIG)

    print("[5/6] backtest OOS ...")
    oos_result = run_backtest(oos_df, _PrecomputedRSI(oos_rsi, oos_target), BACKTEST_CONFIG)

    # 6. Save
    print(f"\n[6/6] writing artifacts -> {EXPERIMENT_DIR.name}/")

    is_m = _result_metrics(is_result)
    oos_m = _result_metrics(oos_result)
    verdict = _verdict(oos_m["sharpe"])

    summary = {
        "experiment_id": "001_rsi_btc_4h",
        "step": "walk-forward",
        "status": "WFO_COMPLETE",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "schema_version": "1.0",

        "provenance": {
            "git_commit": _git_commit(),
            "python_version": sys.version.split()[0],
            "pandas_version": pd.__version__,
            "data_sha256": _sha256_file(DATA_FILE) if DATA_FILE.exists() else None,
        },

        "split": {
            "split_index": SPLIT_INDEX,
            "is_start": str(df.index[0]),
            "is_end": str(df.index[SPLIT_INDEX - 1]),
            "oos_start": str(df.index[SPLIT_INDEX]),
            "oos_end": str(df.index[-1]),
            "is_rows": int(SPLIT_INDEX),
            "oos_rows": int(n - SPLIT_INDEX),
            "warmup_rows": WARMUP_BARS,
            "force_flat_at_split": FORCE_FLAT_AT_SPLIT,
        },

        "strategy": {"name": "RSIMeanReversion", **STRATEGY_ARGS},
        "config": asdict(BACKTEST_CONFIG),

        "is_metrics": is_m,
        "oos_metrics": oos_m,

        "decision": {
            "criterion": "oos_sharpe sign per pre-registration",
            "oos_sharpe": oos_m["sharpe"],
            "verdict": verdict,
            "note": "WFO FAIL: OOS Sharpe < 0. Bootstrap remains a separate pre-registered uncertainty analysis.",
        },
    }

    RESULTS_JSON.write_text(json.dumps(summary, indent=2, default=str))
    is_result.equity_curve.rename("equity").to_frame().to_csv(IS_EQUITY_CSV, index=True)
    oos_result.equity_curve.rename("equity").to_frame().to_csv(OOS_EQUITY_CSV, index=True)

    print(f"      -> {RESULTS_JSON.name}")
    print(f"      -> {IS_EQUITY_CSV.name}  ({len(is_result.equity_curve)} rows)")
    print(f"      -> {OOS_EQUITY_CSV.name}  ({len(oos_result.equity_curve)} rows)")

    print("\n" + "-" * 68)
    print("WALK-FORWARD RESULT")
    print("-" * 68)
    print(f"  IS   trades={is_m['trade_count']:>4}  net_pnl={is_m['net_pnl']:>12,.2f}  sharpe={is_m['sharpe']:>7.3f}")
    print(f"  OOS  trades={oos_m['trade_count']:>4}  net_pnl={oos_m['net_pnl']:>12,.2f}  sharpe={oos_m['sharpe']:>7.3f}")
    print(f"  VERDICT (per pre-reg): {verdict}")
    print("-" * 68)
    print("PASS != robust edge. Bootstrap is a separate step.")
    print("=" * 68)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
