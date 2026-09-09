#!/usr/bin/env python3
"""Protocol-frozen LTCM 1998 historical holdout.

Frozen specification:
- channel_selection_protocol_v1.md @ a179608
- ltcm_protocol_addendum_v1_1.md @ 3448f2e
- ltcm_protocol_addendum_v1_2.md @ 50f1438
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parent
CASES_DIR = BASE / "Cases"
DATA_DIR = BASE / "data" / "ltcm_holdout"
OUT_DIR = BASE / "output" / "ltcm_holdout"

PROTOCOL_SHA = "1a843d8cae550da2019c2bb8f39c38a5c7be11c5d8d75aa432cd5a3d33701f8d"
ADDENDUM_V1_1_SHA = "d49d97b889eed4d8b760081718ba3be61d16be7fb8bbaaf94bfbe245d0280095"
ADDENDUM_V1_2_SHA = "4912c7aa02a9f23ab0a08311c9fb0fe05f12cfb1c64a17af47f9de0a7ecc162b"
PROTOCOL_COMMIT = "a179608"
ADDENDUM_V1_1_COMMIT = "3448f2e"
ADDENDUM_V1_2_COMMIT = "50f1438"

REFERENCE_DATE = "1998-09-23"
FRED_VINTAGE_DATE = "2026-09-09"
DATA_START = "1994-01-08"
DATA_END = "1999-07-08"
CONTROL_START = "1994-01-08"
CONTROL_END = "1996-07-07"
CALIBRATION_START = "1995-01-09"
CALIBRATION_END = "1997-07-07"
POST_CONTROL_END = "1999-04-08"

DELTA = 5
PERCENTILE = 99
N_PERMUTATIONS = 10_000
BLOCK_SIZES = (5, 10, 20)
SEEDS = {"independent": 20261231, 5: 20261232, 10: 20261233, 20: 20261234}
SERIES = {"rho": "DFF", "psi": "TEDRATE", "omega": "TOTBKCR"}

# Existing 2008 modules read these at import/runtime; do not edit Cases/config.py.
os.environ["FRED_VINTAGE_DATE"] = FRED_VINTAGE_DATE
sys.path.insert(0, str(CASES_DIR))

import config as case_config  # noqa: E402
from data_fetcher import (  # noqa: E402
    compute_rate_of_change,
    fetch_fred_series,
    interpolate_monthly_to_daily,
)
from pi_calculator import PiResearchCalculator  # noqa: E402
from run_nonoverlap_reanalysis import (  # noqa: E402
    ABLATION_METHODS,
    FORMULATIONS,
    _block_shuffle,
    _permutation_summary,
    _stable_mean,
    mean_ratio,
)


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_protocol() -> None:
    checks = (
        (BASE / "channel_selection_protocol_v1.md", PROTOCOL_SHA),
        (BASE / "ltcm_protocol_addendum_v1_1.md", ADDENDUM_V1_1_SHA),
        (BASE / "ltcm_protocol_addendum_v1_2.md", ADDENDUM_V1_2_SHA),
    )
    for path, expected in checks:
        if not path.exists() or sha(path) != expected:
            raise RuntimeError(f"Frozen protocol integrity failure: {path.name}")


def git_head() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=BASE, text=True
    ).strip()


def save_series(series: pd.Series, path: Path) -> None:
    pd.DataFrame({"date": series.index, "value": series.to_numpy()}).to_csv(
        path, index=False, float_format="%.17g", date_format="%Y-%m-%d"
    )


def collect() -> tuple[pd.Series, pd.Series, pd.Series, list[Path]]:
    if not os.environ.get("FRED_API_KEY"):
        raise RuntimeError("FRED_API_KEY is required; no analysis was run.")
    case_config.FRED_VINTAGE_DATE = FRED_VINTAGE_DATE

    raw = {
        key: fetch_fred_series(series_id, DATA_START, DATA_END)
        for key, series_id in SERIES.items()
    }
    rho = compute_rate_of_change(raw["rho"], DELTA)
    psi = compute_rate_of_change(raw["psi"], DELTA)
    idx = rho.dropna().index.intersection(psi.dropna().index)
    omega = interpolate_monthly_to_daily(raw["omega"], idx)

    rho, psi, omega = rho.reindex(idx), psi.reindex(idx), omega.reindex(idx)
    valid = rho.notna() & psi.notna() & omega.notna()
    idx = idx[valid]
    rho, psi, omega = rho.reindex(idx), psi.reindex(idx), omega.reindex(idx)
    if idx.empty or idx.has_duplicates or not idx.is_monotonic_increasing:
        raise RuntimeError("Invalid aligned LTCM index.")

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    raw_paths = []
    for key, series_id in SERIES.items():
        path = DATA_DIR / f"raw_{series_id}.csv"
        save_series(raw[key], path)
        raw_paths.append(path)
    return rho, psi, omega, raw_paths


def evaluate(rho: pd.Series, psi: pd.Series, omega: pd.Series):
    calc = PiResearchCalculator()
    p_limits = calc.calibrate(
        rho, psi, omega,
        stable_start=CALIBRATION_START,
        stable_end=CALIBRATION_END,
        percentile=PERCENTILE,
    )
    frame = calc.calculate(
        rho, psi, omega,
        analysis_start=CONTROL_START,
        analysis_end=POST_CONTROL_END,
    )
    control = frame.loc[CONTROL_START:CONTROL_END].copy()
    post = frame.loc[
        (frame.index > pd.Timestamp(CONTROL_END))
        & (frame.index <= pd.Timestamp(POST_CONTROL_END))
    ].copy()
    if control.empty or post.empty or len(control.index.intersection(post.index)):
        raise RuntimeError("Frozen control/post-control split is invalid.")
    return frame, control, post, p_limits


def primary_table(control: pd.DataFrame, post: pd.DataFrame) -> pd.DataFrame:
    post_mean, control_mean, ratio = mean_ratio(post, control, FORMULATIONS[0][1])
    return pd.DataFrame([{
        "Case": "LTCM 1998",
        "Domain": "Traditional Finance",
        "Reference_date": REFERENCE_DATE,
        "Control_start": control.index.min().date().isoformat(),
        "Control_end": control.index.max().date().isoformat(),
        "Post_control_start": post.index.min().date().isoformat(),
        "Post_control_end": post.index.max().date().isoformat(),
        "N_control": len(control),
        "N_post_control": len(post),
        "N_exact_overlap": 0,
        "Mean_stress_control": control_mean,
        "Mean_stress_post_control": post_mean,
        "Post_control_to_control_mean_ratio": ratio,
    }]).round(10)


def comparison_table(control: pd.DataFrame, post: pd.DataFrame, definitions) -> pd.DataFrame:
    rows = []
    for item in definitions:
        if len(item) == 2:
            name, fn = item
            row = {"Definition": name}
        else:
            name, level, fn = item
            row = {"Definition": name, "Level": level}
        post_mean, control_mean, ratio = mean_ratio(post, control, fn)
        row.update({
            "N_post_control": len(post),
            "N_control": len(control),
            "Mean_post_control": post_mean,
            "Mean_control": control_mean,
            "Post_control_to_control_mean_ratio": ratio,
        })
        rows.append(row)
    out = pd.DataFrame(rows)
    out["Rank_within_case"] = (
        out["Post_control_to_control_mean_ratio"]
        .rank(method="min", ascending=False).astype(int)
    )
    for c in ("Mean_post_control", "Mean_control", "Post_control_to_control_mean_ratio"):
        out[c] = out[c].round(10)
    return out


def correlation_table(control: pd.DataFrame) -> pd.DataFrame:
    corr = control[["rho", "psi", "omega"]].corr()
    pairs = (("rho", "psi"), ("rho", "omega"), ("psi", "omega"))
    return pd.DataFrame([
        {"Channel_1": a, "Channel_2": b, "Pearson_r": round(float(corr.loc[a, b]), 10)}
        for a, b in pairs
    ])


def permutation_table(post: pd.DataFrame) -> pd.DataFrame:
    rho = post["rho_norm"].to_numpy(float)
    psi = post["psi_norm"].to_numpy(float)
    omega = post["omega_norm"].to_numpy(float)
    observed = _stable_mean(rho * psi * omega)
    rows = []

    rng = np.random.default_rng(SEEDS["independent"])
    null = np.empty(N_PERMUTATIONS)
    for i in range(N_PERMUTATIONS):
        null[i] = _stable_mean(
            rho[rng.permutation(len(rho))]
            * psi[rng.permutation(len(psi))]
            * omega[rng.permutation(len(omega))]
        )
    rows.append({
        "Method": "Independent shuffle", "Block_size_observations": 1,
        "N_permutations": N_PERMUTATIONS, "RNG_seed": SEEDS["independent"],
        "Observed_mean_stress": observed, **_permutation_summary(observed, null),
    })

    for block in BLOCK_SIZES:
        if block >= len(post):
            raise RuntimeError(f"Frozen block size {block} invalid for N={len(post)}")
        rng = np.random.default_rng(SEEDS[block])
        null = np.empty(N_PERMUTATIONS)
        for i in range(N_PERMUTATIONS):
            null[i] = _stable_mean(
                _block_shuffle(rho, block, rng)
                * _block_shuffle(psi, block, rng)
                * _block_shuffle(omega, block, rng)
            )
        rows.append({
            "Method": "Block shuffle", "Block_size_observations": block,
            "N_permutations": N_PERMUTATIONS, "RNG_seed": SEEDS[block],
            "Observed_mean_stress": observed, **_permutation_summary(observed, null),
        })

    out = pd.DataFrame(rows)
    for c in ("Observed_mean_stress", "Null_mean_stress", "Null_std_stress", "z_score", "p_value_plus_one"):
        out[c] = out[c].round(10)
    return out


def main() -> int:
    verify_protocol()
    analysis_commit = git_head()
    rho, psi, omega, raw_paths = collect()
    frame, control, post, p_limits = evaluate(rho, psi, omega)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    processed_path = DATA_DIR / "ltcm_historical_holdout_processed.csv"
    frame.index.name = "date"
    frame.to_csv(processed_path, float_format="%.17g", date_format="%Y-%m-%d")

    outputs = {
        "primary": primary_table(control, post),
        "formulations": comparison_table(control, post, FORMULATIONS),
        "ablation": comparison_table(control, post, ABLATION_METHODS),
        "correlations": correlation_table(control),
        "permutation": permutation_table(post),
    }
    paths = {}
    for name, table in outputs.items():
        path = OUT_DIR / f"table_ltcm_{name}.csv"
        table.to_csv(path, index=False)
        paths[name] = path

    artifact_paths = [*raw_paths, processed_path, *paths.values()]
    manifest = {
        "case": "LTCM 1998",
        "reference_date": REFERENCE_DATE,
        "fred_vintage_date": FRED_VINTAGE_DATE,
        "series": SERIES,
        "data_start": DATA_START,
        "data_end": DATA_END,
        "control": [CONTROL_START, CONTROL_END],
        "calibration": [CALIBRATION_START, CALIBRATION_END],
        "post_control_end": POST_CONTROL_END,
        "delta_observations": DELTA,
        "percentile": PERCENTILE,
        "p_limits": {k: float(v) for k, v in p_limits.items()},
        "seeds": {str(k): int(v) for k, v in SEEDS.items()},
        "block_sizes": list(BLOCK_SIZES),
        "n_permutations": N_PERMUTATIONS,
        "protocol_commit": PROTOCOL_COMMIT,
        "protocol_sha256": PROTOCOL_SHA,
        "addendum_v1_1_commit": ADDENDUM_V1_1_COMMIT,
        "addendum_v1_1_sha256": ADDENDUM_V1_1_SHA,
        "addendum_v1_2_commit": ADDENDUM_V1_2_COMMIT,
        "addendum_v1_2_sha256": ADDENDUM_V1_2_SHA,
        "analysis_code_commit": analysis_commit,
        "artifact_sha256": {
            p.relative_to(BASE).as_posix(): sha(p) for p in artifact_paths
        },
    }
    (OUT_DIR / "manifest_ltcm.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    print("\n===== LTCM PRIMARY =====")
    print(outputs["primary"].to_string(index=False))
    print("\n===== FORMULATIONS =====")
    print(outputs["formulations"][["Definition", "Post_control_to_control_mean_ratio", "Rank_within_case"]].to_string(index=False))
    print("\n===== ABLATION =====")
    print(outputs["ablation"][["Definition", "Post_control_to_control_mean_ratio", "Rank_within_case"]].to_string(index=False))
    print("\n===== CORRELATIONS =====")
    print(outputs["correlations"].to_string(index=False))
    print("\n===== PERMUTATION =====")
    print(outputs["permutation"][["Method", "Block_size_observations", "z_score", "p_value_plus_one"]].to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
