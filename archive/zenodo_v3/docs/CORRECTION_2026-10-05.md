# Correction note — 2026-10-05

This note records two documentation clarifications identified during the manuscript/repository consistency review. It does **not** alter any frozen analytical output.

## 1. Fukushima post-control mean-stress ratio in `Audit report.md`

The Revision Addendum table in `archive/zenodo_v3/docs/Audit report.md` lists the Fukushima post-control mean-stress ratio as **1.53812×**. That value is stale and is not the canonical frozen revised-primary result.

The canonical frozen output is:

- `archive/zenodo_v3/golden/output/table_nonoverlap_primary.csv`
- `archive/zenodo_v3/golden/output/table_nonoverlap_formulations.csv`

Both record the Fukushima multiplicative post-control/control mean-stress ratio as:

**2.3159924201×**

The current manuscript reports the canonical value (rounded to 2.32×). The stale audit-table value is retained in the historical audit document for provenance and is superseded by this dated correction note.

## 2. Calibration implementation terminology

Historical Zenodo v3 audit/sensitivity code includes an epsilon safety floor such as `max(P99, 1e-10)` in some archived implementations.

The current hardened development calculator (`Cases/pi_calculator.py`) instead rejects invalid, non-finite, or non-positive calibration references and rejects negative/non-finite normalization inputs rather than silently substituting an epsilon or clipping invalid values.

Accordingly, manuscript descriptions of the current framework should not generalize the legacy epsilon-floor behavior to all repository implementations.

## Scope

This correction concerns documentation/provenance only. No frozen input, output, holdout selection, simulation replicate, random seed, or reported canonical result is modified.
