import io
import json
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import requests
import socket
import urllib3.util.connection as urllib3_connection

# Environment-specific network fix: force IPv4 for USGS requests.
urllib3_connection.allowed_gai_family = lambda: socket.AF_INET

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "zenodo_v4" / "config" / "holdout2_candidate_query.json"
OUT_PATH = ROOT / "zenodo_v4" / "holdout2" / "holdout2_candidate_universe.csv"

with CONFIG_PATH.open("r", encoding="utf-8") as f:
    cfg = json.load(f)

u = cfg["candidate_universe"]
bounds = u["geographic_bounds"]
env = u["retrieval_utc_envelope"]
dates = u["conceptual_date_interval"]

params = {
    "starttime": env["starttime_inclusive"],
    "endtime": env["endtime_boundary"],
    "eventtype": u["eventtype"],
    "minmagnitude": u["minimum_candidate_magnitude"],
    "minlatitude": bounds["minlatitude"],
    "maxlatitude": bounds["maxlatitude"],
    "minlongitude": bounds["minlongitude"],
    "maxlongitude": bounds["maxlongitude"],
}

# Completeness check before filtering
count_resp = requests.get(
    u["count_endpoint"],
    params=params,
    timeout=60,
)
count_resp.raise_for_status()
expected_count = int(count_resp.text.strip())

if expected_count > int(u["limit"]):
    raise RuntimeError(
        f"USGS returned {expected_count} events, exceeding frozen limit {u['limit']}."
    )

query_params = dict(params)
query_params.update(
    {
        "format": u["format"],
        "orderby": u["orderby"],
        "limit": u["limit"],
    }
)

resp = requests.get(
    u["query_endpoint"],
    params=query_params,
    timeout=60,
)
resp.raise_for_status()

df = pd.read_csv(io.StringIO(resp.text))

if len(df) != expected_count:
    raise RuntimeError(
        f"Completeness failure: count endpoint={expected_count}, CSV rows={len(df)}"
    )

required = {"id", "time", "mag", "latitude", "longitude", "place"}
missing = required - set(df.columns)
if missing:
    raise RuntimeError(f"Missing USGS columns: {sorted(missing)}")

df["utc_timestamp"] = pd.to_datetime(df["time"], utc=True, errors="raise")
df["jst_timestamp"] = df["utc_timestamp"].dt.tz_convert(ZoneInfo("Asia/Tokyo"))
df["jst_date"] = df["jst_timestamp"].dt.date

start_date = pd.Timestamp(dates["start_date_inclusive"]).date()
end_date = pd.Timestamp(dates["end_date_inclusive"]).date()

df = df[
    (df["jst_date"] >= start_date)
    & (df["jst_date"] <= end_date)
].copy()

out = pd.DataFrame(
    {
        "event_id": df["id"].astype(str),
        "utc_origin_timestamp": df["utc_timestamp"].astype(str),
        "jst_origin_timestamp": df["jst_timestamp"].astype(str),
        "jst_date": df["jst_timestamp"].dt.strftime("%Y-%m-%d"),
        "jst_time": df["jst_timestamp"].dt.strftime("%H:%M:%S"),
        "magnitude": pd.to_numeric(df["mag"], errors="raise"),
        "latitude": pd.to_numeric(df["latitude"], errors="raise"),
        "longitude": pd.to_numeric(df["longitude"], errors="raise"),
        "place": df["place"].fillna("").astype(str),
        "eligibility_flag": "",
        "exclusion_reason": "",
    }
)

if out["event_id"].duplicated().any():
    dupes = out.loc[out["event_id"].duplicated(), "event_id"].tolist()
    raise RuntimeError(f"Duplicate event IDs found: {dupes}")

out = out.sort_values("event_id").reset_index(drop=True)

OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
out.to_csv(OUT_PATH, index=False)

print(f"USGS rows before JST filtering: {expected_count}")
print(f"Frozen candidate-universe rows: {len(out)}")
print(f"Saved: {OUT_PATH}")
