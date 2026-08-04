from pathlib import Path

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "golden" / "output" / "table_nonoverlap_ablation.csv"
OUT_DIR = ROOT / "output" / "figures" / "revised"
OUT_DIR.mkdir(parents=True, exist_ok=True)

CASE_ORDER = [
    "2008 Financial",
    "Terra-Luna",
    "Fukushima",
    "COVID-19",
    "Supply Chain",
]

CASE_LABELS = {
    "2008 Financial": "2008\nFinancial",
    "Terra-Luna": "Terra–\nLuna",
    "Fukushima": "Fukushima",
    "COVID-19": "COVID-19",
    "Supply Chain": "Supply\nChain",
}

PANELS = [
    ("a", "Single-channel definitions", ["rho only", "psi only", "omega only"]),
    ("b", "Dual-channel definitions", ["rho x psi", "rho x omega", "psi x omega"]),
    ("c", "Triple-channel definitions", ["rho + psi + omega", "max(rho,psi,omega)", "rho x psi x omega"]),
]

METHOD_LABELS = {
    "rho only": "ρ only",
    "psi only": "Ψ only",
    "omega only": "Ω only",
    "rho x psi": "ρ × Ψ",
    "rho x omega": "ρ × Ω",
    "psi x omega": "Ψ × Ω",
    "rho + psi + omega": "ρ + Ψ + Ω",
    "max(rho,psi,omega)": "max(ρ,Ψ,Ω)",
    "rho x psi x omega": "ρ × Ψ × Ω",
}

COLORS = {
    "rho only": "#90CAF9",
    "psi only": "#64B5F6",
    "omega only": "#42A5F5",
    "rho x psi": "#FFCC80",
    "rho x omega": "#FFB74D",
    "psi x omega": "#FFA726",
    "rho + psi + omega": "#BDBDBD",
    "max(rho,psi,omega)": "#9E9E9E",
    "rho x psi x omega": "#D32F2F",
}

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 8,
    "axes.labelsize": 9,
    "axes.titlesize": 9,
    "xtick.labelsize": 7,
    "ytick.labelsize": 8,
    "legend.fontsize": 7,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
})

df = pd.read_csv(CSV_PATH)

required = {"Case", "Method", "Post_control_to_control_mean_ratio"}
missing = required - set(df.columns)
if missing:
    raise ValueError(f"Missing columns in {CSV_PATH.name}: {sorted(missing)}")

fig, axes = plt.subplots(3, 1, figsize=(7.08, 8.1), sharey=True)

x = np.arange(len(CASE_ORDER))
width = 0.22

for ax, (panel_letter, panel_title, methods) in zip(axes, PANELS):
    for j, method in enumerate(methods):
        vals = []
        for case in CASE_ORDER:
            subset = df[(df["Case"] == case) & (df["Method"] == method)]
            if len(subset) != 1:
                raise ValueError(f"Expected one row for case={case}, method={method}")
            vals.append(float(subset["Post_control_to_control_mean_ratio"].iloc[0]))

        offset = (j - 1) * width
        ax.bar(
            x + offset,
            vals,
            width=width,
            color=COLORS[method],
            edgecolor="white",
            linewidth=0.5,
            label=METHOD_LABELS[method],
            zorder=3,
        )

    ax.axhline(1, color="#666666", linestyle="--", linewidth=0.8, zorder=2)
    ax.set_yscale("log")
    ax.set_ylim(0.35, 20000)
    ax.set_xticks(x)
    ax.set_xticklabels([CASE_LABELS[c] for c in CASE_ORDER])
    ax.grid(axis="y", color="#D9D9D9", linewidth=0.7, alpha=0.75, zorder=0)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(direction="out")
    ax.set_ylabel("Mean-stress ratio\n(post-control / control)")
    ax.set_title(panel_title, loc="left", fontweight="bold", pad=6)
    ax.text(
        -0.08, 1.04, panel_letter,
        transform=ax.transAxes,
        fontsize=10,
        fontweight="bold",
        va="bottom",
    )
    ax.legend(frameon=False, loc="upper left", ncol=3)

fig.suptitle(
    "Channel ablation across nine stress definitions",
    fontsize=10,
    fontweight="bold",
    y=0.995,
)

fig.subplots_adjust(left=0.12, right=0.995, top=0.95, bottom=0.08, hspace=0.42)

png = OUT_DIR / "Figure_benchmark_revised.png"
pdf = OUT_DIR / "Figure_benchmark_revised.pdf"
fig.savefig(png, dpi=300, bbox_inches="tight", facecolor="white")
fig.savefig(pdf, bbox_inches="tight", facecolor="white")
plt.close(fig)

print(f"Created: {png.relative_to(ROOT)}")
print(f"Created: {pdf.relative_to(ROOT)}")
