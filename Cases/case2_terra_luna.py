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
        if not np.isfinite(DPY) or DPY <= 0:
            raise ValueError("DPY must be positive and finite.")
        self.dt = 1.0 / float(DPY)
        self.p = {}
        self.ok = False

    def calibrate(self, r, p, o):
        stable = {
            "r": r[STABLE_START:STABLE_END].dropna(),
            "p": p[STABLE_START:STABLE_END].dropna(),
            "o": o[STABLE_START:STABLE_END].dropna(),
        }

        for name, series in stable.items():
            if series.empty:
                raise ValueError(
                    f"{name}: no observations in Terra calibration period."
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

        candidate = {
            name: float(
                np.percentile(
                    series.to_numpy(dtype=float),
                    PLIMIT_PCT,
                )
            )
            for name, series in stable.items()
        }

        for name, value in candidate.items():
            if not np.isfinite(value) or value <= 0:
                raise ValueError(
                    f"{name}: P_limit must be positive and finite; "
                    f"got {value}."
                )

        self.p = candidate
        self.ok = True

        print(
            f"  P_limits: ρ={self.p['r']:.2f}, "
            f"Ψ={self.p['p']:.4f}, Ω={self.p['o']:.4f}"
        )
        return self.p

    def calc(self, r, p, o, s=None, e=None):
        if not self.ok:
            raise RuntimeError("calibrate() must be called before calc().")

        if s:
            r, p, o = r[s:], p[s:], o[s:]
        if e:
            r, p, o = r[:e], p[:e], o[:e]

        idx = r.index.intersection(p.index).intersection(o.index)
        idx = idx.sort_values()

        if len(idx) == 0:
            raise ValueError("No common Terra analysis observations.")
        if idx.has_duplicates:
            raise ValueError("Terra analysis index contains duplicate dates.")

        r = r.reindex(idx)
        p = p.reindex(idx)
        o = o.reindex(idx)

        channels = {"rho": r, "psi": p, "omega": o}

        for name, series in channels.items():
            values = series.to_numpy(dtype=float)
            if not np.isfinite(values).all():
                raise ValueError(
                    f"{name}: analysis data contain non-finite values."
                )
            if (values < 0).any():
                raise ValueError(
                    f"{name}: analysis data must be non-negative."
                )

        for key in ("r", "p", "o"):
            value = self.p.get(key)
            if value is None or not np.isfinite(value) or value <= 0:
                raise RuntimeError(
                    f"Invalid calibrated P_limit for {key}: {value}"
                )

        rn = r / self.p["r"]
        pn = p / self.p["p"]
        on = o / self.p["o"]

        for name, series in {
            "rho_norm": rn,
            "psi_norm": pn,
            "omega_norm": on,
        }.items():
            values = series.to_numpy(dtype=float)
            if not np.isfinite(values).all():
                raise ValueError(
                    f"{name}: normalized data contain non-finite values."
                )
            if (values < 0).any():
                raise ValueError(
                    f"{name}: normalized data must be non-negative."
                )

        st = rn * pn * on
        stress_values = st.to_numpy(dtype=float)

        if not np.isfinite(stress_values).all():
            raise ValueError("Terra stress contains non-finite values.")
        if (stress_values < 0).any():
            raise ValueError("Terra stress must be non-negative.")

        pi = (st * self.dt).cumsum()

        if not np.isfinite(pi.to_numpy(dtype=float)).all():
            raise ValueError("Terra Pi contains non-finite values.")

        return pd.DataFrame(
            {
                "rho": r,
                "psi": p,
                "omega": o,
                "rho_norm": rn,
                "psi_norm": pn,
                "omega_norm": on,
                "stress": st,
                "pi": pi,
            },
            index=idx,
        )

def fetch():
    import yfinance as yf
    print("="*60+"\n  Terra-Luna v2: ρ=BTC, Ψ=LUNA, Ω=Corr\n"+"="*60)
    
    btc = yf.download(
        "BTC-USD",
        start=DATA_START,
        end=DATA_END,
        progress=False,
        auto_adjust=False,
    )
    if btc.empty:
        raise RuntimeError("BTC-USD retrieval returned no data.")
    if isinstance(btc.columns, pd.MultiIndex):
        btc.columns = btc.columns.get_level_values(0)
    if "Close" not in btc.columns:
        raise RuntimeError("BTC-USD response has no Close column.")
    btc.index = pd.to_datetime(btc.index).tz_localize(None).normalize()
    btc = btc[~btc.index.duplicated(keep="last")].sort_index()
    rho = pd.to_numeric(btc["Close"], errors="coerce").diff(
        DELTA_RHO
    ).abs()
    print(f"  ρ (BTC |Δ{DELTA_RHO}d|): {rho.dropna().shape[0]} pts")
    
    luna_df = yf.download(
        "LUNC-USD",
        start=DATA_START,
        end=DATA_END,
        progress=False,
        auto_adjust=False,
    )
    if luna_df.empty:
        raise RuntimeError("LUNC-USD retrieval returned no data.")
    if isinstance(luna_df.columns, pd.MultiIndex):
        luna_df.columns = luna_df.columns.get_level_values(0)
    if "Close" not in luna_df.columns:
        raise RuntimeError("LUNC-USD response has no Close column.")
    luna_df.index = (
        pd.to_datetime(luna_df.index).tz_localize(None).normalize()
    )
    luna_df = luna_df[
        ~luna_df.index.duplicated(keep="last")
    ].sort_index()
    luna = pd.to_numeric(luna_df["Close"], errors="coerce")
    print(f"  Ψ LUNA Classic (LUNC-USD): {len(luna)} rows")
    psi = luna.diff(DELTA_PSI).abs()
    
    eth = yf.download(
        "ETH-USD",
        start=DATA_START,
        end=DATA_END,
        progress=False,
        auto_adjust=False,
    )
    if eth.empty:
        raise RuntimeError("ETH-USD retrieval returned no data.")
    if isinstance(eth.columns, pd.MultiIndex):
        eth.columns = eth.columns.get_level_values(0)
    if "Close" not in eth.columns:
        raise RuntimeError("ETH-USD response has no Close column.")
    eth.index = pd.to_datetime(eth.index).tz_localize(None).normalize()
    eth = eth[~eth.index.duplicated(keep="last")].sort_index()
    
    prices = pd.DataFrame(
        {
            "BTC": pd.to_numeric(btc["Close"], errors="coerce"),
            "ETH": pd.to_numeric(eth["Close"], errors="coerce"),
            "LUNA": luna,
        }
    ).sort_index()

    if (prices.dropna() <= 0).any().any():
        raise ValueError(
            "BTC/ETH/LUNA prices must be positive before log returns."
        )

    rets = np.log(prices / prices.shift(1))

    omega_values = []

    for i in range(len(rets)):
        if i < CORR_WIN:
            omega_values.append(np.nan)
            continue

        window = rets.iloc[i - CORR_WIN:i]

        # Ω has one fixed definition: pairwise correlations among all
        # three required assets over a complete 60-observation window.
        # If that definition cannot be evaluated, the value is missing.
        if (
            len(window) != CORR_WIN
            or window[["BTC", "ETH", "LUNA"]].isna().any().any()
        ):
            omega_values.append(np.nan)
            continue

        corr = window[["BTC", "ETH", "LUNA"]].corr()
        upper = corr.to_numpy(dtype=float)[
            np.triu_indices(3, k=1)
        ]

        if not np.isfinite(upper).all():
            omega_values.append(np.nan)
            continue

        mean_corr = float(upper.mean())

        if mean_corr < -1.0 - 1e-12 or mean_corr > 1.0 + 1e-12:
            raise ValueError(
                f"Invalid mean correlation outside [-1, 1]: {mean_corr}"
            )

        omega_value = (mean_corr + 1.0) / 2.0

        if not np.isfinite(omega_value):
            raise ValueError("Computed Terra omega is non-finite.")

        omega_values.append(omega_value)

    omega = pd.Series(
        omega_values,
        index=rets.index,
        name="omega",
        dtype=float,
    )
    print(f"  Ω (corr): {omega.dropna().shape[0]} pts")
    
    common = (
        rho.dropna()
        .index.intersection(psi.dropna().index)
        .intersection(omega.dropna().index)
        .sort_values()
    )

    if len(common) == 0:
        raise ValueError("No complete Terra observations remain.")
    if common.has_duplicates:
        raise ValueError("Terra common index contains duplicate dates.")

    rho = rho.reindex(common)
    psi = psi.reindex(common)
    omega = omega.reindex(common)

    aligned = {
        "rho": rho,
        "psi": psi,
        "omega": omega,
    }

    for name, series in aligned.items():
        values = series.to_numpy(dtype=float)

        if not np.isfinite(values).all():
            raise ValueError(
                f"{name}: aligned Terra data contain non-finite values."
            )
        if (values < 0).any():
            raise ValueError(
                f"{name}: aligned Terra data must be non-negative."
            )

    print(f"  📊 최종: {len(common)} pts")

    return aligned

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
    c = PiCalc(); c.calibrate(d['rho'],d['psi'],d['omega'])
    cr = c.calc(d['rho'],d['psi'],d['omega'],s=CRISIS_START,e=CRISIS_END)
    ct = c.calc(d['rho'],d['psi'],d['omega'],s=NEG_CONTROL_START,e=NEG_CONTROL_END)
    print(f"\n  Crisis Π: {cr['pi'].max():.4f} | Control Π: {ct['pi'].max():.4f}")
    cr.to_csv(f"{OUTPUT_DIR}/crisis_terra_luna_pi.csv")
    ct.to_csv(f"{OUTPUT_DIR}/control_terra_luna_pi.csv")
    pd.Series(c.p).to_csv(f"{OUTPUT_DIR}/p_limits.csv")
    plot_traj(cr,"Terra-Luna v2 (2022-05)",COLLAPSE_DATE,f"{OUTPUT_DIR}/fig1_pi_terra_luna.png")
    plot_comp(cr,ct,COLLAPSE_DATE,f"{OUTPUT_DIR}/fig2_terra_luna_vs_control.png")
    cd = pd.Timestamp(COLLAPSE_DATE)
    loc = cr.index.get_indexer([cd], method="nearest")

    if loc[0] < 0:
        raise ValueError("No crisis observation available near collapse date.")

    collapse_date = cr.index[loc[0]]
    pc = float(cr.loc[collapse_date, "pi"])
    cf = float(ct["pi"].iloc[-1])

    if not np.isfinite(pc):
        raise ValueError("Terra collapse Pi must be finite.")
    if not np.isfinite(cf) or cf <= 0:
        raise ValueError(
            "Terra control Pi must be positive and finite."
        )

    separation = pc / cf

    print(
        f"\n{'=' * 60}"
        f"\n  Π@collapse: {pc:.4f}"
        f"\n  Control:    {cf:.4f}"
        f"\n  Separation: {separation:.1f}x"
        f"\n{'=' * 60}"
    )

if __name__=="__main__": main()
