"""Side-by-side sheets: latest ornament preview render | reference crop | 50 % blend, for the QA record.

    python3 scripts/orn_compare.py [--tag full01]
Writes renders/previews/ornament/compare_<asset>.png using scripts/qa_compare.py (ffmpeg only).
"""
import sys, os, glob, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = Path("/Users/dk/Projects/3d render blender 3rd attempt building")
CROPS = MAIN / "reference" / "photos" / "ornament_crops"
PREV = ROOT / "renders" / "previews" / "ornament"
QA = ROOT / "scripts" / "qa_compare.py"

PAIRS = [
    ("capital_rotunda_v1", "corinthian_capital_1.jpg"),
    ("capital_rotunda_v2", "inner_capital_2.jpg"),
    ("capital_colonnade_v1", "colonnade_capital_2.jpg"),
    ("capital_inner_v1", "inner_capital_1.jpg"),
    ("maiden_v1", "weeping_maidens_2.jpg"),
    ("maiden_v2", "weeping_maidens_3.jpg"),
    ("attic_figure_v1", "attic_corner_figure_1.jpg"),
    ("attic_figure_v2", "attic_corner_figure_3.jpg"),
    ("winged_figure_v1", "angel_2.jpg"),
    ("urn_v1", "urn_pedestal_1.jpg"),
    ("urn_niche_v1", "drum_urn_finial_2.jpg"),
    ("attic_panel_v1", "zimm_panel_1.jpg"),
    ("attic_panel_v2", "zimm_panel_3.jpg"),
    ("keystone_v1", "keystone_mask_1.jpg"),
    ("drum_band_v1", "drum_urn_finial_2.jpg"),
    ("rosette_band_v1", "rostra_band_1.jpg"),
    ("entablature_note", None),
]


def latest(asset, tag=None):
    pat = str(PREV / f"{tag}_{asset}.png") if tag else str(PREV / f"*_{asset}.png")
    files = sorted(glob.glob(pat), key=os.path.getmtime)
    return files[-1] if files else None


def main():
    tag = sys.argv[sys.argv.index("--tag") + 1] if "--tag" in sys.argv else None
    outs = []
    for asset, crop in PAIRS:
        if crop is None:
            continue
        r = latest(asset, tag)
        c = CROPS / crop
        if not r or not c.exists():
            print(f"[orn_compare] skip {asset}: render {r} crop {c.exists()}")
            continue
        out = PREV / f"compare_{asset}.png"
        subprocess.run(["python3", str(QA), "--render", r, "--ref", str(c), "--out", str(out)], check=False)
        print(f"[orn_compare] {out.name}")
        outs.append(str(out))
    if outs:
        subprocess.run(["python3", str(QA), "--sheet", str(PREV / "compare_sheet.png")] + outs, check=False)
        print(f"[orn_compare] sheet compare_sheet.png ({len(outs)} panels)")


if __name__ == "__main__":
    main()
