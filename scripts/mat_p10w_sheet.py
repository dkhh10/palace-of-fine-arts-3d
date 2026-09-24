"""Phase 10 r2 comparison sheet (plain python): renders/qa_comparisons/mat_p10w_sheet.png

    /opt/homebrew/bin/python3.13 scripts/mat_p10w_sheet.py <before_hero> <after_hero> <before_cam05> <after_cam05> \
        <before_cam06> <after_cam06> [out.png]

Rows (100 % crops, before | after | ref 169, pixel-registered on the 1920x1080 hero frame; the numbers are the box's
lum / hue / sat / R-B from scripts/mat_p10w_measure.py): reflection column, open water, conifer mass (box 1s),
willow box (box 2), column shafts; then cam05 and cam06 before | after at 960 px wide (no photo at those stations).
"""
import sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mat_p10w_measure as M        # noqa: E402
from mat_r7_measure import stats, BOXES, COL_BOX   # noqa: E402
import env_p10_boxes as EB          # noqa: E402

ROWS = [  # name, crop window, measured box, reference frame ("s" stone / "f" foliage)
    ("reflection column", (840, 740, 1080, 860), BOXES["water_refl"], "s"),
    ("open water (near + ripples)", (1150, 960, 1450, 1060), BOXES["near_water_sky"], "s"),
    ("conifer mass (box 1s)", tuple(int(v) for v in (0.655 * 1920, 0.28 * 1080, 0.74 * 1920, 0.44 * 1080)),
     tuple(int(v) for v in (0.655 * 1920, 0.28 * 1080, 0.74 * 1920, 0.44 * 1080)), "f"),
    ("willow box (box 2)", tuple(int(v) for v in (0.39 * 1920, 0.45 * 1080, 0.47 * 1920, 0.62 * 1080)),
     tuple(int(v) for v in (0.39 * 1920, 0.45 * 1080, 0.47 * 1920, 0.62 * 1080)), "f"),
    ("column shafts", (1000, 300, 1240, 470), COL_BOX, "s"),
]
TW = 480


def tile(a, win, text):
    x0, y0, x1, y1 = win
    c = Image.fromarray(np.clip(a[y0:y1, x0:x1], 0, 255).astype(np.uint8))
    c = c.resize((TW, int(TW * (y1 - y0) / (x1 - x0))), Image.Resampling.NEAREST)
    d = ImageDraw.Draw(c)
    d.rectangle((0, 0, TW, 14), fill=(0, 0, 0))
    d.text((3, 1), text, fill=(255, 255, 0))
    return c


def main(bh, ah, b5, a5, b6, a6, out):
    B, A = M.load(bh), M.load(ah)
    RS, RF = M.ref_stone(), M.ref_foliage()
    rows = []
    for name, win, bx, rk in ROWS:
        R = RS if rk == "s" else RF
        tiles = []
        for tag, a in (("before", B), ("after", A), ("ref 169", R)):
            if name == "column shafts":
                s = M.columns(a)
            else:
                x0, y0, x1, y1 = bx
                s = stats(a[y0:y1, x0:x1])
            extra = ""
            if name == "reflection column":
                t = M.texture(a)
                extra = f" Lx{t['Lx']:.1f} asp{t['aspect']:.1f} an{t['aniso']:.2f} cv{t['cv']:.2f}"
            if rk == "f":
                f = M.foliage(a)["con" if "conifer" in name else "wil"]
                extra = f" luma{f['luma']:.0f} B/G{f['bg']:.2f} dark{f['dark']:.0f}%"
            tiles.append(tile(a, win, f"{name} {tag}: L{s['lum']:.0f} h{s['hue']:.0f} s{s['sat']:.2f} RB{s['rb']:+.0f}{extra}"))
        h = max(t.height for t in tiles)
        row = Image.new("RGB", (3 * TW, h), (18, 18, 18))
        for i, t in enumerate(tiles):
            row.paste(t, (i * TW, 0))
        rows.append(row)
    for cam, (pb, pa) in (("cam05", (b5, a5)), ("cam06", (b6, a6))):
        ims = []
        for tag, p in (("before", pb), ("after", pa)):
            im = Image.open(p).convert("RGB").resize((720, 405), Image.Resampling.LANCZOS)
            ImageDraw.Draw(im).text((4, 4), f"{cam} {tag} (1280x720 32 spp)", fill=(255, 255, 0))
            ims.append(im)
        row = Image.new("RGB", (3 * TW, 405), (18, 18, 18))
        row.paste(ims[0], (0, 0)); row.paste(ims[1], (720, 0))
        rows.append(row)
    H = sum(r.height for r in rows) + 4 * len(rows)
    sheet = Image.new("RGB", (3 * TW, H), (18, 18, 18))
    y = 0
    for r in rows:
        sheet.paste(r, (0, y)); y += r.height + 4
    sheet.save(out)
    print(f"[p10w sheet] {out} {sheet.size}")


if __name__ == "__main__":
    a = sys.argv[1:]
    out = a[6] if len(a) > 6 else str(M.EB.ROOT / "renders" / "qa_comparisons" / "mat_p10w_sheet.png")
    main(*a[:6], out)
