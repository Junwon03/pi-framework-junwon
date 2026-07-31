"""
Supplementary Table 15: Transform Window Sensitivity (Delta-k)
================================================================
Evaluates sensitivity of the 2008 Financial case to alternative diff() windows.
k = 1, 3, 5 (baseline), 10, 20 business days

Fully self-contained: no imports from repo modules.
Place in: {repo_root}/sensitivity/sensitivity_delta_k.py
Run from repo root: python sensitivity/sensitivity_delta_k.py
Requires: FRED_API_KEY environment variable

Outputs:
  output/table_ST15_delta_k_sensitivity.csv
  output/table_ST15_nonoverlap_delta_k.csv
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

# 2008 case configuration (mirrors config.py)
DATA_START = '2004-01-01'
DATA_END = '2009-06-30'
STABLE_START = '2005-01-01'
STABLE_END = '2007-06-30'
CRISIS_START = '2005-01-01'
CRISIS_END = '2009-03-31'
CONTROL_START = '2004-01-01'
CONTROL_END = '2006-06-30'
PLIMIT_PERCENTILE = 99
BIZ_DAYS = 252

K_VALUES = [1, 3, 5, 10, 20]
BASELINE_K = 5


# ================================================================
# FRED fetch (self-contained, no fredapi)
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
    """
    Full Pi pipeline: calibrate P-limits -> normalize -> S(t) -> cumulative Pi.
    Returns dict with pi_final, N, and p_limits.
    """
    # Calibrate: P-limits from stable period
    rho_s = rho[stable_start:stable_end].dropna()
    psi_s = psi[stable_start:stable_end].dropna()
    omega_s = omega[stable_start:stable_end].dropna()

    p_limits = {
        'rho': max(np.percentile(rho_s, PLIMIT_PERCENTILE), 1e-10),
        'psi': max(np.percentile(psi_s, PLIMIT_PERCENTILE), 1e-10),
        'omega': max(np.percentile(omega_s, PLIMIT_PERCENTILE), 1e-10),
    }

    # Slice analysis window
    r = rho[analysis_start:analysis_end].dropna()
    p = psi[analysis_start:analysis_end].dropna()
    o = omega[analysis_start:analysis_end].dropna()
    idx = r.index.intersection(p.index).intersection(o.index)
    r, p, o = r.reindex(idx), p.reindex(idx), o.reindex(idx)

    # Normalize
    r_norm = (r / p_limits['rho']).clip(lower=0)
    p_norm = (p / p_limits['psi']).clip(lower=0)
    o_norm = (o / p_limits['omega']).clip(lower=0)

    # S(t) = rho * psi * omega; Pi = cumsum(S * dt)
    stress = r_norm * p_norm * o_norm
    pi = (stress * dt).cumsum()

    return {
        'pi_final': pi.iloc[-1] if len(pi) > 0 else 0,
        'N': len(idx),
        'p_limits': p_limits,
        'stress_values': stress,
        'index': idx,
    }


# ================================================================
# Run single k value
# ================================================================
def run_case_with_k(k, dff_raw, ted_raw, bkcr_raw):
    dt = 1.0 / BIZ_DAYS
    print(f"\n  k = {k} days {'(BASELINE)' if k == BASELINE_K else ''}")

    # Transform
    rho = dff_raw.diff(k).abs()
    psi = ted_raw.diff(k).abs()
    common_idx = rho.dropna().index.intersection(psi.dropna().index)
    omega = interpolate_to_daily(bkcr_raw, common_idx)
    rho = rho.reindex(common_idx)
    psi = psi.reindex(common_idx)
    valid = rho.notna() & psi.notna() & omega.notna()
    idx = common_idx[valid]
    rho, psi, omega = rho.reindex(idx), psi.reindex(idx), omega.reindex(idx)

    # Crisis
    crisis = compute_pi_pipeline(rho, psi, omega,
                                 STABLE_START, STABLE_END,
                                 CRISIS_START, CRISIS_END, dt)
    # Control
    control = compute_pi_pipeline(rho, psi, omega,
                                  STABLE_START, STABLE_END,
                                  CONTROL_START, CONTROL_END, dt)

    pi_c = crisis['pi_final']
    pi_n = control['pi_final']
    sep_pi = pi_c / pi_n if pi_n > 0 else float('inf')

    T_c = crisis['N'] * dt
    T_n = control['N'] * dt
    sep_s = (pi_c / T_c) / (pi_n / T_n) if (T_n > 0 and pi_n > 0) else float('inf')

    # Primary non-overlap comparison:
    # mean crisis stress strictly after the actual control end date,
    # divided by mean stress across the full control window.
    if control['N'] == 0:
        raise ValueError("Control window contains no observations.")

    control_end = control['index'].max()
    crisis_exclusive_stress = crisis['stress_values'].loc[
        crisis['stress_values'].index > control_end
    ]

    if crisis_exclusive_stress.empty:
        raise ValueError(
            "No crisis observations remain after the control window."
        )

    mean_crisis_exclusive = float(crisis_exclusive_stress.mean())
    mean_control = float(control['stress_values'].mean())

    if mean_control <= 0:
        raise ValueError("Control mean stress must be positive.")

    sep_nonoverlap = mean_crisis_exclusive / mean_control

    # Permutation test (1000 iid)
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

    print(
        f"    N={crisis['N']}, Sep(Pi)={sep_pi:.1f}x, "
        f"Sep(non-overlap mean)={sep_nonoverlap:.4f}x, "
        f"z={z:.2f}, p={pval:.4f}"
    )

    return {
        'k': k,
        'N_crisis': crisis['N'],
        'N_control': control['N'],
        'Pi_crisis': round(pi_c, 4),
        'Pi_control': round(pi_n, 4),
        'Sep_Pi': round(sep_pi, 1),
        'Sep_S_bar': round(sep_s, 1),
        'z': round(z, 2),
        'p': round(pval, 4),
        'Control_end': control_end.date().isoformat(),
        'Exclusive_crisis_start': (
            crisis_exclusive_stress.index.min().date().isoformat()
        ),
        'Exclusive_crisis_end': (
            crisis_exclusive_stress.index.max().date().isoformat()
        ),
        'N_crisis_exclusive': len(crisis_exclusive_stress),
        'Mean_crisis_exclusive': round(mean_crisis_exclusive, 10),
        'Mean_control': round(mean_control, 10),
        'Nonoverlap_mean_ratio': round(sep_nonoverlap, 10),
    }


# ================================================================
# Main
# ================================================================
def main():
    print("=" * 58)
    print("  ST15: Transform Window Sensitivity (Delta-k)")
    print("  2008 Financial -- k = 1, 3, 5, 10, 20 days")
    print("=" * 58)

    if not FRED_API_KEY:
        print("  WARNING: FRED_API_KEY not set. Skipping ST15.")
        return

    print("\n  Fetching FRED data...")
    dff_raw = fetch_fred('DFF', DATA_START, DATA_END)
    ted_raw = fetch_fred('TEDRATE', DATA_START, DATA_END)
    bkcr_raw = fetch_fred('TOTBKCR', DATA_START, DATA_END)
    print(f"  DFF: {len(dff_raw)}, TEDRATE: {len(ted_raw)}, TOTBKCR: {len(bkcr_raw)}")

    results = []
    for k in K_VALUES:
        try:
            r = run_case_with_k(k, dff_raw, ted_raw, bkcr_raw)
            results.append(r)
        except Exception as e:
            print(f"    ERROR for k={k}: {e}")

    if results:
        df = pd.DataFrame(results)

        legacy_columns = [
            'k',
            'N_crisis',
            'N_control',
            'Pi_crisis',
            'Pi_control',
            'Sep_Pi',
            'Sep_S_bar',
            'z',
            'p',
        ]
        legacy_df = df[legacy_columns].copy()

        out_path = os.path.join(
            OUT_DIR,
            'table_ST15_delta_k_sensitivity.csv',
        )
        legacy_df.to_csv(out_path, index=False)

        nonoverlap_columns = [
            'k',
            'Control_end',
            'Exclusive_crisis_start',
            'Exclusive_crisis_end',
            'N_crisis_exclusive',
            'N_control',
            'Mean_crisis_exclusive',
            'Mean_control',
            'Nonoverlap_mean_ratio',
        ]
        nonoverlap_df = df[nonoverlap_columns].copy()

        nonoverlap_path = os.path.join(
            OUT_DIR,
            'table_ST15_nonoverlap_delta_k.csv',
        )
        nonoverlap_df.to_csv(nonoverlap_path, index=False)

        print(f"\n  Saved: {out_path}")
        print(legacy_df.to_string(index=False))
        print(f"\n  Saved: {nonoverlap_path}")
        print(nonoverlap_df.to_string(index=False))

        baseline = legacy_df[legacy_df['k'] == BASELINE_K]
        if not baseline.empty:
            print(f"\n  Baseline (k=5): Sep(Pi) = {baseline.iloc[0]['Sep_Pi']}x")
        print(
            f"  Range: Sep(Pi) = "
            f"{legacy_df['Sep_Pi'].min()}x to "
            f"{legacy_df['Sep_Pi'].max()}x"
        )
        print(f"  All p < 0.05: {(legacy_df['p'] < 0.05).all()}")
        print(
            f"  All legacy Sep(Pi) > 1: "
            f"{(legacy_df['Sep_Pi'] > 1).all()}"
        )
        print(
            f"  Non-overlap mean-ratio range: "
            f"{nonoverlap_df['Nonoverlap_mean_ratio'].min():.4f}x to "
            f"{nonoverlap_df['Nonoverlap_mean_ratio'].max():.4f}x"
        )
        print(
            f"  All non-overlap mean ratios > 1: "
            f"{(nonoverlap_df['Nonoverlap_mean_ratio'] > 1).all()}"
        )


if __name__ == '__main__':
    main()
