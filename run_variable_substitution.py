"""
Pi Framework — Variable Substitution Robustness (2008 Financial Case)
=====================================================================
Tests whether the framework's conclusions hold when individual variables
are replaced with conceptually similar alternatives from public sources.

Key design: uses the SAME date indices, channel transformations, and
2008 calibration period as the frozen baseline analysis. Alternative source
series replace the corresponding baseline source while the observation
windows and channel transformation definitions are held fixed.

Substitutions tested (2008 Financial Crisis):
  rho: Fed Funds Rate (DFF) -> 2-Year Treasury Yield (DGS2)
  Psi: TED Spread (TEDRATE) -> VIX (VIXCLS)
  Omega: Bank Credit (TOTBKCR) -> Commercial Paper (COMPOUT)

Requires: FRED_API_KEY environment variable
Usage: python run_variable_substitution.py

Outputs: output/table_variable_substitution.csv
"""

import pandas as pd
import numpy as np
import os
import sys
import time

# ================================================================
# CONFIG
# ================================================================

_base = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(_base, 'data')

OUT_DIR = os.path.join(_base, 'output')
os.makedirs(OUT_DIR, exist_ok=True)

FRED_API_KEY = os.environ.get("FRED_API_KEY", "")
FRED_VINTAGE_DATE = os.environ.get("FRED_VINTAGE_DATE", "")

# Files from existing analysis
CRISIS_FILE = 'crisis_2008_pi.csv'
CONTROL_FILE = 'control_2004_2006_pi.csv'

# Match the frozen 2008 baseline specification.
STABLE_START = "2005-01-01"
STABLE_END = "2007-06-30"
DELTA_OBSERVATIONS = 5


# ================================================================
# FRED DATA FETCHING
# ================================================================

def fetch_fred(series_id, start, end):
    """Fetch one exact FRED series from the fixed requested vintage."""
    import requests

    if not FRED_API_KEY:
        raise RuntimeError("FRED_API_KEY is required.")
    if not FRED_VINTAGE_DATE:
        raise RuntimeError("FRED_VINTAGE_DATE is required.")

    url = "https://api.stlouisfed.org/fred/series/observations"
    params = {
        "series_id": series_id,
        "api_key": FRED_API_KEY,
        "file_type": "json",
        "observation_start": start,
        "observation_end": end,
        "realtime_start": FRED_VINTAGE_DATE,
        "realtime_end": FRED_VINTAGE_DATE,
    }

    try:
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as exc:
        raise RuntimeError(
            f"FRED request failed for {series_id}: {exc}"
        ) from exc

    try:
        payload = resp.json()
    except ValueError as exc:
        raise RuntimeError(
            f"FRED returned invalid JSON for {series_id}."
        ) from exc

    observations = payload.get("observations")
    if not observations:
        raise RuntimeError(
            f"FRED returned no observations for {series_id} "
            f"from {start} to {end} at vintage {FRED_VINTAGE_DATE}."
        )

    df = pd.DataFrame(observations)
    required = {"date", "value"}
    if not required.issubset(df.columns):
        raise RuntimeError(
            f"Malformed FRED response for {series_id}: "
            f"missing {sorted(required - set(df.columns))}"
        )

    dates = pd.to_datetime(df["date"], errors="coerce")
    values = pd.to_numeric(df["value"], errors="coerce")
    series = pd.Series(values.to_numpy(), index=dates, name=series_id)
    series = series.loc[series.index.notna()]
    series = series.dropna()
    series = series[~series.index.duplicated(keep="last")].sort_index()

    if series.empty:
        raise RuntimeError(
            f"No finite numeric observations remain for {series_id}."
        )
    if not np.isfinite(series.to_numpy(dtype=float)).all():
        raise RuntimeError(
            f"Non-finite values remain in FRED series {series_id}."
        )

    return series


def align_to_index(series, target_index):
    """
    Align a source series to target dates using only information available
    on or before each target date.

    Original source dates are retained before forward filling. Future values
    are never backward-filled into earlier target dates.
    """
    if not isinstance(series, pd.Series):
        raise TypeError("series must be a pandas Series.")

    source = series.copy()
    source.index = pd.DatetimeIndex(source.index)
    source = source[~source.index.duplicated(keep="last")].sort_index()

    target = pd.DatetimeIndex(target_index)
    if target.empty:
        raise ValueError("target_index must not be empty.")
    if target.has_duplicates:
        raise ValueError("target_index contains duplicate dates.")

    combined_index = source.index.union(target).sort_values()
    aligned = source.reindex(combined_index).ffill().reindex(target)

    if aligned.isna().any():
        missing = aligned.index[aligned.isna()]
        raise ValueError(
            "Causal alignment lacks a prior source observation for "
            f"{len(missing)} target date(s); first missing target is "
            f"{missing[0].date()}."
        )

    values = aligned.to_numpy(dtype=float)
    if not np.isfinite(values).all():
        raise ValueError("Aligned series contains non-finite values.")

    return aligned


# ================================================================
# CORE ANALYSIS
# ================================================================

def run_substitution_test():
    """Run the full variable substitution analysis."""
    print('=' * 75)
    print('  VARIABLE SUBSTITUTION SENSITIVITY (2008 Financial)')
    print('  Using existing analysis date indices for exact comparability')
    print('=' * 75)

    if not FRED_API_KEY:
        raise RuntimeError("FRED_API_KEY is required for this analysis.")
    if not FRED_VINTAGE_DATE:
        raise RuntimeError(
            "FRED_VINTAGE_DATE is required for reproducible FRED retrieval."
        )

    # ── Load existing analysis data ──
    crisis_path = os.path.join(DATA_DIR, CRISIS_FILE)
    control_path = os.path.join(DATA_DIR, CONTROL_FILE)

    if not os.path.exists(crisis_path) or not os.path.exists(control_path):
        raise FileNotFoundError(
            f"Cannot find {CRISIS_FILE} or {CONTROL_FILE} in {DATA_DIR}"
        )

    crisis_df = pd.read_csv(crisis_path, index_col=0, parse_dates=True)
    control_df = pd.read_csv(control_path, index_col=0, parse_dates=True)

    print(f'\n  Existing analysis:')
    print(f'    Crisis: {crisis_df.index[0].date()} to {crisis_df.index[-1].date()}, N={len(crisis_df)}')
    print(f'    Control: {control_df.index[0].date()} to {control_df.index[-1].date()}, N={len(control_df)}')

    # Verify baseline separation from existing data
    dt = 1.0 / 365
    pi_crisis_existing = (crisis_df['stress'] * dt).sum()
    pi_control_existing = (control_df['stress'] * dt).sum()
    if not np.isfinite(pi_control_existing) or pi_control_existing <= 0:
        raise ValueError("Existing control cumulative stress must be positive and finite.")
    if not np.isfinite(pi_crisis_existing):
        raise ValueError("Existing crisis cumulative stress must be finite.")
    sep_existing = pi_crisis_existing / pi_control_existing
    print(f'    Existing baseline Sep = {sep_existing:.1f}x')

    # Get baseline normalized channels
    crisis_rho = crisis_df['rho_norm']
    crisis_psi = crisis_df['psi_norm']
    crisis_omega = crisis_df['omega_norm']
    control_rho = control_df['rho_norm']
    control_psi = control_df['psi_norm']
    control_omega = control_df['omega_norm']

    # ── Fetch alternative variables from FRED ──
    # Need to cover both crisis and control date ranges
    fetch_start = min(crisis_df.index[0], control_df.index[0]).strftime('%Y-%m-%d')
    fetch_end = max(crisis_df.index[-1], control_df.index[-1]).strftime('%Y-%m-%d')

    # Also need stable period data for P-limit calculation
    # Stable period ends before crisis, use control start - 1 year as safety
    stable_fetch_start = (control_df.index[0] - pd.DateOffset(years=1)).strftime('%Y-%m-%d')

    print(f'\n  Fetching FRED data ({stable_fetch_start} to {fetch_end})...')

    alt_series = {}
    required_series = [
        ('DGS2', '2-Year Treasury (alt rho)'),
        ('VIXCLS', 'VIX (alt Psi)'),
        ('COMPOUT', 'Commercial Paper (alt Omega)'),
    ]

    for sid, desc in required_series:
        print(f'    Fetching {sid} ({desc})...')
        s = fetch_fred(sid, stable_fetch_start, fetch_end)
        alt_series[sid] = s
        print(
            f'      -> {len(s)} observations '
            f'[{s.index.min().date()} to {s.index.max().date()}]'
        )

    missing = [sid for sid, _ in required_series if sid not in alt_series]
    if missing:
        raise RuntimeError(
            f"Required FRED series were not retrieved: {missing}"
        )

    # ── Compute P-limits for alternative variables ──
    # Use the same stable/calibration period as the frozen 2008 baseline.
    calibration_idx = crisis_df.index[
        (crisis_df.index >= pd.Timestamp(STABLE_START))
        & (crisis_df.index <= pd.Timestamp(STABLE_END))
    ]

    if calibration_idx.empty:
        raise ValueError(
            f"No frozen baseline dates found in calibration period "
            f"{STABLE_START} to {STABLE_END}."
        )

    def compute_plimit(series, ref_index, percentile=99):
        """Compute a strict percentile P-limit over the reference period."""
        aligned = align_to_index(series, ref_index)
        vals = aligned.to_numpy(dtype=float)

        if len(vals) == 0:
            raise ValueError("Cannot compute P-limit from zero observations.")
        if not np.isfinite(vals).all():
            raise ValueError("P-limit reference values must be finite.")

        p_limit = float(np.percentile(vals, percentile))
        if not np.isfinite(p_limit) or p_limit <= 0:
            raise ValueError(
                f"Invalid P{percentile} calibration value: {p_limit}"
            )
        return p_limit

    # ── Build substitution configurations ──
    def compute_sep_with_sub(crisis_rho_vals, crisis_psi_vals, crisis_omega_vals,
                              control_rho_vals, control_psi_vals, control_omega_vals):
        """Compute the legacy cumulative separation."""
        crisis_stress = crisis_rho_vals * crisis_psi_vals * crisis_omega_vals
        control_stress = control_rho_vals * control_psi_vals * control_omega_vals
        pi_cr = (crisis_stress * dt).sum()
        pi_ct = (control_stress * dt).sum()
        if not np.isfinite(pi_cr) or not np.isfinite(pi_ct):
            raise ValueError("Cumulative stress values must be finite.")
        if pi_ct <= 0:
            raise ValueError("Control cumulative stress must be positive.")
        return pi_cr, pi_ct, pi_cr / pi_ct

    def compute_post_control_mean_with_sub(
        crisis_rho_vals,
        crisis_psi_vals,
        crisis_omega_vals,
        control_rho_vals,
        control_psi_vals,
        control_omega_vals,
    ):
        """Compute the primary post-control/control mean-stress ratio."""
        crisis_stress = (
            crisis_rho_vals * crisis_psi_vals * crisis_omega_vals
        )
        control_stress = (
            control_rho_vals * control_psi_vals * control_omega_vals
        )

        if not isinstance(crisis_stress, pd.Series):
            raise TypeError("Crisis stress must retain a datetime index.")
        if not isinstance(control_stress, pd.Series):
            raise TypeError("Control stress must retain a datetime index.")

        control_end = control_stress.index.max()
        post_control_stress = crisis_stress.loc[
            crisis_stress.index > control_end
        ]

        if post_control_stress.empty:
            raise ValueError(
                "No crisis observations remain after the control window."
            )
        if post_control_stress.isna().any() or control_stress.isna().any():
            raise ValueError(
                "Missing stress values in the non-overlap comparison."
            )

        crisis_mean = float(post_control_stress.mean())
        control_mean = float(control_stress.mean())

        if control_mean <= 0:
            raise ValueError("Control mean stress must be positive.")

        return (
            crisis_mean,
            control_mean,
            crisis_mean / control_mean,
            len(post_control_stress),
        )

    # Baseline (using existing normalized channels)
    pi_cr_b, pi_ct_b, sep_b = compute_sep_with_sub(
        crisis_rho, crisis_psi, crisis_omega,
        control_rho, control_psi, control_omega)

    print(f'\n  Baseline (from existing norm channels): Sep = {sep_b:.1f}x')

    mean_cr_b, mean_ct_b, post_control_ratio_b, n_post_control_b = (
        compute_post_control_mean_with_sub(
            crisis_rho,
            crisis_psi,
            crisis_omega,
            control_rho,
            control_psi,
            control_omega,
        )
    )
    print(
        f'  Baseline post-control/control mean ratio = '
        f'{post_control_ratio_b:.4f}x'
    )

    post_control_results = [{
        'Configuration': 'Baseline (DFF x TEDRATE x TOTBKCR)',
        'rho': 'DFF',
        'psi': 'TEDRATE',
        'omega': 'TOTBKCR',
        'Mean_post_control': round(mean_cr_b, 10),
        'Mean_control': round(mean_ct_b, 10),
        'Post_control_to_control_mean_ratio': round(post_control_ratio_b, 10),
        'N_post_control': n_post_control_b,
        'N_control': len(control_df),
        'Pct_change_from_baseline': '0.0%',
    }]

    results = [{
        'Configuration': 'Baseline (DFF x TEDRATE x TOTBKCR)',
        'rho': 'DFF', 'psi': 'TEDRATE', 'omega': 'TOTBKCR',
        'Pi_crisis': round(pi_cr_b, 4),
        'Pi_control': round(pi_ct_b, 4),
        'Separation': round(sep_b, 1),
        'N_crisis': len(crisis_df),
        'N_control': len(control_df),
        'Pct_change_from_baseline': '0.0%',
    }]

    # ── Prepare alternative normalized channels ──
    def normalize_alt(
        series_key,
        transform,
        crisis_idx,
        control_idx,
        calibration_idx,
    ):
        """
        Substitute one source series while preserving the baseline channel
        transformation and calibration definition.

        - rho/psi alternatives: absolute 5-observation first difference
        - omega alternative: level
        - P-limit: 99th percentile over the fixed 2008 calibration period

        Source transformations are computed before date alignment. Alignment
        is causal: only observations available on or before a target date are
        carried forward.
        """
        if series_key not in alt_series:
            raise KeyError(f"Required alternative series missing: {series_key}")

        raw = alt_series[series_key].copy().sort_index()

        if transform == "abs_diff_5":
            transformed = raw.diff(DELTA_OBSERVATIONS).abs().dropna()

        elif transform == "level":
            transformed = raw.dropna()

        else:
            raise ValueError(f"Unsupported transform: {transform}")

        if transformed.empty:
            raise ValueError(
                f"{series_key}: transformation produced no usable observations."
            )

        # P-limit uses the same fixed calibration period as the baseline.
        p99 = compute_plimit(
            transformed,
            calibration_idx,
            percentile=99,
        )

        # Align only after transformation so missing target dates do not
        # change the definition of a five-observation difference.
        crisis_vals = align_to_index(transformed, crisis_idx)
        control_vals = align_to_index(transformed, control_idx)

        crisis_norm = crisis_vals / p99
        control_norm = control_vals / p99

        for label, values in (
            ("crisis", crisis_norm),
            ("control", control_norm),
        ):
            arr = values.to_numpy(dtype=float)
            if values.isna().any() or not np.isfinite(arr).all():
                raise ValueError(
                    f"{series_key}: {label} normalized values must be "
                    "complete and finite."
                )
            if (arr < 0).any():
                raise ValueError(
                    f"{series_key}: normalized values must be non-negative."
                )

        return crisis_norm, control_norm

    crisis_idx = crisis_df.index
    ctrl_idx = control_df.index

    # Prepare alt channels
    alt_rho_cr, alt_rho_ct = normalize_alt(
        'DGS2',
        'abs_diff_5',
        crisis_idx,
        ctrl_idx,
        calibration_idx,
    )
    alt_psi_cr, alt_psi_ct = normalize_alt(
        'VIXCLS',
        'abs_diff_5',
        crisis_idx,
        ctrl_idx,
        calibration_idx,
    )
    alt_omega_cr, alt_omega_ct = normalize_alt(
        'COMPOUT',
        'level',
        crisis_idx,
        ctrl_idx,
        calibration_idx,
    )

    # ── Run substitutions ──
    subs = [
        {
            'name': 'rho -> DGS2 (2-Year Treasury)',
            'cr': (alt_rho_cr, crisis_psi, crisis_omega),
            'ct': (alt_rho_ct, control_psi, control_omega),
            'labels': ('DGS2', 'TEDRATE', 'TOTBKCR'),
        },
        {
            'name': 'Psi -> VIXCLS (VIX)',
            'cr': (crisis_rho, alt_psi_cr, crisis_omega),
            'ct': (control_rho, alt_psi_ct, control_omega),
            'labels': ('DFF', 'VIXCLS', 'TOTBKCR'),
        },
        {
            'name': 'Omega -> COMPOUT (Commercial Paper)',
            'cr': (crisis_rho, crisis_psi, alt_omega_cr),
            'ct': (control_rho, control_psi, alt_omega_ct),
            'labels': ('DFF', 'TEDRATE', 'COMPOUT'),
        },
        {
            'name': 'All three substituted (DGS2 x VIX x COMPOUT)',
            'cr': (alt_rho_cr, alt_psi_cr, alt_omega_cr),
            'ct': (alt_rho_ct, alt_psi_ct, alt_omega_ct),
            'labels': ('DGS2', 'VIXCLS', 'COMPOUT'),
        },
    ]

    if len(subs) != 4:
        raise AssertionError("Expected exactly four substitution configurations.")

    for sub in subs:
        print(f'\n  Testing: {sub["name"]}...')
        pi_cr, pi_ct, sep = compute_sep_with_sub(*sub['cr'], *sub['ct'])
        pct = (sep / sep_b - 1) * 100

        mean_cr, mean_ct, post_control_ratio, n_post_control = (
            compute_post_control_mean_with_sub(*sub['cr'], *sub['ct'])
        )
        post_control_pct = (
            (post_control_ratio / post_control_ratio_b - 1) * 100
        )

        print(f'    Sep = {sep:.1f}x ({pct:+.1f}% from baseline)')
        print(
            f'    Post-control/control mean ratio = {post_control_ratio:.4f}x '
            f'({post_control_pct:+.1f}% from baseline)'
        )

        results.append({
            'Configuration': sub['name'],
            'rho': sub['labels'][0],
            'psi': sub['labels'][1],
            'omega': sub['labels'][2],
            'Pi_crisis': round(pi_cr, 4),
            'Pi_control': round(pi_ct, 4),
            'Separation': round(sep, 1),
            'N_crisis': len(crisis_df),
            'N_control': len(control_df),
            'Pct_change_from_baseline': f'{pct:+.1f}%',
        })

        post_control_results.append({
            'Configuration': sub['name'],
            'rho': sub['labels'][0],
            'psi': sub['labels'][1],
            'omega': sub['labels'][2],
            'Mean_post_control': round(mean_cr, 10),
            'Mean_control': round(mean_ct, 10),
            'Post_control_to_control_mean_ratio': round(post_control_ratio, 10),
            'N_post_control': n_post_control,
            'N_control': len(control_df),
            'Pct_change_from_baseline': f'{post_control_pct:+.1f}%',
        })

    # ── Save ──
    if len(results) != 5 or len(post_control_results) != 5:
        raise AssertionError(
            "Expected baseline plus four substitution configurations."
        )

    df = pd.DataFrame(results)
    df.to_csv(
        os.path.join(OUT_DIR, 'table_variable_substitution.csv'),
        index=False,
    )

    post_control_df = pd.DataFrame(post_control_results)
    post_control_path = os.path.join(
        OUT_DIR,
        'table_nonoverlap_variable_substitution.csv',
    )
    post_control_df.to_csv(post_control_path, index=False)

    # ── Summary ──
    print(f'\n  {"="*70}')
    print(f'  {"Configuration":<48} {"Sep":>8} {"Change":>10}')
    print(f'  {"-"*70}')
    for r in results:
        print(f'  {r["Configuration"]:<48} {r["Separation"]:>7.1f}x {r["Pct_change_from_baseline"]:>10}')
    print(f'  {"="*70}')

    seps = [r['Separation'] for r in results]
    all_positive = all(s > 1.0 for s in seps)
    if len(results) > 1:
        changes = [abs(float(r['Pct_change_from_baseline'].replace('%','').replace('+','')))
                    for r in results[1:]]
        max_change = max(changes)
    else:
        max_change = 0

    print(f'\n  Descriptive summary:')
    print(f'    All configurations: crisis > control? {"Yes" if all_positive else "No"}')
    print(f'    Maximum deviation from baseline: {max_change:.1f}%')
    print(f'    Baseline matches run_all.py: Sep = {sep_b:.1f}x')

    if all_positive:
        print('    RESULT: Directional crisis > control relation retained across the tested substitutions')
    else:
        print('    RESULT: At least one tested substitution does not retain the directional relation')

    print(f'\n  Post-control variable-substitution summary:')
    print(
        post_control_df[
            [
                'Configuration',
                'Post_control_to_control_mean_ratio',
                'Pct_change_from_baseline',
            ]
        ].to_string(index=False)
    )

    print(f'\n  Saved: table_variable_substitution.csv')
    print(f'  Saved: table_nonoverlap_variable_substitution.csv')
    return results


def main():
    print()
    print('=' * 75)
    print('  Pi FRAMEWORK - VARIABLE SUBSTITUTION SENSITIVITY')
    print('  2008 Financial: Alternative variables from FRED')
    print('  Using existing crisis/control date indices')
    print('=' * 75)

    run_substitution_test()
    print()


if __name__ == '__main__':
    main()
