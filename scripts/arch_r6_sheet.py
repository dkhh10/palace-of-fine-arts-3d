"""Architecture round 6 composite: the hero-facing stack before / after / ref 169, with the course table burnt in.

    python3 scripts/arch_r6_sheet.py

Inputs, all already in the 1920x1080 cam01 pixel grid:
  before : panel 0 of renders/qa_comparisons/round06_cam01_aligned_vs_ref169.png (QA's round-06 Cycles hero)
  ref    : panel 1 of the same sheet (ref 169 warped into the render frame by qa_silhouette align, REF169_XF)
  after  : renders/previews/architecture/arch_r6_cam01_stack.png (this round's Cycles 64 spp border render)
Outputs:
  renders/qa_comparisons/arch_r6_aligned_vs_ref169.png   3 panels (after | ref | blend) -- the file qa_stack_offset
                                                         re-runs on, so QA's own tool measures this round's rows
  renders/qa_comparisons/arch_r6_sheet.png               the composite for the report
"""
import sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
QA = ROOT / "renders" / "qa_comparisons"
BEFORE_SHEET = QA / "round06_cam01_aligned_vs_ref169.png"
AFTER = ROOT / "renders" / "previews" / "architecture" / "arch_r6_cam01_stack.png"
FONT = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
X0, X1, Y0, Y1 = 830, 1100, 140, 380          # the band the round-6 work moves (measurement band is x 880-1040)
SCALE = 1.55

# course table: (label, before row, after row, ref 169 row); rows are 1920x1080 cam01 rows.
TABLE = [("attic crown, top lit edge", "168", "168", "169"),
         ("attic cornice corona soffit", "(none)", "181.6", "182"),
         ("attic relief field top", "180", "198.4", "198"),
         ("attic relief field bottom", "241", "268.9", "269"),
         ("entablature corona soffit", "254", "280.6", "281"),
         ("frieze top (dentil bed bottom)", "280", "302.0", "300-302"),
         ("architrave bottom", "309", "327.7", "328"),
         ("capital top (pier, az 64.9)", "303", "322.9", "318 +-4")]

im = Image.open(BEFORE_SHEET).convert("RGB")
W, H = im.width // 3, im.height
before = im.crop((0, 0, W, H))
ref = im.crop((W, 0, 2 * W, H))
after = Image.open(AFTER).convert("RGB")
assert after.size == (W, H), f"{after.size} != {(W, H)}"

# ---- 3-panel aligned sheet in QA's own layout, so scripts/qa_stack_offset.py measures this round unchanged
blend = Image.fromarray((0.5 * np.asarray(after).astype(float) + 0.5 * np.asarray(ref).astype(float)).astype("uint8"))
sheet = Image.new("RGB", (3 * W, H))
for i, p in enumerate((after, ref, blend)):
    sheet.paste(p, (i * W, 0))
sheet.save(QA / "arch_r6_aligned_vs_ref169.png")

# ---- the composite for the report
f_lab = ImageFont.truetype(FONT, 17)
f_tab = ImageFont.truetype(FONT, 15)
panels = []
for img, name in ((before, "BEFORE  round 06"), (after, "AFTER  round 06 -> r6"), (ref, "REF 169  (aligned)")):
    c = img.crop((X0, Y0, X1, Y1)).resize((int((X1 - X0) * SCALE), int((Y1 - Y0) * SCALE)), Image.LANCZOS)
    d = ImageDraw.Draw(c)
    for y in range(Y0, Y1, 10):
        yy = (y - Y0) * SCALE
        d.line([(0, yy), (16 if y % 20 == 0 else 8, yy)], fill=(255, 40, 40))
        if y % 20 == 0:
            d.text((18, yy - 7), str(y), font=f_tab, fill=(255, 70, 70))
    d.rectangle([0, 0, c.width - 1, 24], fill=(0, 0, 0))
    d.text((6, 4), name, font=f_lab, fill=(255, 235, 90))
    panels.append(c)

gap, pad = 10, 12
tw = 470
out = Image.new("RGB", (sum(p.width for p in panels) + 2 * gap + tw + 3 * pad, panels[0].height + 2 * pad), (18, 18, 20))
d = ImageDraw.Draw(out)
x = pad
for p in panels:
    out.paste(p, (x, pad))
    x += p.width + gap
x += pad
d.text((x, pad + 2), "course row on cam01 (1920x1080)", font=f_lab, fill=(255, 235, 90))
d.text((x, pad + 26), f"{'course':30s}{'before':>8s}{'after':>8s}{'ref169':>9s}", font=f_tab, fill=(180, 200, 255))
for i, (lab, b, a, r) in enumerate(TABLE):
    d.text((x, pad + 46 + i * 19), f"{lab:30s}{b:>8s}{a:>8s}{r:>9s}", font=f_tab, fill=(235, 235, 235))
y = pad + 46 + len(TABLE) * 19 + 12
for line in ["13.42 px/m at the wall plane; 1 m of outward",
             "projection lifts a point 5.16 px.",
             "",
             "envelope HELD: --sil apex 87.5 corner_top 212.0",
             "W_a 544 px rise/W_a 0.2288 (round 4 alpha render",
             "88 / 212 / 544 / 0.228) -> 0.0-0.6 % on all four.",
             "",
             "tris LOD0 2,694,686 LOD1 1,109,390 (+0.01 %).",
             "UVProj re-baked by the build: 26,376 verts,",
             "0 clamped, round-trip 0.00 px, 3/3 named points."]:
    d.text((x, y), line, font=f_tab, fill=(200, 200, 200))
    y += 19
out.save(QA / "arch_r6_sheet.png")
print(f"[arch_r6_sheet] wrote {QA / 'arch_r6_aligned_vs_ref169.png'} and {QA / 'arch_r6_sheet.png'} {out.size}")
