#!/usr/bin/env python3
"""Phase 10 ENV probe: the cam-01 foliage boxes of docs/briefs/phase10_env.md, on any 1920x1080 cam-01 frame and on
ref 169 registered to the cam-01 frame by the round-02 align transform (`env_r8_fit.REF_XF`).  No Blender.

    /opt/homebrew/bin/python3.13 scripts/env_p10_boxes.py [label=path.png ...]

Definitions (one place, used for every column):
  * sky      B > 140 and B - R > 5 and B >= G - 10   (ref sky ~ (185-203, 227-239, 251-253) and its pale horizon
             (236, 249, 245); render sky ~ (149-166, 188-199, 226-230); lit stone (233, 202, 88) and lit foliage
             (108, 111, 86) fail B - R > 5 or B > 140)
  * dark     Rec.601 luma < 60 (the threshold `env_r8_fit.ref_profile` measured ref 169's mass with)
  * leaf     G - 0.85 R > 5 and B < G                (QA 16's leaf mask, `qa_r16_probe`)
  * top row  over the box's columns, the first row from y = 0.15 downward with 3 consecutive non-sky pixels; the
             median over columns is the crown-top row, p25 the tallest quarter (1080-px rows and frame y).
Boxes (frame fractions, y down):
  1  NE mass (brief)        x 0.580-0.740  y 0.280-0.440   the brief's box; x < 0.655 is the rotunda body here
  1s NE mass, sky side      x 0.655-0.740  y 0.280-0.440   the part a tree may fill (the plan's cam-01 span rule)
  2  willow left of rotunda x 0.390-0.470  y 0.450-0.620   impost height to the water line
  3  north wing bays        x 0.602-1.000  y 0.380-0.587   `env_preview.sky_through_wing('north')`'s box (z 4-17 m)
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
MAIN = Path("/Users/dk/Projects/3d render blender 3rd attempt building")
REF169 = MAIN / "reference/photos/raw/ref_169_main_Palace_of_Fine_Arts_16794p.jpg"
REF_XF = (0.7640, 223.2, 0.7667, 97.0)          # env_r8_fit.REF_XF: cam-01 px -> raw ref-169 px
W, H = 1920, 1080
BOXES = {
    "1  NE mass (brief)": (0.580, 0.280, 0.740, 0.440),
    "1s NE mass sky side": (0.655, 0.280, 0.740, 0.440),
    "2  willow box": (0.390, 0.450, 0.470, 0.620),
    "3  N wing bays": (0.602, 0.380, 1.000, 0.587),
}
TOP_COLS = {"1  NE mass (brief)": (0.655, 0.740), "1s NE mass sky side": (0.655, 0.740)}


def ref_frame():
    sx, dx, sy, dy = REF_XF
    im = Image.open(REF169).convert("RGB")
    box = (dx, dy, W * sx + dx, H * sy + dy)
    return np.asarray(im.transform((W, H), Image.Transform.EXTENT, box, Image.Resampling.BICUBIC)).astype(float)


def load(p):
    im = Image.open(p).convert("RGB")
    if im.size != (W, H):
        im = im.resize((W, H), Image.Resampling.LANCZOS)
    return np.asarray(im).astype(float)


def masks(a):
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    sky = (b > 140) & (b - r > 5) & (b >= g - 10)
    dark = (0.299 * r + 0.587 * g + 0.114 * b) < 60
    leaf = ((g - 0.85 * r) > 5) & (b < g)
    return sky, dark, leaf


def top_row(sky, x0, x1):
    c0, c1 = int(x0 * W), int(x1 * W)
    r0 = int(0.15 * H)
    ns = ~sky[r0:, c0:c1]
    run = ns[:-2] & ns[1:-1] & ns[2:]
    rows = []
    for j in range(run.shape[1]):
        k = np.argmax(run[:, j])
        rows.append(r0 + k if run[k, j] else H)
    rows = np.array(rows)
    return float(np.median(rows)), float(np.percentile(rows, 25))


def stats(a):
    sky, dark, leaf = masks(a)
    out = {}
    for name, (x0, y0, x1, y1) in BOXES.items():
        sl = (slice(int(y0 * H), int(y1 * H)), slice(int(x0 * W), int(x1 * W)))
        d = dict(dark=100 * dark[sl].mean(), sky=100 * sky[sl].mean(), leaf=100 * leaf[sl].mean())
        if name in TOP_COLS:
            d["top"], d["top25"] = top_row(sky, *TOP_COLS[name])
        out[name] = d
    return out


def main(argv):
    frames = [("ref169", None)]
    for a in argv:
        lab, _, p = a.partition("=")
        frames.append((lab, p))
    res = {}
    for lab, p in frames:
        res[lab] = stats(ref_frame() if p is None else load(p))
    print(f"{'box':22s} {'frame':14s} {'dark%':>7s} {'sky%':>7s} {'leaf%':>7s} {'top px':>7s} {'top y':>6s} {'p25 px':>7s}")
    for name in BOXES:
        for lab, _ in frames:
            d = res[lab][name]
            t = f"{d['top']:7.0f} {d['top'] / H:6.3f} {d['top25']:7.0f}" if "top" in d else ""
            print(f"{name:22s} {lab:14s} {d['dark']:7.1f} {d['sky']:7.1f} {d['leaf']:7.1f} {t}")
    return res


if __name__ == "__main__":
    main(sys.argv[1:])
