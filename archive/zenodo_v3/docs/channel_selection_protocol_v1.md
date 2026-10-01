# Protocol v1 PRE-FREEZE — 1998 LTCM Historical Holdout

**Status:** PRE-FREEZE. No LTCM framework outcome may be generated or inspected while this file remains under review.

## 1. Purpose

The original five cases are retrospective development cases. This holdout is not intended to add another domain or establish population-level external validity. Its purpose is narrower:

> apply an already-developed financial-domain construction to one previously unused historical financial episode without LTCM-specific channel substitution, window tuning, or post-result modification.

The episode is the September 1998 near-failure of Long-Term Capital Management (LTCM), a highly leveraged hedge fund whose disorderly liquidation was judged capable of posing broader financial-system risks.

This is a **protocol-frozen historical holdout application**, not prospective forecasting or prospective validation.

## 2. Episode and reference date

- Episode: Long-Term Capital Management near-failure / private-sector recapitalization
- Reference date: **1998-09-23**
- Reference-date rationale: on 23 September 1998, fourteen banks and securities firms agreed to recapitalize LTCM with approximately $3.625 billion, preventing an abrupt liquidation.
- Primary external sources:
  - Federal Reserve History, *Near Failure of Long-Term Capital Management*
  - Federal Reserve Bank of New York, William J. McDonough testimony, 1 October 1998

The reference date is a historical anchor, not a claim that all financial stress began on that day.

## 3. Prior-use status

Before protocol freeze, repository/current-tree and Git-history searches supplied by the author showed no LTCM / Long-Term Capital framework implementation or prior LTCM framework output.

If a prior LTCM framework output is later discovered before freeze, stop and reassess the held-out designation before computing any new LTCM result.

## 4. Financial-domain construction transferred from the 2008 development case

No LTCM-specific primary channel is selected.

| Channel | Series | Source | Frozen transform |
|---|---|---|---|
| x1 | DFF | FRED / Board of Governors | absolute five-observation difference |
| x2 | TEDRATE | FRED / Federal Reserve Bank of St. Louis | absolute five-observation difference |
| x3 | TOTBKCR | FRED / Board of Governors | level |

This is the same primary financial-domain channel construction used in the 2008 development case.

### 4.1 Alignment

Reuse the 2008 financial-case alignment logic without LTCM-specific changes:

- DFF and TEDRATE are transformed using five-observation absolute differences.
- TOTBKCR enters as a level.
- TOTBKCR is aligned to the common daily index using time-linear interpolation **only between observed source values**.
- trailing forward fill is permitted under the existing 2008 rule.
- no backward fill.
- no leading extrapolation.
- only rows with the required finite aligned values are retained.

No new interpolation, smoothing, rolling width, or missing-data rule may be introduced after freeze.

## 5. Normalization

Reuse the existing framework rule:

- calculate a channel-specific P99 from the frozen calibration period;
- divide each channel by its corresponding calibration P99;
- values below zero are clipped to zero;
- no upper cap;
- each channel enters the product once with unit exponent;
- no fitted coefficients.

The primary instantaneous score remains:

`S_t = x1_t * x2_t * x3_t`

## 6. Window rule — mechanical transfer of the 2008 financial-case geometry

To remove LTCM-specific window discretion, the held-out uses the **same nominal calendar offsets relative to the reference date that were used in the 2008 financial development case**.

### 6.1 Development-case offsets

2008 reference date: `2008-09-15`

| Boundary | 2008 nominal date | Offset from reference |
|---|---:|---:|
| Control start | 2004-01-01 | -1719 days |
| Control end | 2006-06-30 | -808 days |
| Calibration start | 2005-01-01 | -1353 days |
| Calibration end | 2007-06-30 | -443 days |
| Post-control end / event-window end | 2009-03-31 | +197 days |

The 2008 primary analysis defines post-control observations as observations strictly after the last control observation.

### 6.2 Mechanically transferred LTCM nominal dates

LTCM reference date: `1998-09-23`

Applying the same day offsets gives:

| Boundary | LTCM frozen nominal date |
|---|---:|
| Control start | **1994-01-08** |
| Control end | **1996-07-07** |
| Calibration start | **1995-01-09** |
| Calibration end | **1997-07-07** |
| Post-control end | **1999-04-08** |

The LTCM post-control segment is:

> every valid aligned observation strictly after the control end (`1996-07-07`) and on or before `1999-04-08`.

Actual retained first/last observation dates may differ by a small number of calendar days because of the five-observation transform, holidays, source frequency, and deterministic common-index alignment. **No manual boundary adjustment is permitted.**

### 6.3 Warm-up observations

The data fetch may include observations before a nominal window boundary only to compute the prespecified five-observation differences or interpolation. Warm-up observations are not included in calibration/control/post-control statistics unless their resulting transformed timestamp lies inside the corresponding frozen nominal window.

## 7. Metadata-only feasibility audit

The audit is limited to source existence, coverage, frequency, provenance, and implementability. No framework outcome has been used to select the episode, channels, transforms, or windows.

### DFF

- FRED series: DFF
- Frequency: Daily, 7-Day
- Available from: 1954-07-01
- LTCM required range: covered

### TEDRATE

- FRED series: TEDRATE
- Frequency: Daily
- Available: 1986-01-02 to 2022-01-21
- LTCM required range: covered
- The series is discontinued only after 2022; this does not affect the 1994–1999 holdout range.

### TOTBKCR

- FRED series: TOTBKCR
- Frequency: Weekly, ending Wednesday
- Available from: 1973-01-03
- LTCM required range: covered

### Audit conclusion

**PASS for metadata feasibility.** No required proxy substitution is needed, and the existing 2008 financial construction is technically transferable over the frozen LTCM date range.

This is not yet an outcome-based pass/fail result for the framework.

## 8. Forbidden before final freeze

Do not compute, inspect, or compare any LTCM-specific:

- normalized channel trajectory;
- `S_t` trajectory;
- control mean stress;
- post-control mean stress;
- `R_PC/C`;
- product/sum/max ranking;
- nine-definition ablation result;
- pairwise-correlation result if it is being used to alter the specification;
- permutation statistic, z-score, or p-value;
- alternative window result;
- alternative channel result.

Metadata-level row counts and missingness checks are allowed only to establish technical implementability and must not be used to optimize the specification.

## 9. Analysis package after freeze

After this protocol is committed and hash-recorded, perform only the already-established evaluation package:

1. primary non-overlapping post-control/control mean-stress ratio;
2. full-channel product vs sum vs maximum;
3. nine-definition channel ablation;
4. pairwise control-window redundancy diagnostics;
5. temporal-alignment permutation diagnostics:
   - independent shuffle;
   - block size 5;
   - block size 10;
   - block size 20;
   - B = 10,000 each;
6. deterministic output/hash verification.

Prespecified permutation seeds for LTCM:

- independent: `20261231`
- block 5: `20261232`
- block 10: `20261233`
- block 20: `20261234`

No additional metric is required for the held-out.

## 10. Failure / fallback rule

There is **no outcome-driven fallback**.

After freeze, do not:

- replace DFF, TEDRATE, or TOTBKCR;
- change the five-observation transform;
- change interpolation/fill rules;
- move the reference date;
- move the calibration/control/post-control windows;
- redraw or substitute the episode;
- add a second held-out because the LTCM result is weak;
- change permutation block sizes or seeds after viewing results.

If the frozen implementation is technically impossible for a reason not discovered during the metadata audit, stop and report the implementation failure. Any revised protocol must receive a new version and must not be presented as the original frozen test.

## 11. Interpretation limits

Regardless of the eventual result:

- LTCM is one historical application, not a population sample.
- it does not establish prospective forecasting performance.
- it does not prove domain-agnostic channel discovery.
- it does not validate the five original retrospective mappings retroactively.
- it does test whether the already-developed financial construction and a precommitted analysis procedure can be executed on a previously unused historical episode without outcome-driven modification.

## 12. Freeze procedure

Only after final human review of this file:

1. rename/copy to `channel_selection_protocol_v1.md` (or an equivalently stable repository path);
2. record the exact file SHA-256;
3. commit the protocol before any LTCM framework-output code is executed;
4. record the Git commit hash and timestamp;
5. preferably archive/release the protocol artifact together with repository provenance;
6. create LTCM output-generation code in a separate subsequent commit;
7. run the LTCM analysis once under the frozen rules;
8. report the result whether favorable, null, mixed, or adverse to the framework.

---

**Current status:** metadata audit complete; protocol remains PRE-FREEZE; no LTCM framework outcome should be generated yet.
