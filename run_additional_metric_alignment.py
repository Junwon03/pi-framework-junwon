"""Deterministic metric alignment for the three additional comparison cases.

Reads only frozen CSV inputs from data/. It preserves the original cumulative
ratio as a legacy descriptive quantity and applies the revised mean-stress
ratio uniformly across all three cases.

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
        "frequency": "daily",
    },
    "2019 Repo Near-miss": {
        "crisis": "crisis_repo_pi.csv",
        "control": "control_repo_pi.csv",
        "frequency": "daily",
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


def estimate_dt(frame: pd.DataFrame) -> float:
    """Apply the repository daily/monthly integration convention."""
    if len(frame) <= 1:
        return 1.0 / 365.0

    average_gap_days = (
        frame.index[-1] - frame.index[0]
    ).days / len(frame)

    return 1.0 / 12.0 if average_gap_days > 20 else 1.0 / 365.0


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

        dt_crisis = estimate_dt(crisis)
        dt_control = estimate_dt(control)

        cumulative_crisis = float(
            (crisis["stress"] * dt_crisis).sum()
        )
        cumulative_control = float(
            (control["stress"] * dt_control).sum()
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
            "Primary_mean_stress_ratio": (
                mean_crisis / mean_control
            ),
            "Interpretive_status": (
                "Exploratory boundary comparison"
            ),
        })

    result = pd.DataFrame(rows)

    numeric_columns = [
        "Cumulative_crisis",
        "Cumulative_control",
        "Legacy_cumulative_ratio",
        "Mean_stress_crisis",
        "Mean_stress_control",
        "Primary_mean_stress_ratio",
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
    print("  Legacy cumulative ratio retained; mean-stress ratio is primary")
    print("=" * 76)
    print(
        table[
            [
                "Case",
                "N_crisis",
                "N_control",
                "N_exact_overlap",
                "Legacy_cumulative_ratio",
                "Primary_mean_stress_ratio",
            ]
        ].to_string(index=False)
    )
    print()
    print(f"  Saved: {output_path.relative_to(BASE)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
