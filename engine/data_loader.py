"""
Data loader with frozen snapshots.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


REQUIRED_COLUMNS = ["Open", "High", "Low", "Close", "Volume"]


@dataclass
class DataManifest:
    source: str
    symbol: str
    timeframe: str
    start: str
    end: str
    retrieved_at: str
    row_count: int
    columns: list
    sha256: str

    def to_markdown(self) -> str:
        lines = [
            "# Data Manifest",
            "",
            f"- **Source:** {self.source}",
            f"- **Symbol:** {self.symbol}",
            f"- **Timeframe:** {self.timeframe}",
            f"- **Start:** {self.start}",
            f"- **End:** {self.end}",
            f"- **Retrieved at:** {self.retrieved_at}",
            f"- **Row count:** {self.row_count}",
            f"- **Columns:** {', '.join(self.columns)}",
            f"- **SHA-256:** `{self.sha256}`",
            "",
            "> Reproducibility relies on this frozen CSV.",
        ]
        return "\n".join(lines)


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def _integrity_guards(df: pd.DataFrame) -> None:
    assert isinstance(df.index, pd.DatetimeIndex), "Index must be DatetimeIndex"
    assert df.index.tz is not None, "Index must be timezone-aware"
    assert str(df.index.tz) == "UTC", f"Expected UTC, got {df.index.tz}"
    assert df.index.is_monotonic_increasing, "Index must be sorted"
    assert not df.index.has_duplicates, "Index must not have duplicates"
    assert list(df.columns) == REQUIRED_COLUMNS, (
        f"Expected columns {REQUIRED_COLUMNS}, got {list(df.columns)}"
    )


def _fetch_yfinance(symbol: str, timeframe: str, period: str = "730d") -> pd.DataFrame:
    try:
        import yfinance as yf
    except ImportError as e:
        raise ImportError("yfinance not installed.") from e

    df = yf.download(
        symbol, interval=timeframe, period=period,
        auto_adjust=False, progress=False,
    )
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df[REQUIRED_COLUMNS].dropna().copy()
    return df


def freeze_snapshot(symbol, timeframe, out_dir, *, source="yfinance", period="730d"):
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    if source == "yfinance":
        df = _fetch_yfinance(symbol, timeframe, period=period)
    else:
        raise ValueError(f"Unknown source: {source}")

    _integrity_guards(df)

    csv_path = out_path / f"{symbol}_{timeframe}.csv"
    df.to_csv(csv_path, date_format="%Y-%m-%d %H:%M:%S%z")

    manifest = DataManifest(
        source=source,
        symbol=symbol,
        timeframe=timeframe,
        start=str(df.index[0]),
        end=str(df.index[-1]),
        retrieved_at=datetime.now(timezone.utc).isoformat(),
        row_count=len(df),
        columns=list(df.columns),
        sha256=_sha256_file(csv_path),
    )

    (out_path / "MANIFEST.md").write_text(manifest.to_markdown(), encoding="utf-8")
    return manifest


def load_frozen(csv_path):
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"Frozen data not found: {path}")

    df = pd.read_csv(path, index_col=0, parse_dates=True)
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")

    _integrity_guards(df)
    return df


def verify_manifest(manifest_path, csv_path) -> bool:
    manifest_path = Path(manifest_path)
    csv_path = Path(csv_path)

    if not manifest_path.exists() or not csv_path.exists():
        return False

    text = manifest_path.read_text(encoding="utf-8")
    for line in text.splitlines():
        if "SHA-256" in line:
            expected = line.split("`")[1].strip()
            actual = _sha256_file(csv_path)
            return expected == actual
    return False
