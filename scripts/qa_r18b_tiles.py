#!/usr/bin/env python3
"""QA round 18b tile cutter — the six-station full-resolution review, MOBILE.

The gate5c mobile captures are 1170x2532 portrait (buffer 832x1801 at dpr 0.71, the 1.5 Mpx cap),
so the 3 x 2 grid CLAUDE.md names is cut as 2 columns x 3 rows: six 585x844 tiles per station,
each written at 100 % (no downscale) plus its luma / contrast statistics, so a hole, a missing group
or a flat untextured surface is visible and numbered.

    python3 scripts/qa_r18b_tiles.py            # gate5cm -> renders/web/tiles/gate5c/ (gitignored)
    python3 scripts/qa_r18b_tiles.py gate5bm    # the pre-fix capture, for the canvas-defect evidence
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "renders" / "web"
COLS, ROWS = 2, 3
LUMA = np.array([0.2126, 0.7152, 0.0722])


def hard(a):
    gx = np.abs(np.diff(a, axis=1))
    return (gx > 12).mean() * 100


def main(tag="gate5cm"):
    out = WEB / "tiles" / tag
    out.mkdir(parents=True, exist_ok=True)
    print(f"{'tile':14s} {'lum':>7s} {'std':>7s} {'p05':>7s} {'p95':>7s} {'hard%':>7s} {'flat px%':>9s}")
    for st in range(1, 7):
        im = Image.open(WEB / f"{tag}_cam{st:02d}.png").convert("RGB")
        w, h = im.size
        tw, th = w // COLS, h // ROWS
        for r in range(ROWS):
            for c in range(COLS):
                box = (c * tw, r * th, (c + 1) * tw, (r + 1) * th)
                t = im.crop(box)
                name = f"cam{st:02d}_r{r + 1}c{c + 1}"
                t.save(out / f"{name}.png")
                a = np.asarray(t, dtype=np.float64) @ LUMA
                # "flat px" = pixels whose 3x3 neighbourhood varies by less than 1/255
                d = np.abs(np.diff(a, axis=1))
                flat = (d < 1).mean() * 100
                print(f"{name:14s} {a.mean():7.2f} {a.std():7.2f} {np.percentile(a, 5):7.2f} "
                      f"{np.percentile(a, 95):7.2f} {hard(a):6.2f}% {flat:8.2f}%")
    print(f"-> {out}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "gate5cm")
