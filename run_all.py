"""
Pi Structural Stability Index - Legacy Audit Generator
=================================================
5-case cross-case retrospective characterization + statistical tests
+ legacy audit diagnostics + historical audit figures

All analyses run from pre-computed CSV data in data/ folder.
No API keys needed for core analyses.
Legacy SVB transferability-feasibility audit requires FRED_API_KEY.

Usage:
  python run_all.py              # Legacy original-window and audit analyses
  python run_all.py --svb        # Include legacy SVB feasibility audit (not revised evidence)
  python run_all.py --st15       # Run legacy ST15 live-FRED reconstruction (not revised evidence)
  python run_all.py --figures    # Generate historical audit figures (needs matplotlib)
  python run_all.py --all        # Legacy analyses, diagnostics, and audit figures
"""

import pandas as pd
import numpy as np
import os
import sys
import argparse
from scipy import stats as scipy_stats
import subprocess

# ================================================================
# CONFIG
# ================================================================

_base = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(_base, 'data')

OUT_DIR = os.path.join(_base, 'output')
FRED_VINTAGE_DATE = os.environ.get("FRED_VINTAGE_DATE", "")

CASES = {
    '2008 Financial': {
        'crisis': 'crisis_2008_pi.csv',
        'control': 'control_2004_2006_pi.csv',
        'domain': 'Traditional Finance',
        'variables': 'DFF / TEDRATE / TOTBKCR',
        'collapse': '2008-09-15',
    },
    'Terra-Luna': {
        'crisis': 'crisis_terra_luna_pi.csv',
        'control': 'control_terra_luna_pi.csv',
        'domain': 'Digital Assets',
        'variables': 'BTC |Δ5d| / LUNC |Δ1d| / BTC-ETH-LUNC Corr (60d)',
        'collapse': '2022-05-09',
    },
    'Fukushima': {
        'crisis': 'crisis_fukushima_pi.csv',
        'control': 'control_fukushima_pi.csv',
        'domain': 'Physical Infrastructure',
        'variables': 'Seismic Energy / Nikkei Vol (5d) / USD-JPY Change',
        'collapse': '2011-03-11',
    },
    'COVID-19': {
        'crisis': 'crisis_covid_pi.csv',
        'control': 'control_covid_pi.csv',
        'domain': 'Pandemic / Public Health',
        'variables': 'Cases (7d Avg) / VIX / HY Spread',
        'collapse': '2020-03-23',
    },
    'Supply Chain': {
        'crisis': 'crisis_supply_chain_pi.csv',
        'control': 'control_supply_chain_pi.csv',
        'domain': 'Global Logistics',
        'variables': 'PCEDG / Delivery Time / Freight PPI',
        'collapse': '2021-10-01',
    },
}

N_PERM = 10000
RNG_SEED = 42

DPY_BY_CASE = {
    "2008 Financial": 365,
    "Terra-Luna": 365,
    "Fukushima": 365,
    "COVID-19": 365,
    "Supply Chain": 12,
}

REQUIRED_ANALYSIS_COLUMNS = [
    "rho",
    "psi",
    "omega",
    "rho_norm",
    "psi_norm",
    "omega_norm",
    "stress",
    "pi",
]


# ================================================================
# UTILITIES
# ================================================================

def case_dt(name):
    if name not in DPY_BY_CASE:
        raise KeyError(
            f"No explicit observations-per-year specification for {name}."
        )

    dpy = float(DPY_BY_CASE[name])

    if not np.isfinite(dpy) or dpy <= 0:
        raise ValueError(
            f"{name}: DPY must be positive and finite."
        )

    return 1.0 / dpy


def positive_finite_ratio(numerator, denominator, label):
    numerator = float(numerator)
    denominator = float(denominator)

    if not np.isfinite(numerator):
        raise ValueError(
            f"{label}: numerator must be finite; got {numerator}."
        )

    if not np.isfinite(denominator) or denominator <= 0:
        raise ValueError(
            f"{label}: denominator must be positive and finite; "
            f"got {denominator}."
        )

    ratio = numerator / denominator

    if not np.isfinite(ratio):
        raise ValueError(
            f"{label}: ratio must be finite; got {ratio}."
        )

    return ratio


def validate_case_frame(name, role, df):
    if df.empty:
        raise ValueError(
            f"{name}/{role}: frozen analysis file is empty."
        )

    if df.index.has_duplicates:
        raise ValueError(
            f"{name}/{role}: duplicate dates detected."
        )

    if not df.index.is_monotonic_increasing:
        raise ValueError(
            f"{name}/{role}: dates are not chronological."
        )

    missing = [
        col
        for col in REQUIRED_ANALYSIS_COLUMNS
        if col not in df.columns
    ]

    if missing:
        raise ValueError(
            f"{name}/{role}: missing required columns: {missing}"
        )

    numeric = df[
        REQUIRED_ANALYSIS_COLUMNS
    ].apply(
        pd.to_numeric,
        errors="coerce",
    )

    values = numeric.to_numpy(dtype=float)

    if not np.isfinite(values).all():
        raise ValueError(
            f"{name}/{role}: non-finite analysis values detected."
        )

    if (values < 0).any():
        raise ValueError(
            f"{name}/{role}: negative values detected in "
            "non-negative analytical channels."
        )

    expected_stress = (
        numeric["rho_norm"]
        * numeric["psi_norm"]
        * numeric["omega_norm"]
    )

    if not np.allclose(
        numeric["stress"].to_numpy(dtype=float),
        expected_stress.to_numpy(dtype=float),
        rtol=1e-12,
        atol=1e-12,
    ):
        max_diff = float(
            np.max(
                np.abs(
                    numeric["stress"].to_numpy(dtype=float)
                    - expected_stress.to_numpy(dtype=float)
                )
            )
        )
        raise ValueError(
            f"{name}/{role}: stored stress does not reproduce "
            f"rho_norm*psi_norm*omega_norm; max_abs_diff={max_diff}"
        )

    clean = df.copy()

    for col in REQUIRED_ANALYSIS_COLUMNS:
        clean[col] = numeric[col]

    # Historical frozen CSVs may contain case-generator-specific Pi
    # conventions. run_all.py has always reconstructed Pi from stress.
    # Preserve that behavior, but make the cadence explicit by case.
    dt = case_dt(name)
    clean["pi"] = (
        clean["stress"] * dt
    ).cumsum()

    if not np.isfinite(
        clean["pi"].to_numpy(dtype=float)
    ).all():
        raise ValueError(
            f"{name}/{role}: reconstructed Pi is non-finite."
        )

    if (
        clean["pi"].to_numpy(dtype=float)
        < 0
    ).any():
        raise ValueError(
            f"{name}/{role}: reconstructed Pi is negative."
        )

    return clean


def load_case(name):
    info = CASES[name]

    crisis_path = os.path.join(
        DATA_DIR,
        info["crisis"],
    )
    control_path = os.path.join(
        DATA_DIR,
        info["control"],
    )

    if not os.path.isfile(crisis_path):
        raise FileNotFoundError(crisis_path)

    if not os.path.isfile(control_path):
        raise FileNotFoundError(control_path)

    crisis = pd.read_csv(
        crisis_path,
        index_col=0,
        parse_dates=True,
    )

    control = pd.read_csv(
        control_path,
        index_col=0,
        parse_dates=True,
    )

    crisis = validate_case_frame(
        name,
        "crisis",
        crisis,
    )

    control = validate_case_frame(
        name,
        "control",
        control,
    )

    return crisis, control


# ================================================================
# ANALYSIS 1: CROSS-CASE RETROSPECTIVE CHARACTERIZATION
# ================================================================

def run_cross_domain():
    print("=" * 75)
    print(
        "  ANALYSIS 1: Cross-Case Retrospective Characterization "
        "(5 Cases)"
    )
    print("=" * 75)

    results = []

    for name, info in CASES.items():
        cr, ct = load_case(name)
        dt = case_dt(name)

        pi_cr = float(
            (cr["stress"] * dt).sum()
        )
        pi_ct = float(
            (ct["stress"] * dt).sum()
        )

        sep = positive_finite_ratio(
            pi_cr,
            pi_ct,
            f"{name} cumulative crisis/control separation",
        )

        s_max = float(
            cr["stress"].max()
        )

        if not np.isfinite(s_max):
            raise ValueError(
                f"{name}: stress maximum is non-finite."
            )

        results.append({
            "name": name,
            "domain": info["domain"],
            "pi_crisis": pi_cr,
            "pi_control": pi_ct,
            "separation": sep,
            "stress_max": s_max,
            "n_crisis": len(cr),
            "n_control": len(ct),
        })

    print(
        f'\n  {"Case":<18} {"Domain":<22} '
        f'{"Π_crisis":<12} {"Π_control":<12} '
        f'{"Ratio":<10} {"Relation":<18}'
    )
    print(f'  {"-" * 90}')

    for r in results:
        relation = (
            "crisis > control"
            if r["separation"] > 1.0
            else "crisis ≤ control"
        )

        print(
            f'  {r["name"]:<18} '
            f'{r["domain"]:<22} '
            f'{r["pi_crisis"]:<12.4f} '
            f'{r["pi_control"]:<12.4f} '
            f'{r["separation"]:<10.1f}x '
            f'{relation:<18}'
        )

    above_one_count = sum(
        1
        for r in results
        if r["separation"] > 1.0
    )

    print(
        "\n  Original-window cumulative ratios above 1.0: "
        f"{above_one_count}/5 selected cases"
    )
    print(
        "  Descriptive legacy contrast; overlap and "
        "unequal-duration caveats apply."
    )

    return results

# ================================================================
# ANALYSIS 2: MULTIPLICATIVE vs ADDITIVE vs MAX
# ================================================================

def run_mult_vs_add():
    print(f'\n\n{"=" * 75}')
    print(
        "  ANALYSIS 2: Multiplicative vs Additive vs Max"
    )
    print(
        "  S = ρ×Ψ×Ω  vs  S = ρ+Ψ+Ω  "
        "vs  S = max(ρ,Ψ,Ω)"
    )
    print("=" * 75)

    results = []

    for name in CASES:
        cr, ct = load_case(name)
        dt = case_dt(name)

        def calc_pi(df, mode):
            r = df["rho_norm"]
            p = df["psi_norm"]
            o = df["omega_norm"]

            if mode == "mult":
                stress = r * p * o
            elif mode == "add":
                stress = r + p + o
            elif mode == "max":
                stress = df[
                    [
                        "rho_norm",
                        "psi_norm",
                        "omega_norm",
                    ]
                ].max(axis=1)
            else:
                raise ValueError(
                    f"Unknown formulation: {mode}"
                )

            value = float(
                (stress * dt).sum()
            )

            if not np.isfinite(value) or value < 0:
                raise ValueError(
                    f"{name}/{mode}: integrated stress "
                    "must be finite and non-negative."
                )

            return value

        res = {
            "name": name,
        }

        for mode in [
            "mult",
            "add",
            "max",
        ]:
            pi_cr = calc_pi(
                cr,
                mode,
            )
            pi_ct = calc_pi(
                ct,
                mode,
            )

            sep = positive_finite_ratio(
                pi_cr,
                pi_ct,
                f"{name}/{mode} crisis/control separation",
            )

            res[mode] = {
                "crisis": pi_cr,
                "control": pi_ct,
                "sep": sep,
            }

        results.append(
            res
        )

    print(
        f'\n  {"Case":<18} {"Multiply":<14} '
        f'{"Additive":<14} {"Max":<14} {"Highest":<12}'
    )
    print(f'  {"-" * 70}')

    mult_wins = 0

    for r in results:
        seps = {
            "Multiply": r["mult"]["sep"],
            "Additive": r["add"]["sep"],
            "Max": r["max"]["sep"],
        }

        winner = max(
            seps,
            key=seps.get,
        )

        if winner == "Multiply":
            mult_wins += 1

        print(
            f'  {r["name"]:<18} '
            f'{r["mult"]["sep"]:<14.1f}x '
            f'{r["add"]["sep"]:<14.1f}x '
            f'{r["max"]["sep"]:<14.1f}x '
            f'{winner}'
        )

    print(
        "\n  Multiplicative highest separation: "
        f"{mult_wins}/{len(results)} selected cases"
    )

    return results

# ================================================================
# ANALYSIS 3: PERMUTATION TEST
# ================================================================

def run_permutation_test():
    print(f'\n\n{"=" * 75}')
    print(
        f"  ANALYSIS 3: Permutation Test "
        f"(B = {N_PERM:,}, seed = {RNG_SEED})"
    )
    print(
        "  Null diagnostic: independent random re-alignment "
        "of observed channel values"
    )
    print("=" * 75)

    results = {}

    for case_index, name in enumerate(CASES):
        cr, _ = load_case(name)
        dt = case_dt(name)

        rho = cr["rho_norm"].to_numpy(dtype=float)
        psi = cr["psi_norm"].to_numpy(dtype=float)
        omega = cr["omega_norm"].to_numpy(dtype=float)

        n = len(rho)

        if n < 2:
            raise ValueError(
                f"{name}: permutation test requires at least "
                "2 observations."
            )

        actual_pi = float(
            np.sum(rho * psi * omega) * dt
        )

        if not np.isfinite(actual_pi):
            raise ValueError(
                f"{name}: actual permutation statistic "
                "must be finite."
            )

        # Each case gets a reproducible independent RNG stream.
        seed_sequence = np.random.SeedSequence(
            [RNG_SEED, case_index]
        )
        rng = np.random.default_rng(
            seed_sequence
        )

        shuffled_pis = np.empty(
            N_PERM,
            dtype=float,
        )

        for i in range(N_PERM):
            r_s = rng.permutation(rho)
            p_s = rng.permutation(psi)
            o_s = rng.permutation(omega)

            shuffled_pis[i] = (
                np.sum(r_s * p_s * o_s)
                * dt
            )

        if not np.isfinite(shuffled_pis).all():
            raise ValueError(
                f"{name}: permutation null contains "
                "non-finite values."
            )

        exceedances = int(
            np.count_nonzero(
                shuffled_pis >= actual_pi
            )
        )

        # Finite Monte Carlo p-value.
        # This avoids reporting an impossible estimated p=0.
        p_value = (
            exceedances + 1
        ) / (
            N_PERM + 1
        )

        null_mean = float(
            shuffled_pis.mean()
        )
        null_std = float(
            shuffled_pis.std()
        )

        if not np.isfinite(null_std) or null_std <= 0:
            raise ValueError(
                f"{name}: permutation null standard deviation "
                f"must be positive and finite; got {null_std}."
            )

        z_score = (
            actual_pi - null_mean
        ) / null_std

        if not np.isfinite(z_score):
            raise ValueError(
                f"{name}: permutation z-score must be finite."
            )

        results[name] = {
            "actual_pi": actual_pi,
            "mean_shuffled": null_mean,
            "std_shuffled": null_std,
            "p_value": p_value,
            "z_score": z_score,
            "n": n,
            "B": N_PERM,
            "seed": RNG_SEED,
            "case_seed_index": case_index,
            "exceedances": exceedances,
            "null_distribution": shuffled_pis,
        }

        sig = (
            "***" if p_value < 0.001
            else "**" if p_value < 0.01
            else "*" if p_value < 0.05
            else "n.s."
        )

        print(f"\n  {name} (n={n}):")
        print(
            f"    Actual Π = {actual_pi:.6f}, "
            f"Shuffled = {null_mean:.6f} ± {null_std:.6f}"
        )
        print(
            f"    exceedances = {exceedances}/{N_PERM}, "
            f"p_MC = {p_value:.6g}, "
            f"z = {z_score:.2f} {sig}"
        )

    print(f'\n  {"─" * 78}')
    print(
        f'  {"Case":<18} {"N":<8} '
        f'{"b/B":<14} {"z-score":<10} '
        f'{"p_MC":<12} {"Sig":<6}'
    )
    print(f'  {"─" * 78}')

    for name, r in results.items():
        sig = (
            "***" if r["p_value"] < 0.001
            else "**" if r["p_value"] < 0.01
            else "*" if r["p_value"] < 0.05
            else "n.s."
        )

        print(
            f'  {name:<18} '
            f'{r["n"]:<8} '
            f'{r["exceedances"]}/{r["B"]:<8} '
            f'{r["z_score"]:<10.2f} '
            f'{r["p_value"]:<12.6g} '
            f'{sig}'
        )

    n_tests = len(results)

    print(
        f"\n  Bonferroni correction "
        f"(n={n_tests}):"
    )

    for name, r in results.items():
        p_corr = min(
            r["p_value"] * n_tests,
            1.0,
        )

        sig = (
            "***" if p_corr < 0.001
            else "**" if p_corr < 0.01
            else "*" if p_corr < 0.05
            else "n.s."
        )

        print(
            f"    {name:<18}: "
            f"p_corrected = {p_corr:.6g} {sig}"
        )

    # Historical audit continuity only; not revised evidence.
    p_values = [
        r["p_value"]
        for r in results.values()
    ]

    chi2_stat = -2.0 * sum(
        np.log(p)
        for p in p_values
    )

    fisher_p = float(
        scipy_stats.chi2.sf(
            chi2_stat,
            df=2 * len(p_values),
        )
    )

    if not np.isfinite(fisher_p):
        raise ValueError(
            "Legacy Fisher combined p-value is non-finite."
        )

    print(
        "\n  Legacy Fisher combination "
        f"(audit only; not revised evidence): "
        f"{fisher_p:.2e}"
    )

    return results

# ================================================================
# LEGACY AUDIT: RETROSPECTIVE PATTERN LABELS
# ================================================================

def run_failure_modes():
    print(f'\n\n{"=" * 75}')
    print('  LEGACY AUDIT: Retrospective Pattern Labels')
    print('=' * 75)

    results = []

    for name, info in CASES.items():
        cr, _ = load_case(name)

        pi_max = cr['pi'].iloc[-1]
        collapse_date = pd.Timestamp(info['collapse'])

        nearest_idx = cr.index.get_indexer([collapse_date], method='nearest')[0]
        pi_at_collapse = cr['pi'].iloc[nearest_idx]
        pct_of_max = (pi_at_collapse / pi_max * 100) if pi_max > 0 else 0

        threshold = pi_max * 0.10
        crossed = cr[cr['pi'] >= threshold].index
        if len(crossed) > 0:
            first_cross = crossed[0]
            lead_days = (collapse_date - first_cross).days
        else:
            lead_days = 0

        # Retrospective labels retained for audit reproducibility; not validated failure laws, warning classes, or revised evidence.
        if pct_of_max > 80:
            mode = 'Pre-loaded'
            analogy = 'Creep rupture'
        elif lead_days > 300:
            mode = 'Ductile'
            analogy = 'Metal fatigue'
        else:
            mode = 'Brittle'
            analogy = 'Glass fracture'

        results.append({
            'name': name, 'pi_at_collapse': pi_at_collapse,
            'pct_of_max': pct_of_max, 'lead_days': lead_days,
            'mode': mode, 'analogy': analogy,
        })

    print(f'\n  {"Case":<18} {"Π@collapse":<12} {"% of max":<10} {"Lead(days)":<12} {"Mode":<14} {"Analogy":<16}')
    print(f'  {"-" * 82}')

    for r in results:
        print(f'  {r["name"]:<18} {r["pi_at_collapse"]:<12.3f} {r["pct_of_max"]:<10.1f}% {r["lead_days"]:<12d} {r["mode"]:<14} {r["analogy"]:<16}')

    return results


# ================================================================
# ANALYSIS 5: LEGACY SVB FEASIBILITY AUDIT (optional, needs FRED API)
# ================================================================

def run_svb_oos():
    print(f'\n\n{"=" * 75}')
    print(
        "  ANALYSIS 5: Legacy SVB "
        "Transferability-Feasibility Audit"
    )
    print(
        "  Variables: SAME as 2008 | "
        "P-limits: SAME as 2008 | NO re-tuning"
    )
    print("=" * 75)

    fred_api_key = os.environ.get(
        "FRED_API_KEY",
        "",
    )

    if not fred_api_key:
        raise RuntimeError(
            "Legacy SVB audit was explicitly requested, "
            "but FRED_API_KEY is not set."
        )

    if not FRED_VINTAGE_DATE:
        raise RuntimeError(
            "Legacy SVB audit was explicitly requested, "
            "but FRED_VINTAGE_DATE is not set."
        )

    import requests

    cr_2008, _ = load_case(
        "2008 Financial"
    )

    stable = cr_2008.loc[
        :"2007-06-30"
    ].copy()

    if stable.empty:
        raise ValueError(
            "2008 stable calibration window is empty."
        )

    def extract_plimit(col_raw, col_norm):
        mask = (
            (stable[col_raw] > 0)
            & (stable[col_norm] > 0.01)
        )

        if not mask.any():
            raise ValueError(
                f"Cannot recover frozen P-limit for "
                f"{col_raw}/{col_norm}: no valid observations."
            )

        ratios = (
            stable.loc[mask, col_raw]
            / stable.loc[mask, col_norm]
        ).to_numpy(
            dtype=float
        )

        if not np.isfinite(ratios).all():
            raise ValueError(
                f"Recovered P-limit ratios for {col_raw} "
                "contain non-finite values."
            )

        if (ratios <= 0).any():
            raise ValueError(
                f"Recovered P-limit ratios for {col_raw} "
                "must be positive."
            )

        value = float(
            np.median(ratios)
        )

        if not np.isfinite(value) or value <= 0:
            raise ValueError(
                f"Recovered P-limit for {col_raw} "
                "must be positive and finite."
            )

        return value

    p_rho = extract_plimit(
        "rho",
        "rho_norm",
    )
    p_psi = extract_plimit(
        "psi",
        "psi_norm",
    )
    p_omega = extract_plimit(
        "omega",
        "omega_norm",
    )

    print(
        "\n  2008 P-limits "
        "(recovered from frozen calibration channels):"
    )
    print(
        f"    P_rho = {p_rho:.4f}, "
        f"P_psi = {p_psi:.4f}, "
        f"P_omega = {p_omega:.4f}"
    )
    print(
        f"  FRED vintage: {FRED_VINTAGE_DATE}"
    )

    def fetch_fred(series_id, start, end):
        url = (
            "https://api.stlouisfed.org/"
            "fred/series/observations"
        )

        params = {
            "series_id": series_id,
            "api_key": fred_api_key,
            "file_type": "json",
            "observation_start": start,
            "observation_end": end,
            "realtime_start": FRED_VINTAGE_DATE,
            "realtime_end": FRED_VINTAGE_DATE,
        }

        response = requests.get(
            url,
            params=params,
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
                f"{series_id}: FRED returned no observations "
                f"for vintage {FRED_VINTAGE_DATE}."
            )

        frame = pd.DataFrame(
            observations
        )

        required = {
            "date",
            "value",
        }

        if not required.issubset(
            frame.columns
        ):
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
                f"{series_id}: invalid FRED dates."
            )

        raw_values = (
            frame["value"]
            .astype(str)
            .str.strip()
        )

        missing_sentinel = (
            raw_values == "."
        )

        values = pd.to_numeric(
            raw_values.where(
                ~missing_sentinel,
                np.nan,
            ),
            errors="coerce",
        )

        invalid_numeric = (
            values.isna()
            & ~missing_sentinel
        )

        if invalid_numeric.any():
            raise ValueError(
                f"{series_id}: malformed numeric FRED values."
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
                f"{series_id}: duplicate FRED dates."
            )

        series = series.sort_index()

        if not np.isfinite(
            series.to_numpy(dtype=float)
        ).all():
            raise ValueError(
                f"{series_id}: non-finite FRED observations."
            )

        # A series that ends far before the requested end date
        # cannot support the stated SVB-era audit.
        latest_allowed_gap = pd.Timedelta(
            days=45
        )

        if (
            pd.Timestamp(end)
            - series.index.max()
            > latest_allowed_gap
        ):
            raise ValueError(
                f"{series_id}: latest observation "
                f"{series.index.max().date()} does not cover "
                f"the requested window through {end}."
            )

        return series

    print(
        "\n  Fetching SVB-era data from FRED..."
    )

    dff = fetch_fred(
        "DFF",
        "2022-01-01",
        "2023-06-30",
    )
    ted = fetch_fred(
        "TEDRATE",
        "2022-01-01",
        "2023-06-30",
    )
    bkcr = fetch_fred(
        "TOTBKCR",
        "2022-01-01",
        "2023-06-30",
    )

    print(
        f"    DFF:  {len(dff)} pts"
    )
    print(
        f"    TED:  {len(ted)} pts"
    )
    print(
        f"    BKCR: {len(bkcr)} pts"
    )

    omega_full = (
        bkcr
        .pct_change(
            fill_method=None
        )
        .abs()
        .dropna()
    )

    common = (
        dff.index
        .intersection(ted.index)
        .intersection(omega_full.index)
        .sort_values()
    )

    if common.empty:
        raise ValueError(
            "SVB audit has no exact common dates across "
            "DFF, TEDRATE, and transformed TOTBKCR."
        )

    rho = dff.reindex(
        common
    )
    psi = ted.reindex(
        common
    )
    omega = omega_full.reindex(
        common
    )

    raw = pd.DataFrame({
        "rho": rho,
        "psi": psi,
        "omega": omega,
    })

    raw_values = raw.to_numpy(
        dtype=float
    )

    if not np.isfinite(
        raw_values
    ).all():
        raise ValueError(
            "SVB aligned channels contain non-finite values."
        )

    if (raw_values < 0).any():
        raise ValueError(
            "SVB transformed channels must be non-negative."
        )

    rho_n = rho / p_rho
    psi_n = psi / p_psi
    omega_n = omega / p_omega

    normalized = pd.DataFrame({
        "rho_norm": rho_n,
        "psi_norm": psi_n,
        "omega_norm": omega_n,
    })

    normalized_values = normalized.to_numpy(
        dtype=float
    )

    if not np.isfinite(
        normalized_values
    ).all():
        raise ValueError(
            "SVB normalized channels contain non-finite values."
        )

    if (
        normalized_values < 0
    ).any():
        raise ValueError(
            "SVB normalized channels must be non-negative."
        )

    stress = (
        rho_n
        * psi_n
        * omega_n
    )

    if not np.isfinite(
        stress.to_numpy(dtype=float)
    ).all():
        raise ValueError(
            "SVB stress contains non-finite values."
        )

    dt = 1.0 / 365.0

    crisis_mask = (
        common >= pd.Timestamp(
            "2022-07-01"
        )
    )

    control_mask = (
        common < pd.Timestamp(
            "2022-07-01"
        )
    )

    if not crisis_mask.any():
        raise ValueError(
            "SVB audit has no crisis-window observations."
        )

    if not control_mask.any():
        raise ValueError(
            "SVB audit has no control-window observations."
        )

    pi_cr = float(
        (stress[crisis_mask] * dt).sum()
    )

    pi_ct = float(
        (stress[control_mask] * dt).sum()
    )

    sep = positive_finite_ratio(
        pi_cr,
        pi_ct,
        "SVB legacy crisis/control separation",
    )

    print("\n  Results:")
    print(
        f"    Π (crisis,  2022-07 ~ 2023-06): "
        f"{pi_cr:.6f}"
    )
    print(
        f"    Π (control, 2022-01 ~ 2022-06): "
        f"{pi_ct:.6f}"
    )
    print(
        f"    Separation ratio: {sep:.1f}x"
    )
    print(
        "\n  This is a feasibility audit, "
        "not revised out-of-sample evidence."
    )

    return {
        "pi_cr": pi_cr,
        "pi_ct": pi_ct,
        "sep": sep,
    }

# ================================================================
# LEGACY AUDIT S1: P-LIMIT SCALE-INVARIANCE DIAGNOSTIC
# ================================================================

def run_plimit_sensitivity():
    print(f'\n\n{"=" * 75}')
    print(
        "  LEGACY AUDIT S1: "
        "P-limit Scale-Invariance Diagnostic"
    )
    print("=" * 75)
    print(
        "  Note: algebraic scale-invariance diagnostic, "
        "not independent empirical robustness evidence."
    )
    print(
        "  P-limits are estimated from the control window "
        "for this historical diagnostic."
    )
    print(
        "  Non-positive P-limits are reported as undefined; "
        "no epsilon denominator is substituted."
    )

    percentiles = [
        95,
        97.5,
        99,
        99.5,
    ]

    rows = []

    for case_name in CASES:
        cr, ct = load_case(case_name)
        dt = case_dt(case_name)

        for pct in percentiles:
            limits = {}

            for variable in [
                "rho",
                "psi",
                "omega",
            ]:
                values = ct[
                    variable
                ].to_numpy(
                    dtype=float
                )

                if len(values) == 0:
                    raise ValueError(
                        f"{case_name}/{variable}: "
                        "empty S1 control series."
                    )

                if not np.isfinite(values).all():
                    raise ValueError(
                        f"{case_name}/{variable}: "
                        "non-finite S1 control values."
                    )

                limit = float(
                    np.percentile(
                        values,
                        pct,
                    )
                )

                limits[variable] = limit

            invalid = {
                variable: limit
                for variable, limit in limits.items()
                if (
                    not np.isfinite(limit)
                    or limit <= 0
                )
            }

            if invalid:
                separation = np.nan

                detail = ", ".join(
                    f"{variable}={limit:.12g}"
                    for variable, limit in invalid.items()
                )

                status = (
                    "Undefined: non-positive or "
                    f"non-finite P-limit ({detail})"
                )

                print(
                    f"  {case_name} P{pct}: {status}"
                )

            else:
                stress_cr = (
                    (cr["rho"] / limits["rho"])
                    * (cr["psi"] / limits["psi"])
                    * (cr["omega"] / limits["omega"])
                )

                stress_ct = (
                    (ct["rho"] / limits["rho"])
                    * (ct["psi"] / limits["psi"])
                    * (ct["omega"] / limits["omega"])
                )

                crisis_values = stress_cr.to_numpy(
                    dtype=float
                )
                control_values = stress_ct.to_numpy(
                    dtype=float
                )

                if not np.isfinite(
                    crisis_values
                ).all():
                    raise ValueError(
                        f"{case_name} P{pct}: "
                        "non-finite crisis stress."
                    )

                if not np.isfinite(
                    control_values
                ).all():
                    raise ValueError(
                        f"{case_name} P{pct}: "
                        "non-finite control stress."
                    )

                if (
                    (crisis_values < 0).any()
                    or (control_values < 0).any()
                ):
                    raise ValueError(
                        f"{case_name} P{pct}: "
                        "negative S1 stress."
                    )

                pi_cr = float(
                    (stress_cr * dt).sum()
                )

                pi_ct = float(
                    (stress_ct * dt).sum()
                )

                separation = positive_finite_ratio(
                    pi_cr,
                    pi_ct,
                    f"{case_name} P{pct} "
                    "S1 crisis/control separation",
                )

                status = "Defined"

            rows.append({
                "Case": case_name,
                "Percentile": f"P{pct}",
                "P_rho": limits["rho"],
                "P_psi": limits["psi"],
                "P_omega": limits["omega"],
                "Separation": separation,
                "Status": status,
            })

    df = pd.DataFrame(rows)

    pivot = df.pivot(
        index="Case",
        columns="Percentile",
        values="Separation",
    )

    print()
    print(pivot.to_string())

    df.to_csv(
        os.path.join(
            OUT_DIR,
            "table_S1_plimit_sensitivity.csv",
        ),
        index=False,
    )

    print(
        "  Saved: table_S1_plimit_sensitivity.csv"
    )

    return df

# ================================================================
# LEGACY AUDIT S2: VARIABLE PERTURBATION (2008)
# ================================================================

def run_variable_perturbation():
    print(f'\n\n{"=" * 75}')
    print(
        "  LEGACY AUDIT S2: Variable Perturbation (2008)"
    )
    print("=" * 75)
    print(
        f"  Note: single-case Gaussian perturbation diagnostic; "
        f"seed={RNG_SEED}."
    )
    print(
        "  Perturbed normalized channels are truncated at zero "
        "to preserve their non-negative stress-domain definition."
    )
    print(
        "  Retained for audit reproducibility, "
        "not revised robustness evidence."
    )

    cr8, ct8 = load_case(
        "2008 Financial"
    )

    dt = case_dt(
        "2008 Financial"
    )

    base_cr = float(
        (cr8["stress"] * dt).sum()
    )

    base_ct = float(
        (ct8["stress"] * dt).sum()
    )

    base_sep = positive_finite_ratio(
        base_cr,
        base_ct,
        "2008 perturbation baseline separation",
    )

    rng = np.random.default_rng(
        RNG_SEED
    )

    rows = []

    labels = {
        "rho_norm": "ρ (Fed Funds Rate)",
        "psi_norm": "Ψ (TED Spread)",
        "omega_norm": "Ω (Bank Credit)",
    }

    for noise in [
        10,
        20,
        30,
        50,
    ]:
        for variable, label in labels.items():
            cp = cr8.copy()
            tp = ct8.copy()

            crisis_sd = float(
                cr8[variable].std()
            )

            control_sd = float(
                ct8[variable].std()
            )

            if (
                not np.isfinite(crisis_sd)
                or crisis_sd < 0
            ):
                raise ValueError(
                    f"{variable}: crisis standard deviation "
                    "must be finite and non-negative."
                )

            if (
                not np.isfinite(control_sd)
                or control_sd < 0
            ):
                raise ValueError(
                    f"{variable}: control standard deviation "
                    "must be finite and non-negative."
                )

            crisis_noise = rng.normal(
                0.0,
                crisis_sd * noise / 100.0,
                len(cr8),
            )

            control_noise = rng.normal(
                0.0,
                control_sd * noise / 100.0,
                len(ct8),
            )

            cp[variable] = (
                cp[variable]
                + crisis_noise
            ).clip(
                lower=0.0
            )

            tp[variable] = (
                tp[variable]
                + control_noise
            ).clip(
                lower=0.0
            )

            sc = float(
                (
                    cp["rho_norm"]
                    * cp["psi_norm"]
                    * cp["omega_norm"]
                    * dt
                ).sum()
            )

            st = float(
                (
                    tp["rho_norm"]
                    * tp["psi_norm"]
                    * tp["omega_norm"]
                    * dt
                ).sum()
            )

            sep = positive_finite_ratio(
                sc,
                st,
                f"2008 {noise}% {variable} perturbation separation",
            )

            pct_change = (
                sep / base_sep - 1.0
            ) * 100.0

            if not np.isfinite(pct_change):
                raise ValueError(
                    f"2008 {noise}% {variable}: "
                    "non-finite percent change."
                )

            rows.append({
                "Perturbed_Variable": label,
                "Noise_Level": f"{noise}%",
                "Separation": round(
                    sep,
                    1,
                ),
                "Pct_Change": f"{pct_change:+.1f}%",
                "Seed": RNG_SEED,
                "RNG": "numpy.default_rng",
                "Truncation": "lower=0",
            })

            print(
                f"  {noise}% noise on {label}: "
                f"{sep:.1f}× ({pct_change:+.1f}%)"
            )

    pd.DataFrame(
        rows
    ).to_csv(
        os.path.join(
            OUT_DIR,
            "table_S2_variable_robustness.csv",
        ),
        index=False,
    )

    print(
        "  Saved: table_S2_variable_robustness.csv"
    )

    return rows

# ================================================================
# SUPPLEMENTARY S4: CONTROL-WINDOW CORRELATION DIAGNOSTIC
# ================================================================

def run_control_window_correlations():
    print(f'\n\n{"=" * 75}')
    print(
        '  SUPPLEMENTARY S4: Control-Window Pairwise Linear '
        'Correlations'
    )
    print('=' * 75)

    rows = []
    for case_name in CASES:
        _, control = load_case(case_name)
        rp = control['rho_norm'].corr(control['psi_norm'])
        ro = control['rho_norm'].corr(control['omega_norm'])
        po = control['psi_norm'].corr(control['omega_norm'])
        mx = max(abs(rp), abs(ro), abs(po))

        rows.append({
            'Case': case_name,
            'Correlation_window': 'Full control window',
            'r(rho,psi)': round(rp, 3),
            'r(rho,omega)': round(ro, 3),
            'r(psi,omega)': round(po, 3),
            'max|r|': round(mx, 3),
            'Interpretive_status': (
                'Descriptive pairwise linear correlation; '
                'no pass/fail threshold'
            ),
        })

        print(
            f'  {case_name:<18} max|r| = {mx:.3f} '
            '(descriptive; no pass/fail threshold)'
        )

    pd.DataFrame(rows).to_csv(
        os.path.join(OUT_DIR, 'table_S4_nonredundancy.csv'),
        index=False,
    )
    print('  Saved: table_S4_nonredundancy.csv')
    return rows


# ================================================================
# PUBLICATION FIGURES (optional, needs matplotlib)
# ================================================================

def generate_figures(permutation_results):
    print(f'\n\n{"=" * 75}')
    print('  GENERATING PUBLICATION FIGURES (300 dpi)')
    print('=' * 75)

    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        import matplotlib.ticker as mticker
        import matplotlib.dates as mdates
    except ImportError as exc:
        raise RuntimeError(
            "Figures were explicitly requested but matplotlib "
            "could not be imported."
        ) from exc

    fig_dir = os.path.join(OUT_DIR, 'figures', 'legacy')
    os.makedirs(fig_dir, exist_ok=True)

    DPI = 300
    FS = 8
    PL = 12
    C = {'crisis': '#D32F2F', 'control': '#1976D2',
         'mult': '#D32F2F', 'add': '#FF9800', 'max': '#9E9E9E'}

    plt.rcParams.update({
        'font.family': 'sans-serif',
        'font.sans-serif': ['Arial', 'Helvetica', 'DejaVu Sans'],
        'font.size': FS, 'axes.labelsize': FS+1, 'axes.titlesize': FS+1,
        'xtick.labelsize': FS-1, 'ytick.labelsize': FS-1,
        'legend.fontsize': FS-1, 'figure.dpi': DPI, 'savefig.dpi': DPI,
        'savefig.bbox': 'tight', 'axes.spines.top': False,
        'axes.spines.right': False,
    })

    cases_list = list(CASES.keys())

    def cum_pi(df, dt_val):
        return (df['stress'] * dt_val).cumsum()

    # Load pre-built tables
    t1 = pd.read_csv(os.path.join(OUT_DIR, 'table1_cross_domain.csv'))
    t2 = pd.read_csv(os.path.join(OUT_DIR, 'table2_mult_vs_add.csv'))
    t4 = pd.read_csv(os.path.join(OUT_DIR, 'table4_failure_modes.csv'))

    # ── FIGURE 1: Π(t) time series ──
    print('  Figure 1: Π(t) time series...')
    fig, axes = plt.subplots(5, 1, figsize=(7.08, 10), constrained_layout=True)
    label_map = {'2008 Financial': '2008 Financial Crisis',
                 'Terra-Luna': 'Terra-Luna Collapse',
                 'Fukushima': 'Fukushima Disaster',
                 'COVID-19': 'COVID-19 Pandemic',
                 'Supply Chain': 'Supply Chain Disruption'}
    collapse_dates = {
        '2008 Financial': pd.Timestamp('2008-09-15'),
        'Terra-Luna': pd.Timestamp('2022-05-09'),
        'Fukushima': pd.Timestamp('2011-03-11'),
        'COVID-19': pd.Timestamp('2020-03-23'),
        'Supply Chain': pd.Timestamp('2021-10-01'),
    }
    for i, name in enumerate(cases_list):
        label = label_map[name]
        ax = axes[i]
        cr, ct = load_case(name)
        dt_cr = dt_ct = case_dt(name)
        ax.plot(cr.index, cum_pi(cr, dt_cr), color=C['crisis'], lw=1.2, label='Full event window')
        ax.plot(ct.index, cum_pi(ct, dt_ct), color=C['control'], lw=1.2, label='Control')

        if name == '2008 Financial':
            overlap_start = max(cr.index.min(), ct.index.min())
            overlap_end = min(cr.index.max(), ct.index.max())
            ax.axvspan(
                overlap_start,
                overlap_end,
                color='#78909C',
                alpha=0.16,
                linewidth=0,
                zorder=0,
                label='Partial overlap (60.5% of control)',
            )

        collapse = collapse_dates[name]
        if cr.index[0] <= collapse <= cr.index[-1]:
            ax.axvline(collapse, color='#2c3e50', linestyle='--', linewidth=0.8,
                       alpha=0.7, label='Reference date')
        ax.set_ylabel('Π(t)')
        ax.set_title(label, fontsize=FS+1, fontweight='bold', loc='left')
        ax.text(-0.08, 1.05, chr(97+i), transform=ax.transAxes,
                fontsize=PL, fontweight='bold', va='top')
        if i == 0:
            ax.legend(loc='upper left', frameon=False)
        locator = mdates.AutoDateLocator(
            minticks=4,
            maxticks=6,
            interval_multiples=True,
        )
        ax.xaxis.set_major_locator(locator)
        ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))
        ax.tick_params(axis='x', labelrotation=30)
        for tick in ax.get_xticklabels():
            tick.set_ha('right')
    fig.savefig(os.path.join(fig_dir, 'Figure1_Pi_timeseries.png'), dpi=DPI)
    fig.savefig(os.path.join(fig_dir, 'Figure1_Pi_timeseries.pdf'))
    plt.close(fig); print('    ✅')

    # ── FIGURE 2: Cross-domain separation ──
    print('  Figure 2: Cross-domain separation...')
    fig, ax = plt.subplots(figsize=(7.08, 3.5))
    seps = t1['separation'].values
    labels = [{'2008 Financial': '2008\nFinancial\nCrisis',
               'Terra-Luna': 'Terra-Luna\nCollapse',
               'Fukushima': 'Fukushima\nDisaster',
               'COVID-19': 'COVID-19\nPandemic',
               'Supply Chain': 'Supply Chain\nDisruption'}[c] for c in cases_list]
    bars = ax.bar(range(5), seps, color=C['crisis'], edgecolor='white', width=0.6, zorder=3)
    for b, v in zip(bars, seps):
        fmt = f'{v:,.0f}×' if v > 100 else f'{v:.1f}×'
        ax.text(b.get_x()+b.get_width()/2, b.get_height()*1.1, fmt,
                ha='center', va='bottom', fontsize=FS, fontweight='bold')
    ax.set_xticks(range(5)); ax.set_xticklabels(labels, fontsize=FS-1)
    ax.set_ylabel('Crisis/Control Separation Ratio')
    ax.set_yscale('log'); ax.set_ylim(1, 10000)
    ax.axhline(1, color='grey', ls='--', lw=0.8, alpha=0.5)
    ax.grid(axis='y', alpha=0.3, zorder=0)
    fig.savefig(os.path.join(fig_dir, 'Figure2_cross_domain_separation.png'), dpi=DPI)
    fig.savefig(os.path.join(fig_dir, 'Figure2_cross_domain_separation.pdf'))
    plt.close(fig); print('    ✅')

    # ── FIGURE 3: Mult vs Add vs Max ──
    print('  Figure 3: Mult vs Add vs Max...')
    fig, ax = plt.subplots(figsize=(7.08, 3.5))
    x = np.arange(5); w = 0.25
    ax.bar(x-w, t2['Multiply_sep'], w, label='Multiplicative (ρ×Ψ×Ω)',
           color=C['mult'], edgecolor='white', zorder=3)
    ax.bar(x, t2['Additive_sep'], w, label='Additive (ρ+Ψ+Ω)',
           color=C['add'], edgecolor='white', zorder=3)
    ax.bar(x+w, t2['Max_sep'], w, label='Max (max{ρ,Ψ,Ω})',
           color=C['max'], edgecolor='white', zorder=3)
    ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=FS-1)
    ax.set_ylabel('Separation Ratio (×)')
    ax.set_yscale('log'); ax.set_ylim(1, 10000)
    ax.legend(frameon=False, fontsize=FS-1, loc='upper left')
    ax.axhline(1, color='grey', ls='--', lw=0.8, alpha=0.5)
    ax.grid(axis='y', alpha=0.3, zorder=0)
    fig.savefig(os.path.join(fig_dir, 'Figure3_mult_vs_add_vs_max.png'), dpi=DPI)
    fig.savefig(os.path.join(fig_dir, 'Figure3_mult_vs_add_vs_max.pdf'))
    plt.close(fig); print('    ✅')

    # ── FIGURE 4: Permutation distributions ──
    print(
        "  Figure 4: permutation tests "
        "(reusing Analysis 3 null distributions)..."
    )

    fig, axes = plt.subplots(
        1,
        5,
        figsize=(7.08, 2.5),
        constrained_layout=True,
    )

    for i, name in enumerate(cases_list):
        ax = axes[i]

        if name not in permutation_results:
            raise ValueError(
                f"Missing permutation results for {name}."
            )

        result = permutation_results[
            name
        ]

        pi_actual = float(
            result["actual_pi"]
        )

        pi_null = np.asarray(
            result["null_distribution"],
            dtype=float,
        )

        if len(pi_null) != result["B"]:
            raise ValueError(
                f"{name}: permutation null length "
                f"{len(pi_null)} != B={result['B']}."
            )

        if not np.isfinite(
            pi_null
        ).all():
            raise ValueError(
                f"{name}: permutation null contains "
                "non-finite values."
            )

        p_value = float(
            result["p_value"]
        )

        z_score = float(
            result["z_score"]
        )

        if not (
            0 < p_value <= 1
        ):
            raise ValueError(
                f"{name}: invalid Monte Carlo p-value "
                f"{p_value}."
            )

        if not np.isfinite(
            z_score
        ):
            raise ValueError(
                f"{name}: non-finite permutation z-score."
            )

        ax.hist(
            pi_null,
            bins=50,
            color="#BBDEFB",
            edgecolor="white",
            lw=0.3,
            density=True,
            zorder=2,
        )

        ax.axvline(
            pi_actual,
            color=C["crisis"],
            lw=1.5,
            zorder=3,
        )

        ax.set_title(
            name,
            fontsize=FS,
            fontweight="bold",
        )

        ax.text(
            0.95,
            0.95,
            f"z={z_score:.1f}\n"
            f"p_MC={p_value:.3g}",
            transform=ax.transAxes,
            ha="right",
            va="top",
            fontsize=FS - 2,
            bbox=dict(
                boxstyle="round,pad=0.3",
                facecolor="white",
                alpha=0.8,
            ),
        )

        if i == 0:
            ax.set_ylabel(
                "Density"
            )

        ax.set_xlabel(
            "Π_null"
        )

        ax.text(
            -0.15,
            1.08,
            chr(97 + i),
            transform=ax.transAxes,
            fontsize=PL,
            fontweight="bold",
            va="top",
        )

    fig.savefig(
        os.path.join(
            fig_dir,
            "Figure4_permutation_tests.png",
        ),
        dpi=DPI,
    )

    fig.savefig(
        os.path.join(
            fig_dir,
            "Figure4_permutation_tests.pdf",
        )
    )

    plt.close(
        fig
    )

    print("    ✅")

    # ── LEGACY FIGURE 5: Retrospective pattern labels ──
    print('  Legacy Figure 5: Retrospective pattern labels...')
    fig, axes = plt.subplots(1, 5, figsize=(7.08, 2.5), constrained_layout=True)
    mc = {'Ductile': '#1976D2', 'Brittle': '#D32F2F', 'Pre-loaded': '#FF9800'}
    for i, name in enumerate(cases_list):
        ax = axes[i]; cr, _ = load_case(name); dt_cr = case_dt(name)
        pi_cum = cum_pi(cr, dt_cr)
        pi_norm = pi_cum / pi_cum.max()
        days = (cr.index - cr.index[0]).days
        mode = t4[t4['name'] == name]['mode'].values[0]
        pct = t4[t4['name'] == name]['pct_of_max'].values[0]
        color = mc.get(mode, 'grey')
        ax.fill_between(days, 0, pi_norm, alpha=0.3, color=color, zorder=2)
        ax.plot(days, pi_norm, color=color, lw=1.2, zorder=3)
        ax.axhline(0.1, color='grey', ls=':', lw=0.8, alpha=0.7)
        if i == 0:
            ax.text(0.03, 0.115, '10% threshold', transform=ax.transAxes,
                    ha='left', va='bottom', fontsize=FS-2, color='grey')
        display_mode = 'Preloaded' if mode == 'Pre-loaded' else mode
        ax.set_title(
            f'{name}\n({display_mode})',
            fontsize=FS,
            fontweight='bold',
            color=color,
        )
        ax.text(0.96, 0.88, f'{pct:.0f}% at\nreference date', transform=ax.transAxes,
                ha='right', va='top', fontsize=FS-2, color=color, fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.7, edgecolor='none'))
        if i == 0: ax.set_ylabel('Π(t) / Π_end')
        ax.set_ylim(0, 1.05)
        ax.text(-0.15, 1.12, chr(97+i), transform=ax.transAxes,
                fontsize=PL, fontweight='bold', va='top')
    fig.supxlabel('Days', fontsize=FS+1)
    fig.savefig(os.path.join(fig_dir, 'Figure5_failure_modes.png'), dpi=DPI)
    fig.savefig(os.path.join(fig_dir, 'Figure5_failure_modes.pdf'))
    plt.close(fig); print('    ✅')

    # Figure 6 was withdrawn from the revised submission and is not generated.

    print(f'\n  All figures saved to {fig_dir}/')
    for f in sorted(os.listdir(fig_dir)):
        sz = os.path.getsize(os.path.join(fig_dir, f)) / 1024
        print(f'    {f}  ({sz:.0f} KB)')


# ================================================================
# MAIN
# ================================================================

def main():
    parser = argparse.ArgumentParser(description='Pi Framework Legacy Audit Artifact Generator')
    parser.add_argument('--svb', action='store_true',
                        help='Include legacy SVB feasibility audit; not revised evidence')
    parser.add_argument('--figures', action='store_true',
                        help='Generate historical audit figures (needs matplotlib)')
    parser.add_argument('--st15', action='store_true',
                        help='Run legacy ST15 live-FRED reconstruction audit (not revised evidence)')
    parser.add_argument('--all', action='store_true',
                        help='Run all offline legacy analyses, diagnostics, and audit figures')
    args = parser.parse_args()

    if args.all:
        # --all means all offline reproducible audit outputs.
        # Live-FRED legacy audits require explicit --svb or --st15.
        args.figures = True

    os.makedirs(OUT_DIR, exist_ok=True)

    print()
    print('╔' + '═' * 73 + '╗')
    print('║' + '  Π STRUCTURAL STABILITY INDEX — LEGACY AUDIT GENERATOR'.ljust(73) + '║')
    print('║' + '  Historical original-window and audit artifacts'.ljust(73) + '║')
    print('╚' + '═' * 73 + '╝')
    print(f'  Data directory: {DATA_DIR}')
    print(f'  Cases: {len(CASES)}')
    print(f'  Permutations: {N_PERM:,}')

    # Check data files
    missing = []
    for name, info in CASES.items():
        for key in ['crisis', 'control']:
            path = os.path.join(DATA_DIR, info[key])
            if not os.path.exists(path):
                missing.append(f'{name}/{key}')

    if missing:
        print(f'\n  ❌ Missing data files:')
        for m in missing:
            print(f'    - {m}')
        print(f'\n  Place CSV files in {DATA_DIR}/ and re-run.')
        sys.exit(1)

    print(f'  All data files found ✅')

    # ── Legacy original-window analyses ──
    r1 = run_cross_domain()
    r2 = run_mult_vs_add()
    r3 = run_permutation_test()
    r4 = run_failure_modes()

    r5 = None
    if args.svb:
        r5 = run_svb_oos()

    # ── Legacy audit diagnostics plus active S4 descriptive table ──
    run_plimit_sensitivity()
    run_variable_perturbation()
    run_control_window_correlations()

    # ── Save CSV outputs (before figures, which read these files) ──
    df1 = pd.DataFrame(r1)
    df1.to_csv(os.path.join(OUT_DIR, 'table1_cross_domain.csv'), index=False)

    rows2 = []
    for r in r2:
        rows2.append({
            'Case': r['name'],
            'Multiply_sep': round(r['mult']['sep'], 1),
            'Additive_sep': round(r['add']['sep'], 1),
            'Max_sep': round(r['max']['sep'], 1),
            'Winner': ('Multiply' if r['mult']['sep'] >= r['add']['sep']
                       and r['mult']['sep'] >= r['max']['sep'] else 'Other'),
        })
    pd.DataFrame(rows2).to_csv(os.path.join(OUT_DIR, 'table2_mult_vs_add.csv'), index=False)

    rows3 = []
    for name, r in r3.items():
        rows3.append({
            "Case": name,
            "N": r["n"],
            "Pi_actual": round(r["actual_pi"], 6),
            "Pi_shuffled_mean": round(r["mean_shuffled"], 6),
            "Pi_shuffled_std": round(r["std_shuffled"], 6),
            "z_score": round(r["z_score"], 2),
            "Monte_Carlo_p": r["p_value"],
            "Exceedances": r["exceedances"],
            "B": r["B"],
            "Seed": r["seed"],
            "Case_seed_index": r["case_seed_index"],
            "Unadjusted_p_lt_0_05": (
                "Yes" if r["p_value"] < 0.05 else "No"
            ),
        })
    pd.DataFrame(rows3).to_csv(os.path.join(OUT_DIR, 'table3_permutation.csv'), index=False)

    df4 = pd.DataFrame(r4)
    df4.to_csv(os.path.join(OUT_DIR, 'table4_failure_modes.csv'), index=False)

    # ── Figures ──
    if args.figures:
        generate_figures(r3)


    # ── Legacy ST15 alternate reconstruction audit ──
    # Excluded from the default revised evidentiary pipeline.
    # It runs only when explicitly requested via --st15 or --all.
    if args.st15:
        print(f'\n\n{"━" * 74}')
        print(
            "  LEGACY ST15 ALTERNATE RECONSTRUCTION AUDIT"
        )
        print(f'{"━" * 74}')

        fred_api_key = os.environ.get(
            "FRED_API_KEY",
            "",
        )

        if not fred_api_key:
            raise RuntimeError(
                "ST15 was explicitly requested, "
                "but FRED_API_KEY is not set."
            )

        if not FRED_VINTAGE_DATE:
            raise RuntimeError(
                "ST15 was explicitly requested, "
                "but FRED_VINTAGE_DATE is not set."
            )

        repo_root = os.path.dirname(
            os.path.abspath(__file__)
        )

        script = os.path.join(
            repo_root,
            "sensitivity",
            "sensitivity_delta_k.py",
        )

        output_name = (
            "table_ST15_delta_k_sensitivity.csv"
        )

        expected_output = os.path.join(
            repo_root,
            "output",
            output_name,
        )

        if not os.path.isfile(
            script
        ):
            raise FileNotFoundError(
                f"Requested ST15 script not found: {script}"
            )

        # Delete any pre-existing artifact so a stale file
        # cannot be mistaken for a successful fresh run.
        if os.path.exists(
            expected_output
        ):
            os.remove(
                expected_output
            )

        print(
            "  [ST15] Legacy alternate live-FRED "
            "reconstruction (k = 1,3,5,10,20)..."
        )

        try:
            result = subprocess.run(
                [
                    sys.executable,
                    script,
                ],
                capture_output=True,
                text=True,
                timeout=300,
                env={
                    **os.environ,
                    "FRED_VINTAGE_DATE": FRED_VINTAGE_DATE,
                },
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(
                "ST15 exceeded the 300-second timeout."
            ) from exc

        if result.returncode != 0:
            stderr_tail = (
                result.stderr.strip().split("\n")[-1]
                if result.stderr.strip()
                else ""
            )

            stdout_tail = (
                result.stdout.strip().split("\n")[-1]
                if result.stdout.strip()
                else ""
            )

            detail = (
                stderr_tail
                or stdout_tail
                or "no diagnostic output"
            )

            raise RuntimeError(
                f"ST15 failed with exit code "
                f"{result.returncode}: {detail[:300]}"
            )

        if not os.path.isfile(
            expected_output
        ):
            raise RuntimeError(
                "ST15 returned success but did not create "
                f"output/{output_name}."
            )

        st15 = pd.read_csv(
            expected_output
        )

        if st15.empty:
            raise ValueError(
                "ST15 output is empty."
            )

        numeric = st15.select_dtypes(
            include=[np.number]
        )

        if not numeric.empty:
            if not np.isfinite(
                numeric.to_numpy(dtype=float)
            ).all():
                raise ValueError(
                    "ST15 output contains non-finite "
                    "numeric values."
                )

        print(
            f"    Done → output/{output_name}"
        )

    # ── Final summary ──
    above_one = sum(1 for r in r1 if r['separation'] > 1.0)
    mult_wins = sum(1 for r in r2
                    if r['mult']['sep'] >= r['add']['sep']
                    and r['mult']['sep'] >= r['max']['sep'])
    sig_count = sum(1 for r in r3.values() if r['p_value'] < 0.05)

    print(f'\n\n{"╔" + "═" * 73 + "╗"}')
    print(f'{"║  FINAL SUMMARY":<74}{"║"}')
    print(f'{"╚" + "═" * 73 + "╝"}')
    print(f'  1. Original-window cumulative ratio > 1.0: {above_one}/5 selected cases')
    print(f'  2. Three-formulation comparison: multiplicative highest in {mult_wins}/5')
    print(
        '  3. Legacy original-window channel-alignment diagnostic: '
        f'{sig_count}/5 unadjusted p < 0.05'
    )
    print('  4. Legacy audit: retrospective pattern labels retained; not revised evidence')
    if r5:
        print(f'  5. Legacy SVB feasibility audit: {r5["sep"]:.1f}x (not revised evidence)')
    print('  Retrospective characterization completed for five selected cases')

    # Summary text
    with open(os.path.join(OUT_DIR, 'summary.txt'), 'w') as f:
        f.write('Pi Framework — Retrospective Cross-Case Results\n')
        f.write('=' * 50 + '\n\n')
        f.write(f'1. Original-window cumulative ratio > 1.0: {above_one}/5 selected cases\n')
        f.write(f'2. Three-formulation comparison: multiplicative highest in {mult_wins}/5\n')
        f.write(
            '3. Legacy original-window channel-alignment diagnostic: '
            f'{sig_count}/5 unadjusted p < 0.05\n'
        )
        f.write('4. Legacy audit: retrospective pattern labels retained; not revised evidence\n')
        if r5:
            f.write(f'5. Legacy SVB feasibility audit: {r5["sep"]:.1f}x (not revised evidence)\n')
        f.write('Interpretation: retrospective characterization of five selected cases; not universal validation or prospective prediction.\n')
        f.write(
            '\nActive supporting diagnostics: S4 control-window '
            'correlations, post-control variable substitution, '
            'additional-case metric alignment, and specification '
            'provenance.\n'
        )
        f.write(
            'Legacy audits retained for reproducibility but excluded '
            'from revised evidence: retrospective pattern labels and '
            'threshold grid, S1 scale invariance, S2 perturbation, '
            'ST15 transform-window reconstruction, and ST17 '
            'trajectory analyses.\n'
        )
        if args.figures:
            f.write(f'Figures: 6 historical audit figures (300 dpi PNG + PDF)\n')

    print(f'\n  Results saved to {OUT_DIR}/')
    print()


if __name__ == '__main__':
    main()
