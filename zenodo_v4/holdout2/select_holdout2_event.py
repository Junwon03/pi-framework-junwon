import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]

BASE = ROOT / "zenodo_v4" / "holdout2"

CANDIDATE_PATH = BASE / "holdout2_candidate_universe.csv"
AUDIT_PATH = BASE / "holdout2_eligibility_audit.csv"
SELECTION_PATH = BASE / "holdout2_selection_record.json"
SELECTED_EVENT_PATH = BASE / "holdout2_selected_event.json"

SEED = 731006


def sha256_file(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    candidates = pd.read_csv(CANDIDATE_PATH)
    audit = pd.read_csv(AUDIT_PATH)

    if candidates["event_id"].duplicated().any():
        raise RuntimeError("Duplicate event_id in candidate universe.")

    if audit["event_id"].duplicated().any():
        raise RuntimeError("Duplicate event_id in eligibility audit.")

    flag = audit["eligibility_flag"]

    if flag.dtype != bool:
        flag = (
            flag.astype(str)
            .str.strip()
            .str.lower()
            .map({"true": True, "false": False})
        )

    if flag.isna().any():
        raise RuntimeError("Invalid eligibility_flag values.")

    eligible = audit.loc[flag].copy()
    eligible = eligible.sort_values("event_id").reset_index(drop=True)

    n = len(eligible)

    if n == 0:
        raise RuntimeError(
            "No eligible Holdout-2 candidates; selection cannot proceed."
        )

    if n == 1:
        draw_index = 0
    else:
        rng = np.random.Generator(
            np.random.PCG64(
                np.random.SeedSequence([SEED])
            )
        )
        draw_index = int(rng.integers(0, n))

    selected_id = str(eligible.loc[draw_index, "event_id"])

    selected_match = candidates.loc[
        candidates["event_id"].astype(str) == selected_id
    ]

    if len(selected_match) != 1:
        raise RuntimeError(
            f"Expected exactly one candidate row for {selected_id}, "
            f"found {len(selected_match)}."
        )

    selected = selected_match.iloc[0]

    selection_record = {
        "status": "FINAL_PRE_OUTPUT_SELECTION",
        "seed": SEED,
        "rng": "NumPy Generator(PCG64(SeedSequence([731006])))",
        "eligible_candidate_count": n,
        "eligible_event_ids_sorted": eligible["event_id"].astype(str).tolist(),
        "draw_index_zero_based": draw_index,
        "selected_event_id": selected_id,
        "numpy_version": np.__version__,
        "candidate_universe_sha256": sha256_file(CANDIDATE_PATH),
        "eligibility_audit_sha256": sha256_file(AUDIT_PATH),
        "selection_script_sha256": sha256_file(Path(__file__)),
        "redraw_permitted": False,
        "selection_basis": (
            "Frozen eligibility only; no framework score, operator contrast, "
            "or outcome was used for selection."
        ),
    }

    selected_event = {
        "status": "FINAL_PRE_OUTPUT_SELECTED_EVENT",
        "event_id": selected_id,
        "utc_origin_timestamp": str(selected["utc_origin_timestamp"]),
        "jst_origin_timestamp": str(selected["jst_origin_timestamp"]),
        "reference_date_jst": str(selected["jst_date"]),
        "jst_origin_time": str(selected["jst_time"]),
        "magnitude": float(selected["magnitude"]),
        "latitude": float(selected["latitude"]),
        "longitude": float(selected["longitude"]),
        "place": str(selected["place"]),
        "control_observations": 250,
        "post_control_observations": 250,
        "control_rule": (
            "250 aligned valid observations strictly preceding "
            "the JST reference date"
        ),
        "post_control_rule": (
            "JST reference-date observation plus the next "
            "249 aligned valid observations"
        ),
        "normalization": (
            "Channel-specific P99 from control/calibration observations; "
            "no upper cap"
        ),
        "primary_score": "S = z1 * z2 * z3",
        "benchmarks": [
            "sum on identical normalized inputs",
            "maximum on identical normalized inputs",
        ],
        "result_policy": (
            "Report frozen result regardless of direction, magnitude, "
            "or operator ranking."
        ),
        "redraw_permitted": False,
    }

    with SELECTION_PATH.open("w", encoding="utf-8") as f:
        json.dump(selection_record, f, indent=2, ensure_ascii=False)
        f.write("\n")

    with SELECTED_EVENT_PATH.open("w", encoding="utf-8") as f:
        json.dump(selected_event, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"Eligible candidates: {n}")
    print(f"Draw index: {draw_index}")
    print(f"Selected event_id: {selected_id}")
    print(f"Saved: {SELECTION_PATH}")
    print(f"Saved: {SELECTED_EVENT_PATH}")


if __name__ == "__main__":
    main()
