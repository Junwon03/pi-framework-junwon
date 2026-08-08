"""
Pi Framework — Channel Ablation Benchmark
==========================================
Compares separation ratios across single-channel, dual-channel,
and triple-channel stress definitions for 5 selected cases.

Describes how the 3-channel multiplicative formulation (ρ×Ψ×Ω)
compares with simpler alternatives in the selected cases.

Uses the SAME pre-computed CSV data as run_all.py.
No additional data collection required.

Usage:
  python run_benchmark.py

Output:
  output/benchmark_full.csv        — 45-cell result table (9 methods × 5 domains)
  output/benchmark_summary.txt     — Console-formatted summary
  output/figures/Figure_benchmark.png  — Bar chart (if matplotlib available)
  output/figures/Figure_benchmark.pdf
"""

import pandas as pd
import numpy as np
import os
import sys

# ================================================================
# CONFIG (identical to run_all.py)
# ================================================================

_base = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(_base, 'data')

OUT_DIR = os.path.join(_base, 'output')

CASES = {
    '2008 Financial': {
        'crisis': 'crisis_2008_pi.csv',
        'control': 'control_2004_2006_pi.csv',
        'domain': 'Traditional Finance',
    },
    'Terra-Luna': {
        'crisis': 'crisis_terra_luna_pi.csv',
        'control': 'control_terra_luna_pi.csv',
        'domain': 'Digital Assets',
    },
    'Fukushima': {
        'crisis': 'crisis_fukushima_pi.csv',
        'control': 'control_fukushima_pi.csv',
        'domain': 'Physical Infrastructure',
    },
    'COVID-19': {
        'crisis': 'crisis_covid_pi.csv',
        'control': 'control_covid_pi.csv',
        'domain': 'Pandemic / Public Health',
    },
    'Supply Chain': {
        'crisis': 'crisis_supply_chain_pi.csv',
        'control': 'control_supply_chain_pi.csv',
        'domain': 'Global Logistics',
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

    if (channels < 0).any():
        raise ValueError(
            f"{name}/{role}: normalized channels must be nonnegative."
        )

    if (stress < 0).any():
        raise ValueError(
            f"{name}/{role}: stress must be nonnegative."
        )

    expected_stress = (
        channels[:, 0]
        * channels[:, 1]
        * channels[:, 2]
    )

    if not np.allclose(
        stress,
        expected_stress,
        rtol=1e-12,
        atol=1e-12,
    ):
        max_diff = float(
            np.max(
                np.abs(
                    stress - expected_stress
                )
            )
        )

        raise ValueError(
            f"{name}/{role}: stored stress does not equal "
            "rho_norm*psi_norm*omega_norm; "
            f"max_abs_diff={max_diff:.12g}."
        )


def load_case(name):
    """Load and validate frozen crisis/control inputs."""
    if name not in CASES:
        raise KeyError(
            f"Unknown benchmark case: {name}"
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
    )

    ct = pd.read_csv(
        control_path,
        index_col=0,
        parse_dates=True,
    )

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

    return cr, ct

# ================================================================
# BENCHMARK METHODS
# ================================================================

# Each method: (label, level, function(rho, psi, omega) -> stress)
METHODS = [
    # Level 1: Single channel
    ('ρ only',       '1-Single',  lambda r, p, o: r),
    ('Ψ only',       '1-Single',  lambda r, p, o: p),
    ('Ω only',       '1-Single',  lambda r, p, o: o),
    # Level 2: Dual channel (multiplicative)
    ('ρ × Ψ',       '2-Dual',    lambda r, p, o: r * p),
    ('ρ × Ω',       '2-Dual',    lambda r, p, o: r * o),
    ('Ψ × Ω',       '2-Dual',    lambda r, p, o: p * o),
    # Level 3: Triple channel (alternative aggregations)
    ('ρ + Ψ + Ω',   '3-Triple',  lambda r, p, o: r + p + o),
    ('max(ρ,Ψ,Ω)',  '3-Triple',  lambda r, p, o: np.maximum(np.maximum(r, p), o)),
    ('ρ × Ψ × Ω',   '3-Triple',  lambda r, p, o: r * p * o),
]


def calc_separation(name, cr, ct, stress_fn):
    """
    Calculate crisis/control separation for one channel formulation.

    Cadence is explicit per selected case. Inputs and derived stress
    arrays must be finite and nonnegative. A nonpositive control
    integral is undefined and fails closed rather than returning inf.
    """
    dt = case_dt(name)

    s_cr = np.asarray(
        stress_fn(
            cr['rho_norm'].to_numpy(dtype=float),
            cr['psi_norm'].to_numpy(dtype=float),
            cr['omega_norm'].to_numpy(dtype=float),
        ),
        dtype=float,
    )

    s_ct = np.asarray(
        stress_fn(
            ct['rho_norm'].to_numpy(dtype=float),
            ct['psi_norm'].to_numpy(dtype=float),
            ct['omega_norm'].to_numpy(dtype=float),
        ),
        dtype=float,
    )

    if s_cr.shape != (len(cr),):
        raise ValueError(
            f"{name}: crisis stress function returned "
            f"shape {s_cr.shape}, expected {(len(cr),)}."
        )

    if s_ct.shape != (len(ct),):
        raise ValueError(
            f"{name}: control stress function returned "
            f"shape {s_ct.shape}, expected {(len(ct),)}."
        )

    if not np.isfinite(s_cr).all():
        raise ValueError(
            f"{name}: crisis derived stress contains non-finite values."
        )

    if not np.isfinite(s_ct).all():
        raise ValueError(
            f"{name}: control derived stress contains non-finite values."
        )

    if (s_cr < 0).any():
        raise ValueError(
            f"{name}: crisis derived stress contains negative values."
        )

    if (s_ct < 0).any():
        raise ValueError(
            f"{name}: control derived stress contains negative values."
        )

    pi_cr = float(
        np.sum(s_cr * dt)
    )

    pi_ct = float(
        np.sum(s_ct * dt)
    )

    if not np.isfinite(pi_cr) or pi_cr < 0:
        raise ValueError(
            f"{name}: crisis integral is invalid: {pi_cr}."
        )

    if not np.isfinite(pi_ct) or pi_ct <= 0:
        raise ValueError(
            f"{name}: control integral must be positive and finite; "
            f"got {pi_ct}."
        )

    sep = pi_cr / pi_ct

    if not np.isfinite(sep):
        raise ValueError(
            f"{name}: separation ratio is non-finite."
        )

    return {
        'pi_crisis': pi_cr,
        'pi_control': pi_ct,
        'separation': sep,
    }

# ================================================================
# MAIN BENCHMARK
# ================================================================

def run_benchmark():
    print()
    print('╔' + '═' * 73 + '╗')
    print('║  Π FRAMEWORK — CHANNEL ABLATION BENCHMARK                              ║')
    print('║  9 Methods × 5 Domains = 45 Comparisons                                ║')
    print('╚' + '═' * 73 + '╝')
    print(f'  Data directory: {DATA_DIR}')
    print()

    os.makedirs(OUT_DIR, exist_ok=True)

    # Check data & columns
    for name in CASES:
        cr, ct = load_case(name)
        needed = ['rho_norm', 'psi_norm', 'omega_norm']
        missing = [c for c in needed if c not in cr.columns]
        if missing:
            print(f'  ❌ {name}: missing columns {missing} in crisis CSV')
            sys.exit(1)
        missing_ct = [c for c in needed if c not in ct.columns]
        if missing_ct:
            print(f'  ❌ {name}: missing columns {missing_ct} in control CSV')
            sys.exit(1)
    print('  All data files and columns verified ✅\n')

    # ── Run all combinations ──
    rows = []

    for name in CASES:
        cr, ct = load_case(name)

        for method_name, level, stress_fn in METHODS:
            result = calc_separation(name, cr, ct, stress_fn)
            rows.append({
                'Case': name,
                'Domain': CASES[name]['domain'],
                'Method': method_name,
                'Level': level,
                'Pi_crisis': round(result['pi_crisis'], 6),
                'Pi_control': round(result['pi_control'], 6),
                'Separation': round(result['separation'], 2),
            })

    df = pd.DataFrame(rows)

    expected_rows = len(CASES) * len(METHODS)

    if len(df) != expected_rows:
        raise RuntimeError(
            f"Expected {expected_rows} benchmark rows, got {len(df)}."
        )

    if df.duplicated(['Case', 'Method']).any():
        raise RuntimeError(
            "Duplicate case/method benchmark rows found."
        )

    numeric = df[
        ['Pi_crisis', 'Pi_control', 'Separation']
    ].to_numpy(dtype=float)

    if not np.isfinite(numeric).all():
        raise ValueError(
            "Benchmark result table contains non-finite values."
        )

    # ── Console output: Pivot table ──
    print('=' * 90)
    print('  CHANNEL ABLATION RESULTS')
    print('  Separation Ratio (Crisis Π / Control Π) by Method and Domain')
    print('=' * 90)

    # Method order for display
    method_order = [m[0] for m in METHODS]
    case_order = list(CASES.keys())

    # Print header
    header = f'  {"Method":<16} {"Level":<11}'
    for case in case_order:
        short = case[:12]
        header += f' {short:>12}'
    header += f' {"  Mean":>8}'
    print(header)
    print('  ' + '─' * (len(header) - 2))

    # Print rows
    for method_name, level, _ in METHODS:
        line = f'  {method_name:<16} {level:<11}'
        seps = []
        for case in case_order:
            sep = df[(df['Case'] == case) & (df['Method'] == method_name)]['Separation'].values[0]
            seps.append(sep)
            if sep >= 100:
                line += f' {sep:>11,.0f}×'
            else:
                line += f' {sep:>11.1f}×'
        mean_sep = np.mean(seps)
        line += f' {mean_sep:>7.1f}×'
        print(line)

        # Separator between levels
        if method_name in ['Ω only', 'Ψ × Ω']:
            print('  ' + '─' * (len(header) - 2))

    # ── Cases where Π has the highest separation ──
    print()
    pi_method = 'ρ × Ψ × Ω'
    wins = 0
    for case in case_order:
        pi_sep = df[(df['Case'] == case) & (df['Method'] == pi_method)]['Separation'].values[0]
        others = df[(df['Case'] == case) & (df['Method'] != pi_method)]['Separation'].max()
        if pi_sep >= others:
            wins += 1

    print(f'  ρ×Ψ×Ω has the highest separation in {wins}/5 selected cases')

    # ── Rank table ──
    print(f'\n  MEAN SEPARATION RANKING ACROSS SELECTED CASES:')
    rank_df = df.groupby('Method')['Separation'].mean().sort_values(ascending=False)
    for i, (method, mean_val) in enumerate(rank_df.items(), 1):
        marker = ' ◀ Π' if method == pi_method else ''
        print(f'    {i}. {method:<16}  mean = {mean_val:>8.1f}×{marker}')

    # ── Relative separation ratios ──
    print(f'\n  RELATIVE SEPARATION OF Π TO ALTERNATIVES:')
    pi_means = {}
    for case in case_order:
        pi_means[case] = df[(df['Case'] == case) & (df['Method'] == pi_method)]['Separation'].values[0]

    for method_name, level, _ in METHODS:
        if method_name == pi_method:
            continue
        improvements = []
        for case in case_order:
            alt_sep = df[(df['Case'] == case) & (df['Method'] == method_name)]['Separation'].values[0]
            if not np.isfinite(alt_sep) or alt_sep <= 0:
                raise ValueError(
                    f"{case}/{method_name}: alternative separation "
                    f"must be positive and finite; got {alt_sep}."
                )

            improvement = pi_means[case] / alt_sep

            if not np.isfinite(improvement):
                raise ValueError(
                    f"{case}/{method_name}: relative separation "
                    "is non-finite."
                )

            improvements.append(improvement)

        if len(improvements) != len(case_order):
            raise RuntimeError(
                f"{method_name}: expected {len(case_order)} "
                f"relative comparisons, got {len(improvements)}."
            )

        mean_impr = np.mean(improvements)
        print(f'    vs {method_name:<16}: mean Π/alternative ratio = {mean_impr:>5.1f}×')

    # ── Save CSV ──
    csv_path = os.path.join(OUT_DIR, 'benchmark_full.csv')
    df.to_csv(csv_path, index=False)
    print(f'\n  Saved: {csv_path}')

    # ── Save pivot CSV (for manuscript table) ──
    pivot = df.pivot_table(index='Method', columns='Case',
                           values='Separation', sort=False)
    pivot = pivot.reindex(index=method_order, columns=case_order)
    pivot['Mean'] = pivot.mean(axis=1)
    pivot_path = os.path.join(OUT_DIR, 'benchmark_pivot.csv')
    pivot.to_csv(pivot_path)
    print(f'  Saved: {pivot_path}')

    # ── Save summary text ──
    summary_path = os.path.join(OUT_DIR, 'benchmark_summary.txt')
    with open(summary_path, 'w') as f:
        f.write('Pi Framework — Channel Ablation Benchmark\n')
        f.write('=' * 50 + '\n\n')
        f.write(f'Methods tested: {len(METHODS)}\n')
        f.write(f'Selected cases tested: {len(CASES)}\n')
        f.write(f'Total comparisons: {len(METHODS) * len(CASES)}\n\n')
        f.write('Mean separation ranking across selected cases:\n')
        for i, (method, mean_val) in enumerate(rank_df.items(), 1):
            marker = ' <-- Pi (current framework)' if method == pi_method else ''
            f.write(f'  {i}. {method:<16}  mean = {mean_val:.1f}x{marker}\n')
        f.write(f'\nCases with highest ρ×Ψ×Ω separation: {wins}/5 selected cases\n')
    print(f'  Saved: {summary_path}')

    return df


# ================================================================
# OPTIONAL FIGURE
# ================================================================

def generate_benchmark_figure(df):
    """Generate grouped bar chart of benchmark results."""
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
    except ImportError:
        print('\n  ⚠ matplotlib not installed. Skipping figure.')
        return

    fig_dir = os.path.join(OUT_DIR, 'figures')
    os.makedirs(fig_dir, exist_ok=True)

    case_order = list(CASES.keys())
    method_order = [m[0] for m in METHODS]

    # Color scheme: gradient from light (single) to dark (triple)
    colors = {
        # Single - blues
        'ρ only':       '#90CAF9',
        'Ψ only':       '#64B5F6',
        'Ω only':       '#42A5F5',
        # Dual - oranges
        'ρ × Ψ':       '#FFCC80',
        'ρ × Ω':       '#FFB74D',
        'Ψ × Ω':       '#FFA726',
        # Triple - reds/grey
        'ρ + Ψ + Ω':   '#BDBDBD',
        'max(ρ,Ψ,Ω)':  '#9E9E9E',
        'ρ × Ψ × Ω':   '#D32F2F',
    }

    FS = 8
    DPI = 300

    plt.rcParams.update({
        'font.family': 'sans-serif',
        'font.sans-serif': ['Arial', 'Helvetica', 'DejaVu Sans'],
        'font.size': FS, 'axes.labelsize': FS + 1,
        'axes.titlesize': FS + 1, 'xtick.labelsize': FS - 1,
        'ytick.labelsize': FS - 1, 'legend.fontsize': FS - 2,
        'figure.dpi': DPI, 'savefig.dpi': DPI, 'savefig.bbox': 'tight',
        'axes.spines.top': False, 'axes.spines.right': False,
    })

    fig, ax = plt.subplots(figsize=(7.08, 4.0))

    n_cases = len(case_order)
    n_methods = len(method_order)
    x = np.arange(n_cases)
    total_width = 0.8
    bar_width = total_width / n_methods

    for j, method in enumerate(method_order):
        seps = []
        for case in case_order:
            val = df[(df['Case'] == case) & (df['Method'] == method)]['Separation'].values[0]
            seps.append(val)
        offset = (j - n_methods / 2 + 0.5) * bar_width
        bars = ax.bar(x + offset, seps, bar_width,
                       label=method, color=colors[method],
                       edgecolor='white', linewidth=0.3, zorder=3)

    # Labels
    case_labels = ['2008\nFinancial', 'Terra-\nLuna', 'Fukushima',
                   'COVID-19', 'Supply\nChain']
    ax.set_xticks(x)
    ax.set_xticklabels(case_labels)
    ax.set_ylabel('Separation Ratio (Crisis Π / Control Π)')
    ax.set_yscale('log')
    ax.set_ylim(0.5, 20000)
    ax.axhline(1, color='grey', ls='--', lw=0.8, alpha=0.5)
    ax.grid(axis='y', alpha=0.3, zorder=0)

    # Legend grouped by level
    ax.legend(ncol=3, loc='upper left', frameon=False,
              columnspacing=0.8, handletextpad=0.4)

    ax.set_title('Channel Ablation: Single → Dual → Triple Channel Comparison',
                 fontsize=FS + 2, fontweight='bold', pad=12)

    # Save
    fig.savefig(os.path.join(fig_dir, 'Figure_benchmark.png'), dpi=DPI)
    fig.savefig(os.path.join(fig_dir, 'Figure_benchmark.pdf'))
    plt.close(fig)
    print(f'\n  Figure saved: {fig_dir}/Figure_benchmark.png')
    print(f'  Figure saved: {fig_dir}/Figure_benchmark.pdf')


# ================================================================
# MAIN
# ================================================================

if __name__ == '__main__':
    df = run_benchmark()
    generate_benchmark_figure(df)
    print('\n  Done.\n')
