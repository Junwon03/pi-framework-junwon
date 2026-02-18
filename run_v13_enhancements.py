"""
Pi Framework — v13 Enhancements
================================
Two new analyses to complete NatComms preparation:
  1. Sliding-window controls with FIXED SHORT windows (180-day / 6-month)
     → Multiple control Π values, effect size (Cohen's d), 95% CI
  2. Block permutation test (preserves autocorrelation)
     → Validates that independent-shuffle p-values are not inflated

Usage:
  python run_v13_enhancements.py

Outputs to output/ folder.
"""

import pandas as pd
import numpy as np
import os
import sys
from scipy import stats as scipy_stats

# ================================================================
# CONFIG (same as run_all.py)
# ================================================================

_base = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(_base, 'data')
if not os.path.exists(DATA_DIR):
    DATA_DIR = os.path.join(_base, 'Data')

OUT_DIR = os.path.join(_base, 'output')
os.makedirs(OUT_DIR, exist_ok=True)

CASES = {
    '2008 Financial': {
        'crisis': 'crisis_2008_pi.csv',
        'control': 'control_2004_2006_pi.csv',
        'domain': 'Traditional Finance',
        'collapse': '2008-09-15',
        'freq': 'daily',
    },
    'Terra-Luna': {
        'crisis': 'crisis_terra_luna_pi.csv',
        'control': 'control_terra_luna_pi.csv',
        'domain': 'Digital Assets',
        'collapse': '2022-05-09',
        'freq': 'daily',
    },
    'Fukushima': {
        'crisis': 'crisis_fukushima_pi.csv',
        'control': 'control_fukushima_pi.csv',
        'domain': 'Physical Infrastructure',
        'collapse': '2011-03-11',
        'freq': 'daily',
    },
    'COVID-19': {
        'crisis': 'crisis_covid_pi.csv',
        'control': 'control_covid_pi.csv',
        'domain': 'Pandemic / Public Health',
        'collapse': '2020-03-23',
        'freq': 'daily',
    },
    'Supply Chain': {
        'crisis': 'crisis_supply_chain_pi.csv',
        'control': 'control_supply_chain_pi.csv',
        'domain': 'Global Logistics',
        'collapse': '2021-10-01',
        'freq': 'monthly',
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
# ENHANCEMENT 1: SLIDING-WINDOW CONTROLS (FIXED SHORT WINDOWS)
# ================================================================

def run_sliding_controls():
    """
    Use FIXED SHORT windows from the control period to generate
    multiple control Π values.
    
    Daily cases: 180-day windows, sliding every 30 days
    Monthly case (Supply Chain): 6-month windows, sliding every 2 months
    
    For each window, compute Π and S̄=Π/T.
    Then compute:
      - Effect size (Cohen's d) = (crisis_metric - mean_ctrl) / std_ctrl
      - 95% CI of separation ratio from control distribution
    """
    print('=' * 75)
    print('  ENHANCEMENT 1: Sliding-Window Controls (Fixed Short Windows)')
    print('  Daily: 180-day windows / Monthly: 6-month windows')
    print('=' * 75)

    all_results = []

    for name, info in CASES.items():
        cr, ct = load_case(name)
        dt_cr = estimate_dt(cr)
        dt_ct = estimate_dt(ct)

        needed = ['rho_norm', 'psi_norm', 'omega_norm']
        if not all(c in ct.columns for c in needed):
            print(f'  {name}: Missing norm columns, skipping')
            continue

        # Crisis Π and S̄
        pi_crisis = (cr['stress'] * dt_cr).sum()
        T_crisis = len(cr) * dt_cr
        sbar_crisis = pi_crisis / T_crisis if T_crisis > 0 else 0

        # Fixed window size
        if info['freq'] == 'monthly':
            win_size = 6    # 6 months
            step = 2        # slide every 2 months
        else:
            win_size = 180  # 180 days
            step = 30       # slide every 30 days

        control_len = len(ct)

        # Generate sliding windows
        window_pis = []
        window_sbars = []

        for start in range(0, max(1, control_len - win_size + 1), step):
            end = start + win_size
            if end > control_len:
                break
            window = ct.iloc[start:end]
            stress_w = window['rho_norm'] * window['psi_norm'] * window['omega_norm']
            pi_w = (stress_w * dt_ct).sum()
            T_w = len(window) * dt_ct
            sbar_w = pi_w / T_w if T_w > 0 else 0
            window_pis.append(pi_w)
            window_sbars.append(sbar_w)

        n_windows = len(window_pis)

        if n_windows < 2:
            # Not enough control data for sliding windows
            # Use full control as single window
            stress_ct = ct['rho_norm'] * ct['psi_norm'] * ct['omega_norm']
            pi_ct_full = (stress_ct * dt_ct).sum()
            T_ct = len(ct) * dt_ct
            sbar_ct_full = pi_ct_full / T_ct if T_ct > 0 else 0

            result = {
                'Case': name,
                'Window_size': win_size,
                'N_windows': 1,
                'Pi_crisis': round(pi_crisis, 6),
                'Sbar_crisis': round(sbar_crisis, 6),
                'Pi_ctrl_mean': round(pi_ct_full, 6),
                'Pi_ctrl_std': 'N/A',
                'Sbar_ctrl_mean': round(sbar_ct_full, 6),
                'Sbar_ctrl_std': 'N/A',
                'Sep_Pi_mean': round(pi_crisis / pi_ct_full if pi_ct_full > 0 else float('inf'), 1),
                'Sep_Pi_95CI_lo': 'N/A',
                'Sep_Pi_95CI_hi': 'N/A',
                'Sep_Sbar_mean': round(sbar_crisis / sbar_ct_full if sbar_ct_full > 0 else float('inf'), 1),
                'Cohen_d_Pi': 'N/A',
                'Cohen_d_Sbar': 'N/A',
                'Note': 'Control shorter than window; single control used',
            }
            all_results.append(result)
            print(f'\n  {name}: Control too short for {win_size}-unit windows (N_ctrl={control_len})')
            print(f'    Using full control: Sep(Π)={result["Sep_Pi_mean"]}×, Sep(S̄)={result["Sep_Sbar_mean"]}×')
            continue

        # Statistics
        mean_pi = np.mean(window_pis)
        std_pi = np.std(window_pis, ddof=1)
        mean_sbar = np.mean(window_sbars)
        std_sbar = np.std(window_sbars, ddof=1)

        # Separation ratios for each window
        seps_pi = [pi_crisis / w if w > 0 else float('inf') for w in window_pis]
        seps_sbar = [sbar_crisis / w if w > 0 else float('inf') for w in window_sbars]

        # 95% CI of separation (from distribution of window separations)
        sep_pi_lo = np.percentile(seps_pi, 2.5)
        sep_pi_hi = np.percentile(seps_pi, 97.5)

        # Cohen's d
        d_pi = (pi_crisis - mean_pi) / std_pi if std_pi > 0 else float('inf')
        d_sbar = (sbar_crisis - mean_sbar) / std_sbar if std_sbar > 0 else float('inf')

        result = {
            'Case': name,
            'Window_size': win_size,
            'N_windows': n_windows,
            'Pi_crisis': round(pi_crisis, 6),
            'Sbar_crisis': round(sbar_crisis, 6),
            'Pi_ctrl_mean': round(mean_pi, 6),
            'Pi_ctrl_std': round(std_pi, 6),
            'Sbar_ctrl_mean': round(mean_sbar, 6),
            'Sbar_ctrl_std': round(std_sbar, 6),
            'Sep_Pi_mean': round(np.mean(seps_pi), 1),
            'Sep_Pi_95CI_lo': round(sep_pi_lo, 1),
            'Sep_Pi_95CI_hi': round(sep_pi_hi, 1),
            'Sep_Sbar_mean': round(np.mean(seps_sbar), 1),
            'Cohen_d_Pi': round(d_pi, 2),
            'Cohen_d_Sbar': round(d_sbar, 2),
            'Note': '',
        }
        all_results.append(result)

        print(f'\n  {name} ({n_windows} windows of {win_size} units):')
        print(f'    Π_crisis = {pi_crisis:.6f}')
        print(f'    Π_ctrl = {mean_pi:.6f} ± {std_pi:.6f}')
        print(f'    Sep(Π): mean={np.mean(seps_pi):.1f}× [95%CI: {sep_pi_lo:.1f}×–{sep_pi_hi:.1f}×]')
        print(f'    Sep(S̄): mean={np.mean(seps_sbar):.1f}×')
        print(f'    Cohen d(Π)={d_pi:.2f}, d(S̄)={d_sbar:.2f}')

    df = pd.DataFrame(all_results)
    df.to_csv(os.path.join(OUT_DIR, 'table_v13_sliding_controls.csv'), index=False)
    print(f'\n  Saved: table_v13_sliding_controls.csv')
    return all_results


# ================================================================
# ENHANCEMENT 2: BLOCK PERMUTATION TEST
# ================================================================

def run_block_permutation():
    """
    Block permutation preserves within-block temporal structure.
    Instead of shuffling individual time points, we:
      1. Divide each channel into blocks of size B
      2. Shuffle the blocks (not individual points)
      3. This preserves short-range autocorrelation while destroying
         cross-channel temporal alignment
    
    Block sizes tested: B = 5, 10, 20 days (1, 2, 4 months for Supply Chain)
    Compare resulting p-values with independent shuffle p-values.
    """
    print(f'\n\n{"=" * 75}')
    print(f'  ENHANCEMENT 2: Block Permutation Test (N = {N_PERM:,})')
    print(f'  Preserves within-block autocorrelation')
    print('=' * 75)

    # Block sizes for daily and monthly
    block_sizes_daily = [5, 10, 20]
    block_sizes_monthly = [2, 3, 4]

    all_results = []

    for name, info in CASES.items():
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

        # Independent shuffle (baseline, same as run_all.py)
        shuffled_indep = np.zeros(N_PERM)
        for i in range(N_PERM):
            r_s = rho[np.random.permutation(n)]
            p_s = psi[np.random.permutation(n)]
            o_s = omega[np.random.permutation(n)]
            shuffled_indep[i] = np.sum(r_s * p_s * o_s) * dt

        p_indep = np.mean(shuffled_indep >= actual_pi)
        z_indep = (actual_pi - np.mean(shuffled_indep)) / np.std(shuffled_indep) if np.std(shuffled_indep) > 0 else float('inf')

        block_sizes = block_sizes_monthly if info['freq'] == 'monthly' else block_sizes_daily

        print(f'\n  {name} (n={n}):')
        print(f'    Independent shuffle: z={z_indep:.2f}, p={p_indep:.4f}' if p_indep > 0 else f'    Independent shuffle: z={z_indep:.2f}, p<{1/N_PERM:.0e}')

        for B in block_sizes:
            if B >= n:
                continue

            # Create block indices
            n_blocks = n // B
            remainder = n % B

            shuffled_block = np.zeros(N_PERM)
            for i in range(N_PERM):
                # Shuffle blocks for each channel independently
                def block_shuffle(arr, block_size, n_blk, rem):
                    blocks = [arr[j*block_size:(j+1)*block_size] for j in range(n_blk)]
                    if rem > 0:
                        blocks.append(arr[n_blk*block_size:])
                    perm = np.random.permutation(len(blocks))
                    return np.concatenate([blocks[p] for p in perm])

                r_s = block_shuffle(rho, B, n_blocks, remainder)
                p_s = block_shuffle(psi, B, n_blocks, remainder)
                o_s = block_shuffle(omega, B, n_blocks, remainder)

                shuffled_block[i] = np.sum(r_s * p_s * o_s) * dt

            p_block = np.mean(shuffled_block >= actual_pi)
            z_block = (actual_pi - np.mean(shuffled_block)) / np.std(shuffled_block) if np.std(shuffled_block) > 0 else float('inf')

            p_str = f'{p_block:.4f}' if p_block > 0 else f'<{1/N_PERM:.0e}'
            print(f'    Block B={B}: z={z_block:.2f}, p={p_str}')

            all_results.append({
                'Case': name,
                'N': n,
                'Block_size': B,
                'Method': f'Block B={B}',
                'Actual_Pi': round(actual_pi, 6),
                'Mean_shuffled': round(np.mean(shuffled_block), 6),
                'Std_shuffled': round(np.std(shuffled_block), 6),
                'z_score': round(z_block, 2),
                'p_value': round(p_block, 4) if p_block > 0 else 0,
                'p_display': p_str,
                'Significant_005': 'Yes' if p_block < 0.05 else 'No',
                'Significant_001': 'Yes' if p_block < 0.001 else 'No',
            })

        # Also add independent shuffle result for comparison
        p_str_indep = f'{p_indep:.4f}' if p_indep > 0 else f'<{1/N_PERM:.0e}'
        all_results.append({
            'Case': name,
            'N': n,
            'Block_size': 1,
            'Method': 'Independent',
            'Actual_Pi': round(actual_pi, 6),
            'Mean_shuffled': round(np.mean(shuffled_indep), 6),
            'Std_shuffled': round(np.std(shuffled_indep), 6),
            'z_score': round(z_indep, 2),
            'p_value': round(p_indep, 4) if p_indep > 0 else 0,
            'p_display': p_str_indep,
            'Significant_005': 'Yes' if p_indep < 0.05 else 'No',
            'Significant_001': 'Yes' if p_indep < 0.001 else 'No',
        })

    df = pd.DataFrame(all_results)
    df.to_csv(os.path.join(OUT_DIR, 'table_v13_block_permutation.csv'), index=False)

    # Summary table: compare independent vs block for each case
    print(f'\n  {"─"*75}')
    print(f'  Summary: Independent vs Block Permutation')
    print(f'  {"─"*75}')
    print(f'  {"Case":<18} {"Indep z":<10} {"B=5 z":<10} {"B=10 z":<10} {"B=20 z":<10} {"Conclusion":<15}')
    print(f'  {"─"*75}')

    for name in CASES:
        sub = df[df['Case'] == name]
        indep = sub[sub['Method'] == 'Independent']
        z_ind = indep['z_score'].values[0] if len(indep) > 0 else 'N/A'

        block_sizes = block_sizes_monthly if CASES[name]['freq'] == 'monthly' else block_sizes_daily
        z_blocks = []
        for B in block_sizes:
            row = sub[sub['Method'] == f'Block B={B}']
            z_blocks.append(str(row['z_score'].values[0]) if len(row) > 0 else 'N/A')

        # Pad to 3 entries
        while len(z_blocks) < 3:
            z_blocks.append('N/A')

        # Conclusion: if all block z > 1.96, results hold
        all_sig = all(
            sub[(sub['Method'].str.startswith('Block'))]['Significant_005'].values == 'Yes'
        ) if len(sub[sub['Method'].str.startswith('Block')]) > 0 else False

        conclusion = 'Robust' if all_sig else 'Weakened'
        print(f'  {name:<18} {z_ind:<10} {z_blocks[0]:<10} {z_blocks[1]:<10} {z_blocks[2]:<10} {conclusion:<15}')

    print(f'\n  Saved: table_v13_block_permutation.csv')
    return df


# ================================================================
# MAIN
# ================================================================

def main():
    print()
    print('╔' + '═' * 73 + '╗')
    print('║  Π FRAMEWORK — v13 ENHANCEMENTS                                       ║')
    print('║  Sliding controls (fixed window) + Block permutation                   ║')
    print('╚' + '═' * 73 + '╝')
    print(f'  Data directory: {DATA_DIR}')
    print(f'  Permutations: {N_PERM:,}')

    # Check data
    missing = []
    for name, info in CASES.items():
        for key in ['crisis', 'control']:
            path = os.path.join(DATA_DIR, info[key])
            if not os.path.exists(path):
                missing.append(f'{name}/{key}')
    if missing:
        print(f'\n  ❌ Missing: {missing}')
        sys.exit(1)

    print(f'  All data files found ✅\n')

    r1 = run_sliding_controls()
    r2 = run_block_permutation()

    print(f'\n\n{"="*75}')
    print('  v13 ENHANCEMENT SUMMARY')
    print(f'{"="*75}')
    print(f'  1. Sliding controls: fixed-window distributions computed')
    print(f'  2. Block permutation: autocorrelation-preserving p-values computed')
    print(f'\n  Output files:')
    for f in ['table_v13_sliding_controls.csv', 'table_v13_block_permutation.csv']:
        path = os.path.join(OUT_DIR, f)
        if os.path.exists(path):
            sz = os.path.getsize(path)
            print(f'    {f} ({sz} bytes)')
    print()


if __name__ == '__main__':
    main()
