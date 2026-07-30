"""
Π Structural Stability Index — Phase 1 Pilot
=============================================
2008 Global Financial Crisis

실행: python main.py --fred-key YOUR_KEY
또는: config.py에 FRED_API_KEY 설정 후 python main.py

파이프라인:
    1. FRED 데이터 수집 (DFF, TEDRATE, TOTBKCR)
    2. 변수 변환 (변화율, 보간)
    3. 안정기 P_limit 산출 (순환논증 방지)
    4. 정규화 → S(t) → Π(t) 누적 적분
    5. Negative Control 비교
    6. 시각화 + 리포트
"""

import os
import sys
import argparse
import pandas as pd
import numpy as np
from datetime import datetime

from config import (
    FRED_API_KEY, OUTPUT_DIR,
    CRISIS_START, CRISIS_END,
    NEG_CONTROL_START, NEG_CONTROL_END,
    CRISIS_DATE
)
from data_fetcher import fetch_all_data
from pi_calculator import PiResearchCalculator
from visualize import (
    plot_pi_trajectory,
    plot_crisis_vs_control,
    print_summary_report
)


def run_phase1(fred_key: str = None):
    """Phase 1 전체 파이프라인 실행"""
    
    # API 키 설정
    if fred_key:
        import config
        config.FRED_API_KEY = fred_key
        from data_fetcher import fetch_fred_series  # reload with new key
    
    print("")
    print("╔" + "═" * 68 + "╗")
    print("║" + "  Π STRUCTURAL STABILITY INDEX".center(68) + "║")
    print("║" + "  Phase 1 Pilot: 2008 Global Financial Crisis".center(68) + "║")
    print("║" + f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}".center(68) + "║")
    print("╚" + "═" * 68 + "╝")
    print("")
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # ============================================================
    # Step 1: 데이터 수집
    # ============================================================
    print("━" * 60)
    print("  STEP 1: 데이터 수집")
    print("━" * 60)
    
    data = fetch_all_data()
    
    # ============================================================
    # Step 2: Calibration (P_limit 산출)
    # ============================================================
    print("\n" + "━" * 60)
    print("  STEP 2: P_limit Calibration")
    print("━" * 60)
    
    calculator = PiResearchCalculator()
    p_limits = calculator.calibrate(
        rho=data['rho'],
        psi=data['psi'],
        omega=data['omega']
    )
    
    # ============================================================
    # Step 3: 위기 기간 Π 계산
    # ============================================================
    print("\n" + "━" * 60)
    print("  STEP 3: Crisis Period Π 계산")
    print(f"  기간: {CRISIS_START} ~ {CRISIS_END}")
    print("━" * 60)
    
    crisis_result = calculator.calculate(
        rho=data['rho'],
        psi=data['psi'],
        omega=data['omega'],
        analysis_start=CRISIS_START,
        analysis_end=CRISIS_END
    )
    
    print(f"\n  ✅ 계산 완료: {len(crisis_result)} 데이터 포인트")
    print(f"     Π range: {crisis_result['pi'].min():.6f} ~ {crisis_result['pi'].max():.6f}")
    
    # ============================================================
    # Step 4: Negative Control Π 계산
    # ============================================================
    print("\n" + "━" * 60)
    print("  STEP 4: Negative Control Π 계산")
    print(f"  기간: {NEG_CONTROL_START} ~ {NEG_CONTROL_END}")
    print("━" * 60)
    
    control_result = calculator.calculate(
        rho=data['rho'],
        psi=data['psi'],
        omega=data['omega'],
        analysis_start=NEG_CONTROL_START,
        analysis_end=NEG_CONTROL_END
    )
    
    print(f"\n  ✅ 계산 완료: {len(control_result)} 데이터 포인트")
    print(f"     Π range: {control_result['pi'].min():.6f} ~ {control_result['pi'].max():.6f}")
    
    # ============================================================
    # Step 5: 결과 저장
    # ============================================================
    print("\n" + "━" * 60)
    print("  STEP 5: 결과 저장")
    print("━" * 60)
    
    # CSV
    crisis_csv = os.path.join(OUTPUT_DIR, 'crisis_2008_pi.csv')
    control_csv = os.path.join(OUTPUT_DIR, 'control_2004_2006_pi.csv')
    
    crisis_result.to_csv(crisis_csv)
    control_result.to_csv(control_csv)
    
    print(f"  📁 {crisis_csv}")
    print(f"  📁 {control_csv}")
    
    # P_limit 기록
    plimit_path = os.path.join(OUTPUT_DIR, 'p_limits.csv')
    pd.Series(p_limits).to_csv(plimit_path)
    print(f"  📁 {plimit_path}")
    
    # ============================================================
    # Step 6: 시각화
    # ============================================================
    print("\n" + "━" * 60)
    print("  STEP 6: 시각화")
    print("━" * 60)
    
    # Figure 1: Π 궤적
    fig1_path = os.path.join(OUTPUT_DIR, 'fig1_pi_trajectory_2008.png')
    plot_pi_trajectory(crisis_result, save_path=fig1_path)
    
    # Figure 2: Crisis vs Control
    fig2_path = os.path.join(OUTPUT_DIR, 'fig2_crisis_vs_control.png')
    plot_crisis_vs_control(crisis_result, control_result, save_path=fig2_path)
    
    # ============================================================
    # Step 7: 리포트
    # ============================================================
    print_summary_report(crisis_result, control_result, p_limits)
    
    # ============================================================
    # 판단 기준
    # ============================================================
    print("\n" + "━" * 60)
    print("  NEXT STEPS")
    print("━" * 60)
    
    # Lehman 시점 Π
    crisis_date = pd.Timestamp(CRISIS_DATE)
    if crisis_date in crisis_result.index:
        pi_lehman = crisis_result.loc[crisis_date, 'pi']
    else:
        nearest = crisis_result.index[crisis_result.index.get_indexer(
            [crisis_date], method='nearest')]
        pi_lehman = crisis_result.loc[nearest[0], 'pi']
    
    control_final = control_result['pi'].iloc[-1]
    
    separation = pi_lehman / control_final if control_final > 0 else float('inf')
    
    print(f"""
    위기 시점 Π: {pi_lehman:.6f}
    Control Π:  {control_final:.6f}
    분리도:     {separation:.2f}x
    """)
    
    if separation > 3:
        print("    ✅ 수렴 관찰됨 → Phase 2 진행 (도메인 확장)")
        print("       다음 사례: Terra-Luna (디지털자산) + Texas 정전 (물리인프라)")
    elif separation > 1.5:
        print("    🔵 부분적 수렴 → 변수/파라미터 조정 후 재실행")
        print("       검토 대상: DELTA_DAYS, PLIMIT_PERCENTILE, 변수 선택")
    else:
        print("    ⚠️ 수렴 미관찰 → 모델 근본 재검토 필요")
        print("       검토 대상: 적분 구조, 정규화 방식, 변수 매핑")
    
    print("\n" + "═" * 60)
    print(f"  📁 모든 결과: {os.path.abspath(OUTPUT_DIR)}")
    print("═" * 60 + "\n")
    
    return {
        'crisis': crisis_result,
        'control': control_result,
        'p_limits': p_limits,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Π Structural Stability Index - Phase 1 Pilot'
    )
    parser.add_argument(
        '--fred-key', type=str, default=None,
        help='FRED API Key (또는 config.py에 설정)'
    )
    
    args = parser.parse_args()
    
    key = args.fred_key or FRED_API_KEY
    
    if key == "YOUR_FRED_API_KEY_HERE" or not key:
        print("❌ FRED API 키를 설정하세요!")
        print("   방법 1: python main.py --fred-key YOUR_KEY")
        print("   방법 2: config.py의 FRED_API_KEY 수정")
        sys.exit(1)
    
    results = run_phase1(fred_key=key)
