"""
Π Phase 1 - Core Calculator
=============================
순수 누적 적분 기반 Π 지수 계산

수학적 정의:
    S(t) = ρ̃(t) · Ψ̃(t) · Ω̃(t)
    Π(T) = Σ S(t) · Δt/τ₀

물리적 근거:
    - 열역학 제2법칙: 비가역적 엔트로피 누적
    - 볼츠만 통계역학: 미시상태 소진 (W → 1)
    - 슈뢰딩거: 중첩 상태의 붕괴 (파동함수 collapse)
    - Miner's Rule: D = Σ(nᵢ/Nᵢ), D → 1.0에서 파단

정규화:
    - 안정기(위기 이전) 99th percentile = P_limit
    - 각 변수를 P_limit으로 나눠 0~1 비율로
    - Miner's Rule의 Nᵢ에 해당
    - 순환 논증 방지: 기준은 붕괴 이전 데이터만으로 결정
"""

import pandas as pd
import numpy as np
from typing import Tuple, Dict
from config import (
    STABLE_START, STABLE_END,
    PLIMIT_PERCENTILE,
    TAU_0, BUSINESS_DAYS_PER_YEAR
)


class PiResearchCalculator:
    """
    연구용 Π 계산기
    
    대시보드 버전과의 핵심 차이:
    1. Percentile rank가 아닌 P_limit 기반 정규화
    2. EMA smoothing이 아닌 순수 누적 적분
    3. 안정기 데이터로 사전적 기준 설정 (순환논증 방지)
    """
    
    def __init__(self, tau_0: float = TAU_0):
        self.tau_0 = tau_0
        self.dt = 1.0 / BUSINESS_DAYS_PER_YEAR  # 일별 시간 단위 (연 기준)
        self.p_limits = {}
        self.is_calibrated = False
    
    # ================================================================
    # Step 1: P_limit 산출 (안정기 데이터 기반)
    # ================================================================
    def calibrate(self, 
                  rho: pd.Series, 
                  psi: pd.Series, 
                  omega: pd.Series,
                  stable_start: str = STABLE_START,
                  stable_end: str = STABLE_END,
                  percentile: int = PLIMIT_PERCENTILE) -> Dict:
        """
        안정기 데이터에서 P_limit 산출
        
        Miner's Rule의 Nᵢ에 해당:
        재료역학에서 S-N curve로 한계를 미리 측정하듯,
        위기 이전 안정기의 99th percentile을 구조적 한계용량으로 설정.
        
        Returns:
            각 변수의 P_limit 딕셔너리
        """
        print("\n[Calibration] 안정기 P_limit 산출")
        print(f"  안정기: {stable_start} ~ {stable_end}")
        print(f"  Percentile: {percentile}th")
        print("-" * 50)
        
        # 안정기 슬라이싱
        rho_stable = rho[stable_start:stable_end].dropna()
        psi_stable = psi[stable_start:stable_end].dropna()
        omega_stable = omega[stable_start:stable_end].dropna()
        
        if len(rho_stable) == 0 or len(psi_stable) == 0 or len(omega_stable) == 0:
            raise ValueError("안정기 데이터 부족! 기간 설정 확인 필요.")
        
        # P_limit 계산
        self.p_limits = {
            'rho': np.percentile(rho_stable, percentile),
            'psi': np.percentile(psi_stable, percentile),
            'omega': np.percentile(omega_stable, percentile),
        }
        
        # 0 방지 (division by zero)
        for key in self.p_limits:
            if self.p_limits[key] == 0 or np.isnan(self.p_limits[key]):
                self.p_limits[key] = 1e-10
                print(f"  ⚠️ {key} P_limit = 0 → 1e-10으로 대체")
        
        self.is_calibrated = True
        
        # 리포트
        print(f"\n  📊 P_limit 결과:")
        print(f"     ρ P_limit: {self.p_limits['rho']:.6f}")
        print(f"     Ψ P_limit: {self.p_limits['psi']:.6f}")
        print(f"     Ω P_limit: {self.p_limits['omega']:.2f}")
        
        # 안정기 통계
        print(f"\n  📈 안정기 통계:")
        print(f"     ρ: mean={rho_stable.mean():.6f}, "
              f"std={rho_stable.std():.6f}, "
              f"max={rho_stable.max():.6f}")
        print(f"     Ψ: mean={psi_stable.mean():.6f}, "
              f"std={psi_stable.std():.6f}, "
              f"max={psi_stable.max():.6f}")
        print(f"     Ω: mean={omega_stable.mean():.2f}, "
              f"std={omega_stable.std():.2f}, "
              f"max={omega_stable.max():.2f}")
        
        return self.p_limits
    
    # ================================================================
    # Step 2: 정규화
    # ================================================================
    def normalize(self, 
                  rho: pd.Series, 
                  psi: pd.Series, 
                  omega: pd.Series) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        P_limit 기반 정규화: 각 변수를 [0, ∞) → 클립 없이 비율로 변환
        
        ρ̃ = ρ / P_limit_ρ
        Ψ̃ = Ψ / P_limit_Ψ
        Ω̃ = Ω / P_limit_Ω
        
        위기 구간에서 1.0 초과 가능 = 한계용량 초과 상태.
        이것이 Miner's Rule에서 nᵢ/Nᵢ > 1인 과부하 사이클에 해당.
        """
        if not self.is_calibrated:
            raise RuntimeError("calibrate()를 먼저 실행하세요!")
        
        rho_norm = rho / self.p_limits['rho']
        psi_norm = psi / self.p_limits['psi']
        omega_norm = omega / self.p_limits['omega']
        
        # 0 미만 방지 (변화율은 이미 절대값이므로 이론상 불필요하지만 안전장치)
        rho_norm = rho_norm.clip(lower=0)
        psi_norm = psi_norm.clip(lower=0)
        omega_norm = omega_norm.clip(lower=0)
        
        return rho_norm, psi_norm, omega_norm
    
    # ================================================================
    # Step 3: 응력 S(t) 계산
    # ================================================================
    def compute_stress(self,
                       rho_norm: pd.Series,
                       psi_norm: pd.Series,
                       omega_norm: pd.Series) -> pd.Series:
        """
        순간 응력: S(t) = ρ̃(t) · Ψ̃(t) · Ω̃(t)
        
        곱 구조의 물리적 의미:
        - 세 메커니즘이 독립적으로 작용하는 것이 아니라 상승적(multiplicatively)으로 작용
        - 하나라도 0이면 전체 응력이 0 (안전 메커니즘)
        - 모두 높으면 기하급수적 증폭 (파국적 상승)
        """
        stress = rho_norm * psi_norm * omega_norm
        return stress
    
    # ================================================================
    # Step 4: Π 누적 적분
    # ================================================================
    def compute_pi(self, stress: pd.Series) -> pd.Series:
        """
        Π(T) = Σ_{t=0}^{T} S(t) · Δt / τ₀
        
        순수 누적. 감쇠 없음.
        
        물리적 근거:
        - 열역학 제2법칙: 엔트로피는 비가역적으로 증가
        - Miner's Rule: 누적 손상 D = Σ(nᵢ/Nᵢ), D → 1.0에서 파단
        - 상공간 소진: 접근 가능한 미시상태가 점진적으로 줄어듦
        
        τ₀로 나누는 이유:
        - 시간을 시스템 고유 시간 단위로 무차원화
        - 서로 다른 도메인의 시간 스케일을 통일
        """
        # 각 시점의 기여분
        increment = stress * (self.dt / self.tau_0)
        
        # 순수 누적 (cumulative sum)
        pi = increment.cumsum()
        
        return pi
    
    # ================================================================
    # 전체 파이프라인
    # ================================================================
    def calculate(self,
                  rho: pd.Series,
                  psi: pd.Series,
                  omega: pd.Series,
                  analysis_start: str = None,
                  analysis_end: str = None) -> pd.DataFrame:
        """
        전체 계산 파이프라인
        
        1. 정규화 (사전 calibrate 필요)
        2. 응력 S(t) 계산
        3. Π 누적 적분
        
        Returns:
            DataFrame with columns:
            [rho, psi, omega, rho_norm, psi_norm, omega_norm, stress, pi]
        """
        if not self.is_calibrated:
            raise RuntimeError("calibrate()를 먼저 실행하세요!")
        
        # 분석 기간 슬라이싱
        if analysis_start:
            rho = rho[analysis_start:]
            psi = psi[analysis_start:]
            omega = omega[analysis_start:]
        if analysis_end:
            rho = rho[:analysis_end]
            psi = psi[:analysis_end]
            omega = omega[:analysis_end]
        
        # 공통 인덱스
        common_idx = rho.index.intersection(psi.index).intersection(omega.index)
        rho = rho.reindex(common_idx)
        psi = psi.reindex(common_idx)
        omega = omega.reindex(common_idx)
        
        # 정규화
        rho_norm, psi_norm, omega_norm = self.normalize(rho, psi, omega)
        
        # 응력
        stress = self.compute_stress(rho_norm, psi_norm, omega_norm)
        
        # Π 누적 적분
        pi = self.compute_pi(stress)
        
        # 결과 조립
        result = pd.DataFrame({
            'rho': rho,
            'psi': psi,
            'omega': omega,
            'rho_norm': rho_norm,
            'psi_norm': psi_norm,
            'omega_norm': omega_norm,
            'stress': stress,
            'pi': pi,
        }, index=common_idx)
        
        return result


if __name__ == "__main__":
    print("Π Research Calculator - Phase 1")
    print("Run main.py for full pipeline.")
