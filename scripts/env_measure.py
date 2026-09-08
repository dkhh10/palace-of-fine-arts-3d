#!/usr/bin/env python3
"""ENV round-3 measurements against ref 169 (python3 + numpy + PIL, no Blender).

    python3 scripts/env_measure.py RENDER_1920x1080.png [--label NAME]

Reports the four boxes QA round 02 used for the two environment defects, on the hero frame:

  QA-02-7  colonnade wings   left_wing / right_wing  (500 x 120 px bands over the colonnade shafts)
  QA-02-6  lagoon            water_flank / water_near

The reference numbers come from the ALIGNED ref-169 panel of `renders/qa_comparisons/round02_cam01_aligned_vs_ref169.png`
(that sheet is render | aligned photo | blend, so the photo panel is x 1920..3840). Using that panel rather than the
raw photo is what makes these numbers directly comparable to QA's: the boxes below reproduce QA-02-7's 66.0 / 137.2
and 88.3 / 141.0 and QA-02-6's flank pair exactly.

NOTE ON NAMES: QA round 02 called the x 60-560 band "north". In this project's world north is -X, and the hero camera
at (-14.1, 100) looking at the origin puts -X on the RIGHT of the frame, so x 60-560 is in fact the SOUTH wing. The
boxes are named left_wing / right_wing here to avoid inheriting the swap; the mapping is
  left_wing  = QA's "north band" = the SOUTH (roof306) colonnade
  right_wing = QA's "south band" = the NORTH (roof310) colonnade
"""
import argparse
import colorsys
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
MAIN = Path("/Users/dk/Projects/3d render blender 3rd attempt building")   # the reference photos live here only
ALIGNED = ROOT / "renders" / "qa_comparisons" / "round02_cam01_aligned_vs_ref169.png"
REF_PANEL = ROOT / "renders" / "previews" / "environment" / "ref169_aligned_cam01.png"
REF_RAW = MAIN / "reference" / "photos" / "raw" / "ref_169_main_Palace_of_Fine_Arts_16794p.jpg"

# QA round 03 quotes TWO reference numbers for the wing band and asks for both to be within 25 %
# (docs/qa_round_03.md, QA-03-10): the round-02 *aligned* panel and the *raw* ref-169 file (1920x1192) with the
# render box carried across by the align transform.  QA's raw mapping of the render band 60 480 560 600 is
# 269 465 651 557 -> ref lum 109.5; the aligned panel over the render box reads 137.2.
RAW_BOXES = {
    "left_wing":   (269, 465, 651, 557),     # QA-03-10's raw-mapped north-wing band
    "right_wing":  (1262, 465, 1644, 557),   # the same affine (x*0.7640+223.2, y*0.7667+97.0) on the right band
}

# name -> (x0, y0, x1, y1) on the 1920x1080 hero frame
BOXES = {
    "left_wing":   (60, 480, 560, 600),      # QA-02-7 "north band"
    "right_wing":  (1360, 480, 1860, 600),   # QA-02-7 "south band"
    "water_flank": (100, 900, 400, 960),     # QA-02-6 "mid-left band"
    "water_near":  (1150, 1000, 1450, 1050), # QA-02-6 near field (the over-saturated cyan patch)
}
# QA-02-7 / QA-02-6 acceptance: wings within 25 % of ref luminance, near-water saturation <= 0.45
TOL = {"left_wing": 0.25, "right_wing": 0.25, "water_flank": 0.30}


def ref_panel():
    """The aligned ref-169 hero panel, extracted once from the round-02 comparison sheet."""
    if not REF_PANEL.exists():
        if not ALIGNED.exists():
            sys.exit(f"missing {ALIGNED}")
        sheet = Image.open(ALIGNED).convert("RGB")
        REF_PANEL.parent.mkdir(parents=True, exist_ok=True)
        sheet.crop((1920, 0, 3840, sheet.height)).save(REF_PANEL)
        print(f"[env_measure] wrote {REF_PANEL.relative_to(ROOT)}")
    return np.asarray(Image.open(REF_PANEL).convert("RGB")).astype(np.float32)


def ref_raw():
    """The raw ref-169 file, for the boxes QA carried across with the align transform."""
    if not REF_RAW.exists():
        return None
    return np.asarray(Image.open(REF_RAW).convert("RGB")).astype(np.float32)


def stats(img, box):
    x0, y0, x1, y1 = box
    m = img[y0:y1, x0:x1].reshape(-1, 3).mean(axis=0)
    lum = float(0.2126 * m[0] + 0.7152 * m[1] + 0.0722 * m[2])
    h, s, _ = colorsys.rgb_to_hsv(*(m / 255.0))
    return dict(rgb=m, lum=lum, hue=h * 360.0, sat=s)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("render")
    ap.add_argument("--label", default="")
    a = ap.parse_args()
    img = np.asarray(Image.open(a.render).convert("RGB")).astype(np.float32)
    if img.shape[:2] != (1080, 1920):
        sys.exit(f"expected a 1920x1080 hero frame, got {img.shape[1]}x{img.shape[0]}")
    ref = ref_panel()
    raw = ref_raw()
    print(f"\n=== {a.label or Path(a.render).name}   vs aligned ref 169")
    print(f"{'box':13s} {'render lum':>10s} {'ref lum':>8s} {'ratio':>7s} {'r/g/b render':>22s} "
          f"{'hue':>6s} {'sat':>6s}  {'ref hue/sat':>12s}")
    for name, box in BOXES.items():
        r, f = stats(img, box), stats(ref, box)
        ratio = r["lum"] / max(1e-6, f["lum"])
        flag = ""
        if name in TOL:
            flag = "  OK" if abs(ratio - 1.0) <= TOL[name] else f"  OFF by {100 * (ratio - 1):+.0f} %"
        if name == "water_near":
            flag = "  OK" if r["sat"] <= 0.45 else f"  sat {r['sat']:.3f} > 0.45"
        print(f"{name:13s} {r['lum']:10.1f} {f['lum']:8.1f} {ratio:7.2f} "
              f"{r['rgb'][0]:6.1f},{r['rgb'][1]:5.1f},{r['rgb'][2]:5.1f}  {r['hue']:6.1f} {r['sat']:6.3f}  "
              f"{f['hue']:6.1f}/{f['sat']:.3f}{flag}")
    if raw is None:
        print(f"\n[env_measure] {REF_RAW} not found; raw-panel test skipped")
        return
    print(f"\n=== the same bands against the RAW ref 169 ({raw.shape[1]}x{raw.shape[0]}), QA-03-10 mapping")
    print(f"{'box':13s} {'render lum':>10s} {'raw lum':>8s} {'ratio':>7s}  {'raw box':>24s}")
    for name, rbox in RAW_BOXES.items():
        r, f = stats(img, BOXES[name]), stats(raw, rbox)
        ratio = r["lum"] / max(1e-6, f["lum"])
        flag = "  OK" if abs(ratio - 1.0) <= TOL.get(name, 0.25) else f"  OFF by {100 * (ratio - 1):+.0f} %"
        print(f"{name:13s} {r['lum']:10.1f} {f['lum']:8.1f} {ratio:7.2f}  {str(rbox):>24s}{flag}")


if __name__ == "__main__":
    main()
