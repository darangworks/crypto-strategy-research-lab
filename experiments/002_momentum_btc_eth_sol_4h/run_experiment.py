"""
Experiment 002 — Cross-sectional momentum (BTC/ETH/SOL 4H).

Pre-registration : experiments/002_momentum_btc_eth_sol_4h/PRE_REGISTRATION.md
Data freeze      : data/002_btc_eth_sol_4h/ (locked, common 4334-bar grid)

Rules:
  - No re-alignment: common grid is locked at data-freeze stage.
  - Load → verify manifest SHA-256 → verify identical timestamp grid
    → build panel → run.
  - Any mismatch (hash, grid, columns) → exit non-zero, no output.
  - No tuning, no WFO, no bootstrap.
  - Baseline is produced by this runner only.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from engine.backtest import BacktestConfig  # noqa: E402
from engine.cross_sectional_backtest import run_cross_sectional_backtest  # noqa: E402
from strategies.cross_sectional_momentum.strategy import (  # noqa: E402
    CrossSectionalMomentum,
)


EXPERIMENT_DIR = Path(__file__).resolve().parent
RESULTS_JSON   = EXPERIMENT_DIR / "results.json"
EQUITY_CSV     = EXPERIMENT_DIR / "equity_curve.csv"
TRADES_CSV     = EXPERIMENT_DIR / "trades.csv"

DATA_DIR       = REPO_ROOT / "data" / "002_btc_eth_sol_4h"
MANIFEST_FILE  = DATA_DIR / "MANIFEST.md"

ASSET_FILES = {
    "BTC-USD": DATA_DIR / "BTC-USD_4h.csv",
    "ETH-USD": DATA_DIR / "ETH-USD_4h.csv",
    "SOL-USD": DATA_DIR / "SOL-USD_4h.csv",
}
EXPECTED_COLUMNS = ["Open", "High", "Low", "Close", "Volume"]


# --- frozen specification (do not edit) ---------------------------------
LOOKBACK = 6
TIEBREAK_ORDER = ["BTC-USD", "ETH-USD", "SOL-USD"]
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
    """Extract SHA-256 per asset from MANIFEST.md.

    Expected MANIFEST format (from freeze script):
    | BTC-USD | BTC-USD_4h.csv | 4334 | ... | `0aaaa...` |
    """
    if not manifest_path.exists():
        raise FileNotFoundError(f"MANIFEST not found: {manifest_path}")

    hashes: dict = {}
    for line in manifest_path.read_text(encoding="utf-8").splitlines():
        if not line.strip().startswith("|"):
            continue
        parts = [p.strip() for p in line.strip().strip("|").split("|")]
        if len(parts) < 3:
            continue
        symbol = parts[0]
        if symbol not in ASSET_FILES:
            continue
        # last column is the SHA-256, possibly with backticks
        candidate = parts[-1].strip("`").strip()
        if len(candidate) == 64 and all(
            c in "0123456789abcdef" for c in candidate.lower()
        ):
            hashes[symbol] = candidate.lower()

    missing = [s for s in ASSET_FILES if s not in hashes]
    if missing:
        raise RuntimeError(
            f"MANIFEST missing SHA-256 for: {missing}"
        )
    return hashes


# --- data loading / verification ---------------------------------------
def _load_asset_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Frozen CSV not found: {path}")
    df = pd.read_csv(path, index_col=0, parse_dates=True)
    df.index = pd.to_datetime(df.index, utc=True)
    df.index.name = "Datetime"
    return df


def _verify_asset_integrity(symbol: str, df: pd.DataFrame) -> None:
    if list(df.columns) != EXPECTED_COLUMNS:
        raise RuntimeError(
            f"[{symbol}] columns mismatch: {list(df.columns)}"
        )
    if df.index.tz is None:
        raise RuntimeError(f"[{symbol}] index has no timezone")
    if not df.index.is_monotonic_increasing:
        raise RuntimeError(f"[{symbol}] index not monotonic")
    if df.index.has_duplicates:
        raise RuntimeError(f"[{symbol}] duplicate timestamps")
    if df[EXPECTED_COLUMNS].isna().any().any():
        nan_cols = df[EXPECTED_COLUMNS].isna().any()
        raise RuntimeError(
            f"[{symbol}] NaN in columns: {nan_cols[nan_cols].index.tolist()}"
        )


def load_panel() -> dict:
    print(f"\n[1/5] Verify MANIFEST + load frozen panel")
    expected_hashes = _parse_manifest_hashes(MANIFEST_FILE)
    print(f"      manifest hashes parsed for: {list(expected_hashes)}")

    panel: dict = {}
    for symbol, path in ASSET_FILES.items():
        actual = _sha256_file(path)
        if actual != expected_hashes[symbol]:
            raise RuntimeError(
                f"[{symbol}] SHA-256 mismatch.\n"
                f"  expected: {expected_hashes[symbol]}\n"
                f"  actual:   {actual}"
            )
        df = _load_asset_csv(path)
        _verify_asset_integrity(symbol, df)
        print(f"      [{symbol}] sha256 OK, rows={len(df)}")
        panel[symbol] = df

    # All three must share the exact same timestamp grid (locked at freeze)
    base_index = panel["BTC-USD"].index
    for symbol, df in panel.items():
        if not df.index.equals(base_index):
            raise RuntimeError(
                f"[{symbol}] timestamp grid does not match BTC-USD. "
                "The runner MUST NOT re-align; this is a data-freeze violation."
            )
    print(f"      common grid: rows={len(base_index)}  "
          f"{base_index[0]} → {base_index[-1]}")

    return panel


# --- output helpers -----------------------------------------------------
def _trades_to_df(trades) -> pd.DataFrame:
    if not trades:
        return pd.DataFrame()
    rows = [asdict(t) if is_dataclass(t) else vars(t) for t in trades]
    return pd.DataFrame(rows)


def _equity_to_df(equity: pd.Series) -> pd.DataFrame:
    if equity is None:
        return pd.DataFrame()
    if isinstance(equity, pd.Series):
        return equity.rename("equity").to_frame()
    return pd.DataFrame(equity)


# --- main ----------------------------------------------------------------
def main() -> int:
    print("=" * 68)
    print("EXPERIMENT 002 — CROSS-SECTIONAL MOMENTUM (BTC/ETH/SOL 4H)")
    print("=" * 68)

    dirty = _git_is_dirty()
    if dirty:
        raise RuntimeError(
            "Baseline requires a clean git working tree. "
            "Commit or stash all changes before running."
        )

    # 1. Load + verify panel
    panel = load_panel()

    # 2. Strategy
    print(f"\n[2/5] CrossSectionalMomentum(lookback={LOOKBACK}, "
          f"tiebreak_order={TIEBREAK_ORDER})")
    strategy = CrossSectionalMomentum(
        lookback=LOOKBACK,
        tiebreak_order=TIEBREAK_ORDER,
    )

    # 3. Config
    print(f"\n[3/5] BacktestConfig (pre-registered)")
    print(f"      initial_capital = {BACKTEST_CONFIG.initial_capital:,.2f}")
    print(f"      position_pct    = {BACKTEST_CONFIG.position_pct}")
    print(f"      commission      = {BACKTEST_CONFIG.commission}")
    print(f"      slippage        = {BACKTEST_CONFIG.slippage}")

    # 4. Run
    print(f"\n[4/5] run_cross_sectional_backtest(...)")
    result = run_cross_sectional_backtest(panel, strategy, BACKTEST_CONFIG)

    trades_df = _trades_to_df(result.trades)
    equity_df = _equity_to_df(result.equity_curve)

    # 5. Save
    print(f"\n[5/5] writing artifacts -> {EXPERIMENT_DIR.name}/")

    # Recompute hashes for provenance (do not trust any cached value)
    data_hashes = {sym: _sha256_file(p) for sym, p in ASSET_FILES.items()}

    summary = {
        "experiment_id": "002_momentum_btc_eth_sol_4h",
        "status": "BASELINE",
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

        "data": {
            "dir": str(DATA_DIR.relative_to(REPO_ROOT)),
            "assets": list(ASSET_FILES.keys()),
            "rows": int(len(panel["BTC-USD"])),
            "start": str(panel["BTC-USD"].index[0]),
            "end": str(panel["BTC-USD"].index[-1]),
            "common_grid": True,
        },

        "strategy": {
            "name": "CrossSectionalMomentum",
            "lookback": LOOKBACK,
            "tiebreak_order": TIEBREAK_ORDER,
            "top_n": 1,
            "long_only": True,
        },

        "backtest": asdict(BACKTEST_CONFIG),

        "metrics": {
            "net_pnl":       float(result.net_pnl),
            "sharpe":        float(result.sharpe),
            "profit_factor": float(result.profit_factor),
            "win_rate":      float(result.win_rate),
            "max_drawdown":  float(result.max_drawdown),
            "trade_count":   int(result.trade_count),
        },
    }

    RESULTS_JSON.write_text(json.dumps(summary, indent=2, default=str))
    equity_df.to_csv(EQUITY_CSV, index=True)
    trades_df.to_csv(TRADES_CSV, index=False)

    print(f"      -> {RESULTS_JSON.name}")
    print(f"      -> {EQUITY_CSV.name}  ({len(equity_df)} rows)")
    print(f"      -> {TRADES_CSV.name}  ({len(trades_df)} rows)")

    m = summary["metrics"]
    print("\n" + "-" * 68)
    print("BASELINE METRICS — Experiment 002")
    print("-" * 68)
    print(f"  trades        : {m['trade_count']}")
    print(f"  net_pnl       : {m['net_pnl']:>14,.2f}")
    print(f"  sharpe        : {m['sharpe']:>14.3f}")
    print(f"  profit_factor : {m['profit_factor']:>14.3f}")
    print(f"  win_rate      : {m['win_rate']:>14.3f}")
    print(f"  max_drawdown  : {m['max_drawdown']:>14.3f}")
    print("-" * 68)
    print("NOTE: baseline only. No interpretation. Leakage suite is next.")
    print("=" * 68)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())