# Manuscript Figures

This directory contains the manuscript-specific figure-generation layer for the current paper.

The underlying frozen analysis outputs remain in their canonical locations under:

- `archive/zenodo_v3/golden/output/`
- `archive/zenodo_v3/golden/ltcm_holdout/`
- `zenodo_v4/holdout2/results/`
- `zenodo_v4/simulation/results/`

The scripts in this directory only read those frozen outputs and render the five manuscript figures.

## Build

From the repository root:

```bash
bash manuscript_figures/build_final_figure_set.sh
```

This regenerates:

- Figure 1 — framework and evidence design
- Figure 2 — development-case multiplicative separation
- Figure 3 — LTCM frozen historical holdout
- Figure 4 — Holdout 2 output-blind historical transfer
- Figure 5 — controlled Simulation v2

The final PNG/PDF set is assembled under `manuscript_figures/final_figure_set/`, with a SHA-256 manifest and a local ZIP. Generated binary outputs are ignored by Git and are produced by GitHub Actions as the `manuscript-figure-set` artifact.

Figure 5 intentionally preserves the frozen combined-simulation panel layout while applying the manuscript operator color mapping: Product blue, Sum light gray, Maximum dark gray.
