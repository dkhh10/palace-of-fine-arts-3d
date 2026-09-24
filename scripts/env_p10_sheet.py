"""Phase 10 ENV sheet: cam-01 100 % crops (NE mass + willow) Cycles before (cycles_p9) / Cycles after / ref 169,
then cam02 and cam05 Eevee before / after full frames at 960.  No Blender.

    /opt/homebrew/bin/python3.13 scripts/env_p10_sheet.py
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import env_p10_boxes as B

ROOT = Path(__file__).resolve().parents[1]
PREV = ROOT / "renders/previews/environment"
BEFORE_CYC = B.MAIN / "renders/qa_comparisons/cycles_p9/cam01_1080_32spp.png"
AFTER_CYC = PREV / "p10_cycles_after2_cam01.png"
OUT = ROOT / "renders/qa_comparisons/env_p10_sheet.png"
CROP = (int(0.36 * 1920), int(0.22 * 1080), int(0.78 * 1920), int(0.64 * 1080))   # willow .39-.47 + NE mass .58-.74


def label(im, text):
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, 11 * len(text) + 12, 28), fill=(0, 0, 0))
    d.text((6, 6), text, fill=(255, 255, 255))
    return im


def boxes(im):
    d = ImageDraw.Draw(im)
    for name, (x0, y0, x1, y1) in B.BOXES.items():
        if name.startswith("3"):
            continue
        d.rectangle((x0 * 1920 - CROP[0], y0 * 1080 - CROP[1], x1 * 1920 - CROP[0], y1 * 1080 - CROP[1]),
                    outline=(255, 0, 255), width=2)
    return im


ref = Image.fromarray(B.ref_frame().clip(0, 255).astype("uint8"))
row1 = [("cam01 Cycles 32spp BEFORE (cycles_p9)", Image.open(BEFORE_CYC).convert("RGB")),
        ("cam01 Cycles 32spp AFTER (p10, front column 20 m)", Image.open(AFTER_CYC).convert("RGB")),
        ("ref 169 registered to cam01", ref)]
crops = [label(boxes(im.crop(CROP)), t) for t, im in row1]
cw, ch = crops[0].size
fr = []
for cam in ("02", "05"):
    for tag in ("before", "after2"):
        im = Image.open(PREV / f"p10_{tag}_cam{cam}.png").convert("RGB")
        im.thumbnail((960, 960))
        fr.append(label(im, f"cam{cam} Eevee {'BEFORE' if tag == 'before' else 'AFTER'}"))
fw, fh = fr[0].size
W = max(3 * cw, 2 * fw)
sheet = Image.new("RGB", (W, ch + 2 * fh), (20, 20, 20))
for k, c in enumerate(crops):
    sheet.paste(c, (k * cw, 0))
for k, f in enumerate(fr):
    sheet.paste(f, ((k % 2) * fw, ch + (k // 2) * fh))
sheet.save(OUT)
print(f"[env_p10_sheet] {OUT} {sheet.size}")
