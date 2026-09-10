#!/usr/bin/env python3
"""Six 100 % tiles of a hero frame (CLAUDE.md gate check, 2026-09-10). python3 + PIL, no Blender.

    python3 scripts/qa_hero_tiles.py IMG OUT_DIR [--cols 3 --rows 2]
Writes OUT_DIR/<stem>_tile_r<R>c<C>.png at 100 % (no resampling). View each with the Read tool; never judge the downscale.
"""
import sys, argparse
from pathlib import Path
from PIL import Image
ap = argparse.ArgumentParser(); ap.add_argument("img"); ap.add_argument("out"); ap.add_argument("--cols", type=int, default=3); ap.add_argument("--rows", type=int, default=2)
a = ap.parse_args()
im = Image.open(a.img); W, H = im.size; out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
tw, th = W // a.cols, H // a.rows
for r in range(a.rows):
    for c in range(a.cols):
        box = (c * tw, r * th, W if c == a.cols - 1 else (c + 1) * tw, H if r == a.rows - 1 else (r + 1) * th)
        p = out / f"{Path(a.img).stem}_tile_r{r}c{c}.png"; im.crop(box).save(p); print(p, box)
