# A Cross-Domain Multiplicative Framework for Systemic Stress

This repository contains the current development version of a cross-domain framework for multichannel systemic-stress characterization.

The core score is deliberately simple:

S_t = z1,t × z2,t × z3,t

where each non-negative channel is normalized using a fixed calibration rule. The framework uses no fitted channel weights, fitted exponents, machine-learning optimization, or adaptive thresholds.

## Current status


**Zenodo v4 — pre-results evaluation stage**

The current evaluation layer is being frozen before inspection of new simulation or Holdout-2 analytical outputs.

The v4 design asks two focused questions:

1. How does the product behave as the number of simultaneously stressed channels increases?
2. How does cross-channel dependence alter product behavior relative to additive and maximum benchmarks?

The design principle is:

> **Simple model, hard tests.**

No v4 analytical result should be interpreted as prespecified unless the governing protocol and machine-readable configuration were committed before that result was inspected.

## Repository structure

    .
    ├── README.md
    ├── LICENSE
    ├── requirements-lock.txt
    ├── Cases/
    ├── data/
    ├── zenodo_v4/
    │   ├── protocol/
    │   │   ├── Protocol_v2_FINAL_PreFreeze.docx
    │   │   └── Holdout_2_Eligibility_Plan_FINAL_PreOutput.docx
    │   └── config/
    │       ├── simulation_config_v2.json
    │       └── holdout2_candidate_query.json
    └── archive/
        └── zenodo_v3/

## Current v4 layer

The `zenodo_v4/` directory contains the current pre-results evaluation protocol and machine-readable configuration for the next archival version.

No new simulation output or Holdout-2 framework score should be inspected before the relevant freeze commits and tags are recorded.

## Retained development cases

The `Cases/` directory contains the retrospective development-case implementations retained from the previous research stage.

These cases remain development evidence and are not reclassified as independent validation.

## Data

The `data/` directory contains retained project data and frozen historical material required by the current evaluation workflow.

## Previous Zenodo v3 archive

The `archive/zenodo_v3/` directory contains the prior analysis code, audit material, golden outputs, sensitivity analyses, figures, verification scripts, and workflow associated with the previous archived version.

These materials are retained for provenance and reproducibility rather than presented as the current analysis pipeline.

## Existing archived version

The previous archived research state is preserved through Zenodo.

**DOI:** `10.5281/zenodo.22765907`

Historical reproducibility snapshot:

`df0f0ca58bcfdd6582ef52c936ad7a8ac68b9937`

The current v4 work does not overwrite that archived state.

## Evaluation policy

The current evaluation follows fixed principles:

- no post-result operator tuning;
- no fitted channel weights or exponents;
- product, sum, and maximum use identical normalized inputs;
- controlled simulation results are interpreted conditionally rather than used to declare a universal winner;
- existing historical cases retain their development status;
- the new historical holdout is selected using an output-blind prespecified procedure;
- unfavorable, weak, or null results are retained;
- post-freeze corrections require an explicit dated amendment.

## Version terminology

Repository/archive version and protocol version are separate:

- **Zenodo v3** — previous archived research state;
- **Zenodo v4** — current research revision under development;
- **Protocol v2** — version of the controlled-evaluation protocol used within Zenodo v4.

## License

See `LICENSE`.
