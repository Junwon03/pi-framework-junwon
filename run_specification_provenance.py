"""Deterministic provenance table for the five retrospective case specifications.

This is a post-review documentation artifact, not a preregistration.
It records the transformations implemented in the repository and explicitly
documents the retrospective, iterative status and raw-data provenance limits.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


BASE = Path(__file__).resolve().parent
OUT_DIR = BASE / "output"

COMMON_SELECTION_STATUS = (
    "Retrospective, domain-informed, and iteratively developed; "
    "not preregistered"
)
COMMON_NORMALIZATION = (
    "Divide by channel-specific calibration-period 99th percentile; "
    "clip lower bound at 0; no upper cap"
)

CASE_META = {
    "2008 Financial": {
        "control": "2004-01-01 to 2006-06-30",
        "crisis": "2005-01-01 to 2009-03-31",
        "calibration": "2005-01-01 to 2007-06-30",
        "calibration_relation": (
            "Overlaps the control window and extends one year beyond "
            "the control end; remains before the 2008-09-15 event date"
        ),
        "crisis_file": "data/crisis_2008_pi.csv",
        "control_file": "data/control_2004_2006_pi.csv",
        "code": "Cases/config.py; Cases/data_fetcher.py; Cases/pi_calculator.py",
        "raw_status": (
            "Processed crisis/control CSVs are frozen and hash-checked; "
            "the original FRED response snapshot and vintage manifest "
            "are not archived"
        ),
        "joint_alternative": "DGS2 x VIXCLS x COMPOUT",
    },
    "Terra-Luna": {
        "control": "2021-07-01 to 2022-01-31",
        "crisis": "2021-07-01 to 2022-07-31",
        "calibration": "2021-07-01 to 2022-03-31",
        "calibration_relation": (
            "Starts with the control window and extends two months beyond "
            "the control end; remains before the 2022-05-09 event date"
        ),
        "crisis_file": "data/crisis_terra_luna_pi.csv",
        "control_file": "data/control_terra_luna_pi.csv",
        "code": "Cases/case2_terra_luna.py",
        "raw_status": (
            "Processed crisis/control CSVs are frozen and hash-checked; "
            "the original Yahoo Finance responses and provider versions "
            "are not archived"
        ),
        "joint_alternative": "None recorded in active revised evidence",
    },
    "Fukushima": {
        "control": "2010-06-01 to 2011-02-28",
        "crisis": "2010-06-01 to 2011-09-30",
        "calibration": "2010-06-01 to 2011-02-28",
        "calibration_relation": "Identical to the control window",
        "crisis_file": "data/crisis_fukushima_pi.csv",
        "control_file": "data/control_fukushima_pi.csv",
        "code": "Cases/case3_fukushima.py",
        "raw_status": (
            "Processed crisis/control CSVs are frozen and hash-checked; "
            "the original USGS and Yahoo Finance responses are not archived"
        ),
        "joint_alternative": "None recorded in active revised evidence",
    },
    "COVID-19": {
        "control": "2019-07-01 to 2020-01-31",
        "crisis": "2019-07-01 to 2020-04-30",
        "calibration": "2019-07-01 to 2020-01-31",
        "calibration_relation": "Identical to the control window",
        "crisis_file": "data/crisis_covid_pi.csv",
        "control_file": "data/control_covid_pi.csv",
        "code": "Cases/case4_covid.py",
        "raw_status": (
            "Canonical processed crisis/control CSVs are frozen and hash-locked; "
            "the active case implementation performs no live source retrieval "
            "and has no runtime source fallback"
        ),
        "joint_alternative": "None recorded in active revised evidence",
    },
    "Supply Chain": {
        "control": "2019-01-01 to 2020-06-30",
        "crisis": "2019-01-01 to 2022-12-31",
        "calibration": "2019-01-01 to 2020-06-30",
        "calibration_relation": "Identical to the control window",
        "crisis_file": "data/crisis_supply_chain_pi.csv",
        "control_file": "data/control_supply_chain_pi.csv",
        "code": "Cases/case5_supply_chain.py",
        "raw_status": (
            "Processed crisis/control CSVs are frozen and hash-checked; "
            "the original FRED response snapshots and vintage manifest "
            "are not archived"
        ),
        "joint_alternative": "None recorded in active revised evidence",
    },
}

SPECIFICATIONS = [
    {
        "Case": "2008 Financial",
        "Channel": "rho",
        "Role_mapping": "External monetary-policy movement",
        "Series_or_input": "DFF",
        "Source_as_configured": "FRED",
        "Transformation": "Absolute 5-observation first difference",
        "Actually_tested_alternative": "DGS2 level",
    },
    {
        "Case": "2008 Financial",
        "Channel": "psi",
        "Role_mapping": "Interbank funding-stress movement",
        "Series_or_input": "TEDRATE",
        "Source_as_configured": "FRED",
        "Transformation": "Absolute 5-observation first difference",
        "Actually_tested_alternative": "VIXCLS level",
    },
    {
        "Case": "2008 Financial",
        "Channel": "omega",
        "Role_mapping": "Banking-system structural scale",
        "Series_or_input": "TOTBKCR",
        "Source_as_configured": "FRED",
        "Transformation": (
            "Level value; align to the common daily index, apply time-linear "
            "interpolation only inside the observed range, then permit "
            "trailing forward fill; no backward fill"
        ),
        "Actually_tested_alternative": (
            "COMPOUT absolute percentage change"
        ),
    },
    {
        "Case": "Terra-Luna",
        "Channel": "rho",
        "Role_mapping": "Broader crypto-market movement",
        "Series_or_input": "BTC-USD close",
        "Source_as_configured": "Yahoo Finance",
        "Transformation": "Absolute 5-observation first difference",
        "Actually_tested_alternative": (
            "None recorded in active revised evidence"
        ),
    },
    {
        "Case": "Terra-Luna",
        "Channel": "psi",
        "Role_mapping": "LUNC-specific price movement",
        "Series_or_input": "LUNC-USD close",
        "Source_as_configured": "Yahoo Finance",
        "Transformation": "Absolute 1-observation first difference",
        "Actually_tested_alternative": (
            "None recorded in active revised evidence"
        ),
    },
    {
        "Case": "Terra-Luna",
        "Channel": "omega",
        "Role_mapping": "Cross-asset return co-movement",
        "Series_or_input": "BTC-USD, ETH-USD, and LUNC-USD",
        "Source_as_configured": "Yahoo Finance",
        "Transformation": (
            "Mean pairwise correlation of log returns over the preceding "
            "60 observations, transformed as (mean correlation + 1) / 2 "
            "using only complete three-asset windows; no clipping, "
            "filling, or fallback value is applied"
        ),
        "Actually_tested_alternative": (
            "None recorded in active revised evidence"
        ),
    },
    {
        "Case": "Fukushima",
        "Channel": "rho",
        "Role_mapping": "Physical seismic load",
        "Series_or_input": (
            "Japan-region USGS earthquakes, magnitude 2.0 or greater"
        ),
        "Source_as_configured": "USGS FDSN Event API",
        "Transformation": (
            "Construct the full daily calendar; no-event days contribute "
            "rho=0. For positive-event days, convert magnitude to energy "
            "using 10^(1.5M + 4.8), sum daily energy, then take log10"
        ),
        "Actually_tested_alternative": (
            "None recorded in active revised evidence"
        ),
    },
    {
        "Case": "Fukushima",
        "Channel": "psi",
        "Role_mapping": "Japanese equity-market volatility",
        "Series_or_input": "^N225 close",
        "Source_as_configured": "Yahoo Finance",
        "Transformation": (
            "Daily percentage return; 5-observation rolling standard "
            "deviation annualized by sqrt(252)"
        ),
        "Actually_tested_alternative": (
            "None recorded in active revised evidence"
        ),
    },
    {
        "Case": "Fukushima",
        "Channel": "omega",
        "Role_mapping": "Foreign-exchange stress",
        "Series_or_input": "JPY=X close",
        "Source_as_configured": "Yahoo Finance",
        "Transformation": "Absolute daily percentage change",
        "Actually_tested_alternative": (
            "None recorded in active revised evidence"
        ),
    },
    {
        "Case": "COVID-19",
        "Channel": "rho",
        "Role_mapping": "Global epidemic load",
        "Series_or_input": "Global confirmed COVID-19 cases",
        "Source_as_configured": (
            "Frozen tracked COVID CSV; original construction metadata "
            "records Johns Hopkins CSSE"
        ),
        "Transformation": (
            "Difference global cumulative cases, clip negative revisions "
            "to zero, then apply a 7-day rolling mean"
        ),
        "Actually_tested_alternative": (
            "None recorded in active revised evidence"
        ),
    },
    {
        "Case": "COVID-19",
        "Channel": "psi",
        "Role_mapping": "Financial-market volatility",
        "Series_or_input": "^VIX close",
        "Source_as_configured": (
            "Frozen tracked COVID CSV; original construction metadata "
            "records Yahoo Finance ^VIX"
        ),
        "Transformation": "VIX closing level in the frozen construction",
        "Actually_tested_alternative": (
            "None recorded in active revised evidence"
        ),
    },
    {
        "Case": "COVID-19",
        "Channel": "omega",
        "Role_mapping": "High-yield credit-market stress",
        "Series_or_input": "BAMLH0A0HYM2",
        "Source_as_configured": (
            "Frozen tracked COVID CSV; original construction metadata "
            "records FRED BAMLH0A0HYM2"
        ),
        "Transformation": (
            "High-yield option-adjusted spread level in the frozen "
            "construction; no runtime proxy or fallback branch is active"
        ),
        "Actually_tested_alternative": (
            "No separate active revised substitution table"
        ),
    },
    {
        "Case": "Supply Chain",
        "Channel": "rho",
        "Role_mapping": "Durable-goods demand movement",
        "Series_or_input": "PCEDG",
        "Source_as_configured": "FRED",
        "Transformation": "Absolute month-over-month percentage change",
        "Actually_tested_alternative": (
            "None recorded in active revised evidence"
        ),
    },
    {
        "Case": "Supply Chain",
        "Channel": "psi",
        "Role_mapping": "Delivery-time deterioration",
        "Series_or_input": "DTCDISA066MSFRBNY",
        "Source_as_configured": "FRED",
        "Transformation": "Level value clipped at a lower bound of zero",
        "Actually_tested_alternative": (
            "None recorded in active revised evidence"
        ),
    },
    {
        "Case": "Supply Chain",
        "Channel": "omega",
        "Role_mapping": "Freight-price movement",
        "Series_or_input": "WPU3012",
        "Source_as_configured": "FRED",
        "Transformation": "Absolute month-over-month percentage change",
        "Actually_tested_alternative": (
            "None recorded in active revised evidence"
        ),
    },
]


def build_table() -> pd.DataFrame:
    """Combine row-level specifications with case-level provenance."""
    rows: list[dict[str, object]] = []

    for specification in SPECIFICATIONS:
        meta = CASE_META[specification["Case"]]
        rows.append({
            **specification,
            "Control_window": meta["control"],
            "Legacy_crisis_window": meta["crisis"],
            "Calibration_period": meta["calibration"],
            "Calibration_rule": "Channel-specific 99th percentile",
            "Calibration_relation_to_control": (
                meta["calibration_relation"]
            ),
            "Normalization": COMMON_NORMALIZATION,
            "Selection_status": COMMON_SELECTION_STATUS,
            "Joint_alternative_test": meta["joint_alternative"],
            "Frozen_crisis_input": meta["crisis_file"],
            "Frozen_control_input": meta["control_file"],
            "Code_reference": meta["code"],
            "Raw_provenance_status": meta["raw_status"],
        })

    result = pd.DataFrame(rows)

    if len(result) != 15:
        raise AssertionError(
            f"Expected 15 case-channel rows, found {len(result)}"
        )

    if result[["Case", "Channel"]].duplicated().any():
        raise AssertionError("Duplicate case-channel specification found")

    expected_channels = {"rho", "psi", "omega"}
    for case_name in CASE_META:
        channels = set(
            result.loc[result["Case"] == case_name, "Channel"]
        )
        if channels != expected_channels:
            raise AssertionError(
                f"{case_name}: channels {channels} != {expected_channels}"
            )

    for column in ("Frozen_crisis_input", "Frozen_control_input"):
        missing = [
            value
            for value in result[column].unique()
            if not (BASE / value).is_file()
        ]
        if missing:
            raise FileNotFoundError(
                f"Missing frozen inputs in {column}: {missing}"
            )

    return result


def main() -> int:
    """Generate the deterministic provenance table."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    table = build_table()
    output_path = OUT_DIR / "table_specification_provenance.csv"
    table.to_csv(output_path, index=False)

    print("=" * 76)
    print("  RETROSPECTIVE SPECIFICATION PROVENANCE")
    print("  Post-review documentation; not a preregistration")
    print("=" * 76)
    print(
        table[
            [
                "Case",
                "Channel",
                "Series_or_input",
                "Calibration_period",
                "Actually_tested_alternative",
            ]
        ].to_string(index=False)
    )
    print()
    print(f"  Rows: {len(table)}")
    print(f"  Saved: {output_path.relative_to(BASE)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
