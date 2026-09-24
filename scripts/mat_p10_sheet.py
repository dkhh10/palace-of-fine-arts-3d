"""Phase 10 r1, step 9 -- the comparison sheet: 100 % crops before / after / ref 169 with box numbers, cam02 / cam03
seam crops, and the text of the hold table (plain python: numpy + PIL).

    python3 scripts/mat_p10_sheet.py <before_hero> <after_hero> <before_cam02> <after_cam02> <before_cam03> \
        <after_cam03> <table.txt>  -> renders/qa_comparisons/mat_p10_sheet.png
"""
import sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0, str(Path(__file__).resolve().parent))
from mat_r7_measure import load, stats, COL_BOX
import mat_projection as MP

CROPS = {  # 1920x1080 hero frame, 100 % (240 x 80..120 px, read off the before hero)
    "attic": (840, 170, 1080, 270), "drum": (840, 90, 1080, 170), "column shaft": (1000, 360, 1240, 480),
    "entablature": (840, 290, 1080, 350), "arch": (860, 360, 1100, 470)}


def crop(a, b):
    x0, y0, x1, y1 = b
    return a[y0:y1, x0:x1]


def label(img, text):
    d = ImageDraw.Draw(img); d.rectangle((0, 0, img.width, 14), fill=(0, 0, 0)); d.text((3, 1), text, fill=(255, 255, 0))
    return img


def main(bh, ah, b2, a2, b3, a3, table):
    B, A = load(bh), load(ah)
    R, inb = MP.warp_ref169()
    rows = []
    for name, bx in CROPS.items():
        tiles = []
        for tag, a in (("before", B), ("after", A), ("ref169", R)):
            c = crop(a, bx); s = stats(c)
            im = Image.fromarray(np.clip(c, 0, 255).astype(np.uint8)).resize((480, int(480 * c.shape[0] / c.shape[1])), Image.NEAREST)
            tiles.append(label(im, f"{name} {tag}: L{s['lum']:.0f} h{s['hue']:.0f} s{s['sat']:.2f} aniso{s['aniso']:.2f}"))
        h = max(t.height for t in tiles)
        row = Image.new("RGB", (1440, h)); [row.paste(t, (i * 480, 0)) for i, t in enumerate(tiles)]
        rows.append(row)
    for tag, (pb, pa) in (("cam02", (b2, a2)), ("cam03", (b3, a3))):
        b = np.asarray(Image.open(pb).convert("RGB")); a = np.asarray(Image.open(pa).convert("RGB"))
        d = np.abs(a.astype(float) - b.astype(float)).mean(-1)
        ys, xs = np.nonzero(d > 3)
        cy, cx = (int(np.median(ys)), int(np.median(xs))) if len(ys) else (360, 640)
        y0 = int(np.clip(cy - 120, 0, b.shape[0] - 240)); x0 = int(np.clip(cx - 180, 0, b.shape[1] - 360))
        tiles = [label(Image.fromarray(x[y0:y0 + 240, x0:x0 + 360]).resize((480, 320), Image.NEAREST), f"{tag} {t} (100 %, x{x0} y{y0})")
                 for x, t in ((b, "before"), (a, "after"))]
        dd = np.clip(d[y0:y0 + 240, x0:x0 + 360] * 8, 0, 255).astype(np.uint8)
        tiles.append(label(Image.fromarray(dd).convert("RGB").resize((480, 320), Image.NEAREST), f"{tag} |after-before| x8"))
        row = Image.new("RGB", (1440, 320)); [row.paste(t, (i * 480, 0)) for i, t in enumerate(tiles)]
        rows.append(row)
    txt = Path(table).read_text().splitlines()
    trow = Image.new("RGB", (1440, 14 * len(txt) + 10)); dr = ImageDraw.Draw(trow)
    for i, line in enumerate(txt):
        dr.text((6, 4 + 14 * i), line, fill=(230, 230, 230))
    rows.append(trow)
    H = sum(r.height for r in rows)
    sheet = Image.new("RGB", (1440, H)); y = 0
    for r in rows:
        sheet.paste(r, (0, y)); y += r.height
    out = Path(__file__).resolve().parents[1] / "renders" / "qa_comparisons" / "mat_p10_sheet.png"
    sheet.save(out)
    print(f"[sheet] {out} {sheet.size}")


if __name__ == "__main__":
    main(*sys.argv[1:8])
