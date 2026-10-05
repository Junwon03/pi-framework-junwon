# A Cross-Domain Multiplicative Framework for Systemic Stress

This repository contains the current research and reproducibility materials for a deliberately simple cross-domain framework for multichannel systemic-stress characterization.

The core score is

`S_t = z1,t × z2,t × z3,t`

where each non-negative channel is normalized using a fixed calibration rule. The framework uses no fitted channel weights, fitted exponents, machine-learning optimization, or adaptive thresholds.

## Current status

**Zenodo v4 — frozen evaluation results available**

The current repository state contains the prespecified and frozen evaluation layer developed after the retrospective Zenodo v3 analyses. It includes:

- five retrospective development cases retained from the prior archive;
- the frozen 1998 LTCM historical holdout retained unchanged from Zenodo v3;
- an output-blind historical earthquake holdout selected from a prespecified candidate universe with a fixed random seed and no redraw;
- controlled Simulation v2 results varying activation breadth and cross-channel dependence under fixed product, sum, and maximum operators;
- machine-readable configurations, frozen outputs, source snapshots where required, and SHA-256 manifests.

The v4 evaluation asks two focused structural questions:

1. How does the product behave as the number of simultaneously stressed channels increases?
2. How does cross-channel dependence alter product behavior relative to additive and maximum benchmarks?

The design principle is:

> **Simple model, hard tests.**

The v4 holdout-selection and simulation protocols/configurations were committed before the corresponding frozen outputs were inspected. Historical development cases remain retrospective and are not relabeled as independent validation.

## Evidential hierarchy

The repository intentionally separates evidence with different levels of design independence:

1. **Retrospective development cases** — five heterogeneous historical episodes used to develop and characterize the framework.
2. **Historical Holdout 1: LTCM 1998** — the frozen 2008 financial specification transferred without result-driven revision; the unfavorable operator ranking is retained.
3. **Historical Holdout 2** — a development-informed earthquake template with output-blind event selection from a prespecified candidate universe, fixed seed, and no redraw.
4. **Controlled Simulation v2** — activation breadth, dependence, and normalization are varied under a known data-generating process.

Neither historical holdout is prospective. The repository does not claim calibrated forecasting accuracy, causal identification, universal operator superiority, or a universal numerical risk scale.

## Repository structure

```text
.
├── README.md
├── LICENSE
├── requirements-lock.txt
├── Cases/                         # retained/hardened development implementations
├── data/                          # retained project data and historical material
├── zenodo_v4/
│   ├── README.md                  # v4 freeze/results map and verification guide
│   ├── protocol/                  # prespecified protocol documents
│   ├── config/                    # machine-readable frozen configurations
│   ├── holdout2/                  # selection records, data, outputs, manifests
│   └── simulation/                # code, replicate outputs, summaries, figures, manifests
└── archive/
    └── zenodo_v3/                 # previous frozen archive, development outputs, LTCM holdout
```

## Zenodo v4 layer

The `zenodo_v4/` directory contains the frozen Holdout 2 and Simulation v2 evaluation materials. See `zenodo_v4/README.md` for the freeze chronology, contents, and verification map.

The GitHub Actions workflow `.github/workflows/build_zenodo_v4_package.yml` verifies the frozen v4 hashes and structural checks and assembles a review/archive package. The package also carries forward the canonical Zenodo v3 development outputs and the frozen LTCM holdout materials needed to support the current manuscript evidence hierarchy.

## Retained development cases

The `Cases/` directory contains the retrospective development-case implementations retained from the previous research stage. These cases remain development evidence.

The current hardened calculator rejects invalid, non-finite, negative, or non-positive calibration inputs rather than silently replacing them. Some legacy Zenodo v3 audit/sensitivity code retains historical epsilon-floor behavior; those files are preserved for provenance and should not be confused with the current hardened implementation.

## Previous Zenodo v3 archive

The `archive/zenodo_v3/` directory contains the previous analysis code, frozen inputs, audit material, golden outputs, sensitivity analyses, figures, verification scripts, and the frozen LTCM historical holdout.

**Archived DOI:** `10.5281/zenodo.22765907`

Historical reproducibility snapshot:

`df0f0ca58bcfdd6582ef52c936ad7a8ac68b9937`

The current v4 work does not overwrite that archived state. Historical audit documents are retained as provenance records even when later canonical outputs supersede a stale value. See `archive/zenodo_v3/docs/CORRECTION_2026-10-05.md` for the explicit Fukushima audit-table correction and implementation clarification.

## Evaluation policy

The current evaluation follows fixed principles:

- no post-result operator tuning;
- no fitted channel weights or exponents;
- product, sum, and maximum use identical normalized inputs within each evaluation;
- controlled simulation results are interpreted conditionally rather than used to declare a universal winner;
- existing historical cases retain their development status;
- Holdout 2 uses an output-blind prespecified selection procedure;
- unfavorable, weak, or null results are retained;
- post-freeze corrections require an explicit dated amendment rather than silent rewriting of provenance.

## Version terminology

Repository/archive version and protocol version are separate:

- **Zenodo v3** — previous archived research state, including the development analyses and frozen LTCM holdout;
- **Zenodo v4** — current frozen evaluation revision containing Holdout 2 and Simulation v2, with v3 evidence carried forward for the manuscript package;
- **Protocol v2** — version of the controlled-evaluation protocol used within Zenodo v4.

## License

See `LICENSE`.
