from pathlib import Path

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "manuscript_figures"
OUT.mkdir(exist_ok=True)

DPI = 300

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times New Roman", "Times", "DejaVu Serif"],
    "mathtext.fontset": "dejavuserif",
    "font.size": 8,
    "axes.labelsize": 8,
    "axes.titlesize": 9,
    "xtick.labelsize": 7.2,
    "ytick.labelsize": 7.2,
    "legend.fontsize": 7,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
})


def save(fig, name):
    png = OUT / f"{name}.png"
    pdf = OUT / f"{name}.pdf"
    fig.savefig(png, dpi=DPI, bbox_inches="tight", facecolor="white")
    fig.savefig(pdf, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"Created: {png}")
    print(f"Created: {pdf}")


def box(
    ax,
    x,
    y,
    w,
    h,
    title,
    body,
    face="#FAFAFA",
    edge="#707070",
    title_size=7.0,
    body_size=5.9,
):
    patch = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle="round,pad=0.006,rounding_size=0.006",
        linewidth=0.9,
        edgecolor=edge,
        facecolor=face,
    )
    ax.add_patch(patch)
    ax.text(
        x + w / 2,
        y + h * 0.69,
        title,
        ha="center",
        va="center",
        fontsize=title_size,
        fontweight="bold",
        linespacing=1.0,
        wrap=True,
    )
    ax.text(
        x + w / 2,
        y + h * 0.30,
        body,
        ha="center",
        va="center",
        fontsize=body_size,
        linespacing=1.10,
        wrap=True,
    )


def arrow(ax, x1, y1, x2, y2):
    ax.add_patch(
        FancyArrowPatch(
            (x1, y1),
            (x2, y2),
            arrowstyle="-|>",
            mutation_scale=9,
            linewidth=0.9,
            color="#666666",
            shrinkA=1,
            shrinkB=1,
        )
    )


def figure1():
    fig, ax = plt.subplots(figsize=(7.08, 4.15))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    ax.text(
        0.50,
        0.95,
        "Concurrent-stress construction and evidence design",
        ha="center",
        va="center",
        fontsize=9.0,
        fontweight="bold",
    )
    ax.text(
        0.50,
        0.865,
        "Deterministic computational pipeline",
        ha="center",
        va="center",
        fontsize=8.1,
        fontweight="bold",
        color="#444444",
    )

    y = 0.60
    h = 0.18
    xs = [0.025, 0.225, 0.425, 0.625, 0.825]
    w = 0.15

    box(ax, xs[0], y, w, h, "Observations", "Domain-specific\nraw indicators",
        title_size=7.0, body_size=5.9)
    box(ax, xs[1], y, w, h, "Channels",
        "Three non-negative\nstress channels\n$x_{1,t}, x_{2,t}, x_{3,t}$",
        title_size=7.0, body_size=5.7)
    box(ax, xs[2], y, w, h, "Normalization",
        "Fixed control-period\nP99 references\n$z_{j,t}=x_{j,t}/c_j$",
        title_size=6.8, body_size=5.7)
    box(ax, xs[3], y, w, h, "Operators", "Product\nSum\nMaximum",
        title_size=7.0, body_size=5.9)
    box(ax, xs[4], y, w, h, "Contrast", "Mean post /\nmean control",
        title_size=7.0, body_size=5.9)

    for i in range(4):
        arrow(ax, xs[i] + w + 0.004, y + h / 2,
              xs[i + 1] - 0.004, y + h / 2)

    ax.text(
        0.50,
        0.445,
        "Complementary evaluation evidence",
        ha="center",
        va="center",
        fontsize=8.1,
        fontweight="bold",
        color="#444444",
    )

    ev_y = 0.17
    ev_h = 0.19
    ev_w = 0.205
    ev_x = [0.030, 0.275, 0.520, 0.765]

    box(ax, ev_x[0], ev_y, ev_w, ev_h, "Development",
        "5 retrospective\ncross-domain cases",
        face="#F7F7F7", edge="#707070", title_size=7.0, body_size=5.9)
    box(ax, ev_x[1], ev_y, ev_w, ev_h, "Frozen\ntransfer",
        "LTCM 1998\nhistorical holdout",
        face="#F3F7FB", edge="#557FA8", title_size=6.8, body_size=5.8)
    box(ax, ev_x[2], ev_y, ev_w, ev_h, "Output-blind\ntransfer",
        "Holdout 2\nfixed-seed event selection",
        face="#F3F7FB", edge="#557FA8", title_size=6.6, body_size=5.7)
    box(ax, ev_x[3], ev_y, ev_w, ev_h, "Controlled\nsimulation",
        "Activation breadth ×\ndependence × intensity",
        face="#F7F7F7", edge="#707070", title_size=6.6, body_size=5.6)

    arrow(ax, 0.70, 0.585, 0.70, 0.505)

    ax.text(
        0.50,
        0.055,
        "The same fixed operators are evaluated across empirical transfers "
        "and a controlled data-generating process.",
        ha="center",
        va="center",
        fontsize=6.4,
        color="#555555",
    )

    save(fig, "Figure1_framework_evidence")


def figure2():
    path = (
        ROOT / "archive" / "zenodo_v3" / "golden" / "output"
        / "table_nonoverlap_primary.csv"
    )
    df = pd.read_csv(path)

    order = [
        "2008 Financial",
        "Terra-Luna",
        "Fukushima",
        "COVID-19",
        "Supply Chain",
    ]
    labels = {
        "2008 Financial": "2008\nFinancial",
        "Terra-Luna": "Terra–Luna",
        "Fukushima": "Fukushima",
        "COVID-19": "COVID-19",
        "Supply Chain": "Supply\nChain",
    }

    df = df.set_index("Case").loc[order].reset_index()
    values = df["Post_control_to_control_mean_ratio"].to_numpy()
    x = np.arange(len(order))

    fig, ax = plt.subplots(figsize=(7.08, 3.55))
    bars = ax.bar(
        x,
        values,
        width=0.58,
        color="#A7A7A7",
        edgecolor="#555555",
        linewidth=0.7,
        zorder=3,
    )

    ax.axhline(1.0, color="#555555", linestyle="--", linewidth=0.9, zorder=2)
    ax.set_yscale("log")
    ax.set_ylim(0.8, 20000)

    for bar, value in zip(bars, values):
        text = f"{value:,.0f}×" if value >= 1000 else f"{value:.2f}×"
        ax.annotate(
            text,
            xy=(bar.get_x() + bar.get_width() / 2, value),
            xytext=(0, 5),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=7.2,
            fontweight="bold",
        )

    ax.set_xticks(x)
    ax.set_xticklabels([labels[c] for c in order])
    ax.set_ylabel("Post-control / control\nmean-stress ratio")
    ax.set_title(
        "Development cases: multiplicative stress separation",
        fontweight="bold",
        pad=9,
    )
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", which="major", linewidth=0.6, alpha=0.35, zorder=0)
    ax.tick_params(direction="out", length=3)
    ax.margins(x=0.07)
    fig.subplots_adjust(left=0.13, right=0.98, bottom=0.20, top=0.87)

    save(fig, "Figure2_development_cases")


def figure3():
    path = (
        ROOT / "archive" / "zenodo_v3" / "golden" / "ltcm_holdout"
        / "table_ltcm_formulations.csv"
    )
    df = pd.read_csv(path)

    order = ["Multiplicative", "Additive", "Maximum"]
    df = df.set_index("Definition").loc[order].reset_index()
    values = df["Post_control_to_control_mean_ratio"].to_numpy()
    labels = ["Product", "Sum", "Maximum"]
    y = np.array([0.78, 0.50, 0.22])

    fig, ax = plt.subplots(figsize=(6.2, 2.25))
    ax.axvline(1.0, color="#555555", linestyle="--", linewidth=0.9, zorder=1)

    colors = ["#557FA8", "#A7A7A7", "#8F8F8F"]

    for yi, value, color in zip(y, values, colors):
        ax.hlines(yi, 1.0, value, color=color, linewidth=1.8, zorder=2)
        ax.scatter(
            value,
            yi,
            s=58,
            color=color,
            edgecolor="#444444",
            linewidth=0.7,
            zorder=3,
        )
        ax.annotate(
            f"{value:.3f}×",
            xy=(value, yi),
            xytext=(8, 0),
            textcoords="offset points",
            ha="left",
            va="center",
            fontsize=7.5,
            fontweight="bold",
        )

    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.set_ylim(0.10, 0.90)
    ax.set_xlim(0.99, 1.195)
    ax.set_xlabel("Post-control / control mean-stress ratio")
    ax.set_title(
        "LTCM 1998 frozen historical holdout",
        fontweight="bold",
        pad=10,
    )
    ax.text(
        0.50,
        1.015,
        "Control: 576 observations   |   Post-control: 642 observations",
        transform=ax.transAxes,
        ha="center",
        va="bottom",
        fontsize=6.5,
        color="#555555",
    )
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(False)
    ax.grid(axis="x", linewidth=0.6, alpha=0.30, zorder=0)
    ax.tick_params(axis="y", length=0)
    ax.tick_params(axis="x", direction="out", length=3)
    fig.subplots_adjust(left=0.20, right=0.93, bottom=0.24, top=0.78)

    save(fig, "Figure3_ltcm_holdout")


def figure4():
    import json
    import matplotlib.dates as mdates

    series_path = (
        ROOT / "zenodo_v4" / "holdout2" / "results"
        / "holdout2_aligned_series.csv"
    )
    summary_path = (
        ROOT / "zenodo_v4" / "holdout2" / "results"
        / "holdout2_summary.json"
    )

    df = pd.read_csv(series_path)
    df["date"] = pd.to_datetime(df["date"])

    with summary_path.open(encoding="utf-8") as f:
        summary = json.load(f)

    assert len(df) == 500
    assert df["period"].value_counts().to_dict() == {
        "control": 250,
        "post": 250,
    }

    event_date = pd.Timestamp(summary["selected_event"]["reference_date_jst"])
    magnitude = summary["selected_event"]["magnitude"]

    ratios = np.array([
        summary["operators"]["product"]["post_control_ratio"],
        summary["operators"]["sum"]["post_control_ratio"],
        summary["operators"]["maximum"]["post_control_ratio"],
    ])
    operator_labels = ["Product", "Sum", "Maximum"]
    product_control_mean = summary["operators"]["product"]["mean_control"]
    product_post_mean = summary["operators"]["product"]["mean_post"]

    fig, axes = plt.subplots(
        1,
        2,
        figsize=(7.08, 3.35),
        gridspec_kw={"width_ratios": [1.65, 1.0], "wspace": 0.35},
    )
    ax1, ax2 = axes

    control = df[df["period"] == "control"]
    post = df[df["period"] == "post"]

    ax1.plot(
        control["date"], control["product"],
        color="#8F8F8F", linewidth=0.75, zorder=2,
    )
    ax1.plot(
        post["date"], post["product"],
        color="#557FA8", linewidth=0.75, zorder=2,
    )
    ax1.axvline(
        event_date, color="#444444", linestyle="--", linewidth=0.9, zorder=3,
    )

    ax1.hlines(
        product_control_mean,
        control["date"].min(),
        control["date"].max(),
        color="#666666",
        linewidth=1.3,
        linestyle="-",
        zorder=4,
    )
    ax1.hlines(
        product_post_mean,
        post["date"].min(),
        post["date"].max(),
        color="#315F8A",
        linewidth=1.3,
        linestyle="-",
        zorder=4,
    )

    ax1.text(
        0.02, 0.96, "Control",
        transform=ax1.transAxes, ha="left", va="top",
        fontsize=6.7, color="#666666",
    )
    ax1.text(
        0.98, 0.96, "Post",
        transform=ax1.transAxes, ha="right", va="top",
        fontsize=6.7, color="#315F8A",
    )
    ax1.annotate(
        f"M{magnitude:.1f}\n26 Sep 2003",
        xy=(event_date, 0.82),
        xycoords=("data", "axes fraction"),
        xytext=(10, 0),
        textcoords="offset points",
        ha="left",
        va="center",
        fontsize=6.4,
        color="#444444",
    )

    ax1.set_ylabel("Product stress")
    ax1.set_title(
        "A. Daily product stress",
        loc="left",
        fontweight="bold",
        fontsize=8.2,
        pad=7,
    )
    ax1.xaxis.set_major_locator(mdates.MonthLocator(interval=6))
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%b\n%Y"))
    ax1.set_xlim(df["date"].min(), df["date"].max())
    ax1.margins(x=0)
    ax1.set_ylim(0, max(1.08, df["product"].max() * 1.05))
    ax1.spines["top"].set_visible(False)
    ax1.spines["right"].set_visible(False)
    ax1.grid(axis="y", linewidth=0.55, alpha=0.28, zorder=0)
    ax1.tick_params(direction="out", length=3)

    y = np.array([0.75, 0.50, 0.25])
    colors = ["#557FA8", "#A7A7A7", "#8F8F8F"]
    ax2.axvline(1.0, color="#555555", linestyle="--", linewidth=0.9, zorder=1)

    for yi, value, color in zip(y, ratios, colors):
        ax2.hlines(yi, 1.0, value, color=color, linewidth=1.8, zorder=2)
        ax2.scatter(
            value, yi, s=52, color=color,
            edgecolor="#444444", linewidth=0.7, zorder=3,
        )
        ax2.annotate(
            f"{value:.3f}×",
            xy=(value, yi),
            xytext=(6, 0),
            textcoords="offset points",
            ha="left",
            va="center",
            fontsize=6.8,
            fontweight="bold",
        )

    ax2.set_yticks(y)
    ax2.set_yticklabels(operator_labels)
    ax2.set_ylim(0.10, 0.90)
    ax2.set_xlim(0.99, 1.285)
    ax2.set_xlabel("Post / control mean ratio")
    ax2.set_title(
        "B. Operator comparison",
        loc="left",
        fontweight="bold",
        fontsize=8.2,
        pad=7,
    )
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_visible(False)
    ax2.spines["left"].set_visible(False)
    ax2.grid(axis="x", linewidth=0.55, alpha=0.28, zorder=0)
    ax2.tick_params(axis="y", length=0)
    ax2.tick_params(axis="x", direction="out", length=3)

    fig.suptitle(
        "Holdout 2: output-blind historical transfer",
        fontsize=9.2,
        fontweight="bold",
        y=0.98,
    )
    fig.text(
        0.50,
        0.015,
        "250 control observations   |   250 post observations   |   "
        "fixed-seed selection with no redraw",
        ha="center",
        va="bottom",
        fontsize=6.3,
        color="#555555",
    )
    fig.subplots_adjust(left=0.10, right=0.97, bottom=0.22, top=0.82)

    save(fig, "Figure4_holdout2")


if __name__ == "__main__":
    figure1()
    figure2()
    figure3()
    figure4()
