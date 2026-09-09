"""Verify frozen LTCM historical-holdout outputs against golden baselines."""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path


BASE = Path(__file__).resolve().parents[1]
GOLDEN_DIR = BASE / "golden" / "ltcm_holdout"
ACTUAL_DIR = BASE / "output" / "ltcm_holdout"

EXPECTED_FILES = (
    "table_ltcm_primary.csv",
    "table_ltcm_formulations.csv",
    "table_ltcm_ablation.csv",
    "table_ltcm_correlations.csv",
    "table_ltcm_permutation.csv",
    "manifest_ltcm.json",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    failures = 0
    matched = 0

    if not GOLDEN_DIR.is_dir():
        print(f"ERROR: missing golden directory: {GOLDEN_DIR}")
        return 1

    if not ACTUAL_DIR.is_dir():
        print(f"ERROR: missing actual directory: {ACTUAL_DIR}")
        return 1

    for name in EXPECTED_FILES:
        golden = GOLDEN_DIR / name
        actual = ACTUAL_DIR / name

        if not golden.is_file():
            print(f"MISSING GOLDEN: {name}")
            failures += 1
            continue

        if not actual.is_file():
            print(f"MISSING OUTPUT: {name}")
            failures += 1
            continue

        golden_hash = sha256(golden)
        actual_hash = sha256(actual)

        if golden_hash != actual_hash:
            print(f"DIFF: {name}")
            print(f"  GOLDEN_SHA256={golden_hash}")
            print(f"  ACTUAL_SHA256={actual_hash}")
            failures += 1
            continue

        print(f"MATCH: {name}")
        matched += 1

    print()
    print(
        f"SUMMARY: expected={len(EXPECTED_FILES)} "
        f"matched={matched} failed={failures}"
    )

    if failures:
        print("FAIL: LTCM holdout artifacts differ from frozen golden baselines.")
        return 1

    print("OK: all frozen LTCM holdout artifacts match golden baselines.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
