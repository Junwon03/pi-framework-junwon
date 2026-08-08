"""
Pi Framework — v13 Enhancements
================================
Two new analyses to complete NatComms preparation:
  1. Fixed-observation sliding control-window diagnostic
     → Empirical control-window distributions and percentile ranges
  2. Independent and contiguous-block alignment permutation diagnostic
     → Sensitivity of channel-alignment results to block-preserving shuffles

Usage:
  python run_v13_enhancements.py

Outputs to output/ folder.
"""

import pandas as pd
import numpy as np
import os
import sys

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

N_PERM = 10_000
RNG_SEED = 42

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
            f"{label}: numerator must be finite."
        )

    if not np.isfinite(denominator) or denominator <= 0:
        raise ValueError(
            f"{label}: denominator must be positive and finite; "
            f"got {denominator}."
        )

    value = numerator / denominator

    if not np.isfinite(value):
        raise ValueError(
            f"{label}: ratio must be finite."
        )

    return value


def validate_case_frame(name, role, df):
    required = {
        'rho_norm',
        'psi_norm',
        'omega_norm',
        'stress',
        'pi',
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

    numeric = df[
        [
            'rho_norm',
            'psi_norm',
            'omega_norm',
            'stress',
            'pi',
        ]
    ].to_numpy(dtype=float)

    if not np.isfinite(numeric).all():
        raise ValueError(
            f"{name}/{role}: non-finite analytical values."
        )

    if (numeric < 0).any():
        raise ValueError(
            f"{name}/{role}: negative analytical values."
        )

    expected_stress = (
        df['rho_norm'].to_numpy(dtype=float)
        * df['psi_norm'].to_numpy(dtype=float)
        * df['omega_norm'].to_numpy(dtype=float)
    )

    actual_stress = df['stress'].to_numpy(dtype=float)

    if not np.allclose(
        actual_stress,
        expected_stress,
        rtol=1e-12,
        atol=1e-12,
    ):
        max_diff = float(
            np.max(
                np.abs(
                    actual_stress - expected_stress
                )
            )
        )

        raise ValueError(
            f"{name}/{role}: stored stress does not equal "
            f"rho_norm*psi_norm*omega_norm; "
            f"max_abs_diff={max_diff:.12g}."
        )


def load_case(name):
    info = CASES[name]

    crisis_path = os.path.join(
        DATA_DIR,
        info['crisis'],
    )

    control_path = os.path.join(
        DATA_DIR,
        info['control'],
    )

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

    # Historical cumulative Pi is reconstructed with the
    # explicitly declared cadence used by the legacy audit.
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


def permutation_summary(observed, null_values, label):
    observed = float(observed)

    null_values = np.asarray(
        null_values,
        dtype=float,
    )

    if not np.isfinite(observed):
        raise ValueError(
            f"{label}: observed value is non-finite."
        )

    if (
        null_values.ndim != 1
        or len(null_values) != N_PERM
    ):
        raise ValueError(
            f"{label}: expected {N_PERM} null values, "
            f"got shape {null_values.shape}."
        )

    if not np.isfinite(null_values).all():
        raise ValueError(
            f"{label}: null distribution contains "
            "non-finite values."
        )

    null_mean = float(
        null_values.mean()
    )

    null_std = float(
        null_values.std()
    )

    if not np.isfinite(null_std) or null_std <= 0:
        raise ValueError(
            f"{label}: null standard deviation "
            "must be positive and finite."
        )

    exceedances = int(
        np.count_nonzero(
            null_values >= observed
        )
    )

    p_value = (
        exceedances + 1
    ) / (
        N_PERM + 1
    )

    z_score = (
        observed - null_mean
    ) / null_std

    if not np.isfinite(z_score):
        raise ValueError(
            f"{label}: z-score is non-finite."
        )

    return {
        'mean': null_mean,
        'std': null_std,
        'z': float(z_score),
        'p': float(p_value),
        'exceedances': exceedances,
    }


def block_shuffle(arr, block_size, rng):
    arr = np.asarray(
        arr,
        dtype=float,
    )

    n = len(arr)

    if block_size <= 0 or block_size >= n:
        raise ValueError(
            f"Invalid block size {block_size} for n={n}."
        )

    blocks = [
        arr[start:min(start + block_size, n)]
        for start in range(0, n, block_size)
    ]

    order = rng.permutation(
        len(blocks)
    )

    shuffled = np.concatenate(
        [blocks[i] for i in order]
    )

    if len(shuffled) != n:
        raise AssertionError(
            "Block shuffle changed observation count."
        )

    return shuffled

# ================================================================
# ENHANCEMENT 1: SLIDING-WINDOW CONTROLS (FIXED SHORT WINDOWS)
# ================================================================

def run_sliding_controls():
    """
    Fixed-observation sliding control-window diagnostic.

    Daily-design cases:
        180-observation windows, step 30 observations.

    Monthly-design case:
        6-observation windows, step 2 observations.

    Overlapping windows are descriptive and are not independent samples.
    Reported 2.5th/97.5th percentiles are empirical window ranges,
    not confidence intervals.

    Standardized distances compare the single crisis aggregate with
    the distribution of control-window aggregates; they are not
    labelled Cohen's d.
    """

    print('=' * 75)
    print(
        '  ENHANCEMENT 1: Sliding Control-Window Diagnostic'
    )
    print(
        '  Daily-design: 180 observations / step 30; '
        'Monthly-design: 6 observations / step 2'
    )
    print('=' * 75)

    all_results = []

    for name, info in CASES.items():
        cr, ct = load_case(name)
        dt = case_dt(name)

        pi_crisis = float(
            cr['stress'].sum() * dt
        )

        T_crisis = len(cr) * dt

        if not np.isfinite(T_crisis) or T_crisis <= 0:
            raise ValueError(
                f"{name}: invalid crisis exposure total."
            )

        sbar_crisis = (
            pi_crisis / T_crisis
        )

        if not np.isfinite(sbar_crisis):
            raise ValueError(
                f"{name}: non-finite crisis mean stress."
            )

        if info['freq'] == 'monthly':
            win_size = 6
            step = 2
        elif info['freq'] == 'daily':
            win_size = 180
            step = 30
        else:
            raise ValueError(
                f"{name}: unsupported frequency "
                f"{info['freq']!r}."
            )

        control_len = len(ct)

        window_pis = []
        window_sbars = []

        if control_len >= win_size:
            for start in range(
                0,
                control_len - win_size + 1,
                step,
            ):
                window = ct.iloc[
                    start:start + win_size
                ]

                if len(window) != win_size:
                    raise AssertionError(
                        f"{name}: incomplete sliding window."
                    )

                pi_w = float(
                    window['stress'].sum() * dt
                )

                T_w = len(window) * dt

                if not np.isfinite(T_w) or T_w <= 0:
                    raise ValueError(
                        f"{name}: invalid control-window exposure."
                    )

                sbar_w = (
                    pi_w / T_w
                )

                if (
                    not np.isfinite(pi_w)
                    or not np.isfinite(sbar_w)
                ):
                    raise ValueError(
                        f"{name}: non-finite control-window metric."
                    )

                window_pis.append(
                    pi_w
                )

                window_sbars.append(
                    sbar_w
                )

        n_windows = len(
            window_pis
        )

        if n_windows < 2:
            # Explicit descriptive fallback only. No distributional
            # uncertainty statistic is claimed from a single control.
            pi_ct_full = float(
                ct['stress'].sum() * dt
            )

            T_ct = len(ct) * dt

            if not np.isfinite(T_ct) or T_ct <= 0:
                raise ValueError(
                    f"{name}: invalid full-control exposure."
                )

            sbar_ct_full = (
                pi_ct_full / T_ct
            )

            sep_pi = positive_finite_ratio(
                pi_crisis,
                pi_ct_full,
                f"{name} full-control Pi separation",
            )

            sep_sbar = positive_finite_ratio(
                sbar_crisis,
                sbar_ct_full,
                f"{name} full-control mean-stress separation",
            )

            result = {
                'Case': name,
                'Window_size_observations': win_size,
                'Step_observations': step,
                'N_windows': 1,
                'Pi_crisis': round(pi_crisis, 6),
                'Sbar_crisis': round(sbar_crisis, 6),
                'Pi_ctrl_mean': round(pi_ct_full, 6),
                'Pi_ctrl_std': 'N/A',
                'Sbar_ctrl_mean': round(
                    sbar_ct_full,
                    6,
                ),
                'Sbar_ctrl_std': 'N/A',
                'Sep_Pi_mean': round(
                    sep_pi,
                    1,
                ),
                'Sep_Pi_P2_5': 'N/A',
                'Sep_Pi_P97_5': 'N/A',
                'Sep_Sbar_mean': round(
                    sep_sbar,
                    1,
                ),
                'Standardized_distance_Pi': 'N/A',
                'Standardized_distance_Sbar': 'N/A',
                'Status': (
                    'Single full-control descriptive fallback; '
                    'control shorter than configured sliding window'
                ),
            }

            all_results.append(
                result
            )

            print(
                f'\n  {name}: control shorter than '
                f'{win_size}-observation window '
                f'(N_ctrl={control_len})'
            )

            print(
                f'    Full-control descriptive ratio: '
                f'Pi={sep_pi:.1f}x, '
                f'Sbar={sep_sbar:.1f}x'
            )

            continue

        window_pis = np.asarray(
            window_pis,
            dtype=float,
        )

        window_sbars = np.asarray(
            window_sbars,
            dtype=float,
        )

        if (
            not np.isfinite(window_pis).all()
            or not np.isfinite(window_sbars).all()
        ):
            raise ValueError(
                f"{name}: non-finite sliding-window metrics."
            )

        mean_pi = float(
            window_pis.mean()
        )

        std_pi = float(
            window_pis.std(ddof=1)
        )

        mean_sbar = float(
            window_sbars.mean()
        )

        std_sbar = float(
            window_sbars.std(ddof=1)
        )

        if not np.isfinite(std_pi) or std_pi <= 0:
            raise ValueError(
                f"{name}: Pi control-window standard deviation "
                "must be positive and finite."
            )

        if not np.isfinite(std_sbar) or std_sbar <= 0:
            raise ValueError(
                f"{name}: mean-stress control-window standard "
                "deviation must be positive and finite."
            )

        seps_pi = np.array(
            [
                positive_finite_ratio(
                    pi_crisis,
                    value,
                    f"{name} sliding Pi separation",
                )
                for value in window_pis
            ],
            dtype=float,
        )

        seps_sbar = np.array(
            [
                positive_finite_ratio(
                    sbar_crisis,
                    value,
                    f"{name} sliding mean-stress separation",
                )
                for value in window_sbars
            ],
            dtype=float,
        )

        sep_pi_lo = float(
            np.percentile(
                seps_pi,
                2.5,
            )
        )

        sep_pi_hi = float(
            np.percentile(
                seps_pi,
                97.5,
            )
        )

        standardized_pi = (
            pi_crisis - mean_pi
        ) / std_pi

        standardized_sbar = (
            sbar_crisis - mean_sbar
        ) / std_sbar

        if not np.isfinite(
            [
                sep_pi_lo,
                sep_pi_hi,
                standardized_pi,
                standardized_sbar,
            ]
        ).all():
            raise ValueError(
                f"{name}: non-finite sliding-control statistic."
            )

        result = {
            'Case': name,
            'Window_size_observations': win_size,
            'Step_observations': step,
            'N_windows': n_windows,
            'Pi_crisis': round(pi_crisis, 6),
            'Sbar_crisis': round(sbar_crisis, 6),
            'Pi_ctrl_mean': round(mean_pi, 6),
            'Pi_ctrl_std': round(std_pi, 6),
            'Sbar_ctrl_mean': round(mean_sbar, 6),
            'Sbar_ctrl_std': round(std_sbar, 6),
            'Sep_Pi_mean': round(
                float(seps_pi.mean()),
                1,
            ),
            'Sep_Pi_P2_5': round(
                sep_pi_lo,
                1,
            ),
            'Sep_Pi_P97_5': round(
                sep_pi_hi,
                1,
            ),
            'Sep_Sbar_mean': round(
                float(seps_sbar.mean()),
                1,
            ),
            'Standardized_distance_Pi': round(
                standardized_pi,
                2,
            ),
            'Standardized_distance_Sbar': round(
                standardized_sbar,
                2,
            ),
            'Status': (
                'Empirical overlapping control-window diagnostic; '
                'percentile range is not a confidence interval'
            ),
        }

        all_results.append(
            result
        )

        print(
            f'\n  {name} '
            f'({n_windows} windows of '
            f'{win_size} observations):'
        )

        print(
            f'    Pi_crisis = {pi_crisis:.6f}'
        )

        print(
            f'    Pi_ctrl = {mean_pi:.6f} '
            f'+/- {std_pi:.6f}'
        )

        print(
            f'    Sep(Pi): mean='
            f'{seps_pi.mean():.1f}x '
            f'[empirical P2.5-P97.5: '
            f'{sep_pi_lo:.1f}x-{sep_pi_hi:.1f}x]'
        )

        print(
            f'    Sep(Sbar): mean='
            f'{seps_sbar.mean():.1f}x'
        )

        print(
            f'    Standardized distance: '
            f'Pi={standardized_pi:.2f}, '
            f'Sbar={standardized_sbar:.2f}'
        )

    if len(all_results) != len(CASES):
        raise RuntimeError(
            f"Expected {len(CASES)} sliding-control rows, "
            f"got {len(all_results)}."
        )

    df = pd.DataFrame(
        all_results
    )

    df.to_csv(
        os.path.join(
            OUT_DIR,
            'table_v13_sliding_controls.csv',
        ),
        index=False,
    )

    print(
        '\n  Saved: table_v13_sliding_controls.csv'
    )

    return all_results

# ================================================================
# ENHANCEMENT 2: BLOCK PERMUTATION TEST
# ================================================================

def run_block_permutation():
    """
    Retrospective alignment-permutation diagnostic.

    Independent shuffle matches the hardened run_all.py null:
    each normalized channel is independently permuted with a
    deterministic per-case RNG stream.

    Block shuffle independently permutes contiguous blocks within
    each channel. This preserves ordering inside each block while
    disrupting cross-channel alignment. It is a sensitivity
    diagnostic, not a formal proof that autocorrelation has been
    fully controlled.
    """

    print(f'\n\n{"=" * 75}')
    print(
        f'  ENHANCEMENT 2: Block Permutation Diagnostic '
        f'(N = {N_PERM:,})'
    )
    print(
        '  Contiguous within-block ordering retained; '
        'cross-channel block alignment permuted'
    )
    print('=' * 75)

    block_sizes_daily = [
        5,
        10,
        20,
    ]

    block_sizes_monthly = [
        2,
        3,
        4,
    ]

    all_results = []

    for case_index, (name, info) in enumerate(
        CASES.items()
    ):
        cr, _ = load_case(name)
        dt = case_dt(name)

        rho = cr[
            'rho_norm'
        ].to_numpy(dtype=float)

        psi = cr[
            'psi_norm'
        ].to_numpy(dtype=float)

        omega = cr[
            'omega_norm'
        ].to_numpy(dtype=float)

        n = len(rho)

        if n < 2:
            raise ValueError(
                f"{name}: permutation requires at least "
                "2 observations."
            )

        actual_pi = float(
            np.sum(
                rho * psi * omega
            ) * dt
        )

        if not np.isfinite(actual_pi):
            raise ValueError(
                f"{name}: actual Pi is non-finite."
            )

        # Exact deterministic independent-null convention used
        # by hardened run_all.py.
        independent_rng = np.random.default_rng(
            np.random.SeedSequence(
                [
                    RNG_SEED,
                    case_index,
                ]
            )
        )

        shuffled_indep = np.empty(
            N_PERM,
            dtype=float,
        )

        for i in range(N_PERM):
            shuffled_indep[i] = (
                np.sum(
                    rho[
                        independent_rng.permutation(n)
                    ]
                    * psi[
                        independent_rng.permutation(n)
                    ]
                    * omega[
                        independent_rng.permutation(n)
                    ]
                )
                * dt
            )

        indep_summary = permutation_summary(
            actual_pi,
            shuffled_indep,
            f"{name}/Independent",
        )

        print(f'\n  {name} (n={n}):')

        print(
            '    Independent shuffle: '
            f'z={indep_summary["z"]:.2f}, '
            f'p_MC={indep_summary["p"]:.6g}, '
            f'exceed={indep_summary["exceedances"]}/{N_PERM}'
        )

        if info['freq'] == 'monthly':
            block_sizes = (
                block_sizes_monthly
            )
        elif info['freq'] == 'daily':
            block_sizes = (
                block_sizes_daily
            )
        else:
            raise ValueError(
                f"{name}: unsupported frequency "
                f"{info['freq']!r}."
            )

        for block_size in block_sizes:
            if block_size >= n:
                raise ValueError(
                    f"{name}: configured block size "
                    f"{block_size} is not valid for n={n}."
                )

            # Separate deterministic stream for every
            # case/block-size combination.
            block_rng = np.random.default_rng(
                np.random.SeedSequence(
                    [
                        RNG_SEED,
                        case_index,
                        block_size,
                    ]
                )
            )

            shuffled_block = np.empty(
                N_PERM,
                dtype=float,
            )

            for i in range(N_PERM):
                r_s = block_shuffle(
                    rho,
                    block_size,
                    block_rng,
                )

                p_s = block_shuffle(
                    psi,
                    block_size,
                    block_rng,
                )

                o_s = block_shuffle(
                    omega,
                    block_size,
                    block_rng,
                )

                shuffled_block[i] = (
                    np.sum(
                        r_s * p_s * o_s
                    )
                    * dt
                )

            block_summary = permutation_summary(
                actual_pi,
                shuffled_block,
                f"{name}/Block B={block_size}",
            )

            print(
                f'    Block B={block_size}: '
                f'z={block_summary["z"]:.2f}, '
                f'p_MC={block_summary["p"]:.6g}, '
                f'exceed={block_summary["exceedances"]}/{N_PERM}'
            )

            all_results.append({
                'Case': name,
                'N': n,
                'Block_size': block_size,
                'Method': f'Block B={block_size}',
                'Actual_Pi': round(
                    actual_pi,
                    6,
                ),
                'Mean_shuffled': round(
                    block_summary['mean'],
                    6,
                ),
                'Std_shuffled': round(
                    block_summary['std'],
                    6,
                ),
                'z_score': round(
                    block_summary['z'],
                    2,
                ),
                'p_value_plus_one': (
                    block_summary['p']
                ),
                'Exceedances': (
                    block_summary['exceedances']
                ),
                'N_permutations': N_PERM,
                'Seed': RNG_SEED,
                'Case_seed_index': case_index,
                'Block_seed_component': block_size,
                'Significant_005': (
                    'Yes'
                    if block_summary['p'] < 0.05
                    else 'No'
                ),
                'Significant_001': (
                    'Yes'
                    if block_summary['p'] < 0.001
                    else 'No'
                ),
            })

        all_results.append({
            'Case': name,
            'N': n,
            'Block_size': 1,
            'Method': 'Independent',
            'Actual_Pi': round(
                actual_pi,
                6,
            ),
            'Mean_shuffled': round(
                indep_summary['mean'],
                6,
            ),
            'Std_shuffled': round(
                indep_summary['std'],
                6,
            ),
            'z_score': round(
                indep_summary['z'],
                2,
            ),
            'p_value_plus_one': (
                indep_summary['p']
            ),
            'Exceedances': (
                indep_summary['exceedances']
            ),
            'N_permutations': N_PERM,
            'Seed': RNG_SEED,
            'Case_seed_index': case_index,
            'Block_seed_component': 0,
            'Significant_005': (
                'Yes'
                if indep_summary['p'] < 0.05
                else 'No'
            ),
            'Significant_001': (
                'Yes'
                if indep_summary['p'] < 0.001
                else 'No'
            ),
        })

    expected_rows = len(CASES) * 4

    if len(all_results) != expected_rows:
        raise RuntimeError(
            f"Expected {expected_rows} permutation rows, "
            f"got {len(all_results)}."
        )

    df = pd.DataFrame(
        all_results
    )

    numeric_columns = [
        'Actual_Pi',
        'Mean_shuffled',
        'Std_shuffled',
        'z_score',
        'p_value_plus_one',
        'Exceedances',
        'N_permutations',
        'Seed',
        'Case_seed_index',
        'Block_seed_component',
    ]

    if not np.isfinite(
        df[numeric_columns].to_numpy(
            dtype=float
        )
    ).all():
        raise ValueError(
            "Permutation output contains non-finite values."
        )

    if (
        (df['p_value_plus_one'] <= 0).any()
        or (df['p_value_plus_one'] > 1).any()
    ):
        raise ValueError(
            "Permutation p-values must lie in (0, 1]."
        )

    df.to_csv(
        os.path.join(
            OUT_DIR,
            'table_v13_block_permutation.csv',
        ),
        index=False,
    )

    print(f'\n  {"-" * 75}')
    print(
        '  Summary: Independent vs Block Permutation'
    )
    print(f'  {"-" * 75}')

    for name in CASES:
        sub = df[
            df['Case'] == name
        ]

        independent = sub[
            sub['Method'] == 'Independent'
        ]

        if len(independent) != 1:
            raise RuntimeError(
                f"{name}: expected one independent row."
            )

        block_rows = sub[
            sub['Method'].str.startswith(
                'Block B='
            )
        ]

        if len(block_rows) != 3:
            raise RuntimeError(
                f"{name}: expected three block rows."
            )

        all_sig = bool(
            (
                block_rows['p_value_plus_one']
                < 0.05
            ).all()
        )

        print(
            f'  {name:<18} '
            f'indep_z='
            f'{independent.iloc[0]["z_score"]:<6} '
            f'all_block_p<0.05='
            f'{"Yes" if all_sig else "No"}'
        )

    print(
        '\n  Saved: table_v13_block_permutation.csv'
    )

    return df

# ================================================================
# MAIN
# ================================================================

def main():
    print()
    print(
        '╔' + '═' * 73 + '╗'
    )
    print(
        '║  Π FRAMEWORK — v13 RETROSPECTIVE AUDIT DIAGNOSTICS'.ljust(74)
        + '║'
    )
    print(
        '║  Sliding control windows + alignment permutation sensitivity'.ljust(74)
        + '║'
    )
    print(
        '╚' + '═' * 73 + '╝'
    )

    print(
        f'  Data directory: {DATA_DIR}'
    )

    print(
        f'  Permutations: {N_PERM:,}; '
        f'base seed: {RNG_SEED}'
    )

    missing = []

    for name, info in CASES.items():
        for role in [
            'crisis',
            'control',
        ]:
            file_path = os.path.join(
                DATA_DIR,
                info[role],
            )

            if not os.path.exists(
                file_path
            ):
                missing.append(
                    f'{name}/{role}'
                )

    if missing:
        raise FileNotFoundError(
            'Missing required case files: '
            + ', '.join(missing)
        )

    print(
        '  All required data files found.'
    )

    run_sliding_controls()
    run_block_permutation()

    required_outputs = [
        'table_v13_sliding_controls.csv',
        'table_v13_block_permutation.csv',
    ]

    for filename in required_outputs:
        output_path = os.path.join(
            OUT_DIR,
            filename,
        )

        if (
            not os.path.exists(output_path)
            or os.path.getsize(output_path) <= 0
        ):
            raise RuntimeError(
                f"Missing or empty required output: "
                f"{filename}"
            )

    print(f'\n{"=" * 75}')
    print(
        '  v13 RETROSPECTIVE AUDIT SUMMARY'
    )
    print(f'{"=" * 75}')
    print(
        '  1. Overlapping sliding control-window '
        'descriptive distributions computed'
    )
    print(
        '  2. Independent and contiguous-block '
        'alignment permutation diagnostics computed'
    )

    print('\n  Output files:')

    for filename in required_outputs:
        output_path = os.path.join(
            OUT_DIR,
            filename,
        )

        print(
            f'    {filename} '
            f'({os.path.getsize(output_path)} bytes)'
        )

    print()

if __name__ == '__main__':
    main()
