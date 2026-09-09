"""Composite for the round-7 review fixes (docs/reviews/mat_r7_review.md items 1, 3, 6).

    python3 scripts/mat_r7fix_sheet.py

Row 1 -- QA-05-4's reflection column box 900 760 1020 840 at 1:1 (probed 2026-09-09: 100 % MAT_water_lagoon at a
mean 22.1 m), for the shipped water and for four sheen weights plus sweep case w6, against ref 169 warped into the
render frame.  The label under each panel is what QA scores: saturation, hue and R-B.  The point of the row is
that every sheen weight that clears `sat >= 0.25` clears it at hue ~213, i.e. by making the box bluer.

Row 2 -- QA-02-6 from above: CAM_qa_06_aerial at the shipped WATER_MURK_GAIN 0.15 and at round 6's 1.00, in both
engines, with QA's own round-05 aerial for scale.  The label is the open-water box (60 380 340 500).

Writes renders/qa_comparisons/mat_r7fix_sheet.png.
"""
import sys, os
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
PREV = ROOT / "renders/previews/materials"
QA = ROOT / "renders/previews/qa"
ALIGNED = ROOT / "renders/qa_comparisons/round05_cam01_aligned_vs_ref169.png"
OUT = ROOT / "renders/qa_comparisons/mat_r7fix_sheet.png"

REFL = (900, 760, 1020, 840)          # QA-05-4's reflection column, 1920x1080 hero grid
AERIAL = (60, 380, 340, 500)          # open lagoon water in the 1280x720 cam06 frame
BG, FG, DIM, GOOD, BAD = (20, 20, 22), (238, 238, 232), (150, 150, 145), (150, 220, 150), (235, 150, 140)
PAD, LABEL_H = 8, 46


def font(sz):
    for p in ("/System/Library/Fonts/SFNSMono.ttf", "/System/Library/Fonts/Menlo.ttc",
              "/System/Library/Fonts/Supplemental/Courier New.ttf"):
        if Path(p).exists():
            try:
                return ImageFont.truetype(p, sz)
            except Exception:
                pass
    return ImageFont.load_default()


F, FB = font(13), font(16)


def stats(c):
    m = c.reshape(-1, 3).mean(axis=0)
    r, g, b = m
    L = 0.2126 * r + 0.7152 * g + 0.0722 * b
    mx, mn = float(max(m)), float(min(m))
    d = mx - mn
    if d < 1e-6:
        h = 0.0
    elif mx == r:
        h = 60 * (((g - b) / d) % 6)
    elif mx == g:
        h = 60 * ((b - r) / d + 2)
    else:
        h = 60 * ((r - g) / d + 4)
    return L, h, float(d / mx if mx > 0 else 0.0), float(r - b)


def crop(path, box, panel=0, res=(1920, 1080), zoom=3):
    im = Image.open(path).convert("RGB")
    W, H = im.size
    n = max(1, round(W / res[0])) if W % res[0] == 0 and W // res[0] > 1 else 1
    if n > 1:
        im = im.crop((panel * (W // n), 0, (panel + 1) * (W // n), H))
    if im.size != res:
        im = im.resize(res, Image.BILINEAR)
    a = np.asarray(im).astype(np.float64)
    x0, y0, x1, y1 = box
    s = stats(a[y0:y1, x0:x1])
    c = im.crop(box)
    return c.resize((c.width * zoom, c.height * zoom), Image.NEAREST), s


ROW1 = [("shipped  gain 0.15  sheen 0", PREV / "r7w_s0_hero.png", 0),
        ("+ sheen 0.35", PREV / "r7w_s1_hero.png", 0),
        ("+ sheen 0.70", PREV / "r7w_s2_hero.png", 0),
        ("+ sheen 1.00", PREV / "r7w_s3_hero.png", 0),
        ("w6  gain 0.70 sheen 0.35", PREV / "r7w_w6_hero.png", 0),
        ("s4  sheen 1.0 warm tint", PREV / "r7w_s4_hero.png", 0),
        ("REF 169 (aligned)", ALIGNED, 1)]
ROW2 = [("Eevee  gain 0.15 SHIPPED", PREV / "r7fix_cam06_eevee_g0.15.png"),
        ("Eevee  gain 1.00 (r6)", PREV / "r7fix_cam06_eevee_g1.00.png"),
        ("Cycles gain 0.15 SHIPPED", PREV / "r7fix_cam06_cycles_g0.15.png"),
        ("Cycles gain 1.00 (r6)", PREV / "r7fix_cam06_cycles_g1.00.png"),
        ("QA round 05 aerial (Eevee)", QA / "round05_06_aerial.png")]

r1 = [(t, *crop(p, REFL, panel=k)) for t, p, k in ROW1 if p.exists()]
r2 = []
for t, p in ROW2:
    if not p.exists():
        continue
    im = Image.open(p).convert("RGB")
    a = np.asarray(im).astype(np.float64)
    x0, y0, x1, y1 = AERIAL
    s = stats(a[y0:y1, x0:x1])
    d = ImageDraw.Draw(im)
    d.rectangle([x0, y0, x1, y1], outline=(255, 60, 60), width=3)
    r2.append((t, im.resize((im.width // 2, im.height // 2), Image.LANCZOS), s))

w1 = sum(c.width for _, c, _ in r1) + PAD * (len(r1) + 1)
h1 = (r1[0][1].height if r1 else 0) + LABEL_H
w2 = sum(c.width for _, c, _ in r2) + PAD * (len(r2) + 1)
h2 = (r2[0][1].height if r2 else 0) + LABEL_H
W = max(w1, w2)
H = 30 + h1 + 34 + h2 + 30
sheet = Image.new("RGB", (W, H), BG)
d = ImageDraw.Draw(sheet)

d.text((PAD, 8), "QA-05-4 reflection column 900 760 1020 840 at 3x  --  100 % MAT_water_lagoon, mean 22.1 m  "
                 "(test: sat >= 0.25 AND the photo's warm hue 33.7)", font=FB, fill=FG)
x, y = PAD, 30
for t, c, s in r1:
    sheet.paste(c, (x, y))
    L, hu, sa, rb = s
    warm = 25.0 <= hu <= 60.0
    col = GOOD if (sa >= 0.25 and warm) else (BAD if sa >= 0.25 else DIM)
    d.text((x, y + c.height + 3), t[:34], font=F, fill=FG)
    d.text((x, y + c.height + 18), f"sat {sa:.3f}  hue {hu:5.1f}", font=F, fill=col)
    d.text((x, y + c.height + 31), f"R-B {rb:+6.1f}  lum {L:5.1f}", font=F, fill=DIM)
    x += c.width + PAD

y += h1 + 10
d.text((PAD, y), "QA-02-6 from above: CAM_qa_06_aerial, open-water box 60 380 340 500 (red)  --  the shipped gain "
                 "vs round 6's, both engines", font=FB, fill=FG)
y += 24
x = PAD
for t, c, s in r2:
    sheet.paste(c, (x, y))
    L, hu, sa, rb = s
    d.text((x, y + c.height + 3), t[:40], font=F, fill=FG)
    d.text((x, y + c.height + 18), f"lagoon lum {L:6.1f}  sat {sa:.3f}", font=F, fill=FG)
    x += c.width + PAD

OUT.parent.mkdir(parents=True, exist_ok=True)
sheet.save(OUT)
print(f"[sheet] {OUT} {sheet.size}")
