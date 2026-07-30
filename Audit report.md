# Π Framework — Code & Data Integrity Audit Report

**Date:** 2025-02-17
**Scope:** Full repository review (Cases/, run_*.py, sensitivity/, Data/)
**Method:** Automated numerical verification + logic review + manipulation screening

---

## Executive Summary

The frozen baseline numerical results are reproducible from the committed CSV data. The repository review found no direct evidence of deliberate data alteration, but code inspection alone cannot establish the absence of selective case, variable, window, or analysis choices. Several design and reporting limitations are documented below.

**Scope-limited assessment:** No direct evidence of data alteration was identified in the audited repository state. Indicators:

- Unfavorable results, including Supply Chain p=0.26, Repo Sep=0.7×, and non-redundancy failures, are retained in the repository and supporting documentation; their final manuscript placement is determined separately in revision.
- The retained transform window k=5 has a one-business-week interpretation and does not maximize tested separation; k=10 yields 21.1× versus 17.9× for k=5. The audit cannot independently establish the original selection process.
- Across the 8 examined random seeds, z-scores varied by approximately ±0.5 and the reported significance decisions were unchanged. This is a limited seed-sensitivity check, not proof of seed independence.
- No outlier-removal operation, NaN manipulation, or post hoc row exclusion was identified in the audited CSV files and inspected pipeline code.

---

## Issues Found (by severity)

### 🔴 LEVEL 1: Must Fix Before Submission

#### 1.1 τ₀ Definition Inconsistency

**Problem:** The manuscript Methods section states "τ₀ = 1/252 year for business-day data" but `run_all.py` (which generates all paper results) uses `dt = 1/365` for ALL daily cases via `estimate_dt()`.

**Evidence:**
- `pi_calculator.py` (Case 1 standalone): `BUSINESS_DAYS_PER_YEAR = 252`, so `dt = 1/252`
- `run_all.py` line 98-99: `return 1.0/12 if avg_gap > 20 else 1.0/365`
- Table 2 values (Π_crisis=1.2579 for 2008) match `dt=1/365`, NOT `dt=1/252`

**Impact on results:** None — separation ratios are dt-invariant (dt cancels in the ratio). Verified: Sep=18.6× regardless of dt=1/252, 1/365, or 1/100.

**Fix:** Update manuscript Methods to state "τ₀ = 1/365 year for all daily cases, 1/12 year for monthly cases." Alternatively, update `run_all.py` to use dt=1/252 for business-day data and recalculate Table 2 absolute values (ratios won't change).

#### 1.2 COVID-19 Collapse Date Dual Definition

**Problem:** Two different collapse dates are used for COVID-19:
- `case4_covid.py`: `COLLAPSE_DATE = "2020-03-11"` (WHO pandemic declaration)
- `run_all.py`: `collapse = "2020-03-23"` (S&P 500 bottom)

Table 5's exploratory pattern assignment uses 2020-03-23 (from `run_all.py`), yielding Π@collapse = 10.3%.

**Fix:** Unify to one date and document the rationale. If using 2020-03-23, update `case4_covid.py` to match and note it represents the financial bottom, not the epidemiological declaration.

#### 1.3 COVID-19 Exploratory-Label Boundary Sensitivity

**Problem:** COVID-19 Π@collapse/Π_max = 10.3%, and the Explosive/Brittle boundary is exactly 10%. The classification as "Brittle" depends on a 0.3 percentage point margin.

**Fix:** Acknowledge this boundary case explicitly in the manuscript. Consider noting that COVID-19 sits at the Explosive-Brittle boundary. The classification is code-correct but should not be presented as definitive.

---

### 🟡 LEVEL 2: Should Fix for Transparency

#### 2.1 Nested Control Design (Crisis Window Contains Control)

**Problem:** In 4 of 5 cases, 100% of the control data is a subset of the crisis window:

| Case | Crisis | Control | Overlap |
|------|--------|---------|---------|
| 2008 Financial | 2005-01 to 2009-03 | 2004-01 to 2006-06 | 60% of control |
| Terra-Luna | 2021-07 to 2022-07 | 2021-07 to 2022-01 | 100% |
| Fukushima | 2010-06 to 2011-09 | 2010-06 to 2011-02 | 100% |
| COVID-19 | 2019-07 to 2020-04 | 2019-07 to 2020-01 | 100% |
| Supply Chain | 2019-02 to 2022-12 | 2019-02 to 2020-06 | 100% |

This means Π_crisis includes the control period's stress plus additional crisis stress, so Π_crisis > Π_control is partly guaranteed by construction (longer window).

**Additional diagnostic:** Time-normalized mean stress S̄ = Π/T remains higher in the selected crisis windows than in the selected controls. This reduces the direct duration effect but does not remove the nested-window, case-selection, or variable-selection limitations. The permutation procedure evaluates temporal channel alignment within the specified windows and should not be treated as independent validation of the window design.

| Case | Sep(Π) | Sep(S̄) |
|------|--------|--------|
| 2008 Financial | 18.6× | 10.8× |
| Terra-Luna | 1.9× | 1.1× |
| Fukushima | 2.3× | 1.2× |
| COVID-19 | 3,627× | 2,573× |
| Supply Chain | 9.2× | 3.3× |

**Fix:** Acknowledge the nested design and report the time-normalized contrasts as descriptive supplementary evidence rather than confirmation.

#### 2.2 COVID-19 Floor Effect (3,627× Separation)

**Problem:** The extreme separation is mechanically amplified by the multiplicative structure. In the control period, ρ (COVID cases) = 0 for 146/149 days (98%), making S(t) = 0 by construction. This creates a near-zero denominator.

**Fix:** Note that the 3,627× figure partly reflects a zero-baseline floor effect. Under the selected variables and multiplicative construction, the transition produces a large ratio, but its magnitude is not directly comparable with the other cases and is not a general measure of discriminative performance.

#### 2.3 Supply Chain Ablation Caveat

**Problem:** The manuscript claims "Multiplicative wins 5/5." In the full ablation benchmark, Supply Chain is won by Ψ×Ω (34.5×) rather than ρ×Ψ×Ω (9.2×). The 3-channel product LOSES in this case because the ρ channel (durable goods PCE) dilutes the signal.

The claim counts COVID-19 where the multiplicative advantage is driven by the floor effect noted above.

**Fix:** The README and manuscript already acknowledge this partially. Strengthen by saying "Multiplicative wins 4/5 cases; in Supply Chain, the 2-channel Ψ×Ω outperforms due to a weakly informative ρ channel."

#### 2.4 Supplementary S1 P-limit Baseline Discrepancy

**Problem:** `run_plimit_sensitivity()` computes P-limits from the *control period raw values* (`ct['rho']`), while the main analysis computes P-limits from a *stable period* defined in each case config. For the 2008 case, stable=[2005-01, 2007-06] vs control=[2004-01, 2006-06] — overlapping but not identical.

**Impact:** S1 is internally consistent, but its P-limits differ from the main analysis. The unchanged separation across percentiles is primarily an algebraic scale-invariance property because common normalization factors cancel in the crisis/control ratio; it is not independent empirical robustness evidence.

**Fix:** State that S1 uses control-period P-limits, while the main analysis uses predefined stable periods, and describe S1 as a scale-invariance diagnostic.

---

### 🟢 LEVEL 3: Minor / Cosmetic

#### 3.1 FRED Series ID: FEDFUNDS vs DFF

`config.py` uses `FRED_SERIES['rho'] = 'FEDFUNDS'`, but the manuscript Table 1 says "DFF." Both refer to the Federal Funds Effective Rate on FRED. The series ID on FRED is actually `DFF` (daily) and `FEDFUNDS` (monthly). Since the code uses 5-day changes on daily data, `DFF` is the correct FRED ID.

**Fix:** Update `config.py` to `'DFF'` for consistency with manuscript.

#### 3.2 Terra-Luna Ablation Rounding

Manuscript ST5 reports ρ-only ablation for Terra-Luna as 1.7×. Code precise value is 1.65×, which rounds to 1.7 (conventional) or 1.6 (banker's rounding).

**Fix:** Use 1.7 with a note that all ablation values are rounded to one decimal place using conventional rounding, or use 1.6 for consistency.

#### 3.3 ST15 Baseline vs Table 2 Baseline

ST15 baseline (k=5) shows Sep=17.9× (N=1045/608), while Table 2 shows Sep=18.6× (N=990/574). The difference comes from wider date alignment in `sensitivity_delta_k.py` which fetches fresh FRED data with slightly different index alignment.

**Fix:** Add footnote: "ST15 uses independently fetched data with wider date alignment; minor differences from Table 2 baseline reflect index alignment, not methodological inconsistency."

---

## Reproduced Implementation and Baseline Checks

| Check | Result |
|-------|--------|
| S(t) = ρ̃ × Ψ̃ × Ω̃ implementation | Max error < 10⁻¹⁴ across all cases |
| Π = cumsum(S·dt) cumulative integral | Exact match |
| P-limit calibration (99th percentile) | Correct, with 1e-10 floor for division safety |
| No negative values in normalized channels | Confirmed all ≥ 0 |
| Permutation test: independent shuffling | ρ, Ψ, Ω shuffled independently ✅ |
| Permutation test: one-sided p-value | `p = mean(shuffled >= actual)` ✅ |
| Fisher combined p-value | 1.66×10⁻¹¹ verified ✅ |
| Exploratory pattern-label thresholds | Legacy assignments reproduced for all 5 cases; this does not validate the labels as system classes |
| Random seed sensitivity | Significance decisions unchanged across the 8 examined seeds; scope is limited to those seeds |
| Equal-weight implementation | No explicit channel coefficients are present in S = ρ̃×Ψ̃×Ω̃; normalization choices still affect implicit scaling |
| Stored-data integrity checks | 0 NaN and 0 Inf values in the audited CSV files; no exclusion operation identified in the inspected pipeline |
| dt cancels in separation ratio | Verified algebraically and numerically ✅ |
| Unfavorable stored results | Supply Chain p=0.26, Repo 0.7×, and max|r|=0.952 are present in the repository and documentation |
| Transform-window record | k=5 is not the separation-maximizing tested value; repository inspection cannot independently establish the original selection process |
| Frozen baseline execution | The audited baseline scripts completed and reproduced the recorded CSV/text outputs; the revised CI configuration is tracked separately |
| Frozen manuscript-baseline alignment | Recorded baseline tables matched the pre-revision outputs; retired analyses and revised interpretations are excluded from the new evidentiary package |

---

## Data Manipulation Assessment

**Question:** Is there evidence of intentional data massage or result-favorable manipulation?

**Answer: No.**

Evidence for this conclusion:

1. **Unfavorable additional results are retained.** Dot-com, 2019 Repo, and Thailand Flood include weak, negative, or non-significant findings. Their inclusion improves transparency but does not by itself rule out selection effects in the primary five cases.

2. **The retained transform window is not the tested optimum.** k=10 gives higher separation than k=5. The one-week interpretation provides a rationale for k=5, but the audit cannot independently reconstruct or preregister the original selection process.

3. **Unfavorable results are documented.** Supply Chain's non-significant permutation result (p=0.26), high collinearity (max|r|=0.952), and Ψ×Ω ablation superiority are retained. This improves transparency but does not prove that every analytical choice was reported.

4. **No exclusion operation was identified in the audited pipeline.** The stored CSV files contain 0 NaN and 0 Inf values. In the audited COVID-19 data, zero-stress days occur when ρ=0 under the multiplicative construction rather than through a visible cleaning exclusion.

5. **Limited seed sensitivity.** Permutation-test significance decisions are unchanged across the 8 examined seeds; broader seed independence is not established.

6. **Several limitations are explicitly documented.** These include N=5, partly post hoc variable selection, nested controls, SVB infeasibility, and the monthly resolution of Supply Chain.

**Areas where a skeptical reviewer might push back** (not evidence of manipulation, but potential weaknesses):

- The nested control design structurally favors Π_crisis > Π_control. Mean-stress contrasts remain above 1 in the selected cases, but this does not eliminate the design or selection limitations.
- COVID-19's extreme separation (3,627×) is partly a floor effect, not purely discriminative power.
- The three-formulation comparison places the multiplicative formulation highest in 5/5 cases, whereas the broader nine-combination ablation places ρ×Ψ×Ω highest in 4/5; COVID is additionally affected by the floor effect.
- Terra-Luna's time-normalized separation (S̄ ratio = 1.1×) is marginal.
