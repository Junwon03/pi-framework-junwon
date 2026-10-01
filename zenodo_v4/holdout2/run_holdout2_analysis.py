import hashlib
import io
import json
import socket
import time
from pathlib import Path

import numpy as np
import pandas as pd
import requests
import urllib3.util.connection as urllib3_connection
import yfinance as yf


# ---------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "zenodo_v4" / "holdout2"

CONFIG_PATH = ROOT / "zenodo_v4" / "config" / "holdout2_candidate_query.json"
SELECTED_EVENT_PATH = BASE / "holdout2_selected_event.json"
AUDIT_PATH = BASE / "holdout2_eligibility_audit.csv"
PREOUTPUT_MANIFEST_PATH = BASE / "holdout2_preoutput_sha256.txt"

DATA_DIR = BASE / "data"
RESULTS_DIR = BASE / "results"

USGS_RAW_PATH = DATA_DIR / "holdout2_usgs_m2plus_events.csv"
N225_RAW_PATH = DATA_DIR / "holdout2_n225_close.csv"
JPYX_RAW_PATH = DATA_DIR / "holdout2_jpyx_close.csv"

ALIGNED_PATH = RESULTS_DIR / "holdout2_aligned_series.csv"
SUMMARY_PATH = RESULTS_DIR / "holdout2_summary.json"


# Environment-specific network transport fix previously verified locally.
urllib3_connection.allowed_gai_family = lambda: socket.AF_INET


# ---------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------

def sha256_file(path):
    h = hashlib.sha256()

    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)

    return h.hexdigest()


def verify_preoutput_manifest():
    if not PREOUTPUT_MANIFEST_PATH.exists():
        raise RuntimeError("Pre-output SHA-256 manifest is missing.")

    for line in PREOUTPUT_MANIFEST_PATH.read_text(
        encoding="utf-8"
    ).splitlines():

        if not line.strip():
            continue

        expected, relative_path = line.split(maxsplit=1)

        path = ROOT / relative_path.strip()

        if not path.exists():
            raise RuntimeError(
                f"Pre-output manifest file missing: {path}"
            )

        actual = sha256_file(path)

        if actual != expected:
            raise RuntimeError(
                "Pre-output manifest verification failed:\n"
                f"file={relative_path}\n"
                f"expected={expected}\n"
                f"actual={actual}"
            )


def request_same_source(url, params, attempts=3):
    last_error = None

    for attempt in range(1, attempts + 1):
        try:
            response = requests.get(
                url,
                params=params,
                timeout=(15, 60),
            )
            response.raise_for_status()
            return response

        except requests.RequestException as exc:
            last_error = exc

            if attempt < attempts:
                time.sleep(2)

    raise RuntimeError(
        f"Request failed after {attempts} attempts: {url}: {last_error}"
    )


def save_close_snapshot(close, path):
    out = pd.DataFrame(
        {
            "date": close.index.strftime("%Y-%m-%d"),
            "close": close.to_numpy(),
        }
    )

    out.to_csv(path, index=False)


# ---------------------------------------------------------------------
# Load frozen configuration
# ---------------------------------------------------------------------

verify_preoutput_manifest()

with CONFIG_PATH.open("r", encoding="utf-8") as f:
    cfg = json.load(f)

with SELECTED_EVENT_PATH.open("r", encoding="utf-8") as f:
    selected = json.load(f)

audit = pd.read_csv(AUDIT_PATH)

event_id = str(selected["event_id"])
reference_date = pd.Timestamp(
    selected["reference_date_jst"]
).normalize()

audit_row = audit.loc[
    audit["event_id"].astype(str) == event_id
]

if len(audit_row) != 1:
    raise RuntimeError(
        f"Expected one eligibility row for {event_id}; "
        f"found {len(audit_row)}."
    )

audit_row = audit_row.iloc[0]

eligibility_value = str(
    audit_row["eligibility_flag"]
).strip().lower()

if eligibility_value != "true":
    raise RuntimeError(
        f"Selected event is not marked eligible: {event_id}"
    )

expected_control_start = pd.Timestamp(
    audit_row["control_start"]
).normalize()

expected_control_end = pd.Timestamp(
    audit_row["control_end"]
).normalize()

expected_post_start = pd.Timestamp(
    audit_row["post_start"]
).normalize()

expected_post_end = pd.Timestamp(
    audit_row["post_end"]
).normalize()

if expected_post_start != reference_date:
    raise RuntimeError(
        "Frozen audit post-start does not equal selected reference date."
    )


# ---------------------------------------------------------------------
# Financial channels
# ---------------------------------------------------------------------

def download_close(ticker, start, end_exclusive):
    data = yf.download(
        ticker,
        start=start.strftime("%Y-%m-%d"),
        end=end_exclusive.strftime("%Y-%m-%d"),
        progress=False,
        auto_adjust=False,
        actions=False,
        threads=False,
    )

    if data.empty:
        raise RuntimeError(
            f"{ticker}: provider returned no data."
        )

    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    if "Close" not in data.columns:
        raise RuntimeError(
            f"{ticker}: response has no Close column."
        )

    idx = pd.to_datetime(data.index)

    if getattr(idx, "tz", None) is not None:
        idx = idx.tz_localize(None)

    data.index = idx.normalize()

    data = (
        data[
            ~data.index.duplicated(keep="last")
        ]
        .sort_index()
    )

    close = pd.to_numeric(
        data["Close"],
        errors="coerce",
    )

    if close.dropna().empty:
        raise RuntimeError(
            f"{ticker}: no numeric Close observations."
        )

    return close


# Buffer is retrieval-only. Frozen analytical windows are determined
# below from the exact 250 + 250 aligned observations.
finance_start = expected_control_start - pd.Timedelta(days=60)
finance_end_exclusive = expected_post_end + pd.Timedelta(days=61)

n225_close = download_close(
    "^N225",
    finance_start,
    finance_end_exclusive,
)

jpyx_close = download_close(
    "JPY=X",
    finance_start,
    finance_end_exclusive,
)

n225_return = n225_close.pct_change(
    fill_method=None
)

x2_psi = (
    n225_return
    .rolling(5)
    .std()
    * np.sqrt(252)
)

x3_omega = (
    jpyx_close
    .pct_change(fill_method=None)
    .abs()
)

common_financial_dates = (
    x2_psi.dropna()
    .index
    .intersection(
        x3_omega.dropna().index
    )
    .sort_values()
)

if common_financial_dates.has_duplicates:
    raise RuntimeError(
        "Common financial-date index has duplicates."
    )

if reference_date not in common_financial_dates:
    raise RuntimeError(
        "Selected JST reference date is no longer present "
        "in the common valid financial-date index."
    )

pre_dates = common_financial_dates[
    common_financial_dates < reference_date
]

post_dates = common_financial_dates[
    common_financial_dates >= reference_date
]

if len(pre_dates) < 250:
    raise RuntimeError(
        "Fewer than 250 valid control observations."
    )

if len(post_dates) < 250:
    raise RuntimeError(
        "Fewer than 250 valid post-control observations."
    )

control_dates = pre_dates[-250:]
post_dates = post_dates[:250]

if (
    control_dates[0] != expected_control_start
    or control_dates[-1] != expected_control_end
    or post_dates[0] != expected_post_start
    or post_dates[-1] != expected_post_end
):
    raise RuntimeError(
        "Current provider data do not reproduce the frozen "
        "eligibility-audit window boundaries."
    )

analysis_dates = control_dates.append(
    post_dates
)


# ---------------------------------------------------------------------
# Physical seismic-load channel
# ---------------------------------------------------------------------

def fetch_usgs_m2plus(start_date, end_date):
    query_url = cfg["candidate_universe"]["query_endpoint"]
    count_url = cfg["candidate_universe"]["count_endpoint"]

    bounds = cfg["candidate_universe"]["geographic_bounds"]

    min_mag = float(
        cfg["fukushima_template_constants"][
            "seismic_load_minmagnitude"
        ]
    )

    start_jst = pd.Timestamp(
        start_date,
        tz="Asia/Tokyo",
    )

    end_exclusive_jst = (
        pd.Timestamp(
            end_date,
            tz="Asia/Tokyo",
        )
        + pd.Timedelta(days=1)
    )

    chunks = []

    current_jst = start_jst

    while current_jst < end_exclusive_jst:
        next_jst = min(
            current_jst + pd.DateOffset(months=1),
            end_exclusive_jst,
        )

        start_utc = current_jst.tz_convert("UTC")

        end_utc = (
            next_jst.tz_convert("UTC")
            - pd.Timedelta(microseconds=1)
        )

        base_params = {
            "starttime": start_utc.isoformat(),
            "endtime": end_utc.isoformat(),
            "eventtype": "earthquake",
            "minmagnitude": min_mag,
            "minlatitude": bounds["minlatitude"],
            "maxlatitude": bounds["maxlatitude"],
            "minlongitude": bounds["minlongitude"],
            "maxlongitude": bounds["maxlongitude"],
        }

        count_response = request_same_source(
            count_url,
            base_params,
        )

        try:
            expected_count = int(
                count_response.text.strip()
            )
        except ValueError as exc:
            raise RuntimeError(
                "USGS count response was not an integer."
            ) from exc

        if expected_count > 20000:
            raise RuntimeError(
                "USGS monthly chunk exceeds 20,000 events."
            )

        if expected_count > 0:
            query_params = dict(base_params)

            query_params.update(
                {
                    "format": "csv",
                    "orderby": "time-asc",
                    "limit": 20000,
                }
            )

            response = request_same_source(
                query_url,
                query_params,
            )

            frame = pd.read_csv(
                io.StringIO(response.text)
            )

            required = {
                "id",
                "time",
                "mag",
                "latitude",
                "longitude",
            }

            missing = required - set(
                frame.columns
            )

            if missing:
                raise RuntimeError(
                    f"USGS response missing columns: "
                    f"{sorted(missing)}"
                )

            if len(frame) != expected_count:
                raise RuntimeError(
                    "USGS completeness failure: "
                    f"count={expected_count}, "
                    f"rows={len(frame)}"
                )

            chunks.append(frame)

        current_jst = next_jst

    if not chunks:
        raise RuntimeError(
            "USGS returned no M2+ events over the analytical window."
        )

    eq = pd.concat(
        chunks,
        ignore_index=True,
    )

    if eq["id"].duplicated().any():
        raise RuntimeError(
            "USGS analytical catalog contains duplicate event IDs."
        )

    eq["mag"] = pd.to_numeric(
        eq["mag"],
        errors="coerce",
    )

    eq["utc_timestamp"] = pd.to_datetime(
        eq["time"],
        utc=True,
        errors="coerce",
    )

    if eq["mag"].isna().any():
        raise RuntimeError(
            "USGS catalog contains invalid magnitudes."
        )

    if eq["utc_timestamp"].isna().any():
        raise RuntimeError(
            "USGS catalog contains invalid timestamps."
        )

    eq["jst_timestamp"] = (
        eq["utc_timestamp"]
        .dt.tz_convert("Asia/Tokyo")
    )

    eq["jst_date"] = pd.to_datetime(
        eq["jst_timestamp"]
        .dt.strftime("%Y-%m-%d")
    )

    eq = eq[
        (eq["jst_date"] >= start_date)
        & (eq["jst_date"] <= end_date)
    ].copy()

    if (eq["mag"] < min_mag).any():
        raise RuntimeError(
            "USGS catalog contains an event below frozen M2 threshold."
        )

    eq["energy_joules"] = (
        10.0
        ** (
            1.5 * eq["mag"]
            + 4.8
        )
    )

    if not np.isfinite(
        eq["energy_joules"]
    ).all():
        raise RuntimeError(
            "Calculated seismic energy is non-finite."
        )

    return eq


usgs_events = fetch_usgs_m2plus(
    expected_control_start,
    expected_post_end,
)

daily_energy = (
    usgs_events
    .groupby("jst_date")[
        "energy_joules"
    ]
    .sum()
)

calendar = pd.date_range(
    expected_control_start,
    expected_post_end,
    freq="D",
)

daily_energy = daily_energy.reindex(
    calendar,
    fill_value=0.0,
)

x1_rho = pd.Series(
    0.0,
    index=calendar,
    name="x1_rho",
)

positive = daily_energy > 0

x1_rho.loc[positive] = np.log10(
    daily_energy.loc[positive]
)


# ---------------------------------------------------------------------
# Align frozen 250 + 250 observations
# ---------------------------------------------------------------------

x1 = x1_rho.reindex(
    analysis_dates
)

x2 = x2_psi.reindex(
    analysis_dates
)

x3 = x3_omega.reindex(
    analysis_dates
)

for name, series in {
    "x1_rho": x1,
    "x2_psi": x2,
    "x3_omega": x3,
}.items():

    values = series.to_numpy(
        dtype=float
    )

    if not np.isfinite(values).all():
        raise RuntimeError(
            f"{name}: aligned values contain non-finite observations."
        )

    if (values < 0).any():
        raise RuntimeError(
            f"{name}: aligned values must be non-negative."
        )


aligned = pd.DataFrame(
    {
        "date": analysis_dates,
        "period": (
            ["control"] * 250
            + ["post"] * 250
        ),
        "x1_rho": x1.to_numpy(),
        "x2_psi": x2.to_numpy(),
        "x3_omega": x3.to_numpy(),
    }
)


# ---------------------------------------------------------------------
# Frozen P99 normalization
# ---------------------------------------------------------------------

control_mask = (
    aligned["period"] == "control"
)

p99 = {}

for channel in [
    "x1_rho",
    "x2_psi",
    "x3_omega",
]:
    value = float(
        np.percentile(
            aligned.loc[
                control_mask,
                channel,
            ].to_numpy(dtype=float),
            99,
        )
    )

    if not np.isfinite(value) or value <= 0:
        raise RuntimeError(
            f"{channel}: invalid P99 calibration value {value}"
        )

    p99[channel] = value


aligned["z1"] = (
    aligned["x1_rho"]
    / p99["x1_rho"]
)

aligned["z2"] = (
    aligned["x2_psi"]
    / p99["x2_psi"]
)

aligned["z3"] = (
    aligned["x3_omega"]
    / p99["x3_omega"]
)

# No upper cap.
aligned["product"] = (
    aligned["z1"]
    * aligned["z2"]
    * aligned["z3"]
)

aligned["sum"] = (
    aligned["z1"]
    + aligned["z2"]
    + aligned["z3"]
)

aligned["maximum"] = aligned[
    ["z1", "z2", "z3"]
].max(axis=1)


# ---------------------------------------------------------------------
# Frozen summaries
# ---------------------------------------------------------------------

def period_mean(column, period):
    return float(
        aligned.loc[
            aligned["period"] == period,
            column,
        ].mean()
    )


operator_summary = {}

for operator in [
    "product",
    "sum",
    "maximum",
]:
    control_mean = period_mean(
        operator,
        "control",
    )

    post_mean = period_mean(
        operator,
        "post",
    )

    ratio = None

    if control_mean > 0:
        ratio = (
            post_mean
            / control_mean
        )

    operator_summary[operator] = {
        "mean_control": control_mean,
        "mean_post": post_mean,
        "post_control_ratio": (
            None
            if ratio is None
            else float(ratio)
        ),
        "ratio_defined": ratio is not None,
    }


channel_summary = {}

for channel in [
    "x1_rho",
    "x2_psi",
    "x3_omega",
]:
    channel_summary[channel] = {
        "mean_control": period_mean(
            channel,
            "control",
        ),
        "mean_post": period_mean(
            channel,
            "post",
        ),
    }


control_corr = (
    aligned.loc[
        control_mask,
        [
            "x1_rho",
            "x2_psi",
            "x3_omega",
        ],
    ]
    .corr()
)


# ---------------------------------------------------------------------
# Save reproducibility artifacts
# ---------------------------------------------------------------------

DATA_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

RESULTS_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

usgs_events.to_csv(
    USGS_RAW_PATH,
    index=False,
)

save_close_snapshot(
    n225_close,
    N225_RAW_PATH,
)

save_close_snapshot(
    jpyx_close,
    JPYX_RAW_PATH,
)

aligned_out = aligned.copy()

aligned_out["date"] = (
    aligned_out["date"]
    .dt.strftime("%Y-%m-%d")
)

aligned_out.to_csv(
    ALIGNED_PATH,
    index=False,
)


summary = {
    "status": "FROZEN_HOLDOUT2_RESULT",
    "selected_event": {
        "event_id": event_id,
        "reference_date_jst": (
            reference_date.strftime(
                "%Y-%m-%d"
            )
        ),
        "magnitude": float(
            selected["magnitude"]
        ),
        "place": selected["place"],
    },
    "analysis_window": {
        "control_observations": 250,
        "post_observations": 250,
        "control_start": (
            control_dates[0]
            .strftime("%Y-%m-%d")
        ),
        "control_end": (
            control_dates[-1]
            .strftime("%Y-%m-%d")
        ),
        "post_start": (
            post_dates[0]
            .strftime("%Y-%m-%d")
        ),
        "post_end": (
            post_dates[-1]
            .strftime("%Y-%m-%d")
        ),
    },
    "normalization_p99": p99,
    "channel_means": channel_summary,
    "control_pairwise_correlations": {
        row: {
            col: float(
                control_corr.loc[
                    row,
                    col,
                ]
            )
            for col in control_corr.columns
        }
        for row in control_corr.index
    },
    "operators": operator_summary,
    "source_artifacts": {
        "usgs_m2plus_rows": int(
            len(usgs_events)
        ),
        "usgs_sha256": sha256_file(
            USGS_RAW_PATH
        ),
        "n225_sha256": sha256_file(
            N225_RAW_PATH
        ),
        "jpyx_sha256": sha256_file(
            JPYX_RAW_PATH
        ),
        "aligned_series_sha256": sha256_file(
            ALIGNED_PATH
        ),
    },
    "frozen_rules": {
        "seismic_channel": (
            "All M>=2.0 USGS events inside the frozen Japan-region "
            "bounds are aggregated by JST calendar date; no-event "
            "days equal zero."
        ),
        "equity_channel": (
            "^N225 close daily pct return; 5-observation rolling "
            "SD annualized by sqrt(252)."
        ),
        "fx_channel": (
            "JPY=X close absolute daily pct change."
        ),
        "normalization": (
            "Channel-specific control-period P99; no upper cap."
        ),
        "primary_score": "product = z1 * z2 * z3",
        "benchmarks": [
            "sum = z1 + z2 + z3",
            "maximum = max(z1, z2, z3)",
        ],
        "primary_contrast": (
            "mean(post) / mean(control)"
        ),
    },
}

with SUMMARY_PATH.open(
    "w",
    encoding="utf-8",
) as f:
    json.dump(
        summary,
        f,
        indent=2,
        ensure_ascii=False,
    )
    f.write("\n")


print("Holdout 2 analysis completed.")
print(f"Selected event: {event_id}")
print(
    "Reference date:",
    reference_date.strftime("%Y-%m-%d"),
)

for operator in [
    "product",
    "sum",
    "maximum",
]:
    result = operator_summary[operator]

    print(
        f"{operator}: "
        f"control={result['mean_control']:.8g}, "
        f"post={result['mean_post']:.8g}, "
        f"ratio={result['post_control_ratio']}"
    )

print(f"Saved: {ALIGNED_PATH}")
print(f"Saved: {SUMMARY_PATH}")
