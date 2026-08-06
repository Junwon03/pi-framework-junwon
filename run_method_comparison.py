"""
Legacy retrospective trajectory and method-comparison audits.

The ST17 trajectory tables evaluate threshold-crossing timing relative to
predefined event dates. They are retrospective, uncalibrated diagnostics and
are excluded from the revised evidentiary package. The original trajectory
uses thresholds derived from raw control stress while evaluating rolling
crisis means; the matched variant uses rolling-control thresholds and searches
strictly after the control-window end. Neither analysis establishes warning,
forecasting, prospective validation, or calibrated false-alarm performance.

The optional ST16 method comparison is likewise retained only for audit
reproducibility. Output filenames and numerical procedures remain unchanged.

Usage:
    python run_method_comparison.py
    python run_method_comparison.py --include-audit-method-comparison
"""

import argparse
import pandas as pd
import numpy as np
from scipy import stats
from sklearn.decomposition import PCA
import os
import warnings
warnings.filterwarnings('ignore')

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.dates import DateFormatter

_base = os.path.dirname(os.path.abspath(__file__))

DATA_DIR = os.path.join(_base, "data")

OUTPUT_DIR = os.path.join(_base, "output")
FIG_DIR = os.path.join(OUTPUT_DIR, "figures", "legacy")
os.makedirs(FIG_DIR, exist_ok=True)

np.random.seed(42)

CASES = {
    "2008 Financial": ("crisis_2008_pi.csv", "control_2004_2006_pi.csv"),
    "Terra-Luna": ("crisis_terra_luna_pi.csv", "control_terra_luna_pi.csv"),
    "Fukushima": ("crisis_fukushima_pi.csv", "control_fukushima_pi.csv"),
    "COVID-19": ("crisis_covid_pi.csv", "control_covid_pi.csv"),
    "Supply Chain": ("crisis_supply_chain_pi.csv", "control_supply_chain_pi.csv"),
}

COLLAPSE_DATES = {
    "2008 Financial": "2008-09-15",
    "Terra-Luna": "2022-05-09",
    "Fukushima": "2011-03-11",
    "COVID-19": "2020-03-23",
    "Supply Chain": "2021-10-01",
}

ROLLING_WINDOWS = {
    "2008 Financial": 90,
    "Terra-Luna": 30,
    "Fukushima": 30,
    "COVID-19": 30,
    "Supply Chain": 3,
}

CHANNELS = ['rho_norm', 'psi_norm', 'omega_norm']


def estimate_dt(df):
    avg_gap = (df.index[-1] - df.index[0]).days / len(df)
    return 1.0 / 12 if avg_gap > 20 else 1.0 / 365


# ═══════════════════════════════════════════════════════════════
# Legacy audit analysis: method comparison
# ═══════════════════════════════════════════════════════════════

def compute_pi(df, dt):
    return (df['stress'] * dt).sum()


def compute_csd_variance(df, window=None):
    if window is None:
        window = max(10, len(df) // 5)
    window = min(window, len(df) - 1)
    vars_ = []
    for col in CHANNELS:
        rv = df[col].rolling(window, min_periods=max(2, window // 2)).var()
        vars_.append(rv.mean())
    return np.mean(vars_)


def compute_csd_autocorr(df, window=None):
    if window is None:
        window = max(10, len(df) // 5)
    window = min(window, len(df) - 1)
    acs = []
    for col in CHANNELS:
        ac = df[col].rolling(window, min_periods=max(2, window // 2)).apply(
            lambda x: pd.Series(x).autocorr(lag=1) if len(x) > 1 else 0, raw=False
        )
        acs.append(ac.mean())
    return np.mean(acs)


def compute_pca_stress(df, dt):
    X = df[CHANNELS].dropna().values
    if len(X) < 3:
        return 0
    pca = PCA(n_components=1)
    pc1 = pca.fit_transform(X).flatten()
    if np.corrcoef(pc1, X.mean(axis=1))[0, 1] < 0:
        pc1 = -pc1
    pc1 = np.clip(pc1, 0, None)
    return np.sum(pc1) * dt


def compute_additive(df, dt):
    s = df['rho_norm'] + df['psi_norm'] + df['omega_norm']
    return (s * dt).sum()


def compute_max_channel(df, dt):
    s = np.maximum(np.maximum(df['rho_norm'], df['psi_norm']), df['omega_norm'])
    return (s * dt).sum()


def run_method_comparison():
    print("=" * 80)
    print("  LEGACY AUDIT: Head-to-Head Method Comparison")
    print("=" * 80)

    results = []

    for name, (cf, ctf) in CASES.items():
        cr = pd.read_csv(f"{DATA_DIR}/{cf}", index_col=0, parse_dates=True)
        ct = pd.read_csv(f"{DATA_DIR}/{ctf}", index_col=0, parse_dates=True)
        dt_cr, dt_ct = estimate_dt(cr), estimate_dt(ct)

        methods = {
            'Π (ρ×Ψ×Ω)': (compute_pi(cr, dt_cr), compute_pi(ct, dt_ct)),
            'CSD Variance': (compute_csd_variance(cr), compute_csd_variance(ct)),
            'CSD AC(1)': (compute_csd_autocorr(cr), compute_csd_autocorr(ct)),
            'PCA-PC1': (compute_pca_stress(cr, dt_cr), compute_pca_stress(ct, dt_ct)),
            'Additive': (compute_additive(cr, dt_cr), compute_additive(ct, dt_ct)),
            'Max': (compute_max_channel(cr, dt_cr), compute_max_channel(ct, dt_ct)),
        }

        for method, (val_cr, val_ct) in methods.items():
            sep = val_cr / val_ct if abs(val_ct) > 1e-15 else float('inf')
            results.append({'Case': name, 'Method': method, 'Crisis': val_cr,
                            'Control': val_ct, 'Sep': sep})

        best_method = max(methods, key=lambda m: methods[m][0] / methods[m][1]
                          if abs(methods[m][1]) > 1e-15 else -1)
        print(f"\n  {name}: best = {best_method}")
        for method, (val_cr, val_ct) in methods.items():
            sep = val_cr / val_ct if abs(val_ct) > 1e-15 else float('inf')
            tag = " ◀" if method == best_method else ""
            print(f"    {method:18s}: {sep:>10.1f}×{tag}")

    df = pd.DataFrame(results)
    pivot = df.pivot(index='Method', columns='Case', values='Sep')
    pivot = pivot[['2008 Financial', 'Terra-Luna', 'Fukushima', 'COVID-19', 'Supply Chain']]
    pivot.round(1).to_csv(f"{OUTPUT_DIR}/table_ST16_method_comparison.csv")
    print(f"\n  → Saved: {OUTPUT_DIR}/table_ST16_method_comparison.csv")

    # Win count
    wins = {}
    for case in pivot.columns:
        w = pivot[case].idxmax()
        wins[w] = wins.get(w, 0) + 1
    print(f"\n  Win count: {wins}")

    return pivot


# ═══════════════════════════════════════════════════════════════
# Legacy audit: retrospective rolling-trajectory analysis
# ═══════════════════════════════════════════════════════════════

def run_retrospective_trajectory():
    print("\n" + "=" * 80)
    print("  LEGACY AUDIT: RETROSPECTIVE ROLLING-TRAJECTORY ANALYSIS")
    print("=" * 80)

    results = []

    for name, (cf, ctf) in CASES.items():
        cr = pd.read_csv(f"{DATA_DIR}/{cf}", index_col=0, parse_dates=True)
        ct = pd.read_csv(f"{DATA_DIR}/{ctf}", index_col=0, parse_dates=True)
        collapse = pd.Timestamp(COLLAPSE_DATES[name])
        rw = ROLLING_WINDOWS[name]

        ct_mean = ct['stress'].mean()
        ct_std = ct['stress'].std()
        thresh_2s = ct_mean + 2 * ct_std
        thresh_3s = ct_mean + 3 * ct_std

        rolling = cr['stress'].rolling(rw, min_periods=max(2, rw // 2)).mean()

        above_2s = cr.index[rolling > thresh_2s]
        above_3s = cr.index[rolling > thresh_3s]

        first_2s = above_2s[0] if len(above_2s) > 0 else None
        first_3s = above_3s[0] if len(above_3s) > 0 else None

        offset_2s = (first_2s - collapse).days if first_2s else None
        offset_3s = (first_3s - collapse).days if first_3s else None

        results.append({
            'Case': name,
            'Event_date': COLLAPSE_DATES[name],
            'Rolling_window': rw,
            'Control_mean_stress': round(ct_mean, 6),
            'Threshold_2σ': round(thresh_2s, 6),
            'Threshold_3σ': round(thresh_3s, 6),
            'First_crossing_2σ': first_2s.date() if first_2s else 'N/A',
            'First_crossing_3σ': first_3s.date() if first_3s else 'N/A',
            'Days_relative_to_event_2σ': offset_2s if offset_2s is not None else 'N/A',
            'Days_relative_to_event_3σ': offset_3s if offset_3s is not None else 'N/A',
            'Crossing_timing': (
                'Before event' if offset_2s is not None and offset_2s < 0 else
                'After event' if offset_2s is not None and offset_2s > 0 else
                'On event date' if offset_2s == 0 else 'No crossing'
            ),
        })

        first_2s_text = (
            first_2s.date().isoformat()
            if first_2s is not None
            else "N/A"
        )
        offset_text = offset_2s if offset_2s is not None else "N/A"
        print(
            f"  {name:20s}: first 2σ crossing "
            f"{first_2s_text:>12}, "
            f"offset={offset_text:>5} days relative to event"
        )

    df = pd.DataFrame(results)
    df.to_csv(f"{OUTPUT_DIR}/table_ST17_retrospective_trajectory.csv", index=False)
    print(f"\n  → Saved: {OUTPUT_DIR}/table_ST17_retrospective_trajectory.csv")

    # ── Figure 7: 2008 retrospective trajectory ──
    _plot_2008_retrospective()

    return df


def run_matched_threshold_sensitivity():
    """Evaluate rolling-matched thresholds and control exceedances.

    The same rolling window and minimum-period rule are applied to the
    crisis and control stress series. Thresholds are estimated from the
    rolling-control distribution. Crisis crossings are searched only after
    the end of the prespecified control window.

    Rolling values immediately after the control end retain prior observations
    from the causal rolling window. This is a retrospective sensitivity
    diagnostic, not a prospective prediction test.
    """
    print("\n" + "=" * 80)
    print("  LEGACY AUDIT: ST17 ROLLING-MATCHED THRESHOLD SENSITIVITY")
    print("  Control exceedances and post-control crisis crossings")
    print("=" * 80)

    results = []

    for name, (crisis_file, control_file) in CASES.items():
        crisis = pd.read_csv(
            f"{DATA_DIR}/{crisis_file}",
            index_col=0,
            parse_dates=True,
        ).sort_index()

        control = pd.read_csv(
            f"{DATA_DIR}/{control_file}",
            index_col=0,
            parse_dates=True,
        ).sort_index()

        event_date = pd.Timestamp(COLLAPSE_DATES[name])
        rolling_window = ROLLING_WINDOWS[name]
        min_periods = max(2, rolling_window // 2)
        control_end = control.index.max()

        crisis_rolling = (
            crisis["stress"]
            .rolling(
                rolling_window,
                min_periods=min_periods,
            )
            .mean()
            .dropna()
        )

        control_rolling = (
            control["stress"]
            .rolling(
                rolling_window,
                min_periods=min_periods,
            )
            .mean()
            .dropna()
        )

        post_control_rolling = crisis_rolling.loc[
            crisis_rolling.index > control_end
        ]

        if control_rolling.empty:
            raise ValueError(
                f"{name}: no valid rolling-control observations"
            )

        if post_control_rolling.empty:
            raise ValueError(
                f"{name}: no valid crisis rolling observations "
                "after the control window"
            )

        control_rolling_mean = float(control_rolling.mean())
        control_rolling_std = float(control_rolling.std())

        for sigma in (2, 3):
            threshold = (
                control_rolling_mean
                + sigma * control_rolling_std
            )

            control_exceedances = control_rolling.loc[
                control_rolling > threshold
            ]

            post_control_crossings = post_control_rolling.loc[
                post_control_rolling > threshold
            ]

            first_control_exceedance = (
                control_exceedances.index[0]
                if len(control_exceedances)
                else None
            )

            first_post_control_crossing = (
                post_control_crossings.index[0]
                if len(post_control_crossings)
                else None
            )

            event_offset = (
                int(
                    (
                        first_post_control_crossing
                        - event_date
                    ).days
                )
                if first_post_control_crossing is not None
                else None
            )

            crossing_timing = (
                "Before event"
                if event_offset is not None and event_offset < 0
                else "After event"
                if event_offset is not None and event_offset > 0
                else "On event date"
                if event_offset == 0
                else "No crossing"
            )

            exceedance_count = len(control_exceedances)
            exceedance_rate = (
                exceedance_count / len(control_rolling)
            )

            control_interpretation = (
                "Threshold exceeded in control; crossing is not "
                "unique to the post-control crisis trajectory"
                if exceedance_count
                else "No threshold exceedance observed in the "
                "prespecified control window"
            )

            results.append({
                "Case": name,
                "Sigma": sigma,
                "Event_date": event_date.date().isoformat(),
                "Rolling_window": rolling_window,
                "Min_periods": min_periods,
                "Control_start": (
                    control.index.min().date().isoformat()
                ),
                "Control_end": control_end.date().isoformat(),
                "Post_control_search_start": (
                    post_control_rolling.index.min()
                    .date()
                    .isoformat()
                ),
                "Control_rolling_mean": round(
                    control_rolling_mean,
                    10,
                ),
                "Control_rolling_std": round(
                    control_rolling_std,
                    10,
                ),
                "Matched_threshold": round(
                    threshold,
                    10,
                ),
                "Control_valid_rolling_N": len(control_rolling),
                "Control_exceedance_count": exceedance_count,
                "Control_exceedance_rate": round(
                    exceedance_rate,
                    6,
                ),
                "First_control_exceedance": (
                    first_control_exceedance.date().isoformat()
                    if first_control_exceedance is not None
                    else "N/A"
                ),
                "Control_exceedance_observed": (
                    "Yes" if exceedance_count else "No"
                ),
                "Control_exceedance_interpretation": (
                    control_interpretation
                ),
                "Post_control_valid_rolling_N": (
                    len(post_control_rolling)
                ),
                "First_post_control_crossing": (
                    first_post_control_crossing.date().isoformat()
                    if first_post_control_crossing is not None
                    else "N/A"
                ),
                "Days_relative_to_event": (
                    event_offset
                    if event_offset is not None
                    else "N/A"
                ),
                "Crossing_timing": crossing_timing,
            })

    result = pd.DataFrame(results)

    if len(result) != len(CASES) * 2:
        raise AssertionError(
            "Expected two threshold rows per selected case."
        )

    if result.duplicated(["Case", "Sigma"]).any():
        raise AssertionError(
            "Duplicate case/sigma rows found."
        )

    output_path = (
        f"{OUTPUT_DIR}/"
        "table_ST17_matched_threshold_sensitivity.csv"
    )
    result.to_csv(output_path, index=False)

    print()
    print(
        result[
            [
                "Case",
                "Sigma",
                "Control_exceedance_count",
                "Control_exceedance_rate",
                "First_post_control_crossing",
                "Days_relative_to_event",
                "Crossing_timing",
            ]
        ].to_string(index=False)
    )

    print(f"\n  → Saved: {output_path}")
    return result


def _plot_2008_retrospective():
    cr = pd.read_csv(f"{DATA_DIR}/crisis_2008_pi.csv", index_col=0, parse_dates=True)
    ct = pd.read_csv(f"{DATA_DIR}/control_2004_2006_pi.csv", index_col=0, parse_dates=True)
    dt = 1 / 365

    cr['pi_expanding'] = (cr['stress'] * dt).cumsum()
    cr['stress_rolling'] = cr['stress'].rolling(90, min_periods=45).mean()

    LEHMAN = pd.Timestamp('2008-09-15')
    BEAR_STEARNS = pd.Timestamp('2008-03-14')
    BNP_PARIBAS = pd.Timestamp('2007-08-09')

    ct_mean = ct['stress'].mean()
    ct_std = ct['stress'].std()
    thresh_2s = ct_mean + 2 * ct_std
    thresh_3s = ct_mean + 3 * ct_std
    first_2s = cr.index[cr['stress_rolling'] > thresh_2s][0]

    fig, axes = plt.subplots(2, 1, figsize=(10, 8), gridspec_kw={'height_ratios': [2, 1]})

    # Panel a
    ax = axes[0]
    ax.plot(cr.index, cr['stress_rolling'], color='#2c3e50', lw=1.2,
            label='90-day rolling S̅(t)')
    ax.axhline(thresh_2s, color='#e67e22', ls='--', lw=0.8, label='2σ control benchmark')
    ax.axhline(thresh_3s, color='#e74c3c', ls='--', lw=0.8, label='3σ control benchmark')
    ax.axvline(LEHMAN, color='#c0392b', lw=1.5, alpha=0.7,
               label='Lehman Brothers (Sep 15, 2008)')
    ax.axvline(BEAR_STEARNS, color='#8e44ad', lw=1, alpha=0.5, ls=':',
               label='Bear Stearns (Mar 14, 2008)')
    ax.axvline(BNP_PARIBAS, color='#27ae60', lw=1, alpha=0.5, ls=':',
               label='BNP Paribas freeze (Aug 9, 2007)')
    ax.axvline(first_2s, color='#e67e22', lw=1, alpha=0.7, ls='-.',
               label=f'First crossing of 2σ benchmark ({first_2s.strftime("%b %d, %Y")})')
    ax.set_ylabel('Rolling mean stress S̅(t)')
    ax.set_title('a  Retrospective stress trajectory: 2008 Financial Crisis',
                 fontweight='bold', loc='left')
    ax.legend(fontsize=7.5, loc='upper left', framealpha=0.9)
    ax.set_xlim(cr.index[0], cr.index[-1])
    ax.xaxis.set_major_formatter(DateFormatter('%Y-%m'))

    # Panel b
    ax = axes[1]
    ax.fill_between(cr.index, 0, cr['pi_expanding'], color='#3498db', alpha=0.3)
    ax.plot(cr.index, cr['pi_expanding'], color='#2c3e50', lw=1.2)
    for date, lbl, col in [(BNP_PARIBAS, 'BNP', '#27ae60'),
                           (BEAR_STEARNS, 'Bear', '#8e44ad'),
                           (LEHMAN, 'Lehman', '#c0392b')]:
        ax.axvline(date, color=col, lw=1 if lbl != 'Lehman' else 1.5, alpha=0.7,
                   ls=':' if lbl != 'Lehman' else '-')
        nearest = cr.index[cr.index.get_indexer([date], method='nearest')[0]]
        pi_at = cr.loc[nearest, 'pi_expanding']
        ax.annotate(f'{lbl}\nΠ={pi_at:.3f}', xy=(date, pi_at), fontsize=7,
                    ha='center', va='bottom', color=col, fontweight='bold')

    ax.set_ylabel('Cumulative Π(t)')
    ax.set_xlabel('Date')
    ax.set_title('b  Cumulative normalized-stress exposure Π(t)', fontweight='bold', loc='left')
    ax.set_xlim(cr.index[0], cr.index[-1])
    ax.xaxis.set_major_formatter(DateFormatter('%Y-%m'))

    plt.tight_layout()
    plt.savefig(f"{FIG_DIR}/Supplementary_Figure_S2_retrospective_trajectory.pdf", bbox_inches='tight', dpi=300)
    plt.savefig(f"{FIG_DIR}/Supplementary_Figure_S2_retrospective_trajectory.png", bbox_inches='tight', dpi=200)
    plt.close()
    print(f"  → Saved: Supplementary_Figure_S2_retrospective_trajectory.pdf/.png")


# ═══════════════════════════════════════════════════════════════
def parse_args():
    parser = argparse.ArgumentParser(
        description="Run legacy retrospective trajectory and optional method-comparison audits."
    )
    parser.add_argument(
        "--include-audit-method-comparison",
        action="store_true",
        help=(
            "Also run the legacy method comparison retained only for "
            "audit reproducibility."
        ),
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.include_audit_method_comparison:
        run_method_comparison()
    run_retrospective_trajectory()
    run_matched_threshold_sensitivity()
    print("\n  Done.")
