from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parents[1]
FIGURE_ROOT = ROOT / "output" / "figures"
SUBMISSION_DIR = FIGURE_ROOT / "submission"

# 제출 원고에서 실제 사용하는 피겨만 명시한다.
FIGURES = [
    (
        "Main Figure 1",
        FIGURE_ROOT / "legacy" / "Figure1_Pi_timeseries",
        "Figure1_Pi_timeseries",
    ),
    (
        "Main Figure 2",
        FIGURE_ROOT / "revised" / "Figure2_cross_domain_separation_revised",
        "Figure2_cross_domain_separation_revised",
    ),
    (
        "Main Figure 3",
        FIGURE_ROOT / "revised" / "Figure3_mult_vs_add_vs_max_revised",
        "Figure3_mult_vs_add_vs_max_revised",
    ),
    (
        "Main Figure 4",
        FIGURE_ROOT / "revised" / "Figure4_permutation_tests_revised",
        "Figure4_permutation_tests_revised",
    ),
    (
        "Main Figure 5",
        FIGURE_ROOT / "legacy" / "Figure5_failure_modes",
        "Figure5_failure_modes",
    ),
    (
        "Supplementary Figure S1",
        FIGURE_ROOT
        / "revised"
        / "Supplementary_Figure_S1_channel_ablation_revised",
        "Supplementary_Figure_S1_channel_ablation_revised",
    ),
    (
        "Supplementary Figure S2",
        FIGURE_ROOT
        / "legacy"
        / "Supplementary_Figure_S2_retrospective_trajectory",
        "Supplementary_Figure_S2_retrospective_trajectory",
    ),
]


def main() -> None:
    # 이전 조립 결과를 지워 오래된 파일이 남지 않게 한다.
    if SUBMISSION_DIR.exists():
        shutil.rmtree(SUBMISSION_DIR)

    SUBMISSION_DIR.mkdir(parents=True)

    manifest_lines = [
        "# Submission Figure Manifest",
        "",
        "This directory contains only the figures used in the revised submission.",
        "",
        "| Manuscript label | Submission file | Source set |",
        "|---|---|---|",
    ]

    copied = []

    for manuscript_label, source_stem, destination_stem in FIGURES:
        source_set = source_stem.parent.name

        for extension in (".png", ".pdf"):
            source = source_stem.with_suffix(extension)
            destination = SUBMISSION_DIR / f"{destination_stem}{extension}"

            if not source.is_file():
                raise FileNotFoundError(f"Required figure not found: {source}")

            shutil.copy2(source, destination)
            copied.append(destination)

        manifest_lines.append(
            f"| {manuscript_label} | `{destination_stem}.png/.pdf` "
            f"| `{source_set}` |"
        )

    manifest_lines.extend(
        [
            "",
            "## Excluded output",
            "",
            "- Figure 6 is withdrawn and is not included in this submission set.",
            "- Legacy Figures 2–4 are retained for audit purposes but are not included here.",
            "",
        ]
    )

    manifest = SUBMISSION_DIR / "SUBMISSION_MANIFEST.md"
    manifest.write_text("\n".join(manifest_lines), encoding="utf-8")

    print(f"Submission directory rebuilt: {SUBMISSION_DIR.relative_to(ROOT)}")
    for path in copied:
        print(f"  Copied: {path.relative_to(ROOT)}")
    print(f"  Created: {manifest.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
