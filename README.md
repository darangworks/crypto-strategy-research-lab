# Crypto Strategy Research Lab

A reproducible research system for testing, validating, and falsifying systematic crypto trading strategies.

---

## Why this project exists

**Project 1** asked whether I could rigorously validate a strategy.
**Project 2** asks whether I can build a reproducible system for researching many strategies.

The goal is not to find a profitable strategy.
The goal is to build the infrastructure that makes it possible to discover whether robust strategies exist.

---

## What this project is not

- Not a collection of TradingView scripts
- Not a backtest gallery
- Not a signal service

---

## Research Protocol

See PROTOCOL.md for the full protocol.

**Negative results are first-class outputs.**

---

## Structure

engine/        - execution infrastructure
validation/    - statistical validation
strategies/    - individual strategies
experiments/   - research campaigns
results/       - outcomes
reports/       - written reports
data/          - frozen snapshots

---

## Strategy API

1. hypothesis()         - economic rationale
2. compute_features(df) - causal feature engineering
3. target_position(df)  - desired position at each bar

The engine handles execution, costs, and sizing.

---

## Current Status

v0.1 - Infrastructure (no strategies yet)

- [x] Repository structure
- [x] Strategy API defined
- [x] Research protocol defined
- [ ] Data loader
- [ ] Backtest engine
- [ ] Cost model
- [ ] Validation modules
- [ ] First training strategy

---

## License

Code: MIT
Documentation: CC BY 4.0
