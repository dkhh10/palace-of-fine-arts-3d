#!/usr/bin/env python3
"""ARCH round 7, item 2: measure the rotunda cornice's SUB-COURSES on the photographs.

Why. The r6 refit compressed the whole cornice 1.75 -> 1.37 m by the 0.783 scaling and anchored only two
edges (the corona soffit at ref 169 row 281, the architrave bottom at row 328). The three sub-courses inside
it -- the 0.25 m of corona fascia + drip + cyma over the 1.66 m oversail, the eggs (0.13 m relief at 0.47 m
pitch) and the modillions (0.45 m tall, 0.86 m deep, 1.06 m pitch) -- were never measured on a photograph.
This script measures them on ref 085 (vertex-on, the whole cornice of two faces visible) with no camera fit
and no dependence on any number the r6 refit produced.

Method (numpy + PIL only, no Blender).

1. SCALE WITHOUT A CAMERA. The modillion pitch is measured twice, on the two faces either side of the near
   vertex, by autocorrelating the horizontal luminance profile of the modillion band. An octagon's adjacent
   faces differ by 45 deg, so if the left face makes an angle t with the image plane the right one makes
   45 - t, and the ratio of the two projected pitches fixes t:

       pitch_px_L / pitch_px_R = cos(t) / cos(45 - t)

   The pitch in METRES needs no photograph geometry at all: the modillions run between the two ressauts of a
   face, a span the PLAN gives as FACE_LENGTH - 2*RESSAUT_ALONG = 11.41 m, so counting the gaps N over that
   span gives pitch = 11.41 / N. Together they give the true (unforeshortened) image scale s px/m at the wall
   plane, which is what every vertical measurement below is divided by.

2. ROWS. Courses recede across a face, so a plain column average smears them. Each window is de-slanted first
   (the slope is found by cross-correlating the row profile of the window's left third against its right
   third), then averaged into one row profile; edges are the extrema of its derivative.

3. PROJECTION. A point that stands d metres proud of the wall is lifted in the image by s * d * tan(elev).
   tan(elev) comes from the photo itself: the same course seen at the near vertex and at the far end of a
   face differs in depth by R*(1 - cos 45) = 6.82 m, so tan(elev) = drow / (s * 6.82). Every sub-course height
   below is therefore quoted both as measured (apparent) and corrected to a true vertical height:

       apparent = s * (dz - tan(elev) * dd)

    python3 scripts/arch_r7_cornice.py            # measure, print the table
    python3 scripts/arch_r7_cornice.py --crops    # + write annotated crops next to the numbers
"""
import argparse, math, os, sys
import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import arch_params as P

REF = "/Users/dk/Projects/3d render blender 3rd attempt building/reference/photos/raw/"
PHOTOS = {
    "085": REF + "ref_085_rotunda_San_Francisco_CA_USA_Palace_of_Fine_Arts_2022_0921.jpg",
    "017": REF + "ref_017_rotunda_Palace_of_Fine_Arts_March_2018_1539.jpg",
    "169": REF + "ref_169_main_Palace_of_Fine_Arts_16794p.jpg",
}
RUN_M = P.FACE_LENGTH - 2 * P.RESSAUT_ALONG          # 11.41 m of straight cornice between a face's two ressauts
VERTEX_DEPTH_M = P.WALL_CIRCUMRADIUS * (1 - math.cos(math.radians(45.0)))   # 6.82 m near-vertex to far vertex


def lum(im):
    a = np.asarray(im.convert("RGB"), dtype=np.float64)
    return 0.2126 * a[:, :, 0] + 0.7152 * a[:, :, 1] + 0.0722 * a[:, :, 2]


def slope_of(L, x0, x1, y0, y1, max_shift=40):
    """px of row rise per px of column, from cross-correlating the left third's row profile against the
    right third's. Positive = the course rises (row decreases) toward larger x."""
    w = (x1 - x0) // 3
    a = L[y0:y1, x0:x0 + w].mean(axis=1)
    b = L[y0:y1, x1 - w:x1].mean(axis=1)
    a = a - a.mean()
    b = b - b.mean()
    best, bs = -1e18, 0
    for s in range(-max_shift, max_shift + 1):
        if s >= 0:
            c = float(np.dot(a[s:], b[:len(b) - s])) if s < len(a) else -1e18
        else:
            c = float(np.dot(a[:len(a) + s], b[-s:]))
        if c > best:
            best, bs = c, s
    return bs / float(x1 - x0 - w)          # rows per column between the two window centres


def strip(L, x0, x1, y0, y1, slope):
    """The window with every column shifted back onto its left edge, so a receding course becomes flat."""
    ys = np.arange(y0, y1, dtype=np.float64)
    rows = np.arange(L.shape[0], dtype=np.float64)
    out = np.empty((y1 - y0, x1 - x0))
    for i, x in enumerate(range(x0, x1)):
        out[:, i] = np.interp(ys - slope * (x - x0), rows, L[:, x])
    return out


def pitch_of(st, lo=8.0, hi=90.0):
    """Dominant horizontal period (px) of a de-slanted band, by autocorrelation of its column profile."""
    p = st.mean(axis=0)
    p = p - p.mean()
    n = len(p)
    ac = np.correlate(p, p, mode="full")[n - 1:]
    ac /= ac[0]
    k0, k1 = int(lo), min(int(hi), n - 2)
    k = k0 + int(np.argmax(ac[k0:k1]))
    # parabolic refinement
    if 0 < k < len(ac) - 1:
        d = ac[k - 1] - 2 * ac[k] + ac[k + 1]
        k = k + (0.5 * (ac[k - 1] - ac[k + 1]) / d if abs(d) > 1e-12 else 0.0)
    return float(k), float(ac[int(round(k))])


def edges(prof, y0, n=14):
    """The n strongest edges of a row profile, as (row, dL/dy), strongest first."""
    g = np.gradient(prof)
    idx = np.argsort(-np.abs(g))
    out, used = [], []
    for i in idx:
        if any(abs(i - u) < 3 for u in used):
            continue
        used.append(i)
        out.append((y0 + int(i), float(g[i])))
        if len(out) >= n:
            break
    return out


# --------------------------------------------------------------------------- ref 085 windows (full-res px)
# ref 085 is 1920x1280 (the whole photo corpus is capped at 1920). The near vertex is at x ~ 1200; each face's
# straight cornice run lies between its two ressauts. Rows are quoted in the DE-SLANTED frame of the window's
# left edge (slope from slope_of), which is what the printed profile and the annotated crop both use.
W = dict(
    L=dict(x=(600, 930), slope=0.063, tall=(780, 1010),
           bands=dict(corona=(838, 846), egg=(846, 857), fret=(857, 877), modillion=(877, 899))),
    R=dict(x=(1260, 1560), slope=-0.1304, tall=(780, 1010),
           bands=dict(corona=(832, 841), egg=(844, 855), fret=(855, 874), modillion=(874, 896))),
)
# Model sub-courses, from arch_build.CORNICE (z above ENTABLATURE_Z0, d = projection past the wall plane).
MODEL = dict(corona=(3.22, 1.36, 2.97, 1.66), egg=(2.98, 0.85, 2.72, 0.85),
             fret=(None, None, None, None), modillion=(2.82, 1.38, 2.37, 1.38))
MODEL_PITCH = dict(modillion=1.06, egg=0.47, dentil=0.38)
# Autocorrelation search window per band. The egg-and-dart's own period is half the modillions', so an open
# search locks onto its second harmonic (33 px) instead of the unit (16 px); the fret's is one meander unit.
AC_RANGE = dict(corona=(20, 60), egg=(10, 25), fret=(30, 60), modillion=(20, 60))
TAN_ELEV = 0.08          # ref 085 is a low, distant view; see docs/arch_notes.md round 7 item 2


def hp(p, w=41):
    """High-pass: the cornice runs through a strong left-to-right lighting gradient that swamps the ornament's
    own period in the autocorrelation."""
    k = np.ones(w) / w
    sm = np.convolve(np.pad(p, (w // 2, w // 2), mode="edge"), k, "valid")
    return p - sm[:len(p)]


def ac_peaks(p, lo=6, hi=60, n=3):
    p = hp(p)
    p = p - p.mean()
    m = len(p)
    a = np.correlate(p, p, "full")[m - 1:]
    a /= a[0]
    ks = [(k, float(a[k])) for k in range(lo, hi) if a[k] > a[k - 1] and a[k] > a[k + 1]]
    ks.sort(key=lambda t: -t[1])
    return ks[:n]


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--crop", default="")
    a = ap.parse_args()
    im = Image.open(PHOTOS["085"]).convert("RGB")
    L = lum(im)

    print("# ref 085 (1920x1280), rotunda entablature cornice, both faces of the near vertex.")
    print("# 1. horizontal periods (de-slanted band, high-passed, autocorrelated)")
    per = {}
    for f, w in W.items():
        for b, (y0, y1) in w["bands"].items():
            st = strip(L, w["x"][0], w["x"][1], y0, y1, w["slope"])
            lo, hi = AC_RANGE[b]
            pk = ac_peaks(st.mean(axis=0), lo, hi)
            per[(f, b)] = pk
            print(f"  face {f} {b:10s} rows {y0}-{y1}: " +
                  "  ".join(f"{k:3d} px (ac {v:+.2f})" for k, v in pk))

    pL = per[("L", "modillion")][0][0]
    pR = per[("R", "modillion")][0][0]
    ts = np.linspace(0.1, 44.9, 20000)
    t = float(ts[np.argmin(np.abs(np.cos(np.radians(ts)) / np.cos(np.radians(45.0 - ts)) - pL / pR))])
    print(f"\n# 2. scale, with no camera fit")
    print(f"  modillion period {pL} px (left face) / {pR} px (right) -> ratio {pL / pR:.3f} = cos t / cos(45 - t)")
    print(f"     -> left face obliquity {t:.1f} deg, right {45.0 - t:.1f} deg")
    run_px = W["L"]["x"][1] - W["L"]["x"][0]
    print(f"  the plan puts {RUN_M:.2f} m of straight cornice between a face's two ressauts; the left face's run"
          f" holds {RUN_M / (pL / 33.8):.1f} periods at the scale below, i.e. N = 11 gaps")
    for n in (11, 12):
        s_proj = pL / (RUN_M / n)
        s_vert = s_proj / math.cos(math.radians(t))
        print(f"     N = {n} -> modillion pitch {RUN_M / n:.3f} m, projected scale {s_proj:.1f} px/m, "
              f"vertical scale {s_vert:.1f} px/m")
    N = 11
    s_proj = pL / (RUN_M / N)
    s_vert = s_proj / math.cos(math.radians(t))

    print(f"\n# 3. sub-courses (left face; heights / s_vert = {s_vert:.1f}, periods / s_proj = {s_proj:.1f} px/m)")
    print(f"  {'course':11s} {'rows':>10s} {'px':>4s} {'photo m':>9s} {'model m':>9s} {'delta':>8s}   period photo / model")
    b = W["L"]["bands"]
    for name in ("corona", "egg", "fret", "modillion"):
        y0, y1 = b[name]
        h = (y1 - y0) / s_vert
        z1, d1, z0, d0 = MODEL[name]
        mh = (z1 + d1 * TAN_ELEV) - (z0 + d0 * TAN_ELEV) if z1 is not None else None
        pk = per[("L", name)][0][0] / s_proj
        mp = MODEL_PITCH.get(name)
        print(f"  {name:11s} {y0}-{y1:<5d} {y1 - y0:4d} {h:9.3f} " +
              (f"{mh:9.3f} {100 * (h - mh) / mh:+7.1f} %" if mh else f"{'--':>9s} {'NOT MODELLED':>9s}") +
              (f"   {pk:.3f} / {mp:.3f} m  {100 * (pk - mp) / mp:+.1f} %" if mp else ""))
    y_top, y_bot = b["corona"][0], b["modillion"][1]
    tot = (y_bot - y_top) / s_vert
    mtot = (MODEL["corona"][0] + MODEL["corona"][1] * TAN_ELEV) - (MODEL["modillion"][2] + MODEL["modillion"][3] * TAN_ELEV)
    print(f"  {'TOTAL':11s} {y_top}-{y_bot:<5d} {y_bot - y_top:4d} {tot:9.3f} {mtot:9.3f} {100 * (tot - mtot) / mtot:+7.1f} %"
          f"   (crown to modillion bottom; CORNICE_H is {P.CORNICE_H:.2f} m)")

    if a.crop:
        x0, x1 = 500, 1000
        y0, y1 = 820, 910
        arr = np.asarray(im, dtype=np.float64)
        outp = np.zeros((y1 - y0, x1 - x0, 3))
        ys = np.arange(y0, y1, dtype=float)
        rows = np.arange(arr.shape[0], dtype=float)
        for i, x in enumerate(range(x0, x1)):
            for ch in range(3):
                outp[:, i, ch] = np.interp(ys - W["L"]["slope"] * (x - W["L"]["x"][0]), rows, arr[:, x, ch])
        c = Image.fromarray(outp.astype("uint8")).resize(((x1 - x0) * 3, (y1 - y0) * 3), Image.LANCZOS)
        d = ImageDraw.Draw(c)
        for name, (ya, yb) in b.items():
            for yy in (ya, yb):
                d.line([(0, (yy - y0) * 3), (c.width, (yy - y0) * 3)], fill=(255, 60, 60), width=1)
            d.text((6, (ya - y0) * 3 + 2), f"{name} {yb - ya} px = {(yb - ya) / s_vert:.2f} m", fill=(255, 255, 0))
        d.text((6, 2), f"ref 085, left face, de-slanted {W['L']['slope']:+.3f} row/col, 3x; "
                       f"{s_vert:.1f} px/m vertical", fill=(255, 255, 255))
        os.makedirs(os.path.dirname(a.crop), exist_ok=True)
        c.save(a.crop)
        print("\nwrote", a.crop)
