"""
Pi Framework — Exploratory Additional Comparison Cases
============================================
Generates exploratory crisis/control datasets using existing variable
definitions applied to different periods. Archived cumulative quantities
retain historical fixed per-observation weights for reproducibility; these
weights are not elapsed-time integration.

Cases:
  1. 2000 Dot-com Crash (Traditional Finance)
     Variables: DFF × TEDRATE × TOTBKCR (identical to 2008)
     Crisis: 1999-01 to 2002-12
     Control: 1996-01 to 1998-12
     Stable (P-limit): 1993-01 to 1998-12

  2. 2019 Repo Crisis — NEAR-MISS (Traditional Finance)
     Variables: DFF × TEDRATE × TOTBKCR (identical to 2008)
     Crisis: 2019-01 to 2020-02 (pre-COVID, includes Sep 2019 repo spike)
     Control: 2017-01 to 2018-12
     Stable (P-limit): 2014-01 to 2018-12

  3. 2011 Thailand Floods (Global Logistics)
     Variables: DGORDER × ISM delivery times × WPU3012 (identical to Supply Chain)
     Crisis: 2011-01 to 2012-06
     Configured control: 2009-01 to 2010-12
     Usable aligned control observations: 2009-06-01 to 2010-12-01
     Stable (P-limit): 2006-01 to 2010-12

Requires: FRED_API_KEY environment variable
Usage: python run_additional_cases.py

Outputs:
  data/crisis_dotcom_pi.csv, data/control_dotcom_pi.csv
  data/crisis_repo_pi.csv, data/control_repo_pi.csv
  data/crisis_thailand_pi.csv, data/control_thailand_pi.csv
  output/table_additional_cases.csv
  output/table_additional_permutation.csv
  output/table_additional_time_normalized.csv
  output/table_additional_nonredundancy.csv
"""

import pandas as pd
import numpy as np
import os
import sys
import time as time_module
from scipy import stats

FRED_API_KEY = os.environ.get('FRED_API_KEY', '')
FRED_VINTAGE_DATE = os.environ.get("FRED_VINTAGE_DATE", "")
_base = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(_base, 'data')
OUT_DIR = os.path.join(_base, 'output')
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(OUT_DIR, exist_ok=True)

N_PERMUTATIONS = 10_000
PERMUTATION_SEED = 42
MIN_CALIBRATION_OBS = 10


# ================================================================
# FRED FETCH
# ================================================================

def positive_finite_ratio(numerator, denominator, label):
    numerator = float(numerator)
    denominator = float(denominator)

    if not np.isfinite(numerator):
        raise ValueError(
            f"{label}: numerator must be finite."
        )

    if not np.isfinite(denominator) or denominator <= 0:
        raise ValueError(
            f"{label}: denominator must be positive and finite; "
            f"got {denominator}."
        )

    ratio = numerator / denominator

    if not np.isfinite(ratio):
        raise ValueError(
            f"{label}: ratio must be finite."
        )

    return ratio


def fetch_fred(series_id, start, end):
    import requests

    if not FRED_API_KEY:
        raise RuntimeError(
            "FRED_API_KEY is required."
        )

    if not FRED_VINTAGE_DATE:
        raise RuntimeError(
            "FRED_VINTAGE_DATE is required."
        )

    response = requests.get(
        "https://api.stlouisfed.org/fred/series/observations",
        params={
            "series_id": series_id,
            "api_key": FRED_API_KEY,
            "file_type": "json",
            "observation_start": start,
            "observation_end": end,
            "realtime_start": FRED_VINTAGE_DATE,
            "realtime_end": FRED_VINTAGE_DATE,
        },
        timeout=30,
    )

    response.raise_for_status()

    payload = response.json()

    if (
        not isinstance(payload, dict)
        or "observations" not in payload
    ):
        raise ValueError(
            f"{series_id}: invalid FRED response schema."
        )

    observations = payload["observations"]

    if not observations:
        raise ValueError(
            f"{series_id}: no observations returned."
        )

    frame = pd.DataFrame(observations)

    required = {"date", "value"}

    if not required.issubset(frame.columns):
        raise ValueError(
            f"{series_id}: missing FRED fields "
            f"{sorted(required - set(frame.columns))}."
        )

    dates = pd.to_datetime(
        frame["date"],
        errors="coerce",
    )

    if dates.isna().any():
        raise ValueError(
            f"{series_id}: invalid dates returned by FRED."
        )

    raw_values = frame["value"].astype(str).str.strip()

    missing_sentinel = raw_values.eq(".")

    values = pd.to_numeric(
        raw_values.where(
            ~missing_sentinel,
            np.nan,
        ),
        errors="coerce",
    )

    malformed = (
        values.isna()
        & ~missing_sentinel
    )

    if malformed.any():
        raise ValueError(
            f"{series_id}: malformed numeric FRED observations."
        )

    series = pd.Series(
        values.to_numpy(dtype=float),
        index=dates,
        name=series_id,
    ).dropna()

    if series.empty:
        raise ValueError(
            f"{series_id}: no usable numeric observations."
        )

    if series.index.has_duplicates:
        raise ValueError(
            f"{series_id}: duplicate dates returned by FRED."
        )

    series = series.sort_index()

    if not series.index.is_monotonic_increasing:
        raise ValueError(
            f"{series_id}: dates are not chronological."
        )

    if not np.isfinite(
        series.to_numpy(dtype=float)
    ).all():
        raise ValueError(
            f"{series_id}: non-finite values returned by FRED."
        )

    return series

# ================================================================
# CASE DEFINITIONS
# ================================================================

CASES = {
    'dotcom': {
        'name': '2000 Dot-com Crash',
        'domain': 'Traditional Finance',
        'freq': 'weekly',
        'variables': {
            'rho': {'series': 'DFF', 'transform': 'raw'},
            'psi': {'series': 'TEDRATE', 'transform': 'raw'},
            'omega': {'series': 'TOTBKCR', 'transform': 'raw'},
        },
        'stable_start': '1993-01-01',
        'stable_end': '1998-12-31',
        'control_start': '1996-01-01',
        'control_end': '1998-12-31',
        'crisis_start': '1999-01-01',
        'crisis_end': '2002-12-31',
        'fetch_start': '1993-01-01',
        'fetch_end': '2002-12-31',
        'legacy_observation_weight': 1.0 / 365,
    },
    'repo': {
        'name': '2019 Repo Near-miss',
        'domain': 'Traditional Finance (Near-miss)',
        'freq': 'weekly',
        'variables': {
            'rho': {'series': 'DFF', 'transform': 'raw'},
            'psi': {'series': 'TEDRATE', 'transform': 'raw'},
            'omega': {'series': 'TOTBKCR', 'transform': 'raw'},
        },
        'stable_start': '2014-01-01',
        'stable_end': '2018-12-31',
        'control_start': '2017-01-01',
        'control_end': '2018-12-31',
        'crisis_start': '2019-01-01',
        'crisis_end': '2020-02-29',  # Pre-COVID cutoff
        'fetch_start': '2014-01-01',
        'fetch_end': '2020-02-29',
        'legacy_observation_weight': 1.0 / 365,
    },
    'thailand': {
        'name': '2011 Thailand Floods',
        'domain': 'Global Logistics',
        'freq': 'monthly',
        'variables': {
            'rho': {'series': 'DGORDER', 'transform': 'pct_change'},
            'psi': {'series': 'DTCDISA066MSFRBNY', 'transform': 'clip_nonneg'},
            'omega': {'series': 'WPU3012', 'transform': 'pct_change'},
        },
        'stable_start': '2006-01-01',
        'stable_end': '2010-12-31',
        'control_start': '2009-01-01',
        'control_end': '2010-12-31',
        'crisis_start': '2011-01-01',
        'crisis_end': '2012-06-30',
        'fetch_start': '2006-01-01',
        'fetch_end': '2012-06-30',
        'legacy_observation_weight': 1.0 / 12,
    },
}


# ================================================================
# PIPELINE
# ================================================================

def process_case(case_id, case_def):
    print(f'\n  {"=" * 60}')
    print(
        f'  {case_def["name"]} '
        f'({case_def["domain"]})'
    )
    print(f'  {"=" * 60}')

    raw = {}

    for ch_name, ch_def in case_def["variables"].items():
        print(
            f'    Fetching {ch_def["series"]}...'
        )

        series = fetch_fred(
            ch_def["series"],
            case_def["fetch_start"],
            case_def["fetch_end"],
        )

        print(
            f"      -> {len(series)} obs"
        )

        raw[ch_name] = series
        time_module.sleep(0.3)

    # Apply each transform on the native source series first.
    # No pct_change row is invented as zero.
    transformed = {}

    for ch_name, ch_def in case_def["variables"].items():
        series = raw[ch_name].copy()
        transform = ch_def["transform"]

        if transform == "pct_change":
            series = (
                series
                .pct_change(fill_method=None)
                .abs()
                .dropna()
            )

        elif transform == "clip_nonneg":
            # Intentional one-sided stress definition:
            # negative/zero diffusion = no positive delay stress.
            series = series.where(
                series > 0,
                0.0,
            )

        elif transform == "raw":
            pass

        else:
            raise ValueError(
                f"{case_def['name']}/{ch_name}: "
                f"unknown transform {transform!r}."
            )

        values = series.to_numpy(dtype=float)

        if len(values) == 0:
            raise ValueError(
                f"{case_def['name']}/{ch_name}: "
                "transform produced no observations."
            )

        if not np.isfinite(values).all():
            raise ValueError(
                f"{case_def['name']}/{ch_name}: "
                "non-finite transformed values."
            )

        if (values < 0).any():
            raise ValueError(
                f"{case_def['name']}/{ch_name}: "
                "negative transformed stress values."
            )

        transformed[ch_name] = series

    # Exact intersection only. No forward/back fill or interpolation.
    common_idx = transformed["rho"].index

    for ch_name in ["psi", "omega"]:
        common_idx = common_idx.intersection(
            transformed[ch_name].index
        )

    common_idx = common_idx.sort_values()

    if len(common_idx) == 0:
        raise ValueError(
            f"{case_def['name']}: no exact common dates."
        )

    if common_idx.has_duplicates:
        raise ValueError(
            f"{case_def['name']}: duplicate aligned dates."
        )

    print(
        f"    Common index: {len(common_idx)} dates"
    )

    channels = {
        ch_name: transformed[ch_name].reindex(common_idx)
        for ch_name in ["rho", "psi", "omega"]
    }

    aligned = pd.DataFrame(channels)

    if not np.isfinite(
        aligned.to_numpy(dtype=float)
    ).all():
        raise ValueError(
            f"{case_def['name']}: "
            "aligned channels contain non-finite values."
        )

    stable_mask = (
        (common_idx >= pd.Timestamp(case_def["stable_start"]))
        & (common_idx <= pd.Timestamp(case_def["stable_end"]))
    )

    plimits = {}

    for ch_name in ["rho", "psi", "omega"]:
        vals = (
            channels[ch_name][stable_mask]
            .to_numpy(dtype=float)
        )

        if len(vals) <= MIN_CALIBRATION_OBS:
            raise ValueError(
                f"{case_def['name']}/{ch_name}: "
                f"only {len(vals)} stable observations; "
                f"need > {MIN_CALIBRATION_OBS}."
            )

        if not np.isfinite(vals).all():
            raise ValueError(
                f"{case_def['name']}/{ch_name}: "
                "non-finite stable observations."
            )

        p99 = float(
            np.percentile(vals, 99)
        )

        if not np.isfinite(p99) or p99 <= 0:
            raise ValueError(
                f"{case_def['name']}/{ch_name}: "
                f"P99 must be positive and finite; got {p99}."
            )

        plimits[ch_name] = p99

        print(
            f"    P99({ch_name}) = {p99:.6f} "
            f"(from {len(vals)} stable obs)"
        )

    stable_frame = aligned.loc[stable_mask]

    correlations = stable_frame.corr()

    r_rp = float(
        correlations.loc["rho", "psi"]
    )
    r_ro = float(
        correlations.loc["rho", "omega"]
    )
    r_po = float(
        correlations.loc["psi", "omega"]
    )

    corr_values = np.array(
        [r_rp, r_ro, r_po],
        dtype=float,
    )

    if not np.isfinite(corr_values).all():
        raise ValueError(
            f"{case_def['name']}: "
            "stable-window correlation is undefined."
        )

    max_r = float(
        np.max(np.abs(corr_values))
    )

    print(
        "    Stable-window correlations: "
        f"r(rho,psi)={r_rp:.3f}, "
        f"r(rho,omega)={r_ro:.3f}, "
        f"r(psi,omega)={r_po:.3f}"
    )
    print(
        f"    max|r| = {max_r:.3f} "
        "(descriptive; no pass/fail threshold)"
    )

    # No post-normalization clipping or epsilon denominator.
    norm = {
        ch_name: channels[ch_name] / plimits[ch_name]
        for ch_name in ["rho", "psi", "omega"]
    }

    normalized = pd.DataFrame({
        "rho_norm": norm["rho"],
        "psi_norm": norm["psi"],
        "omega_norm": norm["omega"],
    })

    norm_values = normalized.to_numpy(dtype=float)

    if not np.isfinite(norm_values).all():
        raise ValueError(
            f"{case_def['name']}: "
            "normalized channels contain non-finite values."
        )

    if (norm_values < 0).any():
        raise ValueError(
            f"{case_def['name']}: "
            "normalized channels contain negative values."
        )

    stress = (
        norm["rho"]
        * norm["psi"]
        * norm["omega"]
    )

    stress_values = stress.to_numpy(dtype=float)

    if not np.isfinite(stress_values).all():
        raise ValueError(
            f"{case_def['name']}: stress is non-finite."
        )

    if (stress_values < 0).any():
        raise ValueError(
            f"{case_def['name']}: stress is negative."
        )

    legacy_weight = float(
        case_def["legacy_observation_weight"]
    )

    if not np.isfinite(legacy_weight) or legacy_weight <= 0:
        raise ValueError(
            f"{case_def['name']}: invalid legacy observation weight."
        )

    pi = (
        stress * legacy_weight
    ).cumsum()

    df_full = pd.DataFrame({
        "rho": channels["rho"],
        "psi": channels["psi"],
        "omega": channels["omega"],
        "rho_norm": norm["rho"],
        "psi_norm": norm["psi"],
        "omega_norm": norm["omega"],
        "stress": stress,
        "pi": pi,
    })

    crisis_mask = (
        (common_idx >= pd.Timestamp(case_def["crisis_start"]))
        & (common_idx <= pd.Timestamp(case_def["crisis_end"]))
    )

    control_mask = (
        (common_idx >= pd.Timestamp(case_def["control_start"]))
        & (common_idx <= pd.Timestamp(case_def["control_end"]))
    )

    crisis_df = df_full.loc[
        crisis_mask
    ].copy()

    control_df = df_full.loc[
        control_mask
    ].copy()

    if crisis_df.empty:
        raise ValueError(
            f"{case_def['name']}: crisis window is empty."
        )

    if control_df.empty:
        raise ValueError(
            f"{case_def['name']}: control window is empty."
        )

    crisis_df["pi"] = (
        crisis_df["stress"] * legacy_weight
    ).cumsum()

    control_df["pi"] = (
        control_df["stress"] * legacy_weight
    ).cumsum()

    pi_crisis = float(
        crisis_df["pi"].iloc[-1]
    )

    pi_control = float(
        control_df["pi"].iloc[-1]
    )

    sep = positive_finite_ratio(
        pi_crisis,
        pi_control,
        f"{case_def['name']} legacy cumulative separation",
    )

    print(
        f'\n    Crisis: '
        f'{crisis_df.index[0].date()} to '
        f'{crisis_df.index[-1].date()}, '
        f'N={len(crisis_df)}'
    )

    print(
        f'    Control: '
        f'{control_df.index[0].date()} to '
        f'{control_df.index[-1].date()}, '
        f'N={len(control_df)}'
    )

    print(
        f"    Pi_crisis = {pi_crisis:.6f}"
    )
    print(
        f"    Pi_control = {pi_control:.6f}"
    )
    print(
        f"    Separation = {sep:.1f}x"
    )

    legacy_weight_total_crisis = (
        len(crisis_df) * legacy_weight
    )

    legacy_weight_total_control = (
        len(control_df) * legacy_weight
    )

    mean_stress_crisis = float(
        crisis_df["stress"].mean()
    )

    mean_stress_control = float(
        control_df["stress"].mean()
    )

    mean_stress_ratio = positive_finite_ratio(
        mean_stress_crisis,
        mean_stress_control,
        f"{case_def['name']} mean-stress separation",
    )

    print(
        f"    Running permutation test "
        f"({N_PERMUTATIONS:,} shuffles, "
        f"seed={PERMUTATION_SEED})..."
    )

    crisis_values = crisis_df[
        ["rho_norm", "psi_norm", "omega_norm"]
    ].to_numpy(
        dtype=float
    )

    n_obs = len(crisis_values)

    if n_obs < 2:
        raise ValueError(
            f"{case_def['name']}: "
            "permutation requires at least 2 observations."
        )

    # Preserve the historical per-case deterministic stream.
    rng = np.random.default_rng(
        PERMUTATION_SEED
    )

    perm_pis = np.empty(
        N_PERMUTATIONS,
        dtype=float,
    )

    for i in range(N_PERMUTATIONS):
        idx_r = rng.permutation(n_obs)
        idx_p = rng.permutation(n_obs)
        idx_o = rng.permutation(n_obs)

        shuffled_stress = (
            crisis_values[idx_r, 0]
            * crisis_values[idx_p, 1]
            * crisis_values[idx_o, 2]
        )

        perm_pis[i] = (
            shuffled_stress.sum()
            * legacy_weight
        )

    if not np.isfinite(perm_pis).all():
        raise ValueError(
            f"{case_def['name']}: "
            "permutation null contains non-finite values."
        )

    null_mean = float(
        perm_pis.mean()
    )

    null_std = float(
        perm_pis.std()
    )

    if not np.isfinite(null_std) or null_std <= 0:
        raise ValueError(
            f"{case_def['name']}: "
            "permutation null standard deviation "
            "must be positive and finite."
        )

    exceedances = int(
        np.count_nonzero(
            perm_pis >= pi_crisis
        )
    )

    p_value = (
        exceedances + 1
    ) / (
        N_PERMUTATIONS + 1
    )

    z_score = (
        pi_crisis - null_mean
    ) / null_std

    if not np.isfinite(z_score):
        raise ValueError(
            f"{case_def['name']}: non-finite z-score."
        )

    print(
        f"    null = {null_mean:.6f} ± {null_std:.6f}"
    )
    print(
        f"    exceedances = "
        f"{exceedances}/{N_PERMUTATIONS}, "
        f"z = {z_score:.2f}, "
        f"p_MC = {p_value:.6g}"
    )

    stress_max = float(
        crisis_df["stress"].max()
    )

    if not np.isfinite(stress_max):
        raise ValueError(
            f"{case_def['name']}: non-finite stress maximum."
        )

    return {
        "case_id": case_id,
        "name": case_def["name"],
        "domain": case_def["domain"],
        "freq": case_def["freq"],
        "n_crisis": len(crisis_df),
        "n_control": len(control_df),
        "pi_crisis": pi_crisis,
        "pi_control": pi_control,
        "separation": sep,
        "stress_max": stress_max,
        "legacy_weight_total_crisis": legacy_weight_total_crisis,
        "legacy_weight_total_control": legacy_weight_total_control,
        "mean_stress_crisis": mean_stress_crisis,
        "mean_stress_control": mean_stress_control,
        "mean_stress_ratio": mean_stress_ratio,
        "z_score": z_score,
        "p_value": p_value,
        "permutation_mean": null_mean,
        "permutation_std": null_std,
        "exceedances": exceedances,
        "n_permutations": N_PERMUTATIONS,
        "seed": PERMUTATION_SEED,
        "r_rp": r_rp,
        "r_ro": r_ro,
        "r_po": r_po,
        "max_r": max_r,
        "_crisis_df": crisis_df,
        "_control_df": control_df,
    }

def main():
    print()
    print("=" * 70)
    print(
        "  Pi FRAMEWORK - "
        "EXPLORATORY ADDITIONAL COMPARISON CASES"
    )
    print(
        "  Boundary comparisons; not validation episodes"
    )
    print("=" * 70)

    if not FRED_API_KEY:
        raise RuntimeError(
            "FRED_API_KEY is required."
        )

    if not FRED_VINTAGE_DATE:
        raise RuntimeError(
            "FRED_VINTAGE_DATE is required."
        )

    print(
        f"  FRED vintage: {FRED_VINTAGE_DATE}"
    )

    # Fail closed: every configured case must complete.
    results = [
        process_case(case_id, case_def)
        for case_id, case_def in CASES.items()
    ]

    if len(results) != len(CASES):
        raise RuntimeError(
            f"Expected {len(CASES)} completed cases, "
            f"got {len(results)}."
        )

    # Promote generated case CSVs only after every case succeeded.
    for result in results:
        result["_crisis_df"].to_csv(
            os.path.join(
                DATA_DIR,
                f'crisis_{result["case_id"]}_pi.csv',
            )
        )

        result["_control_df"].to_csv(
            os.path.join(
                DATA_DIR,
                f'control_{result["case_id"]}_pi.csv',
            )
        )

    cross = pd.DataFrame([
        {
            "name": r["name"],
            "domain": r["domain"],
            "pi_crisis": round(r["pi_crisis"], 6),
            "pi_control": round(r["pi_control"], 6),
            "separation": round(r["separation"], 1),
            "stress_max": round(r["stress_max"], 4),
            "n_crisis": r["n_crisis"],
            "n_control": r["n_control"],
        }
        for r in results
    ])

    cross.to_csv(
        os.path.join(
            OUT_DIR,
            "table_additional_cases.csv",
        ),
        index=False,
    )

    perm = pd.DataFrame([
        {
            "Case": r["name"],
            "N": r["n_crisis"],
            "Pi_actual": round(r["pi_crisis"], 6),
            "Pi_shuffled_mean": round(
                r["permutation_mean"],
                6,
            ),
            "Pi_shuffled_std": round(
                r["permutation_std"],
                6,
            ),
            "z_score": round(r["z_score"], 2),
            "Monte_Carlo_p": r["p_value"],
            "Exceedances": r["exceedances"],
            "B": r["n_permutations"],
            "Seed": r["seed"],
            "Significant": (
                "Yes"
                if r["p_value"] < 0.05
                else "No"
            ),
        }
        for r in results
    ])

    perm.to_csv(
        os.path.join(
            OUT_DIR,
            "table_additional_permutation.csv",
        ),
        index=False,
    )

    tn = pd.DataFrame([
        {
            "Case": r["name"],
            "Frequency": r["freq"],
            "N_crisis": r["n_crisis"],
            "N_control": r["n_control"],
            "Legacy_observation_weight": (
                CASES[r["case_id"]][
                    "legacy_observation_weight"
                ]
            ),
            "Legacy_weight_total_crisis": round(
                r["legacy_weight_total_crisis"],
                10,
            ),
            "Legacy_weight_total_control": round(
                r["legacy_weight_total_control"],
                10,
            ),
            "Legacy_cumulative_ratio": round(
                r["separation"],
                10,
            ),
            "Exploratory_mean_stress_ratio": round(
                r["mean_stress_ratio"],
                10,
            ),
            "Interpretive_status": (
                "Exploratory boundary comparison; "
                "legacy cumulative values use fixed "
                "per-observation weights"
            ),
        }
        for r in results
    ])

    tn.to_csv(
        os.path.join(
            OUT_DIR,
            "table_additional_time_normalized.csv",
        ),
        index=False,
    )

    nr = pd.DataFrame([
        {
            "Case": r["name"],
            "Correlation_window": (
                "Stable calibration period"
            ),
            "r(rho,psi)": round(r["r_rp"], 3),
            "r(rho,omega)": round(r["r_ro"], 3),
            "r(psi,omega)": round(r["r_po"], 3),
            "max|r|": round(r["max_r"], 3),
            "Interpretive_status": (
                "Descriptive pairwise linear correlation; "
                "no pass/fail threshold"
            ),
        }
        for r in results
    ])

    nr.to_csv(
        os.path.join(
            OUT_DIR,
            "table_additional_nonredundancy.csv",
        ),
        index=False,
    )

    print(f'\n  {"=" * 78}')
    print("  SUMMARY")
    print(f'  {"=" * 78}')

    for r in results:
        print(
            f'  {r["name"]:<30} '
            f'legacy={r["separation"]:.1f}x  '
            f'mean={r["mean_stress_ratio"]:.1f}x  '
            f'z={r["z_score"]:.2f}  '
            f'p_MC={r["p_value"]:.6g}  '
            f'max|r|={r["max_r"]:.3f}'
        )

    print(
        "\n  Saved: table_additional_cases.csv, "
        "table_additional_permutation.csv"
    )
    print(
        "         table_additional_time_normalized.csv, "
        "table_additional_nonredundancy.csv"
    )
    print(
        "         + crisis/control CSVs in data/"
    )
    print()

if __name__ == '__main__':
    main()
