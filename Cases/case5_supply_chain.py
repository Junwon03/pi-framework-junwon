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

import os

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import requests

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

FRED_API_KEY = os.environ.get("FRED_API_KEY", "")
FRED_VINTAGE_DATE = os.environ.get("FRED_VINTAGE_DATE", "")

# FRED Series IDs
SERIES = {
    'rho': 'PCEDG',              # Personal Consumption: Durable Goods (billions $)
    'psi': 'DTCDISA066MSFRBNY',  # Empire State Delivery Time Diffusion Index
    'omega': 'WPU3012',          # PPI: Freight Transportation
}


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
                    f"{name}: no Supply calibration observations."
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

        limits = {
            name: float(
                np.percentile(
                    series.to_numpy(dtype=float),
                    PLIMIT_PCT,
                )
            )
            for name, series in stable.items()
        }

        for name, value in limits.items():
            if not np.isfinite(value) or value <= 0:
                raise ValueError(
                    f"{name}: P_limit must be positive and finite; "
                    f"got {value}."
                )

        self.p = limits
        self.ok = True

        print(
            f"  P_limits: "
            f"rho={self.p['r']:.4f}, "
            f"psi={self.p['p']:.4f}, "
            f"omega={self.p['o']:.4f}"
        )

        return self.p

    def calc(self, r, p, o, s=None, e=None):
        if not self.ok:
            raise RuntimeError(
                "calibrate() must be called before calc()."
            )

        if s:
            r, p, o = r[s:], p[s:], o[s:]

        if e:
            r, p, o = r[:e], p[:e], o[:e]

        idx = (
            r.index
            .intersection(p.index)
            .intersection(o.index)
            .sort_values()
        )

        if len(idx) == 0:
            raise ValueError("No common Supply observations.")

        if idx.has_duplicates:
            raise ValueError(
                "Supply analysis index contains duplicate dates."
            )

        r = r.reindex(idx)
        p = p.reindex(idx)
        o = o.reindex(idx)

        for name, series in {
            "rho": r,
            "psi": p,
            "omega": o,
        }.items():
            values = series.to_numpy(dtype=float)

            if not np.isfinite(values).all():
                raise ValueError(
                    f"{name}: analysis data contain non-finite values."
                )

            if (values < 0).any():
                raise ValueError(
                    f"{name}: analysis data must be non-negative."
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

        stress = rn * pn * on

        if not np.isfinite(
            stress.to_numpy(dtype=float)
        ).all():
            raise ValueError(
                "Supply stress contains non-finite values."
            )

        if (stress.to_numpy(dtype=float) < 0).any():
            raise ValueError(
                "Supply stress must be non-negative."
            )

        pi = (stress * self.dt).cumsum()

        if not np.isfinite(
            pi.to_numpy(dtype=float)
        ).all():
            raise ValueError(
                "Supply Pi contains non-finite values."
            )

        return pd.DataFrame(
            {
                "rho": r,
                "psi": p,
                "omega": o,
                "rho_norm": rn,
                "psi_norm": pn,
                "omega_norm": on,
                "stress": stress,
                "pi": pi,
            },
            index=idx,
        )

def fetch_fred(series_id, label=""):
    """Fetch one complete monthly FRED series at a fixed vintage."""
    if not FRED_API_KEY:
        raise RuntimeError(
            "FRED_API_KEY is required for Supply analysis."
        )

    if not FRED_VINTAGE_DATE:
        raise RuntimeError(
            "FRED_VINTAGE_DATE is required for Supply analysis."
        )

    url = (
        "https://api.stlouisfed.org/"
        "fred/series/observations"
    )

    params = {
        "series_id": series_id,
        "api_key": FRED_API_KEY,
        "file_type": "json",
        "observation_start": DATA_START,
        "observation_end": DATA_END,
        "realtime_start": FRED_VINTAGE_DATE,
        "realtime_end": FRED_VINTAGE_DATE,
    }

    response = requests.get(
        url,
        params=params,
        timeout=30,
    )
    response.raise_for_status()

    payload = response.json()
    observations = payload.get("observations")

    if not isinstance(observations, list):
        raise RuntimeError(
            f"{series_id}: malformed FRED observations response."
        )

    if not observations:
        raise RuntimeError(
            f"{series_id}: FRED returned no observations."
        )

    frame = pd.DataFrame(observations)

    required = {"date", "value"}
    missing = required - set(frame.columns)

    if missing:
        raise RuntimeError(
            f"{series_id}: FRED response missing columns: "
            f"{sorted(missing)}"
        )

    frame["date"] = pd.to_datetime(
        frame["date"],
        errors="raise",
    )

    frame["value"] = pd.to_numeric(
        frame["value"],
        errors="coerce",
    )

    series = (
        frame
        .dropna(subset=["value"])
        .set_index("date")["value"]
        .sort_index()
    )

    if series.empty:
        raise RuntimeError(
            f"{series_id}: no numeric FRED observations."
        )

    if series.index.has_duplicates:
        raise RuntimeError(
            f"{series_id}: duplicate FRED dates."
        )

    expected_index = pd.date_range(
        DATA_START,
        DATA_END,
        freq="MS",
    )

    if not series.index.equals(expected_index):
        missing_dates = expected_index.difference(
            series.index
        )
        extra_dates = series.index.difference(
            expected_index
        )

        raise RuntimeError(
            f"{series_id}: incomplete monthly FRED series; "
            f"missing={list(missing_dates.strftime('%Y-%m-%d'))}, "
            f"extra={list(extra_dates.strftime('%Y-%m-%d'))}."
        )

    values = series.to_numpy(dtype=float)

    if not np.isfinite(values).all():
        raise RuntimeError(
            f"{series_id}: FRED data contain non-finite values."
        )

    return series

def fetch():
    print("=" * 60)
    print("  Supply Chain Crisis: ALL DATA FROM FRED")
    print(
        "  rho=PCEDG | psi=Delivery Time | "
        "omega=Freight PPI"
    )
    print(
        f"  Fixed FRED vintage: {FRED_VINTAGE_DATE}"
    )
    print("=" * 60)

    print("\n[1/3] rho: PCEDG (Durable Goods PCE)")
    print("-" * 50)
    print(f"  Fetching {SERIES['rho']}...", end=" ")

    rho_raw = fetch_fred(SERIES["rho"])
    print(f"ok {len(rho_raw)} months")

    # Absolute month-over-month durable-goods demand change.
    # fill_method=None prevents implicit missing-value propagation.
    rho = rho_raw.pct_change(
        fill_method=None
    ).abs()

    print(
        f"  PCEDG range: "
        f"${rho_raw.min():.0f}B ~ ${rho_raw.max():.0f}B"
    )
    print(
        f"  rho (|MoM change|): "
        f"{rho.dropna().shape[0]} pts"
    )

    print(
        f"\n[2/3] psi: Empire State Delivery Time "
        f"({SERIES['psi']})"
    )
    print("-" * 50)
    print(f"  Fetching {SERIES['psi']}...", end=" ")

    psi_raw = fetch_fred(SERIES["psi"])
    print(f"ok {len(psi_raw)} months")

    # Explicit one-sided stress transform:
    # positive diffusion-index values indicate worsening
    # delivery times; zero/negative values do not contribute
    # positive delivery-delay stress.
    psi = psi_raw.where(
        psi_raw > 0,
        0.0,
    )

    print(
        f"  Delivery time range: "
        f"{psi_raw.min():.1f} ~ {psi_raw.max():.1f}"
    )

    psi_2021 = psi_raw.loc["2021"]

    print(
        f"  2021 peak: {psi_2021.max():.1f} "
        f"on {psi_2021.idxmax().strftime('%Y-%m')}"
    )

    print(
        f"  One-sided psi transform: "
        f"{int((psi_raw < 0).sum())} negative raw months "
        "mapped to 0 stress"
    )

    print(
        f"\n[3/3] omega: PPI Freight Transportation "
        f"({SERIES['omega']})"
    )
    print("-" * 50)
    print(f"  Fetching {SERIES['omega']}...", end=" ")

    omega_raw = fetch_fred(SERIES["omega"])
    print(f"ok {len(omega_raw)} months")

    # Absolute month-over-month freight-price change.
    omega = omega_raw.pct_change(
        fill_method=None
    ).abs()

    print(
        f"  Freight PPI range: "
        f"{omega_raw.min():.1f} ~ {omega_raw.max():.1f}"
    )
    print(
        f"  omega (|MoM change|): "
        f"{omega.dropna().shape[0]} pts"
    )

    print("\n[Align]")

    common = (
        rho.dropna()
        .index.intersection(psi.dropna().index)
        .intersection(omega.dropna().index)
        .sort_values()
    )

    if len(common) == 0:
        raise ValueError(
            "No common Supply monthly observations."
        )

    if common.has_duplicates:
        raise ValueError(
            "Supply common index contains duplicate dates."
        )

    rho = rho.reindex(common)
    psi = psi.reindex(common)
    omega = omega.reindex(common)

    for name, series in {
        "rho": rho,
        "psi": psi,
        "omega": omega,
    }.items():
        values = series.to_numpy(dtype=float)

        if not np.isfinite(values).all():
            raise ValueError(
                f"{name}: aligned Supply data contain "
                "non-finite values."
            )

        if (values < 0).any():
            raise ValueError(
                f"{name}: aligned Supply data "
                "must be non-negative."
            )

    for d in [
        "2020-06-01",
        "2021-01-01",
        "2021-06-01",
        "2021-10-01",
        "2022-01-01",
    ]:
        ts = pd.Timestamp(d)
        loc = common.get_indexer(
            [ts],
            method="nearest",
        )

        if loc[0] < 0:
            raise ValueError(
                f"No Supply observation near {d}."
            )

        idx = common[loc[0]]

        print(
            f"  {d}: "
            f"rho={rho.loc[idx]:.4f}, "
            f"psi={psi.loc[idx]:.1f}, "
            f"omega={omega.loc[idx]:.4f}"
        )

    print(f"  Final: {len(common)} months")

    return {
        "rho": rho,
        "psi": psi,
        "omega": omega,
    }

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
    loc = cr.index.get_indexer(
        [cd],
        method="nearest",
    )

    if loc[0] < 0:
        raise ValueError(
            "No Supply observation near selected peak date."
        )

    peak_obs = cr.index[loc[0]]
    pc = float(cr.loc[peak_obs, "pi"])
    cf = float(ct["pi"].iloc[-1])

    if not np.isfinite(pc):
        raise ValueError(
            "Supply peak-date Pi must be finite."
        )

    if not np.isfinite(cf) or cf <= 0:
        raise ValueError(
            "Supply control Pi must be positive and finite."
        )

    separation = pc / cf

    print(f"\n{'='*60}")
    print(f"  Pi@peak:     {pc:.6f}")
    print(f"  Control:     {cf:.6f}")
    print(f"  Separation:  {separation:.1f}x")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
