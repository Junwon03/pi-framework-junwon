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
        if not np.isfinite(tau_0) or tau_0 <= 0:
            raise ValueError("tau_0 must be positive and finite.")
        if (
            not np.isfinite(BUSINESS_DAYS_PER_YEAR)
            or BUSINESS_DAYS_PER_YEAR <= 0
        ):
            raise ValueError(
                "BUSINESS_DAYS_PER_YEAR must be positive and finite."
            )

        self.tau_0 = float(tau_0)
        self.dt = 1.0 / float(BUSINESS_DAYS_PER_YEAR)
        self.p_limits = {}
        self.is_calibrated = False
    
    # ================================================================
    # Step 1: P_limit 산출 (안정기 데이터 기반)
    # ================================================================
    def calibrate(
        self,
        rho: pd.Series,
        psi: pd.Series,
        omega: pd.Series,
        stable_start: str = STABLE_START,
        stable_end: str = STABLE_END,
        percentile: int = PLIMIT_PERCENTILE,
    ) -> Dict:
        """
        안정기 데이터에서 P_limit 산출.

        Each channel uses the declared percentile over its available
        observations inside the fixed stable period. Invalid calibration
        values are rejected rather than replaced by an arbitrary epsilon.
        """
        if not 0 < percentile <= 100:
            raise ValueError(
                f"percentile must be in (0, 100], got {percentile}."
            )

        print("\n[Calibration] 안정기 P_limit 산출")
        print(f"  안정기: {stable_start} ~ {stable_end}")
        print(f"  Percentile: {percentile}th")
        print("-" * 50)

        stable = {
            "rho": rho[stable_start:stable_end].dropna(),
            "psi": psi[stable_start:stable_end].dropna(),
            "omega": omega[stable_start:stable_end].dropna(),
        }

        for name, series in stable.items():
            if len(series) == 0:
                raise ValueError(
                    f"{name}: no calibration observations in "
                    f"{stable_start} to {stable_end}."
                )

            values = series.to_numpy(dtype=float)

            if not np.isfinite(values).all():
                raise ValueError(
                    f"{name}: calibration data contain non-finite values."
                )

            if (values < 0).any():
                raise ValueError(
                    f"{name}: calibration data must be non-negative."
                )

        candidate_limits = {
            name: float(np.percentile(series.to_numpy(dtype=float), percentile))
            for name, series in stable.items()
        }

        for name, value in candidate_limits.items():
            if not np.isfinite(value) or value <= 0:
                raise ValueError(
                    f"{name}: invalid P_limit {value}; "
                    "P_limit must be positive and finite."
                )

        # Assign state only after every calibration check has passed.
        self.p_limits = candidate_limits
        self.is_calibrated = True

        rho_stable = stable["rho"]
        psi_stable = stable["psi"]
        omega_stable = stable["omega"]

        print("\n  📊 P_limit 결과:")
        print(f"     ρ P_limit: {self.p_limits['rho']:.6f}")
        print(f"     Ψ P_limit: {self.p_limits['psi']:.6f}")
        print(f"     Ω P_limit: {self.p_limits['omega']:.2f}")

        print("\n  📈 안정기 통계:")
        print(
            f"     ρ: mean={rho_stable.mean():.6f}, "
            f"std={rho_stable.std():.6f}, "
            f"max={rho_stable.max():.6f}"
        )
        print(
            f"     Ψ: mean={psi_stable.mean():.6f}, "
            f"std={psi_stable.std():.6f}, "
            f"max={psi_stable.max():.6f}"
        )
        print(
            f"     Ω: mean={omega_stable.mean():.2f}, "
            f"std={omega_stable.std():.2f}, "
            f"max={omega_stable.max():.2f}"
        )

        return self.p_limits

    # ================================================================
    # Step 2: 정규화
    # ================================================================
    def normalize(
        self,
        rho: pd.Series,
        psi: pd.Series,
        omega: pd.Series,
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        P_limit 기반 정규화.

        ρ̃ = ρ / P_limit_ρ
        Ψ̃ = Ψ / P_limit_Ψ
        Ω̃ = Ω / P_limit_Ω

        Invalid negative or non-finite inputs are rejected rather than
        silently clipped or replaced.
        """
        if not self.is_calibrated:
            raise RuntimeError("calibrate()를 먼저 실행하세요!")

        channels = {
            "rho": rho,
            "psi": psi,
            "omega": omega,
        }

        for name, series in channels.items():
            if not isinstance(series, pd.Series):
                raise TypeError(f"{name} must be a pandas Series.")
            if series.empty:
                raise ValueError(f"{name} must not be empty.")

            values = series.to_numpy(dtype=float)

            if not np.isfinite(values).all():
                raise ValueError(
                    f"{name}: normalization input contains non-finite values."
                )

            if (values < 0).any():
                raise ValueError(
                    f"{name}: normalization input must be non-negative."
                )

            p_limit = self.p_limits.get(name)
            if p_limit is None:
                raise RuntimeError(f"Missing calibrated P_limit for {name}.")
            if not np.isfinite(p_limit) or p_limit <= 0:
                raise RuntimeError(
                    f"{name}: calibrated P_limit must be positive and finite."
                )

        rho_norm = rho / self.p_limits["rho"]
        psi_norm = psi / self.p_limits["psi"]
        omega_norm = omega / self.p_limits["omega"]

        normalized = {
            "rho_norm": rho_norm,
            "psi_norm": psi_norm,
            "omega_norm": omega_norm,
        }

        for name, series in normalized.items():
            values = series.to_numpy(dtype=float)

            if not np.isfinite(values).all():
                raise ValueError(
                    f"{name}: normalized values contain non-finite values."
                )
            if (values < 0).any():
                raise ValueError(
                    f"{name}: normalized values must be non-negative."
                )

        return rho_norm, psi_norm, omega_norm

    # ================================================================
    # Step 3: 응력 S(t) 계산
    # ================================================================
    def compute_stress(
        self,
        rho_norm: pd.Series,
        psi_norm: pd.Series,
        omega_norm: pd.Series,
    ) -> pd.Series:
        """순간 응력 S(t) = ρ̃(t) · Ψ̃(t) · Ω̃(t)."""
        if not (
            rho_norm.index.equals(psi_norm.index)
            and rho_norm.index.equals(omega_norm.index)
        ):
            raise ValueError(
                "Normalized channel indices must match exactly."
            )

        if rho_norm.empty:
            raise ValueError("Cannot compute stress from empty channels.")

        for name, series in {
            "rho_norm": rho_norm,
            "psi_norm": psi_norm,
            "omega_norm": omega_norm,
        }.items():
            values = series.to_numpy(dtype=float)

            if not np.isfinite(values).all():
                raise ValueError(
                    f"{name}: stress input contains non-finite values."
                )
            if (values < 0).any():
                raise ValueError(
                    f"{name}: stress input must be non-negative."
                )

        stress = rho_norm * psi_norm * omega_norm
        values = stress.to_numpy(dtype=float)

        if not np.isfinite(values).all():
            raise ValueError("Stress contains non-finite values.")
        if (values < 0).any():
            raise ValueError("Stress must be non-negative.")

        return stress

    # ================================================================
    # Step 4: Π 누적 적분
    # ================================================================
    def compute_pi(self, stress: pd.Series) -> pd.Series:
        """Π(T) = cumulative sum of S(t) · Δt / τ₀."""
        if stress.empty:
            raise ValueError("Cannot compute Pi from an empty stress series.")

        values = stress.to_numpy(dtype=float)

        if not np.isfinite(values).all():
            raise ValueError("Stress contains non-finite values.")
        if (values < 0).any():
            raise ValueError("Stress must be non-negative.")

        if not np.isfinite(self.dt) or self.dt <= 0:
            raise RuntimeError("dt must be positive and finite.")
        if not np.isfinite(self.tau_0) or self.tau_0 <= 0:
            raise RuntimeError("tau_0 must be positive and finite.")

        increment = stress * (self.dt / self.tau_0)
        pi = increment.cumsum()

        pi_values = pi.to_numpy(dtype=float)
        if not np.isfinite(pi_values).all():
            raise ValueError("Pi contains non-finite values.")

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

        if len(common_idx) == 0:
            raise ValueError("No common analysis dates across rho/psi/omega.")
        if common_idx.has_duplicates:
            raise ValueError("Common analysis index contains duplicate dates.")
        if not common_idx.is_monotonic_increasing:
            common_idx = common_idx.sort_values()

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
