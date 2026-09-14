text
# Crypto Strategy Research Lab

**A reproducible research pipeline for systematic trading strategies.**

The goal isn't to find a strategy that backtests well. The goal is
to find out whether the evidence survives validation.

This repository contains the pipeline, two completed experiments
(both rejected under pre-registered criteria), and the process
lessons from building and running it.

---

## What this repo is

An end-to-end research pipeline for systematic trading hypotheses:
Research Question
↓
Hypothesis + Economic Mechanism
↓
Causal Specification
↓
Pre-Registration (frozen)
↓
Data Freeze (SHA-256)
↓
Baseline Backtest
↓
Leakage Validation
↓
Walk-Forward
↓
Bootstrap
↓
Independent Audit
↓
Frozen Verdict

text

Every stage produces frozen, auditable artifacts. Every verdict
is derived from pre-registered criteria. Negative results are
first-class outputs.

---

## Experiments

| # | Hypothesis | Assets | TF | WFO | Bootstrap | Final |
|---|------------|--------|----|-----|-----------|-------|
| 001 | RSI mean reversion (14/30/50) | BTC-USD | 4H | FAIL | INCONCLUSIVE | **REJECTED** |
| 002 | Cross-sectional momentum (lookback=6, top-1) | BTC/ETH/SOL | 4H | REJECTED | INCONCLUSIVE | **REJECTED** |

Both specifications were frozen before execution. Neither was
modified after seeing results. Full verdicts are inside each
experiment's folder.

### Experiment 001 — RSI mean reversion

- Data: BTC-USD 4H, frozen 4,334 bars (2024-09 → 2026-09)
- Baseline: 31 trades, net_pnl = +$1,393.73, Sharpe = 0.313
- Leakage suite: PASS
- Walk-forward (50/50): IS Sharpe = +1.558, OOS Sharpe = −0.757 → **FAIL**
- Bootstrap: CI includes 0 → INCONCLUSIVE
- **Verdict: REJECTED / NOT PROMOTED**

### Experiment 002 — Cross-sectional momentum

- Data: BTC/ETH/SOL 4H, common 4,334-bar grid (intersection of sources)
- Baseline: 1,159 trades, net_pnl = −$78,027.73, Sharpe = −0.859
- Leakage suite: PASS (with cross-asset-specific tests)
- Walk-forward (50/50): OOS Sharpe = −2.344, OOS mean_spread < 0 → **REJECTED**
- Bootstrap: strategy layer FAIL, predictive layer INCONCLUSIVE
- **Verdict: REJECTED / NOT PROMOTED**

---

## What's inside
crypto-strategy-research-lab/
├── README.md ← this file
├── OVERVIEW.md ← research overview + experiment matrix
├── REPRODUCE.md ← reproducibility contract
├── PROTOCOL.md ← program-level research rules
├── LICENSE ← MIT (code)
├── LICENSE-DOCS ← CC BY 4.0 (documentation / reports)
│
├── engine/ ← data loader + backtest engines
├── strategies/ ← strategy implementations
├── validation/ ← leakage / oracle tests
├── tests/ ← pytest suite (60+ tests)
│
├── data/ ← frozen snapshots (MANIFEST + SHA-256)
├── experiments/ ← per-experiment artifacts (frozen)
├── knowledge/lessons/ ← process lessons
├── reports/ ← program-level reports + roadmap
└── assets/ ← pointer (no plots committed)


---

## Core principles

1. **Pre-registration before results.** Specifications are frozen
   before execution. Any change after seeing results requires a new
   experiment.

2. **Negative results are first-class outputs.** A rejected
   hypothesis is a successful experiment.

3. **Frozen data + code + protocol = reproducibility.** Every result
   ties to a specific commit, a specific data SHA-256, and a
   specific pre-registration.

4. **Independent audit.** Every accounting and results artifact is
   reconstructed independently before being frozen.

5. **Layered validation.** Causal correctness, out-of-sample
   persistence, and statistical uncertainty are evaluated
   separately. Later layers cannot rescue earlier failures.

---

## Why this repo exists

Most public backtests optimize for "looks good." This repo does the
opposite: it builds infrastructure whose purpose is to reject
hypotheses cleanly and reproducibly.

Both experiments here were rejected. The reusable asset is not
either strategy — it's the pipeline itself.

---

## Quick start

See REPRODUCE.md for the full reproduction contract.
git clone https://github.com/darangworks/crypto-strategy-research-lab.git
cd crypto-strategy-research-lab
pip install -e ".[dev]"

pytest tests/ -q
python experiments/001_rsi_btc_4h/run_experiment.py
python experiments/002_momentum_btc_eth_sol_4h/run_experiment.py


Frozen-result reproduction does not require internet access.

---

## Lessons

Seven process lessons from Experiment 001 and seven from
Experiment 002 are documented under knowledge/lessons/. They cover
provenance discipline, cross-sectional data construction, the
difference between sign-based and CI-based criteria, and the value
of independent audit even when the audit itself has bugs.

---

## License

- Code (engine, strategies, validation, tests, runners): MIT.
  See LICENSE.
- Documentation and research reports (README, OVERVIEW,
  REPRODUCE, PROTOCOL, VERDICTs, lessons, reports): CC BY 4.0.
  See LICENSE-DOCS.

---

## Citation

Darang, M. (2026). Crypto Strategy Research Lab: A reproducible
research pipeline for systematic trading strategies.
https://github.com/darangworks/crypto-strategy-research-lab