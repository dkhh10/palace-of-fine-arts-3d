#!/usr/bin/env python3
"""Entablature shadow-band measurement (QA-05-6). python3 + numpy + PIL only; never opens Blender.

The QA metric: over a box on the 1920x1080 hero, `row std` = std-dev over rows of the per-row mean luminance
(hard horizontal shadow bands make it large), and `texture std` = std-dev of every pixel luminance in the box.
QA round 05: render 20.9 / photo (ref 169, raw, mapped with S=1.3108 dx=-291.8 dy=-124.6) 53.6 on box
900 262 1020 296.  Acceptance for QA-05-6: row std >= 0.75 * photo = 40.2.

  python3 scripts/arch_entab_measure.py stats IMG [--box x0 y0 x1 y1] [--ref PHOTO] [--transform S DX DY]
  python3 scripts/arch_entab_measure.py profile IMG --box ... [--ref ...] [--transform ...]
        prints the per-row mean luminance of both, side by side, so the bands can be located row by row
  python3 scripts/arch_entab_measure.py strip --out OUT.png --panel LABEL IMG x0 y0 x1 y1 [--panel ...] [--zoom N]
        magnified crops stacked vertically with the row profile drawn as a curve and the two stds burnt in
"""
import argparse
import numpy as np
from PIL import Image, ImageDraw, ImageFont

FONT = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
HERO_BOX = (900, 262, 1020, 296)
REF169 = "reference/photos/raw/ref_169_main_Palace_of_Fine_Arts_16794p.jpg"
# qa_silhouette align, round 05: photo px * S + D = render px
REF169_XF = (1.3108, -291.8, -124.6)


def lum(path):
    a = np.asarray(Image.open(path).convert("RGB")).astype(np.float32)
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def map_box(box, xf):
    s, dx, dy = xf
    return tuple(int(round((v - d) / s)) for v, d in zip(box, (dx, dy, dx, dy)))


def measure(L, box):
    x0, y0, x1, y1 = box
    sub = L[y0:y1, x0:x1]
    rows = sub.mean(axis=1)
    cols = sub.mean(axis=0)
    return dict(row_std=float(rows.std()), col_std=float(cols.std()), tex_std=float(sub.std()),
                mean=float(sub.mean()), rows=rows, n=sub.shape)


def resample_rows(rows, n):
    """resample a row profile to n samples so photo and render profiles line up row for row"""
    x = np.linspace(0, 1, len(rows))
    return np.interp(np.linspace(0, 1, n), x, rows)


def cmd_stats(a):
    box = tuple(a.box) if a.box else HERO_BOX
    r = measure(lum(a.img), box)
    print(f"RENDER {a.img}")
    print(f"  box {box} {r['n']}  mean {r['mean']:.1f}  row std {r['row_std']:.1f}  "
          f"col std {r['col_std']:.1f}  tex std {r['tex_std']:.1f}")
    if a.ref:
        xf = tuple(a.transform) if a.transform else REF169_XF
        rb = map_box(box, xf)
        p = measure(lum(a.ref), rb)
        print(f"PHOTO  {a.ref}")
        print(f"  box {rb} {p['n']}  mean {p['mean']:.1f}  row std {p['row_std']:.1f}  "
              f"col std {p['col_std']:.1f}  tex std {p['tex_std']:.1f}")
        print(f"RATIO  row std {r['row_std'] / p['row_std']:.3f} (need >= 0.75)   "
              f"tex std {r['tex_std'] / p['tex_std']:.3f} (need >= 0.60)")
    return r


def cmd_profile(a):
    box = tuple(a.box) if a.box else HERO_BOX
    r = measure(lum(a.img), box)
    ref = None
    if a.ref:
        xf = tuple(a.transform) if a.transform else REF169_XF
        ref = measure(lum(a.ref), map_box(box, xf))
        pr = resample_rows(ref["rows"], len(r["rows"]))
    print(f"{'y':>5} {'render':>8} {'photo':>8}")
    for i, v in enumerate(r["rows"]):
        s = f"{box[1] + i:5d} {v:8.1f}"
        if ref is not None:
            s += f" {pr[i]:8.1f}"
        print(s)
    cmd_stats(a)


def cmd_strip(a):
    font = ImageFont.truetype(FONT, 20)
    panels = []
    W = a.width
    for label, path, x0, y0, x1, y1 in a.panel:
        box = (int(x0), int(y0), int(x1), int(y1))
        L = lum(path)
        m = measure(L, box)
        crop = Image.open(path).convert("RGB").crop(box)
        h = int(crop.height * W / crop.width)
        crop = crop.resize((W, h), Image.NEAREST)
        p = Image.new("RGB", (W + 260, h + 30), (18, 18, 20))
        p.paste(crop, (0, 30))
        d = ImageDraw.Draw(p)
        d.text((4, 4), f"{label}  box {box}  row std {m['row_std']:.1f}  tex std {m['tex_std']:.1f}",
               font=font, fill=(255, 220, 120))
        # row profile curve on the right, 0..255 mapped to 250 px
        rows = m["rows"]
        pts = [(W + 5 + rows[int(i * len(rows) / h)] * 250 / 255.0, 30 + i) for i in range(h)]
        d.line(pts, fill=(120, 230, 255), width=2)
        panels.append(p)
    Wd = max(p.width for p in panels)
    sheet = Image.new("RGB", (Wd, sum(p.height + 6 for p in panels)), (18, 18, 20))
    y = 0
    for p in panels:
        sheet.paste(p, (0, y)); y += p.height + 6
    sheet.save(a.out)
    print("wrote", a.out, sheet.size)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("stats", "profile"):
        s = sub.add_parser(name)
        s.add_argument("img")
        s.add_argument("--box", type=int, nargs=4)
        s.add_argument("--ref", default=None)
        s.add_argument("--transform", type=float, nargs=3, default=None)
    s = sub.add_parser("strip")
    s.add_argument("--out", required=True)
    s.add_argument("--width", type=int, default=760)
    s.add_argument("--panel", action="append", nargs=6, required=True,
                   metavar=("LABEL", "IMG", "X0", "Y0", "X1", "Y1"))
    a = ap.parse_args()
    {"stats": cmd_stats, "profile": cmd_profile, "strip": cmd_strip}[a.cmd](a)


if __name__ == "__main__":
    main()
