"""Round-8 materials comparison sheet -- QA-06-3 (the water blocker) and QA-06-8 (the coffered saucer).

    python3 scripts/mat_r8_sheet.py

Three rows, BEFORE / AFTER / REFERENCE at the same pixel scale.  BEFORE is the round-7 water rendered on THIS
master and THIS rig (sweep case w0, `mat_r8_sweep.py`), not round 6's frame, so the column isolates what round 8
changed from what lighting r14 changed.  Reference is ref 169 warped into the render frame (panel 1 of
round05_cam01_aligned_vs_ref169.png), i.e. the pixels QA measures.

  1. the reflection column, box 900 760 1020 840 at 1:1  -- QA-06-3's R-B test
  2. the whole near / mid water field, x 780-1560 y 700-1080
  3. cam04's coffered saucer (QA-06-8), round 06 vs round 08, Eevee

Writes renders/qa_comparisons/mat_r8_sheet.png.
"""
import sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
PREV = ROOT / "renders/previews/materials"
QC = ROOT / "renders/qa_comparisons"
OUT = QC / "mat_r8_sheet.png"
PANEL_W = 620
PAD, LABEL_H, BG, FG, DIM = 8, 46, (20, 20, 22), (238, 238, 232), (150, 150, 146)
REFL, WATER = (900, 760, 1020, 840), (780, 700, 1560, 1080)


def font(sz):
    for p in ("/System/Library/Fonts/SFNSMono.ttf", "/System/Library/Fonts/Menlo.ttc",
              "/System/Library/Fonts/Supplemental/Courier New.ttf"):
        if Path(p).exists():
            try:
                return ImageFont.truetype(p, sz)
            except Exception:
                pass
    return ImageFont.load_default()


def panels(path, unit=1920):
    im = Image.open(path).convert("RGB")
    n = max(1, round(im.width / unit)) if im.width % unit == 0 else 1
    w = im.width // n
    return [im.crop((i * w, 0, (i + 1) * w, im.height)) for i in range(n)]


def stat(im, box):
    a = np.asarray(im.crop(box), dtype=np.float64)
    m = a.reshape(-1, 3).mean(axis=0)
    r, g, b = m
    L = 0.2126 * r + 0.7152 * g + 0.0722 * b
    mx, mn = float(max(m)), float(min(m))
    d = mx - mn
    h = 0.0 if d < 1e-6 else (60 * (((g - b) / d) % 6) if mx == r else
                              (60 * ((b - r) / d + 2) if mx == g else 60 * ((r - g) / d + 4)))
    gg = 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]
    return dict(lum=L, hue=h, sat=(d / mx if mx else 0.0), rb=r - b, std=float(gg.std()))


def fit(im, w=PANEL_W):
    return im.resize((w, max(1, round(im.height * w / im.width))), Image.LANCZOS)


def row(draw, y, images, captions, heads):
    x = PAD
    for im, cap, head in zip(images, captions, heads):
        draw.text((x, y), head, font=font(15), fill=FG)
        yy = y + 20
        SHEET.paste(im, (x, yy))
        for i, line in enumerate(cap):
            draw.text((x, yy + im.height + 3 + i * 15), line, font=font(12), fill=DIM if i else FG)
        x += PANEL_W + PAD
    return y + 20 + images[0].height + 3 + LABEL_H


before = panels(PREV / "r8w_w0_hero.png")[0]
after = panels(PREV / "r8_cycles_01_lagoon_hero.png")[0]
ref = panels(QC / "round05_cam01_aligned_vs_ref169.png")[1]
c4_before = panels(QC / "round06_cam04.png", unit=1280)[0]
c4_after = Image.open(PREV / "r8_eevee_04_rotunda_ceiling.png").convert("RGB")

r1 = [fit(im.crop(REFL).resize((480, 320), Image.NEAREST)) for im in (before, after, ref)]
r2 = [fit(im.crop(WATER)) for im in (before, after, ref)]
CF = (0.400, 0.400, 0.200, 0.200)
c4box = lambda im: (int(CF[0] * im.width), int(CF[1] * im.height),
                    int((CF[0] + CF[2]) * im.width), int((CF[1] + CF[3]) * im.height))
REF083 = Path("/Users/dk/Projects/3d render blender 3rd attempt building"
              "/reference/photos/raw/ref_083_rotunda_San_Francisco_40326830584.jpg")
ref083 = Image.open(REF083).convert("RGB")
_h = min(ref083.height, int(ref083.width * c4_after.height / c4_after.width))
ref083 = ref083.crop(((ref083.width - int(_h * c4_after.width / c4_after.height)) // 2,
                      (ref083.height - _h) // 2,
                      (ref083.width + int(_h * c4_after.width / c4_after.height)) // 2,
                      (ref083.height + _h) // 2))
r3 = [fit(c4_before), fit(c4_after), fit(ref083)]

H = 30 + sum(im.height + 20 + LABEL_H for im in (r1[0], r2[0], r3[0])) + 3 * PAD
SHEET = Image.new("RGB", (3 * PANEL_W + 4 * PAD, H), BG)
d = ImageDraw.Draw(SHEET)
d.text((PAD, 6), "MATERIALS ROUND 8  --  QA-06-3 water (blocker) and QA-06-8 coffers.  BEFORE = round-7 water on "
                 "THIS master and lighting r14 (sweep case w0).  Cycles 1920x1080 / 64 spp.", font=font(15), fill=FG)


def cap(im, box, tag):
    s = stat(im, box)
    return [f"{tag}", f"lum {s['lum']:.1f}  hue {s['hue']:.1f}  sat {s['sat']:.3f}",
            f"R-B {s['rb']:+.1f}   std {s['std']:.1f}"]


y = 30
y = row(d, y, r1, [cap(before, REFL, "round-7 water, r14 rig"), cap(after, REFL, "round-8 water SHIPPED"),
                   cap(ref, REFL, "ref 169, aligned")],
        ["1  reflection column 900 760 1020 840 at 4x  (test: R-B >= +30, hue 25-45, lum 124-208)", "", ""])
y = row(d, y, r2, [cap(before, (1150, 1000, 1450, 1050), "round-7 water: near box"),
                   cap(after, (1150, 1000, 1450, 1050), "round-8 water: near box"),
                   cap(ref, (1150, 1000, 1450, 1050), "ref 169: near box")],
        ["2  the water field x 780-1560 y 700-1080  (near-water box quoted: sat 0.22-0.32, hue 185-200)", "", ""])
y = row(d, y, r3, [cap(c4_before, c4box(c4_before), "round 06 cam04 (Eevee panel)"),
                   cap(c4_after, c4box(c4_after), "round 08 cam04 (Eevee)"),
                   ["ref 083 (not frame-aligned; read, not pixel-compare)",
                    "QA's reading of ref 083: coffer field sat 0.427",
                    "coffer / own sky 0.35-0.55: held at 0.357"]],
        ["3  cam04 coffered saucer, QA-06-8 (coffer field box = central 20 % of the frame)", "", ""])
SHEET.save(OUT)
print(f"[r8sheet] {OUT}  {SHEET.size}")
