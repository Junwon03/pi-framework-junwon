"""
Π Phase 1 - Data Fetcher
=========================
FRED API에서 원시 데이터 수집 + 변환
"""

import pandas as pd
import numpy as np
import requests
import config
from config import (
    FRED_SERIES,
    DATA_START, DATA_END,
    DELTA_DAYS,
)


def fetch_fred_series(series_id: str, start: str, end: str) -> pd.Series:
    """
    Fetch one exact FRED series from the explicitly configured vintage.

    Missing FRED observations remain NaN; they are not silently replaced.
    """
    api_key = config.FRED_API_KEY
    vintage_date = config.FRED_VINTAGE_DATE

    if not api_key:
        raise RuntimeError("FRED_API_KEY is required.")
    if not vintage_date:
        raise RuntimeError(
            "FRED_VINTAGE_DATE is required for reproducible retrieval."
        )

    print(
        f"  Fetching {series_id} "
        f"(FRED vintage {vintage_date})..."
    )

    url = "https://api.stlouisfed.org/fred/series/observations"
    params = {
        "series_id": series_id,
        "api_key": api_key,
        "file_type": "json",
        "observation_start": start,
        "observation_end": end,
        "realtime_start": vintage_date,
        "realtime_end": vintage_date,
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise RuntimeError(
            f"FRED request failed for {series_id}: {exc}"
        ) from exc

    try:
        payload = response.json()
    except ValueError as exc:
        raise RuntimeError(
            f"FRED returned invalid JSON for {series_id}."
        ) from exc

    observations = payload.get("observations")
    if not observations:
        raise RuntimeError(
            f"FRED returned no observations for {series_id} "
            f"from {start} to {end} at vintage {vintage_date}."
        )

    frame = pd.DataFrame(observations)
    required = {"date", "value"}
    if not required.issubset(frame.columns):
        raise RuntimeError(
            f"Malformed FRED response for {series_id}: "
            f"missing {sorted(required - set(frame.columns))}"
        )

    dates = pd.to_datetime(frame["date"], errors="coerce")
    values = pd.to_numeric(frame["value"], errors="coerce")

    data = pd.Series(
        values.to_numpy(),
        index=dates,
        name=series_id,
        dtype=float,
    )
    data = data.loc[data.index.notna()]
    data.index = pd.DatetimeIndex(data.index).tz_localize(None).normalize()
    data = data[~data.index.duplicated(keep="last")].sort_index()

    valid = data.dropna()
    if valid.empty:
        raise RuntimeError(
            f"No numeric observations remain for FRED series {series_id}."
        )
    if not np.isfinite(valid.to_numpy(dtype=float)).all():
        raise RuntimeError(
            f"Non-finite numeric observations found in {series_id}."
        )

    print(
        f"    {series_id}: {len(data)} rows, "
        f"{len(valid)} numeric "
        f"({data.index[0].strftime('%Y-%m-%d')} ~ "
        f"{data.index[-1].strftime('%Y-%m-%d')})"
    )

    return data


def compute_rate_of_change(series: pd.Series, delta: int = DELTA_DAYS) -> pd.Series:
    """
    변화율 절대값 계산: |Δ(delta일)|
    
    F = ma: 시스템 충격은 수준이 아니라 변화 속도에서 온다.
    절대값: 방향이 아니라 크기가 손상을 만든다.
    """
    change = series.diff(delta).abs()
    return change


def interpolate_monthly_to_daily(
    lower_frequency: pd.Series,
    daily_index: pd.DatetimeIndex,
) -> pd.Series:
    """
    Retrospectively interpolate a lower-frequency state series to target dates.

    Linear interpolation is allowed only between observed source values.
    A trailing target date may carry forward the latest prior observation.
    Leading values are never backward-filled from future observations.
    """
    source = lower_frequency.dropna().copy()
    source.index = pd.DatetimeIndex(source.index)
    source = source[~source.index.duplicated(keep="last")].sort_index()

    target = pd.DatetimeIndex(daily_index)
    if source.empty:
        raise ValueError("Cannot interpolate an empty source series.")
    if target.empty:
        raise ValueError("Cannot interpolate to an empty target index.")
    if target.has_duplicates:
        raise ValueError("Target index contains duplicate dates.")

    combined_index = source.index.union(target).sort_values()
    combined = source.reindex(combined_index)

    # Retrospective two-sided interpolation is restricted to the interior
    # of observed source dates. This does not extrapolate into the past.
    interpolated = combined.interpolate(
        method="time",
        limit_area="inside",
    )

    # Forward fill only permits use of an already observed past value at
    # the trailing boundary. There is deliberately no backward fill.
    result = interpolated.reindex(target).ffill()

    if result.isna().any():
        missing = result.index[result.isna()]
        raise ValueError(
            "TOTBKCR alignment has no prior/bridging observation for "
            f"{len(missing)} target date(s); first missing target is "
            f"{missing[0].date()}."
        )

    values = result.to_numpy(dtype=float)
    if not np.isfinite(values).all():
        raise ValueError(
            "Interpolated TOTBKCR series contains non-finite values."
        )

    return result


def fetch_all_data(start: str = DATA_START, end: str = DATA_END) -> dict:
    """
    모든 원시 데이터 수집 및 변환
    
    Returns:
        {
            'rho_raw': DFF 원시,
            'psi_raw': TEDRATE 원시,
            'omega_raw': TOTBKCR 원시,
            'rho': |Δ5일| 변화율,
            'psi': |Δ5일| 변화율,
            'omega': 보간된 수준값,
            'dates': 공통 일별 인덱스,
        }
    """
    print("=" * 60)
    print("  Π Phase 1 - Data Collection")
    print("=" * 60)
    
    # 1. 원시 데이터 수집
    print("\n[1/3] FRED 원시 데이터 수집")
    print("-" * 40)
    
    rho_raw = fetch_fred_series(FRED_SERIES['rho'], start, end)
    psi_raw = fetch_fred_series(FRED_SERIES['psi'], start, end)
    omega_raw = fetch_fred_series(FRED_SERIES['omega'], start, end)
    
    # 2. 변환
    print("\n[2/3] 변수 변환")
    print("-" * 40)
    
    # ρ: DFF |Δ5일|
    rho = compute_rate_of_change(rho_raw, DELTA_DAYS)
    print(f"  ρ (DFF |Δ{DELTA_DAYS}일|): {rho.dropna().shape[0]} valid points")
    
    # Ψ: TEDRATE |Δ5일|
    psi = compute_rate_of_change(psi_raw, DELTA_DAYS)
    print(f"  Ψ (TEDRATE |Δ{DELTA_DAYS}일|): {psi.dropna().shape[0]} valid points")
    
    # 3. 공통 인덱스 생성 (ρ, Ψ 기준 - 일별 데이터)
    print("\n[3/3] 데이터 정렬")
    print("-" * 40)
    
    # ρ와 Ψ의 공통 일별 인덱스
    common_idx = rho.dropna().index.intersection(psi.dropna().index)
    
    # Ω: 월별 → 일별 보간
    omega = interpolate_monthly_to_daily(omega_raw, common_idx)
    print(f"  Ω (TOTBKCR 보간): {omega.dropna().shape[0]} valid points")
    
    # 최종 정렬
    rho = rho.reindex(common_idx)
    psi = psi.reindex(common_idx)
    omega = omega.reindex(common_idx)
    
    # 결측 확인
    valid_mask = rho.notna() & psi.notna() & omega.notna()
    final_idx = common_idx[valid_mask]

    if len(final_idx) == 0:
        raise ValueError("No complete aligned observations remain.")

    if final_idx.has_duplicates:
        raise ValueError("Final aligned index contains duplicate dates.")
    if not final_idx.is_monotonic_increasing:
        raise ValueError("Final aligned index is not chronological.")

    for name, series in {
        "rho": rho.reindex(final_idx),
        "psi": psi.reindex(final_idx),
        "omega": omega.reindex(final_idx),
    }.items():
        values = series.to_numpy(dtype=float)
        if not np.isfinite(values).all():
            raise ValueError(
                f"Final {name} channel contains non-finite values."
            )

    print(f"\n  📊 최종 공통 데이터: {len(final_idx)} 영업일")
    print(f"     기간: {final_idx[0].strftime('%Y-%m-%d')} ~ "
          f"{final_idx[-1].strftime('%Y-%m-%d')}")
    
    result = {
        'rho_raw': rho_raw,
        'psi_raw': psi_raw,
        'omega_raw': omega_raw,
        'rho': rho.reindex(final_idx),
        'psi': psi.reindex(final_idx),
        'omega': omega.reindex(final_idx),
        'dates': final_idx,
    }
    
    print("\n" + "=" * 60)
    print("  ✅ 데이터 수집 완료")
    print("=" * 60)
    
    return result


if __name__ == "__main__":
    data = fetch_all_data()
    
    print("\n📋 데이터 샘플 (마지막 10일):")
    sample = pd.DataFrame({
        'ρ (DFF Δ)': data['rho'].tail(10),
        'Ψ (TEDRATE Δ)': data['psi'].tail(10),
        'Ω (TOTBKCR)': data['omega'].tail(10),
    })
    print(sample.to_string())
