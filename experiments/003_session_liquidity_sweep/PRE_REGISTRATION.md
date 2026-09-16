

# Experiment 003 — Session Liquidity Sweep with Structural Confirmation

## Pre-Registration
### Causal Specification v0.5 — FINAL LOCKED FOR GATE 1

### 0. Research Question & Scope
> آیا شکست و بازگشت از یک محدوده قیمتی مشخص‌شده در یک session (Asian Range)، که در session بعدی (London) با یک تأیید ساختاری عینی (FVG) همراه شود، در داده‌های خارج از نمونه (OOS) و پس از کسر هزینه‌های معاملاتی، شواهدی از بازده پیش‌بینانه نسبت به یک انتخاب جهت تصادفی در همان موقعیت‌ها ایجاد می‌کند؟

**Scope Clarification:**
The primary experiment evaluates whether the **directional choice** associated with the qualifying sweep/FVG signal adds predictive information beyond a random directional choice at the same signal timestamps.
It **does not separately test** whether the signal timestamps themselves are superior to unconditional random entry opportunities.

---

### 1. Universe, Instrument & Data Source

| فیلد | تعریف |
|---|---|
| **Data Provider** | TBD — قفل در Gate 2 |
| **Instrument** | XAU/USD (Gold Spot vs USD) |
| **Timeframe** | 15-minute (M15) |
| **Timezone** | UTC |
| **Price Fields** | OHLC |
| **Missing Bars** | اگر یک bar M15 غایب باشد، آن trading day از experiment حذف می‌شود |
| **Duplicate Timestamps** | اولین رکورد نگه داشته می‌شود؛ موارد بعدی حذف و مستند می‌شوند |
| **Weekend / Market Closure** | شنبه/یکشنبه و روزهای با closure غیرمنتظره حذف و مستند می‌شوند |
| **Data Revisions** | Snapshot فریزشده با SHA-256. هیچ اصلاح بعدی مجاز نیست |
| **Period** | TBD — قفل در Gate 2 |
| **Commission** | TBD — قفل در Gate 2 |
| **Slippage** | TBD — قفل در Gate 2 |

**قانون هزینه‌ها:** هیچ backtest‌ای قبل از قفل شدن اعداد costs در pre-registration اجرا نمی‌شود.

---

### 2. Trading Day Definition
```text
Trading Day D:
  ├─ Asian Range:      D 17:00 UTC  →  D+1 00:00 UTC
  ├─ London Sweep:     D+1 02:00 UTC →  D+1 07:00 UTC
  ├─ Confirmation:     D+1 02:00 UTC →  D+1 12:00 UTC
  └─ Trade Exit:       حداکثر تا D+1 23:59 UTC
```

---

### 3. Asian Range (بدون Exclusion Filter)
* **Window:** `D 17:00 UTC` تا `D+1 00:00 UTC`
* **Computation:**
  * `Asian_High[D]` = `max(high)` در تمام کندل‌های M15 داخل window
  * `Asian_Low[D]` = `min(low)` در تمام کندل‌های M15 داخل window
* **Exclusion Filter:** **هیچ فیلتری روی range width اعمال نمی‌شود.**

---

### 4. Liquidity Sweep Definition
* **Window:** `D+1 02:00 UTC` تا `D+1 07:00 UTC`
* **Bullish Sweep:** حداقل یک کندل M15 با `low < Asian_Low[D]` و `close > Asian_Low[D]`
* **Bearish Sweep:** حداقل یک کندل M15 با `high > Asian_High[D]` و `close < Asian_High[D]`
* **No minimum penetration threshold.**
* **Availability:** در close همان کندل M15 تأیید می‌شود.

---

### 5. Structural Confirmation (FVG)
* **Window:** `D+1 02:00 UTC` تا `D+1 12:00 UTC`
* **Causality Rule:** FVG باید **strictly after** qualifying sweep candle رخ دهد.
* **Bullish FVG:** `low[t] > high[t-2]`
* **Bearish FVG:** `high[t] < low[t-2]`
* **First FVG Rule:** Qualifying FVG اولین timestamp‌ای است که شرط FVG پس از qualifying sweep true می‌شود.

---

### 6. Signal State Machine (Causal Multi-Sweep Handling)
```text
STATE 0: NO SWEEP → (first sweep) → STATE 1
STATE 1: CANDIDATE SWEEP
  - If opposite sweep BEFORE FVG → STATE_CANCELLED
  - If matching FVG (strictly after sweep) → STATE 2
STATE 2: CONFIRMED SIGNAL → (next bar open) → STATE 3
STATE 3: TRADE OPEN (Subsequent sweeps IGNORED) → (exit) → STATE 4
STATE 4: CLOSED
```
**قانون طلایی:** یک معامله که وارد STATE_TRADE_OPEN شده، **هرگز** نمی‌تواند بر اساس اتفاقات بعد از ورود، retroactively حذف یا باطل شود.

---

### 7. Entry & Execution
* **Signal Confirmation:** در close کندل `t` (transition به STATE_CONFIRMED).
* **Execution:** در **open کندل `t+1`**.
* **Direction:** Bullish Sweep + Bullish FVG → Long / Bearish Sweep + Bearish FVG → Short
* **Position Sizing:** 100% equity

---

### 8. Exit Rules
* **Stop Loss (SL):** Long = `Asian_Low[D]` / Short = `Asian_High[D]` (بدون offset)
* **Take Profit (TP):** Risk:Reward = 1:2.5
* **Intrabar Same-Bar Rule:** اگر در یک کندل M15 هم TP و هم SL لمس شوند، **SL اول اجرا می‌شود** (SL-first rule).
* **Time Exit:** اگر تا `D+1 23:59 UTC` هیچ SL یا TP فعال نشود، پوزیشن در close آخرین کندل روز بسته می‌شود.

---

### 9. Chronological Split
* **70% earliest chronological data:** Development / specification-freeze period.
  * **Crucial Constraint:** The 70% development period is **not used for post-hoc selection** of the hypothesis, entry rules, exit rules, benchmark, or primary evidence framework. All such decisions must be frozen before the OOS period is evaluated.
* **30% latest chronological data:** Strict Out-of-Sample (OOS) evaluation period.
  * پس از شروع این دوره، **هیچ تغییری** در specification مجاز نیست.

---

### 10. Preregistered Benchmark (Directional-Choice)
* **Signal Timestamps:** دقیقاً همان timestamp های entry استراتژی اصلی
* **Entry Prices:** دقیقاً همان open[t+1] استراتژی اصلی
* **SL & TP Rules:** دقیقاً همان قوانین (Asian_High/Low, 1:2.5, SL-first)
* **Direction Sampling:** مستقل، `P(Long) = P(Short) = 0.5`
* **Random Seed:** Fixed — در Gate 2 ثبت می‌شود
* **Number of Replications:** N = 10,000
* **Transaction Costs:** دقیقاً برابر با استراتژی اصلی

---

### 11. Evidence Evaluation Framework (FINAL)

#### Primary Statistic:
> **Mean net return per trade** (پس از کسر هزینه‌های معاملاتی predefined).

#### Primary Comparison:
```text
Strategy mean net return per trade
MINUS
paired random-benchmark mean net return per trade
(computed on identical signal timestamps)
```

#### Bootstrap Procedure (LOCKED):
For each trade, compute the paired performance difference:
```text
d_i = strategy_net_return_i - benchmark_net_return_i
```
The primary uncertainty interval is obtained by **resampling the paired trade-level differences d_i with replacement**.
* **Number of bootstrap replications:** N = 10,000
* **Confidence interval:** two-sided percentile 95% CI (2.5th and 97.5th percentiles).
* **Constraint:** The paired structure must be preserved during resampling. Strategy and benchmark returns must never be resampled independently.

#### Decision Rule:

| وضعیت | شرط |
|---|---|
| **PROMOTED** | Lower bound of the preregistered 95% CI > 0 |
| **REJECTED** | Upper bound of the preregistered 95% CI < 0 |
| **INCONCLUSIVE** | 95% CI contains 0 |

#### Secondary / Descriptive Metrics (گزارش می‌شوند، اما decision-driving نیستند):
Net P&L, Total trade count, Sharpe ratio, Profit Factor, Win rate, Maximum drawdown, Equity curve.

---

### 12. Secondary / Exploratory Analyses
* Asian range width distribution
* Sweep penetration depth
* Time-of-day distribution of signals
* **Cross-Asset Robustness:** XAG/USD یا EUR/USD

---

### 13. Validation Protocol
1. **Leakage Tests:** حداقل 7 تست مشابه Project 1 و 2
2. **Random-Walk Oracle Test:** استراتژی روی synthetic random walk نباید edge داشته باشد
3. **Chronological Consistency**
4. **Accounting Parity**
5. **Bootstrap:** همان procedure تعریف‌شده در بخش 11

---

### 14. Architectural Constraint
* **Minimum infrastructure only.**
* اصل: *"Experiments exercise the architecture; experiments do not justify architecture."*

---

### 15. Locking Statement (Immutable)
پس از PASS شدن این سند در Gate 1:
> هیچ تغییری در hypothesis، inclusion/exclusion criteria، primary statistic، bootstrap procedure، evidence framework، entry/exit rules، benchmark specification، trading-day definition، یا state machine پس از مشاهده نتایج OOS مجاز نخواهد بود.
>
> هرگونه ایده جدید (تغییر SL/TP، اضافه کردن Range Filter، تغییر Penetration Threshold، و غیره) باید به‌صورت یک **experiment جدید (Experiment 004+)** pre-registered شود، نه به‌عنوان اصلاح Experiment 003.
