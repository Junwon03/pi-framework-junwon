"""
Legacy Audit Analysis: Matched-Pipeline Comparison
===================================================
This analysis is excluded from the revised manuscript's evidentiary package
and retained only for audit reproducibility.

Runs Dot-com and Repo cases using an identical pipeline to 2008:
  - TOTBKCR weekly -> daily interpolation + ffill
  - DFF and TEDRATE: |Delta-5d| transforms
  - dt = 1/365 (consistent with manuscript τ₀ = 1/365 for daily data)
  Note: Sep(Π) is dt-invariant (dt cancels in the ratio), verified numerically.

Fully self-contained: no imports from repo modules.
Place in: {repo_root}/sensitivity/sensitivity_matched_pipeline.py
Run from repo root: python sensitivity/sensitivity_matched_pipeline.py
Requires: FRED_API_KEY environment variable

Output: output/table_ST16_matched_pipeline.csv
"""

import os
import sys
import pandas as pd
import numpy as np
import requests

FRED_API_KEY = os.environ.get('FRED_API_KEY', '')
FRED_VINTAGE_DATE = os.environ.get("FRED_VINTAGE_DATE", "2026-02-17")
_base = os.path.dirname(os.path.abspath(__file__))
_repo = os.path.dirname(_base)
OUT_DIR = os.path.join(_repo, 'output')
os.makedirs(OUT_DIR, exist_ok=True)

DELTA_DAYS = 5
PLIMIT_PERCENTILE = 99
DAYS_PER_YEAR = 365  # manuscript τ₀ = 1/365; Sep is dt-invariant


# ================================================================
# FRED fetch (self-contained)
# ================================================================
def fetch_fred(series_id, start, end):
    url = (f"https://api.stlouisfed.org/fred/series/observations?"
           f"series_id={series_id}&api_key={FRED_API_KEY}"
           f"&file_type=json&observation_start={start}&observation_end={end}"
           f"&realtime_start={FRED_VINTAGE_DATE}&realtime_end={FRED_VINTAGE_DATE}")
    resp = requests.get(url, timeout=30)
    if resp.status_code != 200:
        raise RuntimeError(f"HTTP {resp.status_code} for {series_id}")
    obs = resp.json().get('observations', [])
    df = pd.DataFrame(obs)
    df['date'] = pd.to_datetime(df['date'])
    df['value'] = pd.to_numeric(df['value'], errors='coerce')
    s = df.set_index('date')['value'].dropna()
    s.index = s.index.tz_localize(None).normalize()
    s = s[~s.index.duplicated(keep='last')].sort_index()
    return s


def interpolate_to_daily(monthly, daily_index):
    combined = monthly.reindex(monthly.index.union(daily_index))
    interpolated = combined.interpolate(method='time')
    return interpolated.reindex(daily_index).ffill().bfill()


# ================================================================
# Pi calculation (embedded from pi_calculator.py)
# ================================================================
def compute_pi_pipeline(rho, psi, omega, stable_start, stable_end,
                        analysis_start, analysis_end, dt):
    # Calibrate
    rho_s = rho[stable_start:stable_end].dropna()
    psi_s = psi[stable_start:stable_end].dropna()
    omega_s = omega[stable_start:stable_end].dropna()

    p_limits = {
        'rho': max(np.percentile(rho_s, PLIMIT_PERCENTILE), 1e-10),
        'psi': max(np.percentile(psi_s, PLIMIT_PERCENTILE), 1e-10),
        'omega': max(np.percentile(omega_s, PLIMIT_PERCENTILE), 1e-10),
    }

    # Slice
    r = rho[analysis_start:analysis_end].dropna()
    p = psi[analysis_start:analysis_end].dropna()
    o = omega[analysis_start:analysis_end].dropna()
    idx = r.index.intersection(p.index).intersection(o.index)
    r, p, o = r.reindex(idx), p.reindex(idx), o.reindex(idx)

    # Normalize -> stress -> Pi
    r_norm = (r / p_limits['rho']).clip(lower=0)
    p_norm = (p / p_limits['psi']).clip(lower=0)
    o_norm = (o / p_limits['omega']).clip(lower=0)
    stress = r_norm * p_norm * o_norm
    pi = (stress * dt).cumsum()

    return {
        'pi_final': pi.iloc[-1] if len(pi) > 0 else 0,
        'N': len(idx),
        'p_limits': p_limits,
        'index': idx,
    }


# ================================================================
# Case definitions
# ================================================================
CASES = {
    'dotcom_matched': {
        'name': '2000 Dot-com (matched pipeline)',
        'fetch_start': '1993-01-01',
        'fetch_end': '2002-12-31',
        'stable_start': '1993-01-01',
        'stable_end': '1998-12-31',
        'control_start': '1996-01-01',
        'control_end': '1998-12-31',
        'crisis_start': '1999-01-01',
        'crisis_end': '2002-12-31',
    },
    'repo_matched': {
        'name': '2019 Repo (matched pipeline)',
        'fetch_start': '2014-01-01',
        'fetch_end': '2020-02-29',
        'stable_start': '2014-01-01',
        'stable_end': '2018-12-31',
        'control_start': '2017-01-01',
        'control_end': '2018-12-31',
        'crisis_start': '2019-01-01',
        'crisis_end': '2020-02-29',
    },
}


def run_matched_pipeline(case_key):
    cfg = CASES[case_key]
    dt = 1.0 / DAYS_PER_YEAR

    print(f"\n  {cfg['name']}")
    print(f"  Pipeline: |Delta-{DELTA_DAYS}d| + daily interpolation + dt=1/{DAYS_PER_YEAR}")

    # Fetch
    dff_raw = fetch_fred('DFF', cfg['fetch_start'], cfg['fetch_end'])
    ted_raw = fetch_fred('TEDRATE', cfg['fetch_start'], cfg['fetch_end'])
    bkcr_raw = fetch_fred('TOTBKCR', cfg['fetch_start'], cfg['fetch_end'])
    print(f"  DFF: {len(dff_raw)}, TEDRATE: {len(ted_raw)}, TOTBKCR: {len(bkcr_raw)}")

    # Transform: |Delta-5d|
    rho = dff_raw.diff(DELTA_DAYS).abs()
    psi = ted_raw.diff(DELTA_DAYS).abs()
    common_idx = rho.dropna().index.intersection(psi.dropna().index)
    omega = interpolate_to_daily(bkcr_raw, common_idx)

    rho = rho.reindex(common_idx)
    psi = psi.reindex(common_idx)
    valid = rho.notna() & psi.notna() & omega.notna()
    idx = common_idx[valid]
    rho, psi, omega = rho.reindex(idx), psi.reindex(idx), omega.reindex(idx)

    print(f"  Aligned: {len(idx)} daily observations")

    # Crisis + Control
    crisis = compute_pi_pipeline(rho, psi, omega,
                                 cfg['stable_start'], cfg['stable_end'],
                                 cfg['crisis_start'], cfg['crisis_end'], dt)
    control = compute_pi_pipeline(rho, psi, omega,
                                  cfg['stable_start'], cfg['stable_end'],
                                  cfg['control_start'], cfg['control_end'], dt)

    pi_c = crisis['pi_final']
    pi_n = control['pi_final']
    sep_pi = pi_c / pi_n if pi_n > 0 else float('inf')

    T_c = crisis['N'] * dt
    T_n = control['N'] * dt
    sep_s = (pi_c / T_c) / (pi_n / T_n) if (T_n > 0 and pi_n > 0) else float('inf')

    # Permutation test
    rng = np.random.RandomState(42)
    p_lim = crisis['p_limits']
    cr_idx = crisis['index']
    r = (rho.reindex(cr_idx) / p_lim['rho']).clip(lower=0).values.copy()
    p = (psi.reindex(cr_idx) / p_lim['psi']).clip(lower=0).values.copy()
    o = (omega.reindex(cr_idx) / p_lim['omega']).clip(lower=0).values.copy()

    actual = (r * p * o).sum()
    perms = []
    for _ in range(1000):
        rng.shuffle(r); rng.shuffle(p); rng.shuffle(o)
        perms.append((r * p * o).sum())
    perms = np.array(perms)
    z = (actual - perms.mean()) / (perms.std() + 1e-15)
    pval = np.mean(perms >= actual)

    print(f"  Sep(Pi)={sep_pi:.1f}x, Sep(S_bar)={sep_s:.1f}x, z={z:.2f}, p={pval:.4f}")

    return {
        'case': cfg['name'],
        'pipeline': f'|Delta-{DELTA_DAYS}d| + interp + dt=1/{DAYS_PER_YEAR}',
        'N_crisis': crisis['N'],
        'N_control': control['N'],
        'Sep_Pi': round(sep_pi, 1),
        'Sep_S_bar': round(sep_s, 1),
        'z': round(z, 2),
        'p': round(pval, 4),
    }


# ================================================================
# Main
# ================================================================
def main():
    print("=" * 58)
    print("  ST16: Matched-Pipeline Specificity Test")
    print("  Dot-com & Repo with full 2008 pipeline")
    print("=" * 58)

    if not FRED_API_KEY:
        print("  WARNING: FRED_API_KEY not set. Skipping ST16.")
        return

    results = []
    for key in CASES:
        try:
            r = run_matched_pipeline(key)
            results.append(r)
        except Exception as e:
            print(f"  ERROR for {key}: {e}")
            import traceback
            traceback.print_exc()

    # Reference rows for comparison
    # Raw weekly results from run_additional_cases.py (different pipeline, included for context)
    ref_rows = [
        {'case': '2000 Dot-com (raw weekly)', 'pipeline': 'raw levels, weekly',
         'N_crisis': '-', 'N_control': '-',
         'Sep_Pi': 1.2, 'Sep_S_bar': 0.9, 'z': '-', 'p': '-'},
        {'case': '2019 Repo (raw weekly)', 'pipeline': 'raw levels, weekly',
         'N_crisis': '-', 'N_control': '-',
         'Sep_Pi': 0.7, 'Sep_S_bar': 1.2, 'z': '-', 'p': '-'},
    ]

    # Compute 2008 baseline dynamically from existing CSV (not hardcoded)
    data_dir = os.path.join(_repo, 'data')
    cr_2008_path = os.path.join(data_dir, 'crisis_2008_pi.csv')
    ct_2008_path = os.path.join(data_dir, 'control_2004_2006_pi.csv')
    if os.path.exists(cr_2008_path) and os.path.exists(ct_2008_path):
        cr_2008 = pd.read_csv(cr_2008_path, index_col=0, parse_dates=True)
        ct_2008 = pd.read_csv(ct_2008_path, index_col=0, parse_dates=True)
        dt_base = 1.0 / DAYS_PER_YEAR
        pi_cr = (cr_2008['stress'] * dt_base).sum()
        pi_ct = (ct_2008['stress'] * dt_base).sum()
        T_cr = len(cr_2008) * dt_base
        T_ct = len(ct_2008) * dt_base
        sep_pi = round(pi_cr / pi_ct, 1) if pi_ct > 0 else float('inf')
        sep_sbar = round((pi_cr / T_cr) / (pi_ct / T_ct), 1) if pi_ct > 0 and T_ct > 0 else float('inf')
        ref_rows.append({
            'case': '2008 Financial (baseline)',
            'pipeline': f'|Delta-{DELTA_DAYS}d| + interp + dt=1/{DAYS_PER_YEAR}',
            'N_crisis': len(cr_2008), 'N_control': len(ct_2008),
            'Sep_Pi': sep_pi, 'Sep_S_bar': sep_sbar, 'z': 6.33, 'p': 0.001,
        })
        print(f"  2008 baseline computed from CSV: Sep(Π) = {sep_pi}×, Sep(S̄) = {sep_sbar}×")
    else:
        print("  WARNING: 2008 CSV not found, using hardcoded baseline")
        ref_rows.append({
            'case': '2008 Financial (baseline)',
            'pipeline': f'|Delta-{DELTA_DAYS}d| + interp + dt=1/{DAYS_PER_YEAR}',
            'N_crisis': 990, 'N_control': 574,
            'Sep_Pi': 18.6, 'Sep_S_bar': 10.8, 'z': 6.33, 'p': 0.001,
        })

    all_results = results + ref_rows
    df = pd.DataFrame(all_results)
    out_path = os.path.join(OUT_DIR, 'table_ST16_matched_pipeline.csv')
    df.to_csv(out_path, index=False)

    print(f"\n  Saved: {out_path}")
    print(df.to_string(index=False))

    print("\n  INTERPRETATION:")
    print("  - If matched Sep still << 2008 (18.6x): domain specificity confirmed")
    print("  - If matched Sep >> raw Sep: transform amplifies signal")
    print("  - If matched Sep ~ 2008: reframe as severity gradient")


if __name__ == '__main__':
    main()
