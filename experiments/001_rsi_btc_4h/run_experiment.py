"""
Experiment 001 — RSI(14/30/50) mean reversion روی BTC-USD 4H.

Pre-registration : experiments/001_rsi_btc_4h/PRE_REGISTRATION.md
Frozen data      : data/001_btc_4h/BTC-USD_4h.csv   (status: FROZEN)
هدف              : تولید artifact پایه برای Experiment 001.

Evaluator-approved (2026-09-13): GO

Rules enforced:
  - No parameter tuning
  - No architecture changes
  - No new filters
  - Only the pre-registered configuration is executed
  - Data is loaded via load_frozen() — never re-downloaded
  - Results written to disk, not interpreted here
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path

# --- قابل import کردن ریشه ریپو ------------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pandas as pd  # noqa: E402

from engine.data_loader import load_frozen  # noqa: E402
from engine.backtest import BacktestConfig, run_backtest  # noqa: E402
from strategies.rsi_mean_reversion.strategy import RSIMeanReversion  # noqa: E402


# --- مسیرها --------------------------------------------------------------
EXPERIMENT_DIR = Path(__file__).resolve().parent
RESULTS_JSON = EXPERIMENT_DIR / "results.json"
EQUITY_CSV = EXPERIMENT_DIR / "equity_curve.csv"
TRADES_CSV = EXPERIMENT_DIR / "trades.csv"
DATA_DIR = REPO_ROOT / "data" / "001_btc_4h"
DATA_FILE = DATA_DIR / "BTC-USD_4h.csv"
MANIFEST_FILE = DATA_DIR / "MANIFEST.md"


# --- spec فریز‌شده‌ی pre-registered (ویرایش نکن) -------------------------
STRATEGY_ARGS = {"rsi_period": 14,
                 "entry_threshold": 30.0, "exit_threshold": 50.0}
STRATEGY_SPEC = {
    "name": "RSIMeanReversion",
    "rsi_period": 14,
    "entry_threshold": 30.0,
    "exit_threshold": 50.0,
    "rsi_style": "Wilder",
    "cross_semantics": "strict",
}

BACKTEST_CONFIG = BacktestConfig(
    initial_capital=100_000.0,
    position_pct=0.10,
    commission=0.0005,
    slippage=0.0002,
)


# --- provenance helpers --------------------------------------------------
def _git_commit() -> str:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=REPO_ROOT, stderr=subprocess.DEVNULL,
        )
        return out.decode().strip()
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


def _manifest_sha256() -> str | None:
    """استخراج SHA-256 از MANIFEST.md (اگر وجود داشت)."""
    if not MANIFEST_FILE.exists():
        return None
    for line in MANIFEST_FILE.read_text().splitlines():
        low = line.lower()
        if "sha-256" in low or "sha256" in low:
            for tok in line.replace("`", " ").replace(":", " ").split():
                tok = tok.strip()
                if len(tok) == 64 and all(c in "0123456789abcdef" for c in tok.lower()):
                    return tok.lower()
    return None


# --- helpers -------------------------------------------------------------
def _first_attr(obj, *names, default=float("nan")):
    for n in names:
        if hasattr(obj, n):
            return getattr(obj, n)
    return default


def _trades_to_df(trades) -> pd.DataFrame:
    if not trades:
        return pd.DataFrame()
    rows = [asdict(t) if is_dataclass(t) else vars(t) for t in trades]
    return pd.DataFrame(rows)


def _equity_to_df(equity) -> pd.DataFrame:
    if equity is None:
        return pd.DataFrame()
    if isinstance(equity, pd.Series):
        return equity.rename("equity").to_frame()
    return pd.DataFrame(equity)


# --- main ----------------------------------------------------------------
def main() -> int:
    print("=" * 68)
    print("EXPERIMENT 001 — RSI(14/30/50) mean reversion — BTC-USD 4H")
    print("=" * 68)

    dirty = _git_is_dirty()
    if dirty:
        print("\n⚠️  WARNING: working tree is dirty.")
        print("    Baseline should be produced from a clean commit.")
        print("    Continue at your own risk (provenance will be marked).\n")

    # ۱. لود داده فریز‌شده ---------------------------------------------
    print(f"\n[1/5] load_frozen({DATA_FILE.name})")
    df = load_frozen(DATA_FILE)
    print(f"      rows = {len(df)}")
    print(f"      from = {df.index[0]}")
    print(f"      to   = {df.index[-1]}")

    # ۲. ساخت strategy ------------------------------------------------
    print(f"\n[2/5] RSIMeanReversion({STRATEGY_ARGS})")
    strategy = RSIMeanReversion(**STRATEGY_ARGS)

    # ۳. اعلام کانفیگ -------------------------------------------------
    print("\n[3/5] BacktestConfig (pre-registered)")
    print(f"      initial_capital = {BACKTEST_CONFIG.initial_capital:,.2f}")
    print(f"      position_pct    = {BACKTEST_CONFIG.position_pct}")
    print(f"      commission      = {BACKTEST_CONFIG.commission}")
    print(f"      slippage        = {BACKTEST_CONFIG.slippage}")

    # ۴. اجرا ---------------------------------------------------------
    print("\n[4/5] run_backtest(...)")
    result = run_backtest(df, strategy, BACKTEST_CONFIG)

    trades_df = _trades_to_df(result.trades)
    equity_df = _equity_to_df(result.equity_curve)

    # ۵. ذخیره --------------------------------------------------------
    print(f"\n[5/5] writing artifacts -> {EXPERIMENT_DIR.name}/")

    data_sha_actual = _sha256_file(DATA_FILE) if DATA_FILE.exists() else None
    data_sha_expected = _manifest_sha256()

    summary = {
        # --- identity -------------------------------------------------
        "experiment_id": "001_rsi_btc_4h",
        "status": "BASELINE",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "schema_version": "1.0",

        # --- provenance ----------------------------------------------
        "provenance": {
            "git_commit": _git_commit(),
            "git_dirty": dirty,
            "python_version": sys.version.split()[0],
            "pandas_version": pd.__version__,
        },

        # --- data ----------------------------------------------------
        "data": {
            "source": "yfinance",
            "symbol": "BTC-USD",
            "timeframe": "4h",
            "file": str(DATA_FILE.relative_to(REPO_ROOT)),
            "rows": int(len(df)),
            "start": str(df.index[0]),
            "end": str(df.index[-1]),
            "sha256_actual": data_sha_actual,
            "sha256_expected": data_sha_expected,
            "sha256_match": (
                (data_sha_actual == data_sha_expected)
                if (data_sha_actual and data_sha_expected) else None
            ),
        },

        # --- strategy (frozen) ---------------------------------------
        "strategy": STRATEGY_SPEC,

        # --- backtest config (frozen) --------------------------------
        "backtest": asdict(BACKTEST_CONFIG),

        # --- results -------------------------------------------------
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

    # --- خلاصه --------------------------------------------------------
    m = summary["metrics"]
    print("\n" + "-" * 68)
    print("BASELINE METRICS — Experiment 001")
    print("-" * 68)
    print(f"  trades        : {m['trade_count']}")
    print(f"  net_pnl       : {m['net_pnl']:>14,.2f}")
    print(f"  sharpe        : {m['sharpe']:>14.3f}")
    print(f"  profit_factor : {m['profit_factor']:>14.3f}")
    print(f"  win_rate      : {m['win_rate']:>14.3f}")
    print(f"  max_drawdown  : {m['max_drawdown']:>14.3f}")
    print("-" * 68)
    print("NOTE: عدد مثبت اینجا مدرکِ edge نیست.")
    print("      این یک baseline است. Validation مرحله‌ی جداگانه است.")
    print("      قبل از هر تفسیر یا validation، نتیجه را برای audit بفرست.")
    print("=" * 68)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
