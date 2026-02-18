"""
Π Structural Stability Index
Case 4: COVID-19 Pandemic (2020-03)
Domain: Global Pandemic / Financial Contagion
========================================
  ρ = WHO/Johns Hopkins 일별 신규 확진자 수 (7일 rolling)
      외부 충격 = 팬데믹 확산 (applied load)
  Ψ = VIX (CBOE Volatility Index)
      내부 반응 = 시장 공포 (stress response)
  Ω = ICE BofA High Yield Spread (BAMLH0A0HYM2, FRED)
      구조적 결합 = 신용시장 동결 (reserve depletion)

물리적 인과 사슬: 팬데믹(원인) → 시장 공포(반응) → 신용 동결(상태)

Data Sources:
  - Johns Hopkins CSSE COVID-19 Dataset (github.com/CSSEGISandData)
  - CBOE VIX via Yahoo Finance
  - FRED (Federal Reserve Bank of St. Louis): BAMLH0A0HYM2

의존성: pip install yfinance pandas numpy matplotlib requests fredapi
"""

import os, sys, time
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import requests
import warnings
warnings.filterwarnings('ignore')

# COVID financial dislocation: 2020-02-20 ~ 2020-03-23 (S&P bottom)
# Fed unlimited QE declared 2020-03-23 → recovery phase begins
# Crisis window limited to financial shock phase (through Apr 2020)
COLLAPSE_DATE = "2020-03-11"  # WHO declares pandemic
DATA_START = "2019-07-01"
DATA_END = "2020-04-30"
STABLE_START = "2019-07-01"
STABLE_END = "2020-01-31"
CRISIS_START = "2019-07-01"
CRISIS_END = "2020-04-30"
NEG_CONTROL_START = "2019-07-01"
NEG_CONTROL_END = "2020-01-31"
PLIMIT_PCT = 99; DPY = 365
# Note: Crisis window ends 2020-04-30 to capture financial dislocation only.
# COVID cases continued rising after this, but financial markets recovered
# following Fed unlimited QE (2020-03-23). Extended pandemic effects are
# a separate phenomenon from the acute financial shock analyzed here.
OUTPUT_DIR = "./output"

FRED_API_KEY = os.environ.get('FRED_API_KEY', '')

# Johns Hopkins CSSE raw data URLs
JH_CONFIRMED_URL = (
    "https://raw.githubusercontent.com/CSSEGISandData/COVID-19/"
    "master/csse_covid_19_data/csse_covid_19_time_series/"
    "time_series_covid19_confirmed_global.csv"
)


class PiCalc:
    def __init__(self):
        self.dt = 1.0/DPY; self.p = {}
    def calibrate(self, r, p, o):
        rs = r[STABLE_START:STABLE_END].dropna()
        ps = p[STABLE_START:STABLE_END].dropna()
        os_ = o[STABLE_START:STABLE_END].dropna()
        self.p = {k: max(np.percentile(v, PLIMIT_PCT), 1e-10)
                  for k,v in zip(['r','p','o'],[rs,ps,os_])}
        print(f"  P_limits: rho={self.p['r']:.4f}, psi={self.p['p']:.4f}, omega={self.p['o']:.4f}")
        return self.p
    def calc(self, r, p, o, s=None, e=None):
        if s: r,p,o = r[s:],p[s:],o[s:]
        if e: r,p,o = r[:e],p[:e],o[:e]
        idx = r.index.intersection(p.index).intersection(o.index)
        r,p,o = r.reindex(idx),p.reindex(idx),o.reindex(idx)
        rn=(r/self.p['r']).clip(0); pn=(p/self.p['p']).clip(0); on=(o/self.p['o']).clip(0)
        st = rn*pn*on; pi = (st*self.dt).cumsum()
        return pd.DataFrame({'rho':r,'psi':p,'omega':o,
            'rho_norm':rn,'psi_norm':pn,'omega_norm':on,
            'stress':st,'pi':pi}, index=idx)


def fetch_covid_cases():
    """Johns Hopkins CSSE → Global daily new cases (7-day rolling avg)"""
    print("\n[1/3] rho: COVID-19 Daily New Cases (Johns Hopkins CSSE)")
    print("-" * 50)

    try:
        print("  Fetching JH CSSE data...", end=" ")
        resp = requests.get(JH_CONFIRMED_URL, timeout=60)
        if resp.status_code != 200:
            print(f"HTTP {resp.status_code}")
            return None

        import io
        df = pd.read_csv(io.StringIO(resp.text))
        print(f"ok {len(df)} countries/regions")

        # 날짜 컬럼 추출 (첫 4개는 Province, Country, Lat, Long)
        date_cols = df.columns[4:]
        dates = pd.to_datetime(date_cols)

        # 전 세계 합계
        global_cumulative = df[date_cols].sum(axis=0)
        global_cumulative.index = dates

        # 일별 신규 확진자
        daily_new = global_cumulative.diff().clip(lower=0)

        # 7일 rolling average (노이즈 제거)
        rho = daily_new.rolling(7).mean()

        # 기간 필터
        rho = rho[DATA_START:DATA_END]
        rho.index = rho.index.normalize()

        print(f"  Global new cases (7d avg):")
        print(f"    2020-01-31: {rho.get(pd.Timestamp('2020-01-31'), 0):.0f}")
        print(f"    2020-03-11: {rho.get(pd.Timestamp('2020-03-11'), 0):.0f}")
        print(f"    2020-03-23: {rho.get(pd.Timestamp('2020-03-23'), 0):.0f}")
        print(f"    Peak: {rho.max():.0f} on {rho.idxmax().strftime('%Y-%m-%d')}")
        print(f"  rho: {rho.dropna().shape[0]} pts")
        return rho

    except Exception as e:
        print(f"err: {e}")
        return None


def fetch_vix():
    """Yahoo Finance → VIX"""
    print("\n[2/3] psi: VIX (CBOE Volatility Index)")
    print("-" * 50)
    import yfinance as yf

    print("  ^VIX...", end=" ")
    vix = yf.download('^VIX', start=DATA_START, end=DATA_END, progress=False)
    if vix is None or len(vix) == 0:
        print("FAIL"); return None
    if isinstance(vix.columns, pd.MultiIndex):
        vix.columns = vix.columns.get_level_values(0)
    vix.index = pd.to_datetime(vix.index).tz_localize(None).normalize()
    psi = vix['Close']
    print(f"ok {len(psi)} rows")

    print(f"  VIX 2020-01-31: {psi.get(pd.Timestamp('2020-01-31'), 0):.2f}")
    print(f"  VIX 2020-03-16: {psi.get(pd.Timestamp('2020-03-16'), 0):.2f} (record)")
    print(f"  VIX peak: {psi.max():.2f} on {psi.idxmax().strftime('%Y-%m-%d')}")
    return psi


def fetch_hy_spread():
    """FRED → ICE BofA US High Yield Index Option-Adjusted Spread"""
    print("\n[3/3] omega: High Yield Credit Spread (FRED: BAMLH0A0HYM2)")
    print("-" * 50)

    series_id = "BAMLH0A0HYM2"

    # Try FRED API first
    if FRED_API_KEY:
        print("  FRED API...", end=" ")
        url = (f"https://api.stlouisfed.org/fred/series/observations?"
               f"series_id={series_id}&api_key={FRED_API_KEY}"
               f"&file_type=json"
               f"&observation_start={DATA_START}&observation_end={DATA_END}")
        try:
            resp = requests.get(url, timeout=30)
            if resp.status_code == 200:
                obs = resp.json().get('observations', [])
                if len(obs) > 10:
                    df = pd.DataFrame(obs)
                    df['date'] = pd.to_datetime(df['date'])
                    df['value'] = pd.to_numeric(df['value'], errors='coerce')
                    omega = df.set_index('date')['value'].dropna()
                    omega.index = omega.index.normalize()
                    print(f"ok {len(omega)} rows")
                    return omega
        except Exception as e:
            print(f"err: {e}")

    # Fallback: fredapi library
    try:
        print("  fredapi library...", end=" ")
        from fredapi import Fred
        fred = Fred(api_key=FRED_API_KEY)
        omega = fred.get_series(series_id, observation_start=DATA_START,
                                observation_end=DATA_END)
        omega.index = pd.to_datetime(omega.index).normalize()
        omega = omega.dropna()
        print(f"ok {len(omega)} rows")
        return omega
    except Exception as e:
        print(f"err: {e}")

    # Fallback 2: yfinance HYG ETF as proxy
    print("  Fallback: HYG ETF spread proxy...", end=" ")
    import yfinance as yf

    hyg = yf.download('HYG', start=DATA_START, end=DATA_END, progress=False)
    lqd = yf.download('LQD', start=DATA_START, end=DATA_END, progress=False)

    if hyg is not None and lqd is not None and len(hyg) > 10 and len(lqd) > 10:
        if isinstance(hyg.columns, pd.MultiIndex):
            hyg.columns = hyg.columns.get_level_values(0)
        if isinstance(lqd.columns, pd.MultiIndex):
            lqd.columns = lqd.columns.get_level_values(0)
        hyg.index = pd.to_datetime(hyg.index).tz_localize(None).normalize()
        lqd.index = pd.to_datetime(lqd.index).tz_localize(None).normalize()

        # HYG/LQD ratio as credit stress proxy
        # Lower ratio = higher stress (HY underperforms IG)
        common = hyg.index.intersection(lqd.index)
        ratio = hyg['Close'].reindex(common) / lqd['Close'].reindex(common)
        # Invert: higher = more stress
        omega = (1 / ratio) * 100  # scale
        omega = omega.pct_change().abs().rolling(5).mean()  # volatility of ratio
        print(f"ok {len(omega.dropna())} rows (HYG/LQD proxy)")
        print("  WARNING: Using ETF proxy, not direct spread data")
        return omega
    else:
        print("FAIL")
        return None


def fetch():
    print("=" * 60)
    print("  COVID-19: rho=Cases(JH) | psi=VIX | omega=HY Spread")
    print("=" * 60)

    rho = fetch_covid_cases()
    if rho is None: return None

    psi = fetch_vix()
    if psi is None: return None

    omega = fetch_hy_spread()
    if omega is None: return None

    # Align: rho(calendar) + omega(business days) → trading days (psi/VIX)
    print("\n[Align]")
    trading_days = psi.dropna().index
    print(f"  Trading days: {len(trading_days)}")

    # rho: calendar → trading days (ffill weekends)
    rho.index = pd.to_datetime(rho.index).normalize()
    rho_aligned = rho.reindex(trading_days, method='ffill').fillna(0)

    # omega: business days → trading days
    omega.index = pd.to_datetime(omega.index).normalize()
    omega_aligned = omega.reindex(trading_days, method='ffill')

    psi_aligned = psi.reindex(trading_days)

    # Debug
    for d in ['2020-01-31', '2020-03-11', '2020-03-16', '2020-03-23']:
        ts = pd.Timestamp(d)
        if ts in trading_days:
            print(f"  {d}: rho={rho_aligned.get(ts, 0):.0f}, "
                  f"psi={psi_aligned.get(ts, 0):.2f}, "
                  f"omega={omega_aligned.get(ts, 0):.4f}")

    v = rho_aligned.notna() & psi_aligned.notna() & omega_aligned.notna()
    f = trading_days[v]
    print(f"  Final: {len(f)} pts, rho>0: {(rho_aligned.reindex(f) > 0).sum()}")
    return {'rho': rho_aligned.reindex(f),
            'psi': psi_aligned.reindex(f),
            'omega': omega_aligned.reindex(f)}


def plot_traj(res, title, cd, path=None):
    plt.rcParams.update({'figure.dpi':150,'font.family':'serif','font.size':11,
                         'axes.grid':True,'grid.alpha':0.3})
    fig, ax = plt.subplots(3,1,figsize=(14,12),
                           gridspec_kw={'height_ratios':[3,2,2]}, sharex=True)
    c = pd.Timestamp(cd)
    ax[0].plot(res.index, res['pi'], color='#1a1a2e', lw=2, label='Pi(t)')
    ax[0].axvline(x=c, color='red', ls='--', alpha=.8, lw=1.5,
                  label=f'WHO Pandemic ({cd})')
    m = res['pi'].max()
    if m > 0: ax[0].axhline(y=m*.7, color='orange', ls=':', alpha=.6, label='~70% Pi_max')
    ax[0].set_ylabel('Pi(t)', fontweight='bold')
    ax[0].set_title(f'Pi: {title}', fontsize=15, fontweight='bold'); ax[0].legend()

    ax[1].fill_between(res.index, res['stress'], alpha=.4, color='#e74c3c', label='S(t)')
    ax[1].axvline(x=c, color='red', ls='--', alpha=.6)
    ax[1].set_ylabel('S(t)', fontweight='bold'); ax[1].legend()

    ax[2].plot(res.index, res['rho_norm'], color='#3498db', lw=1, alpha=.8,
               label='rho(COVID Cases)')
    ax[2].plot(res.index, res['psi_norm'], color='#e67e22', lw=1, alpha=.8,
               label='psi(VIX)')
    ax[2].plot(res.index, res['omega_norm'], color='#27ae60', lw=1, alpha=.8,
               label='omega(HY Spread)')
    ax[2].axhline(y=1, color='gray', ls=':', alpha=.5)
    ax[2].axvline(x=c, color='red', ls='--', alpha=.6)
    ax[2].set_ylabel('Normalized', fontweight='bold')
    ax[2].set_xlabel('Date'); ax[2].legend(ncol=2)

    for a in ax:
        a.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
        a.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    plt.xticks(rotation=45); plt.tight_layout()
    if path: plt.savefig(path, dpi=300, bbox_inches='tight'); print(f"  Saved {path}")
    plt.close()


def plot_comp(cr, ct, cd, path=None):
    fig, ax = plt.subplots(1, 2, figsize=(16,6))
    ax[0].plot(cr.index, cr['pi'], color='#c0392b', lw=2)
    ax[0].set_title('Crisis', fontweight='bold')
    ax[0].axvline(x=pd.Timestamp(cd), color='red', ls='--', alpha=.8,
                  label=f'WHO Pandemic ({cd})'); ax[0].legend()
    ax[1].plot(ct.index, ct['pi'], color='#27ae60', lw=2)
    ax[1].set_title('Negative Control', fontweight='bold')
    ym = max(cr['pi'].max(), ct['pi'].max()) * 1.1
    ax[0].set_ylim(0, ym); ax[1].set_ylim(0, ym)
    for a in ax:
        a.set_ylabel('Pi(t)')
        a.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        plt.setp(a.xaxis.get_majorticklabels(), rotation=45)
    plt.suptitle('Pi: Crisis vs Control', fontsize=15, fontweight='bold', y=1.02)
    plt.tight_layout()
    if path: plt.savefig(path, dpi=300, bbox_inches='tight'); print(f"  Saved {path}")
    plt.close()


def main():
    print("\n=== Pi Case 4: COVID-19 Pandemic (JH + VIX + FRED) ===\n")
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    d = fetch()
    if not d: print("FAIL"); sys.exit(1)

    c = PiCalc()
    c.calibrate(d['rho'], d['psi'], d['omega'])

    cr = c.calc(d['rho'], d['psi'], d['omega'], s=CRISIS_START, e=CRISIS_END)
    ct = c.calc(d['rho'], d['psi'], d['omega'], s=NEG_CONTROL_START, e=NEG_CONTROL_END)

    print(f"\n  Crisis Pi: {cr['pi'].max():.6f} | Control Pi: {ct['pi'].max():.6f}")

    cr.to_csv(f"{OUTPUT_DIR}/crisis_covid_pi.csv")
    ct.to_csv(f"{OUTPUT_DIR}/control_covid_pi.csv")
    pd.Series(c.p).to_csv(f"{OUTPUT_DIR}/p_limits.csv")

    plot_traj(cr, "COVID-19 Pandemic (2020-03)", COLLAPSE_DATE,
              f"{OUTPUT_DIR}/fig1_pi_covid.png")
    plot_comp(cr, ct, COLLAPSE_DATE,
              f"{OUTPUT_DIR}/fig2_covid_vs_control.png")

    cd = pd.Timestamp(COLLAPSE_DATE)
    n = cr.index[cr.index.get_indexer([cd], method='nearest')]
    pc = cr.loc[n[0], 'pi']; cf = ct['pi'].iloc[-1]
    s = pc/cf if cf > 0 else float('inf')

    print(f"\n{'='*60}")
    print(f"  Pi@pandemic: {pc:.6f}")
    print(f"  Control:     {cf:.6f}")
    print(f"  Separation:  {s:.1f}x")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
