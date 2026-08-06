from pathlib import Path

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
INPUT_DIR = ROOT / "golden" / "output"
OUTPUT_DIR = ROOT / "output" / "figures" / "revised"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

CASE_ORDER = [
    "2008 Financial",
    "Terra-Luna",
    "Fukushima",
    "COVID-19",
    "Supply Chain",
]

CASE_LABELS = {
    "2008 Financial": "2008\nFinancial\nCrisis",
    "Terra-Luna": "Terra–Luna\nCollapse",
    "Fukushima": "Fukushima\nDisaster",
    "COVID-19": "COVID-19\nPandemic",
    "Supply Chain": "Supply Chain\nDisruption",
}

PANEL_TITLES = {
    "2008 Financial": "2008 Financial",
    "Terra-Luna": "Terra–Luna",
    "Fukushima": "Fukushima",
    "COVID-19": "COVID-19",
    "Supply Chain": "Supply Chain",
}

RED = "#D62F2F"
ORANGE = "#FF9800"
GREY = "#9E9E9E"
BLUE = "#3775B5"
DPI = 300

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 8,
    "axes.labelsize": 9,
    "axes.titlesize": 9,
    "xtick.labelsize": 7.5,
    "ytick.labelsize": 8,
    "legend.fontsize": 7.5,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
})


def require_columns(df, required, filename):
    missing = [column for column in required if column not in df.columns]
    if missing:
        raise ValueError(f"{filename}: missing columns {missing}")


def save_figure(fig, filename):
    png = OUTPUT_DIR / f"{filename}.png"
    pdf = OUTPUT_DIR / f"{filename}.pdf"

    fig.savefig(png, dpi=DPI, bbox_inches="tight", facecolor="white")
    fig.savefig(pdf, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    print(f"Created: {png.relative_to(ROOT)}")
    print(f"Created: {pdf.relative_to(ROOT)}")


def style_axis(ax):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", color="#D9D9D9", linewidth=0.7, alpha=0.75, zorder=0)
    ax.tick_params(direction="out")


def figure_2():
    filename = "table_nonoverlap_primary.csv"
    df = pd.read_csv(INPUT_DIR / filename)

    require_columns(
        df,
        ["Case", "Post_control_to_control_mean_ratio"],
        filename,
    )

    df = df.set_index("Case").loc[CASE_ORDER].reset_index()
    values = df["Post_control_to_control_mean_ratio"].to_numpy()
    x = np.arange(len(CASE_ORDER))

    fig, ax = plt.subplots(figsize=(7.08, 3.35))

    bars = ax.bar(
        x,
        values,
        width=0.58,
        color=RED,
        edgecolor="white",
        linewidth=0.7,
        zorder=3,
    )

    for bar, value in zip(bars, values):
        label = f"{value:,.0f}×" if value >= 100 else f"{value:.2f}×"
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            value * 1.13,
            label,
            ha="center",
            va="bottom",
            fontsize=8,
            fontweight="bold",
        )

    ax.axhline(1, color="#666666", linestyle="--", linewidth=0.8, zorder=2)
    ax.set_yscale("log")
    ax.set_ylim(0.9, 20000)
    ax.set_xticks(x)
    ax.set_xticklabels([CASE_LABELS[case] for case in CASE_ORDER])
    ax.set_ylabel("Mean-stress ratio\n(post-control / control)")
    ax.margins(x=0.04)
    style_axis(ax)

    fig.subplots_adjust(left=0.12, right=0.99, bottom=0.25, top=0.97)
    save_figure(fig, "Figure2_cross_domain_separation_revised")


def figure_3():
    filename = "table_nonoverlap_formulations.csv"
    df = pd.read_csv(INPUT_DIR / filename)

    require_columns(
        df,
        ["Case", "Formulation", "Post_control_to_control_mean_ratio"],
        filename,
    )

    pivot = df.pivot(
        index="Case",
        columns="Formulation",
        values="Post_control_to_control_mean_ratio",
    ).loc[CASE_ORDER]

    x = np.arange(len(CASE_ORDER))
    width = 0.24

    fig, ax = plt.subplots(figsize=(7.08, 3.35))

    bars_mult = ax.bar(
        x - width,
        pivot["Multiplicative"],
        width,
        label="Multiplicative (ρ×Ψ×Ω)",
        color=RED,
        edgecolor="white",
        linewidth=0.6,
        zorder=3,
    )
    bars_add = ax.bar(
        x,
        pivot["Additive"],
        width,
        label="Additive (ρ+Ψ+Ω)",
        color=ORANGE,
        edgecolor="white",
        linewidth=0.6,
        zorder=3,
    )
    bars_max = ax.bar(
        x + width,
        pivot["Maximum"],
        width,
        label="Maximum",
        color=GREY,
        edgecolor="white",
        linewidth=0.6,
        zorder=3,
    )

    # Numeric labels preserve distinctions that are visually compressed
    # near the reference value of 1 on the logarithmic axis.
    for bars in (bars_mult, bars_add, bars_max):
        for bar in bars:
            value = float(bar.get_height())
            x_pos = bar.get_x() + bar.get_width() / 2
            label = f"{value:,.0f}" if value >= 100 else f"{value:.2f}"

            ax.annotate(
                label,
                xy=(x_pos, value),
                xytext=(0, 3),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=6.2,
                clip_on=False,
                zorder=5,
            )

    ax.axhline(1, color="#666666", linestyle="--", linewidth=0.8, zorder=2)
    ax.set_yscale("log")
    ax.set_ylim(0.7, 20000)
    ax.set_xticks(x)
    ax.set_xticklabels([CASE_LABELS[case] for case in CASE_ORDER])
    ax.set_ylabel("Mean-stress ratio\n(post-control / control)")
    ax.legend(frameon=False, loc="upper left")
    ax.margins(x=0.03)
    style_axis(ax)

    fig.subplots_adjust(left=0.12, right=0.99, bottom=0.25, top=0.97)
    save_figure(fig, "Figure3_mult_vs_add_vs_max_revised")


def figure_4():
    filename = "table_nonoverlap_permutation.csv"
    df = pd.read_csv(INPUT_DIR / filename)

    require_columns(
        df,
        [
            "Case",
            "Method",
            "Block_size_observations",
            "p_value_plus_one",
        ],
        filename,
    )

    fig, axes = plt.subplots(
        2,
        3,
        figsize=(7.08, 4.8),
        sharey=True,
    )
    axes = axes.ravel()

    short_titles = {
        "2008 Financial": "2008 Financial",
        "Terra-Luna": "Terra–Luna",
        "Fukushima": "Fukushima",
        "COVID-19": "COVID-19",
        "Supply Chain": "Supply Chain",
    }

    for index, case in enumerate(CASE_ORDER):
        ax = axes[index]
        case_df = df[df["Case"] == case].copy()

        independent = case_df[
            case_df["Method"].str.contains(
                "Independent", case=False, na=False
            )
        ]
        blocks = case_df[
            case_df["Method"].str.contains(
                "Block", case=False, na=False
            )
        ].sort_values("Block_size_observations")

        if len(independent) != 1:
            raise ValueError(
                f"{case}: expected one independent-shuffle row"
            )

        independent_p = independent.iloc[0]["p_value_plus_one"]

        x_positions = [0]
        x_labels = ["Ind."]

        ax.scatter(
            [0],
            [independent_p],
            color=RED,
            marker="o",
            s=34,
            zorder=4,
        )

        independent_label = (
            f"{independent_p:.4f}"
            if independent_p < 0.001
            else f"{independent_p:.3f}"
        )
        independent_offset = 11 if 0.03 <= independent_p <= 0.08 else 6

        ax.annotate(
            independent_label,
            xy=(0, independent_p),
            xytext=(0, independent_offset),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=5.8,
            color=RED,
            zorder=6,
            bbox=dict(
                facecolor="white",
                edgecolor="none",
                alpha=0.90,
                pad=0.15,
            ),
        )

        if not blocks.empty:
            block_x = np.arange(1, len(blocks) + 1)
            block_p = blocks["p_value_plus_one"].to_numpy()

            ax.plot(
                block_x,
                block_p,
                color=BLUE,
                linewidth=1.1,
                zorder=3,
            )
            ax.scatter(
                block_x,
                block_p,
                color=BLUE,
                marker="^",
                s=34,
                zorder=4,
            )

            for x_pos, p_value in zip(block_x, block_p):
                block_label = (
                    f"{p_value:.4f}"
                    if p_value < 0.001
                    else f"{p_value:.3f}"
                )
                block_offset = 11 if 0.03 <= p_value <= 0.08 else 6

                ax.annotate(
                    block_label,
                    xy=(x_pos, p_value),
                    xytext=(0, block_offset),
                    textcoords="offset points",
                    ha="center",
                    va="bottom",
                    fontsize=5.8,
                    color=BLUE,
                    zorder=6,
                    bbox=dict(
                        facecolor="white",
                        edgecolor="none",
                        alpha=0.90,
                        pad=0.15,
                    ),
                )

            x_positions.extend(block_x.tolist())
            x_labels.extend(
                [
                    str(int(value))
                    for value in blocks["Block_size_observations"]
                ]
            )

        ax.axhline(
            0.05,
            color="#666666",
            linestyle="--",
            linewidth=0.8,
            zorder=2,
        )
        ax.set_yscale("log")
        ax.set_ylim(8e-5, 1)
        ax.set_xticks(x_positions)
        ax.set_xticklabels(x_labels)
        ax.set_title(
            short_titles[case],
            fontsize=9,
            fontweight="bold",
            pad=5,
        )
        ax.text(
            -0.10,
            1.03,
            chr(97 + index),
            transform=ax.transAxes,
            fontsize=9,
            fontweight="bold",
            ha="left",
            va="bottom",
            clip_on=False,
        )
        ax.grid(
            axis="y",
            color="#D9D9D9",
            linewidth=0.6,
            alpha=0.75,
            zorder=0,
        )
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.tick_params(direction="out")

        if index in (0, 3):
            ax.set_ylabel("Plus-one empirical p-value")

    legend_ax = axes[5]
    legend_ax.axis("off")
    legend_ax.scatter([], [], color=RED, marker="o", s=34,
                      label="Independent shuffle")
    legend_ax.scatter([], [], color=BLUE, marker="^", s=34,
                      label="Block shuffle")
    legend_ax.plot([], [], color="#666666", linestyle="--",
                   linewidth=0.8, label="p = 0.05")
    legend_ax.legend(
        frameon=False,
        loc="center left",
        fontsize=8,
    )
    legend_ax.text(
        0.0,
        0.28,
        "Numbers on the x-axis denote\nblock size in aligned observations.",
        transform=legend_ax.transAxes,
        fontsize=7,
        va="top",
    )

    fig.subplots_adjust(
        left=0.10,
        right=0.99,
        bottom=0.10,
        top=0.95,
        wspace=0.28,
        hspace=0.38,
    )
    save_figure(fig, "Figure4_permutation_tests_revised")


def main():
    figure_2()
    figure_3()
    figure_4()
    print("All revised publication figures created successfully.")


if __name__ == "__main__":
    main()
