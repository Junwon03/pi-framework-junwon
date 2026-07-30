"""
Pi Framework — Additional Comparison Cases
============================================
Generates new crisis/control datasets using EXISTING variable definitions
applied to different time periods. No variable redefinition.

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
     Control: 2009-01 to 2010-12
     Stable (P-limit): 2006-01 to 2010-12

Requires: FRED_API_KEY environment variable
Usage: python run_additional_cases.py

Outputs:
  data/crisis_dotcom_pi.csv, data/control_dotcom_pi.csv
  data/crisis_repo_pi.csv, data/control_repo_pi.csv
  data/crisis_thailand_pi.csv, data/control_thailand_pi.csv
  output/table_additional_cases.csv
  output/table_additional_permutation.csv
"""

import pandas as pd
import numpy as np
import os
import sys
import time as time_module
from scipy import stats

FRED_API_KEY = os.environ.get('FRED_API_KEY', '')
FRED_VINTAGE_DATE = os.environ.get("FRED_VINTAGE_DATE", "2026-02-17")
_base = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(_base, 'data')
OUT_DIR = os.path.join(_base, 'output')
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(OUT_DIR, exist_ok=True)


# ================================================================
# FRED FETCH
# ================================================================

def fetch_fred(series_id, start, end):
    import requests
    url = (f"https://api.stlouisfed.org/fred/series/observations?"
           f"series_id={series_id}&api_key={FRED_API_KEY}"
           f"&file_type=json&observation_start={start}&observation_end={end}"
           f"&realtime_start={FRED_VINTAGE_DATE}&realtime_end={FRED_VINTAGE_DATE}")
    resp = requests.get(url, timeout=30)
    if resp.status_code != 200:
        print(f'    ERROR: HTTP {resp.status_code} for {series_id}')
        return None
    obs = resp.json().get('observations', [])
    df = pd.DataFrame(obs)
    df['date'] = pd.to_datetime(df['date'])
    df['value'] = pd.to_numeric(df['value'], errors='coerce')
    return df.set_index('date')['value'].dropna()


# ================================================================
# CASE DEFINITIONS
# ================================================================

CASES = {
    'dotcom': {
        'name': '2000 Dot-com Crash',
        'domain': 'Traditional Finance',
        'freq': 'daily',
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
        'dt': 1.0 / 365,
    },
    'repo': {
        'name': '2019 Repo Near-miss',
        'domain': 'Traditional Finance (Near-miss)',
        'freq': 'daily',
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
        'dt': 1.0 / 365,
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
        'dt': 1.0 / 12,
    },
}


# ================================================================
# PIPELINE
# ================================================================

def process_case(case_id, case_def):
    print(f'\n  {"="*60}')
    print(f'  {case_def["name"]} ({case_def["domain"]})')
    print(f'  {"="*60}')

    # Fetch data
    raw = {}
    for ch_name, ch_def in case_def['variables'].items():
        print(f'    Fetching {ch_def["series"]}...')
        s = fetch_fred(ch_def['series'], case_def['fetch_start'], case_def['fetch_end'])
        if s is None:
            print(f'    FAILED: {ch_def["series"]}')
            return None
        print(f'      -> {len(s)} obs')
        raw[ch_name] = s
        time_module.sleep(0.3)

    # Build common index
    common_idx = raw['rho'].index
    for ch in ['psi', 'omega']:
        common_idx = common_idx.intersection(raw[ch].index)
    common_idx = common_idx.sort_values()
    print(f'    Common index: {len(common_idx)} dates')

    # Apply transforms
    channels = {}
    for ch_name, ch_def in case_def['variables'].items():
        s = raw[ch_name].reindex(common_idx)
        if ch_def['transform'] == 'pct_change':
            s = s.pct_change().abs().fillna(0)
        elif ch_def['transform'] == 'clip_nonneg':
            s = s.clip(lower=0)  # Diffusion index: negative=improvement → set to 0
        channels[ch_name] = s

    # P-limits from stable period
    stable_mask = (common_idx >= case_def['stable_start']) & (common_idx <= case_def['stable_end'])
    plimits = {}
    for ch_name in ['rho', 'psi', 'omega']:
        vals = channels[ch_name][stable_mask].dropna()
        if len(vals) > 10:
            plimits[ch_name] = np.percentile(vals, 99)
        else:
            plimits[ch_name] = vals.max() if len(vals) > 0 else 1.0
        plimits[ch_name] = max(plimits[ch_name], 1e-10)
        print(f'    P99({ch_name}) = {plimits[ch_name]:.6f} (from {stable_mask.sum()} stable obs)')

    # Check non-redundancy in stable period
    stable_rho = channels['rho'][stable_mask]
    stable_psi = channels['psi'][stable_mask]
    stable_omega = channels['omega'][stable_mask]
    r_rp = stable_rho.corr(stable_psi)
    r_ro = stable_rho.corr(stable_omega)
    r_po = stable_psi.corr(stable_omega)
    max_r = max(abs(r_rp), abs(r_ro), abs(r_po))
    print(f'    Non-redundancy: r(rho,psi)={r_rp:.3f}, r(rho,omega)={r_ro:.3f}, r(psi,omega)={r_po:.3f}')
    print(f'    max|r| = {max_r:.3f} {"PASS (<0.7)" if max_r < 0.7 else "FAIL (>=0.7)"}')

    # Normalize (clip at 0 to prevent negative contributions, matching PiCalc)
    norm = {}
    for ch_name in ['rho', 'psi', 'omega']:
        norm[ch_name] = (channels[ch_name] / plimits[ch_name]).clip(lower=0)

    # Stress and Pi
    stress = norm['rho'] * norm['psi'] * norm['omega']
    dt = case_def['dt']
    pi = (stress * dt).cumsum()

    # Build dataframes
    df_full = pd.DataFrame({
        'rho': channels['rho'],
        'psi': channels['psi'],
        'omega': channels['omega'],
        'rho_norm': norm['rho'],
        'psi_norm': norm['psi'],
        'omega_norm': norm['omega'],
        'stress': stress,
        'pi': pi,
    })

    # Split crisis and control
    crisis_mask = (common_idx >= case_def['crisis_start']) & (common_idx <= case_def['crisis_end'])
    control_mask = (common_idx >= case_def['control_start']) & (common_idx <= case_def['control_end'])

    crisis_df = df_full[crisis_mask].copy()
    control_df = df_full[control_mask].copy()

    # Recompute pi from start of each window
    crisis_df['pi'] = (crisis_df['stress'] * dt).cumsum()
    control_df['pi'] = (control_df['stress'] * dt).cumsum()

    pi_crisis = crisis_df['pi'].iloc[-1] if len(crisis_df) > 0 else 0
    pi_control = control_df['pi'].iloc[-1] if len(control_df) > 0 else 0
    sep = pi_crisis / pi_control if pi_control > 0 else float('inf')

    print(f'\n    Crisis: {crisis_df.index[0].date()} to {crisis_df.index[-1].date()}, N={len(crisis_df)}')
    print(f'    Control: {control_df.index[0].date()} to {control_df.index[-1].date()}, N={len(control_df)}')
    print(f'    Pi_crisis = {pi_crisis:.6f}')
    print(f'    Pi_control = {pi_control:.6f}')
    print(f'    Separation = {sep:.1f}x')

    # Save CSVs
    crisis_df.to_csv(os.path.join(DATA_DIR, f'crisis_{case_id}_pi.csv'))
    control_df.to_csv(os.path.join(DATA_DIR, f'control_{case_id}_pi.csv'))

    # Time-normalized
    t_crisis = len(crisis_df) * abs(dt)
    t_control = len(control_df) * abs(dt)
    sbar_crisis = pi_crisis / t_crisis if t_crisis > 0 else 0
    sbar_control = pi_control / t_control if t_control > 0 else 0
    sep_sbar = sbar_crisis / sbar_control if sbar_control > 0 else float('inf')

    # Permutation test
    print(f'    Running permutation test (10,000 shuffles)...')
    n_perm = 10000
    crisis_stress_vals = crisis_df[['rho_norm', 'psi_norm', 'omega_norm']].values
    perm_pis = np.zeros(n_perm)
    rng = np.random.default_rng(42)
    n_obs = len(crisis_stress_vals)

    for i in range(n_perm):
        idx_r = rng.permutation(n_obs)
        idx_p = rng.permutation(n_obs)
        idx_o = rng.permutation(n_obs)
        shuffled_stress = (crisis_stress_vals[idx_r, 0] *
                          crisis_stress_vals[idx_p, 1] *
                          crisis_stress_vals[idx_o, 2])
        perm_pis[i] = shuffled_stress.sum() * dt

    z_score = (pi_crisis - perm_pis.mean()) / perm_pis.std() if perm_pis.std() > 0 else 0
    p_value = (perm_pis >= pi_crisis).sum() / n_perm

    print(f'    z = {z_score:.2f}, p = {p_value:.4f}')

    # Stress max
    stress_max = stress[crisis_mask].max()

    return {
        'case_id': case_id,
        'name': case_def['name'],
        'domain': case_def['domain'],
        'freq': case_def['freq'],
        'n_crisis': len(crisis_df),
        'n_control': len(control_df),
        'pi_crisis': pi_crisis,
        'pi_control': pi_control,
        'separation': sep,
        'stress_max': stress_max,
        't_crisis_yr': t_crisis,
        't_control_yr': t_control,
        'sbar_crisis': sbar_crisis,
        'sbar_control': sbar_control,
        'sep_sbar': sep_sbar,
        'z_score': z_score,
        'p_value': p_value,
        'r_rp': r_rp,
        'r_ro': r_ro,
        'r_po': r_po,
        'max_r': max_r,
    }


def main():
    print()
    print('=' * 70)
    print('  Pi FRAMEWORK - ADDITIONAL COMPARISON CASES')
    print('  Same variables, different time periods')
    print('=' * 70)

    if not FRED_API_KEY:
        print('\n  ERROR: FRED_API_KEY not set.')
        sys.exit(1)

    results = []
    for case_id, case_def in CASES.items():
        res = process_case(case_id, case_def)
        if res:
            results.append(res)

    if not results:
        print('\n  No cases completed.')
        sys.exit(1)

    # Save cross-domain table
    cross = pd.DataFrame([{
        'name': r['name'],
        'domain': r['domain'],
        'pi_crisis': round(r['pi_crisis'], 6),
        'pi_control': round(r['pi_control'], 6),
        'separation': round(r['separation'], 1),
        'stress_max': round(r['stress_max'], 4),
        'n_crisis': r['n_crisis'],
        'n_control': r['n_control'],
    } for r in results])
    cross.to_csv(os.path.join(OUT_DIR, 'table_additional_cases.csv'), index=False)

    # Save permutation table
    perm = pd.DataFrame([{
        'Case': r['name'],
        'N': r['n_crisis'],
        'Pi_actual': round(r['pi_crisis'], 6),
        'z_score': round(r['z_score'], 2),
        'p_value': f'<1e-04' if r['p_value'] < 0.0001 else f'{r["p_value"]:.4f}',
        'Significant': 'Yes' if r['p_value'] < 0.05 else 'No',
    } for r in results])
    perm.to_csv(os.path.join(OUT_DIR, 'table_additional_permutation.csv'), index=False)

    # Save time-normalized table
    tn = pd.DataFrame([{
        'Case': r['name'],
        'N_crisis': r['n_crisis'],
        'N_control': r['n_control'],
        'T_crisis_yr': round(r['t_crisis_yr'], 3),
        'T_control_yr': round(r['t_control_yr'], 3),
        'Sep_Pi': round(r['separation'], 1),
        'Sep_Sbar': round(r['sep_sbar'], 1),
    } for r in results])
    tn.to_csv(os.path.join(OUT_DIR, 'table_additional_time_normalized.csv'), index=False)

    # Save non-redundancy table
    nr = pd.DataFrame([{
        'Case': r['name'],
        'r(rho,psi)': round(r['r_rp'], 3),
        'r(rho,omega)': round(r['r_ro'], 3),
        'r(psi,omega)': round(r['r_po'], 3),
        'max|r|': round(r['max_r'], 3),
        'Pass(<0.7)': 'Yes' if r['max_r'] < 0.7 else 'No',
    } for r in results])
    nr.to_csv(os.path.join(OUT_DIR, 'table_additional_nonredundancy.csv'), index=False)

    # Summary
    print(f'\n  {"="*70}')
    print(f'  SUMMARY')
    print(f'  {"="*70}')
    print(f'  {"Case":<30} {"Sep":>8} {"Sep(Sbar)":>10} {"z":>8} {"p":>10} {"max|r|":>8}')
    print(f'  {"-"*70}')
    for r in results:
        p_str = f'<1e-04' if r['p_value'] < 0.0001 else f'{r["p_value"]:.4f}'
        print(f'  {r["name"]:<30} {r["separation"]:>7.1f}x {r["sep_sbar"]:>9.1f}x {r["z_score"]:>7.2f} {p_str:>10} {r["max_r"]:>7.3f}')

    print(f'\n  Saved: table_additional_cases.csv, table_additional_permutation.csv')
    print(f'         table_additional_time_normalized.csv, table_additional_nonredundancy.csv')
    print(f'         + crisis/control CSVs in data/')
    print()


if __name__ == '__main__':
    main()
