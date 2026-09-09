#!/usr/bin/env python3
"""QA round-06 item 7: where each course of the hero-facing stack sits, render vs ref 169.

The lead needs the offset PER COURSE (not one number for the whole elevation) before the photo-projection pass can
start: architecture measured the cornice 1.04 m high, materials measured the attic panel frame ~0.65 m high, and QA's
attic box catches the render's cornice in its bottom rows. If the offsets differ course by course, a rigid shift of the
projected photo cannot fit and the stack itself has to move.

Input is the aligned overlay sheet written by `qa_silhouette.py align` (3 panels of the render's size:
0 = render, 1 = ref 169 warped into the render frame, 2 = blend), so both images are already in the same pixel grid
and one row means the same thing in both.

  python3 scripts/qa_stack_offset.py --sheet renders/qa_comparisons/round06_cam01_aligned_vs_ref169.png \
      --x0 880 --x1 1040 --y0 150 --y1 350 --pxm 13.42 --out renders/qa_comparisons/round06_stack_offset.png

Method: row-mean luminance L(y) over the column band, smoothed with a 3-row box, then dL/dy. A course boundary is a
local extremum of |dL/dy| above --thresh that is at least --sep rows from a stronger one. Courses are matched by
walking both edge lists top-down in order; the report prints the render row, the ref row, the delta in rows and in
metres at --pxm px/m. The labelled panel (x8 vertical zoom) is written so the match can be checked by eye.
"""
import argparse
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

FONT = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"


def lum(a):
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def smooth(v, k=3):
    ker = np.ones(k) / k
    return np.convolve(v, ker, mode="same")


def edges(L, thresh, sep):
    g = np.gradient(L)
    cand = []
    for y in range(2, len(g) - 2):
        if abs(g[y]) < thresh:
            continue
        if abs(g[y]) >= abs(g[y - 1]) and abs(g[y]) >= abs(g[y + 1]):
            cand.append((y, float(g[y])))
    cand.sort(key=lambda t: -abs(t[1]))
    keep = []
    for y, gv in cand:
        if all(abs(y - k[0]) >= sep for k in keep):
            keep.append((y, gv))
    keep.sort()
    return keep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sheet", required=True)
    ap.add_argument("--x0", type=int, default=880); ap.add_argument("--x1", type=int, default=1040)
    ap.add_argument("--y0", type=int, default=150); ap.add_argument("--y1", type=int, default=350)
    ap.add_argument("--pxm", type=float, default=13.42, help="pixels per metre at the wall plane")
    ap.add_argument("--thresh", type=float, default=1.5)
    ap.add_argument("--sep", type=int, default=4)
    ap.add_argument("--out", default=None)
    ap.add_argument("--profile", action="store_true", help="dump the full row profile of both panels")
    a = ap.parse_args()

    im = Image.open(a.sheet).convert("RGB")
    W = im.width // 3
    R = np.asarray(im.crop((0, 0, W, im.height))).astype(np.float64)
    P = np.asarray(im.crop((W, 0, 2 * W, im.height))).astype(np.float64)

    Lr = smooth(lum(R[a.y0:a.y1, a.x0:a.x1]).mean(axis=1))
    Lp = smooth(lum(P[a.y0:a.y1, a.x0:a.x1]).mean(axis=1))
    er = [(a.y0 + y, g) for y, g in edges(Lr, a.thresh, a.sep)]
    ep = [(a.y0 + y, g) for y, g in edges(Lp, a.thresh, a.sep)]

    if a.profile:
        print(f"{'y':>5s} {'L_render':>9s} {'dL_r':>7s} {'L_ref':>8s} {'dL_p':>7s}")
        gr, gp = np.gradient(Lr), np.gradient(Lp)
        for i in range(len(Lr)):
            print(f"{a.y0+i:5d} {Lr[i]:9.1f} {gr[i]:7.2f} {Lp[i]:8.1f} {gp[i]:7.2f}")

    print(f"\nband x {a.x0}-{a.x1}, rows {a.y0}-{a.y1}, {a.pxm} px/m  ({1/a.pxm*100:.1f} cm per row)")
    print(f"render edges ({len(er)}): " + ", ".join(f"{y}({g:+.1f})" for y, g in er))
    print(f"ref    edges ({len(ep)}): " + ", ".join(f"{y}({g:+.1f})" for y, g in ep))

    # pair edges of the same sign, nearest-first, so a light->dark boundary is never matched to a dark->light one
    used = set()
    pairs = []
    for y, g in er:
        best, bd = None, 1e9
        for j, (yp, gp2) in enumerate(ep):
            if j in used or np.sign(gp2) != np.sign(g):
                continue
            d = abs(yp - y)
            if d < bd:
                best, bd = j, d
        if best is not None and bd <= 24:
            used.add(best)
            pairs.append((y, ep[best][0], g, ep[best][1]))
    print(f"\n{'render y':>9s} {'ref y':>7s} {'d rows':>7s} {'d m':>7s}   sign")
    for y, yp, g, gp2 in pairs:
        d = y - yp
        print(f"{y:9d} {yp:7d} {d:+7d} {-d / a.pxm:+7.3f}   {'dark->light' if g > 0 else 'light->dark'}")
    if pairs:
        ds = np.array([p[0] - p[1] for p in pairs], dtype=float)
        print(f"\nmean {-ds.mean()/a.pxm:+.3f} m, median {-np.median(ds)/a.pxm:+.3f} m, spread "
              f"{(ds.max()-ds.min())/a.pxm:.3f} m  (+ve = the render's course sits HIGHER in frame than the photo's)")

    if a.out:
        zoom, wpan = 8, (a.x1 - a.x0)
        panels = []
        for arr, lab, ed in ((R, "RENDER", er), (P, "REF 169 aligned", ep)):
            c = Image.fromarray(arr[a.y0:a.y1, a.x0:a.x1].astype(np.uint8))
            c = c.resize((wpan * 3, (a.y1 - a.y0) * zoom), Image.LANCZOS)
            panels.append((c, lab, ed))
        font = ImageFont.truetype(FONT, 16)
        H = panels[0][0].height + 30
        out = Image.new("RGB", (2 * (panels[0][0].width + 120) + 20, H), (18, 18, 20))
        d = ImageDraw.Draw(out)
        for i, (c, lab, ed) in enumerate(panels):
            x = i * (c.width + 130) + 110
            out.paste(c, (x, 26))
            d.text((x, 4), lab, font=font, fill=(255, 220, 120) if i == 0 else (140, 230, 255))
            for y, g in ed:
                yy = 26 + (y - a.y0) * zoom
                d.line([(x, yy), (x + c.width, yy)], fill=(255, 80, 80) if g < 0 else (80, 255, 120))
                d.text((x - 105, yy - 8), f"y={y} {g:+.1f}", font=font, fill=(225, 225, 225))
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        out.save(a.out)
        print("wrote", a.out, out.size)


if __name__ == "__main__":
    main()


# --------------------------------------------------------------------------------------------- per-course x-corr
# Item 7 of the round-06 brief. Windows are named courses located on REF 169 (its edges are crisp; the render's are
# not), each given as (row0, row1) in the aligned 1920x1080 grid. For each window the render's row-luminance gradient
# is slid over the ref's and the shift with the highest normalised correlation is the render's offset for that course.
COURSES = [
    ("attic top cornice + dentils", 158, 190),
    ("attic panel frame top",       190, 212),
    ("attic panel frame bottom",    256, 278),
    ("cornice corona + dentils",    276, 300),
    ("frieze top -> bottom",        296, 322),
    ("architrave bottom / capital", 316, 342),
]


def xcorr_courses(sheet, x0, x1, pxm, span=30, courses=COURSES):
    im = Image.open(sheet).convert("RGB")
    W = im.width // 3
    R = lum(np.asarray(im.crop((0, 0, W, im.height))).astype(np.float64))[:, x0:x1].mean(axis=1)
    P = lum(np.asarray(im.crop((W, 0, 2 * W, im.height))).astype(np.float64))[:, x0:x1].mean(axis=1)
    gR, gP = np.gradient(smooth(R)), np.gradient(smooth(P))
    print(f"\ncourse offsets by gradient cross-correlation, band x {x0}-{x1}, +-{span} rows, {pxm} px/m")
    print(f"{'course':32s} {'ref rows':>11s} {'shift':>6s} {'m':>7s} {'corr':>6s}")
    rows = []
    for name, r0, r1 in courses:
        w = gP[r0:r1]
        w = w - w.mean()
        best, bc = 0, -2.0
        for s in range(-span, span + 1):
            v = gR[r0 + s:r1 + s]
            if len(v) != len(w):
                continue
            v = v - v.mean()
            den = np.linalg.norm(v) * np.linalg.norm(w)
            c = float(v @ w / den) if den > 1e-9 else 0.0
            if c > bc:
                best, bc = s, c
        rows.append((name, r0, r1, best, bc))
        print(f"{name:32s} {r0:5d}-{r1:<5d} {best:+6d} {-best/pxm:+7.3f} {bc:6.2f}")
    return rows
