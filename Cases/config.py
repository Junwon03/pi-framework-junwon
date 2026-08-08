"""
Π Structural Stability Index - Phase 1 Pilot Configuration
============================================================
2008 Global Financial Crisis
Physics-grounded variable mapping
"""

# ============================================================
# FRED API
# ============================================================
import os

FRED_API_KEY = os.environ.get("FRED_API_KEY", "")
FRED_VINTAGE_DATE = os.environ.get("FRED_VINTAGE_DATE", "")

# ============================================================
# 분석 기간
# ============================================================
CRISIS_DATE = "2008-09-15"          # Lehman Brothers 파산
DATA_START = "2004-01-01"           # 충분한 lookback 포함
DATA_END = "2009-06-30"             # 위기 이후 안정화까지

# 안정기: P_limit 산출용 (위기 이전)
STABLE_START = "2005-01-01"
STABLE_END = "2007-06-30"

# Negative Control 기간
NEG_CONTROL_START = "2004-01-01"
NEG_CONTROL_END = "2006-06-30"

# 위기 분석 기간
CRISIS_START = "2005-01-01"
CRISIS_END = "2009-03-31"

# ============================================================
# 변수 매핑 (Physics-grounded)
# ============================================================
# ρ (외부 압력) = DFF 변화율 |Δ5일|
#   → F=ma: 시스템 충격은 속도에서 온다
#   → 밀도행렬 ρ: 외부 환경과의 상호작용
#
# Ψ (내부 가속) = TEDRATE 변화율 |Δ5일|
#   → 파동함수 Ψ: 시스템 내부 상태 동역학
#   → 은행 간 신뢰 붕괴의 자생적 가속
#
# Ω (구조적 결합) = TOTBKCR 수준 (월별 → 보간)
#   → 미시상태 다중도: 자유도 감소
#   → 구조적 결합은 상태량 (slow-varying)

FRED_SERIES = {
    'rho': 'DFF',      # Federal Funds Rate (일별)
    'psi': 'TEDRATE',       # TED Spread (일별)
    'omega': 'TOTBKCR',     # Total Bank Credit (월별)
}

# ============================================================
# 변환 파라미터
# ============================================================
DELTA_DAYS = 5               # 변화율 계산 윈도우 (1주)
PLIMIT_PERCENTILE = 99       # 안정기 기준 percentile
TAU_0 = 1                    # 고유 응답 주기 (영업일 단위)
BUSINESS_DAYS_PER_YEAR = 252

# ============================================================
# 출력
# ============================================================
OUTPUT_DIR = "./output"
