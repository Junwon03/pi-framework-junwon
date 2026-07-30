# Π Structural Stability Index

Cross-case retrospective characterization of systemic stress using multiplicative stress integration.

## Quick Start

```bash
pip install -r requirements-lock.txt
python run_all.py          # Core analyses (no API needed)
python run_all.py --all    # Core + supplementary + publication figures
python run_all.py --svb    # Include SVB out-of-sample (needs FRED_API_KEY)
```

For full repository reproducibility, including analyses retained only for audit:

```bash
export FRED_API_KEY="your_key"
export FRED_VINTAGE_DATE="2026-02-17"
python run_all.py --all
python run_benchmark.py
python run_v12_enhancements.py
python run_v13_enhancements.py
python run_nonoverlap_reanalysis.py
python run_threshold_grid.py
python run_variable_substitution.py
python run_additional_cases.py
python sensitivity/sensitivity_delta_k.py
python sensitivity/sensitivity_matched_pipeline.py
python run_method_comparison.py --include-audit-method-comparison
python scripts/verify_outputs.py
```

Additional scripts:

```bash
python run_benchmark.py                          # Channel ablation (9 methods × 5 domains)
python run_v12_enhancements.py                   # Block permutation + non-redundancy
python run_v13_enhancements.py                   # Sliding window + additional cases
python run_nonoverlap_reanalysis.py              # Crisis-exclusive primary comparison
python run_threshold_grid.py                     # Full-factorial label-threshold sensitivity
python run_variable_substitution.py              # Variable substitution sensitivity
python run_additional_cases.py                   # Dot-com, 2019 Repo, Thailand Flood
python run_method_comparison.py                  # Retrospective rolling-trajectory analysis
python run_method_comparison.py --include-audit-method-comparison  # Also run legacy ST16 audit comparison

# Sensitivity analyses (require FRED_API_KEY)
python sensitivity/sensitivity_delta_k.py        # ST15: Transform window k=1,3,5,10,20
python sensitivity/sensitivity_matched_pipeline.py  # Legacy matched-pipeline analysis (audit only)
```

## What This Runs

| # | Analysis | Result |
|---|----------|--------|
| 1 | Non-Overlapping Primary Contrast (5 selected cases) | Crisis-exclusive mean stress exceeds the full control-window mean in 5/5 selected cases; retrospective and case-conditional |
| 2 | Non-Overlapping Three-Formulation Comparison | Multiplicative formulation is highest in 5/5 among multiplicative, additive, and maximum formulations |
| 3 | Permutation Test (n=10,000) | 4/5 significant (p < 0.001), Fisher p = 1.66×10⁻¹¹ under the specified original windows |
| 4 | Exploratory Pattern Labels | Ductile / Brittle / Pre-loaded labels assigned descriptively; not validated classes |
| ST4 | Channel Ablation (9 methods × 5 domains) | Original-window ρ×Ψ×Ω is highest in 4/5 cases; the non-overlap rerun is reported separately |
| S1 | P-limit Scale-Invariance Diagnostic | Separation is unchanged because the common normalization factors cancel algebraically |
| S2 | Variable Perturbation | ±3.2% max deviation at 50% noise |
| S4 | Non-Redundancy | 3/5 pass threshold; Supply Chain max\|r\|=0.952 |
| ST8 | Block Permutation | 4/5 significant under the specified block-permutation procedure |
| ST10-11 | Additional Cases (Dot-com, Repo, Thailand) | Mixed: 1 weak, 1 negative, 1 non-significant |
| ST15 | Transform Window Sensitivity | Non-overlap mean-stress ratios range from 13.9× to 18.1× across k=1..20; all remain above 1 |
| Grid | Label-Threshold Sensitivity | Baseline-label retention ranges from 60% to 100% across the full threshold grid |
| Legacy | Matched-Pipeline Analysis (audit only) | Excluded from the revised evidentiary package; legacy output retained for reproducibility |
| Legacy | Method Comparison (Π vs CSD vs PCA; audit only) | Excluded from the revised evidentiary package; legacy result retained for reproducibility |
| ST17 | Retrospective Rolling-Trajectory Sensitivity | Rolling-matched 2σ post-control crossings occur before the selected event in 4/5 cases, while 2σ control exceedances also occur in 4/5; not predictive |

**Comparison scope:** The revised primary comparison uses crisis observations strictly after the control-window end and compares their mean stress with the mean stress of the full prespecified control window. Under this design, the multiplicative formulation is highest in 5/5 cases among the multiplicative, additive, and maximum formulations. The original-window ST4 ablation compares nine channel combinations; there, ρ×Ψ×Ω is highest in 4/5 cases. For Supply Chain, Ψ×Ω yields 34.5× versus 9.2× for ρ×Ψ×Ω in that original-window specification. The non-overlap nine-method ablation is reported separately and interpreted case by case.

## Output

Running `python run_all.py --all` generates:

```
output/
├── figures/
│   ├── Figure1_Pi_timeseries.png/.pdf
│   ├── Figure2_cross_domain_separation.png/.pdf
│   ├── Figure3_mult_vs_add_vs_max.png/.pdf
│   ├── Figure4_permutation_tests.png/.pdf
│   ├── Figure5_failure_modes.png/.pdf
│   └── Figure6_robustness.png/.pdf
├── table1_cross_domain.csv
├── table2_mult_vs_add.csv
├── table3_permutation.csv
├── table4_failure_modes.csv
├── table_S1_plimit_sensitivity.csv
├── table_S2_variable_robustness.csv
├── table_S4_nonredundancy.csv
└── summary.txt
```

Additional scripts produce the existing benchmark, enhancement, variable-substitution, additional-case, and transform-window outputs. The revised comparison package additionally produces `table_nonoverlap_primary.csv`, `table_nonoverlap_formulations.csv`, `table_nonoverlap_ablation.csv`, `table_nonoverlap_variable_substitution.csv`, `table_ST15_nonoverlap_delta_k.csv`, `table_threshold_grid_labels.csv`, and `table_threshold_grid_retention.csv`. The audit-only matched-pipeline script retains its legacy output filename: `table_ST16_matched_pipeline.csv`.

Running `python run_method_comparison.py` produces:

```
output/
├── figures/
│   └── Figure7_retrospective_trajectory.png/.pdf
├── table_ST17_retrospective_trajectory.csv
└── table_ST17_matched_threshold_sensitivity.csv
```

Adding `--include-audit-method-comparison` also produces the legacy audit output
`table_ST16_method_comparison.csv`.

## Cases

| Case | Domain | Variables (ρ / Ψ / Ω) | Source | Full-window Sep(Π) | Full-window Sep(S̄) | Crisis-exclusive Sep(S̄) |
|------|--------|------------------------|--------|--------------------|---------------------|---------------------------|
| 2008 Financial | Traditional Finance | DFF \|Δ5d\| / TEDRATE \|Δ5d\| / TOTBKCR | FRED | 18.58× | 10.77× | 15.92× |
| Terra-Luna | Digital Assets | BTC \|Δ5d\| / LUNC \|Δ1d\| / BTC–ETH–LUNC correlation (60d) | Yahoo Finance | 1.94× | 1.05× | 1.11× |
| Fukushima | Physical Infrastructure | log10 daily seismic energy / Nikkei volatility (5d) / \|Δ USD/JPY\| | USGS / Yahoo Finance | 2.25× | 1.24× | 1.54× |
| COVID-19 | Pandemic / Public Health | Global cases (7d average) / VIX / HY spread | JH CSSE / Yahoo Finance / FRED | 3,626.66× | 2,573.20× | 8,856.12× |
| Supply Chain | Global Logistics | PCEDG \|MoM\| / positive delivery-time index / Freight PPI \|MoM\| | FRED | 9.21× | 3.33× | 4.65× |

Full-window Sep(Π) is the original cumulative crisis/control ratio. Full-window Sep(S̄) compares mean stress over the original specified windows. Crisis-exclusive Sep(S̄), the revised primary contrast, compares mean stress strictly after the control-window end with mean stress over the full prespecified control window.

## Framework

```
S(t) = ρ̃(t) × Ψ̃(t) × Ω̃(t)     # Multiplicative stress (equal weight, no tuning)
Π(t) = Σ S(τ) · Δt / τ₀          # Cumulative damage integral
```

- **ρ**: External pressure (cause) — e.g., Fed rate changes, earthquake energy, COVID cases
- **Ψ**: Internal amplification (response) — e.g., TED spread, Nikkei volatility, VIX
- **Ω**: Structural degradation (state) — e.g., bank credit, cross-asset correlation, freight PPI
- **τ₀**: Time step = 1/365 year for daily data, 1/12 year for monthly data
- **P-limit normalization**: Each variable is divided by the 99th percentile of the stable (pre-crisis) period

## Design Notes

### Time step (τ₀)

All paper results are generated by `run_all.py`, which uses `dt = 1/365` for daily data and `dt = 1/12` for monthly data. The standalone `pi_calculator.py` (Case 1 only) uses `dt = 1/252` (business days), but this does not affect any reported results because `run_all.py` recalculates the Π column from stress at runtime.

Separation ratios are τ₀-invariant: dt cancels algebraically in Π_crisis / Π_control. Verified numerically (dt=1/252, 1/365, 1/100 all yield Sep=18.6× for 2008).

### Overlapping control design and revised primary contrast

The original control window is fully contained within the crisis range in 4 of 5 cases. In the 2008 case it overlaps 347 of 574 control observations (60.45%). Consequently, the original cumulative crisis/control ratio is partly affected by duplicated observations and unequal accumulation lengths.

The revised primary estimand removes exact overlap from the crisis side. It compares mean stress in crisis observations strictly after the control-window end with mean stress over the full prespecified control window. The resulting ratios are 15.92×, 1.11×, 1.54×, 8,856.12×, and 4.65× for the five selected cases, respectively.

This removes the direct overlap and cumulative-duration artifact from the primary contrast, but it does not create independently sampled controls or eliminate case-selection, variable-selection, event-date, carryover, and window-design limitations. The existing permutation procedure remains conditional on the original specified windows and evaluates temporal channel alignment; it is not independent prospective validation.

### COVID-19 floor effect

The extreme COVID-19 ratios are partly a floor effect: reported cases were zero for 98% of the selected control period, mechanically making S(t) = 0 under the multiplicative construction. This affects both the original cumulative ratio (3,626.66×) and the crisis-exclusive mean-stress ratio (8,856.12×). These magnitudes are not directly comparable with the other cases and should not be interpreted as a general effect-size ranking.

### Equal weight

S = ρ̃ × Ψ̃ × Ω̃ uses no explicit weights. However, P-limit normalization implicitly creates different effective scales: a channel with a lower P-limit will have higher normalized values. This is physically appropriate (it reflects the channel's baseline stability) but "equal weight" should be understood as "equal structural role," not "equal numerical contribution."

## Reproducibility

- **Random seed**: `np.random.seed(42)` fixed globally. Tested across 8 alternative seeds — all conclusions unchanged (z-score variation < ±0.5).
- **Environment**: Python `3.11.8` in CI, dependencies pinned in `requirements-lock.txt`.
- **Frozen API vintage**: CI fixes FRED realtime window via `FRED_VINTAGE_DATE=2026-02-17`.
- **Golden baseline verification**: CI compares generated `output/*.csv`, `output/*.txt`, and `data/*.csv` against `golden/` reference files using SHA-256.
- **Secrets required**: `FRED_API_KEY` must be configured in GitHub Actions secrets for full pipeline.
- **GitHub Actions**: Full pipeline runs in CI and uploads `pi-analysis-results` artifact after reproducibility verification.

**Note on pi column in CSV data files:** The `pi` column in Data/ CSV files is recomputed at runtime by `run_all.py` using `stress × dt` (dt=1/365 for daily, dt=1/12 for monthly). Raw observations (rho, psi, omega, rho_norm, psi_norm, omega_norm, stress) are unchanged from original computation. The 2008 case CSV was originally generated with dt=1/252 by `pi_calculator.py`, but `run_all.py` overrides this with dt=1/365 for consistency with other cases. This has no effect on any reported ratio or test statistic.

## Known Limitations

- **Supply Chain permutation test**: p = 0.26 (not significant). The monthly series contains only 47 observations, limiting statistical power. Both the 9.21× original cumulative contrast and the 4.65× crisis-exclusive mean-stress contrast are descriptive and are not supported by this permutation test.
- **Supply Chain non-redundancy**: max|r| = 0.952 between Ψ (delivery time) and Ω (freight PPI). These two channels are highly collinear, violating the non-redundancy assumption. The 2-channel Ψ×Ω outperforms the 3-channel ρ×Ψ×Ω (34.5× vs 9.2×) in this case.
- **Terra-Luna marginal separation**: The original full-window mean-stress ratio is 1.0525× and the crisis-exclusive ratio is 1.1149×. Although the original-window permutation test is significant (z=5.49), the observed stress-intensity difference is small and specification-sensitive.
- **Exploratory pattern labels**: Ductile, Brittle, and Pre-loaded are retrospective descriptive labels, not established system classes. Across the full factorial threshold grid, baseline-label retention ranges from 60% for Supply Chain to 100% for Terra-Luna and COVID-19, demonstrating unequal case-specific sensitivity.
- **SVB out-of-sample not feasible**: The TED Spread (TEDRATE), a core variable in the 2008 case, is based on LIBOR which was discontinued in June 2023. Only 13 data points were available for the SVB period, producing zero stress values. Substituting an alternative variable would compromise the strict out-of-sample design. This highlights how structural changes in financial benchmarks can invalidate prior calibrations.
- **Additional case results are mixed**: Dot-com (Sep=1.2×, significant but weak), 2019 Repo (Sep=0.7×, crisis < control), Thailand Flood (Sep=3.5× but p=0.49). These are reported honestly as boundary/negative cases. The Dot-com and Repo cases also fail non-redundancy (max|r| = 0.765, 0.866).
- **Sample size**: The five primary cases support a proof-of-concept retrospective characterization only. They are insufficient for statistical generalization, universal validation, or estimation of cross-domain performance.
- **Variable selection**: Variables were selected through domain judgment and iterative, partly post hoc refinement. The specifications are not claimed to be unique or optimal, and inferential results are conditional on these selected variables and windows.
- **Retrospective event-relative analysis**: The matched-threshold sensitivity applies the same rolling operator to crisis and control series and searches crisis crossings only after the control-window end. At 2σ, pre-event post-control crossings occur in 4 of 5 cases, but control exceedances also occur in 4 of 5 cases, reaching 12.5% for Supply Chain. Because rolling observations are autocorrelated and some control samples are small, these exceedance rates are descriptive rather than calibrated false-alarm probabilities. The analysis does not establish prospective validation, forecasting performance, or an independently estimated warning lead.


## Data

Primary manuscript analyses run from pre-computed case files in `Data/`.
Raw source data (used to build case datasets and supplementary tests) come from public APIs:

- [FRED](https://fred.stlouisfed.org): DFF, TEDRATE, TOTBKCR, BAMLH0A0HYM2, PCEDG, DTCDISA066MSFRBNY, WPU3012, DGORDER
- [FRED](https://fred.stlouisfed.org) (supplementary substitution tests): DGS2, VIXCLS, COMPOUT
- [USGS Earthquake Hazards](https://earthquake.usgs.gov): Japan M2+ events via FDSN Event API
- [Johns Hopkins CSSE](https://github.com/CSSEGISandData/COVID-19): Global confirmed COVID-19 cases
- [Yahoo Finance](https://finance.yahoo.com): BTC-USD, ETH-USD, LUNC-USD, ^N225, JPY=X, ^VIX

Note: Proxy series (e.g., HYG/LQD fallback) exist only as contingency logic in data-collection utilities and are not part of the baseline manuscript tables unless explicitly stated.


## Repository Structure

```
├── .github/workflows/run_analysis.yml  # Locked CI pipeline + baseline verification
├── Cases/                          # Individual case data generation scripts
│   ├── config.py                   #   2008 case configuration
│   ├── data_fetcher.py             #   FRED data fetcher (requires API key)
│   ├── pi_calculator.py            #   Core Π calculator (standalone dt=1/252)
│   ├── main.py                     #   2008 case standalone pipeline
│   ├── case2_terra_luna.py         #   Terra-Luna data collection + calculation
│   ├── case3_fukushima.py          #   Fukushima data collection + calculation
│   ├── case4_covid.py              #   COVID-19 data collection + calculation
│   ├── case5_supply_chain.py       #   Supply Chain data collection + calculation
│   └── visualize.py                #   Plotting utilities
├── Data/                           # Pre-computed CSV results (10 files)
├── sensitivity/                    # Sensitivity analyses
│   ├── sensitivity_delta_k.py      #   ST15: Transform window k sweep
│   └── sensitivity_matched_pipeline.py  # Legacy audit-only analysis; excluded from revised evidence
├── run_all.py                      # Unified analysis (Tables 2-5, S1-S3, Figures 1-6)
├── run_benchmark.py                # Channel ablation (ST4)
├── run_v12_enhancements.py         # Block permutation + extended non-redundancy
├── run_v13_enhancements.py         # Sliding window + additional cases (ST10-12)
├── run_nonoverlap_reanalysis.py    # Crisis-exclusive primary comparison and ablations
├── run_threshold_grid.py           # Full-factorial exploratory-label threshold grid
├── run_variable_substitution.py    # Variable substitution sensitivity (ST9)
├── run_additional_cases.py         # Additional case computation
├── run_method_comparison.py        # Retrospective trajectory; optional legacy method-comparison audit
├── requirements-lock.txt           # Pinned Python dependency versions
├── scripts/verify_outputs.py       # Active deterministic CSV/TXT baseline checker
├── golden/                         # Frozen baseline outputs used in CI reproducibility check
├── Audit report.md                 # Code & data integrity audit results
├── LICENSE                         # MIT License
└── README.md                       # This file
```

## AI Disclosure

Large language models were used to assist with code development, pipeline refinement, reproducibility hardening, and audit/readme editing, including:
- Claude Opus 4.5 (Anthropic)
- GPT 5.3 Codex (OpenAI)
All scientific hypotheses, variable selections, methodological decisions, interpretation, and final conclusions were made by the author.  
The complete code is publicly available for independent verification. A full audit record is documented in `Audit report.md`.

## Citation

If you use this framework, please cite:

```
[Paper citation pending]
```
