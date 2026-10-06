#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "Generating manuscript Figures 1-4..."
python3 manuscript_figures/make_manuscript_figures.py

echo "Generating manuscript Figure 5..."
python3 manuscript_figures/make_figure5_manuscript.py

FINAL="manuscript_figures/final_figure_set"
rm -rf "$FINAL"
mkdir -p "$FINAL"

for stem in \
  Figure1_framework_evidence \
  Figure2_development_cases \
  Figure3_ltcm_holdout \
  Figure4_holdout2 \
  Figure5_simulation
do
  cp "manuscript_figures/${stem}.png" "$FINAL/${stem}.png"
  cp "manuscript_figures/${stem}.pdf" "$FINAL/${stem}.pdf"
done

cat > "$FINAL/README.txt" <<'EOF'
Final manuscript figure set

Figure 1 — Concurrent-stress construction and evidence design
Figure 2 — Development cases: multiplicative stress separation
Figure 3 — LTCM 1998 frozen historical holdout
Figure 4 — Holdout 2: output-blind historical transfer
Figure 5 — Controlled Simulation v2

Each figure is supplied as:
- PNG (300 dpi)
- PDF (vector)
EOF

python3 - <<'PY'
from hashlib import sha256
from pathlib import Path

root = Path("manuscript_figures/final_figure_set")
files = sorted(
    p for p in root.iterdir()
    if p.is_file() and p.name != "SHA256SUMS.txt"
)

lines = []
for path in files:
    digest = sha256(path.read_bytes()).hexdigest()
    lines.append(f"{digest}  {path.name}")

(root / "SHA256SUMS.txt").write_text(
    "\n".join(lines) + "\n",
    encoding="utf-8",
)
PY

rm -f manuscript_figures/final_figure_set.zip
(
  cd manuscript_figures
  zip -r -q final_figure_set.zip final_figure_set
)

echo "Final figure set:"
find "$FINAL" -maxdepth 1 -type f -print | sort
echo "ZIP: manuscript_figures/final_figure_set.zip"
