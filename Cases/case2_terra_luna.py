"""
Π Structural Stability Index
Case 2: Terra-Luna Collapse (2022-05) — v2
Domain: Digital Assets
========================================
v2: ρ = BTC |Δ5d| (Fed 금리 동결→0 문제 해결)

의존성: pip install pandas numpy matplotlib yfinance requests
"""

import os, sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import warnings
warnings.filterwarnings('ignore')

COLLAPSE_DATE = "2022-05-09"
DATA_START = "2021-01-01"
DATA_END = "2022-08-31"
STABLE_START = "2021-07-01"
STABLE_END = "2022-03-31"
CRISIS_START = "2021-07-01"
CRISIS_END = "2022-07-31"
NEG_CONTROL_START = "2021-07-01"
NEG_CONTROL_END = "2022-01-31"
DELTA_RHO = 5; DELTA_PSI = 1; CORR_WIN = 60
PLIMIT_PCT = 99; TAU_0 = 1; DPY = 365
OUTPUT_DIR = "./output"

class PiCalc:
    def __init__(self):
        self.dt = 1.0/DPY; self.p = {}; self.ok = False
    def calibrate(self, r, p, o):
        rs, ps, os_ = r[STABLE_START:STABLE_END].dropna(), p[STABLE_START:STABLE_END].dropna(), o[STABLE_START:STABLE_END].dropna()
        self.p = {k: max(np.percentile(v, PLIMIT_PCT), 1e-10) for k,v in zip(['r','p','o'],[rs,ps,os_])}
        self.ok = True
        print(f"  P_limits: ρ={self.p['r']:.2f}, Ψ={self.p['p']:.4f}, Ω={self.p['o']:.4f}")
        return self.p
    def calc(self, r, p, o, s=None, e=None):
        if s: r,p,o = r[s:],p[s:],o[s:]
        if e: r,p,o = r[:e],p[:e],o[:e]
        idx = r.index.intersection(p.index).intersection(o.index)
        r,p,o = r.reindex(idx),p.reindex(idx),o.reindex(idx)
        rn,pn,on = (r/self.p['r']).clip(0),(p/self.p['p']).clip(0),(o/self.p['o']).clip(0)
        st = rn*pn*on; pi = (st*self.dt).cumsum()
        return pd.DataFrame({'rho':r,'psi':p,'omega':o,'rho_norm':rn,'psi_norm':pn,'omega_norm':on,'stress':st,'pi':pi},index=idx)

def fetch():
    import yfinance as yf
    print("="*60+"\n  Terra-Luna v2: ρ=BTC, Ψ=LUNA, Ω=Corr\n"+"="*60)
    
    btc = yf.download('BTC-USD', start=DATA_START, end=DATA_END, progress=False)
    if isinstance(btc.columns, pd.MultiIndex): btc.columns = btc.columns.get_level_values(0)
    btc.index = pd.to_datetime(btc.index).tz_localize(None).normalize()
    rho = btc['Close'].diff(DELTA_RHO).abs()
    print(f"  ρ (BTC |Δ{DELTA_RHO}d|): {rho.dropna().shape[0]} pts")
    
    luna = None
    try:
        import requests
        url = f"https://api.coingecko.com/api/v3/coins/terrausd/market_chart/range?vs_currency=usd&from={int(pd.Timestamp(DATA_START).timestamp())}&to={int(pd.Timestamp(DATA_END).timestamp())}"
        r = requests.get(url, timeout=30)
        if r.status_code == 200 and len(r.json().get('prices',[])) > 30:
            df = pd.DataFrame(r.json()['prices'], columns=['ts','price'])
            df['date'] = pd.to_datetime(df['ts'], unit='ms').dt.normalize()
            luna = df.groupby('date')['price'].last()
            print(f"  Ψ UST (CoinGecko): {len(luna)} rows")
    except: pass
    
    if luna is None or len(luna) < 30:
        for t in ['LUNC-USD','LUNA1-USD']:
            df = yf.download(t, start=DATA_START, end=DATA_END, progress=False)
            if not df.empty:
                if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
                df.index = pd.to_datetime(df.index).tz_localize(None).normalize()
                luna = df['Close']; print(f"  Ψ ({t}): {len(luna)} rows"); break
    if luna is None: print("❌ LUNA 데이터 없음"); return None
    psi = luna.diff(DELTA_PSI).abs()
    
    eth = yf.download('ETH-USD', start=DATA_START, end=DATA_END, progress=False)
    if isinstance(eth.columns, pd.MultiIndex): eth.columns = eth.columns.get_level_values(0)
    eth.index = pd.to_datetime(eth.index).tz_localize(None).normalize()
    
    prices = pd.DataFrame({'BTC':btc['Close'],'ETH':eth['Close'],'LUNA':luna})
    rets = np.log(prices/prices.shift(1))
    ov = []
    for i in range(len(rets)):
        if i < CORR_WIN: ov.append(np.nan); continue
        w = rets.iloc[i-CORR_WIN:i].dropna(axis=1, thresh=CORR_WIN//2)
        if w.shape[1] < 2: ov.append(0.5); continue
        c = w.corr(); u = c.values[np.triu_indices(len(c),k=1)]; u = u[~np.isnan(u)]
        ov.append((np.nanmean(u)+1)/2 if len(u)>0 else 0.5)
    omega = pd.Series(ov, index=rets.index).clip(0,1)
    print(f"  Ω (corr): {omega.dropna().shape[0]} pts")
    
    common = rho.dropna().index.intersection(psi.dropna().index).intersection(omega.dropna().index)
    rho = rho.reindex(common).ffill().bfill()
    psi = psi.reindex(common).ffill().bfill()
    omega = omega.reindex(common).ffill().bfill().fillna(0.5)
    v = rho.notna()&psi.notna()&omega.notna(); f = common[v]
    print(f"  📊 최종: {len(f)} pts")
    return {'rho':rho.reindex(f),'psi':psi.reindex(f),'omega':omega.reindex(f)}

def plot_traj(res, title, cd, path=None):
    plt.rcParams.update({'figure.dpi':150,'font.family':'serif','font.size':11,'axes.grid':True,'grid.alpha':0.3})
    fig,ax = plt.subplots(3,1,figsize=(14,12),gridspec_kw={'height_ratios':[3,2,2]},sharex=True)
    c = pd.Timestamp(cd)
    ax[0].plot(res.index,res['pi'],color='#1a1a2e',lw=2,label='Π(t)')
    ax[0].axvline(x=c,color='red',ls='--',alpha=.8,lw=1.5,label=f'Collapse ({cd})')
    m=res['pi'].max()
    if m>0: ax[0].axhline(y=m*.7,color='orange',ls=':',alpha=.6,label='~70% Π_max')
    ax[0].set_ylabel('Π(t)',fontweight='bold'); ax[0].set_title(f'Π: {title}',fontsize=15,fontweight='bold'); ax[0].legend()
    ax[1].fill_between(res.index,res['stress'],alpha=.4,color='#e74c3c',label='S(t)'); ax[1].axvline(x=c,color='red',ls='--',alpha=.6); ax[1].set_ylabel('S(t)',fontweight='bold'); ax[1].legend()
    ax[2].plot(res.index,res['rho_norm'],color='#3498db',lw=1,alpha=.8,label='ρ̃(BTC)')
    ax[2].plot(res.index,res['psi_norm'],color='#e67e22',lw=1,alpha=.8,label='Ψ̃(LUNA)')
    ax[2].plot(res.index,res['omega_norm'],color='#27ae60',lw=1,alpha=.8,label='Ω̃(Corr)')
    ax[2].axhline(y=1,color='gray',ls=':',alpha=.5); ax[2].axvline(x=c,color='red',ls='--',alpha=.6)
    ax[2].set_ylabel('Normalized',fontweight='bold'); ax[2].set_xlabel('Date'); ax[2].legend(ncol=2)
    for a in ax: a.xaxis.set_major_locator(mdates.MonthLocator(interval=2)); a.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    plt.xticks(rotation=45); plt.tight_layout()
    if path: plt.savefig(path,dpi=300,bbox_inches='tight'); print(f"  📊 {path}")
    plt.close()

def plot_comp(cr,ct,cd,path=None):
    fig,ax=plt.subplots(1,2,figsize=(16,6))
    ax[0].plot(cr.index,cr['pi'],color='#c0392b',lw=2); ax[0].set_title('Crisis',fontweight='bold')
    ax[0].axvline(x=pd.Timestamp(cd),color='red',ls='--',alpha=.8,label=f'Collapse ({cd})'); ax[0].legend()
    ax[1].plot(ct.index,ct['pi'],color='#27ae60',lw=2); ax[1].set_title('Negative Control',fontweight='bold')
    ym=max(cr['pi'].max(),ct['pi'].max())*1.1; ax[0].set_ylim(0,ym); ax[1].set_ylim(0,ym)
    for a in ax: a.set_ylabel('Π(t)'); a.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m')); plt.setp(a.xaxis.get_majorticklabels(),rotation=45)
    plt.suptitle('Π: Crisis vs Control',fontsize=15,fontweight='bold',y=1.02); plt.tight_layout()
    if path: plt.savefig(path,dpi=300,bbox_inches='tight'); print(f"  📊 {path}")
    plt.close()

def main():
    print("\n╔"+"═"*58+"╗\n║  Π Case 2: Terra-Luna v2 (ρ=BTC)".ljust(60)+"║\n╚"+"═"*58+"╝\n")
    os.makedirs(OUTPUT_DIR,exist_ok=True)
    d = fetch()
    if not d: sys.exit(1)
    c = PiCalc(); c.calibrate(d['rho'],d['psi'],d['omega'])
    cr = c.calc(d['rho'],d['psi'],d['omega'],s=CRISIS_START,e=CRISIS_END)
    ct = c.calc(d['rho'],d['psi'],d['omega'],s=NEG_CONTROL_START,e=NEG_CONTROL_END)
    print(f"\n  Crisis Π: {cr['pi'].max():.4f} | Control Π: {ct['pi'].max():.4f}")
    cr.to_csv(f"{OUTPUT_DIR}/crisis_terra_luna_pi.csv")
    ct.to_csv(f"{OUTPUT_DIR}/control_terra_luna_pi.csv")
    pd.Series(c.p).to_csv(f"{OUTPUT_DIR}/p_limits.csv")
    plot_traj(cr,"Terra-Luna v2 (2022-05)",COLLAPSE_DATE,f"{OUTPUT_DIR}/fig1_pi_terra_luna.png")
    plot_comp(cr,ct,COLLAPSE_DATE,f"{OUTPUT_DIR}/fig2_terra_luna_vs_control.png")
    cd=pd.Timestamp(COLLAPSE_DATE); n=cr.index[cr.index.get_indexer([cd],method='nearest')]
    pc=cr.loc[n[0],'pi']; cf=ct['pi'].iloc[-1]; s=pc/cf if cf>0 else float('inf')
    print(f"\n{'='*60}\n  Π@collapse: {pc:.4f}\n  Control:    {cf:.4f}\n  Separation: {s:.1f}x\n{'='*60}")

if __name__=="__main__": main()
