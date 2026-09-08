"""Round-6 materials comparison sheet (QA-04-3 / -5 / -7 / -8).

    python3 scripts/mat_r6_sheet.py

Five rows, each BEFORE (round-5 library) / AFTER (round-6 library) / REFERENCE, all three at the same pixel scale.

  1. attic + entablature at 1:1        -- the QA-04-3 blocker box, with the luminance std-dev on the panel
  2. waterline                          -- QA-04-3c damp / algae band
  3. columns                            -- QA-04-5 chroma, with hue / saturation / mask luminance
  4. coffered saucer                    -- QA-04-7 rib vs panel and the in-coffer gradient (ref 083)
  5. near water                         -- QA-04-8 hue and the sunlit-stone reflection

Before and after are two library versions rendered on ONE master with `mat_scene_check.py --swap`, so the pair
differs by the library and by nothing else. The reference column is QA's ref 169 warped into the render frame
(panel 1 of renders/qa_comparisons/round04_cam01_aligned_vs_ref169.png), i.e. the same pixels QA measures.

Writes renders/qa_comparisons/mat_r6_sheet.png.
"""
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
REFDIR = Path("/Users/dk/Projects/3d render blender 3rd attempt building/reference/photos")
PREV = ROOT / "renders/previews/materials"
ALIGNED = ROOT / "renders/qa_comparisons/round04_cam01_aligned_vs_ref169.png"
OUT = ROOT / "renders/qa_comparisons/mat_r6_sheet.png"

PANEL_W = 620
PAD, LABEL_H, BG, FG, DIM = 8, 34, (20, 20, 22), (238, 238, 232), (155, 155, 150)


def font(sz):
    for p in ("/System/Library/Fonts/SFNSMono.ttf", "/System/Library/Fonts/Menlo.ttc",
              "/System/Library/Fonts/Supplemental/Courier New.ttf"):
        if Path(p).exists():
            try:
                return ImageFont.truetype(p, sz)
            except Exception:
                pass
    return ImageFont.load_default()


def panels(path):
    im = Image.open(path).convert("RGB")
    n = max(1, round(im.width / 1920)) if im.width % 1920 == 0 else 1
    w = im.width // n
    return [im.crop((i * w, 0, (i + 1) * w, im.height)) for i in range(n)]


def lum(a):
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def px_hsv(a):
    mx = a.max(axis=-1); d = mx - a.min(axis=-1)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    dd = np.where(d == 0, 1, d)
    i = a.argmax(axis=-1)
    h = np.where(i == 0, 60 * (((g - b) / dd) % 6), np.where(i == 1, 60 * ((b - r) / dd + 2), 60 * ((r - g) / dd + 4)))
    return np.where(d > 1e-6, h, 0.0), np.where(mx > 0, d / np.where(mx == 0, 1, mx), 0.0)


def stat_std(im, box):
    a = np.asarray(im.crop(box), dtype=np.float32)
    return f"std {lum(a).std():.1f}"


def stat_col(im, box=(680, 280, 1240, 470)):
    a = np.asarray(im.crop(box), dtype=np.float32)
    h, s = px_hsv(a)
    m = (h < 32) & (s > 0.30)
    if m.sum() < 50:
        return "no mask"
    sel = a[m]
    mm = sel.mean(axis=0)
    return f"lum {lum(mm):.0f} hue {px_hsv(mm.reshape(1, 1, 3))[0][0, 0]:.1f} sat {px_hsv(mm.reshape(1, 1, 3))[1][0, 0]:.3f}"


def stat_rgb(im, box):
    a = np.asarray(im.crop(box), dtype=np.float32)
    mm = a.reshape(-1, 3).mean(axis=0)
    h, s = px_hsv(mm.reshape(1, 1, 3))
    return f"lum {lum(mm):.0f} hue {h[0, 0]:.1f} sat {s[0, 0]:.3f}"


def crop(im, box, w=PANEL_W):
    c = im.crop(box)
    return c.resize((w, round(c.height * w / c.width)), Image.LANCZOS)


def main():
    before = panels(PREV / "r6before_scene_hero.png")[0]
    after = panels(PREV / "r6after_scene_hero.png")[0]
    ref = panels(ALIGNED)[1]

    ceil_b = Image.open(PREV / "r6before_scene_ceiling.png").convert("RGB")
    ceil_a = Image.open(PREV / "r6after_scene_ceiling.png").convert("RGB")
    ceil_r = Image.open(REFDIR / "raw/ref_083_rotunda_San_Francisco_40326830584.jpg").convert("RGB")

    STONE = (860, 200, 1080, 310)
    WATERL = (700, 545, 1170, 780)
    COLS = (680, 265, 1240, 480)
    NEARW = (860, 700, 1560, 1060)

    rows = [
        ("QA-04-3  attic + entablature at 1:1 (hero 860-1080 x 200-310)",
         [(crop(before, STONE), "BEFORE r5 lib  " + stat_std(before, (900, 222, 1020, 256)) + " attic / "
           + stat_std(before, (900, 262, 1020, 296)) + " entab"),
          (crop(after, STONE), "AFTER r6 lib   " + stat_std(after, (900, 222, 1020, 256)) + " attic / "
           + stat_std(after, (900, 262, 1020, 296)) + " entab"),
          (crop(ref, STONE), "REF 169        " + stat_std(ref, (900, 222, 1020, 256)) + " attic / "
           + stat_std(ref, (900, 262, 1020, 296)) + " entab")]),
        ("QA-04-3c waterline: damp / algae band",
         [(crop(before, WATERL), "BEFORE"), (crop(after, WATERL), "AFTER"), (crop(ref, WATERL), "REF 169")]),
        ("QA-04-5  columns (mask hue<32 sat>0.30)",
         [(crop(before, COLS), "BEFORE  " + stat_col(before)), (crop(after, COLS), "AFTER   " + stat_col(after)),
          (crop(ref, COLS), "REF 169 " + stat_col(ref))]),
        ("QA-04-7  coffered saucer: rib vs panel, in-coffer gradient",
         [(crop(ceil_b, (0, 0, ceil_b.width, ceil_b.height)), "BEFORE (ribs share the panel material)"),
          (crop(ceil_a, (0, 0, ceil_a.width, ceil_a.height)), "AFTER (MAT_plaster_ceiling_rib)"),
          (crop(ceil_r, (0, 0, ceil_r.width, ceil_r.height)), "REF 083")]),
        ("QA-04-8  near water: hue and the sunlit-stone reflection",
         [(crop(before, NEARW), "BEFORE " + stat_rgb(before, (1150, 1000, 1450, 1050)) + " | refl "
           + stat_rgb(before, (900, 760, 1020, 840))),
          (crop(after, NEARW), "AFTER  " + stat_rgb(after, (1150, 1000, 1450, 1050)) + " | refl "
           + stat_rgb(after, (900, 760, 1020, 840))),
          (crop(ref, NEARW), "REF169 " + stat_rgb(ref, (1150, 1000, 1450, 1050)) + " | refl "
           + stat_rgb(ref, (900, 760, 1020, 840)))]),
    ]

    f_title, f_lab = font(15), font(12)
    W = 3 * PANEL_W + 4 * PAD
    heights = [max(im.height for im, _ in r[1]) + LABEL_H + 22 for r in rows]
    H = sum(heights) + PAD * (len(rows) + 1)
    sheet = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(sheet)
    y = PAD
    for (title, cells), rh in zip(rows, heights):
        d.text((PAD, y), title, font=f_title, fill=FG)
        yy = y + 20
        for i, (im, lab) in enumerate(cells):
            x = PAD + i * (PANEL_W + PAD)
            d.text((x, yy), lab, font=f_lab, fill=DIM)
            sheet.paste(im, (x, yy + 14))
        y += rh + PAD
    OUT.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(OUT)
    print("[r6 sheet] ->", OUT, sheet.size)


if __name__ == "__main__":
    main()
