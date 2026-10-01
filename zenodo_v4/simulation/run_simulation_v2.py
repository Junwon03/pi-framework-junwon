import hashlib
import json
import platform
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]

CONFIG_PATH = (
    ROOT
    / "zenodo_v4"
    / "config"
    / "simulation_config_v2.json"
)

BASE = ROOT / "zenodo_v4" / "simulation"
RESULTS_DIR = BASE / "results"

ALT_PATH = RESULTS_DIR / "simulation_v2_alt_replicates.csv"
NULL_PATH = RESULTS_DIR / "simulation_v2_null_replicates.csv"
SUMMARY_PATH = RESULTS_DIR / "simulation_v2_summary.csv"
METADATA_PATH = RESULTS_DIR / "simulation_v2_run_metadata.json"


def sha256_file(path):
    h = hashlib.sha256()

    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)

    return h.hexdigest()


with CONFIG_PATH.open("r", encoding="utf-8") as f:
    cfg = json.load(f)


sim = cfg["simulation"]
norm_cfg = cfg["normalization"]
rnd = cfg["randomness"]


# ---------------------------------------------------------------------
# Frozen configuration
# ---------------------------------------------------------------------

MASTER_SEED = int(rnd["master_seed"])

CHANNELS = int(sim["channels"])
PHI = float(sim["phi"])

BURN_IN = int(sim["burn_in"])
CONTROL_N = int(sim["control_n"])
POST_N = int(sim["post_control_n"])

ALT_REPS = int(
    sim["alternative_replications_per_cell"]
)

NULL_REPS = int(
    sim["matched_null_replications_per_rho"]
)

K_VALUES = list(sim["grid"]["k"])
RHO_VALUES = list(sim["grid"]["rho"])
DELTA_VALUES = list(sim["grid"]["delta"])

stress_start_1based, stress_end_1based = (
    sim["stress_interval_post_control_1based"]
)

# Python zero-based, end-exclusive.
STRESS_START = int(stress_start_1based) - 1
STRESS_END = int(stress_end_1based)

TOTAL_RETAINED = CONTROL_N + POST_N
TOTAL_GENERATED = BURN_IN + TOTAL_RETAINED

AR_SCALE = np.sqrt(1.0 - PHI ** 2)


# ---------------------------------------------------------------------
# Frozen-design assertions
# ---------------------------------------------------------------------

if CHANNELS != 3:
    raise RuntimeError(
        "Protocol v2 requires exactly three channels."
    )

if K_VALUES != [1, 2, 3]:
    raise RuntimeError(
        f"Unexpected k grid: {K_VALUES}"
    )

if RHO_VALUES != [0.0, 0.3, 0.6, 0.9]:
    raise RuntimeError(
        f"Unexpected rho grid: {RHO_VALUES}"
    )

if DELTA_VALUES != [0.5, 1.0, 1.5]:
    raise RuntimeError(
        f"Unexpected delta grid: {DELTA_VALUES}"
    )

if PHI != 0.5:
    raise RuntimeError(
        f"Unexpected phi: {PHI}"
    )

if BURN_IN != 500:
    raise RuntimeError(
        f"Unexpected burn-in: {BURN_IN}"
    )

if CONTROL_N != 250 or POST_N != 250:
    raise RuntimeError(
        "Protocol requires 250 control and 250 post observations."
    )

if STRESS_START != 75 or STRESS_END != 175:
    raise RuntimeError(
        "Stress interval must be post observations 76-175 inclusive."
    )

if STRESS_END - STRESS_START != 100:
    raise RuntimeError(
        "Stress interval must contain exactly 100 observations."
    )

if ALT_REPS != 1000 or NULL_REPS != 1000:
    raise RuntimeError(
        "Protocol requires 1,000 alternative and 1,000 null replicates."
    )

if (
    norm_cfg["primary"]["name"]
    != "P99_scaling"
):
    raise RuntimeError(
        "Primary normalization must be P99 scaling."
    )

if (
    norm_cfg["supplementary"]["name"]
    != "empirical_percentile"
):
    raise RuntimeError(
        "Supplementary normalization must be empirical percentile."
    )


# ---------------------------------------------------------------------
# Simulation
# ---------------------------------------------------------------------

def covariance_matrix(rho):
    cov = np.full(
        (CHANNELS, CHANNELS),
        float(rho),
        dtype=float,
    )

    np.fill_diagonal(cov, 1.0)

    eigenvalues = np.linalg.eigvalsh(cov)

    if np.any(eigenvalues <= 0):
        raise RuntimeError(
            f"Non-positive-definite covariance for rho={rho}"
        )

    return cov


def generate_baseline(reps, rho, seed_components):
    """
    Generate:
      g_t = phi*g_(t-1) + sqrt(1-phi^2)*epsilon_t
      x_t = exp(g_t)

    Initial latent state is zero before the 500-observation burn-in.
    """

    rng = np.random.Generator(
        np.random.PCG64(
            np.random.SeedSequence(seed_components)
        )
    )

    cov = covariance_matrix(rho)
    chol = np.linalg.cholesky(cov)

    independent = rng.standard_normal(
        size=(
            reps,
            TOTAL_GENERATED,
            CHANNELS,
        )
    )

    innovations = (
        independent
        @ chol.T
    )

    g = np.empty_like(
        innovations,
        dtype=float,
    )

    previous = np.zeros(
        (reps, CHANNELS),
        dtype=float,
    )

    for t in range(TOTAL_GENERATED):
        current = (
            PHI * previous
            + AR_SCALE * innovations[:, t, :]
        )

        g[:, t, :] = current
        previous = current

    retained_g = g[:, BURN_IN:, :]

    x = np.exp(retained_g)

    if not np.isfinite(x).all():
        raise RuntimeError(
            "Generated baseline x contains non-finite values."
        )

    if (x <= 0).any():
        raise RuntimeError(
            "Generated baseline x must be strictly positive."
        )

    return x


def inject_stress(x, k, delta):
    """
    Add delta * control-period observed-scale sample SD
    to first k channels during post observations 76-175.
    """

    x_star = x.copy()

    control = x[:, :CONTROL_N, :]

    control_sd = np.std(
        control,
        axis=1,
        ddof=1,
    )

    if not np.isfinite(control_sd).all():
        raise RuntimeError(
            "Control SD contains non-finite values."
        )

    if (control_sd <= 0).any():
        raise RuntimeError(
            "Control SD must be positive."
        )

    retained_start = (
        CONTROL_N
        + STRESS_START
    )

    retained_end = (
        CONTROL_N
        + STRESS_END
    )

    shift = (
        float(delta)
        * control_sd[:, None, :k]
    )

    x_star[
        :,
        retained_start:retained_end,
        :k,
    ] += shift

    return x_star


# ---------------------------------------------------------------------
# Normalizations
# ---------------------------------------------------------------------

def normalize_p99(x_star):
    control = x_star[:, :CONTROL_N, :]

    p99 = np.percentile(
        control,
        99,
        axis=1,
    )

    if not np.isfinite(p99).all():
        raise RuntimeError(
            "P99 contains non-finite values."
        )

    if (p99 <= 0).any():
        raise RuntimeError(
            "P99 must be positive."
        )

    z = (
        x_star
        / p99[:, None, :]
    )

    return z


def normalize_empirical_percentile(x_star):
    """
    u_jt =
      (0.5 + count{control x_ji <= x*_jt})
      / (n_control + 1)

    The same generated x_star used in the primary analysis
    is reused here.
    """

    reps = x_star.shape[0]

    u = np.empty_like(
        x_star,
        dtype=float,
    )

    control = x_star[:, :CONTROL_N, :]

    for r in range(reps):
        for j in range(CHANNELS):
            sorted_control = np.sort(
                control[r, :, j]
            )

            counts = np.searchsorted(
                sorted_control,
                x_star[r, :, j],
                side="right",
            )

            u[r, :, j] = (
                0.5 + counts
            ) / (
                CONTROL_N + 1.0
            )

    if not np.isfinite(u).all():
        raise RuntimeError(
            "Empirical-percentile normalization contains "
            "non-finite values."
        )

    if (u <= 0).any() or (u >= 1).any():
        raise RuntimeError(
            "Empirical-percentile values must lie strictly "
            "between 0 and 1."
        )

    return u


# ---------------------------------------------------------------------
# Operators and T
# ---------------------------------------------------------------------

def operator_arrays(normalized):
    product = np.prod(
        normalized,
        axis=2,
    )

    summation = np.sum(
        normalized,
        axis=2,
    )

    maximum = np.max(
        normalized,
        axis=2,
    )

    return {
        "product": product,
        "sum": summation,
        "maximum": maximum,
    }


def compute_T(normalized):
    operators = operator_arrays(
        normalized
    )

    out = {}

    for name, values in operators.items():
        control_mean = values[
            :, :CONTROL_N
        ].mean(axis=1)

        post_mean = values[
            :, CONTROL_N:
        ].mean(axis=1)

        if (control_mean <= 0).any():
            raise RuntimeError(
                f"{name}: non-positive control mean."
            )

        if (post_mean <= 0).any():
            raise RuntimeError(
                f"{name}: non-positive post mean."
            )

        T = np.log(
            post_mean
            / control_mean
        )

        if not np.isfinite(T).all():
            raise RuntimeError(
                f"{name}: T contains non-finite values."
            )

        out[name] = T

    return out


def compute_both_normalizations(x_star):
    p99 = normalize_p99(
        x_star
    )

    empirical = normalize_empirical_percentile(
        x_star
    )

    return {
        "p99": compute_T(p99),
        "empirical_percentile": compute_T(
            empirical
        ),
    }


# ---------------------------------------------------------------------
# Matched nulls
# ---------------------------------------------------------------------

null_records = []
null_arrays = {}

for rho_index, rho in enumerate(
    RHO_VALUES
):

    print(
        f"[NULL] rho={rho}"
    )

    seed_components = [
        MASTER_SEED,
        0,
        rho_index,
        0,
        0,
    ]

    x_null = generate_baseline(
        NULL_REPS,
        rho,
        seed_components,
    )

    null_results = compute_both_normalizations(
        x_null
    )

    null_arrays[rho] = null_results

    for normalization, op_data in (
        null_results.items()
    ):
        for operator, values in (
            op_data.items()
        ):
            for replicate, value in enumerate(
                values
            ):
                null_records.append(
                    {
                        "rho": rho,
                        "replicate": replicate,
                        "normalization": normalization,
                        "operator": operator,
                        "T": float(value),
                    }
                )


# ---------------------------------------------------------------------
# Alternatives
# ---------------------------------------------------------------------

alt_records = []
summary_records = []

for k_index, k in enumerate(
    K_VALUES
):
    for rho_index, rho in enumerate(
        RHO_VALUES
    ):
        for delta_index, delta in enumerate(
            DELTA_VALUES
        ):

            print(
                f"[ALT] k={k} "
                f"rho={rho} "
                f"delta={delta}"
            )

            seed_components = [
                MASTER_SEED,
                k_index,
                rho_index,
                delta_index,
                1,
            ]

            x = generate_baseline(
                ALT_REPS,
                rho,
                seed_components,
            )

            x_star = inject_stress(
                x,
                k,
                delta,
            )

            alt_results = (
                compute_both_normalizations(
                    x_star
                )
            )

            for normalization, op_data in (
                alt_results.items()
            ):
                for operator, alt_values in (
                    op_data.items()
                ):

                    null_values = (
                        null_arrays[rho][
                            normalization
                        ][operator]
                    )

                    alt_mean = float(
                        np.mean(alt_values)
                    )

                    alt_sd = float(
                        np.std(
                            alt_values,
                            ddof=1,
                        )
                    )

                    alt_se = (
                        alt_sd
                        / np.sqrt(
                            len(alt_values)
                        )
                    )

                    ci_low = (
                        alt_mean
                        - 1.96 * alt_se
                    )

                    ci_high = (
                        alt_mean
                        + 1.96 * alt_se
                    )

                    null_mean = float(
                        np.mean(
                            null_values
                        )
                    )

                    null_sd = float(
                        np.std(
                            null_values,
                            ddof=1,
                        )
                    )

                    if (
                        not np.isfinite(
                            null_sd
                        )
                        or null_sd <= 0
                    ):
                        raise RuntimeError(
                            "Matched-null SD must be "
                            "positive and finite."
                        )

                    D = (
                        alt_mean
                        - null_mean
                    ) / null_sd

                    summary_records.append(
                        {
                            "k": k,
                            "rho": rho,
                            "delta": delta,
                            "normalization": normalization,
                            "operator": operator,
                            "n_alt": len(
                                alt_values
                            ),
                            "n_null": len(
                                null_values
                            ),
                            "mean_T_alt": alt_mean,
                            "sd_T_alt": alt_sd,
                            "mc95_low_mean_T_alt": (
                                float(ci_low)
                            ),
                            "mc95_high_mean_T_alt": (
                                float(ci_high)
                            ),
                            "mean_T_null": null_mean,
                            "sd_T_null": null_sd,
                            "D": float(D),
                        }
                    )

                    for replicate, value in enumerate(
                        alt_values
                    ):
                        alt_records.append(
                            {
                                "k": k,
                                "rho": rho,
                                "delta": delta,
                                "replicate": replicate,
                                "normalization": normalization,
                                "operator": operator,
                                "T": float(value),
                            }
                        )


# ---------------------------------------------------------------------
# Save
# ---------------------------------------------------------------------

RESULTS_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

alt_df = pd.DataFrame(
    alt_records
)

null_df = pd.DataFrame(
    null_records
)

summary_df = pd.DataFrame(
    summary_records
)


expected_alt_rows = (
    len(K_VALUES)
    * len(RHO_VALUES)
    * len(DELTA_VALUES)
    * ALT_REPS
    * 2
    * 3
)

expected_null_rows = (
    len(RHO_VALUES)
    * NULL_REPS
    * 2
    * 3
)

expected_summary_rows = (
    len(K_VALUES)
    * len(RHO_VALUES)
    * len(DELTA_VALUES)
    * 2
    * 3
)

if len(alt_df) != expected_alt_rows:
    raise RuntimeError(
        f"Unexpected alt row count: "
        f"{len(alt_df)} != {expected_alt_rows}"
    )

if len(null_df) != expected_null_rows:
    raise RuntimeError(
        f"Unexpected null row count: "
        f"{len(null_df)} != {expected_null_rows}"
    )

if len(summary_df) != expected_summary_rows:
    raise RuntimeError(
        f"Unexpected summary row count: "
        f"{len(summary_df)} != {expected_summary_rows}"
    )

alt_df.to_csv(
    ALT_PATH,
    index=False,
)

null_df.to_csv(
    NULL_PATH,
    index=False,
)

summary_df.to_csv(
    SUMMARY_PATH,
    index=False,
)


metadata = {
    "status": "FROZEN_SIMULATION_V2_RESULT",
    "config_sha256": sha256_file(
        CONFIG_PATH
    ),
    "master_seed": MASTER_SEED,
    "bit_generator": "PCG64",
    "numpy_version": np.__version__,
    "pandas_version": pd.__version__,
    "python_version": platform.python_version(),
    "design": {
        "channels": CHANNELS,
        "phi": PHI,
        "burn_in": BURN_IN,
        "control_n": CONTROL_N,
        "post_control_n": POST_N,
        "stress_interval_post_1based": [
            stress_start_1based,
            stress_end_1based,
        ],
        "k": K_VALUES,
        "rho": RHO_VALUES,
        "delta": DELTA_VALUES,
        "alternative_replications_per_cell": ALT_REPS,
        "matched_null_replications_per_rho": NULL_REPS,
    },
    "normalizations": [
        "P99_scaling",
        "empirical_percentile",
    ],
    "operators": [
        "product",
        "sum",
        "maximum",
    ],
    "primary_statistic": (
        "T = log(mean(S_post)/mean(S_control))"
    ),
    "standardized_separation": (
        "D = (mean(T_alt)-mean(T_null))/sd(T_null)"
    ),
    "row_counts": {
        "alternative_replicate_rows": int(
            len(alt_df)
        ),
        "null_replicate_rows": int(
            len(null_df)
        ),
        "summary_rows": int(
            len(summary_df)
        ),
    },
}

with METADATA_PATH.open(
    "w",
    encoding="utf-8",
) as f:
    json.dump(
        metadata,
        f,
        indent=2,
        ensure_ascii=False,
    )
    f.write("\n")


print()
print("Simulation v2 completed.")
print(
    f"Alternative replicate rows: "
    f"{len(alt_df)}"
)
print(
    f"Null replicate rows: "
    f"{len(null_df)}"
)
print(
    f"Summary rows: "
    f"{len(summary_df)}"
)
print(f"Saved: {ALT_PATH}")
print(f"Saved: {NULL_PATH}")
print(f"Saved: {SUMMARY_PATH}")
print(f"Saved: {METADATA_PATH}")
