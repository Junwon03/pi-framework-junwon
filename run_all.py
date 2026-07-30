"""
Pi Structural Stability Index - Unified Analysis
=================================================
5-case cross-case retrospective characterization + statistical tests
+ supplementary sensitivity diagnostics + publication figures

All analyses run from pre-computed CSV data in data/ folder.
No API keys needed for core analyses.
SVB out-of-sample test requires FRED_API_KEY.

Usage:
  python run_all.py              # Core analyses (no API needed)
  python run_all.py --svb        # Include SVB out-of-sample (needs FRED_API_KEY)
  python run_all.py --figures    # Generate publication figures (needs matplotlib)
  python run_all.py --all        # Everything
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
if not os.path.exists(DATA_DIR):
    DATA_DIR = os.path.join(_base, 'Data')

OUT_DIR = os.path.join(_base, 'output')
FRED_VINTAGE_DATE = os.environ.get("FRED_VINTAGE_DATE", "2026-02-17")

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
        'variables': 'UST Mcap / BTC Dominance / LUNA Price',
        'collapse': '2022-05-09',
    },
    'Fukushima': {
        'crisis': 'crisis_fukushima_pi.csv',
        'control': 'control_fukushima_pi.csv',
        'domain': 'Physical Infrastructure',
        'variables': 'Seismic Energy / Aftershock Freq / Nikkei Drop',
        'collapse': '2011-03-11',
    },
    'COVID-19': {
        'crisis': 'crisis_covid_pi.csv',
        'control': 'control_covid_pi.csv',
        'domain': 'Pandemic / Public Health',
        'variables': 'Cases / Deaths / VIX',
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
np.random.seed(42)


# ================================================================
# UTILITIES
# ================================================================

def load_case(name):
    info = CASES[name]
    cr = pd.read_csv(os.path.join(DATA_DIR, info['crisis']),
                     index_col=0, parse_dates=True)
    ct = pd.read_csv(os.path.join(DATA_DIR, info['control']),
                     index_col=0, parse_dates=True)
    # Ensure pi column uses correct dt (1/365 daily, 1/12 monthly)
    for df in [cr, ct]:
        dt = estimate_dt(df)
        df['pi'] = (df['stress'] * dt).cumsum()
    return cr, ct


def estimate_dt(df):
    if len(df) > 1:
        avg_gap = (df.index[-1] - df.index[0]).days / len(df)
        return 1.0/12 if avg_gap > 20 else 1.0/365
    return 1.0/365


# ================================================================
# ANALYSIS 1: CROSS-CASE RETROSPECTIVE CHARACTERIZATION
# ================================================================

def run_cross_domain():
    print('=' * 75)
    print('  ANALYSIS 1: Cross-Case Retrospective Characterization (5 Cases)')
    print('=' * 75)

    results = []

    for name, info in CASES.items():
        cr, ct = load_case(name)
        dt = estimate_dt(cr)

        pi_cr = (cr['stress'] * dt).sum()
        pi_ct = (ct['stress'] * estimate_dt(ct)).sum()
        sep = pi_cr / pi_ct if pi_ct > 0 else float('inf')
        s_max = cr['stress'].max()

        results.append({
            'name': name, 'domain': info['domain'],
            'pi_crisis': pi_cr, 'pi_control': pi_ct,
            'separation': sep, 'stress_max': s_max,
            'n_crisis': len(cr), 'n_control': len(ct),
        })

    print(f'\n  {"Case":<18} {"Domain":<22} {"Π_crisis":<12} {"Π_control":<12} {"Sep":<10} {"Pass":<6}')
    print(f'  {"-" * 78}')

    for r in results:
        passed = '✅' if r['separation'] > 1.5 else '❌'
        print(f'  {r["name"]:<18} {r["domain"]:<22} {r["pi_crisis"]:<12.4f} {r["pi_control"]:<12.4f} {r["separation"]:<10.1f}x {passed:<6}')

    passed_count = sum(1 for r in results if r['separation'] > 1.5)
    print(f'\n  Result: {passed_count}/5 cases PASS (Crisis > Control)')

    return results


# ================================================================
# ANALYSIS 2: MULTIPLICATIVE vs ADDITIVE vs MAX
# ================================================================

def run_mult_vs_add():
    print(f'\n\n{"=" * 75}')
    print('  ANALYSIS 2: Multiplicative vs Additive vs Max')
    print('  S = ρ×Ψ×Ω  vs  S = ρ+Ψ+Ω  vs  S = max(ρ,Ψ,Ω)')
    print('=' * 75)

    results = []

    for name in CASES:
        cr, ct = load_case(name)
        dt = estimate_dt(cr)

        needed = ['rho_norm', 'psi_norm', 'omega_norm']
        if not all(c in cr.columns for c in needed):
            continue

        def calc_pi(df, mode):
            r, p, o = df['rho_norm'], df['psi_norm'], df['omega_norm']
            if mode == 'mult':
                s = r * p * o
            elif mode == 'add':
                s = r + p + o
            else:
                s = df[['rho_norm','psi_norm','omega_norm']].max(axis=1)
            return (s * dt).sum()

        res = {'name': name}
        for mode in ['mult', 'add', 'max']:
            pi_cr = calc_pi(cr, mode)
            pi_ct = calc_pi(ct, mode)
            sep = pi_cr / pi_ct if pi_ct > 0 else float('inf')
            res[mode] = {'crisis': pi_cr, 'control': pi_ct, 'sep': sep}

        results.append(res)

    print(f'\n  {"Case":<18} {"Multiply":<14} {"Additive":<14} {"Max":<14} {"Highest":<12}')
    print(f'  {"-" * 70}')

    mult_wins = 0
    for r in results:
        seps = {'Multiply': r['mult']['sep'], 'Additive': r['add']['sep'], 'Max': r['max']['sep']}
        winner = max(seps, key=seps.get)
        if winner == 'Multiply':
            mult_wins += 1
        print(f'  {r["name"]:<18} {r["mult"]["sep"]:<14.1f}x {r["add"]["sep"]:<14.1f}x {r["max"]["sep"]:<14.1f}x {winner}')

    print(f'\n  Multiplicative highest separation: {mult_wins}/{len(results)} selected cases')

    return results


# ================================================================
# ANALYSIS 3: PERMUTATION TEST
# ================================================================

def run_permutation_test():
    print(f'\n\n{"=" * 75}')
    print(f'  ANALYSIS 3: Permutation Test (N = {N_PERM:,})')
    print(f'  H0: Temporal coincidence of ρ, Ψ, Ω is random')
    print('=' * 75)

    results = {}

    for name in CASES:
        cr, _ = load_case(name)
        dt = estimate_dt(cr)

        needed = ['rho_norm', 'psi_norm', 'omega_norm']
        if not all(c in cr.columns for c in needed):
            continue

        rho = cr['rho_norm'].values
        psi = cr['psi_norm'].values
        omega = cr['omega_norm'].values
        n = len(rho)

        actual_pi = np.sum(rho * psi * omega) * dt

        shuffled_pis = np.zeros(N_PERM)
        for i in range(N_PERM):
            r_s = rho[np.random.permutation(n)]
            p_s = psi[np.random.permutation(n)]
            o_s = omega[np.random.permutation(n)]
            shuffled_pis[i] = np.sum(r_s * p_s * o_s) * dt

        p_value = np.mean(shuffled_pis >= actual_pi)
        z_score = (actual_pi - np.mean(shuffled_pis)) / np.std(shuffled_pis) if np.std(shuffled_pis) > 0 else float('inf')

        results[name] = {
            'actual_pi': actual_pi,
            'mean_shuffled': np.mean(shuffled_pis),
            'std_shuffled': np.std(shuffled_pis),
            'p_value': p_value,
            'z_score': z_score,
            'n': n,
        }

        sig = '***' if p_value < 0.001 else ('**' if p_value < 0.01 else ('*' if p_value < 0.05 else 'n.s.'))
        p_str = f'{p_value:.4f}' if p_value > 0 else f'<{1/N_PERM:.0e}'

        print(f'\n  {name} (n={n}):')
        print(f'    Actual Π = {actual_pi:.6f}, Shuffled = {np.mean(shuffled_pis):.6f} ± {np.std(shuffled_pis):.6f}')
        print(f'    z = {z_score:.2f}, p = {p_str} {sig}')

    # Summary
    print(f'\n  {"─" * 70}')
    print(f'  {"Case":<18} {"N":<8} {"z-score":<10} {"p-value":<12} {"Sig":<6}')
    print(f'  {"─" * 70}')

    for name, r in results.items():
        sig = '***' if r['p_value'] < 0.001 else ('**' if r['p_value'] < 0.01 else ('*' if r['p_value'] < 0.05 else 'n.s.'))
        p_str = f'{r["p_value"]:.4f}' if r['p_value'] > 0 else f'<{1/N_PERM:.0e}'
        print(f'  {name:<18} {r["n"]:<8} {r["z_score"]:<10.2f} {p_str:<12} {sig}')

    # Bonferroni
    n_tests = len(results)
    print(f'\n  Bonferroni correction (n={n_tests}):')
    for name, r in results.items():
        p_corr = min(r['p_value'] * n_tests, 1.0)
        sig = '***' if p_corr < 0.001 else ('**' if p_corr < 0.01 else ('*' if p_corr < 0.05 else 'n.s.'))
        p_str = f'{p_corr:.4f}' if p_corr > 0 else f'<{n_tests/N_PERM:.0e}'
        print(f'    {name:<18}: p_corrected = {p_str} {sig}')

    # Fisher combined
    p_values = [max(r['p_value'], 1/N_PERM) for r in results.values()]
    chi2_stat = -2 * sum(np.log(p) for p in p_values)
    fisher_p = 1 - scipy_stats.chi2.cdf(chi2_stat, df=2*len(p_values))
    print(f'\n  Fisher combined p-value: {fisher_p:.2e}')

    return results


# ================================================================
# ANALYSIS 4: EXPLORATORY PATTERN LABELS
# ================================================================

def run_failure_modes():
    print(f'\n\n{"=" * 75}')
    print('  ANALYSIS 4: Exploratory Pattern Labels')
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

        # Exploratory retrospective pattern labels, not validated failure laws.
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
# ANALYSIS 5: SVB OUT-OF-SAMPLE (optional, needs FRED API)
# ================================================================

def run_svb_oos():
    print(f'\n\n{"=" * 75}')
    print('  ANALYSIS 5: Out-of-Sample — SVB 2023 (2008 calibration)')
    print('  Variables: SAME as 2008 | P-limits: SAME as 2008 | NO re-tuning')
    print('=' * 75)

    FRED_API_KEY = os.environ.get('FRED_API_KEY', '')
    if not FRED_API_KEY:
        print('\n  ⚠ FRED_API_KEY not set. Skipping SVB out-of-sample test.')
        print('  Set FRED_API_KEY environment variable to enable.')
        return None

    import requests

    cr_2008 = pd.read_csv(os.path.join(DATA_DIR, 'crisis_2008_pi.csv'),
                           index_col=0, parse_dates=True)
    stable = cr_2008.loc[:'2007-06-30']

    def extract_plimit(col_raw, col_norm):
        mask = (stable[col_norm] > 0.01) & (stable[col_raw] > 0)
        if mask.any():
            return (stable.loc[mask, col_raw] / stable.loc[mask, col_norm]).median()
        return stable[col_raw].quantile(0.99)

    p_rho = extract_plimit('rho', 'rho_norm')
    p_psi = extract_plimit('psi', 'psi_norm')
    p_omega = extract_plimit('omega', 'omega_norm')

    print(f'\n  2008 P-limits (frozen from 2007 stable period):')
    print(f'    P_rho = {p_rho:.4f}, P_psi = {p_psi:.4f}, P_omega = {p_omega:.4f}')

    def fetch_fred(series_id, start, end):
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
        except Exception as e:
            print(f'    ⚠ Failed to fetch {series_id}: {e}')
        return None

    print(f'\n  Fetching SVB-era data from FRED...')

    dff = fetch_fred('DFF', '2022-01-01', '2023-06-30')
    ted = fetch_fred('TEDRATE', '2022-01-01', '2023-06-30')
    bkcr = fetch_fred('TOTBKCR', '2022-01-01', '2023-06-30')

    if dff is None or ted is None or bkcr is None:
        print('  ⚠ Failed to fetch required series.')
        return None

    print(f'    DFF:  {len(dff)} pts')
    print(f'    TED:  {len(ted)} pts')
    print(f'    BKCR: {len(bkcr)} pts')

    common = dff.index.intersection(ted.index).intersection(bkcr.index)
    rho = dff.reindex(common)
    psi = ted.reindex(common)
    omega = bkcr.reindex(common).pct_change().abs()

    rho_n = (rho / p_rho).clip(lower=0)
    psi_n = (psi / p_psi).clip(lower=0)
    omega_n = (omega / p_omega).clip(lower=0)

    dt = 1.0 / 365
    stress = rho_n * psi_n * omega_n

    crisis_mask = common >= '2022-07-01'
    control_mask = common < '2022-07-01'

    pi_cr = (stress[crisis_mask] * dt).sum()
    pi_ct = (stress[control_mask] * dt).sum()
    sep = pi_cr / pi_ct if pi_ct > 0 else float('inf')

    print(f'\n  Results:')
    print(f'    Π (crisis,  2022-07 ~ 2023-06): {pi_cr:.6f}')
    print(f'    Π (control, 2022-01 ~ 2022-06): {pi_ct:.6f}')
    print(f'    Separation ratio: {sep:.1f}x')

    if sep > 1.5:
        print(f'\n  ✅ OUT-OF-SAMPLE PASS: {sep:.1f}x separation without re-calibration')
    else:
        print(f'\n  ⚠ OUT-OF-SAMPLE RESULT: {sep:.1f}x separation')
        print(f'    SVB was quickly contained (unlike 2008 systemic collapse)')

    return {'pi_cr': pi_cr, 'pi_ct': pi_ct, 'sep': sep}


# ================================================================
# SUPPLEMENTARY TEST S1: P-LIMIT SCALE-INVARIANCE DIAGNOSTIC
# ================================================================

def run_plimit_sensitivity():
    print(f'\n\n{"=" * 75}')
    print('  SUPPLEMENTARY S1: P-limit Scale-Invariance Diagnostic')
    print('=' * 75)
    print('  Note: This is an algebraic diagnostic, not independent empirical')
    print('  robustness evidence. Common P-limit factors cancel in the')
    print('  crisis/control separation ratio.')
    print('  P-limits in this diagnostic are estimated from the control period,')
    print('  whereas the main analysis uses each case\'s predefined stable period.')

    percentiles = [95, 97.5, 99, 99.5]
    rows = []

    for case_name, info in CASES.items():
        cr, ct = load_case(case_name)
        dt_cr, dt_ct = estimate_dt(cr), estimate_dt(ct)

        for pct in percentiles:
            pl = {v: max(np.percentile(ct[v].dropna(), pct), 1e-10)
                  for v in ['rho', 'psi', 'omega']}
            pi_cr = ((cr['rho']/pl['rho'] * cr['psi']/pl['psi'] *
                      cr['omega']/pl['omega']) * dt_cr).sum()
            pi_ct = ((ct['rho']/pl['rho'] * ct['psi']/pl['psi'] *
                      ct['omega']/pl['omega']) * dt_ct).sum()
            sep = pi_cr / pi_ct if pi_ct > 0 else float('inf')
            rows.append({'Case': case_name, 'Percentile': f'P{pct}',
                         'Separation': round(sep, 1)})

    df = pd.DataFrame(rows)
    pivot = df.pivot(index='Case', columns='Percentile', values='Separation')
    print(pivot.to_string())
    df.to_csv(os.path.join(OUT_DIR, 'table_S1_plimit_sensitivity.csv'), index=False)
    print(f'  Saved: table_S1_plimit_sensitivity.csv')
    return df


# ================================================================
# SUPPLEMENTARY TEST S2: VARIABLE PERTURBATION (2008)
# ================================================================

def run_variable_perturbation():
    print(f'\n\n{"=" * 75}')
    print('  SUPPLEMENTARY S2: Variable Perturbation (2008)')
    print('=' * 75)

    cr8, ct8 = load_case('2008 Financial')
    dt8, dtc8 = estimate_dt(cr8), estimate_dt(ct8)
    base_sep = (cr8['stress']*dt8).sum() / (ct8['stress']*dtc8).sum()

    np.random.seed(42)
    rows = []
    for noise in [10, 20, 30, 50]:
        for var in ['rho_norm', 'psi_norm', 'omega_norm']:
            cp, tp = cr8.copy(), ct8.copy()
            cp[var] = (cp[var] + np.random.normal(
                0, cr8[var].std()*noise/100, len(cr8))).clip(0)
            tp[var] = (tp[var] + np.random.normal(
                0, ct8[var].std()*noise/100, len(ct8))).clip(0)
            sc = (cp['rho_norm']*cp['psi_norm']*cp['omega_norm']*dt8).sum()
            st = (tp['rho_norm']*tp['psi_norm']*tp['omega_norm']*dtc8).sum()
            sep = sc/st if st > 0 else float('inf')
            label = {'rho_norm': 'ρ (Fed Funds Rate)',
                     'psi_norm': 'Ψ (TED Spread)',
                     'omega_norm': 'Ω (Bank Credit)'}[var]
            rows.append({'Perturbed_Variable': label,
                         'Noise_Level': f'{noise}%',
                         'Separation': round(sep, 1),
                         'Pct_Change': f'{(sep/base_sep-1)*100:+.1f}%'})
            print(f'  {noise}% noise on {label}: {sep:.1f}× ({(sep/base_sep-1)*100:+.1f}%)')

    pd.DataFrame(rows).to_csv(
        os.path.join(OUT_DIR, 'table_S2_variable_robustness.csv'), index=False)
    print(f'  Saved: table_S2_variable_robustness.csv')
    return rows


# ================================================================
# SUPPLEMENTARY TEST S4: NON-REDUNDANCY
# ================================================================

def run_nonredundancy():
    print(f'\n\n{"=" * 75}')
    print('  SUPPLEMENTARY S4: Non-Redundancy (Pairwise Correlations)')
    print('=' * 75)

    rows = []
    for case_name in CASES:
        _, ct = load_case(case_name)
        rp = ct['rho_norm'].corr(ct['psi_norm'])
        ro = ct['rho_norm'].corr(ct['omega_norm'])
        po = ct['psi_norm'].corr(ct['omega_norm'])
        mx = max(abs(rp), abs(ro), abs(po))
        rows.append({'Case': case_name,
                     'r(rho,psi)': round(rp, 3),
                     'r(rho,omega)': round(ro, 3),
                     'r(psi,omega)': round(po, 3),
                     'max|r|': round(mx, 3),
                     'Pass(<0.7)': 'Yes' if mx < 0.7 else 'No'})
        status = '✅' if mx < 0.7 else '⚠️'
        print(f'  {case_name:<18} max|r| = {mx:.3f} {status}')

    pd.DataFrame(rows).to_csv(
        os.path.join(OUT_DIR, 'table_S4_nonredundancy.csv'), index=False)
    print(f'  Saved: table_S4_nonredundancy.csv')
    return rows


# ================================================================
# PUBLICATION FIGURES (optional, needs matplotlib)
# ================================================================

def generate_figures():
    print(f'\n\n{"=" * 75}')
    print('  GENERATING PUBLICATION FIGURES (300 dpi)')
    print('=' * 75)

    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        import matplotlib.ticker as mticker
    except ImportError:
        print('  ⚠ matplotlib not installed. Skipping figures.')
        print('  Install with: pip install matplotlib')
        return

    fig_dir = os.path.join(OUT_DIR, 'figures')
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
        dt_cr, dt_ct = estimate_dt(cr), estimate_dt(ct)
        ax.plot(cr.index, cum_pi(cr, dt_cr), color=C['crisis'], lw=1.2, label='Crisis')
        ax.plot(ct.index, cum_pi(ct, dt_ct), color=C['control'], lw=1.2, label='Control')
        collapse = collapse_dates[name]
        if cr.index[0] <= collapse <= cr.index[-1]:
            ax.axvline(collapse, color='#2c3e50', linestyle='--', linewidth=0.8,
                       alpha=0.7, label='Collapse date')
        ax.set_ylabel('Π(t)')
        ax.set_title(label, fontsize=FS+1, fontweight='bold', loc='left')
        ax.text(-0.08, 1.05, chr(97+i), transform=ax.transAxes,
                fontsize=PL, fontweight='bold', va='top')
        if i == 0:
            ax.legend(loc='upper left', frameon=False)
        ax.xaxis.set_major_locator(mticker.MaxNLocator(6))
        for t in ax.get_xticklabels():
            t.set_rotation(30); t.set_ha('right')
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
    print('  Figure 4: Permutation tests...')
    fig, axes = plt.subplots(1, 5, figsize=(7.08, 2.5), constrained_layout=True)
    for i, name in enumerate(cases_list):
        ax = axes[i]; cr, _ = load_case(name); dt_cr = estimate_dt(cr)
        pi_actual = (cr['stress'] * dt_cr).sum()
        np.random.seed(42)
        pi_null = np.array([
            (cr['rho_norm'].sample(frac=1).values *
             cr['psi_norm'].sample(frac=1).values *
             cr['omega_norm'].sample(frac=1).values * dt_cr).sum()
            for _ in range(10000)])
        ax.hist(pi_null, bins=50, color='#BBDEFB', edgecolor='white',
                lw=0.3, density=True, zorder=2)
        ax.axvline(pi_actual, color=C['crisis'], lw=1.5, zorder=3)
        p = (pi_null >= pi_actual).mean()
        z = ((pi_actual - pi_null.mean()) / pi_null.std()
             if pi_null.std() > 0 else 0)
        ax.set_title(name, fontsize=FS, fontweight='bold')
        ax.text(0.95, 0.95,
                f'z={z:.1f}\np={"<0.001" if p < 0.001 else f"{p:.3f}"}',
                transform=ax.transAxes, ha='right', va='top', fontsize=FS-2,
                bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))
        if i == 0: ax.set_ylabel('Density')
        ax.set_xlabel('Π_null')
        ax.text(-0.15, 1.08, chr(97+i), transform=ax.transAxes,
                fontsize=PL, fontweight='bold', va='top')
    fig.savefig(os.path.join(fig_dir, 'Figure4_permutation_tests.png'), dpi=DPI)
    fig.savefig(os.path.join(fig_dir, 'Figure4_permutation_tests.pdf'))
    plt.close(fig); print('    ✅')

    # ── FIGURE 5: Failure modes ──
    print('  Figure 5: Failure modes...')
    fig, axes = plt.subplots(1, 5, figsize=(7.08, 2.5), constrained_layout=True)
    mc = {'Ductile': '#1976D2', 'Brittle': '#D32F2F', 'Pre-loaded': '#FF9800'}
    for i, name in enumerate(cases_list):
        ax = axes[i]; cr, _ = load_case(name); dt_cr = estimate_dt(cr)
        pi_cum = cum_pi(cr, dt_cr)
        pi_norm = pi_cum / pi_cum.max()
        days = (cr.index - cr.index[0]).days
        mode = t4[t4['name'] == name]['mode'].values[0]
        pct = t4[t4['name'] == name]['pct_of_max'].values[0]
        color = mc.get(mode, 'grey')
        ax.fill_between(days, 0, pi_norm, alpha=0.3, color=color, zorder=2)
        ax.plot(days, pi_norm, color=color, lw=1.2, zorder=3)
        ax.axhline(0.1, color='grey', ls=':', lw=0.8, alpha=0.7)
        ax.set_title(f'{name}\n({mode})', fontsize=FS, fontweight='bold', color=color)
        ax.text(0.95, 0.55, f'{pct:.0f}%\n@collapse', transform=ax.transAxes,
                ha='right', va='center', fontsize=FS-2, color=color, fontweight='bold')
        if i == 0: ax.set_ylabel('Π(t) / Π_max')
        ax.set_xlabel('Days'); ax.set_ylim(0, 1.05)
        ax.text(-0.15, 1.12, chr(97+i), transform=ax.transAxes,
                fontsize=PL, fontweight='bold', va='top')
    fig.savefig(os.path.join(fig_dir, 'Figure5_failure_modes.png'), dpi=DPI)
    fig.savefig(os.path.join(fig_dir, 'Figure5_failure_modes.pdf'))
    plt.close(fig); print('    ✅')

    # ── FIGURE 6: Sensitivity Diagnostics ──
    print('  Figure 6: Sensitivity Diagnostics...')
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.08, 3.0), constrained_layout=True)

    s1_path = os.path.join(OUT_DIR, 'table_S1_plimit_sensitivity.csv')
    if os.path.exists(s1_path):
        s1 = pd.read_csv(s1_path)
        pct_colors = ['#E3F2FD', '#90CAF9', '#42A5F5', '#1565C0']
        x = np.arange(5); w = 0.18
        for j, pct in enumerate(['P95', 'P97.5', 'P99', 'P99.5']):
            vals = [s1[(s1['Case']==c) & (s1['Percentile']==pct)]['Separation'].values[0]
                    for c in cases_list]
            ax1.bar(x + j*w - 1.5*w, vals, w, label=pct,
                    color=pct_colors[j], edgecolor='white', zorder=3)
        ax1.set_xticks(x)
        ax1.set_xticklabels([c.replace(' ', '\n') for c in cases_list], fontsize=FS-2)
        ax1.set_ylabel('Separation Ratio (×)')
        ax1.set_yscale('log'); ax1.set_ylim(1, 10000)
        ax1.legend(frameon=False, fontsize=FS-2, ncol=2)
        ax1.set_title('P-limit Sensitivity', fontsize=FS+1, fontweight='bold')
        ax1.grid(axis='y', alpha=0.3, zorder=0)
    else:
        ax1.text(0.5, 0.5, 'Run with --all first', transform=ax1.transAxes, ha='center')
    ax1.text(-0.12, 1.05, 'a', transform=ax1.transAxes,
             fontsize=PL, fontweight='bold', va='top')

    s2_path = os.path.join(OUT_DIR, 'table_S2_variable_robustness.csv')
    if os.path.exists(s2_path):
        s2 = pd.read_csv(s2_path)
        vc = ['#EF5350', '#FFA726', '#66BB6A']
        vn = ['ρ (Fed Funds Rate)', 'Ψ (TED Spread)', 'Ω (Bank Credit)']
        vl = ['ρ (Fed Funds)', 'Ψ (TED Spread)', 'Ω (Bank Credit)']
        x2 = np.arange(4); w2 = 0.22
        for j, (n, l) in enumerate(zip(vn, vl)):
            vals = s2[s2['Perturbed_Variable']==n]['Separation'].values
            ax2.bar(x2 + j*w2 - w2, vals, w2, label=l,
                    color=vc[j], edgecolor='white', zorder=3)
        ax2.axhline(18.6, color='grey', ls='--', lw=1, alpha=0.7, label='Baseline (18.6×)')
        ax2.set_xticks(x2); ax2.set_xticklabels(['10%', '20%', '30%', '50%'])
        ax2.set_xlabel('Noise Level (% of σ)')
        ax2.set_ylabel('Separation Ratio (×)')
        ax2.set_ylim(17, 20)
        ax2.legend(frameon=False, fontsize=FS-2, ncol=2)
        ax2.set_title('Variable Perturbation (2008)', fontsize=FS+1, fontweight='bold')
        ax2.grid(axis='y', alpha=0.3, zorder=0)
    else:
        ax2.text(0.5, 0.5, 'Run with --all first', transform=ax2.transAxes, ha='center')
    ax2.text(-0.12, 1.05, 'b', transform=ax2.transAxes,
             fontsize=PL, fontweight='bold', va='top')

    fig.savefig(os.path.join(fig_dir, 'Figure6_robustness.png'), dpi=DPI)
    fig.savefig(os.path.join(fig_dir, 'Figure6_robustness.pdf'))
    plt.close(fig); print('    ✅')

    print(f'\n  All figures saved to {fig_dir}/')
    for f in sorted(os.listdir(fig_dir)):
        sz = os.path.getsize(os.path.join(fig_dir, f)) / 1024
        print(f'    {f}  ({sz:.0f} KB)')


# ================================================================
# MAIN
# ================================================================

def main():
    parser = argparse.ArgumentParser(description='Pi Framework Unified Analysis')
    parser.add_argument('--svb', action='store_true',
                        help='Include SVB out-of-sample test (needs FRED_API_KEY)')
    parser.add_argument('--figures', action='store_true',
                        help='Generate publication figures (needs matplotlib)')
    parser.add_argument('--all', action='store_true',
                        help='Run everything: core + supplementary + figures')
    args = parser.parse_args()

    if args.all:
        args.figures = True

    os.makedirs(OUT_DIR, exist_ok=True)

    print()
    print('╔' + '═' * 73 + '╗')
    print('║  Π STRUCTURAL STABILITY INDEX — UNIFIED ANALYSIS                       ║')
    print('║  Cross-Case Retrospective Characterization + Statistical Tests         ║')
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

    # ── Core analyses ──
    r1 = run_cross_domain()
    r2 = run_mult_vs_add()
    r3 = run_permutation_test()
    r4 = run_failure_modes()

    r5 = None
    if args.svb:
        r5 = run_svb_oos()

    # ── Supplementary tests ──
    run_plimit_sensitivity()
    run_variable_perturbation()
    run_nonredundancy()

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
            'Case': name, 'N': r['n'],
            'Pi_actual': round(r['actual_pi'], 6),
            'Pi_shuffled_mean': round(r['mean_shuffled'], 6),
            'z_score': round(r['z_score'], 2),
            'p_value': r['p_value'] if r['p_value'] > 0 else f'<{1/N_PERM:.0e}',
            'Significant': 'Yes' if r['p_value'] < 0.05 else 'No',
        })
    pd.DataFrame(rows3).to_csv(os.path.join(OUT_DIR, 'table3_permutation.csv'), index=False)

    df4 = pd.DataFrame(r4)
    df4.to_csv(os.path.join(OUT_DIR, 'table4_failure_modes.csv'), index=False)

    # ── Figures ──
    if args.figures:
        generate_figures()


    # ── Transform-window sensitivity analysis (FRED_API_KEY required) ──
    repo_root = os.path.dirname(os.path.abspath(__file__))
    fred_api_key = os.environ.get('FRED_API_KEY', '')

    # The matched-pipeline script is retained in the repository for audit
    # reproducibility but is intentionally excluded from the revised
    # manuscript's default evidentiary pipeline.
    sensitivity_jobs = [
        (
            'ST15',
            os.path.join(repo_root, 'sensitivity', 'sensitivity_delta_k.py'),
            'Transform window sensitivity (k = 1,3,5,10,20)',
            'table_ST15_delta_k_sensitivity.csv',
        ),
    ]

    if any(os.path.exists(script) for _, script, _, _ in sensitivity_jobs):
        print(f'\n\n{"━" * 74}')
        print('  TRANSFORM-WINDOW SENSITIVITY ANALYSIS')
        print(f'{"━" * 74}')

    for label, script, description, output_name in sensitivity_jobs:
        if not os.path.exists(script):
            continue

        print(f'\n  [{label}] {description}...')

        if not fred_api_key:
            print('    Skipped (FRED_API_KEY not set)')
            continue

        expected_output = os.path.join(repo_root, 'output', output_name)
        before_mtime_ns = (
            os.stat(expected_output).st_mtime_ns
            if os.path.exists(expected_output)
            else None
        )

        try:
            res = subprocess.run(
                [sys.executable, script],
                capture_output=True,
                text=True,
                timeout=300,
                env={**os.environ},
            )

            output_exists = os.path.exists(expected_output)
            after_mtime_ns = (
                os.stat(expected_output).st_mtime_ns
                if output_exists
                else None
            )
            output_refreshed = output_exists and (
                before_mtime_ns is None
                or after_mtime_ns != before_mtime_ns
            )

            if res.returncode == 0 and output_refreshed:
                print(f'    Done → output/{output_name}')
            elif res.returncode == 0:
                print(f'    Failed ({output_name} was not newly created or refreshed)')
                message = res.stdout.strip().split('\n')[-1] if res.stdout else ''
                if message:
                    print(f'    {message[:200]}')
            else:
                print(f'    Skipped (exit {res.returncode})')
                message = res.stderr.strip().split('\n')[-1] if res.stderr else ''
                if not message and res.stdout:
                    message = res.stdout.strip().split('\n')[-1]
                if message:
                    print(f'    {message[:200]}')
        except subprocess.TimeoutExpired:
            print('    Skipped (timeout >300s)')
        except Exception as exc:
            print(f'    Skipped ({exc})')

    # ── Final summary ──
    passed = sum(1 for r in r1 if r['separation'] > 1.5)
    mult_wins = sum(1 for r in r2
                    if r['mult']['sep'] >= r['add']['sep']
                    and r['mult']['sep'] >= r['max']['sep'])
    sig_count = sum(1 for r in r3.values() if r['p_value'] < 0.05)

    p_values = [max(r['p_value'], 1/N_PERM) for r in r3.values()]
    chi2 = -2 * sum(np.log(p) for p in p_values)
    fisher_p = 1 - scipy_stats.chi2.cdf(chi2, df=2*len(p_values))

    print(f'\n\n{"╔" + "═" * 73 + "╗"}')
    print(f'{"║  FINAL SUMMARY":<74}{"║"}')
    print(f'{"╚" + "═" * 73 + "╝"}')
    print(f'  1. Cumulative contrast: {passed}/5 selected crisis windows > controls')
    print(f'  2. Three-formulation comparison: multiplicative highest in {mult_wins}/5')
    print(f'  3. Permutation test: {sig_count}/5 significant (p < 0.05)')
    print(f'  4. Exploratory patterns: three labels assigned')
    if r5:
        print(f'  5. SVB out-of-sample: {r5["sep"]:.1f}x separation')
    print(f'\n  Fisher combined p-value: {fisher_p:.2e}')
    print('  Retrospective characterization completed for five selected cases')

    # Summary text
    with open(os.path.join(OUT_DIR, 'summary.txt'), 'w') as f:
        f.write('Pi Framework — Retrospective Cross-Case Results\n')
        f.write('=' * 50 + '\n\n')
        f.write(f'1. Cumulative contrast: {passed}/5 selected crisis windows > controls\n')
        f.write(f'2. Three-formulation comparison: multiplicative highest in {mult_wins}/5\n')
        f.write(f'3. Permutation test: {sig_count}/5 significant (p < 0.05)\n')
        f.write('4. Exploratory patterns: three labels assigned\n')
        if r5:
            f.write(f'5. SVB out-of-sample: {r5["sep"]:.1f}x separation\n')
        f.write(f'\nFisher combined p-value: {fisher_p:.2e}\n')
        f.write('Interpretation: retrospective characterization of five selected cases; not universal validation or prospective prediction.\n')
        f.write(f'\nSupplementary: S1 (P-limit), S2 (Perturbation), S4 (Non-redundancy)\n')
        f.write('Sensitivity: Transform-window analysis retained; matched-pipeline analysis excluded from the revised evidentiary package and retained only for audit reproducibility.\n')
        if args.figures:
            f.write(f'Figures: 6 publication figures (300 dpi PNG + PDF)\n')

    print(f'\n  Results saved to {OUT_DIR}/')
    print()


if __name__ == '__main__':
    main()
