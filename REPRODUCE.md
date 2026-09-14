# Reproducibility Contract

Instructions to reproduce every frozen result in this repository.

Frozen-result reproduction requires no internet access.

---

## Contract

1. No mutable market data. All results are tied to the frozen CSVs under data/. Reproduction never downloads new data.

2. SHA-256 verification is mandatory. Every frozen CSV has a SHA-256 recorded in its MANIFEST.md. Reproduction verifies it.

3. Deterministic seeds. All randomized procedures (bootstrap, synthetic tests) use documented seeds. Default base seed is 20260913.

4. Clean-tree requirement. Baseline, walk-forward, and bootstrap runners refuse to execute on a dirty git working tree.

5. Exact reproduction expected. Reruns from a clean tree must reproduce the frozen artifacts exactly (float-point, unless a tolerance is documented).

---

## Requirements

- Python 3.13 (tested on 3.13.3)
- Python packages in pyproject.toml:
  - numpy >= 1.24 (tested on 2.2.1)
  - pandas >= 2.0 (tested on 2.3.3)
  - scipy >= 1.10
  - pyyaml >= 6.0
  - requests >= 2.31
  - pytest >= 7.4
- Approx. 500 MB disk space.

---

## Step 1 — Clone and install

git clone https://github.com/darangworks/crypto-strategy-research-lab.git
cd crypto-strategy-research-lab
pip install -e ".[dev]"

---

## Step 2 — Verify Python environment

python --version
python -c "import numpy, pandas; print(numpy.__version__, pandas.__version__)"

Expected: Python 3.13.x, numpy 2.x, pandas 2.x.

---

## Step 3 — Verify frozen data hashes

Compare each SHA-256 in data/001_btc_4h/MANIFEST.md and data/002_btc_eth_sol_4h/MANIFEST.md against the corresponding CSV files.

Manually verify each SHA-256 against its MANIFEST.md.

---

## Step 4 — Run the test suite

pytest tests/ -q

Expected: 60+ tests pass. Includes:

- engine unit tests
- strategy specification tests (Exp 001, Exp 002)
- leakage tests (single-asset + cross-sectional)
- walk-forward specification tests

---

## Step 5 — Reproduce Experiment 001 (RSI mean reversion)

python experiments/001_rsi_btc_4h/run_experiment.py
python experiments/001_rsi_btc_4h/run_walkforward.py
python experiments/001_rsi_btc_4h/run_bootstrap.py

Expected artifacts:

- results.json (baseline): 31 trades, net_pnl approx +1393.7348, sharpe approx 0.3134
- walkforward.json: OOS sharpe approx -0.7571905
- bootstrap.json: CI includes 0, INCONCLUSIVE

Note: run_experiment.py requires a clean git working tree.

---

## Step 6 — Reproduce Experiment 002 (cross-sectional momentum)

python experiments/002_momentum_btc_eth_sol_4h/freeze_data_exp002.py

Note: this step reproduces ETH/SOL frozen CSVs from Binance public API (requires internet). BTC is byte-exact copied from Exp 001 (no download). If Binance is unreachable from your network, skip this step and use the pre-existing frozen CSVs (already in repo).

python experiments/002_momentum_btc_eth_sol_4h/run_experiment.py
python experiments/002_momentum_btc_eth_sol_4h/run_walkforward.py
python experiments/002_momentum_btc_eth_sol_4h/run_bootstrap.py

Expected artifacts:

- results.json (baseline): 1,159 trades, net_pnl approx -78,027.73, sharpe approx -0.859
- walkforward.json: OOS sharpe approx -2.3441, OOS mean_spread approx -0.00011844
- bootstrap.json: strategy layer FAIL, predictive layer INCONCLUSIVE

---

## Step 7 — Independent audits

python experiments/002_momentum_btc_eth_sol_4h/audit_signals.py
python experiments/002_momentum_btc_eth_sol_4h/audit_portfolio.py
python experiments/002_momentum_btc_eth_sol_4h/audit_walkforward.py
python experiments/002_momentum_btc_eth_sol_4h/audit_b1_null.py

Expected: all audits PASS with max abs diff = 0.0.

---

## Tolerance for reproduction

| Metric | Tolerance |
|--------|-----------|
| Trade count | exact |
| Trade entry/exit indices | exact |
| Net PnL | rtol 1e-9, atol 1e-6 |
| Sharpe | rtol 1e-9 |
| Bootstrap CI bounds | rtol 1e-9 |
| Equity curve | rtol 1e-9, atol 1e-6 |
| Data SHA-256 | exact |

If your rerun differs by more than these tolerances, please open an issue with:

- git commit hash
- python / numpy / pandas versions
- the specific artifact that differed and by how much

---

## Notes on dependency on external services

- Experiment 001 baseline / WFO / bootstrap: no external services required.
- Experiment 002 freeze script: queries Binance public klines API. Not required for reproducing frozen results; the frozen CSVs are already in the repo.
- Experiment 002 baseline / WFO / bootstrap: no external services required.

---

## Data Contract

Frozen snapshots are immutable. Any modification of strategy, features, thresholds, filters, or execution logic requires a new experiment with its own pre-registration, not a modification of an existing frozen snapshot.

Do not overwrite data/*/MANIFEST.md. Do not edit frozen CSVs. Do not re-run freeze scripts against existing snapshots.