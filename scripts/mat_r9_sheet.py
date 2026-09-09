"""One composite for materials round 9.

    python3 scripts/mat_r9_sheet.py [--out renders/qa_comparisons/mat_r9_sheet.png]

Rows, all 1:1 on the 1920x1080 hero grid unless said otherwise:
  1  attic 1:1        before / after / ref 169 warped into the projector frame (arch_params.REF169_XF + the
                      per-course shift the ratio map itself uses), with lum / hue / sat / R-B burnt in
  2  entablature 1:1  the same three
  3  water            the reflection box and the near-water box, before / after / ref
  4  seams            cam02 and cam05, shipped frame and the projection's own difference x8 around zero grey
  5  engines          the same hero crop in Cycles and in Eevee (round-8 review carry 6)
"""
import sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import mat_projection as MP
from mat_r7_measure import load, stats

P = ROOT / "renders" / "previews" / "materials"
OUT = Path(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv else \
    ROOT / "renders" / "qa_comparisons" / "mat_r9_sheet.png"
BEFORE, AFTER = P / "r9_cycles_01_lagoon_hero.png", P / "r9b_cycles_01_lagoon_hero.png"
EEVEE = P / "r9b_eevee_01_lagoon_hero.png"
PANEL_W = 470
try:
    F = ImageFont.truetype("/System/Library/Fonts/Supplemental/Andale Mono.ttf", 13)
    FB = ImageFont.truetype("/System/Library/Fonts/Supplemental/Andale Mono.ttf", 16)
except Exception:
    F = FB = ImageFont.load_default()


def crop(a, bx, zoom=1):
    im = Image.fromarray(np.clip(a[bx[1]:bx[3], bx[0]:bx[2]], 0, 255).astype(np.uint8))
    if zoom != 1:
        im = im.resize((im.width * zoom, im.height * zoom), Image.NEAREST)
    return im


def label(s):
    st = stats(np.asarray(s).astype(np.float64)) if not isinstance(s, dict) else s
    return f"lum {st['lum']:.1f}  hue {st['hue']:.1f}  sat {st['sat']:.3f}  R-B {st['rb']:+.1f}"


def band(images, titles, notes, width=PANEL_W):
    h = max(im.height for im in images)
    row = Image.new("RGB", (width * len(images), h + 42), (18, 18, 20))
    d = ImageDraw.Draw(row)
    for i, (im, t, n) in enumerate(zip(images, titles, notes)):
        x = i * width + (width - im.width) // 2
        row.paste(im, (x, 22))
        d.text((i * width + 6, 4), t, font=FB, fill=(235, 235, 220))
        d.text((i * width + 6, h + 24), n, font=F, fill=(190, 200, 210))
    return row


a0, a1 = load(BEFORE), load(AFTER)
ae = load(EEVEE)
pho, _ = MP.warp_ref169()

rows = []
for name, bx, zoom in (("attic 900 222 1020 256", (900, 222, 1020, 256), 4),
                       ("entablature 900 262 1020 296", (900, 262, 1020, 296), 4)):
    ims = [crop(a0, bx, zoom), crop(a1, bx, zoom), crop(pho, bx, zoom)]
    rows.append(band(ims, [f"BEFORE  {name}", "AFTER (tint + projection)", "ref 169, registered"],
                     [label(a0[bx[1]:bx[3], bx[0]:bx[2]]), label(a1[bx[1]:bx[3], bx[0]:bx[2]]),
                      label(pho[bx[1]:bx[3], bx[0]:bx[2]])]))

wb = (900, 760, 1020, 840)
nb = (1150, 1000, 1450, 1050)
rows.append(band([crop(a0, wb, 3), crop(a1, wb, 3), crop(pho, wb, 3)],
                 ["BEFORE  reflection 900 760 1020 840", "AFTER  WATER_GLOSS_MIX 0.25", "ref 169"],
                 [label(a0[wb[1]:wb[3], wb[0]:wb[2]]), label(a1[wb[1]:wb[3], wb[0]:wb[2]]),
                  label(pho[wb[1]:wb[3], wb[0]:wb[2]])]))
rows.append(band([crop(a0, nb, 2), crop(a1, nb, 2), crop(pho, nb, 2)],
                 ["BEFORE  near water 1150 1000 1450 1050", "AFTER", "ref 169"],
                 [label(a0[nb[1]:nb[3], nb[0]:nb[2]]), label(a1[nb[1]:nb[3], nb[0]:nb[2]]),
                  label(pho[nb[1]:nb[3], nb[0]:nb[2]])]))

# --- seams: the shipped frame and the projection's own difference, x8 around mid grey
seam_ims, seam_t, seam_n = [], [], []
for cam, bx in (("02", (300, 40, 760, 300)), ("05", (400, 60, 860, 320))):
    off = np.asarray(Image.open(P / f"r9_seam_{cam}_off.png").convert("RGB")).astype(np.float64)
    on = np.asarray(Image.open(P / f"r9_seam_{cam}_on.png").convert("RGB")).astype(np.float64)
    d = (on - off) * 8.0 + 128.0
    seam_ims += [crop(on, bx), crop(d, bx)]
    g = 0.2126 * (on - off)[..., 0] + 0.7152 * (on - off)[..., 1] + 0.0722 * (on - off)[..., 2]
    seam_t += [f"cam{cam} shipped (Eevee)", f"cam{cam} projection difference x8"]
    seam_n += [f"crop {bx}", f"peak {np.abs(g).max():.1f} lum, blurred max step "
                              f"{max(np.abs(np.diff(g, axis=0)).max(), np.abs(np.diff(g, axis=1)).max()):.1f} raw"]
rows.append(band(seam_ims, seam_t, seam_n, width=PANEL_W))

cb = (760, 180, 1180, 420)
rows.append(band([crop(a1, cb), crop(ae, cb), crop(pho, cb)],
                 ["AFTER Cycles 64 spp", "AFTER Eevee 32 TAA (carry 6)", "ref 169"],
                 [label(a1[cb[1]:cb[3], cb[0]:cb[2]]), label(ae[cb[1]:cb[3], cb[0]:cb[2]]),
                  label(pho[cb[1]:cb[3], cb[0]:cb[2]])]))

W = max(r.width for r in rows)
H = sum(r.height for r in rows) + 34
sheet = Image.new("RGB", (W, H), (18, 18, 20))
d = ImageDraw.Draw(sheet)
d.text((8, 8), "MAT round 9 - ref-169 photo projection (weight 0.6, ratio map 1920x1080), photo-derived albedo "
               "tint (1.038, 1.013, 0.758), tinted grazing mirror 0.25, coffer rim chroma", font=FB,
       fill=(240, 235, 215))
y = 34
for r in rows:
    sheet.paste(r, (0, y))
    y += r.height
OUT.parent.mkdir(parents=True, exist_ok=True)
sheet.save(OUT)
print(f"[sheet] {OUT}  {sheet.width}x{sheet.height}")
