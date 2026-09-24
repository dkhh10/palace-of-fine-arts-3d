#!/usr/bin/env python3
"""Phase 10 ENV round 2 sheet: renders/qa_comparisons/env_p10r2_sheet.png.  No Blender.

    /opt/homebrew/bin/python3.13 scripts/env_p10r2_sheet.py

Row 1  cam 01 at 100 % around the willow box (x 0.33-0.51, y 0.40-0.68; box in yellow): Eevee before | Eevee after |
       Cycles 32 spp after | ref 169 (registered, env_p10_boxes.ref_frame), each shown x1.5 (nearest-free resample).
Row 2  the index pass (own-pixel alpha, env_p10r2_mask.py) over ref 169: before (red) | after (red; the P10R2_ADD pale crown orange) | ref's
       hand-segmented willow (cyan) | after silhouette classes (blue column in front, green in-plane stone, red side-arch
       opening, magenta drum; the hero-arch count is in the caption).
Row 3  cam 02 full frame at 960 px: Eevee before | after.
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import env_p10_boxes as B            # noqa: E402
import env_p10r2_willowbox as WB     # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
P = ROOT / "renders" / "previews" / "environment"
OUT = ROOT / "renders" / "qa_comparisons" / "env_p10r2_sheet.png"
W, H = 1920, 1080
CROP = (int(0.33 * W), int(0.40 * H), int(0.51 * W), int(0.68 * H))
BOX = (int(0.39 * W), int(0.45 * H), int(0.47 * W), int(0.62 * H))
K = 1.5
GAP = 8


def rgb(p):
    im = Image.open(p).convert("RGB")
    return im if im.size == (W, H) else im.resize((W, H), Image.Resampling.LANCZOS)


def crop(im, box=True):
    im = im.copy()
    if box:
        ImageDraw.Draw(im).rectangle(BOX, outline=(255, 230, 0), width=2)
    c = im.crop(CROP)
    return c.resize((int(c.size[0] * K), int(c.size[1] * K)), Image.Resampling.LANCZOS)


def overlay(bg, m, col, a=0.55):
    o = np.asarray(bg).astype(float).copy()
    o[m] = o[m] * (1 - a) + np.array(col) * a
    return Image.fromarray(o.astype("uint8"))


def labelled(im, text):
    im = im.copy()
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, im.size[0], 16), fill=(0, 0, 0))
    d.text((4, 2), text, fill=(255, 255, 255))
    return im


def main():
    ref = Image.fromarray(B.ref_frame().astype("uint8"))
    m = {k: WB.load_mask(P / f"p10r2_{k}_mask_target.png") for k in ("before", "after3")}
    rm = WB.ref_mask()
    st = {k: WB.box_stats(v) for k, v in m.items()}
    sr = WB.box_stats(rm)
    js = json.loads((P / "p10r2_after3_mask.json").read_text())["silhouette"]["target"]
    sil = np.asarray(Image.open(P / "p10r2_after3_silhouette_target.png").convert("RGBA"))
    silim = Image.fromarray(np.where(sil[..., 3:4] > 0, sil[..., :3], np.asarray(ref) // 3).astype("uint8"))
    row1 = [labelled(crop(rgb(P / "p10r2_before_cam01.png")), "Eevee BEFORE (6.9,43.4) h9"),
            labelled(crop(rgb(P / "p10r2_after_cam01.png")), "Eevee AFTER willow (4.4,43.4) h5.4 w1.7 + P10R2_ADD"),
            labelled(crop(rgb(P / "p10r2_cycles_after_cam01.png")), "Cycles 32 spp AFTER"),
            labelled(crop(ref), "ref 169 (registered to cam 01)")]
    row2 = [labelled(crop(overlay(ref, m["before"], (255, 0, 0))),
                     f"own px BEFORE: box {st['before'][0]:.1f} %  top row {st['before'][1]:.0f}"),
            labelled(crop(overlay(overlay(ref, WB.load_mask(P / "p10r2_after3_mask_standin.png"), (255, 160, 0), 0.35),
                              m["after3"], (255, 0, 0))),
                     f"own px AFTER (+stand-in orange): box {st['after3'][0]:.1f} %  top row {st['after3'][1]:.0f}"),
            labelled(crop(overlay(ref, rm, (0, 255, 255))), f"ref willow polygon: box {sr[0]:.1f} %  top row {sr[1]:.0f}"),
            labelled(crop(silim), f"AFTER classes: hero arch {js['hero_arch_opening_px']}  drum {js['drum_px']}  "
                                  f"side arch {js['side_arch_opening_px']} px")]
    c2 = [labelled(rgb(P / f"p10r2_{t}_cam02.png").resize((960, 540), Image.Resampling.LANCZOS), f"cam 02 Eevee {t.upper()}")
          for t in ("before", "after")]
    cw, ch = row1[0].size
    width = max(4 * cw + 3 * GAP, 2 * 960 + GAP)
    sheet = Image.new("RGB", (width, 2 * ch + 540 + 2 * GAP + 22), (24, 24, 24))
    ImageDraw.Draw(sheet).text((6, 4), "ENV p10r2 - hero-shore willow to ref 169's box (cam 01 x 0.39-0.47, y 0.45-0.62; "
                                        "own pixels = Cycles holdout alpha, LOD0)", fill=(255, 255, 255))
    y = 22
    for row in (row1, row2):
        for i, im in enumerate(row):
            sheet.paste(im, (i * (cw + GAP), y))
        y += ch + GAP
    for i, im in enumerate(c2):
        sheet.paste(im, (i * (960 + GAP), y))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(OUT)
    print(f"wrote {OUT} {sheet.size}")


if __name__ == "__main__":
    main()
