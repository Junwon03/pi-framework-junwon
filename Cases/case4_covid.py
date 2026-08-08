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

의존성: pandas, numpy, matplotlib; archived COVID inputs in data/
"""

import hashlib
import os
import sys
from pathlib import Path

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# COVID financial dislocation: selected event date = 2020-03-23
# This date is used consistently by the active retrospective analyses.
# Crisis window remains limited to the acute financial shock phase.
COLLAPSE_DATE = "2020-03-23"
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

ROOT_DIR = Path(__file__).resolve().parents[1]

FROZEN_CRISIS_PATH = (
    ROOT_DIR / "data" / "crisis_covid_pi.csv"
)
FROZEN_CONTROL_PATH = (
    ROOT_DIR / "data" / "control_covid_pi.csv"
)

FROZEN_CRISIS_SHA256 = (
    "67a48251e96720da2f0c693aa61f0666"
    "aa6a72288f27576a6061de8ce7d27164"
)
FROZEN_CONTROL_SHA256 = (
    "b047dce647940941ec202924826fc0d4"
    "a4b7fd7d867cc69fbea51019e319551f"
)

RAW_COLUMNS = ["rho", "psi", "omega"]
DERIVED_COLUMNS = [
    "rho_norm",
    "psi_norm",
    "omega_norm",
    "stress",
    "pi",
]


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
                    f"{name}: no observations in COVID calibration period."
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
            raise ValueError("No common COVID observations.")

        if idx.has_duplicates:
            raise ValueError(
                "COVID analysis index contains duplicate dates."
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
        stress_values = stress.to_numpy(dtype=float)

        if not np.isfinite(stress_values).all():
            raise ValueError(
                "COVID stress contains non-finite values."
            )

        if (stress_values < 0).any():
            raise ValueError(
                "COVID stress must be non-negative."
            )

        pi = (stress * self.dt).cumsum()

        if not np.isfinite(
            pi.to_numpy(dtype=float)
        ).all():
            raise ValueError(
                "COVID Pi contains non-finite values."
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

def _sha256(path):
    h = hashlib.sha256()

    with path.open("rb") as f:
        for chunk in iter(
            lambda: f.read(1024 * 1024),
            b"",
        ):
            h.update(chunk)

    return h.hexdigest()


def _load_frozen_archive(path, expected_sha, label):
    if not path.is_file():
        raise FileNotFoundError(
            f"Missing frozen COVID {label} archive: {path}"
        )

    actual_sha = _sha256(path)

    if actual_sha != expected_sha:
        raise RuntimeError(
            f"Frozen COVID {label} hash mismatch: "
            f"expected {expected_sha}, got {actual_sha}"
        )

    frame = pd.read_csv(
        path,
        index_col=0,
        parse_dates=True,
    )

    required = set(RAW_COLUMNS + DERIVED_COLUMNS)
    missing = required - set(frame.columns)

    if missing:
        raise RuntimeError(
            f"Frozen COVID {label} archive is missing columns: "
            f"{sorted(missing)}"
        )

    if frame.empty:
        raise RuntimeError(
            f"Frozen COVID {label} archive is empty."
        )

    if frame.index.has_duplicates:
        raise RuntimeError(
            f"Frozen COVID {label} archive has duplicate dates."
        )

    if not frame.index.is_monotonic_increasing:
        raise RuntimeError(
            f"Frozen COVID {label} archive is not chronological."
        )

    numeric = frame[
        RAW_COLUMNS + DERIVED_COLUMNS
    ].apply(pd.to_numeric, errors="coerce")

    values = numeric.to_numpy(dtype=float)

    if not np.isfinite(values).all():
        raise RuntimeError(
            f"Frozen COVID {label} archive contains "
            "non-finite analysis values."
        )

    if (numeric[RAW_COLUMNS].to_numpy(dtype=float) < 0).any():
        raise RuntimeError(
            f"Frozen COVID {label} raw channels "
            "must be non-negative."
        )

    return numeric


def fetch():
    """
    Load the archived COVID analytical channels.

    These frozen files preserve the originally analyzed
    JH-CSSE global-case, VIX, and BAMLH0A0HYM2 high-yield
    spread channels.

    The live FRED source no longer exposes the required
    historical BAMLH0A0HYM2 period. No semantic proxy
    substitution is permitted.

    Zero rho values already present in the frozen archive
    are part of the archived retrospective specification.
    This loader does not create or impute additional zeros.
    """
    print("=" * 60)
    print(
        "  COVID-19: frozen JH cases | VIX | "
        "BAMLH0A0HYM2"
    )
    print("=" * 60)

    crisis_archive = _load_frozen_archive(
        FROZEN_CRISIS_PATH,
        FROZEN_CRISIS_SHA256,
        "crisis",
    )

    control_archive = _load_frozen_archive(
        FROZEN_CONTROL_PATH,
        FROZEN_CONTROL_SHA256,
        "control",
    )

    raw = crisis_archive[RAW_COLUMNS].copy()

    expected_control = raw.loc[
        NEG_CONTROL_START:NEG_CONTROL_END
    ]

    actual_control = control_archive[
        RAW_COLUMNS
    ]

    if not expected_control.index.equals(
        actual_control.index
    ):
        raise RuntimeError(
            "Frozen COVID crisis/control raw-channel "
            "indices disagree in the control window."
        )

    if not np.allclose(
        expected_control.to_numpy(dtype=float),
        actual_control.to_numpy(dtype=float),
        rtol=0.0,
        atol=0.0,
    ):
        raise RuntimeError(
            "Frozen COVID crisis/control raw channels "
            "disagree in their overlapping control window."
        )

    stable_rho = raw.loc[
        STABLE_START:STABLE_END,
        "rho",
    ]

    print(
        f"  Frozen crisis archive: "
        f"{len(crisis_archive)} rows"
    )
    print(
        f"  Frozen control archive: "
        f"{len(control_archive)} rows"
    )
    print(
        f"  Calibration rho: "
        f"{len(stable_rho)} rows, "
        f"zero={(stable_rho == 0).sum()}, "
        f"positive={(stable_rho > 0).sum()}"
    )

    for date in [
        "2020-01-31",
        "2020-03-11",
        "2020-03-16",
        "2020-03-23",
    ]:
        ts = pd.Timestamp(date)

        if ts in raw.index:
            print(
                f"  {date}: "
                f"rho={raw.loc[ts, 'rho']:.0f}, "
                f"psi={raw.loc[ts, 'psi']:.2f}, "
                f"omega={raw.loc[ts, 'omega']:.4f}"
            )

    return {
        "rho": raw["rho"],
        "psi": raw["psi"],
        "omega": raw["omega"],
    }


def validate_reproduction(crisis, control):
    """
    Independently confirm that the frozen raw channels and
    current formulas reproduce the archived derived values.
    """
    expected = {
        "crisis": _load_frozen_archive(
            FROZEN_CRISIS_PATH,
            FROZEN_CRISIS_SHA256,
            "crisis",
        ),
        "control": _load_frozen_archive(
            FROZEN_CONTROL_PATH,
            FROZEN_CONTROL_SHA256,
            "control",
        ),
    }

    actual = {
        "crisis": crisis,
        "control": control,
    }

    compare_columns = (
        RAW_COLUMNS + DERIVED_COLUMNS
    )

    for label in ("crisis", "control"):
        a = actual[label]
        e = expected[label]

        if not a.index.equals(e.index):
            raise RuntimeError(
                f"COVID {label} reproduction index mismatch."
            )

        for column in compare_columns:
            av = a[column].to_numpy(dtype=float)
            ev = e[column].to_numpy(dtype=float)

            if not np.allclose(
                av,
                ev,
                rtol=1e-12,
                atol=1e-12,
            ):
                max_diff = float(
                    np.max(np.abs(av - ev))
                )

                raise RuntimeError(
                    f"COVID {label} reproduction mismatch "
                    f"for {column}: "
                    f"max_abs_diff={max_diff}"
                )

    print(
        "  Frozen COVID reproduction: PASS "
        "(raw channels -> derived outputs)"
    )

def plot_traj(res, title, cd, path=None):
    plt.rcParams.update({'figure.dpi':150,'font.family':'serif','font.size':11,
                         'axes.grid':True,'grid.alpha':0.3})
    fig, ax = plt.subplots(3,1,figsize=(14,12),
                           gridspec_kw={'height_ratios':[3,2,2]}, sharex=True)
    c = pd.Timestamp(cd)
    ax[0].plot(res.index, res['pi'], color='#1a1a2e', lw=2, label='Pi(t)')
    ax[0].axvline(x=c, color='red', ls='--', alpha=.8, lw=1.5,
                  label=f'Financial dislocation ({cd})')
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
                  label=f'Financial dislocation ({cd})'); ax[0].legend()
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

    c = PiCalc()
    c.calibrate(
        d["rho"],
        d["psi"],
        d["omega"],
    )

    cr = c.calc(
        d["rho"],
        d["psi"],
        d["omega"],
        s=CRISIS_START,
        e=CRISIS_END,
    )

    ct = c.calc(
        d["rho"],
        d["psi"],
        d["omega"],
        s=NEG_CONTROL_START,
        e=NEG_CONTROL_END,
    )

    validate_reproduction(cr, ct)

    print(
        f"\n  Crisis Pi: {cr['pi'].max():.6f} "
        f"| Control Pi: {ct['pi'].max():.6f}"
    )

    cr.to_csv(f"{OUTPUT_DIR}/crisis_covid_pi.csv")
    ct.to_csv(f"{OUTPUT_DIR}/control_covid_pi.csv")
    pd.Series(c.p).to_csv(f"{OUTPUT_DIR}/p_limits.csv")

    plot_traj(cr, "COVID-19 Pandemic (2020-03)", COLLAPSE_DATE,
              f"{OUTPUT_DIR}/fig1_pi_covid.png")
    plot_comp(cr, ct, COLLAPSE_DATE,
              f"{OUTPUT_DIR}/fig2_covid_vs_control.png")

    cd = pd.Timestamp(COLLAPSE_DATE)
    loc = cr.index.get_indexer(
        [cd],
        method="nearest",
    )

    if loc[0] < 0:
        raise ValueError(
            "No COVID observation near selected event date."
        )

    event_obs = cr.index[loc[0]]

    pc = float(cr.loc[event_obs, "pi"])
    cf = float(ct["pi"].iloc[-1])

    if not np.isfinite(pc):
        raise ValueError(
            "COVID event-date Pi must be finite."
        )

    if not np.isfinite(cf) or cf <= 0:
        raise ValueError(
            "COVID control Pi must be positive and finite."
        )

    separation = pc / cf

    print(f"\n{'='*60}")
    print(f"  Pi@event:     {pc:.6f}")
    print(f"  Control:      {cf:.6f}")
    print(f"  Separation:   {separation:.1f}x")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
