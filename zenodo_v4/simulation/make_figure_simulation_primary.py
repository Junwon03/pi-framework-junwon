from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]

SUMMARY_PATH = (
    ROOT
    / "zenodo_v4"
    / "simulation"
    / "results"
    / "simulation_v2_summary.csv"
)

FIG_DIR = (
    ROOT
    / "zenodo_v4"
    / "simulation"
    / "figures"
)

SOURCE_CSV_PATH = FIG_DIR / "figure_simulation_primary_p99_delta1_source.csv"
PNG_PATH = FIG_DIR / "Figure_simulation_primary_p99_delta1.png"
PDF_PATH = FIG_DIR / "Figure_simulation_primary_p99_delta1.pdf"

NORMALIZATION = "p99"
DELTA = 1.0
K_VALUES = [1, 2, 3]
RHO_VALUES = [0.0, 0.3, 0.6, 0.9]
OPERATORS = ["product", "sum", "maximum"]

df = pd.read_csv(SUMMARY_PATH)

plot_df = df[
    (df["normalization"] == NORMALIZATION)
    & (df["delta"] == DELTA)
].copy()

expected_rows = len(K_VALUES) * len(RHO_VALUES) * len(OPERATORS)
if len(plot_df) != expected_rows:
    raise RuntimeError(
        f"Unexpected row count for plotting: {len(plot_df)} != {expected_rows}"
    )

plot_df["rho"] = plot_df["rho"].astype(float)
plot_df["k"] = plot_df["k"].astype(int)
plot_df["D"] = plot_df["D"].astype(float)

plot_df = plot_df.sort_values(
    ["k", "operator", "rho"]
).reset_index(drop=True)

FIG_DIR.mkdir(parents=True, exist_ok=True)
plot_df.to_csv(SOURCE_CSV_PATH, index=False)

fig, axes = plt.subplots(1, 3, figsize=(12, 4), sharey=True)

for ax, k in zip(axes, K_VALUES):
    panel = plot_df[plot_df["k"] == k]

    for operator in OPERATORS:
        sub = panel[panel["operator"] == operator].sort_values("rho")

        if list(sub["rho"]) != RHO_VALUES:
            raise RuntimeError(
                f"Unexpected rho grid for k={k}, operator={operator}: "
                f"{list(sub['rho'])}"
            )

        ax.plot(
            sub["rho"],
            sub["D"],
            marker="o",
            linewidth=1.8,
            label=operator,
        )

    ax.set_title(f"k = {k}")
    ax.set_xlabel("Cross-channel dependence (ρ)")
    ax.set_xticks(RHO_VALUES)
    ax.grid(True, alpha=0.3)

axes[0].set_ylabel("Standardized separation (D)")

handles, labels = axes[0].get_legend_handles_labels()
fig.legend(
    handles,
    labels,
    loc="upper center",
    ncol=3,
    frameon=False,
    bbox_to_anchor=(0.5, 1.06),
)

fig.tight_layout()

fig.savefig(PNG_PATH, dpi=300, bbox_inches="tight")
fig.savefig(PDF_PATH, bbox_inches="tight")
plt.close(fig)

print("Figure source rows:", len(plot_df))
print("Saved:", SOURCE_CSV_PATH)
print("Saved:", PNG_PATH)
print("Saved:", PDF_PATH)
