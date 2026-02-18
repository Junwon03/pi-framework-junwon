"""
Π Phase 1 - Data Fetcher
=========================
FRED API에서 원시 데이터 수집 + 변환
"""

import pandas as pd
import numpy as np
from fredapi import Fred
from config import (
    FRED_API_KEY, FRED_SERIES,
    DATA_START, DATA_END,
    DELTA_DAYS
)


def fetch_fred_series(series_id: str, start: str, end: str) -> pd.Series:
    """FRED에서 단일 시리즈 가져오기"""
    fred = Fred(api_key=FRED_API_KEY)
    
    print(f"  Fetching {series_id}...")
    data = fred.get_series(series_id, start, end)
    
    # 인덱스 정규화
    data.index = pd.to_datetime(data.index).tz_localize(None).normalize()
    data = data[~data.index.duplicated(keep='last')]
    data = data.sort_index()
    
    # NaN 처리 (FRED는 결측일이 있음)
    data = data.replace('.', np.nan).astype(float)
    
    print(f"    ✅ {series_id}: {len(data)} rows "
          f"({data.index[0].strftime('%Y-%m-%d')} ~ {data.index[-1].strftime('%Y-%m-%d')})")
    
    return data


def compute_rate_of_change(series: pd.Series, delta: int = DELTA_DAYS) -> pd.Series:
    """
    변화율 절대값 계산: |Δ(delta일)|
    
    F = ma: 시스템 충격은 수준이 아니라 변화 속도에서 온다.
    절대값: 방향이 아니라 크기가 손상을 만든다.
    """
    change = series.diff(delta).abs()
    return change


def interpolate_monthly_to_daily(monthly: pd.Series, daily_index: pd.DatetimeIndex) -> pd.Series:
    """
    월별 데이터를 일별로 선형 보간
    
    Ω(구조적 결합)는 slow-varying 상태량.
    일별 데이터를 쓰면 오히려 노이즈가 끼어 물리적 의미 훼손.
    """
    # 월별 데이터를 일별 인덱스에 합치기
    combined = monthly.reindex(monthly.index.union(daily_index))
    # 선형 보간
    interpolated = combined.interpolate(method='time')
    # 일별 인덱스로 정렬
    result = interpolated.reindex(daily_index)
    # 앞뒤 채우기 (데이터 시작/끝 결측)
    result = result.ffill().bfill()
    
    return result


def fetch_all_data(start: str = DATA_START, end: str = DATA_END) -> dict:
    """
    모든 원시 데이터 수집 및 변환
    
    Returns:
        {
            'rho_raw': FEDFUNDS 원시,
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
    
    # ρ: FEDFUNDS |Δ5일|
    rho = compute_rate_of_change(rho_raw, DELTA_DAYS)
    print(f"  ρ (FEDFUNDS |Δ{DELTA_DAYS}일|): {rho.dropna().shape[0]} valid points")
    
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
        'ρ (FEDFUNDS Δ)': data['rho'].tail(10),
        'Ψ (TEDRATE Δ)': data['psi'].tail(10),
        'Ω (TOTBKCR)': data['omega'].tail(10),
    })
    print(sample.to_string())
