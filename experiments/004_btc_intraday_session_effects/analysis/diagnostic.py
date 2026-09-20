"""
P004 — BTC Intraday Session Effects
Statistical Diagnostic Script (read-only against frozen dataset)

Implements exactly the locked protocol:
    experiments/004_btc_intraday_session_effects/PROTOCOL.md
    commit a393aad, tag p004-protocol-locked

The frozen dataset is read-only. No modification.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import friedmanchisquare, rankdata, wilcoxon


# ──────────────────────────── Paths ────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
EXPERIMENT_DIR = SCRIPT_DIR.parent
REPO_ROOT = EXPERIMENT_DIR.parents[1]

DATA_FILE = EXPERIMENT_DIR / "data" / "frozen" / \
    "BTCUSDT_1h_2024-01-01_2026-08-31.csv"
OUTPUT_JSON = SCRIPT_DIR / "diagnostic.json"
OUTPUT_MD = SCRIPT_DIR / "diagnostic_report.md"

EXPECTED_SHA256 = "fb8f1537a2f054d49841436ec04eb13e06cdad825d96ad62da77dd9c48ea467e"


# ──────────────────────── Protocol constants ────────────────────
# §3 — Session boundaries (UTC, start-inclusive, end-exclusive)
SESSIONS = {
    "Asia":    (0, 8),
    "London":  (8, 13),
    "NewYork": (13, 21),
}

# §5 — Primary metrics
PRIMARY_METRICS = [
    "session_return",
    "abs_return",
    "session_range",
    "realized_volatility",
    "volume",
]

# §7 — Bootstrap parameters
BOOTSTRAP_N = 10_000
BOOTSTRAP_SEED = 20260920
CI_LEVEL = 0.95

# §8 — Sub-periods (label, start, end)
SUB_PERIODS = [
    ("2024",         "2024-01-01", "2024-12-31"),
    ("2025",         "2025-01-01", "2025-12-31"),
    ("2026_Jan_Aug", "2026-01-01", "2026-08-31"),
]


# ──────────────────────── Helpers ────────────────────────
def _parse_binance_timestamps(s: pd.Series) -> pd.Series:
    """Parse mixed Binance timestamp units: milliseconds before 2025, microseconds from 2025."""
    s = pd.to_numeric(s, errors="raise")

    threshold = 10**14
    mask_ms = s < threshold
    mask_us = s >= threshold

    out = pd.Series(pd.NaT, index=s.index, dtype="datetime64[ns, UTC]")

    if mask_ms.any():
        out.loc[mask_ms] = pd.to_datetime(
            s.loc[mask_ms],
            unit="ms",
            utc=True,
        )

    if mask_us.any():
        out.loc[mask_us] = pd.to_datetime(
            s.loc[mask_us],
            unit="us",
            utc=True,
        )

    return out


def _find_col(df: pd.DataFrame, candidates: list[str]) -> str:
    lower = {c.lower(): c for c in df.columns}
    for cand in candidates:
        if cand.lower() in lower:
            return lower[cand.lower()]
    raise KeyError(
        f"None of {candidates} found in columns: {list(df.columns)}")


def load_frozen_dataset() -> pd.DataFrame:
    """Load the frozen CSV. Read-only. Verify SHA-256."""
    if not DATA_FILE.exists():
        raise FileNotFoundError(f"Frozen dataset not found: {DATA_FILE}")
    actual = hashlib.sha256(DATA_FILE.read_bytes()).hexdigest()
    if actual != EXPECTED_SHA256:
        raise RuntimeError(
            f"Frozen dataset SHA-256 mismatch.\n"
            f"Expected: {EXPECTED_SHA256}\n"
            f"Actual:   {actual}\n"
            f"Refusing to continue."
        )
    df = pd.read_csv(DATA_FILE)

    open_time_col = _find_col(
        df, ["open_time", "Open time", "opentime",
             "datetime", "date", "timestamp"]
    )
    o_col = _find_col(df, ["open", "Open"])
    h_col = _find_col(df, ["high", "High"])
    l_col = _find_col(df, ["low", "Low"])
    c_col = _find_col(df, ["close", "Close"])
    v_col = _find_col(df, ["volume", "Volume"])

    df = df.rename(columns={
        open_time_col: "open_time",
        o_col: "open",
        h_col: "high",
        l_col: "low",
        c_col: "close",
        v_col: "volume",
    })

    df["open_time"] = _parse_binance_timestamps(df["open_time"])
    df = df.sort_values("open_time").reset_index(drop=True)
    return df


def assign_session(hour: int) -> str | None:
    for name, (start, end) in SESSIONS.items():
        if start <= hour < end:
            return name
    return None


def build_observations(df: pd.DataFrame) -> pd.DataFrame:
    """Build one observation per (UTC day, session) per §4."""
    df = df.copy()
    df["utc_date"] = df["open_time"].dt.date
    df["utc_hour"] = df["open_time"].dt.hour
    df["session"] = df["utc_hour"].apply(assign_session)
    df = df[df["session"].notna()].copy()

    expected_hours = {name: end - start for name,
                      (start, end) in SESSIONS.items()}
    rows = []
    for (date, session), group in df.groupby(["utc_date", "session"]):
        group = group.sort_values("open_time")
        expected = expected_hours[session]
        if len(group) != expected:
            continue

        close_first = float(group["close"].iloc[0])
        close_last = float(group["close"].iloc[-1])
        high_max = float(group["high"].max())
        low_min = float(group["low"].min())
        volume_sum = float(group["volume"].sum())

        session_return = float(np.log(close_last / close_first))
        abs_return = float(abs(session_return))

        closes = group["close"].to_numpy(dtype=float)
        log_returns = np.log(closes[1:] / closes[:-1])
        realized_vol = (
            float(np.std(log_returns, ddof=1))
            if len(log_returns) > 1 else float("nan")
        )

        session_range = float(high_max - low_min)

        rows.append({
            "date": pd.Timestamp(date, tz="UTC"),
            "session": session,
            "session_return": session_return,
            "abs_return": abs_return,
            "session_range": session_range,
            "realized_volatility": realized_vol,
            "volume": volume_sum,
        })

    return pd.DataFrame(rows)


def build_complete_days(obs: pd.DataFrame) -> pd.DataFrame:
    """§6.1 — Keep only UTC days with valid observations for ALL sessions."""
    session_names = list(SESSIONS.keys())
    counts = obs.groupby("date")["session"].nunique()
    complete_dates = counts[counts == len(session_names)].index
    return obs[obs["date"].isin(complete_dates)].copy()


def friedman_test(complete_days: pd.DataFrame, metric: str) -> dict:
    """§6.2 — Friedman test across 3 sessions, blocked by UTC day."""
    session_names = list(SESSIONS.keys())
    pivot = complete_days.pivot(index="date", columns="session", values=metric)
    pivot = pivot[session_names].dropna()

    if len(pivot) < 3:
        return {
            "statistic": float("nan"),
            "p_value": float("nan"),
            "n_days": int(len(pivot)),
            "warning": "insufficient_days",
        }

    stat, p = friedmanchisquare(
        pivot[session_names[0]].to_numpy(),
        pivot[session_names[1]].to_numpy(),
        pivot[session_names[2]].to_numpy(),
    )
    n = len(pivot)
    k = len(session_names)
    kendall_w = float(stat) / (n * (k - 1)
                               ) if n > 0 and k > 1 else float("nan")

    return {
        "statistic": float(stat),
        "p_value": float(p),
        "n_days": int(n),
        "kendall_w": kendall_w,
    }


def wilcoxon_pairwise(complete_days: pd.DataFrame, metric: str) -> dict:
    """§6.3 — Wilcoxon signed-rank for each session pair."""
    session_names = list(SESSIONS.keys())
    pivot = complete_days.pivot(index="date", columns="session", values=metric)
    pivot = pivot[session_names].dropna()

    pairs = [("Asia", "London"), ("London", "NewYork"), ("Asia", "NewYork")]
    results = []
    for a, b in pairs:
        x = pivot[a].to_numpy(dtype=float)
        y = pivot[b].to_numpy(dtype=float)
        diffs = x - y
        nz = diffs[diffs != 0]
        if len(nz) == 0:
            results.append({
                "pair": f"{a}_vs_{b}",
                "n": int(len(diffs)),
                "n_nonzero": 0,
                "statistic": float("nan"),
                "p_value": float("nan"),
                "rank_biserial": float("nan"),
            })
            continue
        stat, p = wilcoxon(x, y, zero_method="wilcox", alternative="two-sided")
        ranks = rankdata(np.abs(nz))
        r_plus = float(ranks[nz > 0].sum())
        r_minus = float(ranks[nz < 0].sum())
        denom = r_plus + r_minus
        r_rb = (r_plus - r_minus) / denom if denom > 0 else float("nan")
        results.append({
            "pair": f"{a}_vs_{b}",
            "n": int(len(diffs)),
            "n_nonzero": int(len(nz)),
            "statistic": float(stat),
            "p_value": float(p),
            "rank_biserial": float(r_rb),
        })
    return {"pairs": results}


def holm_correction(p_values: list[float]) -> list[float]:
    """§6.4 — Holm correction within a metric family."""
    m = len(p_values)
    if m == 0:
        return []
    arr = np.array(p_values, dtype=float)
    order = np.argsort(arr)
    sorted_p = arr[order]
    multipliers = np.arange(m, 0, -1)
    adjusted_sorted = sorted_p * multipliers
    adjusted_sorted = np.maximum.accumulate(adjusted_sorted)
    adjusted_sorted = np.minimum(adjusted_sorted, 1.0)
    out = np.empty(m, dtype=float)
    out[order] = adjusted_sorted
    return out.tolist()


def _friedman_stat_from_pivot(pivot: pd.DataFrame) -> float:
    session_names = list(SESSIONS.keys())
    stat, _ = friedmanchisquare(
        pivot[session_names[0]].to_numpy(),
        pivot[session_names[1]].to_numpy(),
        pivot[session_names[2]].to_numpy(),
    )
    return float(stat)


def block_bootstrap_ci(
    complete_days: pd.DataFrame,
    metric: str,
    n_iter: int,
    seed: int,
    ci_level: float,
) -> dict:
    """§7.2 — 95% block-bootstrap CI on UTC-day blocks.

    Note on terminology:
    - For session medians, the returned interval is a percentile bootstrap
      confidence interval for the population median.
    - For the Friedman chi-square statistic, the returned interval is a
      bootstrap distribution of the test statistic under UTC-day block
      resampling. It is NOT a confidence interval for a population
      parameter, and must be reported as such.
    """
    session_names = list(SESSIONS.keys())
    pivot = complete_days.pivot(index="date", columns="session", values=metric)
    pivot = pivot[session_names].dropna()
    if len(pivot) < 3:
        return {"warning": "insufficient_days", "n_days": int(len(pivot))}

    rng = np.random.default_rng(seed)
    n_days = len(pivot)
    days_array = pivot.to_numpy()

    # ── Session median CIs (percentile bootstrap) ─────────────────
    session_medians = {}
    for j, session in enumerate(session_names):
        col = days_array[:, j]
        boot_medians = np.empty(n_iter)
        for it in range(n_iter):
            idx = rng.integers(0, n_days, size=n_days)
            boot_medians[it] = np.median(col[idx])
        alpha = 1.0 - ci_level
        session_medians[session] = {
            "observed_median": float(np.median(col)),
            "ci_low": float(np.quantile(boot_medians, alpha / 2)),
            "ci_high": float(np.quantile(boot_medians, 1 - alpha / 2)),
        }

    # ── Friedman chi-square bootstrap distribution ────────────────
    boot_chi = np.empty(n_iter)
    for it in range(n_iter):
        idx = rng.integers(0, n_days, size=n_days)
        sample = days_array[idx]
        try:
            stat, _ = friedmanchisquare(
                sample[:, 0], sample[:, 1], sample[:, 2])
            boot_chi[it] = stat
        except Exception:
            boot_chi[it] = np.nan
    valid = boot_chi[~np.isnan(boot_chi)]
    if len(valid) == 0:
        friedman_bootstrap = {"warning": "bootstrap_friedman_failed"}
    else:
        alpha = 1.0 - ci_level
        friedman_bootstrap = {
            "observed": _friedman_stat_from_pivot(pivot),
            "bootstrap_quantile_2_5": float(np.quantile(valid, alpha / 2)),
            "bootstrap_quantile_97_5": float(np.quantile(valid, 1 - alpha / 2)),
            "n_valid_iterations": int(len(valid)),
            "note": (
                "Distribution of Friedman chi-square under UTC-day block "
                "resampling. Not a confidence interval for a population parameter."
            ),
        }

    return {
        "n_days": int(n_days),
        "session_medians": session_medians,
        "friedman_chi_square_bootstrap": friedman_bootstrap,
    }


def run_sub_period_stability(obs: pd.DataFrame, metric: str) -> dict:
    """§8.1 — Repeat Friedman + conditional pairwise on sub-periods.

    §6.3 conditionality applies: Wilcoxon only if Friedman is significant
    at alpha = 0.05.
    """
    results = {}
    for label, start, end in SUB_PERIODS:
        start_ts = pd.Timestamp(start, tz="UTC")
        end_ts = pd.Timestamp(end, tz="UTC")
        sub = obs[(obs["date"] >= start_ts) & (obs["date"] <= end_ts)]
        sub_complete = build_complete_days(sub)
        n_days = int(sub_complete["date"].nunique())
        if n_days < 3:
            results[label] = {"warning": "insufficient_days", "n_days": n_days}
            continue
        friedman = friedman_test(sub_complete, metric)
        friedman_significant = friedman.get("p_value", 1) < 0.05
        if friedman_significant:
            wil = wilcoxon_pairwise(sub_complete, metric)
            p_vals = [p["p_value"] for p in wil["pairs"]]
            adj = holm_correction(p_vals)
            for pair, p_adj in zip(wil["pairs"], adj):
                pair["p_value_holm"] = p_adj
            wilcoxon_pairs = wil["pairs"]
            wilcoxon_note = "run (Friedman significant)"
        else:
            wilcoxon_pairs = []
            wilcoxon_note = "not_run (omnibus not significant)"
        results[label] = {
            "friedman": friedman,
            "wilcoxon_pairs": wilcoxon_pairs,
            "wilcoxon_note": wilcoxon_note,
        }
    return results


def apply_interpretation(friedman_results: dict, wilcoxon_results: dict) -> dict:
    """§9 — Apply predefined interpretation rules."""
    sig_metrics = [
        m for m, r in friedman_results.items()
        if r.get("p_value", 1) < 0.05
    ]
    sig_pairs = []
    for metric, w in wilcoxon_results.items():
        if metric not in sig_metrics:
            continue
        for p in w.get("pairs", []):
            if p.get("p_value_holm", 1) < 0.05:
                sig_pairs.append({"metric": metric, "pair": p["pair"]})

    if len(sig_metrics) == 0:
        label = "NO CLEAR STRUCTURE"
    elif len(sig_pairs) == 0:
        label = "WEAK STRUCTURE"
    else:
        label = "STRUCTURE DETECTED"

    return {
        "label": label,
        "significant_metrics": sig_metrics,
        "significant_pairs_after_holm": sig_pairs,
    }


def write_report(summary: dict, path: Path) -> None:
    lines: list[str] = []
    lines.append("# P004 — Diagnostic Report\n")
    lines.append(f"Generated at UTC: {summary['generated_at_utc']}\n")
    lines.append(
        f"Protocol: {summary['protocol_tag']} ({summary['protocol_commit']})\n")
    lines.append(f"Data SHA-256: `{summary['data_sha256']}`\n")
    lines.append(f"Data rows: {summary['data_rows']}\n")
    lines.append("")

    lines.append("## Sessions\n")
    for name, s in summary["session_boundaries"].items():
        lines.append(
            f"- {name}: {s['start_utc']:02d}:00 – {s['end_utc']:02d}:00 UTC ({s['hours']}h)"
        )
    lines.append("")

    lines.append("## Observations\n")
    lines.append(
        f"- Total session-day observations: {summary['observations']['total']}")
    lines.append(
        f"- Complete UTC days: {summary['observations']['complete_days']}")
    lines.append("")

    lines.append("## Metric summary per session\n")
    for metric, by_session in summary["metrics_summary"].items():
        lines.append(f"### {metric}\n")
        lines.append("| Session | n | median | mean | std |")
        lines.append("|---------|---|--------|------|-----|")
        for session, s in by_session.items():
            lines.append(
                f"| {session} | {s['n']} | {s['median']:.6g} | "
                f"{s['mean']:.6g} | {s['std']:.6g} |"
            )
        lines.append("")

    lines.append("## Friedman tests\n")
    lines.append("| Metric | n_days | chi-square | p-value | Kendall's W |")
    lines.append("|--------|--------|------------|---------|-------------|")
    for metric, f in summary["friedman"].items():
        lines.append(
            f"| {metric} | {f.get('n_days', 'NA')} | "
            f"{f.get('statistic', float('nan')):.4g} | "
            f"{f.get('p_value', float('nan')):.6g} | "
            f"{f.get('kendall_w', float('nan')):.4g} |"
        )
    lines.append("")

    lines.append("## Wilcoxon + Holm (only if Friedman significant)\n")
    for metric, w in summary["wilcoxon"].items():
        lines.append(f"### {metric}\n")
        if not w.get("pairs"):
            lines.append(f"Not run: {w.get('note', 'N/A')}\n")
            continue
        lines.append(
            "| Pair | n | n_nonzero | statistic | p-value | p-Holm | rank-biserial |"
        )
        lines.append(
            "|------|---|-----------|-----------|---------|--------|----------------|"
        )
        for p in w["pairs"]:
            lines.append(
                f"| {p['pair']} | {p['n']} | {p['n_nonzero']} | "
                f"{p['statistic']:.4g} | {p['p_value']:.6g} | "
                f"{p.get('p_value_holm', float('nan')):.6g} | "
                f"{p['rank_biserial']:.4g} |"
            )
        lines.append("")

    lines.append(
        "## Bootstrap (95%, UTC-day blocks, 10,000 iterations)\n"
    )
    for metric, b in summary["bootstrap"].items():
        if "warning" in b:
            lines.append(f"### {metric}: {b['warning']}\n")
            continue
        lines.append(f"### {metric}\n")
        lines.append("#### Session medians (percentile bootstrap CI)\n")
        lines.append("| Session | Observed median | CI low | CI high |")
        lines.append("|---------|-----------------|--------|---------|")
        for session, s in b["session_medians"].items():
            lines.append(
                f"| {session} | {s['observed_median']:.6g} | "
                f"{s['ci_low']:.6g} | {s['ci_high']:.6g} |"
            )
        lines.append("")
        fb = b.get("friedman_chi_square_bootstrap", {})
        if "bootstrap_quantile_2_5" in fb:
            lines.append(
                "#### Friedman chi-square bootstrap distribution "
                "(not a confidence interval)\n"
            )
            lines.append(
                f"- Observed chi-square: {fb['observed']:.4g}"
            )
            lines.append(
                f"- Bootstrap 2.5th percentile:  {fb['bootstrap_quantile_2_5']:.4g}"
            )
            lines.append(
                f"- Bootstrap 97.5th percentile: {fb['bootstrap_quantile_97_5']:.4g}"
            )
            lines.append(
                f"- Valid iterations: {fb['n_valid_iterations']}"
            )
            lines.append(f"- Note: {fb['note']}")
        lines.append("")

    lines.append("## Sub-period stability\n")
    for metric, by_period in summary["sub_period_stability"].items():
        lines.append(f"### {metric}\n")
        for period, res in by_period.items():
            if "warning" in res:
                lines.append(
                    f"- {period}: {res['warning']} (n_days={res.get('n_days', 'NA')})"
                )
                continue
            f = res["friedman"]
            lines.append(
                f"- {period}: Friedman p={f.get('p_value', float('nan')):.6g}, "
                f"n_days={f.get('n_days', 'NA')}"
            )
        lines.append("")

    lines.append("## Interpretation (per §9)\n")
    interp = summary["interpretation"]
    lines.append(f"**{interp['label']}**\n")
    if interp["significant_metrics"]:
        lines.append(
            f"- Significant metrics: {', '.join(interp['significant_metrics'])}"
        )
    if interp["significant_pairs_after_holm"]:
        pairs_str = ", ".join(
            f"{p['metric']}:{p['pair']}"
            for p in interp["significant_pairs_after_holm"]
        )
        lines.append(f"- Pairs surviving Holm: {pairs_str}")
    lines.append("")
    lines.append("---\n")
    lines.append("This is a diagnostic result. Not a trading recommendation.")

    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    print("P004 — Diagnostic (read-only against frozen dataset)")

    print(f"\n[1/8] Loading frozen dataset: {DATA_FILE.name}")
    df = load_frozen_dataset()
    print(f"      rows: {len(df)}")

    print("\n[2/8] Building session-day observations (per §4)")
    obs = build_observations(df)
    print(f"      total observations: {len(obs)}")
    print(f"      per session: {obs['session'].value_counts().to_dict()}")

    print("\n[3/8] Filtering complete UTC days (per §6.1)")
    complete = build_complete_days(obs)
    n_complete_days = int(complete["date"].nunique())
    print(f"      complete UTC days: {n_complete_days}")

    print("\n[4/8] Metric summary per session")
    metrics_summary: dict = {}
    for metric in PRIMARY_METRICS:
        metrics_summary[metric] = {}
        for session in SESSIONS.keys():
            vals = complete[complete["session"] == session][metric].to_numpy(
                dtype=float
            )
            metrics_summary[metric][session] = {
                "n": int(len(vals)),
                "median": float(np.median(vals)) if len(vals) else float("nan"),
                "mean": float(np.mean(vals)) if len(vals) else float("nan"),
                "std": float(np.std(vals, ddof=1)) if len(vals) > 1 else float("nan"),
            }

    print("\n[5/8] Friedman tests (per §6.2)")
    friedman_results: dict = {}
    for metric in PRIMARY_METRICS:
        friedman_results[metric] = friedman_test(complete, metric)
        print(f"      {metric}: p={friedman_results[metric]['p_value']:.6g}")

    print("\n[6/8] Wilcoxon + Holm (per §6.3–6.4, conditionally)")
    wilcoxon_results: dict = {}
    for metric in PRIMARY_METRICS:
        f = friedman_results[metric]
        if f.get("p_value", 1) < 0.05:
            wil = wilcoxon_pairwise(complete, metric)
            p_vals = [p["p_value"] for p in wil["pairs"]]
            adj = holm_correction(p_vals)
            for pair, p_adj in zip(wil["pairs"], adj):
                pair["p_value_holm"] = p_adj
            wilcoxon_results[metric] = wil
            print(f"      {metric}: ran Wilcoxon + Holm")
        else:
            wilcoxon_results[metric] = {
                "pairs": [],
                "note": "not_run (omnibus not significant)",
            }
            print(f"      {metric}: skipped (omnibus not sig)")

    print(f"\n[7/8] Bootstrap ({BOOTSTRAP_N} iter, seed {BOOTSTRAP_SEED})")
    bootstrap_results: dict = {}
    for metric in PRIMARY_METRICS:
        bootstrap_results[metric] = block_bootstrap_ci(
            complete, metric, BOOTSTRAP_N, BOOTSTRAP_SEED, CI_LEVEL
        )
        print(f"      {metric}: done")

    print("\n[8/8] Sub-period stability (per §8.1)")
    sub_period_results: dict = {}
    for metric in PRIMARY_METRICS:
        sub_period_results[metric] = run_sub_period_stability(obs, metric)
        print(f"      {metric}: done")

    interpretation = apply_interpretation(friedman_results, wilcoxon_results)
    print(f"\nInterpretation: {interpretation['label']}")

    summary = {
        "experiment": "P004",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "protocol_commit": "a393aad",
        "protocol_tag": "p004-protocol-locked",
        "data_sha256": EXPECTED_SHA256,
        "data_rows": int(len(df)),
        "session_boundaries": {
            name: {"start_utc": start, "end_utc": end, "hours": end - start}
            for name, (start, end) in SESSIONS.items()
        },
        "observations": {
            "total": int(len(obs)),
            "complete_days": n_complete_days,
        },
        "metrics_summary": metrics_summary,
        "friedman": friedman_results,
        "wilcoxon": wilcoxon_results,
        "bootstrap": bootstrap_results,
        "sub_period_stability": sub_period_results,
        "interpretation": interpretation,
    }
    OUTPUT_JSON.write_text(json.dumps(summary, indent=2, default=str))
    write_report(summary, OUTPUT_MD)

    print(f"\nWrote: {OUTPUT_JSON.name}")
    print(f"Wrote: {OUTPUT_MD.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
