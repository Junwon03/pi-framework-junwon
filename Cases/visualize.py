"""
Π Phase 1 - Visualization
===========================
연구용 시각화 (논문 Figure 품질)
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Rectangle
import os
from config import CRISIS_DATE, OUTPUT_DIR


def setup_style():
    """논문 품질 스타일 설정"""
    plt.rcParams.update({
        'figure.figsize': (14, 10),
        'figure.dpi': 150,
        'font.family': 'serif',
        'font.size': 11,
        'axes.labelsize': 13,
        'axes.titlesize': 14,
        'legend.fontsize': 10,
        'figure.facecolor': 'white',
        'axes.facecolor': 'white',
        'axes.grid': True,
        'grid.alpha': 0.3,
        'grid.linestyle': '--',
    })


def plot_pi_trajectory(result: pd.DataFrame, 
                       title: str = "2008 Global Financial Crisis",
                       save_path: str = None):
    """
    Π 궤적 플롯 (메인 Figure)
    
    - 상단: Π(t) 누적 궤적 + 임계 대역
    - 하단: S(t) 순간 응력 + 개별 변수
    """
    setup_style()
    
    fig, axes = plt.subplots(3, 1, figsize=(14, 12), 
                              gridspec_kw={'height_ratios': [3, 2, 2]},
                              sharex=True)
    
    crisis_date = pd.Timestamp(CRISIS_DATE)
    
    # ─────────────────────────────────────────────
    # Panel A: Π(t) 누적 궤적
    # ─────────────────────────────────────────────
    ax1 = axes[0]
    
    ax1.plot(result.index, result['pi'], 
             color='#1a1a2e', linewidth=2.0, label='Π(t)')
    
    # Lehman 파산 수직선
    if crisis_date in result.index or crisis_date >= result.index[0]:
        ax1.axvline(x=crisis_date, color='red', linestyle='--', 
                    alpha=0.8, linewidth=1.5, label=f'Lehman ({CRISIS_DATE})')
    
    # Π 값 범위에 따라 변곡 대역 표시
    pi_max = result['pi'].max()
    if pi_max > 0:
        # 0.7 변곡점 (상대적 위치)
        ax1.axhline(y=pi_max * 0.7, color='orange', linestyle=':', 
                    alpha=0.6, linewidth=1.0, label='~70% of Π_max (inflection zone)')
    
    ax1.set_ylabel('Π(t) — Cumulative Structural Stress', fontweight='bold')
    ax1.set_title(f'Π Structural Stability Index: {title}', 
                  fontsize=15, fontweight='bold', pad=15)
    ax1.legend(loc='upper left')
    
    # ─────────────────────────────────────────────
    # Panel B: S(t) 순간 응력
    # ─────────────────────────────────────────────
    ax2 = axes[1]
    
    ax2.fill_between(result.index, result['stress'], 
                     alpha=0.4, color='#e74c3c', label='S(t) = ρ̃·Ψ̃·Ω̃')
    ax2.plot(result.index, result['stress'], 
             color='#c0392b', linewidth=0.8, alpha=0.8)
    
    if crisis_date >= result.index[0]:
        ax2.axvline(x=crisis_date, color='red', linestyle='--', alpha=0.6)
    
    ax2.set_ylabel('S(t) — Instantaneous Stress', fontweight='bold')
    ax2.legend(loc='upper left')
    
    # ─────────────────────────────────────────────
    # Panel C: 개별 정규화 변수
    # ─────────────────────────────────────────────
    ax3 = axes[2]
    
    ax3.plot(result.index, result['rho_norm'], 
             color='#3498db', linewidth=1.0, alpha=0.8, label='ρ̃ (FEDFUNDS Δ)')
    ax3.plot(result.index, result['psi_norm'], 
             color='#e67e22', linewidth=1.0, alpha=0.8, label='Ψ̃ (TEDRATE Δ)')
    ax3.plot(result.index, result['omega_norm'], 
             color='#27ae60', linewidth=1.0, alpha=0.8, label='Ω̃ (TOTBKCR)')
    
    # P_limit 기준선 (=1.0)
    ax3.axhline(y=1.0, color='gray', linestyle=':', alpha=0.5, 
                label='P_limit (= 1.0)')
    
    if crisis_date >= result.index[0]:
        ax3.axvline(x=crisis_date, color='red', linestyle='--', alpha=0.6)
    
    ax3.set_ylabel('Normalized Variables', fontweight='bold')
    ax3.set_xlabel('Date', fontweight='bold')
    ax3.legend(loc='upper left', ncol=2)
    
    # X축 포맷
    for ax in axes:
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"  📊 Figure 저장: {save_path}")
    
    plt.show()
    return fig


def plot_crisis_vs_control(crisis_result: pd.DataFrame,
                           control_result: pd.DataFrame,
                           save_path: str = None):
    """
    위기 vs Negative Control 비교 플롯
    
    핵심 검증: 위기 시 Π 급등 vs 안정기 Π 낮게 유지
    """
    setup_style()
    
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    
    # 좌측: 위기 기간
    ax1 = axes[0]
    ax1.plot(crisis_result.index, crisis_result['pi'], 
             color='#c0392b', linewidth=2.0)
    ax1.set_title('Crisis Period (2005-01 ~ 2009-03)', fontweight='bold')
    ax1.set_ylabel('Π(t)', fontweight='bold')
    ax1.set_xlabel('Date')
    
    crisis_date = pd.Timestamp(CRISIS_DATE)
    if crisis_date >= crisis_result.index[0]:
        ax1.axvline(x=crisis_date, color='red', linestyle='--', alpha=0.8,
                    label=f'Lehman ({CRISIS_DATE})')
    ax1.legend()
    
    # 우측: Negative Control
    ax2 = axes[1]
    ax2.plot(control_result.index, control_result['pi'], 
             color='#27ae60', linewidth=2.0)
    ax2.set_title('Negative Control (2004-01 ~ 2006-06)', fontweight='bold')
    ax2.set_ylabel('Π(t)', fontweight='bold')
    ax2.set_xlabel('Date')
    
    # 같은 Y축 스케일로 비교
    y_max = max(crisis_result['pi'].max(), control_result['pi'].max()) * 1.1
    ax1.set_ylim(0, y_max)
    ax2.set_ylim(0, y_max)
    
    for ax in axes:
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
    
    plt.suptitle('Π Index: Crisis Period vs Negative Control', 
                 fontsize=15, fontweight='bold', y=1.02)
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"  📊 Figure 저장: {save_path}")
    
    plt.show()
    return fig


def print_summary_report(crisis_result: pd.DataFrame,
                         control_result: pd.DataFrame,
                         p_limits: dict):
    """
    분석 결과 요약 리포트
    """
    crisis_date = pd.Timestamp(CRISIS_DATE)
    
    print("\n" + "=" * 70)
    print("  Π STRUCTURAL STABILITY INDEX — PHASE 1 PILOT REPORT")
    print("  2008 Global Financial Crisis")
    print("=" * 70)
    
    # P_limit
    print("\n  ┌─ P_limit (안정기 99th percentile) ──────────────┐")
    print(f"  │  ρ (FEDFUNDS |Δ5d|) : {p_limits['rho']:.6f}          │")
    print(f"  │  Ψ (TEDRATE |Δ5d|) : {p_limits['psi']:.6f}          │")
    print(f"  │  Ω (TOTBKCR)       : {p_limits['omega']:.2f}             │")
    print("  └──────────────────────────────────────────────────┘")
    
    # 위기 분석
    print("\n  ┌─ Crisis Period ─────────────────────────────────┐")
    
    # Lehman 시점의 Π
    if crisis_date in crisis_result.index:
        pi_at_lehman = crisis_result.loc[crisis_date, 'pi']
    else:
        # 가장 가까운 날짜
        nearest = crisis_result.index[crisis_result.index.get_indexer(
            [crisis_date], method='nearest')]
        pi_at_lehman = crisis_result.loc[nearest[0], 'pi']
    
    pi_max = crisis_result['pi'].max()
    pi_final = crisis_result['pi'].iloc[-1]
    stress_max = crisis_result['stress'].max()
    stress_max_date = crisis_result['stress'].idxmax()
    
    print(f"  │  Π at Lehman ({CRISIS_DATE}): {pi_at_lehman:.6f}     │")
    print(f"  │  Π max              : {pi_max:.6f}     │")
    print(f"  │  Π final            : {pi_final:.6f}     │")
    print(f"  │  S(t) max           : {stress_max:.6f}     │")
    print(f"  │  S(t) max date      : {stress_max_date.strftime('%Y-%m-%d')}     │")
    print("  └──────────────────────────────────────────────────┘")
    
    # Negative Control
    print("\n  ┌─ Negative Control ──────────────────────────────┐")
    
    control_pi_max = control_result['pi'].max()
    control_pi_final = control_result['pi'].iloc[-1]
    control_stress_max = control_result['stress'].max()
    
    print(f"  │  Π max              : {control_pi_max:.6f}     │")
    print(f"  │  Π final            : {control_pi_final:.6f}     │")
    print(f"  │  S(t) max           : {control_stress_max:.6f}     │")
    print("  └──────────────────────────────────────────────────┘")
    
    # 분리도
    print("\n  ┌─ Separation Test ──────────────────────────────┐")
    
    ratio = pi_at_lehman / control_pi_final if control_pi_final > 0 else float('inf')
    
    print(f"  │  Π(Lehman) / Π(Control final) = {ratio:.2f}x     │")
    
    if ratio > 3:
        print(f"  │  ✅ 명확한 분리: 위기 Π >> Control Π          │")
    elif ratio > 1.5:
        print(f"  │  🔵 부분 분리: 추가 검증 필요                  │")
    else:
        print(f"  │  ⚠️ 분리 불충분: 모델 수정 필요               │")
    
    print("  └──────────────────────────────────────────────────┘")
    
    print("\n" + "=" * 70)
    print("  Phase 1 파일럿 완료")
    print("=" * 70)


if __name__ == "__main__":
    print("Run main.py for full pipeline.")
