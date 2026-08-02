"""Verify classified deterministic artifacts against frozen baselines.

The checked package is divided into four explicit groups:

* revised primary outputs;
* active sensitivity, exploratory, and provenance outputs;
* retained legacy-audit outputs; and
* frozen input data.

The classification changes interpretation and reporting only. All 50 previously
checked artifacts remain required in their original verification order. Figures
are excluded because rendering metadata can vary by environment. Retired legacy
analyses remain available for audit reproducibility but are not golden-baseline
requirements.
"""

from __future__ import annotations

import difflib
import hashlib
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
GOLDEN = BASE / "golden"

REVISED_PRIMARY = "revised_primary"
ACTIVE_SENSITIVITY_EXPLORATORY = "active_sensitivity_exploratory"
LEGACY_AUDIT = "legacy_audit"
FROZEN_INPUT = "frozen_input"


EXPECTED_FILE_SPECS = (
    # Core run_all.py artifacts
    ("output/table1_cross_domain.csv", LEGACY_AUDIT),
    ("output/table2_mult_vs_add.csv", LEGACY_AUDIT),
    ("output/table3_permutation.csv", LEGACY_AUDIT),
    ("output/table4_failure_modes.csv", LEGACY_AUDIT),
    ("output/table_S1_plimit_sensitivity.csv", LEGACY_AUDIT),
    ("output/table_S2_variable_robustness.csv", LEGACY_AUDIT),
    ("output/table_S4_nonredundancy.csv", ACTIVE_SENSITIVITY_EXPLORATORY),
    ("output/summary.txt", LEGACY_AUDIT),

    # Original-window benchmark and enhancement artifacts
    ("output/benchmark_full.csv", LEGACY_AUDIT),
    ("output/benchmark_pivot.csv", LEGACY_AUDIT),
    ("output/benchmark_summary.txt", LEGACY_AUDIT),
    ("output/table_enhanced_time_normalized.csv", LEGACY_AUDIT),
    ("output/table_enhanced_sliding_controls.csv", LEGACY_AUDIT),
    ("output/table_enhanced_cutoff_sensitivity.csv", LEGACY_AUDIT),
    ("output/table_v13_sliding_controls.csv", LEGACY_AUDIT),
    ("output/table_v13_block_permutation.csv", LEGACY_AUDIT),

    # Revised primary non-overlap package
    ("output/table_nonoverlap_primary.csv", REVISED_PRIMARY),
    ("output/table_nonoverlap_formulations.csv", REVISED_PRIMARY),
    ("output/table_nonoverlap_ablation.csv", REVISED_PRIMARY),
    ("output/table_nonoverlap_permutation.csv", REVISED_PRIMARY),

    # Revised sensitivity, exploratory, and provenance artifacts
    (
        "output/table_nonoverlap_variable_substitution.csv",
        ACTIVE_SENSITIVITY_EXPLORATORY,
    ),
    (
        "output/table_ST15_nonoverlap_delta_k.csv",
        LEGACY_AUDIT,
    ),
    (
        "output/table_threshold_grid_labels.csv",
        LEGACY_AUDIT,
    ),
    (
        "output/table_threshold_grid_retention.csv",
        LEGACY_AUDIT,
    ),

    # Retained generated legacy-audit artifacts
    ("output/table_ST17_matched_threshold_sensitivity.csv", LEGACY_AUDIT),
    ("output/table_variable_substitution.csv", LEGACY_AUDIT),
    ("output/table_additional_cases.csv", LEGACY_AUDIT),
    ("output/table_additional_permutation.csv", LEGACY_AUDIT),
    ("output/table_additional_time_normalized.csv", LEGACY_AUDIT),

    # Revised additional-case alignment and provenance
    (
        "output/table_additional_metric_alignment.csv",
        ACTIVE_SENSITIVITY_EXPLORATORY,
    ),
    (
        "output/table_specification_provenance.csv",
        ACTIVE_SENSITIVITY_EXPLORATORY,
    ),

    # Additional retained legacy-audit artifacts
    ("output/table_additional_nonredundancy.csv", LEGACY_AUDIT),
    ("output/table_ST15_delta_k_sensitivity.csv", LEGACY_AUDIT),
    (
        "output/table_ST17_retrospective_trajectory.csv",
        LEGACY_AUDIT,
    ),

    # Frozen primary five-case inputs
    ("data/crisis_2008_pi.csv", FROZEN_INPUT),
    ("data/control_2004_2006_pi.csv", FROZEN_INPUT),
    ("data/crisis_terra_luna_pi.csv", FROZEN_INPUT),
    ("data/control_terra_luna_pi.csv", FROZEN_INPUT),
    ("data/crisis_fukushima_pi.csv", FROZEN_INPUT),
    ("data/control_fukushima_pi.csv", FROZEN_INPUT),
    ("data/crisis_covid_pi.csv", FROZEN_INPUT),
    ("data/control_covid_pi.csv", FROZEN_INPUT),
    ("data/crisis_supply_chain_pi.csv", FROZEN_INPUT),
    ("data/control_supply_chain_pi.csv", FROZEN_INPUT),

    # Additional-case frozen inputs
    ("data/crisis_dotcom_pi.csv", FROZEN_INPUT),
    ("data/control_dotcom_pi.csv", FROZEN_INPUT),
    ("data/crisis_repo_pi.csv", FROZEN_INPUT),
    ("data/control_repo_pi.csv", FROZEN_INPUT),
    ("data/crisis_thailand_pi.csv", FROZEN_INPUT),
    ("data/control_thailand_pi.csv", FROZEN_INPUT),
)


EXPECTED_FILES = tuple(
    relative_name
    for relative_name, _category in EXPECTED_FILE_SPECS
)

FILE_CATEGORY = dict(EXPECTED_FILE_SPECS)

REVISED_PRIMARY_FILES = tuple(
    relative_name
    for relative_name, category in EXPECTED_FILE_SPECS
    if category == REVISED_PRIMARY
)

ACTIVE_SENSITIVITY_EXPLORATORY_FILES = tuple(
    relative_name
    for relative_name, category in EXPECTED_FILE_SPECS
    if category == ACTIVE_SENSITIVITY_EXPLORATORY
)

LEGACY_AUDIT_FILES = tuple(
    relative_name
    for relative_name, category in EXPECTED_FILE_SPECS
    if category == LEGACY_AUDIT
)

FROZEN_INPUT_FILES = tuple(
    relative_name
    for relative_name, category in EXPECTED_FILE_SPECS
    if category == FROZEN_INPUT
)


RETIRED_LEGACY_FILES = (
    "output/table_ST16_matched_pipeline.csv",
    "output/table_ST16_method_comparison.csv",
    "output/table_ST17_pseudoprospective.csv",
)


if len(FILE_CATEGORY) != len(EXPECTED_FILE_SPECS):
    raise RuntimeError("EXPECTED_FILE_SPECS contains duplicate filenames.")

if set(EXPECTED_FILES).intersection(RETIRED_LEGACY_FILES):
    raise RuntimeError(
        "Required and retired artifact classifications overlap."
    )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def print_text_diff(
    golden_path: Path,
    actual_path: Path,
    relative_name: str,
    max_lines: int = 120,
) -> None:
    """Print a bounded unified diff for a mismatched UTF-8 text artifact."""
    try:
        golden_lines = golden_path.read_text(
            encoding="utf-8",
        ).splitlines(keepends=True)
        actual_lines = actual_path.read_text(
            encoding="utf-8",
        ).splitlines(keepends=True)
    except UnicodeDecodeError:
        print("  TEXT_DIFF: unavailable for non-UTF-8 artifact")
        return

    diff = difflib.unified_diff(
        golden_lines,
        actual_lines,
        fromfile=f"golden/{relative_name}",
        tofile=f"actual/{relative_name}",
        n=3,
    )

    printed = 0
    for line in diff:
        if printed >= max_lines:
            print(f"  ... diff truncated after {max_lines} lines")
            break
        print("  " + line.rstrip("\n"))
        printed += 1

    if printed == 0:
        print("  TEXT_DIFF: byte-level difference without line-content difference")


def main() -> int:
    if not GOLDEN.is_dir():
        print("ERROR: golden/ directory does not exist.")
        return 1

    failures = 0
    matched = 0

    for relative_name in EXPECTED_FILES:
        golden_path = GOLDEN / relative_name
        actual_path = BASE / relative_name

        if not golden_path.is_file():
            print(f"MISSING GOLDEN: {relative_name}")
            failures += 1
            continue

        if not actual_path.is_file():
            print(f"MISSING OUTPUT: {relative_name}")
            failures += 1
            continue

        golden_hash = sha256(golden_path)
        actual_hash = sha256(actual_path)

        if golden_hash != actual_hash:
            print(f"DIFF: {relative_name}")
            print(f"  GOLDEN_SHA256={golden_hash}")
            print(f"  ACTUAL_SHA256={actual_hash}")
            print_text_diff(
                golden_path,
                actual_path,
                relative_name,
            )
            failures += 1
            continue

        print(f"MATCH: {relative_name}")
        matched += 1

    present_legacy = [
        relative_name
        for relative_name in RETIRED_LEGACY_FILES
        if (BASE / relative_name).is_file()
    ]
    for relative_name in present_legacy:
        print(f"IGNORED LEGACY: {relative_name}")

    print()
    print(
        f"SUMMARY: expected={len(EXPECTED_FILES)} "
        f"matched={matched} failed={failures}"
    )

    if failures:
        print("FAIL: classified deterministic artifacts differ from the golden baselines.")
        return 1

    print(
        "OK: all classified deterministic artifacts match their "
        "golden baselines."
    )
    print(
        "CATEGORIES: "
        f"revised_primary={len(REVISED_PRIMARY_FILES)} "
        f"active_sensitivity_exploratory="
        f"{len(ACTIVE_SENSITIVITY_EXPLORATORY_FILES)} "
        f"legacy_audit={len(LEGACY_AUDIT_FILES)} "
        f"frozen_input={len(FROZEN_INPUT_FILES)}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
