from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf


ROOT = Path(__file__).resolve().parents[2]

CANDIDATE_PATH = (
    ROOT
    / "zenodo_v4"
    / "holdout2"
    / "holdout2_candidate_universe.csv"
)

OUT_PATH = (
    ROOT
    / "zenodo_v4"
    / "holdout2"
    / "holdout2_eligibility_audit.csv"
)

# Frozen Holdout-2 eligibility constants.
CUTOFF = pd.Timedelta(hours=15)

DEV_START = pd.Timestamp("2010-06-08")
DEV_END = pd.Timestamp("2011-09-29")

REQUIRED_PRE = 250
REQUIRED_POST = 250

# The Tohoku/Fukushima mainshock is the known development event.
# The ID is resolved from the frozen USGS candidate universe.
PRIOR_PROJECT_EVENT_IDS = {
    "official20110311054624120_30",
}

# Broad retrieval envelope used only to establish the common valid
# financial-date index. Eligibility itself is determined below.
DATA_START = "1993-01-01"
DATA_END = "2026-10-01"


def download_close(ticker):
    data = yf.download(
        ticker,
        start=DATA_START,
        end=DATA_END,
        progress=False,
        auto_adjust=False,
    )

    if data.empty:
        raise RuntimeError(
            f"{ticker}: provider returned no data. "
            "Provider/network failure is not an eligibility failure."
        )

    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    if "Close" not in data.columns:
        raise RuntimeError(f"{ticker}: response has no Close column.")

    idx = pd.to_datetime(data.index)

    if getattr(idx, "tz", None) is not None:
        idx = idx.tz_localize(None)

    data.index = idx.normalize()
    data = data[~data.index.duplicated(keep="last")].sort_index()

    close = pd.to_numeric(data["Close"], errors="coerce")

    if close.dropna().empty:
        raise RuntimeError(f"{ticker}: no numeric Close observations.")

    return close


def build_common_financial_index():
    nikkei_close = download_close("^N225")
    jpy_close = download_close("JPY=X")

    nikkei_ret = nikkei_close.pct_change(fill_method=None)

    psi = (
        nikkei_ret
        .rolling(5)
        .std()
        * np.sqrt(252)
    )

    omega = (
        jpy_close
        .pct_change(fill_method=None)
        .abs()
    )

    common = (
        psi.dropna()
        .index
        .intersection(omega.dropna().index)
        .sort_values()
    )

    if len(common) == 0:
        raise RuntimeError(
            "No common valid ^N225 / JPY=X transformed dates."
        )

    if common.has_duplicates:
        raise RuntimeError(
            "Common financial-date index contains duplicates."
        )

    return common


def main():
    candidates = pd.read_csv(CANDIDATE_PATH)

    required_columns = {
        "event_id",
        "utc_origin_timestamp",
        "jst_origin_timestamp",
        "jst_date",
        "jst_time",
        "magnitude",
        "latitude",
        "longitude",
        "place",
    }

    missing = required_columns - set(candidates.columns)

    if missing:
        raise RuntimeError(
            f"Candidate universe missing columns: {sorted(missing)}"
        )

    if candidates["event_id"].duplicated().any():
        raise RuntimeError("Candidate universe has duplicate event IDs.")

    common = build_common_financial_index()

    rows = []

    for _, row in candidates.iterrows():
        event_id = str(row["event_id"])

        event_date = pd.Timestamp(row["jst_date"]).normalize()

        event_time = pd.to_timedelta(
            str(row["jst_time"])
        )

        reasons = []

        prior_project_event = (
            event_id in PRIOR_PROJECT_EVENT_IDS
        )

        if prior_project_event:
            reasons.append("prior_project_development_event")

        before_cutoff = event_time < CUTOFF

        if not before_cutoff:
            reasons.append("origin_not_before_15_00_JST")

        event_date_common = event_date in common

        if not event_date_common:
            reasons.append(
                "event_date_not_common_valid_financial_date"
            )

        pre_dates = common[common < event_date]
        post_dates = common[common >= event_date]

        pre_count = len(pre_dates)
        post_count = len(post_dates)

        enough_pre = pre_count >= REQUIRED_PRE
        enough_post = post_count >= REQUIRED_POST

        if not enough_pre:
            reasons.append("fewer_than_250_pre_observations")

        if not enough_post:
            reasons.append("fewer_than_250_post_observations")

        control_start = ""
        control_end = ""
        post_start = ""
        post_end = ""
        overlaps_dev = False

        if event_date_common and enough_pre and enough_post:
            control = pre_dates[-REQUIRED_PRE:]
            post = post_dates[:REQUIRED_POST]

            control_start = control[0].strftime("%Y-%m-%d")
            control_end = control[-1].strftime("%Y-%m-%d")
            post_start = post[0].strftime("%Y-%m-%d")
            post_end = post[-1].strftime("%Y-%m-%d")

            full_window = control.append(post)

            overlaps_dev = bool(
                (
                    (full_window >= DEV_START)
                    & (full_window <= DEV_END)
                ).any()
            )

            if overlaps_dev:
                reasons.append(
                    "analysis_window_overlaps_fukushima_development_interval"
                )

        eligible = len(reasons) == 0

        rows.append(
            {
                "event_id": event_id,
                "jst_date": row["jst_date"],
                "jst_time": row["jst_time"],
                "magnitude": row["magnitude"],
                "prior_project_event": prior_project_event,
                "before_15_00_jst": before_cutoff,
                "event_date_common_valid": event_date_common,
                "available_pre_observations": pre_count,
                "available_post_observations": post_count,
                "control_start": control_start,
                "control_end": control_end,
                "post_start": post_start,
                "post_end": post_end,
                "overlaps_fukushima_development_interval": overlaps_dev,
                "eligibility_flag": eligible,
                "exclusion_reason": ";".join(reasons),
            }
        )

    audit = pd.DataFrame(rows)

    audit = (
        audit
        .sort_values("event_id")
        .reset_index(drop=True)
    )

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    audit.to_csv(OUT_PATH, index=False)

    print(f"Candidates audited: {len(audit)}")
    print(f"Eligible candidates: {int(audit['eligibility_flag'].sum())}")
    print(f"Saved: {OUT_PATH}")


if __name__ == "__main__":
    main()
