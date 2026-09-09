#!/usr/bin/env python3
"""QA round 08 item 2: the photo-projection seam test on cameras OTHER than the projector.

The projection (MAT r9/r9b) is a Window-coordinate lookup from CAM_qa_01_lagoon_hero with a soft band mask
(projection_meta.json "band" = rows 86-100 .. 312-328 of the 1920x1080 hero frame) and a facing mask.  A seam
would appear where the mask leaves 1 on a surface that is continuous in the picture: as a horizontal step at the
band edge, or as a vertical step around the building's curvature where the facing mask ramps out.

Two things are produced, both from the round's own frames (no extra render, no projection-off twin):

  1. `crops`  a composite of 1:1 crops at those two places on cam02 and cam05, so the seam can be looked for.
  2. `step`   the numeric half: inside a crop, the largest COHERENT step of the horizontally-blurred row profile
              (a mask edge is coherent across the whole crop width and survives a blur; a moulding is a real edge
              too, so the number is reported next to the crop's own edge population, and what matters is whether
              any step stands out of that population).

    python3 scripts/qa_r08_seams.py --out renders/qa_comparisons/round08_seams.png
"""
import argparse
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
FONT = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"


def lum(a):
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def step_stats(arr):
    """arr = HxWx3 crop.  Row profile of a horizontally blurred crop, then |d/dy|."""
    L = lum(arr)
    k = np.ones(9) / 9.0
    blur = np.apply_along_axis(lambda r: np.convolve(r, k, mode="same"), 1, L)
    prof = blur.mean(axis=1)
    d = np.abs(np.diff(prof))
    if d.size == 0:
        return 0.0, 0.0, 0
    return float(d.max()), float(np.median(d)), int(np.argmax(d))


CROPS = [
    # (label, image, x0, y0, x1, y1)
    ("cam02 lower band edge (z~26-27 m: capital / architrave)",
     "round08_02_lagoon_ne_threequarter.png", 380, 300, 780, 460),
    ("cam02 facing-mask ramp, rotunda curvature (N face -> E face)",
     "round08_02_lagoon_ne_threequarter.png", 700, 120, 1100, 280),
    ("cam02 upper band edge (z~43-44 m: dome springing)",
     "round08_02_lagoon_ne_threequarter.png", 380, 40, 780, 200),
    ("cam05 lower band edge (attic -> colonnade)",
     "round08_05_south_lawn.png", 300, 230, 700, 390),
    ("cam05 facing-mask ramp along the south wing",
     "round08_05_south_lawn.png", 700, 150, 1100, 310),
    ("cam01 (projector) lower band edge, for reference",
     "round08_01_lagoon_hero_cycles.png", 760, 260, 1160, 420),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "renders/qa_comparisons/round08_seams.png"))
    a = ap.parse_args()
    P = ROOT / "renders/previews/qa"
    ims, labels = [], []
    for label, name, x0, y0, x1, y1 in CROPS:
        im = Image.open(P / name).convert("RGB")
        c = im.crop((x0, y0, x1, y1))
        arr = np.asarray(c).astype(np.float32)
        mx, med, row = step_stats(arr)
        ims.append(c)
        labels.append(f"{label}  [{x0},{y0},{x1},{y1}]  max coherent step {mx:.2f} lum/row at +{row}, "
                      f"median {med:.2f}, ratio {mx / max(med, 1e-6):.1f}x")
        print(f"{label:62s} max {mx:6.2f}  median {med:5.2f}  ratio {mx / max(med, 1e-6):5.1f}x  at row +{row}")
    w = max(i.width for i in ims)
    pad = 26
    sheet = Image.new("RGB", (w, sum(i.height + pad for i in ims)), (12, 12, 12))
    d = ImageDraw.Draw(sheet)
    try:
        f = ImageFont.truetype(FONT, 15)
    except Exception:
        f = ImageFont.load_default()
    y = 0
    for im, lab in zip(ims, labels):
        d.text((6, y + 5), lab, fill=(255, 220, 120), font=f)
        sheet.paste(im, (0, y + pad))
        y += im.height + pad
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    sheet.save(a.out)
    print("wrote", a.out)


if __name__ == "__main__":
    main()
