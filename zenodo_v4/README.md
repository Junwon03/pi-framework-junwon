# Zenodo v4 Frozen Evaluation Layer

This directory contains the frozen post-development evaluation layer used by the current manuscript revision.

## Scope

Zenodo v4 adds two evaluation components to the retained Zenodo v3 development evidence:

1. **Historical Holdout 2** — an output-blind earthquake transfer selected from a prespecified candidate universe using a fixed random seed and no redraw.
2. **Controlled Simulation v2** — a frozen factorial simulation testing activation breadth, cross-channel dependence, and paired normalization behavior for product, sum, and maximum operators.

The previously frozen **LTCM 1998 historical holdout** remains part of the manuscript evidence hierarchy but is preserved under `archive/zenodo_v3/`. The v4 packaging workflow copies the required LTCM frozen materials into the assembled analysis package so that a review/archive artifact can support the complete manuscript evidence chain without altering the original v3 provenance.

## Freeze chronology

The governing selection/protocol/configuration materials were committed before the corresponding outputs were inspected. The repository history records the main sequence:

- Holdout 2 selection freeze before framework output;
- frozen Holdout 2 analysis pipeline;
- frozen Holdout 2 outputs;
- frozen Simulation v2 pipeline/configuration;
- frozen Simulation v2 outputs;
- manuscript simulation figures generated afterward.

The exact Git history is the provenance record. This README summarizes rather than replaces it.

## Directory map

```text
zenodo_v4/
├── README.md
├── protocol/
│   ├── Protocol_v2_FINAL_PreFreeze.docx
│   └── Holdout_2_Eligibility_Plan_FINAL_PreOutput.docx
├── config/
│   ├── simulation_config_v2.json
│   └── holdout2_candidate_query.json
├── holdout2/
│   ├── build_candidate_universe.py
│   ├── build_eligibility_audit.py
│   ├── select_holdout2_event.py
│   ├── run_holdout2_analysis.py
│   ├── holdout2_candidate_universe.csv
│   ├── holdout2_eligibility_audit.csv
│   ├── holdout2_selection_record.json
│   ├── holdout2_selected_event.json
│   ├── holdout2_preoutput_sha256.txt
│   ├── holdout2_result_sha256.txt
│   ├── data/
│   └── results/
└── simulation/
    ├── run_simulation_v2.py
    ├── make_figure_simulation_primary.py
    ├── make_figure_simulation_combined.py
    ├── simulation_v2_result_sha256.txt
    ├── results/
    └── figures/
```

## Holdout 2

The candidate universe contains Japan-region earthquakes meeting the prespecified magnitude/date criteria. Eligibility was determined without using framework outputs. The selected event was drawn once from the sorted eligible-event list with the frozen RNG rule. No redraw was permitted.

The frozen result files and their hashes are recorded under `holdout2/`. The selected-event analysis contains 250 control and 250 post observations and uses the development-informed Fukushima channel template with the prespecified alignment corrections documented in the protocol.

## Simulation v2

Simulation v2 uses the frozen configuration in `config/simulation_config_v2.json`. The design varies:

- activation breadth `k ∈ {1,2,3}`;
- equicorrelation `rho ∈ {0,0.3,0.6,0.9}`;
- stress intensity `delta ∈ {0.5,1.0,1.5}`;
- fixed product, sum, and maximum operators;
- primary P99 normalization plus a paired bounded empirical-percentile reanalysis on the same generated observations.

The primary comparison is matched-null standardized separation. No global operator winner, threshold optimization, classifier, AUC, or forecasting model is fitted.

## Verification

From the repository root, the packaging workflow performs:

```bash
sha256sum -c zenodo_v4/holdout2/holdout2_preoutput_sha256.txt
sha256sum -c zenodo_v4/holdout2/holdout2_result_sha256.txt
sha256sum -c zenodo_v4/simulation/simulation_v2_result_sha256.txt
```

It also validates expected frozen row counts, period counts, missingness, finite simulation statistics, and duplicate keys before assembling the artifact.

The workflow additionally carries forward the canonical Zenodo v3 development outputs and frozen LTCM holdout materials into the assembled package. Those copied files remain v3 provenance artifacts; copying them into a v4 package does not relabel them as newly generated v4 evidence.

## Interpretation boundary

- Development cases are retrospective.
- LTCM is a directly nominated frozen historical transfer.
- Holdout 2 strengthens event-selection independence but inherits a development-informed physical-disaster template.
- Simulation isolates operator behavior under a known data-generating process.
- None of these components alone establishes prospective forecasting accuracy, population-level diagnostic performance, causal identification, or universal product superiority.

## Legacy implementation note

The current hardened development calculator rejects invalid or non-positive calibration references rather than substituting an epsilon and rejects negative/non-finite normalization inputs rather than silently clipping them. Some archived Zenodo v3 sensitivity/audit scripts retain historical epsilon-floor behavior. The distinction is preserved intentionally for provenance.
