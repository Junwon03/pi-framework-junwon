"""Deterministic metric alignment for the three additional comparison cases.

Reads only frozen CSV inputs from data/. It preserves the archived cumulative
ratio as a legacy descriptive quantity using the historical fixed
per-observation repository weights. Those weights are not elapsed-time
integration. The mean-stress ratio is applied uniformly across all cases.

These cases are exploratory boundary comparisons, not formal negative controls
or independent validation episodes.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


BASE = Path(__file__).resolve().parent
DATA_DIR = BASE / "data"
OUT_DIR = BASE / "output"

CASES = {
    "2000 Dot-com Crash": {
        "crisis": "crisis_dotcom_pi.csv",
        "control": "control_dotcom_pi.csv",
        "frequency": "weekly",
    },
    "2019 Repo Near-miss": {
        "crisis": "crisis_repo_pi.csv",
        "control": "control_repo_pi.csv",
        "frequency": "weekly",
    },
    "2011 Thailand Floods": {
        "crisis": "crisis_thailand_pi.csv",
        "control": "control_thailand_pi.csv",
        "frequency": "monthly",
    },
}

REQUIRED_COLUMNS = (
    "rho_norm",
    "psi_norm",
    "omega_norm",
    "stress",
)


def load_frame(path: Path, label: str) -> pd.DataFrame:
    """Load and validate one frozen case input."""
    if not path.is_file():
        raise FileNotFoundError(f"Missing {label} input: {path}")

    frame = pd.read_csv(
        path,
        index_col=0,
        parse_dates=True,
    ).sort_index()

    if frame.empty:
        raise ValueError(f"{label}: empty input")

    if frame.index.has_duplicates:
        raise ValueError(f"{label}: duplicate dates")

    missing = [
        column
        for column in REQUIRED_COLUMNS
        if column not in frame.columns
    ]
    if missing:
        raise ValueError(f"{label}: missing columns {missing}")

    if frame[list(REQUIRED_COLUMNS)].isna().any().any():
        raise ValueError(f"{label}: null values in required columns")

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
            f"{label}: stored stress differs from normalized channel product"
        )

    return frame


def legacy_observation_weight(frequency: str) -> float:
    """Return the archived fixed per-observation repository weight.

    Weekly cases retain the historical 1/365 weight solely to reproduce the
    archived legacy cumulative quantities. It must not be interpreted as the
    elapsed duration represented by one weekly observation.
    """
    weights = {
        "daily": 1.0 / 365.0,
        "weekly": 1.0 / 365.0,
        "monthly": 1.0 / 12.0,
    }

    try:
        return weights[frequency]
    except KeyError as error:
        raise ValueError(
            f"Unsupported source frequency: {frequency}"
        ) from error


def build_table() -> pd.DataFrame:
    """Calculate legacy cumulative and revised mean-stress ratios."""
    rows: list[dict[str, object]] = []

    for case_name, info in CASES.items():
        crisis = load_frame(
            DATA_DIR / info["crisis"],
            f"{case_name} crisis",
        )
        control = load_frame(
            DATA_DIR / info["control"],
            f"{case_name} control",
        )

        overlap = crisis.index.intersection(control.index)
        if len(overlap) != 0:
            raise ValueError(
                f"{case_name}: expected non-overlapping windows, "
                f"found {len(overlap)} shared dates"
            )

        legacy_weight = legacy_observation_weight(
            info["frequency"]
        )

        cumulative_crisis = float(
            (crisis["stress"] * legacy_weight).sum()
        )
        cumulative_control = float(
            (control["stress"] * legacy_weight).sum()
        )
        mean_crisis = float(crisis["stress"].mean())
        mean_control = float(control["stress"].mean())

        if cumulative_control <= 0 or mean_control <= 0:
            raise ValueError(
                f"{case_name}: control denominator must be positive"
            )

        rows.append({
            "Case": case_name,
            "Frequency": info["frequency"],
            "Legacy_observation_weight": legacy_weight,
            "Legacy_weight_interpretation": (
                "Fixed per-observation repository weight; "
                "not elapsed-time integration"
            ),
            "Crisis_start": crisis.index.min().date().isoformat(),
            "Crisis_end": crisis.index.max().date().isoformat(),
            "Control_start": control.index.min().date().isoformat(),
            "Control_end": control.index.max().date().isoformat(),
            "N_crisis": len(crisis),
            "N_control": len(control),
            "N_exact_overlap": len(overlap),
            "Cumulative_crisis": cumulative_crisis,
            "Cumulative_control": cumulative_control,
            "Legacy_cumulative_ratio": (
                cumulative_crisis / cumulative_control
            ),
            "Mean_stress_crisis": mean_crisis,
            "Mean_stress_control": mean_control,
            "Exploratory_mean_stress_ratio": (
                mean_crisis / mean_control
            ),
            "Interpretive_status": (
                "Exploratory boundary comparison"
            ),
        })

    result = pd.DataFrame(rows)

    numeric_columns = [
        "Legacy_observation_weight",
        "Cumulative_crisis",
        "Cumulative_control",
        "Legacy_cumulative_ratio",
        "Mean_stress_crisis",
        "Mean_stress_control",
        "Exploratory_mean_stress_ratio",
    ]
    result[numeric_columns] = result[numeric_columns].round(10)

    return result


def main() -> int:
    """Generate the deterministic additional-case metric table."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    table = build_table()
    output_path = OUT_DIR / "table_additional_metric_alignment.csv"
    table.to_csv(output_path, index=False)

    print("=" * 76)
    print("  ADDITIONAL-CASE METRIC ALIGNMENT")
    print("  Legacy cumulative ratio retained for audit; mean-stress ratio is exploratory")
    print("=" * 76)
    print(
        table[
            [
                "Case",
                "N_crisis",
                "N_control",
                "N_exact_overlap",
                "Legacy_cumulative_ratio",
                "Exploratory_mean_stress_ratio",
            ]
        ].to_string(index=False)
    )
    print()
    print(f"  Saved: {output_path.relative_to(BASE)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
