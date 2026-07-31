"""
Pi Framework — Variable Substitution Robustness (2008 Financial Case)
=====================================================================
Tests whether the framework's conclusions hold when individual variables
are replaced with conceptually similar alternatives from public sources.

Key design: uses the SAME date indices as the existing analysis
(from data/crisis_2008_pi.csv and data/control_2004_2006_pi.csv)
so that baseline separation matches run_all.py exactly.
Only the variable content changes, not the observation window.

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

FRED_API_KEY = os.environ.get('FRED_API_KEY', '')
FRED_VINTAGE_DATE = os.environ.get("FRED_VINTAGE_DATE", "2026-02-17")

# Files from existing analysis
CRISIS_FILE = 'crisis_2008_pi.csv'
CONTROL_FILE = 'control_2004_2006_pi.csv'


# ================================================================
# FRED DATA FETCHING
# ================================================================

def fetch_fred(series_id, start, end):
    """Fetch a FRED series via API."""
    import requests
    url = (f"https://api.stlouisfed.org/fred/series/observations?"
           f"series_id={series_id}&api_key={FRED_API_KEY}"
           f"&file_type=json&observation_start={start}&observation_end={end}"
           f"&realtime_start={FRED_VINTAGE_DATE}&realtime_end={FRED_VINTAGE_DATE}")
    try:
        resp = requests.get(url, timeout=30)
        if resp.status_code == 200:
            obs = resp.json().get('observations', [])
            df = pd.DataFrame(obs)
            df['date'] = pd.to_datetime(df['date'])
            df['value'] = pd.to_numeric(df['value'], errors='coerce')
            return df.set_index('date')['value'].dropna()
        else:
            print(f'    WARNING: HTTP {resp.status_code} for {series_id}')
            return None
    except Exception as e:
        print(f'    WARNING: Failed to fetch {series_id}: {e}')
        return None


def align_to_index(series, target_index):
    """
    Align a FRED series to an existing date index using
    forward-fill then interpolation for any remaining gaps.
    """
    # Reindex to target dates
    aligned = series.reindex(target_index)
    # Forward-fill (for weekly/monthly data that has gaps)
    aligned = aligned.ffill()
    # Backfill any leading NaNs
    aligned = aligned.bfill()
    # Interpolate any remaining interior gaps
    aligned = aligned.interpolate()
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
        print('\n  WARNING: FRED_API_KEY not set. Skipping.')
        return None

    # ── Load existing analysis data ──
    crisis_path = os.path.join(DATA_DIR, CRISIS_FILE)
    control_path = os.path.join(DATA_DIR, CONTROL_FILE)

    if not os.path.exists(crisis_path) or not os.path.exists(control_path):
        print(f'\n  ERROR: Cannot find {CRISIS_FILE} or {CONTROL_FILE} in {DATA_DIR}')
        return None

    crisis_df = pd.read_csv(crisis_path, index_col=0, parse_dates=True)
    control_df = pd.read_csv(control_path, index_col=0, parse_dates=True)

    print(f'\n  Existing analysis:')
    print(f'    Crisis: {crisis_df.index[0].date()} to {crisis_df.index[-1].date()}, N={len(crisis_df)}')
    print(f'    Control: {control_df.index[0].date()} to {control_df.index[-1].date()}, N={len(control_df)}')

    # Verify baseline separation from existing data
    dt = 1.0 / 365
    pi_crisis_existing = (crisis_df['stress'] * dt).sum()
    pi_control_existing = (control_df['stress'] * dt).sum()
    sep_existing = pi_crisis_existing / pi_control_existing if pi_control_existing > 0 else float('inf')
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
    for sid, desc in [('DGS2', '2-Year Treasury (alt rho)'),
                       ('VIXCLS', 'VIX (alt Psi)'),
                       ('COMPOUT', 'Commercial Paper (alt Omega)')]:
        print(f'    Fetching {sid} ({desc})...')
        s = fetch_fred(sid, stable_fetch_start, fetch_end)
        if s is not None:
            print(f'      -> {len(s)} observations')
            alt_series[sid] = s
        else:
            print(f'      -> FAILED')
        time.sleep(0.3)

    # Fallback for Commercial Paper
    if 'COMPOUT' not in alt_series:
        for fallback in ['DTBSPCKM', 'COMPAPER']:
            print(f'    Trying {fallback} as fallback...')
            s = fetch_fred(fallback, stable_fetch_start, fetch_end)
            if s is not None:
                alt_series['COMPOUT'] = s
                print(f'      -> {len(s)} observations')
                break
            time.sleep(0.3)

    # Also fetch baseline variables for P-limit calculation of substitutes
    print(f'    Fetching baseline vars for P-limit reference...')
    for sid in ['DFF', 'TEDRATE', 'TOTBKCR']:
        s = fetch_fred(sid, stable_fetch_start, fetch_end)
        if s is not None:
            alt_series[sid] = s
            print(f'      {sid}: {len(s)} obs')
        time.sleep(0.3)

    # ── Compute P-limits for alternative variables ──
    # Use control period as stable reference (same as run_all.py)
    control_idx = control_df.index

    def compute_plimit(series, ref_index, percentile=99):
        """Compute P-limit over a reference period."""
        aligned = align_to_index(series, ref_index)
        vals = aligned.dropna()
        if len(vals) > 10:
            return np.percentile(vals, percentile)
        return vals.max() if len(vals) > 0 else 1.0

    # ── Build substitution configurations ──
    def compute_sep_with_sub(crisis_rho_vals, crisis_psi_vals, crisis_omega_vals,
                              control_rho_vals, control_psi_vals, control_omega_vals):
        """Compute the legacy cumulative separation."""
        crisis_stress = crisis_rho_vals * crisis_psi_vals * crisis_omega_vals
        control_stress = control_rho_vals * control_psi_vals * control_omega_vals
        pi_cr = (crisis_stress * dt).sum()
        pi_ct = (control_stress * dt).sum()
        return pi_cr, pi_ct, pi_cr / pi_ct if pi_ct > 0 else float('inf')

    def compute_nonoverlap_mean_with_sub(
        crisis_rho_vals,
        crisis_psi_vals,
        crisis_omega_vals,
        control_rho_vals,
        control_psi_vals,
        control_omega_vals,
    ):
        """Compute the primary non-overlapping mean-stress ratio."""
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
        crisis_exclusive = crisis_stress.loc[
            crisis_stress.index > control_end
        ]

        if crisis_exclusive.empty:
            raise ValueError(
                "No crisis observations remain after the control window."
            )
        if crisis_exclusive.isna().any() or control_stress.isna().any():
            raise ValueError(
                "Missing stress values in the non-overlap comparison."
            )

        crisis_mean = float(crisis_exclusive.mean())
        control_mean = float(control_stress.mean())

        if control_mean <= 0:
            raise ValueError("Control mean stress must be positive.")

        return (
            crisis_mean,
            control_mean,
            crisis_mean / control_mean,
            len(crisis_exclusive),
        )

    # Baseline (using existing normalized channels)
    pi_cr_b, pi_ct_b, sep_b = compute_sep_with_sub(
        crisis_rho, crisis_psi, crisis_omega,
        control_rho, control_psi, control_omega)

    print(f'\n  Baseline (from existing norm channels): Sep = {sep_b:.1f}x')

    mean_cr_b, mean_ct_b, nonoverlap_sep_b, n_exclusive_b = (
        compute_nonoverlap_mean_with_sub(
            crisis_rho,
            crisis_psi,
            crisis_omega,
            control_rho,
            control_psi,
            control_omega,
        )
    )
    print(
        f'  Baseline non-overlap mean ratio = '
        f'{nonoverlap_sep_b:.4f}x'
    )

    nonoverlap_results = [{
        'Configuration': 'Baseline (DFF x TEDRATE x TOTBKCR)',
        'rho': 'DFF',
        'psi': 'TEDRATE',
        'omega': 'TOTBKCR',
        'Mean_crisis_exclusive': round(mean_cr_b, 10),
        'Mean_control': round(mean_ct_b, 10),
        'Nonoverlap_mean_ratio': round(nonoverlap_sep_b, 10),
        'N_crisis_exclusive': n_exclusive_b,
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
    def normalize_alt(series_key, transform, crisis_idx, control_idx):
        """
        Normalize an alternative FRED variable using the same approach
        as the baseline: P-limit from control period, then divide.
        Returns (crisis_norm, control_norm) or (None, None) if unavailable.
        """
        if series_key not in alt_series:
            return None, None

        raw = alt_series[series_key]

        # Align to crisis and control indices
        crisis_vals = align_to_index(raw, crisis_idx)
        control_vals = align_to_index(raw, control_idx)

        # Apply transform
        if transform == 'pct_change':
            # Need broader series for pct_change, align and compute
            all_idx = crisis_idx.union(control_idx).sort_values()
            all_vals = align_to_index(raw, all_idx)
            all_pct = all_vals.pct_change().abs().fillna(0)
            crisis_vals = all_pct.reindex(crisis_idx).fillna(0)
            control_vals = all_pct.reindex(control_idx).fillna(0)

        # P-limit from control period
        p99 = np.percentile(control_vals.dropna(), 99) if len(control_vals.dropna()) > 10 else control_vals.max()
        p99 = max(p99, 1e-10)

        return crisis_vals / p99, control_vals / p99

    crisis_idx = crisis_df.index
    ctrl_idx = control_df.index

    # Prepare alt channels
    alt_rho_cr, alt_rho_ct = normalize_alt('DGS2', 'raw', crisis_idx, ctrl_idx)
    alt_psi_cr, alt_psi_ct = normalize_alt('VIXCLS', 'raw', crisis_idx, ctrl_idx)
    alt_omega_cr, alt_omega_ct = normalize_alt('COMPOUT', 'pct_change', crisis_idx, ctrl_idx)

    # ── Run substitutions ──
    subs = []

    if alt_rho_cr is not None:
        subs.append({
            'name': 'rho -> DGS2 (2-Year Treasury)',
            'cr': (alt_rho_cr, crisis_psi, crisis_omega),
            'ct': (alt_rho_ct, control_psi, control_omega),
            'labels': ('DGS2', 'TEDRATE', 'TOTBKCR'),
        })

    if alt_psi_cr is not None:
        subs.append({
            'name': 'Psi -> VIXCLS (VIX)',
            'cr': (crisis_rho, alt_psi_cr, crisis_omega),
            'ct': (control_rho, alt_psi_ct, control_omega),
            'labels': ('DFF', 'VIXCLS', 'TOTBKCR'),
        })

    if alt_omega_cr is not None:
        subs.append({
            'name': 'Omega -> COMPOUT (Commercial Paper)',
            'cr': (crisis_rho, crisis_psi, alt_omega_cr),
            'ct': (control_rho, control_psi, alt_omega_ct),
            'labels': ('DFF', 'TEDRATE', 'COMPOUT'),
        })

    if all(x is not None for x in [alt_rho_cr, alt_psi_cr, alt_omega_cr]):
        subs.append({
            'name': 'All three substituted (DGS2 x VIX x COMPOUT)',
            'cr': (alt_rho_cr, alt_psi_cr, alt_omega_cr),
            'ct': (alt_rho_ct, alt_psi_ct, alt_omega_ct),
            'labels': ('DGS2', 'VIXCLS', 'COMPOUT'),
        })

    for sub in subs:
        print(f'\n  Testing: {sub["name"]}...')
        pi_cr, pi_ct, sep = compute_sep_with_sub(*sub['cr'], *sub['ct'])
        pct = (sep / sep_b - 1) * 100

        mean_cr, mean_ct, nonoverlap_sep, n_exclusive = (
            compute_nonoverlap_mean_with_sub(*sub['cr'], *sub['ct'])
        )
        nonoverlap_pct = (
            (nonoverlap_sep / nonoverlap_sep_b - 1) * 100
        )

        print(f'    Sep = {sep:.1f}x ({pct:+.1f}% from baseline)')
        print(
            f'    Non-overlap mean ratio = {nonoverlap_sep:.4f}x '
            f'({nonoverlap_pct:+.1f}% from baseline)'
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

        nonoverlap_results.append({
            'Configuration': sub['name'],
            'rho': sub['labels'][0],
            'psi': sub['labels'][1],
            'omega': sub['labels'][2],
            'Mean_crisis_exclusive': round(mean_cr, 10),
            'Mean_control': round(mean_ct, 10),
            'Nonoverlap_mean_ratio': round(nonoverlap_sep, 10),
            'N_crisis_exclusive': n_exclusive,
            'N_control': len(control_df),
            'Pct_change_from_baseline': f'{nonoverlap_pct:+.1f}%',
        })

    # ── Save ──
    df = pd.DataFrame(results)
    df.to_csv(
        os.path.join(OUT_DIR, 'table_variable_substitution.csv'),
        index=False,
    )

    nonoverlap_df = pd.DataFrame(nonoverlap_results)
    nonoverlap_path = os.path.join(
        OUT_DIR,
        'table_nonoverlap_variable_substitution.csv',
    )
    nonoverlap_df.to_csv(nonoverlap_path, index=False)

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

    print(f'\n  Non-overlap variable-substitution summary:')
    print(
        nonoverlap_df[
            [
                'Configuration',
                'Nonoverlap_mean_ratio',
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

    results = run_substitution_test()
    if results is None:
        print('\n  Test skipped (no API key or missing data)')
        sys.exit(0)
    print()


if __name__ == '__main__':
    main()
