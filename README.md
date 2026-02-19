# Π Structural Stability Index

Cross-domain framework for systemic collapse detection using multiplicative stress integration.

## Quick Start

```bash
pip install -r requirements-lock.txt
python run_all.py          # Core analyses (no API needed)
python run_all.py --all    # Core + supplementary + publication figures
python run_all.py --svb    # Include SVB out-of-sample (needs FRED_API_KEY)
```

For full reproducibility with the same manuscript baseline:

```bash
export FRED_API_KEY="your_key"
export FRED_VINTAGE_DATE="2026-02-17"
python run_all.py --all
python run_benchmark.py
python run_v12_enhancements.py
python run_v13_enhancements.py
python run_variable_substitution.py
python run_additional_cases.py
python sensitivity/sensitivity_delta_k.py
python sensitivity/sensitivity_matched_pipeline.py
python run_method_comparison.py
python scripts/verify_outputs.py
```

Additional scripts:

```bash
python run_benchmark.py                          # Channel ablation (9 methods × 5 domains)
python run_v12_enhancements.py                   # Block permutation + non-redundancy
python run_v13_enhancements.py                   # Sliding window + additional cases
python run_variable_substitution.py              # Variable substitution robustness
python run_additional_cases.py                   # Dot-com, 2019 Repo, Thailand Flood
python run_method_comparison.py                  # ST16-17: Method benchmark + pseudo-prospective

# Sensitivity analyses (require FRED_API_KEY)
python sensitivity/sensitivity_delta_k.py        # ST14: Transform window k=1,3,5,10,20
python sensitivity/sensitivity_matched_pipeline.py  # ST15: Matched-pipeline specificity
```

## What This Runs

| # | Analysis | Result |
|---|----------|--------|
| 1 | Cross-Domain Validation (5 cases) | 5/5 Crisis > Control |
| 2 | Multiplicative vs Additive vs Max | Multiplicative wins 4/5 (see note below) |
| 3 | Permutation Test (n=10,000) | 4/5 significant (p < 0.001), Fisher p = 1.66×10⁻¹¹ |
| 4 | Failure Mode Classification | 3 classes: Ductile / Brittle / Pre-loaded |
| ST4 | Channel Ablation (9 methods × 5 domains) | ρ×Ψ×Ω highest in 4/5 cases |
| S1 | P-limit Sensitivity | Invariant across P95–P99.5 |
| S2 | Variable Perturbation | ±3.2% max deviation at 50% noise |
| S3 | Non-Redundancy | 3/5 pass threshold; Supply Chain max\|r\|=0.952 |
| ST8 | Block Permutation | 4/5 robust to temporal structure |
| ST10-11 | Additional Cases (Dot-com, Repo, Thailand) | Mixed: 1 weak, 1 negative, 1 non-significant |
| ST14 | Transform Window Sensitivity | Sep range 16.6–21.1× across k=1..20, all p<0.05 |
| ST15 | Matched-Pipeline Specificity | Dot-com 1.3×, Repo 0.8× (confirms specificity) |
| ST16 | Method Comparison (Π vs CSD vs PCA) | Π wins 3/5; CSD AC(1) near-unity across all domains |
| ST17 | Pseudo-Prospective Signal Analysis | 2008: 398-day lead; 3/5 pre-collapse signals |

**Note on "Multiplicative wins":** In the full ablation benchmark (ST4), ρ×Ψ×Ω achieves the highest separation in 4/5 cases. Supply Chain is won by the 2-channel Ψ×Ω (34.5× vs 9.2×) because the ρ channel (durable goods PCE) dilutes the signal. This is disclosed in the manuscript.

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

Additional scripts produce: `benchmark_full.csv`, `benchmark_pivot.csv`, `table_v13_block_permutation.csv`, `table_variable_substitution.csv`, `table_additional_cases.csv`, `table_additional_nonredundancy.csv`, `table_ST15_delta_k_sensitivity.csv`, `table_ST16_matched_pipeline.csv`.

Running `python run_method_comparison.py` additionally produces:

```
output/
├── figures/
│   └── Figure7_pseudo_prospective.png/.pdf
├── table_ST16_method_comparison.csv
└── table_ST17_pseudoprospective.csv
```

## Cases

| Case | Domain | Variables (ρ / Ψ / Ω) | Source | Sep(Π) | Sep(S̄) |
|------|--------|------------------------|--------|--------|--------|
| 2008 Financial | Traditional Finance | DFF \|Δ5d\| / TEDRATE \|Δ5d\| / TOTBKCR | FRED | 18.6× | 10.8× |
| Terra-Luna | Digital Assets | BTC \|Δ5d\| / LUNA \|Δ1d\| / Cross-Correlation | Yahoo/CoinGecko | 1.9× | 1.1× |
| Fukushima | Physical Infrastructure | Seismic Energy (USGS) / Nikkei Vol / USD/JPY | USGS/Yahoo | 2.3× | 1.2× |
| COVID-19 | Pandemic | Cases (JH CSSE) / VIX / HY Spread | JH/Yahoo/FRED | 3,627× | 2,573× |
| Supply Chain | Global Logistics | PCEDG \|MoM\| / Delivery Time / Freight PPI | FRED | 9.2× | 3.3× |

Sep(Π) = cumulative separation ratio. Sep(S̄) = time-normalized mean stress ratio, which controls for differing window lengths between crisis and control periods. See "Design Notes" below.

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

### Nested control design

In 4 of 5 cases the control window is a subset of the crisis window (the pre-crisis portion). This means Π_crisis > Π_control is partly expected from the longer accumulation window alone. The time-normalized comparison (Sep(S̄) column above) controls for this by comparing mean stress *intensity* rather than cumulative totals. All cases maintain Sep(S̄) > 1.0, confirming the stress intensity during crisis genuinely exceeds the pre-crisis baseline. The permutation test provides an additional control by testing temporal coincidence of channels, independent of window length.

### COVID-19 floor effect

The extreme separation (3,627×) is partly a floor effect: COVID cases were literally 0 for 98% of the control period, making S(t) = 0 by the multiplicative structure. The magnitude is not directly comparable to other cases but correctly reflects the binary nature of the pandemic onset.

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

- **Supply Chain permutation test**: p = 0.26 (not significant). Monthly resolution (n=47) provides insufficient statistical power. The 9.2× crisis-control separation remains substantial but statistically unconfirmed.
- **Supply Chain non-redundancy**: max|r| = 0.952 between Ψ (delivery time) and Ω (freight PPI). These two channels are highly collinear, violating the non-redundancy assumption. The 2-channel Ψ×Ω outperforms the 3-channel ρ×Ψ×Ω (34.5× vs 9.2×) in this case.
- **Terra-Luna marginal time-normalized separation**: Sep(S̄) = 1.1× after controlling for window length. While the permutation test is significant (z=5.49), the intensity difference between crisis and control is small.
- **COVID-19 boundary classification**: Π@collapse/Π_max = 10.3%, classified as "Brittle" with the Explosive boundary at 10.0%. This 0.3pp margin means the classification is boundary-sensitive.
- **SVB out-of-sample not feasible**: The TED Spread (TEDRATE), a core variable in the 2008 case, is based on LIBOR which was discontinued in June 2023. Only 13 data points were available for the SVB period, producing zero stress values. Substituting an alternative variable would compromise the strict out-of-sample design. This highlights how structural changes in financial benchmarks can invalidate prior calibrations.
- **Additional case results are mixed**: Dot-com (Sep=1.2×, significant but weak), 2019 Repo (Sep=0.7×, crisis < control), Thailand Flood (Sep=3.5× but p=0.49). These are reported honestly as boundary/negative cases. The Dot-com and Repo cases also fail non-redundancy (max|r| = 0.765, 0.866).
- **Sample size**: N=5 primary cases sufficient for framework validation, not for statistical generalization.
- **Variable selection**: Requires domain expertise. Selection involved iterative refinement; the current variables are not claimed to be unique or optimal.
- **Pseudo-prospective, not prospective**: The rolling stress signal analysis (ST17) uses thresholds calibrated from the full control period and does not constitute a true out-of-sample forecast. The 398-day lead in the 2008 case is retrospectively identified.


## Data

Primary manuscript analyses run from pre-computed case files in `Data/`.
Raw source data (used to build case datasets and supplementary tests) come from public APIs:

- [FRED](https://fred.stlouisfed.org): DFF, TEDRATE, TOTBKCR, BAMLH0A0HYM2, PCEDG, DTCDISA066MSFRBNY, WPU3012, DGORDER
- [FRED](https://fred.stlouisfed.org) (supplementary substitution tests): DGS2, VIXCLS, COMPOUT
- [USGS Earthquake Hazards](https://earthquake.usgs.gov): Japan M2+ events via FDSN Event API
- [Johns Hopkins CSSE](https://github.com/CSSEGISandData/COVID-19): Global confirmed COVID-19 cases
- [Yahoo Finance](https://finance.yahoo.com): BTC-USD, ETH-USD, LUNC-USD, ^N225, JPY=X, ^VIX
- [CoinGecko](https://www.coingecko.com): TerraUSD (UST) market chart

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
│   ├── sensitivity_delta_k.py      #   ST14: Transform window k sweep
│   └── sensitivity_matched_pipeline.py  # ST15: Matched-pipeline specificity
├── run_all.py                      # Unified analysis (Tables 2-5, S1-S3, Figures 1-6)
├── run_benchmark.py                # Channel ablation (ST4)
├── run_v12_enhancements.py         # Block permutation + extended non-redundancy
├── run_v13_enhancements.py         # Sliding window + additional cases (ST10-12)
├── run_variable_substitution.py    # Variable substitution robustness (ST9)
├── run_additional_cases.py         # Additional case computation
├── run_method_comparison.py        # Method benchmark + pseudo-prospective (ST16-17, Figure 7)
├── requirements-lock.txt           # Pinned Python dependency versions
├── scripts/verify_outputs.py       # SHA-256 baseline checker (golden vs generated outputs)
├── golden/                         # Frozen baseline outputs used in CI reproducibility check
├── Audit report.md                 # Code & data integrity audit results
├── LICENSE                         # MIT License
└── README.md                       # This file
```

## AI Disclosure

Large language models were used to assist with code development, pipeline refinement, reproducibility hardening, and audit/readme editing, including:
- Claude (Opus 4.5, Anthropic)
- OpenAI Codex (GPT-5.2, OpenAI)
All scientific hypotheses, variable selections, methodological decisions, interpretation, and final conclusions were made by the author.  
The complete code is publicly available for independent verification. A full audit record is documented in `Audit report.md`.

## Citation

If you use this framework, please cite:

```
[Paper citation pending]
```
