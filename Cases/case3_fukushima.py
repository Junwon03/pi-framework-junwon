"""
Π Structural Stability Index
Case 3: Fukushima Nuclear Disaster (2011-03-11) — v2
Domain: Physical Infrastructure / Natural Disaster
========================================
  ρ = USGS 일별 총 지진 에너지 log10 (Gutenberg-Richter)
      M2+ 포함하여 안정기에도 baseline 확보
  Ψ = Nikkei 225 일별 변동성 (5일 rolling)
  Ω = USD/JPY 일별 변화율

Data Sources:
  - USGS Earthquake Hazards Program (earthquake.usgs.gov)
  - Yahoo Finance (Nikkei 225, USD/JPY via CoinMarketCap pipeline)

의존성: pip install yfinance pandas numpy matplotlib requests
"""

import os, sys, time, io
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import requests
import warnings
warnings.filterwarnings('ignore')

COLLAPSE_DATE = "2011-03-11"
DATA_START = "2010-06-01"
DATA_END = "2011-09-30"
STABLE_START = "2010-06-01"
STABLE_END = "2011-02-28"
CRISIS_START = "2010-06-01"
CRISIS_END = "2011-09-30"
NEG_CONTROL_START = "2010-06-01"
NEG_CONTROL_END = "2011-02-28"
PLIMIT_PCT = 99; DPY = 365
OUTPUT_DIR = "./output"

JP_LAT_MIN = 30; JP_LAT_MAX = 46
JP_LON_MIN = 128; JP_LON_MAX = 146
MIN_MAG = 2.0  # M2+ for baseline coverage


class PiCalc:
    def __init__(self):
        self.dt = 1.0/DPY; self.p = {}
    def calibrate(self, r, p, o):
        rs = r[STABLE_START:STABLE_END].dropna()
        ps = p[STABLE_START:STABLE_END].dropna()
        os_ = o[STABLE_START:STABLE_END].dropna()
        self.p = {k: max(np.percentile(v, PLIMIT_PCT), 1e-10)
                  for k,v in zip(['r','p','o'],[rs,ps,os_])}
        print(f"  P_limits: rho={self.p['r']:.4f}, psi={self.p['p']:.6f}, omega={self.p['o']:.6f}")
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


def mag_to_energy(mag):
    """Gutenberg-Richter: log10(E) = 1.5*M + 4.8 (Joules)"""
    return 10 ** (1.5 * mag + 4.8)


def fetch_usgs_earthquakes():
    """USGS FDSN Event API → Japan region earthquakes"""
    print("\n[1/3] rho: USGS Earthquake Data (Japan, M2+)")
    print("-" * 50)

    all_data = []
    start = pd.Timestamp(DATA_START)
    end = pd.Timestamp(DATA_END)
    current = start

    while current < end:
        month_end = min(current + pd.DateOffset(months=1), end)
        url = (
            f"https://earthquake.usgs.gov/fdsnws/event/1/query?"
            f"format=csv"
            f"&starttime={current.strftime('%Y-%m-%d')}"
            f"&endtime={month_end.strftime('%Y-%m-%d')}"
            f"&minlatitude={JP_LAT_MIN}&maxlatitude={JP_LAT_MAX}"
            f"&minlongitude={JP_LON_MIN}&maxlongitude={JP_LON_MAX}"
            f"&minmagnitude={MIN_MAG}"
            f"&orderby=time"
        )
        try:
            print(f"  {current.strftime('%Y-%m')}...", end=" ")
            resp = requests.get(url, timeout=60)
            if resp.status_code == 200 and len(resp.text) > 100:
                df = pd.read_csv(io.StringIO(resp.text))
                if len(df) > 0:
                    all_data.append(df)
                    print(f"ok {len(df)} events")
                else:
                    print("0 events")
            else:
                print(f"HTTP {resp.status_code}")
        except Exception as e:
            print(f"err: {e}")
        time.sleep(1)
        current = month_end

    if not all_data:
        print("  USGS FAIL"); return None

    eq = pd.concat(all_data, ignore_index=True)
    # UTC time → date (normalize to midnight, tz-naive)
    eq['datetime'] = pd.to_datetime(eq['time'], utc=True)
    eq['date'] = eq['datetime'].dt.tz_localize(None).dt.normalize()
    eq['energy'] = mag_to_energy(eq['mag'])

    print(f"\n  Total: {len(eq)} earthquakes (M{MIN_MAG}+)")
    print(f"  Max magnitude: M{eq['mag'].max():.1f}")

    # 일별 총 에너지 (log10 scale)
    daily_total_energy = eq.groupby('date')['energy'].sum()
    daily_max_mag = eq.groupby('date')['mag'].max()
    daily_count = eq.groupby('date')['mag'].count()

    # log10(총 에너지) → 안정기에도 값이 있음
    rho_raw = np.log10(daily_total_energy.clip(lower=1))

    # 3/11 확인
    if '2011-03-11' in str(daily_max_mag.index):
        d311 = daily_total_energy.get(pd.Timestamp('2011-03-11'), 0)
        m311 = daily_max_mag.get(pd.Timestamp('2011-03-11'), 0)
        c311 = daily_count.get(pd.Timestamp('2011-03-11'), 0)
        print(f"  3/11: M{m311:.1f}, {c311} events, total E={d311:.2e} J, log10={np.log10(d311):.2f}")

    # 안정기 통계
    stable_rho = rho_raw[STABLE_START:STABLE_END]
    print(f"  Stable period: {len(stable_rho)} days with data, "
          f"log10(E) range: {stable_rho.min():.1f} ~ {stable_rho.max():.1f}")

    print(f"  rho (log10 daily energy): {len(rho_raw)} days with quakes")
    return rho_raw


def fetch_nikkei_jpy():
    """Yahoo Finance → Nikkei 225 + USD/JPY"""
    print("\n[2/3] psi: Nikkei 225 Volatility")
    print("[3/3] omega: USD/JPY Rate Change")
    print("-" * 50)
    import yfinance as yf

    # Nikkei 225
    print("  ^N225...", end=" ")
    nk = yf.download('^N225', start=DATA_START, end=DATA_END, progress=False)
    if nk is None or len(nk) == 0:
        print("FAIL"); return None, None
    if isinstance(nk.columns, pd.MultiIndex):
        nk.columns = nk.columns.get_level_values(0)
    nk.index = pd.to_datetime(nk.index).tz_localize(None).normalize()
    print(f"ok {len(nk)} rows")

    nk_ret = nk['Close'].pct_change()
    psi = nk_ret.rolling(5).std() * np.sqrt(252)

    nk_crisis = nk['Close']['2011-03-10':'2011-03-18']
    if len(nk_crisis) >= 2:
        drop = (nk_crisis.iloc[-1] / nk_crisis.iloc[0] - 1) * 100
        print(f"  Nikkei 3/10~3/18: {drop:.1f}% change")

    # USD/JPY
    print("  JPY=X...", end=" ")
    jpy = yf.download('JPY=X', start=DATA_START, end=DATA_END, progress=False)
    if jpy is None or len(jpy) == 0:
        print("FAIL"); return None, None
    if isinstance(jpy.columns, pd.MultiIndex):
        jpy.columns = jpy.columns.get_level_values(0)
    jpy.index = pd.to_datetime(jpy.index).tz_localize(None).normalize()
    print(f"ok {len(jpy)} rows")

    omega = jpy['Close'].pct_change().abs()

    jpy_crisis = jpy['Close']['2011-03-10':'2011-03-18']
    if len(jpy_crisis) >= 2:
        print(f"  USD/JPY 3/10: {jpy_crisis.iloc[0]:.2f} -> min: {jpy_crisis.min():.2f}")

    print(f"  psi (Nikkei vol): {psi.dropna().shape[0]} pts")
    print(f"  omega (JPY change): {omega.dropna().shape[0]} pts")
    return psi, omega


def fetch():
    print("=" * 60)
    print("  Fukushima v2: rho=Quake(USGS) | psi=Nikkei | omega=JPY")
    print("=" * 60)

    rho = fetch_usgs_earthquakes()
    if rho is None: return None

    psi, omega = fetch_nikkei_jpy()
    if psi is None: return None

    # Align: rho(calendar) → trading days
    print("\n[Align]")

    # psi와 omega의 공통 trading days
    trading_days = psi.dropna().index.intersection(omega.dropna().index)
    print(f"  Trading days: {len(trading_days)}")

    # rho를 trading days에 매핑
    # rho의 인덱스를 tz-naive normalized로 통일
    rho.index = pd.to_datetime(rho.index).normalize()

    # 디버그: 겹치는 날짜 확인
    overlap = rho.index.intersection(trading_days)
    print(f"  Overlap (rho & trading): {len(overlap)}")

    if len(overlap) < 10:
        # 날짜 타입 문제일 수 있음 - 직접 매핑
        print("  Direct mapping fallback...")
        rho_dict = {d: v for d, v in zip(rho.index, rho.values)}
        rho_mapped = []
        for td in trading_days:
            # 정확히 같은 날 또는 직전 날
            val = rho_dict.get(td, None)
            if val is None:
                # 이전 날짜에서 가장 가까운 값
                for delta in range(0, 4):
                    check = td - pd.Timedelta(days=delta)
                    val = rho_dict.get(check, None)
                    if val is not None:
                        break
            rho_mapped.append(val if val is not None else 0)
        rho_aligned = pd.Series(rho_mapped, index=trading_days)
    else:
        rho_aligned = rho.reindex(trading_days, method='ffill').fillna(0)

    psi_aligned = psi.reindex(trading_days)
    omega_aligned = omega.reindex(trading_days)

    # 디버그: 3/11 근처 값 확인
    for d in ['2011-03-10', '2011-03-11', '2011-03-14', '2011-03-15']:
        ts = pd.Timestamp(d)
        if ts in rho_aligned.index:
            print(f"  {d}: rho={rho_aligned.loc[ts]:.2f}, "
                  f"psi={psi_aligned.loc[ts]:.4f}, "
                  f"omega={omega_aligned.loc[ts]:.6f}")

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
    ax[0].axvline(x=c, color='red', ls='--', alpha=.8, lw=1.5, label=f'Collapse ({cd})')
    m = res['pi'].max()
    if m > 0: ax[0].axhline(y=m*.7, color='orange', ls=':', alpha=.6, label='~70% Pi_max')
    ax[0].set_ylabel('Pi(t)', fontweight='bold')
    ax[0].set_title(f'Pi: {title}', fontsize=15, fontweight='bold'); ax[0].legend()

    ax[1].fill_between(res.index, res['stress'], alpha=.4, color='#e74c3c', label='S(t)')
    ax[1].axvline(x=c, color='red', ls='--', alpha=.6)
    ax[1].set_ylabel('S(t)', fontweight='bold'); ax[1].legend()

    ax[2].plot(res.index, res['rho_norm'], color='#3498db', lw=1, alpha=.8, label='rho(Quake E)')
    ax[2].plot(res.index, res['psi_norm'], color='#e67e22', lw=1, alpha=.8, label='psi(Nikkei Vol)')
    ax[2].plot(res.index, res['omega_norm'], color='#27ae60', lw=1, alpha=.8, label='omega(JPY)')
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
                  label=f'Collapse ({cd})'); ax[0].legend()
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
    print("\n=== Pi Case 3: Fukushima v2 (USGS + YFinance) ===\n")
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    d = fetch()
    if not d: print("FAIL"); sys.exit(1)

    c = PiCalc()
    c.calibrate(d['rho'], d['psi'], d['omega'])

    cr = c.calc(d['rho'], d['psi'], d['omega'], s=CRISIS_START, e=CRISIS_END)
    ct = c.calc(d['rho'], d['psi'], d['omega'], s=NEG_CONTROL_START, e=NEG_CONTROL_END)

    print(f"\n  Crisis Pi: {cr['pi'].max():.6f} | Control Pi: {ct['pi'].max():.6f}")

    cr.to_csv(f"{OUTPUT_DIR}/crisis_fukushima_pi.csv")
    ct.to_csv(f"{OUTPUT_DIR}/control_fukushima_pi.csv")
    pd.Series(c.p).to_csv(f"{OUTPUT_DIR}/p_limits.csv")

    plot_traj(cr, "Fukushima v2 (2011-03-11)", COLLAPSE_DATE,
              f"{OUTPUT_DIR}/fig1_pi_fukushima.png")
    plot_comp(cr, ct, COLLAPSE_DATE,
              f"{OUTPUT_DIR}/fig2_fukushima_vs_control.png")

    cd = pd.Timestamp(COLLAPSE_DATE)
    n = cr.index[cr.index.get_indexer([cd], method='nearest')]
    pc = cr.loc[n[0], 'pi']; cf = ct['pi'].iloc[-1]
    s = pc/cf if cf > 0 else float('inf')

    print(f"\n{'='*60}")
    print(f"  Pi@collapse: {pc:.6f}")
    print(f"  Control:     {cf:.6f}")
    print(f"  Separation:  {s:.1f}x")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
