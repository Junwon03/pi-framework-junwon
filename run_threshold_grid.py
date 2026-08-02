"""Legacy audit of the retrospective pattern-label threshold grid.

Evaluates all combinations of the existing retrospective label rules:

- Pre-loaded cutoff: 0.70, 0.75, 0.80, 0.85, 0.90
- Ductile timing cutoff: 200, 250, 300, 350, 400 days
- Cumulative-trajectory fraction: 0.05, 0.10, 0.15, 0.20

This produces 5 x 5 x 4 = 100 combinations per selected case. The labels
depend on post hoc event dates and final cumulative trajectories, and several
baseline crossings occur within the corresponding control windows. The
analysis is retained for audit reproducibility but excluded from the revised
evidentiary package. It does not establish validated classes, warning lead
times, or predictive performance.

Output filenames and numerical procedures remain unchanged.

Outputs
-------
output/table_threshold_grid_labels.csv
output/table_threshold_grid_retention.csv
"""

from __future__ import annotations

from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd


BASE = Path(__file__).resolve().parent
OUT_DIR = BASE / "output"

PRELOADED_CUTOFFS = (0.70, 0.75, 0.80, 0.85, 0.90)
DUCTILE_CUTOFFS = (200, 250, 300, 350, 400)
ONSET_FRACTIONS = (0.05, 0.10, 0.15, 0.20)

BASELINE_PRELOADED = 0.80
BASELINE_DUCTILE = 300
BASELINE_ONSET = 0.10

CASES = {
    "2008 Financial": {
        "crisis": "crisis_2008_pi.csv",
        "control": "control_2004_2006_pi.csv",
        "collapse": "2008-09-15",
    },
    "Terra-Luna": {
        "crisis": "crisis_terra_luna_pi.csv",
        "control": "control_terra_luna_pi.csv",
        "collapse": "2022-05-09",
    },
    "Fukushima": {
        "crisis": "crisis_fukushima_pi.csv",
        "control": "control_fukushima_pi.csv",
        "collapse": "2011-03-11",
    },
    "COVID-19": {
        "crisis": "crisis_covid_pi.csv",
        "control": "control_covid_pi.csv",
        "collapse": "2020-03-23",
    },
    "Supply Chain": {
        "crisis": "crisis_supply_chain_pi.csv",
        "control": "control_supply_chain_pi.csv",
        "collapse": "2021-10-01",
    },
}

VALID_LABELS = {"Pre-loaded", "Ductile", "Brittle"}


def locate_data_dir() -> Path:
    """Validate the canonical lowercase data directory."""
    required = {
        "crisis_2008_pi.csv",
        "control_2004_2006_pi.csv",
        "crisis_terra_luna_pi.csv",
        "control_terra_luna_pi.csv",
    }
    candidate = BASE / "data"

    if candidate.is_dir() and all(
        (candidate / filename).is_file()
        for filename in required
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


def load_crisis(case_name: str) -> pd.DataFrame:
    """Load one crisis series and reconstruct cumulative Pi."""
    crisis_path = DATA_DIR / CASES[case_name]["crisis"]

    frame = pd.read_csv(
        crisis_path,
        index_col=0,
        parse_dates=True,
    ).sort_index()

    if frame.empty:
        raise ValueError(f"{case_name}: empty crisis input")

    if "stress" not in frame.columns:
        raise ValueError(f"{case_name}: missing stress column")

    if frame.index.has_duplicates:
        raise ValueError(f"{case_name}: duplicate dates")

    if frame["stress"].isna().any():
        raise ValueError(f"{case_name}: missing stress values")

    if (frame["stress"] < 0).any():
        raise ValueError(f"{case_name}: negative stress values")

    dt = estimate_dt(frame)
    frame["pi"] = (frame["stress"] * dt).cumsum()

    return frame


def calculate_metrics(
    crisis: pd.DataFrame,
    collapse_date: pd.Timestamp,
    onset_fraction: float,
) -> dict[str, object]:
    """Calculate the metrics used by the existing label rule."""
    pi_final = float(crisis["pi"].iloc[-1])

    if not np.isfinite(pi_final) or pi_final <= 0:
        raise ValueError("Final cumulative Pi must be finite and positive.")

    nearest_position = crisis.index.get_indexer(
        [collapse_date],
        method="nearest",
    )[0]

    nearest_date = crisis.index[nearest_position]
    pi_at_collapse = float(crisis["pi"].iloc[nearest_position])
    pct_of_max = pi_at_collapse / pi_final * 100.0

    crossing_threshold = pi_final * onset_fraction
    crossings = crisis.index[crisis["pi"] >= crossing_threshold]

    if len(crossings) == 0:
        first_crossing = pd.NaT
        lead_days = np.nan
    else:
        first_crossing = crossings[0]
        lead_days = int((collapse_date - first_crossing).days)

    return {
        "Nearest_observation_date": nearest_date.date().isoformat(),
        "Pi_at_event": pi_at_collapse,
        "Pi_final": pi_final,
        "Pct_of_max": pct_of_max,
        "First_crossing_date": (
            first_crossing.date().isoformat()
            if not pd.isna(first_crossing)
            else ""
        ),
        "Lead_days": lead_days,
    }


def assign_label(
    pct_of_max: float,
    lead_days: float,
    preloaded_cutoff: float,
    ductile_cutoff: int,
) -> str:
    """Apply the existing ordered exploratory label rule."""
    if pct_of_max > preloaded_cutoff * 100.0:
        return "Pre-loaded"

    if np.isfinite(lead_days) and lead_days > ductile_cutoff:
        return "Ductile"

    return "Brittle"


def evaluate_configuration(
    crisis: pd.DataFrame,
    collapse_date: pd.Timestamp,
    preloaded_cutoff: float,
    ductile_cutoff: int,
    onset_fraction: float,
) -> dict[str, object]:
    """Evaluate one complete threshold combination."""
    metrics = calculate_metrics(
        crisis,
        collapse_date,
        onset_fraction,
    )

    label = assign_label(
        pct_of_max=float(metrics["Pct_of_max"]),
        lead_days=float(metrics["Lead_days"]),
        preloaded_cutoff=preloaded_cutoff,
        ductile_cutoff=ductile_cutoff,
    )

    return {
        **metrics,
        "Label": label,
    }


def build_grid_table() -> pd.DataFrame:
    """Evaluate 100 threshold combinations for each selected case."""
    rows: list[dict[str, object]] = []

    combinations = list(
        product(
            PRELOADED_CUTOFFS,
            DUCTILE_CUTOFFS,
            ONSET_FRACTIONS,
        )
    )

    if len(combinations) != 100:
        raise AssertionError("Threshold grid must contain 100 combinations.")

    for case_name, info in CASES.items():
        crisis = load_crisis(case_name)
        collapse_date = pd.Timestamp(info["collapse"])

        baseline_result = evaluate_configuration(
            crisis=crisis,
            collapse_date=collapse_date,
            preloaded_cutoff=BASELINE_PRELOADED,
            ductile_cutoff=BASELINE_DUCTILE,
            onset_fraction=BASELINE_ONSET,
        )
        baseline_label = baseline_result["Label"]

        for combination_id, (
            preloaded_cutoff,
            ductile_cutoff,
            onset_fraction,
        ) in enumerate(combinations, start=1):
            result = evaluate_configuration(
                crisis=crisis,
                collapse_date=collapse_date,
                preloaded_cutoff=preloaded_cutoff,
                ductile_cutoff=ductile_cutoff,
                onset_fraction=onset_fraction,
            )

            rows.append({
                "Case": case_name,
                "Combination_id": combination_id,
                "Event_date": collapse_date.date().isoformat(),
                "Preloaded_cutoff": preloaded_cutoff,
                "Ductile_lead_cutoff_days": ductile_cutoff,
                "Onset_fraction": onset_fraction,
                "Nearest_observation_date": (
                    result["Nearest_observation_date"]
                ),
                "Pi_at_event": result["Pi_at_event"],
                "Pi_final": result["Pi_final"],
                "Pct_of_max": result["Pct_of_max"],
                "First_crossing_date": result["First_crossing_date"],
                "Lead_days": result["Lead_days"],
                "Label": result["Label"],
                "Baseline_label": baseline_label,
                "Retains_baseline_label": (
                    "Yes"
                    if result["Label"] == baseline_label
                    else "No"
                ),
            })

    grid = pd.DataFrame(rows)

    numeric_columns = [
        "Preloaded_cutoff",
        "Onset_fraction",
        "Pi_at_event",
        "Pi_final",
        "Pct_of_max",
    ]
    grid[numeric_columns] = grid[numeric_columns].round(10)

    return grid


def build_retention_table(grid: pd.DataFrame) -> pd.DataFrame:
    """Summarize label retention and label counts by case."""
    rows: list[dict[str, object]] = []

    for case_name in CASES:
        case_grid = grid.loc[grid["Case"] == case_name].copy()

        if len(case_grid) != 100:
            raise AssertionError(
                f"{case_name}: expected 100 grid combinations, "
                f"found {len(case_grid)}"
            )

        baseline_labels = case_grid["Baseline_label"].unique()
        if len(baseline_labels) != 1:
            raise AssertionError(
                f"{case_name}: inconsistent baseline labels"
            )

        label_counts = case_grid["Label"].value_counts()
        retained_count = int(
            (case_grid["Retains_baseline_label"] == "Yes").sum()
        )

        rows.append({
            "Case": case_name,
            "Baseline_label": baseline_labels[0],
            "Grid_combinations": len(case_grid),
            "Retained_count": retained_count,
            "Retention_rate": retained_count / len(case_grid),
            "Pre-loaded_count": int(
                label_counts.get("Pre-loaded", 0)
            ),
            "Ductile_count": int(label_counts.get("Ductile", 0)),
            "Brittle_count": int(label_counts.get("Brittle", 0)),
        })

    summary = pd.DataFrame(rows)
    summary["Retention_rate"] = summary["Retention_rate"].round(4)

    return summary


def verify_outputs(
    grid: pd.DataFrame,
    summary: pd.DataFrame,
) -> None:
    """Run internal consistency checks before writing outputs."""
    if len(grid) != 500:
        raise AssertionError(
            f"Expected 500 detailed rows, found {len(grid)}"
        )

    if len(summary) != 5:
        raise AssertionError(
            f"Expected 5 summary rows, found {len(summary)}"
        )

    if grid.duplicated(["Case", "Combination_id"]).any():
        raise AssertionError("Duplicate case/grid combinations found.")

    if not set(grid["Label"]).issubset(VALID_LABELS):
        raise AssertionError("Unexpected label found.")

    if not set(grid["Baseline_label"]).issubset(VALID_LABELS):
        raise AssertionError("Unexpected baseline label found.")

    for _, row in summary.iterrows():
        label_total = (
            int(row["Pre-loaded_count"])
            + int(row["Ductile_count"])
            + int(row["Brittle_count"])
        )
        if label_total != 100:
            raise AssertionError(
                f"{row['Case']}: label counts do not sum to 100"
            )

        if int(row["Retained_count"]) > 100:
            raise AssertionError(
                f"{row['Case']}: invalid retention count"
            )


def main() -> int:
    """Run the legacy retrospective-label threshold-grid audit."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 76)
    print("  LEGACY AUDIT: RETROSPECTIVE LABEL THRESHOLD GRID")
    print("  100 historical-rule combinations evaluated per selected case")
    print("=" * 76)
    print(f"  Data directory: {DATA_DIR}")

    grid = build_grid_table()
    summary = build_retention_table(grid)
    verify_outputs(grid, summary)

    grid_path = OUT_DIR / "table_threshold_grid_labels.csv"
    summary_path = OUT_DIR / "table_threshold_grid_retention.csv"

    grid.to_csv(grid_path, index=False)
    summary.to_csv(summary_path, index=False)

    print()
    print(summary.to_string(index=False))
    print()
    print("  Internal grid consistency: PASSED")
    print(f"  Saved: {grid_path.relative_to(BASE)}")
    print(f"  Saved: {summary_path.relative_to(BASE)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
