README_revised.md


Π Structural Stability Index
Cross-case retrospective characterization of systemic stress using multiplicative stress integration.

Quick Start
Install the locked environment:

pip install -r requirements-lock.txt
Generate the revised primary package and active supporting diagnostics from the tracked frozen inputs:

python run_nonoverlap_reanalysis.py
python run_additional_metric_alignment.py
python run_specification_provenance.py
These commands do not generate all 50 classified deterministic artifacts. The repository-wide verifier should therefore not be run after only these three commands on a fresh clone.

Generate the final manuscript figure set:

python run_all.py --all
python scripts/make_nonoverlap_figures.py
python scripts/make_benchmark_revised.py
python run_method_comparison.py
python scripts/assemble_submission_figures.py
The final submission files are assembled in output/figures/submission/. The seven-figure set contains Figures 1 and 5 from the original-window pipeline, revised non-overlap Figures 2–4, revised Supplementary Figure S1, and the 2008 ST17 trajectory illustration as Supplementary Figure S2. Figure 6 is withdrawn and is not assembled. Legacy versions of Figures 2–4 remain available as audit outputs but are excluded from the final submission set.

The 2008 variable-substitution diagnostic additionally requires the frozen FRED vintage:

export FRED_API_KEY="your_key"
export FRED_VINTAGE_DATE="2026-02-17"
python run_variable_substitution.py
The following additional commands reproduce historical or legacy audit artifacts beyond the retained submission figures above. Their deterministic CSV/TXT outputs remain versioned and hash-checked; generated figures are excluded from deterministic hash verification because rendering metadata can vary by environment:

python run_benchmark.py
python run_v12_enhancements.py
python run_v13_enhancements.py
python run_threshold_grid.py
python run_additional_cases.py
python sensitivity/sensitivity_delta_k.py
python sensitivity/sensitivity_matched_pipeline.py
python run_method_comparison.py --include-audit-method-comparison
Full deterministic verification
scripts/verify_outputs.py checks all 50 classified deterministic artifacts against the stored golden baselines. Run it only after the complete set of classified outputs has been generated:

python scripts/verify_outputs.py
A successful repository-wide verification reports expected=50 matched=50 failed=0. The canonical complete generation recipe is the GitHub Actions workflow in .github/workflows/run_analysis.yml. Reconstruction steps that query FRED require FRED_API_KEY together with the fixed FRED_VINTAGE_DATE=2026-02-17.

What This Runs
Revised evidentiary package
Component	Scope and result
Post-control primary contrast	Mean stress strictly after the control-window end exceeds the full control-window mean in the five selected cases: 15.92×, 1.11×, 1.54×, 8,856.12×, and 4.65×
Three-formulation comparison	The unit-exponent multiplicative product is highest in 5/5 selected cases among the multiplicative, additive, and maximum three-channel formulations
Post-control channel-alignment diagnostics	Independent shuffling gives unadjusted p < 0.05 in 4/5 cases; longer block shuffles weaken the COVID-19 result and Supply Chain remains non-significant
Active supporting diagnostics
Component	Scope
Control-window correlations	Descriptive pairwise correlations with no pass/fail threshold; Supply Chain reaches max	r	= 0.952
Variable substitution	2008 specification sensitivity; all tested ratios remain above one, but estimated magnitudes vary substantially
Additional cases	Dot-com, Repo, and Thailand are exploratory boundary comparisons rather than validation episodes
Specification provenance	Reports variable choices, transformations, calibration periods, tested alternatives, and partly post hoc development
Legacy audit artifacts
Original-window cumulative tables and permutations, retrospective pattern labels and their threshold grid, historical scale-invariance and perturbation outputs, ST15 alternate reconstruction, ST16 method comparisons, ST17 trajectories, and earlier enhancement tables are retained for reproducibility but excluded from the revised evidentiary package. The ST17 trajectory remains a retrospective audit analysis, while its 2008 illustration is included in the submission as Supplementary Figure S2.

The study is a retrospective characterization of five selected cases. It does not establish universal validation, prospective prediction, calibrated false-alarm performance, causal channel roles, or population-level cross-domain generalization.

Output
The revised primary package produces:

table_nonoverlap_primary.csv

table_nonoverlap_formulations.csv

table_nonoverlap_ablation.csv

table_nonoverlap_permutation.csv

The four active supporting artifacts are:

table_S4_nonredundancy.csv

table_nonoverlap_variable_substitution.csv

table_additional_metric_alignment.csv

table_specification_provenance.csv

table_S4_nonredundancy.csv retains its historical filename for compatibility; its current contents are descriptive control-window correlations without a pass/fail rule.

All other generated CSV/TXT files are retained as legacy audit artifacts and remain versioned and hash-checked. Historical figures are retained as reproducible audit outputs but are excluded from deterministic hash verification because rendering metadata can vary by environment. Inclusion of a figure in the assembled submission package does not change the evidentiary classification of its underlying analysis.

Figure output structure
output/figures/legacy/ — original-window and audit figures. Figures 1 and 5 and Supplementary Figure S2 are selected for the submission set.

output/figures/revised/ — revised non-overlap Figures 2–4 and revised channel-ablation Supplementary Figure S1.

output/figures/submission/ — the assembled seven-figure manuscript set in PNG and PDF formats, plus SUBMISSION_MANIFEST.md.

Generated figure outputs are reproducible build artifacts and are not part of the deterministic golden-hash baseline.

The verifier classifies 50 deterministic artifacts: 4 revised-primary outputs, 4 active supporting outputs, 26 legacy-audit outputs, and 16 frozen input files.

Cases
Case	Domain	Variables (ρ / Ψ / Ω)	Source	Full-window Sep(Π)	Full-window Sep(S̄)	Post-control Sep(S̄)
2008 Financial	Traditional Finance	DFF |Δ5d| / TEDRATE |Δ5d| / TOTBKCR	FRED	18.58×	10.77×	15.92×
Terra-Luna	Digital Assets	BTC |Δ5d| / LUNC |Δ1d| / BTC–ETH–LUNC correlation (60d)	Yahoo Finance	1.94×	1.05×	1.11×
Fukushima	Physical Infrastructure	log10 daily seismic energy / Nikkei volatility (5d) / |Δ USD/JPY|	USGS / Yahoo Finance	2.25×	1.24×	1.54×
COVID-19	Pandemic / Public Health	Global cases (7d average) / VIX / HY spread	JH CSSE / Yahoo Finance / FRED	3,626.66×	2,573.20×	8,856.12×
Supply Chain	Global Logistics	PCEDG |MoM| / positive delivery-time index / Freight PPI |MoM|	FRED	9.21×	3.33×	4.65×
Full-window Sep(Π) is the original cumulative crisis/control ratio. Full-window Sep(S̄) compares mean stress over the original specified windows. Post-control Sep(S̄), the revised primary contrast, compares mean stress strictly after the control-window end with mean stress over the full prespecified control window.

Framework
For observation i:

S_i = rho_tilde_i * psi_tilde_i * omega_tilde_i
Pi_k = sum(S_i * w_i)
S_i is dimensionless normalized stress.

Each normalized channel enters once with unit exponent.

No outcome-optimized weights or exponents are fitted.

w_i is a fixed observation weight: 1/365 for daily-indexed series and 1/12 for monthly-indexed series.

These weights are not exact elapsed-time intervals.

Pi_k is cumulative normalized stress under this repository convention, not physical energy, physical damage, or a calibrated risk probability.

rho, psi, and omega are retrospective heuristic roles, not identified causal components.

Design Notes
Observation weights
The repository uses fixed per-observation weights of 1/365 for daily-indexed data and 1/12 for monthly-indexed data. This is a reproducible scaling convention, not exact elapsed-time numerical integration.

The standalone historical 2008 calculator uses 1/252. A common observation-weight factor cancels from cumulative crisis/control ratios, while the revised mean-stress estimand does not use these weights. Absolute Pi values therefore depend on the stated repository convention; invariance to a common factor is algebraic rather than independent empirical robustness.

Overlapping control design and revised primary contrast
The original control window is fully contained within the crisis range in 4 of 5 cases. In the 2008 case it overlaps 347 of 574 control observations (60.45%). Consequently, the original cumulative crisis/control ratio is partly affected by duplicated observations and unequal accumulation lengths.

The revised primary estimand removes exact overlap from the crisis side. It compares mean stress in crisis observations strictly after the control-window end with mean stress over the full prespecified control window. The resulting ratios are 15.92×, 1.11×, 1.54×, 8,856.12×, and 4.65× for the five selected cases, respectively.

This removes the direct overlap and cumulative-duration artifact from the primary contrast, but it does not create independently sampled controls or eliminate case-selection, variable-selection, event-date, carryover, and window-design limitations. The original-window permutation tables remain available as legacy diagnostics. A separate post-control permutation analysis evaluates temporal alignment among the three channels within the same post-control segment used by the primary comparison. Neither permutation procedure is a direct test of the crisis-control mean difference or independent prospective validation.

COVID-19 floor effect
The extreme COVID-19 ratios are partly a floor effect: reported cases were zero for 98% of the selected control period, mechanically making S(t) = 0 under the multiplicative construction. This affects both the original cumulative ratio (3,626.66×) and the post-control mean-stress ratio (8,856.12×). These magnitudes are not directly comparable with the other cases and should not be interpreted as a general effect-size ranking.

Unit-exponent product
The three normalized channels each enter the product once with unit exponent. This does not imply equal numerical contribution: calibration choices and channel distributions determine their effective scales. The specification is not claimed to be uniquely optimal, physically privileged, or universally transportable.

Reproducibility
Random-number generation: Deterministic seeds are fixed within each analysis. The post-control permutation table records a distinct seed for every case-method combination and uses finite Monte Carlo p-values (b+1)/(m+1).

Environment: Python 3.11.8 in CI, dependencies pinned in requirements-lock.txt.

Frozen API vintage: CI fixes FRED realtime window via FRED_VINTAGE_DATE=2026-02-17.

Golden baseline verification: CI compares generated output/*.csv, output/*.txt, and data/*.csv against golden/ reference files using SHA-256.

Secrets required: FRED_API_KEY must be configured in GitHub Actions secrets for full pipeline.

GitHub Actions: The full pipeline runs in CI, verifies deterministic artifacts, generates the revised manuscript figures, assembles the final submission package, and uploads two artifacts:

pi-analysis-results — full analysis, data, and audit outputs

submission-figures — the final seven-figure submission package

Note on pi column in CSV data files: The pi column in data/ CSV files is recomputed at runtime by run_all.py using stress × dt (dt=1/365 for daily, dt=1/12 for monthly). Raw observations (rho, psi, omega, rho_norm, psi_norm, omega_norm, stress) are unchanged from original computation. The 2008 case CSV was originally generated with dt=1/252 by pi_calculator.py, but run_all.py overrides this with dt=1/365 for consistency with other cases. This has no effect on any reported ratio or test statistic.

Known Limitations
Supply Chain permutation tests: The original-window test is non-significant (p = 0.26). In the 30-observation post-control segment, the independent-shuffle p-value is 0.192 and block-shuffle p-values range from 0.148 to 0.208. Both the 9.21× original cumulative contrast and the 4.65× post-control mean-stress contrast therefore remain descriptive.

COVID-19 block-shuffle sensitivity: The post-control independent shuffle is significant (p = 0.0001), and block size 5 remains significant (p = 0.015), but block sizes 10 and 20 are not significant (p = 0.066 and 0.228). The channel-alignment result weakens when longer temporal dependence is preserved.

Supply Chain channel dependence: The control-window correlation between psi and omega reaches 0.952, and the two-channel psi × omega formulation exceeds the three-channel product. This is reported as a descriptive dependence limitation rather than a pass/fail test of non-redundancy.

Terra-Luna marginal separation: The original full-window mean-stress ratio is 1.0525× and the post-control ratio is 1.1149×. The post-control independent and block-shuffle diagnostics are significant, but the observed crisis-control stress-intensity difference remains small and specification-sensitive.

Legacy pattern-label audit: Ductile, Brittle, and Pre-loaded labels and their threshold grid are retained for reproducibility but excluded from the revised evidentiary package. They are not established system classes.

Legacy SVB feasibility audit: A like-for-like SVB-era transfer was infeasible because the TEDRATE specification cannot be reconstructed over the requested period. The optional audit is retained for transparency and is not treated as out-of-sample validation.

Additional comparison cases: Dot-com, Repo, and Thailand have exploratory mean-stress ratios of 0.904×, 1.203×, and 3.725×. Their mixed and metric-dependent results are reported as boundary comparisons rather than formal controls or validation episodes; their pairwise correlations are reported descriptively without a pass/fail threshold.

Sample size: The five primary cases support a proof-of-concept retrospective characterization only. They are insufficient for statistical generalization, universal validation, or estimation of cross-domain performance.

Variable selection: Variables were selected through domain judgment and iterative, partly post hoc refinement. The specifications are not claimed to be unique or optimal, and inferential results are conditional on these selected variables and windows.

Legacy ST17 trajectory audit: Retrospective rolling-threshold trajectories and control exceedances are retained as audit artifacts but excluded from revised evidence. They do not establish prospective warning lead, forecasting performance, or calibrated false-alarm rates.

Data
Primary manuscript analyses run from pre-computed case files in data/.
Raw source data (used to build case datasets and supplementary tests) come from public APIs:

FRED: DFF, TEDRATE, TOTBKCR, BAMLH0A0HYM2, PCEDG, DTCDISA066MSFRBNY, WPU3012, DGORDER

FRED (supplementary substitution tests): DGS2, VIXCLS, COMPOUT

USGS Earthquake Hazards: Japan M2+ events via FDSN Event API

Johns Hopkins CSSE: Global confirmed COVID-19 cases

Yahoo Finance: BTC-USD, ETH-USD, LUNC-USD, ^N225, JPY=X, ^VIX

Note: Proxy series (e.g., HYG/LQD fallback) exist only as contingency logic in data-collection utilities and are not part of the baseline manuscript tables unless explicitly stated.

Repository Structure
├── .github/workflows/run_analysis.yml  # Locked CI, verification, and submission-figure artifacts
├── Cases/                              # Individual case data generation scripts
│   ├── config.py                       #   2008 case configuration
│   ├── data_fetcher.py                 #   FRED data fetcher (requires API key)
│   ├── pi_calculator.py                #   Core Π calculator (standalone dt=1/252)
│   ├── main.py                         #   2008 case standalone pipeline
│   ├── case2_terra_luna.py             #   Terra-Luna data collection + calculation
│   ├── case3_fukushima.py              #   Fukushima data collection + calculation
│   ├── case4_covid.py                  #   COVID-19 data collection + calculation
│   ├── case5_supply_chain.py           #   Supply Chain data collection + calculation
│   └── visualize.py                    #   Plotting utilities
├── data/                               # Frozen primary and additional-case CSV inputs (16 files)
├── sensitivity/                        # Sensitivity analyses
│   ├── sensitivity_delta_k.py          #   Legacy ST15 alternate reconstruction audit
│   └── sensitivity_matched_pipeline.py #   Legacy audit-only analysis; excluded from revised evidence
├── scripts/
│   ├── make_nonoverlap_figures.py      # Revised manuscript Figures 2–4
│   ├── make_benchmark_revised.py       # Revised Supplementary Figure S1
│   ├── assemble_submission_figures.py  # Assemble final seven-figure submission set
│   └── verify_outputs.py               # Classified deterministic artifact verifier
├── run_all.py                          # Original-window and legacy generator; retained Figures 1 and 5
├── run_benchmark.py                    # Historical channel-ablation audit
├── run_v12_enhancements.py             # Legacy block-permutation and correlation diagnostics
├── run_v13_enhancements.py             # Sliding window and additional cases
├── run_nonoverlap_reanalysis.py        # Post-control comparison, ablations, and permutation diagnostics
├── run_threshold_grid.py               # Legacy retrospective-label threshold-grid audit
├── run_variable_substitution.py        # Active specification-sensitivity diagnostic
├── run_additional_cases.py             # Additional case computation
├── run_additional_metric_alignment.py  # Additional-case metric alignment from frozen inputs
├── run_specification_provenance.py     # Retrospective case-variable provenance table
├── run_method_comparison.py            # ST17 trajectory and optional ST16 audit outputs
├── output/figures/
│   ├── legacy/                         # Original-window and audit figures
│   ├── revised/                        # Revised manuscript figures
│   └── submission/                     # Final seven-figure package and manifest
├── requirements-lock.txt               # Pinned Python dependency versions
├── golden/                             # Frozen baseline outputs used in CI reproducibility check
├── Audit report.md                     # Code and data integrity audit results
├── revision_analysis_decisions.md      # Post-review analysis decision record
├── LICENSE                             # MIT License
└── README.md                           # This file
AI Disclosure
Large language models were used to assist with code development, pipeline refinement, reproducibility hardening, independent review, and audit/readme editing, including:

Claude Opus 4.5 (Anthropic)

Claude Opus 5 (Anthropic)

Claude Fable 5 (Anthropic)

GPT-5.3 Codex (OpenAI)

GPT-5.6 Thinking (OpenAI)

All scientific hypotheses, variable selections, methodological decisions, interpretation, and final conclusions were made by the author. Model-generated suggestions were reviewed and accepted, modified, or rejected by the author before incorporation.
The complete code is publicly available for independent verification. A full audit record is documented in Audit report.md.

Citation
If you use this framework, please cite:

[Paper citation pending]
