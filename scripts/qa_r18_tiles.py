#!/usr/bin/env python3
"""QA round 18 tile cutter — the six-station full-resolution review CLAUDE.md requires.

Cuts the gate5 (staging URL) capture into 3 x 2 tiles at 100 % and writes each one beside the SAME
crop of round16c (the 6c build QA 17 scored), so a defect that is new to the deployment is visible as
a difference and a carried 6c residual is visible as a match. Also prints the per-tile MAE so the
eye has a number beside it.

    python3 scripts/qa_r18_tiles.py            # all six stations -> renders/web/tiles/gate5/ (gitignored)
    python3 scripts/qa_r18_tiles.py mobile     # the 1170x2532 mobile captures, 2 x 3 contact sheet
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "renders" / "web"
OUT = WEB / "tiles" / "gate5"
COLS, ROWS = 3, 2
LUMA = np.array([0.2126, 0.7152, 0.0722])


def pairs():
    OUT.mkdir(parents=True, exist_ok=True)
    print(f"{'tile':14s} {'gate5 lum':>10s} {'r16c lum':>9s} {'MAE':>7s} {'max|d|':>7s} {'>8/255 %':>9s}")
    for st in range(1, 7):
        a = Image.open(WEB / f"gate5_cam{st:02d}.png").convert("RGB")
        b = Image.open(WEB / f"round16c_cam{st:02d}.png").convert("RGB")
        w, h = a.size
        tw, th = w // COLS, h // ROWS
        for r in range(ROWS):
            for c in range(COLS):
                box = (c * tw, r * th, (c + 1) * tw, (r + 1) * th)
                ta, tb = a.crop(box), b.crop(box)
                sheet = Image.new("RGB", (tw * 2 + 8, th), (20, 20, 20))
                sheet.paste(ta, (0, 0))
                sheet.paste(tb, (tw + 8, 0))
                name = f"cam{st:02d}_r{r + 1}c{c + 1}"
                sheet.save(OUT / f"{name}.png")
                na = np.asarray(ta, dtype=np.float64) @ LUMA
                nb = np.asarray(tb, dtype=np.float64) @ LUMA
                d = np.abs(na - nb)
                print(f"{name:14s} {na.mean():10.2f} {nb.mean():9.2f} {d.mean():7.3f} "
                      f"{d.max():7.2f} {(d > 8).mean() * 100:8.2f}%")


def mobile():
    ims = [Image.open(WEB / f"gate5m_cam{st:02d}.png").convert("RGB") for st in range(1, 7)]
    w, h = 300, int(300 * ims[0].size[1] / ims[0].size[0])
    sheet = Image.new("RGB", (w * 6 + 5 * 6, h), (20, 20, 20))
    for i, im in enumerate(ims):
        sheet.paste(im.resize((w, h), Image.LANCZOS), (i * (w + 6), 0))
    p = OUT / "mobile_sheet.png"
    OUT.mkdir(parents=True, exist_ok=True)
    sheet.save(p)
    print(p, sheet.size)


if __name__ == "__main__":
    (mobile if "mobile" in sys.argv[1:] else pairs)()
