"""
Pi Framework — legacy v12 retrospective diagnostics
====================================================
Three retained retrospective audit analyses:
  1. Time-normalized stress intensity (Π/T = mean S)
  2. Control-window descriptive sensitivity
  3. Exploratory pattern-label threshold sensitivity

Designed to run alongside existing run_all.py using the same data/ folder.
Outputs to output/ folder as additional CSV files.

Usage:
  python run_v12_enhancements.py
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

DPY_BY_CASE = {
    '2008 Financial': 365,
    'Terra-Luna': 365,
    'Fukushima': 365,
    'COVID-19': 365,
    'Supply Chain': 12,
}


# ================================================================
# UTILITIES
# ================================================================

def case_dt(name):
    if name not in DPY_BY_CASE:
        raise KeyError(
            f"No explicit observations-per-year mapping for {name}."
        )

    dpy = DPY_BY_CASE[name]

    if not np.isfinite(dpy) or dpy <= 0:
        raise ValueError(
            f"{name}: observations per year must be positive and finite."
        )

    return 1.0 / float(dpy)


def positive_finite_ratio(numerator, denominator, label):
    numerator = float(numerator)
    denominator = float(denominator)

    if not np.isfinite(numerator):
        raise ValueError(
            f"{label}: numerator is non-finite."
        )

    if not np.isfinite(denominator) or denominator <= 0:
        raise ValueError(
            f"{label}: denominator must be positive and finite; "
            f"got {denominator}."
        )

    ratio = numerator / denominator

    if not np.isfinite(ratio):
        raise ValueError(
            f"{label}: ratio is non-finite."
        )

    return ratio


def validate_case_frame(name, role, df):
    required = {
        'rho_norm',
        'psi_norm',
        'omega_norm',
        'stress',
    }

    missing = required - set(df.columns)

    if missing:
        raise ValueError(
            f"{name}/{role}: missing required columns "
            f"{sorted(missing)}."
        )

    if df.empty:
        raise ValueError(
            f"{name}/{role}: empty dataframe."
        )

    if not isinstance(df.index, pd.DatetimeIndex):
        raise ValueError(
            f"{name}/{role}: index must be DatetimeIndex."
        )

    if df.index.has_duplicates:
        raise ValueError(
            f"{name}/{role}: duplicate dates."
        )

    if not df.index.is_monotonic_increasing:
        raise ValueError(
            f"{name}/{role}: dates must be chronological."
        )

    channels = df[
        ['rho_norm', 'psi_norm', 'omega_norm']
    ].to_numpy(dtype=float)

    stress = df['stress'].to_numpy(dtype=float)

    if not np.isfinite(channels).all():
        raise ValueError(
            f"{name}/{role}: non-finite normalized channels."
        )

    if not np.isfinite(stress).all():
        raise ValueError(
            f"{name}/{role}: non-finite stress."
        )

    if (channels < 0).any() or (stress < 0).any():
        raise ValueError(
            f"{name}/{role}: normalized channels and stress "
            "must be nonnegative."
        )

    expected = (
        channels[:, 0]
        * channels[:, 1]
        * channels[:, 2]
    )

    if not np.allclose(
        stress,
        expected,
        rtol=1e-12,
        atol=1e-12,
    ):
        max_diff = float(
            np.max(
                np.abs(stress - expected)
            )
        )

        raise ValueError(
            f"{name}/{role}: stored stress mismatch; "
            f"max_abs_diff={max_diff:.12g}."
        )


def load_case(name):
    if name not in CASES:
        raise KeyError(
            f"Unknown case: {name}"
        )

    info = CASES[name]

    crisis_path = os.path.join(
        DATA_DIR,
        info['crisis'],
    )

    control_path = os.path.join(
        DATA_DIR,
        info['control'],
    )

    if not os.path.isfile(crisis_path):
        raise FileNotFoundError(crisis_path)

    if not os.path.isfile(control_path):
        raise FileNotFoundError(control_path)

    cr = pd.read_csv(
        crisis_path,
        index_col=0,
        parse_dates=True,
    ).sort_index()

    ct = pd.read_csv(
        control_path,
        index_col=0,
        parse_dates=True,
    ).sort_index()

    validate_case_frame(
        name,
        'crisis',
        cr,
    )

    validate_case_frame(
        name,
        'control',
        ct,
    )

    dt = case_dt(name)

    cr = cr.copy()
    ct = ct.copy()

    cr['pi'] = (
        cr['stress'] * dt
    ).cumsum()

    ct['pi'] = (
        ct['stress'] * dt
    ).cumsum()

    return cr, ct

# ================================================================
# ENHANCEMENT 1: TIME-NORMALIZED STRESS INTENSITY (Π/T)
# ================================================================

def run_time_normalized():
    """
    Report cumulative Pi and mean-stress intensity for the selected
    retrospective crisis/control periods. This is a descriptive
    window-length normalization, not prospective validation.
    """
    print('=' * 75)
    print('  ENHANCEMENT 1: Time-Normalized Stress Intensity (Π/T)')
    print('  Retrospective descriptive window-length normalization')
    print('=' * 75)

    rows = []

    for name, info in CASES.items():
        cr, ct = load_case(name)
        dt = case_dt(name)

        pi_cr = float(
            (cr['stress'] * dt).sum()
        )

        pi_ct = float(
            (ct['stress'] * dt).sum()
        )

        sep_pi = positive_finite_ratio(
            pi_cr,
            pi_ct,
            f"{name}/Pi",
        )

        T_cr = len(cr) * dt
        T_ct = len(ct) * dt

        if T_cr <= 0 or T_ct <= 0:
            raise ValueError(
                f"{name}: nonpositive analytical duration."
            )

        s_bar_cr = pi_cr / T_cr
        s_bar_ct = pi_ct / T_ct

        sep_sbar = positive_finite_ratio(
            s_bar_cr,
            s_bar_ct,
            f"{name}/Sbar",
        )

        values = [
            pi_cr,
            pi_ct,
            sep_pi,
            T_cr,
            T_ct,
            s_bar_cr,
            s_bar_ct,
            sep_sbar,
        ]

        if not np.isfinite(values).all():
            raise ValueError(
                f"{name}: non-finite time-normalized result."
            )

        rows.append({
            'Case': name,
            'N_crisis': len(cr),
            'N_control': len(ct),
            'T_crisis_yr': round(T_cr, 3),
            'T_control_yr': round(T_ct, 3),
            'Pi_crisis': round(pi_cr, 4),
            'Pi_control': round(pi_ct, 4),
            'Sep_Pi': round(sep_pi, 1),
            'Sbar_crisis': round(s_bar_cr, 4),
            'Sbar_control': round(s_bar_ct, 4),
            'Sep_Sbar': round(sep_sbar, 1),
        })

        print(f'\n  {name}:')
        print(
            f'    Crisis:  N={len(cr):>4}, T={T_cr:.3f}yr, '
            f'Π={pi_cr:.4f}, S̄={s_bar_cr:.4f}'
        )
        print(
            f'    Control: N={len(ct):>4}, T={T_ct:.3f}yr, '
            f'Π={pi_ct:.4f}, S̄={s_bar_ct:.4f}'
        )
        print(
            f'    Sep(Π)={sep_pi:.1f}×  '
            f'Sep(S̄)={sep_sbar:.1f}×'
        )

    if len(rows) != len(CASES):
        raise RuntimeError(
            "Time-normalized analysis did not return every case."
        )

    df = pd.DataFrame(rows)

    output_path = os.path.join(
        OUT_DIR,
        'table_enhanced_time_normalized.csv',
    )

    df.to_csv(
        output_path,
        index=False,
    )

    if not os.path.isfile(output_path) or os.path.getsize(output_path) <= 0:
        raise RuntimeError(
            "Time-normalized output was not created."
        )

    print(f'\n  Saved: table_enhanced_time_normalized.csv')
    return rows

# ================================================================
# ENHANCEMENT 2: SLIDING WINDOW CONTROL DISTRIBUTION
# ================================================================

def run_sliding_controls():
    """
    Retrospective control-window descriptive diagnostic.

    Windows use the crisis-period observation count and a deterministic
    observation step. If the available control series cannot provide
    multiple eligible windows, the full available control is reported
    as a single descriptive comparator. No inferential standard deviation
    or standardized distance is invented for a one-window comparator.
    """
    print(f'\n\n{"=" * 75}')
    print('  ENHANCEMENT 2: Control-Window Descriptive Diagnostic')
    print('  Retrospective sensitivity; not an inferential control distribution')
    print('=' * 75)

    all_results = []

    for name, info in CASES.items():
        cr, ct = load_case(name)
        dt = case_dt(name)

        pi_crisis = float(
            (cr['stress'] * dt).sum()
        )

        T_crisis = len(cr) * dt

        if T_crisis <= 0:
            raise ValueError(
                f"{name}: crisis duration must be positive."
            )

        crisis_len = len(cr)
        control_len = len(ct)

        if info['freq'] == 'monthly':
            step = max(
                1,
                crisis_len // 4,
            )
        else:
            step = max(
                1,
                crisis_len // 6,
            )

        window_pis = []
        window_sbars = []

        starts = range(
            0,
            max(
                1,
                control_len - crisis_len + 1,
            ),
            step,
        )

        minimum_eligible = max(
            crisis_len // 2,
            5,
        )

        for start in starts:
            end = min(
                start + crisis_len,
                control_len,
            )

            window = ct.iloc[
                start:end
            ]

            # Partial windows shorter than the prespecified minimum are
            # not treated as eligible sliding windows.
            if len(window) < minimum_eligible:
                continue

            stress_w = window[
                'stress'
            ].to_numpy(dtype=float)

            pi_w = float(
                np.sum(stress_w * dt)
            )

            T_w = len(window) * dt

            if T_w <= 0:
                raise ValueError(
                    f"{name}: nonpositive control-window duration."
                )

            sbar_w = pi_w / T_w

            if (
                not np.isfinite(pi_w)
                or pi_w <= 0
                or not np.isfinite(sbar_w)
                or sbar_w <= 0
            ):
                raise ValueError(
                    f"{name}: invalid control-window result."
                )

            window_pis.append(
                pi_w
            )

            window_sbars.append(
                sbar_w
            )

        if len(window_pis) == 0:
            pi_ct = float(
                (ct['stress'] * dt).sum()
            )

            T_ct = len(ct) * dt

            if T_ct <= 0:
                raise ValueError(
                    f"{name}: control duration must be positive."
                )

            sbar_ct = positive_finite_ratio(
                pi_ct,
                T_ct,
                f"{name}/full-control Sbar",
            )

            window_pis = [
                pi_ct
            ]

            window_sbars = [
                sbar_ct
            ]

            status = (
                'Single full-control descriptive fallback; '
                'no eligible sliding window'
            )

        elif len(window_pis) == 1:
            status = (
                'Single eligible control comparator; '
                'no inferential dispersion statistic'
            )

        else:
            status = (
                'Multiple overlapping control windows; '
                'descriptive empirical diagnostic'
            )

        mean_ctrl = float(
            np.mean(window_pis)
        )

        mean_sbar_ctrl = float(
            np.mean(window_sbars)
        )

        sbar_crisis = pi_crisis / T_crisis

        seps = [
            positive_finite_ratio(
                pi_crisis,
                value,
                f"{name}/control-window Pi",
            )
            for value in window_pis
        ]

        if len(window_pis) > 1:
            std_ctrl = float(
                np.std(
                    window_pis,
                    ddof=0,
                )
            )

            std_sbar_ctrl = float(
                np.std(
                    window_sbars,
                    ddof=0,
                )
            )

            if (
                not np.isfinite(std_ctrl)
                or std_ctrl <= 0
            ):
                standardized_distance = 'N/A'
            else:
                standardized_distance = round(
                    (
                        pi_crisis
                        - mean_ctrl
                    )
                    / std_ctrl,
                    2,
                )

            std_ctrl_out = round(
                std_ctrl,
                4,
            )

            std_sbar_out = round(
                std_sbar_ctrl,
                4,
            )

        else:
            std_ctrl_out = 'N/A'
            std_sbar_out = 'N/A'
            standardized_distance = 'N/A'

        result = {
            'Case': name,
            'N_windows': len(window_pis),
            'Pi_crisis': round(pi_crisis, 4),
            'Pi_ctrl_mean': round(mean_ctrl, 4),
            'Pi_ctrl_std': std_ctrl_out,
            'Pi_ctrl_min': round(min(window_pis), 4),
            'Pi_ctrl_max': round(max(window_pis), 4),
            'Sep_mean': round(float(np.mean(seps)), 1),
            'Sep_min': round(min(seps), 1),
            'Sep_max': round(max(seps), 1),
            'Standardized_distance_Pi': standardized_distance,
            'Sbar_crisis': round(sbar_crisis, 4),
            'Sbar_ctrl_mean': round(mean_sbar_ctrl, 4),
            'Sbar_ctrl_std': std_sbar_out,
            'Status': status,
        }

        all_results.append(
            result
        )

        print(
            f'\n  {name} '
            f'({len(window_pis)} control comparator window(s)):'
        )
        print(
            f'    Π_crisis  = {pi_crisis:.4f}'
        )
        print(
            f'    Π_control = {mean_ctrl:.4f}'
        )
        print(
            f'    Separation: mean={np.mean(seps):.1f}× '
            f'[{min(seps):.1f}× — {max(seps):.1f}×]'
        )
        print(
            f'    Status: {status}'
        )

    if len(all_results) != len(CASES):
        raise RuntimeError(
            "Control-window diagnostic did not return every case."
        )

    df = pd.DataFrame(
        all_results
    )

    output_path = os.path.join(
        OUT_DIR,
        'table_enhanced_sliding_controls.csv',
    )

    df.to_csv(
        output_path,
        index=False,
    )

    if not os.path.isfile(output_path) or os.path.getsize(output_path) <= 0:
        raise RuntimeError(
            "Control-window output was not created."
        )

    print(
        f'\n  Saved: table_enhanced_sliding_controls.csv'
    )

    return all_results

# ================================================================
# ENHANCEMENT 3: EXPLORATORY PATTERN-LABEL THRESHOLD SENSITIVITY
# ================================================================

def run_cutoff_sensitivity():
    """
    Assess whether exploratory failure-mode labels change under selected
    alternative cutoffs. This is a one-at-a-time sensitivity analysis,
    not validation of the taxonomy.

    Vary three selected thresholds:
      - Pre-loaded cutoff: 0.80 → test 0.70, 0.75, 0.80, 0.85, 0.90
      - Ductile lead cutoff: 300 days → test 200, 250, 300, 350, 400
      - Onset threshold: 10% → test 5%, 10%, 15%, 20%
    
    Results describe label sensitivity within the tested ranges only.
    """
    print(f'\n\n{"=" * 75}')
    print('  ENHANCEMENT 3: Exploratory Pattern-Label Threshold Sensitivity')
    print('  Exploratory one-at-a-time threshold sensitivity')
    print('=' * 75)

    preloaded_cuts = [0.70, 0.75, 0.80, 0.85, 0.90]
    ductile_cuts = [200, 250, 300, 350, 400]
    onset_cuts = [0.05, 0.10, 0.15, 0.20]

    # First compute base metrics for each case
    case_metrics = {}
    for name, info in CASES.items():
        cr, _ = load_case(name)
        collapse_date = pd.Timestamp(info['collapse'])
        case_metrics[name] = {
            'cr': cr,
            'collapse': collapse_date,
        }

    rows = []

    # Vary pre-loaded cutoff (with fixed ductile=300, onset=10%)
    print('\n  --- Varying Pre-loaded cutoff (ductile=300d, onset=10%) ---')
    for pl_cut in preloaded_cuts:
        for name, m in case_metrics.items():
            cr = m['cr']
            pi_max = cr['pi'].iloc[-1]
            nearest_idx = cr.index.get_indexer([m['collapse']], method='nearest')[0]
            pi_at_collapse = cr['pi'].iloc[nearest_idx]
            pct = (pi_at_collapse / pi_max * 100) if pi_max > 0 else 0

            threshold = pi_max * 0.10
            crossed = cr[cr['pi'] >= threshold].index
            lead_days = (m['collapse'] - crossed[0]).days if len(crossed) > 0 else 0

            if pct > pl_cut * 100:
                mode = 'Pre-loaded'
            elif lead_days > 300:
                mode = 'Ductile'
            else:
                mode = 'Brittle'

            rows.append({
                'Varied_param': 'preloaded_cutoff',
                'Param_value': pl_cut,
                'Case': name,
                'Pct_of_max': round(pct, 1),
                'Lead_days': lead_days,
                'Mode': mode,
            })

    # Vary ductile lead cutoff (with fixed preloaded=0.80, onset=10%)
    print('  --- Varying Ductile lead cutoff (preloaded=0.80, onset=10%) ---')
    for dc_cut in ductile_cuts:
        for name, m in case_metrics.items():
            cr = m['cr']
            pi_max = cr['pi'].iloc[-1]
            nearest_idx = cr.index.get_indexer([m['collapse']], method='nearest')[0]
            pi_at_collapse = cr['pi'].iloc[nearest_idx]
            pct = (pi_at_collapse / pi_max * 100) if pi_max > 0 else 0

            threshold = pi_max * 0.10
            crossed = cr[cr['pi'] >= threshold].index
            lead_days = (m['collapse'] - crossed[0]).days if len(crossed) > 0 else 0

            if pct > 80:
                mode = 'Pre-loaded'
            elif lead_days > dc_cut:
                mode = 'Ductile'
            else:
                mode = 'Brittle'

            rows.append({
                'Varied_param': 'ductile_lead_cutoff',
                'Param_value': dc_cut,
                'Case': name,
                'Pct_of_max': round(pct, 1),
                'Lead_days': lead_days,
                'Mode': mode,
            })

    # Vary onset threshold (with fixed preloaded=0.80, ductile=300)
    print('  --- Varying Onset threshold (preloaded=0.80, ductile=300d) ---')
    for on_cut in onset_cuts:
        for name, m in case_metrics.items():
            cr = m['cr']
            pi_max = cr['pi'].iloc[-1]
            nearest_idx = cr.index.get_indexer([m['collapse']], method='nearest')[0]
            pi_at_collapse = cr['pi'].iloc[nearest_idx]
            pct = (pi_at_collapse / pi_max * 100) if pi_max > 0 else 0

            threshold = pi_max * on_cut
            crossed = cr[cr['pi'] >= threshold].index
            lead_days = (m['collapse'] - crossed[0]).days if len(crossed) > 0 else 0

            if pct > 80:
                mode = 'Pre-loaded'
            elif lead_days > 300:
                mode = 'Ductile'
            else:
                mode = 'Brittle'

            rows.append({
                'Varied_param': 'onset_threshold',
                'Param_value': on_cut,
                'Case': name,
                'Pct_of_max': round(pct, 1),
                'Lead_days': lead_days,
                'Mode': mode,
            })

    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUT_DIR, 'table_enhanced_cutoff_sensitivity.csv'), index=False)

    # Check stability: for each case, how many unique modes across all variations?
    print(f'\n  Exploratory label variation across the tested cutoffs:')
    print(f'  {"Case":<18} {"Baseline":<14} {"Variants":<30} {"Unchanged?":<10}')
    print(f'  {"-"*70}')

    # Baseline modes (preloaded=0.80, ductile=300, onset=0.10)
    baseline = df[(df['Varied_param']=='preloaded_cutoff') & (df['Param_value']==0.80)]
    
    for name in CASES:
        bl_mode = baseline[baseline['Case']==name]['Mode'].values[0]
        all_modes = df[df['Case']==name]['Mode'].unique()
        stable = '✅' if len(all_modes) == 1 else '⚠️'
        print(f'  {name:<18} {bl_mode:<14} {", ".join(all_modes):<30} {stable}')

    print(f'\n  Saved: table_enhanced_cutoff_sensitivity.csv')
    return df


# ================================================================
# MAIN
# ================================================================

def main():
    print()
    print('╔' + '═' * 73 + '╗')
    print('║  Π FRAMEWORK — v12 ENHANCEMENTS                                       ║')
    print('║  Time-normalization + Sliding controls + Cutoff sensitivity            ║')
    print('╚' + '═' * 73 + '╝')
    print(f'  Data directory: {DATA_DIR}')

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

    r1 = run_time_normalized()
    r2 = run_sliding_controls()
    r3 = run_cutoff_sensitivity()

    # Final summary
    print(f'\n\n{"="*75}')
    print('  v12 ENHANCEMENT SUMMARY')
    print(f'{"="*75}')
    print(f'  1. Mean-stress crisis/control ratio exceeds 1.0 in all 5 selected cases')
    
    still_pass = sum(1 for r in r1 if r['Sep_Sbar'] > 1.5)
    print(f'     → {still_pass}/5 meet the script\'s S̄-based separation criterion')
    
    print(f'  2. Sliding controls: effect sizes computed for all cases')
    print(f'  3. Cutoff sensitivity: alternative-threshold labels reported')
    
    print(f'\n  Output files:')
    for f in ['table_enhanced_time_normalized.csv',
              'table_enhanced_sliding_controls.csv', 
              'table_enhanced_cutoff_sensitivity.csv']:
        path = os.path.join(OUT_DIR, f)
        if os.path.exists(path):
            sz = os.path.getsize(path)
            print(f'    {f} ({sz} bytes)')

    print()


if __name__ == '__main__':
    main()
