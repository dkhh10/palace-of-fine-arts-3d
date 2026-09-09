"""Round-7 materials comparison sheet (QA-05-2 blocker, QA-05-4 water, QA-05-10 shore, ENV's paving).

    python3 scripts/mat_r7_sheet.py [--after r7f]

Four rows, BEFORE (the round-6 library as merged, on the same master and the same lighting r12 rig) / AFTER (the
round-7 library) / REFERENCE, all three at the same pixel scale:

  1. attic + entablature at 1:1     -- the QA-05-2 boxes with lum / sat / std and the streak ANISOTROPY
  2. near water + the building's reflection (QA-05-4)
  3. cam03 colonnade walk           -- MAT_paving_stone / _worn against ref 128
  4. cam05 at 115 m                 -- the distance test (QA-05-12) against ref 063

Reference column: ref 169 warped into the render frame (panel 1 of round05_cam01_aligned_vs_ref169.png), i.e. the
same pixels QA measures; rows 3 and 4 use the raw canonical photos, which are not frame-aligned, so they are shown
for read, not for pixel comparison.

Writes renders/qa_comparisons/mat_r7_sheet.png.
"""
import sys, os
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
# Same resolution as common.REFERENCE_DIR (common.py:14-16), re-stated instead of imported because this script runs
# under plain python3 and common.py imports bpy at module level.  The 175 MB of photos live only in the MAIN
# checkout; a worktree has none, so the path is absolute by design and $PFA_REFERENCE_DIR overrides it.
MAIN_ROOT = Path("/Users/dk/Projects/3d render blender 3rd attempt building")
REFDIR = Path(os.environ.get("PFA_REFERENCE_DIR", str(MAIN_ROOT / "reference"))) / "photos"
PREV = ROOT / "renders/previews/materials"
ALIGNED = ROOT / "renders/qa_comparisons/round05_cam01_aligned_vs_ref169.png"
OUT = ROOT / "renders/qa_comparisons/mat_r7_sheet.png"

AFTER = sys.argv[sys.argv.index("--after") + 1] if "--after" in sys.argv else "r7f"   # r7f = the shipped library
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


def hs(m):
    mx, mn = float(max(m)), float(min(m))
    d = mx - mn
    r, g, b = m
    if d < 1e-6:
        h = 0.0
    elif mx == r:
        h = 60 * (((g - b) / d) % 6)
    elif mx == g:
        h = 60 * ((b - r) / d + 2)
    else:
        h = 60 * ((r - g) / d + 4)
    return h, (d / mx if mx else 0.0)


def stone_stat(im, box):
    a = np.asarray(im.crop(box), dtype=np.float32)
    g = lum(a)
    m = a.reshape(-1, 3).mean(axis=0)
    h, s = hs(m)
    an = g.mean(axis=0).std() / max(g.mean(axis=1).std(), 1e-6)
    return f"lum {lum(m):.0f} sat {s:.3f} std {g.std():.1f} aniso {an:.2f}"


def water_stat(im):
    a = np.asarray(im.crop((1150, 1000, 1450, 1050)), dtype=np.float32).reshape(-1, 3).mean(axis=0)
    b = np.asarray(im.crop((900, 760, 1020, 840)), dtype=np.float32).reshape(-1, 3).mean(axis=0)
    ha, sa = hs(a)
    hb, sb = hs(b)
    return f"near hue {ha:.0f} sat {sa:.3f} | refl hue {hb:.0f} sat {sb:.3f} R-B {b[0] - b[2]:+.0f}"


def band_stat(im, box):
    a = np.asarray(im.crop(box), dtype=np.float32)
    g = lum(a)
    m = a.reshape(-1, 3).mean(axis=0)
    return f"lum {lum(m):.0f} std {g.std():.1f}"


def crop(im, box, w=PANEL_W):
    c = im.crop(box)
    return c.resize((w, max(1, round(c.height * w / c.width))), Image.LANCZOS)


def full(im, aspect=None, w=PANEL_W):
    """The raw canonical photos are not frame-aligned; centre-crop them to the render panel's aspect so the row
    reads as three comparable strips instead of one tall photo beside two letterboxes."""
    if aspect:
        h = min(im.height, int(im.width / aspect))
        ww = min(im.width, int(h * aspect))
        x0, y0 = (im.width - ww) // 2, (im.height - h) // 2
        im = im.crop((x0, y0, x0 + ww, y0 + h))
    return crop(im, (0, 0, im.width, im.height), w)


def main():
    before = panels(PREV / "r7base_scene_hero.png")[0]
    after = panels(PREV / f"{AFTER}_scene_hero.png")[0]
    ref = panels(ALIGNED)[1]
    ATTIC, WATER = (860, 200, 1080, 310), (860, 700, 1560, 1060)

    rows = [("QA-05-2  attic + entablature at 1:1 (hero 860-1080 x 200-310); numbers are QA's attic box 900 222 1020 256",
             [(crop(before, ATTIC), "BEFORE r6 lib  " + stone_stat(before, (900, 222, 1020, 256))),
              (crop(after, ATTIC), f"AFTER {AFTER:8s} " + stone_stat(after, (900, 222, 1020, 256))),
              (crop(ref, ATTIC), "REF 169        " + stone_stat(ref, (900, 222, 1020, 256)))]),
            ("QA-05-4  near water and the building's reflection",
             [(crop(before, WATER), "BEFORE " + water_stat(before)),
              (crop(after, WATER), "AFTER  " + water_stat(after)),
              (crop(ref, WATER), "REF169 " + water_stat(ref))])]

    for tag, camfile, refphoto, box, title in (
            ("cam03", "scene_cam03.png", "raw/ref_128_main_Corinthian_columns_and_rotunda_Palace_of_Fine_Arts.jpg",
             (0, 380, 1280, 720), "ENV hand-off: colonnade walk, MAT_paving_stone / _worn (lower frame)"),
            ("cam05", "scene_cam05.png", "raw/ref_063_rotunda_Palace_of_Fine_Arts_View_of_Rotunda_from_south_eas.jpg",
             (300, 150, 980, 260), "QA-05-12: the stone band at 115 m (cam05)")):
        pb, pa = PREV / f"r7base_{camfile}", PREV / f"{AFTER}_{camfile}"
        if not (pb.exists() and pa.exists()):
            continue
        b, a = Image.open(pb).convert("RGB"), Image.open(pa).convert("RGB")
        cells = [(crop(b, box), "BEFORE r6 lib  " + band_stat(b, box)),
                 (crop(a, box), f"AFTER {AFTER:8s} " + band_stat(a, box))]
        rp = REFDIR / refphoto
        cands = [rp] if rp.exists() else sorted(REFDIR.glob("raw/ref_%s_*" % refphoto.split("_")[1]))
        if cands:
            r = Image.open(cands[0]).convert("RGB")
            asp = (box[2] - box[0]) / float(box[3] - box[1])
            cells.append((full(r, asp), "REF " + cands[0].name[:28] + " (not frame-aligned)"))
        rows.append((title, cells))

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
    print("[r7 sheet] ->", OUT, sheet.size)


if __name__ == "__main__":
    main()
