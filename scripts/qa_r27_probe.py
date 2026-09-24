#!/usr/bin/env python3
"""QA round 27 (Phase 10 gate on the Cycles master) probe. No Blender, no Chrome. Plain python (numpy + PIL).

    /opt/homebrew/bin/python3.13 scripts/qa_r27_probe.py diff     # cycles_p10 vs cycles_p9 per station: MAE % of range, moved px, extents
    /opt/homebrew/bin/python3.13 scripts/qa_r27_probe.py movemap  # per-station moved-pixel maps (viewing fixtures, PFA_QA_TMP)
    /opt/homebrew/bin/python3.13 scripts/qa_r27_probe.py stone    # atlas no-op check: stone-only boxes p9 -> p10 at every station
    /opt/homebrew/bin/python3.13 scripts/qa_r27_probe.py cam02    # the new cypresses vs the rotunda's left base at cam02
    /opt/homebrew/bin/python3.13 scripts/qa_r27_probe.py shafts   # column-shaft hue / sat / b* at cam01/02/05/06 (the col-hue -10 magenta check)
The hero box table (water, stone holds, columns, foliage vs ref 169) is scripts/mat_p10w_measure.py hero, re-run on these frames
(log renders/logs/qa_r27_hero_boxes.log). Moved = any channel differs by > 4 levels (QA 26's definition).
"""
import os
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
P9 = ROOT / "renders/qa_comparisons/cycles_p9"
P10 = ROOT / "renders/qa_comparisons/cycles_p10"
OUT = Path(os.environ.get("PFA_QA_TMP", "/tmp")) / "r27"


def img(d, st, spp=32):
    return np.asarray(Image.open(str(d / f"cam{st:02d}_1080_{spp}spp.png")).convert("RGB")).astype(np.float64)


def lum(a):
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def hsv(a):
    x = a / 255.0
    mx, mn = x.max(-1), x.min(-1)
    d = mx - mn
    s = np.where(mx > 0, d / np.maximum(mx, 1e-6), 0)
    r, g, b = x[..., 0], x[..., 1], x[..., 2]
    h = np.where(mx == r, (g - b) / np.maximum(d, 1e-6) % 6, np.where(mx == g, (b - r) / np.maximum(d, 1e-6) + 2,
                                                                       (r - g) / np.maximum(d, 1e-6) + 4)) * 60
    return h, s, mx


def moved(a, b):
    return (np.abs(a - b).max(-1) > 4)


def blk(a, k=8):
    h, w = a.shape[0] // k * k, a.shape[1] // k * k
    return a[:h, :w].reshape(h // k, k, w // k, k, -1).mean((1, 3))


def bmoved(a, b, k=8):
    """moved on 8x8 block means (suppresses the 32-spp sample noise, which alone moves ~37 % of single pixels)."""
    return np.abs(blk(a, k) - blk(b, k)).max(-1) > 4


def diff():
    print("st  MAE%range  moved%px  moved%8x8blk   extent of 8x8 moves (px)   luma ratio   blk-moved% by row-third (top/mid/bottom)")
    for st in range(1, 7):
        a, b = img(P9, st), img(P10, st)
        mae = float(np.abs(a - b).mean() / 255 * 100)
        m, mb = moved(a, b), bmoved(a, b)
        ys, xs = np.nonzero(mb)
        ext = f"x {8 * xs.min()}-{8 * xs.max() + 7}, y {8 * ys.min()}-{8 * ys.max() + 7}" if len(xs) else "none"
        thirds = [100 * float(mb[i * 45:(i + 1) * 45].mean()) for i in range(3)]
        print(f"{st:02d}  {mae:8.3f}  {100 * m.mean():6.2f}   {100 * mb.mean():6.2f}      {ext:26s} {lum(b).mean() / lum(a).mean():.4f}   "
              + " / ".join(f"{t:5.2f}" for t in thirds))
    a, b = img(P10, 1, 32), img(P10, 1, 64)
    print(f"noise floor: cam01 p10 32 vs 64 spp MAE {np.abs(a - b).mean() / 255 * 100:.3f} %, moved px {100 * moved(a, b).mean():.2f} %, "
          f"8x8 blk {100 * bmoved(a, b).mean():.2f} %")


def movemap():
    OUT.mkdir(parents=True, exist_ok=True)
    for st in range(1, 7):
        a, b = img(P9, st), img(P10, st)
        m = np.kron(bmoved(a, b), np.ones((8, 8), bool))
        base = (lum(b) * 0.45).astype(np.uint8)
        rgb = np.stack([base] * 3, -1)
        rgb[m] = (255, 40, 200)
        Image.fromarray(rgb).resize((960, 540)).save(OUT / f"move_cam{st:02d}.jpg", quality=85)
    print("maps ->", OUT)


# stone-only boxes (1920x1080), chosen on the p9 frames where no tree, water or sky is in the box
STONE = {1: [("attic_sunlit", (620, 250, 760, 300)), ("attic_shaded", (1180, 250, 1300, 300)),
             ("entablature", (560, 330, 780, 360)), ("drum", (880, 150, 1040, 200))],
         3: [("near shaft", (40, 200, 260, 900)), ("rotunda", (760, 300, 1100, 520))],
         4: [("coffers", (700, 300, 1220, 780)), ("ring", (300, 80, 1620, 200))],
         5: [("rotunda", (700, 250, 1000, 500))]}


def stone():
    print("box              p9 lum/sat  ->  p10 lum/sat   max|d| moved%")
    for st, boxes in STONE.items():
        a, b = img(P9, st), img(P10, st)
        for name, (x0, y0, x1, y1) in boxes:
            pa, pb = a[y0:y1, x0:x1], b[y0:y1, x0:x1]
            sa, sb = hsv(pa)[1].mean(), hsv(pb)[1].mean()
            print(f"cam{st:02d} {name:12s} {lum(pa).mean():6.1f}/{sa:.3f} -> {lum(pb).mean():6.1f}/{sb:.3f}   "
                  f"{np.abs(pa - pb).max():5.0f} {100 * moved(pa, pb).mean():6.2f}")


def cam02():
    a, b = img(P9, 2), img(P10, 2)
    m = np.kron(bmoved(a, b), np.ones((8, 8), bool))
    cols = m.mean(0)
    xs = np.nonzero(cols > 0.02)[0]
    print(f"cam02 moved {100 * m.mean():.2f} %; columns with > 2 % moved: x {xs.min() if len(xs) else '-'}-{xs.max() if len(xs) else '-'}")
    for x0 in range(0, 1920, 160):
        c = m[:, x0:x0 + 160]
        ys = np.nonzero(c.any(1))[0]
        if c.mean() > 0.005:
            print(f"  x {x0:4d}-{x0 + 159:4d}: moved {100 * c.mean():5.2f} %, rows {ys.min()}-{ys.max()}, "
                  f"lum {lum(a[:, x0:x0 + 160][c]).mean():5.1f} -> {lum(b[:, x0:x0 + 160][c]).mean():5.1f}")


SHAFTS = {1: (1000, 360, 1240, 480), 2: None, 5: None, 6: None}


def shafts():
    # masked shaft pixels: warm-red hue band, sat > .25, in the given crop (cam01 = the fixed shaft crop of mat_p10w_measure)
    for st, crop in ((1, (1000, 360, 1240, 480)), (2, (0, 0, 1920, 1080)), (5, (0, 0, 1920, 1080)), (6, (0, 0, 1920, 1080))):
        for tag, d in (("p9", P9), ("p10", P10)):
            a = img(d, st)
            x0, y0, x1, y1 = crop
            p = a[y0:y1, x0:x1]
            h, s, v = hsv(p)
            m = ((h > 330) | (h < 20)) & (s > 0.25) & (v > 0.12)
            if m.sum() < 50:
                print(f"cam{st:02d} {tag:4s} n={int(m.sum())}"); continue
            rgb = p[m].mean(0)
            hh = np.where(h[m] > 180, h[m] - 360, h[m])
            print(f"cam{st:02d} {tag:4s} n={int(m.sum()):7d} hue(red-band) {hh.mean():+6.1f} sat {s[m].mean():.3f} "
                  f"lum {lum(rgb[None])[0]:6.1f} R-B {rgb[0] - rgb[2]:+6.1f} B/R {rgb[2] / max(rgb[0], 1):.3f} magenta share "
                  f"{100 * float(((h[m] > 330)).mean()):5.1f} %")


if __name__ == "__main__":
    cmds = sys.argv[1:] or ["diff"]
    for c in cmds:
        globals()[c]()
