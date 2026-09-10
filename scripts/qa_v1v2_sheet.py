#!/usr/bin/env python3
"""v1 vs v2 vs photo composite (lead, Phase 5 v2). python3 + PIL, no Blender.

    python3 scripts/qa_v1v2_sheet.py --v1 renders/final/v1/hero_cam01_3840x2160.png --v2 renders/final/v2/hero_cam01_3840x2160.png \
        --ref reference/photos/raw/ref_169_main_Palace_of_Fine_Arts_16794p.jpg --out renders/final/v2/v1_v2_ref169.png
Top row: v1 | v2 | ref 169 at 960 px wide. Bottom row: the main-arch crop of each at 1:1 of the 1920-wide frame (x 830-1090, y 300-580
in 1920x1080 coordinates; the photo's arch crop from the aligned overlay geometry: scale 1.3108, dx -291.8, dy -126.6).
"""
import argparse
from PIL import Image, ImageDraw, ImageFont
ap = argparse.ArgumentParser()
ap.add_argument("--v1", required=True); ap.add_argument("--v2", required=True); ap.add_argument("--ref", required=True); ap.add_argument("--out", required=True)
a = ap.parse_args()
FONT = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 22)
def load1920(p):
    im = Image.open(p).convert("RGB"); return im.resize((1920, int(1920 * im.height / im.width)), Image.LANCZOS)
v1, v2 = load1920(a.v1), load1920(a.v2)
ref = Image.open(a.ref).convert("RGB")
# photo -> render frame: render_xy = (photo_xy * scale) + (dx, dy)
S, DX, DY = 1.3108, -291.8, -126.6
ref_r = ref.resize((int(ref.width * S), int(ref.height * S)), Image.LANCZOS)
canvas = Image.new("RGB", (1920, 1080), (0, 0, 0)); canvas.paste(ref_r, (int(DX), int(DY))); ref = canvas
ARCH = (830, 300, 1090, 580)
W = 960; h = int(W * 1080 / 1920)
sheet = Image.new("RGB", (W * 3 + 40, h + 20 + (ARCH[3] - ARCH[1]) * 2 + 80), (18, 18, 18))
d = ImageDraw.Draw(sheet)
for i, (im, lab) in enumerate(((v1, "v1 (round 09 master)"), (v2, "v2 (vaults fixed, r17 light)"), (ref, "ref 169 aligned"))):
    x = 10 + i * (W + 10)
    sheet.paste(im.resize((W, h), Image.LANCZOS), (x, 30)); d.text((x, 4), lab, fill=(255, 220, 120), font=FONT)
    crop = im.crop(ARCH); crop = crop.resize((crop.width * 2, crop.height * 2), Image.NEAREST)
    sheet.paste(crop, (x, h + 70)); d.text((x, h + 44), f"main arch 2x of 1920 frame {ARCH}", fill=(200, 200, 200), font=FONT)
sheet.save(a.out); print("wrote", a.out, sheet.size)
