#!/usr/bin/env python3
"""ARCH polish round 4 composite for QA-05-6 (python3 + numpy + PIL; no Blender).

    python3 scripts/arch_p4r4_sheet.py --before B.png --after A.png --ref REF.jpg --out SHEET.png
                                       [--box 900 262 1020 296] [--wide 860 200 1060 330] [--sil sil.json]

Three crops of the rotunda entablature at one on-screen scale -- round-05 hero (before), this round (after) and
ref 169 mapped through the round-05 alignment (S 1.3108, dx -291.8, dy -124.6) -- each with its row-profile curve
and QA's two numbers burnt in, over a text panel carrying the acceptance arithmetic and the cam01 silhouette check.
"""
import argparse, json, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

FONT = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
MONO = "/System/Library/Fonts/Menlo.ttc"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import arch_params as P

XF = P.REF169_XF                       # ref 169 px * S + D = render px (qa_silhouette align, round 05)


def lum(path):
    a = np.asarray(Image.open(path).convert("RGB")).astype(np.float32)
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def map_box(box):
    s, dx, dy = XF
    return tuple(int(round((v - d) / s)) for v, d in zip(box, (dx, dy, dx, dy)))


def measure(L, box):
    x0, y0, x1, y1 = box
    sub = L[y0:y1, x0:x1]
    rows = sub.mean(axis=1)
    return float(rows.std()), float(sub.std()), rows


def panel(path, box, wide, label, colour, width=620, box2=None):
    """one crop panel: the wide crop drawn at `width` px with the QA box outlined, its row-profile curve beside it"""
    L = lum(path)
    row_std, tex_std, _ = measure(L, box)
    _, _, rows = measure(L, wide)
    im = Image.open(path).convert("RGB").crop(wide)
    h = int(im.height * width / im.width)
    im = im.resize((width, h), Image.LANCZOS)
    p = Image.new("RGB", (width + 210, h + 54), (16, 16, 18))
    p.paste(im, (0, 54))
    d = ImageDraw.Draw(p)
    f = ImageFont.truetype(FONT, 19)
    d.text((4, 4), label, font=f, fill=colour)
    d.text((4, 28), f"row-profile std {row_std:.1f}   texture std {tex_std:.1f}   (box {list(box)})",
           font=f, fill=colour)
    sx = width / (wide[2] - wide[0])
    sy = h / (wide[3] - wide[1])
    d.rectangle([(box[0] - wide[0]) * sx, 54 + (box[1] - wide[1]) * sy,
                 (box[2] - wide[0]) * sx, 54 + (box[3] - wide[1]) * sy], outline=(0, 255, 0), width=2)
    if box2:
        d.rectangle([(box2[0] - wide[0]) * sx, 54 + (box2[1] - wide[1]) * sy,
                     (box2[2] - wide[0]) * sx, 54 + (box2[3] - wide[1]) * sy], outline=(255, 220, 0), width=2)
    pts = [(width + 6 + rows[min(int(i / sy), len(rows) - 1)] * 200 / 255.0, 54 + i) for i in range(h)]
    d.line(pts, fill=(120, 230, 255), width=2)
    d.text((width + 6, 30), "row mean lum 0..255", font=ImageFont.truetype(FONT, 13), fill=(120, 230, 255))
    return p, row_std, tex_std


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--before", required=True); ap.add_argument("--after", required=True)
    ap.add_argument("--ref", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--box", type=int, nargs=4, default=[900, 262, 1020, 296])
    ap.add_argument("--wide", type=int, nargs=4, default=[860, 200, 1060, 330])
    ap.add_argument("--model-box", dest="model_box", type=int, nargs=4, default=None,
                    help="the same 34-row window placed on the MODEL's own cornice (yellow); measured on before+after")
    ap.add_argument("--shift", type=float, default=None, help="model-vs-photo vertical displacement, render rows")
    ap.add_argument("--pxm", type=float, default=None, help="render px per metre at the wall plane (arch_entab_probe --map)")
    ap.add_argument("--sil", default=None, help="JSON: {'before': {...}, 'after': {...}} from arch_silhouette measure")
    a = ap.parse_args()
    box, wide = tuple(a.box), tuple(a.wide)
    rbox, rwide = map_box(box), map_box(wide)
    mb = tuple(a.model_box) if a.model_box else None
    p_bef, r_bef, t_bef = panel(a.before, box, wide, "BEFORE  round-05 Cycles hero", (255, 170, 120), box2=mb)
    p_aft, r_aft, t_aft = panel(a.after, box, wide, "AFTER  round-04 cornice rebuild", (150, 255, 150), box2=mb)
    p_ref, r_ref, t_ref = panel(a.ref, rbox, rwide, "REF 169  (round-05 alignment)", (150, 210, 255))
    panels = [p_bef, p_aft, p_ref]

    lines = [
        f"QA-05-6 acceptance: row-profile std >= 0.75 x the photograph's on box {list(box)} of the cam01 Cycles hero.",
        f"  ref 169   row std {r_ref:5.1f}   texture std {t_ref:5.1f}",
        f"  before    row std {r_bef:5.1f}   texture std {t_bef:5.1f}"
        f"   -> {r_bef / r_ref:.2f} / {t_bef / t_ref:.2f} of the photo",
        f"  after     row std {r_aft:5.1f}   texture std {t_aft:5.1f}"
        f"   -> {r_aft / r_ref:.2f} / {t_aft / t_ref:.2f} of the photo"
        f"   [{'PASS' if r_aft >= 0.75 * r_ref else 'FAIL'} on row std]",
    ]
    if mb:
        rb_b, tb_b, _ = measure(lum(a.before), mb)
        rb_a, tb_a, _ = measure(lum(a.after), mb)
        _, _, rr = measure(lum(a.ref), map_box(box))
        lines.append("")
        lines.append(f"The QA box is drawn on the PHOTOGRAPH's cornice. The model's own cornice sits "
                     f"{a.shift:.0f} render rows ({a.shift / a.pxm:.2f} m at {a.pxm:.2f} px/m) higher in the frame,"
                     if a.shift and a.pxm else "Same 34-row window on the model's own cornice (yellow):")
        if a.shift and a.pxm:
            lines.append(f"so the same 34-row window on the MODEL's own cornice (yellow box {list(mb)}) is the honest test:")
        lines.append(f"  before    row std {rb_b:5.1f}   texture std {tb_b:5.1f}"
                     f"   -> {rb_b / r_ref:.2f} / {tb_b / t_ref:.2f} of the photo")
        lines.append(f"  after     row std {rb_a:5.1f}   texture std {tb_a:5.1f}"
                     f"   -> {rb_a / r_ref:.2f} / {tb_a / t_ref:.2f} of the photo"
                     f"   [{'PASS' if rb_a >= 35 else 'FAIL'} on the brief's row std >= 35]")
    if a.sil:
        s = json.load(open(a.sil))
        b, f2 = s.get("before", {}), s.get("after", {})
        lines.append("cam01 silhouette (arch_inspect --alpha -> arch_silhouette measure, same crop):")
        for k in ("apex_y", "corner_top_y", "wa_px", "rise_over_wa"):
            if k in b and k in f2:
                bv, fv = float(b[k]), float(f2[k])
                dp = 100.0 * (fv - bv) / bv if bv else 0.0
                lines.append(f"    {k:14s} before {bv:9.2f}   after {fv:9.2f}   {dp:+.3f} %")
    fm = ImageFont.truetype(MONO, 17)
    th = 16 + 24 * len(lines)
    W = max(max(p.width for p in panels), max(int(fm.getlength(t)) for t in lines) + 16)
    sheet = Image.new("RGB", (W, sum(p.height + 8 for p in panels) + th), (16, 16, 18))
    y = 0
    for p in panels:
        sheet.paste(p, (0, y)); y += p.height + 8
    d = ImageDraw.Draw(sheet)
    for i, t in enumerate(lines):
        d.text((6, y + 8 + 24 * i), t, font=fm, fill=(235, 235, 235))
    sheet.save(a.out)
    print("\n".join(lines))
    print("wrote", a.out, sheet.size)


if __name__ == "__main__":
    main()
