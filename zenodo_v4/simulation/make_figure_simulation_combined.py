from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


# Publication-style serif typography
plt.rcParams["font.family"] = "serif"
plt.rcParams["font.serif"] = [
    "Times New Roman",
    "Times",
    "DejaVu Serif",
    "STIXGeneral",
]
plt.rcParams["mathtext.fontset"] = "stix"
plt.rcParams["axes.unicode_minus"] = False


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

SOURCE_CSV_PATH = (
    FIG_DIR
    / "figure_simulation_combined_delta1_source.csv"
)

PNG_PATH = (
    FIG_DIR
    / "Figure_simulation_combined_delta1.png"
)

PDF_PATH = (
    FIG_DIR
    / "Figure_simulation_combined_delta1.pdf"
)

DELTA = 1.0

K_VALUES = [1, 2, 3]
RHO_VALUES = [0.0, 0.3, 0.6, 0.9]

OPERATORS = [
    "product",
    "sum",
    "maximum",
]

NORMALIZATIONS = [
    "p99",
    "empirical_percentile",
]


df = pd.read_csv(SUMMARY_PATH)

plot_df = df[
    (df["delta"] == DELTA)
    & (df["normalization"].isin(NORMALIZATIONS))
].copy()

expected_rows = (
    2
    * len(K_VALUES)
    * len(RHO_VALUES)
    * len(OPERATORS)
)

if len(plot_df) != expected_rows:
    raise RuntimeError(
        f"Unexpected plotting rows: "
        f"{len(plot_df)} != {expected_rows}"
    )

plot_df["rho"] = plot_df["rho"].astype(float)
plot_df["k"] = plot_df["k"].astype(int)
plot_df["D"] = plot_df["D"].astype(float)

plot_df = plot_df.sort_values(
    [
        "normalization",
        "k",
        "operator",
        "rho",
    ]
).reset_index(drop=True)

FIG_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

plot_df.to_csv(
    SOURCE_CSV_PATH,
    index=False,
)


fig, axes = plt.subplots(
    2,
    3,
    figsize=(12, 7.5),
    sharex=True,
    sharey=True,
)


for row_index, normalization in enumerate(NORMALIZATIONS):

    row_df = plot_df[
        plot_df["normalization"] == normalization
    ]

    for col_index, k in enumerate(K_VALUES):

        ax = axes[row_index, col_index]

        panel = row_df[
            row_df["k"] == k
        ]

        for operator in OPERATORS:

            sub = panel[
                panel["operator"] == operator
            ].sort_values("rho")

            if list(sub["rho"]) != RHO_VALUES:
                raise RuntimeError(
                    f"Unexpected rho grid: "
                    f"{normalization}, "
                    f"k={k}, "
                    f"{operator}"
                )

            ax.plot(
                sub["rho"],
                sub["D"],
                marker="o",
                linewidth=1.8,
                label=operator,
            )

        # k title for every subplot
        ax.set_title(
            f"k = {k}",
            fontsize=12,
            pad=8,
        )

        ax.set_xticks(RHO_VALUES)

        # Show rho tick labels on both rows
        ax.tick_params(
            axis="x",
            labelbottom=True,
        )

        ax.grid(
            True,
            alpha=0.3,
        )

        # No repeated subplot-level x labels
        ax.set_xlabel("")


# Y labels only on the left side
axes[0, 0].set_ylabel(
    "Standardized separation (D)",
    fontsize=11,
)

axes[1, 0].set_ylabel(
    "Standardized separation (D)",
    fontsize=11,
)


# Final panel layout
fig.subplots_adjust(
    top=0.84,
    bottom=0.10,
    left=0.08,
    right=0.98,
    hspace=0.62,
    wspace=0.08,
)

# Increase only the gap between rows:
# move the entire second row downward while preserving
# the title-to-panel spacing within each row.
ROW_SHIFT = 0.03

for ax in axes[1, :]:
    pos = ax.get_position()
    ax.set_position([
        pos.x0,
        pos.y0 - ROW_SHIFT,
        pos.width,
        pos.height,
    ])

# Use the exact horizontal center of the middle column
middle_pos = axes[0, 1].get_position()
middle_x = (middle_pos.x0 + middle_pos.x1) / 2.0


# Shared legend centered over the middle panel
handles, labels = axes[0, 0].get_legend_handles_labels()

fig.legend(
    handles,
    ["Product", "Sum", "Maximum"],
    loc="upper center",
    ncol=3,
    frameon=False,
    bbox_to_anchor=(middle_x, 0.99),
    bbox_transform=fig.transFigure,
)


# Row headings centered on the middle panel
fig.text(
    middle_x,
    0.905,
    "(a) Primary normalization (P99)",
    ha="center",
    va="center",
    fontsize=13,
    fontweight="bold",
)

fig.text(
    middle_x,
    0.425,
    "(b) Empirical-percentile normalization",
    ha="center",
    va="center",
    fontsize=13,
    fontweight="bold",
)


# Shared x-axis label for each row,
# also centered on the middle panel
fig.text(
    middle_x,
    0.505,
    "Cross-channel dependence (ρ)",
    ha="center",
    va="center",
    fontsize=11,
)

fig.text(
    middle_x,
    0.020,
    "Cross-channel dependence (ρ)",
    ha="center",
    va="center",
    fontsize=11,
)


fig.savefig(
    PNG_PATH,
    dpi=300,
    bbox_inches="tight",
)

fig.savefig(
    PDF_PATH,
    bbox_inches="tight",
)

plt.close(fig)


print("Figure source rows:", len(plot_df))
print("Saved:", SOURCE_CSV_PATH)
print("Saved:", PNG_PATH)
print("Saved:", PDF_PATH)
