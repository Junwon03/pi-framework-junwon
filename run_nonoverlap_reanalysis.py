"""Non-overlapping crisis-control reanalysis for the five selected cases.

Primary estimand
-----------------
Mean stress in the crisis-exclusive segment, defined as observations strictly
after the end of the prespecified control window, divided by mean stress in
the full prespecified control window.

The stored channel normalization and P-limits are not recalibrated here.
This script changes only the evaluation window, preserving the original
preprocessing and normalized channel values.

Outputs
-------
output/table_nonoverlap_primary.csv
output/table_nonoverlap_formulations.csv
output/table_nonoverlap_ablation.csv
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import numpy as np
import pandas as pd


BASE = Path(__file__).resolve().parent
OUT_DIR = BASE / "output"

CASES = {
    "2008 Financial": {
        "crisis": "crisis_2008_pi.csv",
        "control": "control_2004_2006_pi.csv",
        "domain": "Traditional Finance",
        "frequency": "daily",
    },
    "Terra-Luna": {
        "crisis": "crisis_terra_luna_pi.csv",
        "control": "control_terra_luna_pi.csv",
        "domain": "Digital Assets",
        "frequency": "daily",
    },
    "Fukushima": {
        "crisis": "crisis_fukushima_pi.csv",
        "control": "control_fukushima_pi.csv",
        "domain": "Physical Infrastructure",
        "frequency": "daily",
    },
    "COVID-19": {
        "crisis": "crisis_covid_pi.csv",
        "control": "control_covid_pi.csv",
        "domain": "Pandemic / Public Health",
        "frequency": "daily",
    },
    "Supply Chain": {
        "crisis": "crisis_supply_chain_pi.csv",
        "control": "control_supply_chain_pi.csv",
        "domain": "Global Logistics",
        "frequency": "monthly",
    },
}

N_PERMUTATIONS = 10_000
PERMUTATION_SEED_BASE = 20_260_731
DAILY_BLOCK_SIZES = (5, 10, 20)
MONTHLY_BLOCK_SIZES = (2, 3, 4)


REQUIRED_COLUMNS = (
    "rho_norm",
    "psi_norm",
    "omega_norm",
    "stress",
)

FORMULATIONS: tuple[
    tuple[str, Callable[[np.ndarray, np.ndarray, np.ndarray], np.ndarray]],
    ...,
] = (
    ("Multiplicative", lambda rho, psi, omega: rho * psi * omega),
    ("Additive", lambda rho, psi, omega: rho + psi + omega),
    (
        "Maximum",
        lambda rho, psi, omega: np.maximum(np.maximum(rho, psi), omega),
    ),
)

ABLATION_METHODS: tuple[
    tuple[str, str, Callable[[np.ndarray, np.ndarray, np.ndarray], np.ndarray]],
    ...,
] = (
    ("rho only", "1-Single", lambda rho, psi, omega: rho),
    ("psi only", "1-Single", lambda rho, psi, omega: psi),
    ("omega only", "1-Single", lambda rho, psi, omega: omega),
    ("rho x psi", "2-Dual", lambda rho, psi, omega: rho * psi),
    ("rho x omega", "2-Dual", lambda rho, psi, omega: rho * omega),
    ("psi x omega", "2-Dual", lambda rho, psi, omega: psi * omega),
    ("rho + psi + omega", "3-Triple", lambda rho, psi, omega: rho + psi + omega),
    (
        "max(rho,psi,omega)",
        "3-Triple",
        lambda rho, psi, omega: np.maximum(np.maximum(rho, psi), omega),
    ),
    (
        "rho x psi x omega",
        "3-Triple",
        lambda rho, psi, omega: rho * psi * omega,
    ),
)


def locate_data_dir() -> Path:
    """Validate the canonical lowercase data directory."""
    required_core = {
        "crisis_2008_pi.csv",
        "control_2004_2006_pi.csv",
        "crisis_terra_luna_pi.csv",
        "control_terra_luna_pi.csv",
    }
    candidate = BASE / "data"

    if candidate.is_dir() and all(
        (candidate / filename).is_file()
        for filename in required_core
    ):
        return candidate

    raise FileNotFoundError(
        "Could not find the tracked five-case CSV inputs in data/."
    )


DATA_DIR = locate_data_dir()


def estimate_dt(frame: pd.DataFrame) -> float:
    """Mirror the existing daily/monthly time-step convention."""
    if len(frame) <= 1:
        return 1.0 / 365.0

    average_gap_days = (
        frame.index[-1] - frame.index[0]
    ).days / len(frame)

    return 1.0 / 12.0 if average_gap_days > 20 else 1.0 / 365.0


def load_case(case_name: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load and validate one crisis/control pair."""
    info = CASES[case_name]

    crisis = pd.read_csv(
        DATA_DIR / info["crisis"],
        index_col=0,
        parse_dates=True,
    ).sort_index()

    control = pd.read_csv(
        DATA_DIR / info["control"],
        index_col=0,
        parse_dates=True,
    ).sort_index()

    for label, frame in (("crisis", crisis), ("control", control)):
        missing = [
            column
            for column in REQUIRED_COLUMNS
            if column not in frame.columns
        ]
        if missing:
            raise ValueError(
                f"{case_name} {label}: missing required columns {missing}"
            )

        if frame.empty:
            raise ValueError(f"{case_name} {label}: empty input")

        if not frame.index.is_monotonic_increasing:
            raise ValueError(f"{case_name} {label}: dates are not sorted")

        if frame.index.has_duplicates:
            raise ValueError(f"{case_name} {label}: duplicate dates found")

        if frame[list(REQUIRED_COLUMNS)].isna().any().any():
            raise ValueError(
                f"{case_name} {label}: null values in required columns"
            )

        reconstructed = (
            frame["rho_norm"]
            * frame["psi_norm"]
            * frame["omega_norm"]
        )
        if not np.allclose(
            frame["stress"],
            reconstructed,
            rtol=1e-10,
            atol=1e-12,
        ):
            raise ValueError(
                f"{case_name} {label}: stored stress is inconsistent "
                "with normalized channel product"
            )

    return crisis, control


def exclusive_segment(
    crisis: pd.DataFrame,
    control: pd.DataFrame,
) -> pd.DataFrame:
    """Return crisis observations strictly after the control end date."""
    segment = crisis.loc[crisis.index > control.index.max()].copy()

    if segment.empty:
        raise ValueError(
            "No crisis-exclusive observations remain after control end."
        )

    return segment


def channel_arrays(
    frame: pd.DataFrame,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return normalized channel arrays."""
    return (
        frame["rho_norm"].to_numpy(dtype=float),
        frame["psi_norm"].to_numpy(dtype=float),
        frame["omega_norm"].to_numpy(dtype=float),
    )


def mean_ratio(
    crisis_exclusive: pd.DataFrame,
    control: pd.DataFrame,
    stress_function: Callable[
        [np.ndarray, np.ndarray, np.ndarray],
        np.ndarray,
    ],
) -> tuple[float, float, float]:
    """Calculate exclusive-crisis mean, control mean, and their ratio."""
    crisis_stress = np.asarray(
        stress_function(*channel_arrays(crisis_exclusive)),
        dtype=float,
    )
    control_stress = np.asarray(
        stress_function(*channel_arrays(control)),
        dtype=float,
    )

    crisis_mean = float(np.mean(crisis_stress))
    control_mean = float(np.mean(control_stress))

    if not np.isfinite(crisis_mean) or not np.isfinite(control_mean):
        raise ValueError("Non-finite stress mean encountered.")

    if control_mean <= 0:
        raise ValueError("Control mean stress must be positive.")

    return crisis_mean, control_mean, crisis_mean / control_mean


def build_primary_table() -> pd.DataFrame:
    """Build window diagnostics and the primary non-overlap comparison."""
    rows: list[dict[str, object]] = []

    for case_name, info in CASES.items():
        crisis, control = load_case(case_name)
        exclusive = exclusive_segment(crisis, control)

        overlap = crisis.index.intersection(control.index)
        contained = (
            control.index.min() >= crisis.index.min()
            and control.index.max() <= crisis.index.max()
        )

        dt_crisis = estimate_dt(crisis)
        dt_control = estimate_dt(control)

        cumulative_crisis = float(
            (crisis["stress"] * dt_crisis).sum()
        )
        cumulative_control = float(
            (control["stress"] * dt_control).sum()
        )

        full_crisis_mean = float(crisis["stress"].mean())
        control_mean = float(control["stress"].mean())
        exclusive_mean = float(exclusive["stress"].mean())

        rows.append({
            "Case": case_name,
            "Domain": info["domain"],
            "Crisis_start": crisis.index.min().date().isoformat(),
            "Crisis_end": crisis.index.max().date().isoformat(),
            "Control_start": control.index.min().date().isoformat(),
            "Control_end": control.index.max().date().isoformat(),
            "Exclusive_crisis_start": (
                exclusive.index.min().date().isoformat()
            ),
            "Exclusive_crisis_end": (
                exclusive.index.max().date().isoformat()
            ),
            "N_crisis_full": len(crisis),
            "N_control": len(control),
            "N_exact_overlap": len(overlap),
            "N_crisis_exclusive": len(exclusive),
            "Control_contained_in_crisis_range": (
                "Yes" if contained else "No"
            ),
            "Control_overlap_fraction": (
                len(overlap) / len(control)
            ),
            "Cumulative_ratio_full_windows": (
                cumulative_crisis / cumulative_control
            ),
            "Mean_ratio_full_windows": (
                full_crisis_mean / control_mean
            ),
            "Mean_stress_control": control_mean,
            "Mean_stress_crisis_exclusive": exclusive_mean,
            "Nonoverlap_mean_ratio": exclusive_mean / control_mean,
        })

    result = pd.DataFrame(rows)

    numeric_columns = [
        "Control_overlap_fraction",
        "Cumulative_ratio_full_windows",
        "Mean_ratio_full_windows",
        "Mean_stress_control",
        "Mean_stress_crisis_exclusive",
        "Nonoverlap_mean_ratio",
    ]
    result[numeric_columns] = result[numeric_columns].round(10)

    return result


def build_formulation_table() -> pd.DataFrame:
    """Recalculate three aggregation formulations using the primary estimand."""
    rows: list[dict[str, object]] = []

    for case_name in CASES:
        crisis, control = load_case(case_name)
        exclusive = exclusive_segment(crisis, control)

        case_rows: list[dict[str, object]] = []

        for formulation_name, stress_function in FORMULATIONS:
            crisis_mean, control_mean, ratio = mean_ratio(
                exclusive,
                control,
                stress_function,
            )

            case_rows.append({
                "Case": case_name,
                "Formulation": formulation_name,
                "N_crisis_exclusive": len(exclusive),
                "N_control": len(control),
                "Mean_crisis_exclusive": crisis_mean,
                "Mean_control": control_mean,
                "Nonoverlap_mean_ratio": ratio,
            })

        case_frame = pd.DataFrame(case_rows)
        case_frame["Rank_within_case"] = (
            case_frame["Nonoverlap_mean_ratio"]
            .rank(method="min", ascending=False)
            .astype(int)
        )
        rows.extend(case_frame.to_dict("records"))

    result = pd.DataFrame(rows)

    numeric_columns = [
        "Mean_crisis_exclusive",
        "Mean_control",
        "Nonoverlap_mean_ratio",
    ]
    result[numeric_columns] = result[numeric_columns].round(10)

    return result


def build_ablation_table() -> pd.DataFrame:
    """Recalculate nine channel definitions using the primary estimand."""
    rows: list[dict[str, object]] = []

    for case_name in CASES:
        crisis, control = load_case(case_name)
        exclusive = exclusive_segment(crisis, control)

        case_rows: list[dict[str, object]] = []

        for method_name, level, stress_function in ABLATION_METHODS:
            crisis_mean, control_mean, ratio = mean_ratio(
                exclusive,
                control,
                stress_function,
            )

            case_rows.append({
                "Case": case_name,
                "Method": method_name,
                "Level": level,
                "N_crisis_exclusive": len(exclusive),
                "N_control": len(control),
                "Mean_crisis_exclusive": crisis_mean,
                "Mean_control": control_mean,
                "Nonoverlap_mean_ratio": ratio,
            })

        case_frame = pd.DataFrame(case_rows)
        case_frame["Rank_within_case"] = (
            case_frame["Nonoverlap_mean_ratio"]
            .rank(method="min", ascending=False)
            .astype(int)
        )
        rows.extend(case_frame.to_dict("records"))

    result = pd.DataFrame(rows)

    numeric_columns = [
        "Mean_crisis_exclusive",
        "Mean_control",
        "Nonoverlap_mean_ratio",
    ]
    result[numeric_columns] = result[numeric_columns].round(10)

    return result


def _block_shuffle(
    values: np.ndarray,
    block_size: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """Shuffle contiguous blocks while preserving order within each block."""
    n_full_blocks = len(values) // block_size
    remainder = len(values) % block_size

    blocks = [
        values[index * block_size:(index + 1) * block_size]
        for index in range(n_full_blocks)
    ]
    if remainder:
        blocks.append(values[n_full_blocks * block_size:])

    order = rng.permutation(len(blocks))
    return np.concatenate([blocks[index] for index in order])


def _permutation_summary(
    observed: float,
    null_values: np.ndarray,
) -> dict[str, float | int]:
    """Summarize a Monte Carlo null using the finite-sample plus-one rule."""
    null_mean = float(np.mean(null_values))
    null_std = float(np.std(null_values, ddof=0))
    exceedances = int(np.count_nonzero(null_values >= observed))
    p_value = (exceedances + 1) / (len(null_values) + 1)

    if null_std > 0:
        z_score = (observed - null_mean) / null_std
    else:
        z_score = float("inf") if observed > null_mean else 0.0

    return {
        "Null_mean_stress": null_mean,
        "Null_std_stress": null_std,
        "z_score": z_score,
        "Exceedance_count": exceedances,
        "p_value_plus_one": p_value,
    }


def build_permutation_table() -> pd.DataFrame:
    """Build crisis-exclusive channel-alignment permutation diagnostics.

    This diagnostic evaluates temporal alignment only within the same
    crisis-exclusive segment used by the primary comparison. It is not a
    direct test of the crisis-control difference in mean stress.
    """
    rows: list[dict[str, object]] = []

    for case_index, (case_name, info) in enumerate(CASES.items()):
        crisis, control = load_case(case_name)
        exclusive = exclusive_segment(crisis, control)
        rho, psi, omega = channel_arrays(exclusive)
        observed = float(np.mean(rho * psi * omega))

        independent_seed = PERMUTATION_SEED_BASE + case_index * 100
        independent_rng = np.random.default_rng(independent_seed)
        independent_null = np.empty(N_PERMUTATIONS, dtype=float)

        for iteration in range(N_PERMUTATIONS):
            independent_null[iteration] = float(np.mean(
                rho[independent_rng.permutation(len(rho))]
                * psi[independent_rng.permutation(len(psi))]
                * omega[independent_rng.permutation(len(omega))]
            ))

        independent_summary = _permutation_summary(
            observed,
            independent_null,
        )
        rows.append({
            "Case": case_name,
            "Frequency": info["frequency"],
            "Control_end": control.index.max().date().isoformat(),
            "Exclusive_crisis_start": (
                exclusive.index.min().date().isoformat()
            ),
            "N_crisis_exclusive": len(exclusive),
            "Method": "Independent shuffle",
            "Block_size": 1,
            "N_permutations": N_PERMUTATIONS,
            "RNG_seed": independent_seed,
            "Observed_mean_stress": observed,
            **independent_summary,
            "Significant_005": (
                "Yes"
                if independent_summary["p_value_plus_one"] < 0.05
                else "No"
            ),
        })

        block_sizes = (
            MONTHLY_BLOCK_SIZES
            if info["frequency"] == "monthly"
            else DAILY_BLOCK_SIZES
        )

        for block_offset, block_size in enumerate(block_sizes, start=1):
            if block_size >= len(exclusive):
                raise ValueError(
                    f"{case_name}: block size {block_size} is not smaller "
                    f"than exclusive sample N={len(exclusive)}."
                )

            block_seed = (
                PERMUTATION_SEED_BASE
                + case_index * 100
                + block_offset
            )
            block_rng = np.random.default_rng(block_seed)
            block_null = np.empty(N_PERMUTATIONS, dtype=float)

            for iteration in range(N_PERMUTATIONS):
                block_null[iteration] = float(np.mean(
                    _block_shuffle(rho, block_size, block_rng)
                    * _block_shuffle(psi, block_size, block_rng)
                    * _block_shuffle(omega, block_size, block_rng)
                ))

            block_summary = _permutation_summary(observed, block_null)
            rows.append({
                "Case": case_name,
                "Frequency": info["frequency"],
                "Control_end": control.index.max().date().isoformat(),
                "Exclusive_crisis_start": (
                    exclusive.index.min().date().isoformat()
                ),
                "N_crisis_exclusive": len(exclusive),
                "Method": "Block shuffle",
                "Block_size": block_size,
                "N_permutations": N_PERMUTATIONS,
                "RNG_seed": block_seed,
                "Observed_mean_stress": observed,
                **block_summary,
                "Significant_005": (
                    "Yes"
                    if block_summary["p_value_plus_one"] < 0.05
                    else "No"
                ),
            })

    result = pd.DataFrame(rows)

    expected_rows = len(CASES) * 4
    if len(result) != expected_rows:
        raise AssertionError(
            f"Expected {expected_rows} permutation rows, found {len(result)}."
        )

    numeric_columns = [
        "Observed_mean_stress",
        "Null_mean_stress",
        "Null_std_stress",
        "z_score",
        "p_value_plus_one",
    ]
    result[numeric_columns] = result[numeric_columns].round(10)

    if (result["p_value_plus_one"] <= 0).any():
        raise AssertionError("Finite Monte Carlo p-values must be positive.")

    return result


def verify_cross_table_consistency(
    primary: pd.DataFrame,
    formulations: pd.DataFrame,
    ablation: pd.DataFrame,
) -> None:
    """Verify that multiplicative results agree across all three tables."""
    primary_ratios = primary.set_index("Case")["Nonoverlap_mean_ratio"]

    formulation_ratios = (
        formulations.loc[
            formulations["Formulation"] == "Multiplicative"
        ]
        .set_index("Case")["Nonoverlap_mean_ratio"]
    )

    ablation_ratios = (
        ablation.loc[
            ablation["Method"] == "rho x psi x omega"
        ]
        .set_index("Case")["Nonoverlap_mean_ratio"]
    )

    if list(primary_ratios.index) != list(CASES):
        raise AssertionError("Primary table case order changed.")

    if not np.allclose(
        primary_ratios.to_numpy(),
        formulation_ratios.reindex(primary_ratios.index).to_numpy(),
        rtol=1e-10,
        atol=1e-10,
    ):
        raise AssertionError(
            "Primary and formulation multiplicative ratios differ."
        )

    if not np.allclose(
        primary_ratios.to_numpy(),
        ablation_ratios.reindex(primary_ratios.index).to_numpy(),
        rtol=1e-10,
        atol=1e-10,
    ):
        raise AssertionError(
            "Primary and ablation multiplicative ratios differ."
        )


def main() -> int:
    """Run the non-overlap reanalysis and save deterministic tables."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 76)
    print("  NON-OVERLAPPING CRISIS-CONTROL REANALYSIS")
    print("  Crisis-exclusive mean stress / full-control mean stress")
    print("=" * 76)
    print(f"  Data directory: {DATA_DIR}")

    primary = build_primary_table()
    formulations = build_formulation_table()
    ablation = build_ablation_table()
    permutations = build_permutation_table()

    verify_cross_table_consistency(
        primary,
        formulations,
        ablation,
    )

    primary_path = OUT_DIR / "table_nonoverlap_primary.csv"
    formulation_path = OUT_DIR / "table_nonoverlap_formulations.csv"
    ablation_path = OUT_DIR / "table_nonoverlap_ablation.csv"
    permutation_path = OUT_DIR / "table_nonoverlap_permutation.csv"

    primary.to_csv(primary_path, index=False)
    formulations.to_csv(formulation_path, index=False)
    ablation.to_csv(ablation_path, index=False)
    permutations.to_csv(permutation_path, index=False)

    print()
    print(
        primary[
            [
                "Case",
                "N_control",
                "N_crisis_exclusive",
                "Nonoverlap_mean_ratio",
            ]
        ].to_string(index=False)
    )

    print()
    print("  Crisis-exclusive independent permutation summary:")
    print(
        permutations.loc[
            permutations["Method"] == "Independent shuffle",
            [
                "Case",
                "N_crisis_exclusive",
                "z_score",
                "p_value_plus_one",
                "Significant_005",
            ],
        ].to_string(index=False)
    )

    print()
    print("  Cross-table multiplicative consistency: PASSED")
    print(f"  Saved: {primary_path.relative_to(BASE)}")
    print(f"  Saved: {formulation_path.relative_to(BASE)}")
    print(f"  Saved: {ablation_path.relative_to(BASE)}")
    print(f"  Saved: {permutation_path.relative_to(BASE)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
