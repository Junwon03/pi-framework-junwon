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
  - Yahoo Finance (Nikkei 225 and USD/JPY)

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
                    f"{name}: no observations in Fukushima calibration period."
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
            f"  P_limits: rho={self.p['r']:.4f}, "
            f"psi={self.p['p']:.6f}, "
            f"omega={self.p['o']:.6f}"
        )
        return self.p

    def calc(self, r, p, o, s=None, e=None):
        if not self.ok:
            raise RuntimeError("calibrate() must be called before calc().")

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
            raise ValueError("No common Fukushima observations.")
        if idx.has_duplicates:
            raise ValueError(
                "Fukushima analysis index contains duplicate dates."
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
        values = stress.to_numpy(dtype=float)

        if not np.isfinite(values).all():
            raise ValueError("Fukushima stress contains non-finite values.")
        if (values < 0).any():
            raise ValueError("Fukushima stress must be non-negative.")

        pi = (stress * self.dt).cumsum()

        if not np.isfinite(pi.to_numpy(dtype=float)).all():
            raise ValueError("Fukushima Pi contains non-finite values.")

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

def mag_to_energy(mag):
    """Gutenberg-Richter: log10(E) = 1.5*M + 4.8 (Joules)"""
    return 10 ** (1.5 * mag + 4.8)


def fetch_usgs_earthquakes():
    """
    Fetch the complete M2+ USGS catalog for the declared Japan bounding box.

    Every monthly query is checked against the USGS count endpoint.
    Missing-event days are genuine zero-event days after a complete catalog
    has been verified; they are not forward-filled from earlier earthquakes.
    """
    print("\n[1/3] rho: USGS Earthquake Data (Japan, M2+)")
    print("-" * 50)

    query_url = "https://earthquake.usgs.gov/fdsnws/event/1/query"
    count_url = "https://earthquake.usgs.gov/fdsnws/event/1/count"

    chunks = []

    current = pd.Timestamp(DATA_START)
    data_end_exclusive = pd.Timestamp(DATA_END) + pd.Timedelta(days=1)

    while current < data_end_exclusive:
        next_month = current + pd.DateOffset(months=1)
        chunk_end_exclusive = min(next_month, data_end_exclusive)
        chunk_end = chunk_end_exclusive - pd.Timedelta(microseconds=1)

        base_params = {
            "starttime": current.isoformat(),
            "endtime": chunk_end.isoformat(),
            "minlatitude": JP_LAT_MIN,
            "maxlatitude": JP_LAT_MAX,
            "minlongitude": JP_LON_MIN,
            "maxlongitude": JP_LON_MAX,
            "minmagnitude": MIN_MAG,
        }

        label = current.strftime("%Y-%m")
        print(f"  {label}...", end=" ")

        try:
            count_response = requests.get(
                count_url,
                params=base_params,
                timeout=60,
            )
            count_response.raise_for_status()
        except requests.RequestException as exc:
            raise RuntimeError(
                f"USGS count request failed for {label}: {exc}"
            ) from exc

        try:
            expected_count = int(count_response.text.strip())
        except ValueError as exc:
            raise RuntimeError(
                f"USGS count response was not an integer for {label}: "
                f"{count_response.text!r}"
            ) from exc

        if expected_count < 0:
            raise RuntimeError(
                f"USGS returned invalid negative count for {label}."
            )

        # Official USGS query service maximum.
        if expected_count > 20000:
            raise RuntimeError(
                f"USGS monthly chunk {label} contains {expected_count} "
                "events, exceeding the 20,000-event query limit. "
                "Use smaller deterministic chunks."
            )

        if expected_count == 0:
            print("ok 0 events")
            current = chunk_end_exclusive
            continue

        query_params = dict(base_params)
        query_params.update(
            {
                "format": "csv",
                "orderby": "time-asc",
                "limit": 20000,
            }
        )

        try:
            response = requests.get(
                query_url,
                params=query_params,
                timeout=60,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise RuntimeError(
                f"USGS event request failed for {label}: {exc}"
            ) from exc

        try:
            frame = pd.read_csv(io.StringIO(response.text))
        except (pd.errors.ParserError, UnicodeDecodeError) as exc:
            raise RuntimeError(
                f"USGS CSV parsing failed for {label}."
            ) from exc

        required = {"id", "time", "mag"}
        if not required.issubset(frame.columns):
            raise RuntimeError(
                f"USGS response for {label} is missing columns: "
                f"{sorted(required - set(frame.columns))}"
            )

        if len(frame) != expected_count:
            raise RuntimeError(
                f"USGS completeness failure for {label}: "
                f"count endpoint={expected_count}, CSV rows={len(frame)}."
            )

        print(f"ok {len(frame)} events")
        chunks.append(frame)

        current = chunk_end_exclusive

    if not chunks:
        raise RuntimeError(
            "USGS returned no M2+ earthquake observations "
            "for the full Fukushima data period."
        )

    eq = pd.concat(chunks, ignore_index=True)

    if eq["id"].isna().any():
        raise RuntimeError("USGS catalog contains missing event IDs.")

    duplicate_ids = int(eq["id"].duplicated().sum())
    if duplicate_ids:
        raise RuntimeError(
            f"USGS catalog contains {duplicate_ids} duplicate event IDs."
        )

    eq["datetime"] = pd.to_datetime(
        eq["time"],
        utc=True,
        errors="coerce",
    )
    eq["mag"] = pd.to_numeric(eq["mag"], errors="coerce")

    if eq["datetime"].isna().any():
        raise RuntimeError("USGS catalog contains invalid event timestamps.")
    if eq["mag"].isna().any():
        raise RuntimeError("USGS catalog contains invalid magnitudes.")

    magnitudes = eq["mag"].to_numpy(dtype=float)

    if not np.isfinite(magnitudes).all():
        raise RuntimeError("USGS magnitudes contain non-finite values.")
    if (magnitudes < MIN_MAG).any():
        raise RuntimeError(
            "USGS response contains an event below MIN_MAG."
        )

    eq["date"] = (
        eq["datetime"]
        .dt.tz_localize(None)
        .dt.normalize()
    )
    eq["energy"] = mag_to_energy(eq["mag"])

    energy_values = eq["energy"].to_numpy(dtype=float)
    if not np.isfinite(energy_values).all():
        raise RuntimeError(
            "Calculated earthquake energies contain non-finite values."
        )
    if (energy_values <= 0).any():
        raise RuntimeError(
            "Calculated earthquake energies must be positive."
        )

    daily_total_energy = eq.groupby("date")["energy"].sum()
    daily_max_mag = eq.groupby("date")["mag"].max()
    daily_count = eq.groupby("date")["mag"].count()

    # Complete calendar-day definition:
    # no catalogued M2+ event in the verified region/day means zero energy.
    calendar = pd.date_range(
        pd.Timestamp(DATA_START),
        pd.Timestamp(DATA_END),
        freq="D",
    )

    daily_total_energy = daily_total_energy.reindex(
        calendar,
        fill_value=0.0,
    )

    # Preserve the original positive-event transformation exactly:
    # log10(E) on earthquake days. A verified zero-event calendar day
    # is assigned E=0 and maps to log10(1)=0.
    rho_raw = np.log10(daily_total_energy.clip(lower=1.0))
    rho_raw.name = "rho"

    rho_values = rho_raw.to_numpy(dtype=float)

    if not np.isfinite(rho_values).all():
        raise RuntimeError("Fukushima rho contains non-finite values.")
    if (rho_values < 0).any():
        raise RuntimeError("Fukushima rho must be non-negative.")

    print(
        f"\n  Total: {len(eq)} unique earthquakes "
        f"(M{MIN_MAG}+)"
    )
    print(f"  Max magnitude: M{eq['mag'].max():.1f}")

    event_date = pd.Timestamp(COLLAPSE_DATE)
    if event_date not in daily_max_mag.index:
        raise RuntimeError(
            f"No USGS earthquake found on collapse date {COLLAPSE_DATE}."
        )

    d311 = float(daily_total_energy.loc[event_date])
    m311 = float(daily_max_mag.loc[event_date])
    c311 = int(daily_count.loc[event_date])

    print(
        f"  3/11: M{m311:.1f}, {c311} events, "
        f"total E={d311:.2e} J, "
        f"log10(E)={np.log10(d311):.2f}"
    )

    stable_rho = rho_raw[STABLE_START:STABLE_END]

    if stable_rho.empty:
        raise RuntimeError("Fukushima stable rho period is empty.")

    print(
        f"  Stable period: {len(stable_rho)} calendar days, "
        f"log10(E_or_1) range: "
        f"{stable_rho.min():.1f} ~ {stable_rho.max():.1f}"
    )
    print(
        f"  rho (log10(max(daily M2+ energy, 1))): "
        f"{len(rho_raw)} calendar days"
    )

    return rho_raw

def fetch_nikkei_jpy():
    """Yahoo Finance -> Nikkei 225 + USD/JPY."""
    print("\n[2/3] psi: Nikkei 225 Volatility")
    print("[3/3] omega: USD/JPY Rate Change")
    print("-" * 50)

    import yfinance as yf

    print("  ^N225...", end=" ")
    nk = yf.download(
        "^N225",
        start=DATA_START,
        end=DATA_END,
        progress=False,
        auto_adjust=False,
    )

    if nk.empty:
        raise RuntimeError("^N225 retrieval returned no data.")
    if isinstance(nk.columns, pd.MultiIndex):
        nk.columns = nk.columns.get_level_values(0)
    if "Close" not in nk.columns:
        raise RuntimeError("^N225 response has no Close column.")

    nk.index = (
        pd.to_datetime(nk.index)
        .tz_localize(None)
        .normalize()
    )
    nk = nk[~nk.index.duplicated(keep="last")].sort_index()
    nk_close = pd.to_numeric(nk["Close"], errors="coerce")

    if nk_close.dropna().empty:
        raise RuntimeError("^N225 has no numeric Close observations.")

    print(f"ok {len(nk)} rows")

    nk_ret = nk_close.pct_change(fill_method=None)
    psi = nk_ret.rolling(5).std() * np.sqrt(252)

    nk_crisis = nk_close["2011-03-10":"2011-03-18"].dropna()
    if len(nk_crisis) >= 2:
        drop = (
            nk_crisis.iloc[-1] / nk_crisis.iloc[0] - 1
        ) * 100
        print(f"  Nikkei 3/10~3/18: {drop:.1f}% change")

    print("  JPY=X...", end=" ")
    jpy = yf.download(
        "JPY=X",
        start=DATA_START,
        end=DATA_END,
        progress=False,
        auto_adjust=False,
    )

    if jpy.empty:
        raise RuntimeError("JPY=X retrieval returned no data.")
    if isinstance(jpy.columns, pd.MultiIndex):
        jpy.columns = jpy.columns.get_level_values(0)
    if "Close" not in jpy.columns:
        raise RuntimeError("JPY=X response has no Close column.")

    jpy.index = (
        pd.to_datetime(jpy.index)
        .tz_localize(None)
        .normalize()
    )
    jpy = jpy[~jpy.index.duplicated(keep="last")].sort_index()
    jpy_close = pd.to_numeric(jpy["Close"], errors="coerce")

    if jpy_close.dropna().empty:
        raise RuntimeError("JPY=X has no numeric Close observations.")

    print(f"ok {len(jpy)} rows")

    omega = jpy_close.pct_change(fill_method=None).abs()

    jpy_crisis = jpy_close["2011-03-10":"2011-03-18"].dropna()
    if len(jpy_crisis) >= 2:
        print(
            f"  USD/JPY 3/10: {jpy_crisis.iloc[0]:.2f} "
            f"-> min: {jpy_crisis.min():.2f}"
        )

    print(f"  psi (Nikkei vol): {psi.dropna().shape[0]} pts")
    print(
        f"  omega (JPY change): "
        f"{omega.dropna().shape[0]} pts"
    )

    return psi, omega

def fetch():
    print("=" * 60)
    print(
        "  Fukushima v2: "
        "rho=Quake(USGS) | psi=Nikkei | omega=JPY"
    )
    print("=" * 60)

    rho = fetch_usgs_earthquakes()
    psi, omega = fetch_nikkei_jpy()

    print("\n[Align]")

    trading_days = (
        psi.dropna()
        .index.intersection(omega.dropna().index)
        .sort_values()
    )

    if len(trading_days) == 0:
        raise ValueError(
            "No common Nikkei/JPY trading observations."
        )
    if trading_days.has_duplicates:
        raise ValueError("Trading-day index contains duplicates.")

    print(f"  Trading days: {len(trading_days)}")

    rho.index = pd.to_datetime(rho.index).normalize()

    # rho is now defined on every calendar date, so trading-day
    # alignment is an exact-date selection, not state carry-forward.
    rho_aligned = rho.reindex(trading_days)
    psi_aligned = psi.reindex(trading_days)
    omega_aligned = omega.reindex(trading_days)

    for name, series in {
        "rho": rho_aligned,
        "psi": psi_aligned,
        "omega": omega_aligned,
    }.items():
        if series.isna().any():
            missing = series.index[series.isna()]
            raise ValueError(
                f"{name}: {len(missing)} missing aligned observations; "
                f"first={missing[0].date()}."
            )

        values = series.to_numpy(dtype=float)

        if not np.isfinite(values).all():
            raise ValueError(
                f"{name}: aligned data contain non-finite values."
            )
        if (values < 0).any():
            raise ValueError(
                f"{name}: aligned data must be non-negative."
            )

    for d in [
        "2011-03-10",
        "2011-03-11",
        "2011-03-14",
        "2011-03-15",
    ]:
        ts = pd.Timestamp(d)
        if ts in rho_aligned.index:
            print(
                f"  {d}: "
                f"rho={rho_aligned.loc[ts]:.2f}, "
                f"psi={psi_aligned.loc[ts]:.4f}, "
                f"omega={omega_aligned.loc[ts]:.6f}"
            )

    print(
        f"  Final: {len(trading_days)} pts, "
        f"rho>0: {(rho_aligned > 0).sum()}"
    )

    return {
        "rho": rho_aligned,
        "psi": psi_aligned,
        "omega": omega_aligned,
    }

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
    loc = cr.index.get_indexer([cd], method="nearest")

    if loc[0] < 0:
        raise ValueError(
            "No Fukushima crisis observation near collapse date."
        )

    collapse_obs = cr.index[loc[0]]
    pc = float(cr.loc[collapse_obs, "pi"])
    cf = float(ct["pi"].iloc[-1])

    if not np.isfinite(pc):
        raise ValueError("Fukushima collapse Pi must be finite.")
    if not np.isfinite(cf) or cf <= 0:
        raise ValueError(
            "Fukushima control Pi must be positive and finite."
        )

    separation = pc / cf

    print(f"\n{'='*60}")
    print(f"  Pi@collapse: {pc:.6f}")
    print(f"  Control:     {cf:.6f}")
    print(f"  Separation:  {separation:.1f}x")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
