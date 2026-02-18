"""
Π Structural Stability Index
Case 5: Global Supply Chain Crisis (2021-2022)
Domain: Supply Chain / Logistics
========================================
  ρ = PCEDG (Personal Consumption Expenditures: Durable Goods, FRED)
      외부 충격 = 소비 폭발 (보조금 → 내구재 수요 급증)
  Ψ = DTCDISA066MSFRBNY (Empire State Mfg: Delivery Time, FRED)
      내부 반응 = 납기 지연 (공급 병목)
  Ω = WPU3012 (PPI: Freight Transportation, FRED)
      구조적 결합 = 운송비 폭등

물리적 인과 사슬: 수요 폭발(원인) → 납기 지연(반응) → 운송비 폭등(상태)

Data Sources: ALL from FRED (Federal Reserve Bank of St. Louis)
Note: Monthly data → DPY=12, dt=1/12

의존성: pip install pandas numpy matplotlib requests
"""

import os, sys, time
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import requests
import warnings
warnings.filterwarnings('ignore')

# Supply chain crisis peak: ~2021-10 (container rates peak, delivery times worst)
COLLAPSE_DATE = "2021-10-01"
DATA_START = "2019-01-01"
DATA_END = "2022-12-31"
STABLE_START = "2019-01-01"
STABLE_END = "2020-06-30"
CRISIS_START = "2019-01-01"
CRISIS_END = "2022-12-31"
NEG_CONTROL_START = "2019-01-01"
NEG_CONTROL_END = "2020-06-30"
PLIMIT_PCT = 99
DPY = 12  # monthly data
OUTPUT_DIR = "./output"

FRED_API_KEY = os.environ.get('FRED_API_KEY', '')

# FRED Series IDs
SERIES = {
    'rho': 'PCEDG',              # Personal Consumption: Durable Goods (billions $)
    'psi': 'DTCDISA066MSFRBNY',  # Empire State Delivery Time Diffusion Index
    'omega': 'WPU3012',          # PPI: Freight Transportation
}


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


def fetch_fred(series_id, label=""):
    """Fetch single series from FRED API"""
    if not FRED_API_KEY:
        print(f"  WARNING: No FRED_API_KEY, trying without...")

    url = (f"https://api.stlouisfed.org/fred/series/observations?"
           f"series_id={series_id}&api_key={FRED_API_KEY}"
           f"&file_type=json"
           f"&observation_start={DATA_START}&observation_end={DATA_END}")
    try:
        resp = requests.get(url, timeout=30)
        if resp.status_code == 200:
            obs = resp.json().get('observations', [])
            if len(obs) > 0:
                df = pd.DataFrame(obs)
                df['date'] = pd.to_datetime(df['date'])
                df['value'] = pd.to_numeric(df['value'], errors='coerce')
                series = df.set_index('date')['value'].dropna()
                series.index = series.index.normalize()
                return series
        print(f"  HTTP {resp.status_code}")
    except Exception as e:
        print(f"  err: {e}")
    return None


def fetch():
    print("=" * 60)
    print("  Supply Chain Crisis: ALL DATA FROM FRED")
    print("  rho=PCEDG | psi=Delivery Time | omega=Freight PPI")
    print("=" * 60)

    # === ρ: PCEDG (Durable Goods Consumption) ===
    print(f"\n[1/3] rho: PCEDG (Durable Goods PCE)")
    print("-" * 50)
    print(f"  Fetching {SERIES['rho']}...", end=" ")
    rho_raw = fetch_fred(SERIES['rho'])
    if rho_raw is None or len(rho_raw) < 10:
        print("FAIL"); return None
    print(f"ok {len(rho_raw)} months")

    # 전월 대비 변화율 (소비 가속도)
    rho = rho_raw.pct_change().abs()
    print(f"  PCEDG range: ${rho_raw.min():.0f}B ~ ${rho_raw.max():.0f}B")
    print(f"  rho (|MoM change|): {rho.dropna().shape[0]} pts")

    time.sleep(1)

    # === Ψ: Delivery Time ===
    print(f"\n[2/3] psi: Empire State Delivery Time ({SERIES['psi']})")
    print("-" * 50)
    print(f"  Fetching {SERIES['psi']}...", end=" ")
    psi_raw = fetch_fred(SERIES['psi'])
    if psi_raw is None or len(psi_raw) < 10:
        print("FAIL"); return None
    print(f"ok {len(psi_raw)} months")

    # Delivery time: 양수 = 납기 늘어남 (악화)
    # 절대값 사용 (악화 정도)
    psi = psi_raw.clip(lower=0)  # 양수만 (지연 증가)
    print(f"  Delivery time range: {psi_raw.min():.1f} ~ {psi_raw.max():.1f}")
    print(f"  2021 peak: {psi_raw['2021'].max():.1f} on {psi_raw['2021'].idxmax().strftime('%Y-%m')}")

    time.sleep(1)

    # === Ω: Freight PPI ===
    print(f"\n[3/3] omega: PPI Freight Transportation ({SERIES['omega']})")
    print("-" * 50)
    print(f"  Fetching {SERIES['omega']}...", end=" ")
    omega_raw = fetch_fred(SERIES['omega'])
    if omega_raw is None or len(omega_raw) < 10:
        print("FAIL"); return None
    print(f"ok {len(omega_raw)} months")

    # 전월 대비 변화율 (운임 가속도)
    omega = omega_raw.pct_change().abs()
    print(f"  Freight PPI range: {omega_raw.min():.1f} ~ {omega_raw.max():.1f}")
    print(f"  omega (|MoM change|): {omega.dropna().shape[0]} pts")

    # Align monthly data
    print("\n[Align]")
    common = rho.dropna().index.intersection(psi.dropna().index).intersection(omega.dropna().index)
    rho = rho.reindex(common)
    psi = psi.reindex(common)
    omega = omega.reindex(common)

    # Debug key dates
    for d in ['2020-06-01', '2021-01-01', '2021-06-01', '2021-10-01', '2022-01-01']:
        ts = pd.Timestamp(d)
        idx = common[common.get_indexer([ts], method='nearest')[0]]
        print(f"  {d}: rho={rho.loc[idx]:.4f}, psi={psi.loc[idx]:.1f}, omega={omega.loc[idx]:.4f}")

    v = rho.notna() & psi.notna() & omega.notna()
    f = common[v]
    print(f"  Final: {len(f)} months")
    return {'rho': rho.reindex(f), 'psi': psi.reindex(f), 'omega': omega.reindex(f)}


def plot_traj(res, title, cd, path=None):
    plt.rcParams.update({'figure.dpi':150,'font.family':'serif','font.size':11,
                         'axes.grid':True,'grid.alpha':0.3})
    fig, ax = plt.subplots(3,1,figsize=(14,12),
                           gridspec_kw={'height_ratios':[3,2,2]}, sharex=True)
    c = pd.Timestamp(cd)
    ax[0].plot(res.index, res['pi'], color='#1a1a2e', lw=2, label='Pi(t)')
    ax[0].axvline(x=c, color='red', ls='--', alpha=.8, lw=1.5,
                  label=f'Supply Chain Peak ({cd})')
    m = res['pi'].max()
    if m > 0: ax[0].axhline(y=m*.7, color='orange', ls=':', alpha=.6, label='~70% Pi_max')
    ax[0].set_ylabel('Pi(t)', fontweight='bold')
    ax[0].set_title(f'Pi: {title}', fontsize=15, fontweight='bold'); ax[0].legend()

    ax[1].fill_between(res.index, res['stress'], alpha=.4, color='#e74c3c', label='S(t)')
    ax[1].axvline(x=c, color='red', ls='--', alpha=.6)
    ax[1].set_ylabel('S(t)', fontweight='bold'); ax[1].legend()

    ax[2].plot(res.index, res['rho_norm'], color='#3498db', lw=1.5, alpha=.8,
               label='rho(Durable Goods)')
    ax[2].plot(res.index, res['psi_norm'], color='#e67e22', lw=1.5, alpha=.8,
               label='psi(Delivery Time)')
    ax[2].plot(res.index, res['omega_norm'], color='#27ae60', lw=1.5, alpha=.8,
               label='omega(Freight PPI)')
    ax[2].axhline(y=1, color='gray', ls=':', alpha=.5)
    ax[2].axvline(x=c, color='red', ls='--', alpha=.6)
    ax[2].set_ylabel('Normalized', fontweight='bold')
    ax[2].set_xlabel('Date'); ax[2].legend(ncol=2)

    for a in ax:
        a.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        a.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    plt.xticks(rotation=45); plt.tight_layout()
    if path: plt.savefig(path, dpi=300, bbox_inches='tight'); print(f"  Saved {path}")
    plt.close()


def plot_comp(cr, ct, cd, path=None):
    fig, ax = plt.subplots(1, 2, figsize=(16,6))
    ax[0].plot(cr.index, cr['pi'], color='#c0392b', lw=2)
    ax[0].set_title('Crisis', fontweight='bold')
    ax[0].axvline(x=pd.Timestamp(cd), color='red', ls='--', alpha=.8,
                  label=f'Peak ({cd})'); ax[0].legend()
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
    print("\n=== Pi Case 5: Supply Chain Crisis (FRED Only) ===\n")
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    d = fetch()
    if not d: print("FAIL"); sys.exit(1)

    c = PiCalc()
    c.calibrate(d['rho'], d['psi'], d['omega'])

    cr = c.calc(d['rho'], d['psi'], d['omega'], s=CRISIS_START, e=CRISIS_END)
    ct = c.calc(d['rho'], d['psi'], d['omega'], s=NEG_CONTROL_START, e=NEG_CONTROL_END)

    print(f"\n  Crisis Pi: {cr['pi'].max():.6f} | Control Pi: {ct['pi'].max():.6f}")

    cr.to_csv(f"{OUTPUT_DIR}/crisis_supply_chain_pi.csv")
    ct.to_csv(f"{OUTPUT_DIR}/control_supply_chain_pi.csv")
    pd.Series(c.p).to_csv(f"{OUTPUT_DIR}/p_limits.csv")

    plot_traj(cr, "Supply Chain Crisis (2021-2022)", COLLAPSE_DATE,
              f"{OUTPUT_DIR}/fig1_pi_supply_chain.png")
    plot_comp(cr, ct, COLLAPSE_DATE,
              f"{OUTPUT_DIR}/fig2_supply_chain_vs_control.png")

    cd = pd.Timestamp(COLLAPSE_DATE)
    n = cr.index[cr.index.get_indexer([cd], method='nearest')]
    pc = cr.loc[n[0], 'pi']; cf = ct['pi'].iloc[-1]
    s = pc/cf if cf > 0 else float('inf')

    print(f"\n{'='*60}")
    print(f"  Pi@peak:     {pc:.6f}")
    print(f"  Control:     {cf:.6f}")
    print(f"  Separation:  {s:.1f}x")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
