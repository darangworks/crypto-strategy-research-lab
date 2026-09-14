# Open Quant Research Program — Roadmap v1 (Frozen 2026-09-14)

## Mission

Researching systematic trading strategies in public, with reproducible
experiments and falsification-first validation.

---

## Architecture (frozen)

Research Core + Validation Core + Knowledge Layer + Distribution Layer
+ lightweight Research Memory + later Research Copilot.

**Distribution is an OUTPUT of the system, not a research engine.**

---

## Operating Loop

Idea -> Hypothesis -> Causal Specification -> Pre-registration -> Data
-> Experiment -> Validation -> Evidence -> Verdict -> Publication
-> Knowledge -> Next Hypothesis

---

## Execution Roadmap (evidence-driven, not calendar-driven)

**Phase 0 — Foundation (DONE)**
- Project 1: Causal kNN Crypto Strategy — COMPLETE (negative)
- Project 2: Crypto Strategy Research Lab — Experiment 001 CLOSED

**Phase 1 — Minimal Public Release (days–weeks)**
- Project 1 minimal release package
- Project 2 minimal release package

**Phase 2 — Selective Distribution**
Per-project, per-platform. Not every project needs every channel.
- Project 1: LinkedIn (done) -> X -> r/algotrading -> r/quant
- Project 2: LinkedIn -> X -> Reddit
- Medium / Telegram only if content justifies

**Phase 3 — Experiment 002**
New pre-registration, new hypothesis, same validation philosophy.
No RSI(14/30/50) tuning.

**Phase 4 — Multiple Experiments (002, 003, 004)**
Accumulate evidence that the Lab is reusable before Project 3.

**Phase 5 — Project 3 (Statistical / ML)**
Only if Phase 4 confirms infrastructure is reusable.

**Phase 6 — Project 4 (Technical + Fundamental)**

**Phase 7 — Project 5 (Tehran Market Transfer)**

**Phase 8 — Research Copilot (deferred)**

---

## Release Package Standard (per project)

Minimum viable:
- `README.md`       — public summary, non-technical
- `REPRODUCE.md`    — one-command reproduction
- `RESULTS.md`      — reported results and factual observations;
                      no final methodological verdict
- `VERDICT.md`      — methodological conclusion
- `METHODOLOGY.md`  — leakage + WFO + bootstrap explained
- `assets/`         — equity curves, distributions

Deferred to later release:
- `CITATION.cff`
- LICENSE polish
- graphical assets

**Rule:** each file is either "what happened" (RESULTS) or
"what the evidence means" (VERDICT). No mixing.

---

## Distribution Strategy

Three tiers:
- Short  (< 500 words)    -> X / LinkedIn
- Medium (1000–2000 w)    -> Reddit / Medium / Telegram
- Long   (repo + docs)    -> GitHub

Rules:
- Negative results headline the negative
- No "edge" or "profitable" claims
- Link to repo in first line
- Same numbers across channels
- Not every project needs every channel

---

## Anti-Patterns (explicitly forbidden)

1. Architecture creep without experimental justification
2. Parameter tuning after seeing results
3. Post-hoc rescue of failed layers
4. Converting research into content production
5. Calendar-driven project launches
6. **Premature generalization** — claiming that a methodology or
   finding generalizes beyond the tested strategy, market, data, or
   validation scope.

Correct language:
> This methodology has been demonstrated on the tested
> specifications; its generalization to other strategy families
> remains an open question.

---

## Current State (2026-09-14)

Project 1:  Causal kNN Crypto Strategy     — COMPLETE (negative)
Project 2:  Crypto Strategy Research Lab   — Experiment 001 CLOSED
                                              - Baseline:  FROZEN
                                              - Leakage:   PASS
                                              - WFO:       FAIL
                                              - Bootstrap: INCONCLUSIVE
                                              - Overall:   NOT PROMOTED

---

## Next Action

Minimal Release Package for Project 1 (in its own repo).