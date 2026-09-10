from pathlib import Path

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "figures" / "revised"
OUT.mkdir(parents=True, exist_ok=True)

DPI = 300

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 8,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
})


def add_box(
    ax, x, y, w, h, title, body,
    face="#FAFAFA",
    edge="#707070",
    title_size=7.8,
    body_size=6.7,
):
    patch = FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.006,rounding_size=0.005",
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
    )

    ax.text(
        x + w / 2,
        y + h * 0.34,
        body,
        ha="center",
        va="center",
        fontsize=body_size,
        linespacing=1.18,
    )


def add_arrow(ax, x1, y1, x2, y2):
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


def add_line(ax, x1, y1, x2, y2):
    ax.plot(
        [x1, x2],
        [y1, y2],
        color="#666666",
        linewidth=0.9,
        solid_capstyle="butt",
    )


def main():
    fig, ax = plt.subplots(figsize=(7.08, 3.65))

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    # ---------------------------------------------------------
    # Section headings
    # ---------------------------------------------------------
    ax.text(
        0.12, 0.91,
        "Evidence design",
        ha="center",
        va="center",
        fontsize=8.5,
        fontweight="bold",
        color="#444444",
    )

    ax.text(
        0.635, 0.91,
        "Shared deterministic computational pipeline",
        ha="center",
        va="center",
        fontsize=8.5,
        fontweight="bold",
        color="#444444",
    )

    # ---------------------------------------------------------
    # Evidence-design boxes
    # ---------------------------------------------------------
    evidence_x = 0.035
    evidence_w = 0.17
    evidence_h = 0.18

    dev_y = 0.62
    hold_y = 0.29

    add_box(
        ax,
        evidence_x, dev_y,
        evidence_w, evidence_h,
        "Development set",
        "5 retrospective cases",
        face="#F7F7F7",
        edge="#707070",
        title_size=7.8,
        body_size=6.7,
    )

    add_box(
        ax,
        evidence_x, hold_y,
        evidence_w, evidence_h,
        "Historical holdout",
        "LTCM 1998\nfrozen before output",
        face="#F3F7FB",
        edge="#557FA8",
        title_size=7.8,
        body_size=6.7,
    )

    # ---------------------------------------------------------
    # Main pipeline boxes
    # ---------------------------------------------------------
    box_y = 0.46
    box_h = 0.22
    box_w = 0.145

    x1 = 0.300
    x2 = 0.475
    x3 = 0.650
    x4 = 0.825

    add_box(
        ax,
        x1, box_y, box_w, box_h,
        "1. Channels",
        "Three case-specific\ninputs\n$x_1,\\;x_2,\\;x_3$",
    )

    add_box(
        ax,
        x2, box_y, box_w, box_h,
        "2. Calibration",
        "Channel-wise P99\nreference values",
    )

    add_box(
        ax,
        x3, box_y, box_w, box_h,
        "3. Stress score",
        "$z_{j,t}=x_{j,t}/c_j$\n"
        "$S_t=z_{1,t}z_{2,t}z_{3,t}$",
        body_size=6.6,
    )

    add_box(
        ax,
        x4, box_y, box_w, box_h,
        "4. Evaluation",
        "$R_{PC/C}$\n"
        "product • sum • max\n"
        "ablation • permutation",
        body_size=6.3,
    )

    # ---------------------------------------------------------
    # Orthogonal merge from evidence design
    #
    # Development ──┐
    #                ├──> Channels
    # Holdout ───────┘
    # ---------------------------------------------------------
    junction_x = 0.245
    EDGE_GAP = 0.010

    dev_mid = dev_y + evidence_h / 2
    hold_mid = hold_y + evidence_h / 2
    pipeline_mid = box_y + box_h / 2

    add_line(
        ax,
        evidence_x + evidence_w + EDGE_GAP,
        dev_mid,
        junction_x,
        dev_mid,
    )

    add_line(
        ax,
        evidence_x + evidence_w + EDGE_GAP,
        hold_mid,
        junction_x,
        hold_mid,
    )

    add_line(
        ax,
        junction_x,
        hold_mid,
        junction_x,
        dev_mid,
    )

    add_arrow(
        ax,
        junction_x,
        pipeline_mid,
        x1 - EDGE_GAP,
        pipeline_mid,
    )

    # ---------------------------------------------------------
    # Straight pipeline arrows
    # ---------------------------------------------------------
    add_arrow(
        ax,
        x1 + box_w + EDGE_GAP,
        pipeline_mid,
        x2 - EDGE_GAP,
        pipeline_mid,
    )

    add_arrow(
        ax,
        x2 + box_w + EDGE_GAP,
        pipeline_mid,
        x3 - EDGE_GAP,
        pipeline_mid,
    )

    add_arrow(
        ax,
        x3 + box_w + EDGE_GAP,
        pipeline_mid,
        x4 - EDGE_GAP,
        pipeline_mid,
    )

    # ---------------------------------------------------------
    # Reproducibility layer
    # ---------------------------------------------------------
    provenance_x = x1
    provenance_y = 0.12
    provenance_w = x4 + box_w - x1
    provenance_h = 0.145

    add_box(
        ax,
        provenance_x,
        provenance_y,
        provenance_w,
        provenance_h,
        "Reproducibility and provenance",
        "Frozen inputs • deterministic outputs • golden baselines\n"
        "SHA-256 verification • Git history",
        face="#F6F6F6",
        edge="#777777",
        title_size=7.6,
        body_size=6.25,
    )

    # Evaluation -> provenance, perfectly vertical
    eval_center = x4 + box_w / 2

    add_arrow(
        ax,
        eval_center,
        box_y - EDGE_GAP,
        eval_center,
        provenance_y + provenance_h + EDGE_GAP,
    )

    # ---------------------------------------------------------
    # Layout
    # ---------------------------------------------------------
    fig.subplots_adjust(
        left=0.02,
        right=0.99,
        bottom=0.05,
        top=0.97,
    )

    png = OUT / "Figure1_workflow_revised.png"
    pdf = OUT / "Figure1_workflow_revised.pdf"

    fig.savefig(
        png,
        dpi=DPI,
        bbox_inches="tight",
        facecolor="white",
    )

    fig.savefig(
        pdf,
        bbox_inches="tight",
        facecolor="white",
    )

    plt.close(fig)

    print(f"Created: {png.relative_to(ROOT)}")
    print(f"Created: {pdf.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
