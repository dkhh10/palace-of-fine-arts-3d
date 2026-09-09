"""Round-9 acceptance table, seam test and coffer chroma (plain python, no Blender).

    python3 scripts/mat_r9_measure.py hero   <before.png> <after.png>
    python3 scripts/mat_r9_measure.py seam   <off.png> <on.png> [--label cam02]
    python3 scripts/mat_r9_measure.py coffer <cam04.png>
    python3 scripts/mat_r9_measure.py cam05  <cam05.png>

`hero` prints the brief's own windows (docs/briefs/materials_r9.md items A, B, C, F) with BEFORE and AFTER side by
side and a PASS/FAIL per row, on QA's 1920x1080 boxes.

`coffer` answers docs/reviews/mat_r8_review.md finding 2, which asked for the saturation numbers the round-8 notes
quoted to come out of a committed script: the saucer is split at its own luminance quartiles -- the light quarter
is the coffer FIELD (MAT_plaster_ceiling), the dark quarter is the RIB / rim (MAT_plaster_ceiling_rib) -- and the
saturation of each is printed against ref 083's 0.427 field / 0.438 rim and QA-07-9's 0.38-0.50 window.

`seam` is the projection's seam test.  Given the same camera rendered with the projection off and on, it reports
the peak luminance change, how much of the frame moved at all, and the largest single-pixel STEP of the
difference: a hard mask edge is a step in the difference and is invisible in either frame alone.
"""
import sys
from pathlib import Path
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mat_r7_measure import load, stats, box, columns, BOXES, lum

# item A / B / C / F of docs/briefs/materials_r9.md, as (row label, getter, window text, test)
REF = dict(attic_sunlit=(188.5, 40.5, 0.582, 133.2), attic_shaded=(120.2, 30.7, 0.457, 68.0),
           water_refl=(164.6, 33.7, 0.370, 71.7), near_water_sky=(105.4, 189.8, 0.246, None),
           lagoon_flank=(152.4, 200.3, None, None))


def hero(before, after):
    a0, a1 = load(before), load(after)
    print(f"{'box':16s} {'before':>26s} {'after':>26s}   window")

    def row(name, get, win):
        s0, s1 = get(a0), get(a1)
        f = lambda s: f"{s['lum']:6.1f}/{s['hue']:5.1f}/{s['sat']:.3f}/{s['rb']:+6.1f}"
        print(f"  {name:14s} {f(s0):>26s} {f(s1):>26s}   {win}")
        return s0, s1

    b, a = row("attic_sunlit", lambda x: box(x, "attic_sunlit"), "lum 178-201, sat .53-.62, R-B >= 120")
    row("attic_string", lambda x: box(x, "attic_string"), "(ref 185.3/39.3/0.585)")
    row("entablature", lambda x: box(x, "entablature"), "sat <= 0.70")
    sh0, sh1 = row("attic_shaded", lambda x: box(x, "attic_shaded"), "lum 103.5-126.5, hue 23.5-35.5, sat <= .50")
    c0, c1 = row("columns", columns, "hue 24.5+-4, sat .55-.65")
    w0, w1 = row("water_refl", lambda x: box(x, "water_refl"), "lum 124-208, R-B >= +35, hue 25-45")
    n0, n1 = row("near_water_sky", lambda x: box(x, "near_water_sky"), "lum 79-131, hue 185-200, sat .22-.32")
    row("ripples", lambda x: box(x, "ripples"), "R-B -26 +- 10")
    row("lagoon_flank", lambda x: box(x, "lagoon_flank"), "lum 114-190, hue <= 210")

    print("\n  texture / direction on 900 222 1020 256 and the narrow box 900 224 1020 248")
    for label, bx in (("QA box", (900, 222, 1020, 256)), ("narrow", (900, 224, 1020, 248))):
        for tag, arr in (("before", a0), ("after", a1)):
            g = lum(arr[bx[1]:bx[3], bx[0]:bx[2]])
            an = g.mean(axis=0).std() / max(g.mean(axis=1).std(), 1e-6)
            print(f"    {label:7s} {tag:6s} std {g.std():5.1f} (ratio {g.std() / 44.5:.2f}, test >= 0.60)  "
                  f"aniso {an:5.2f} (test >= {1.5 if label == 'QA box' else 2.0})")

    ok = lambda c: "PASS" if c else "FAIL"
    print("\n  >> A  attic sat {:.3f} (.53-.62) {} | R-B {:+.1f} (>=120) {} | lum {:.1f} (178-201) {}".format(
        a["sat"], ok(0.53 <= a["sat"] <= 0.62), a["rb"], ok(a["rb"] >= 120), a["lum"], ok(178 <= a["lum"] <= 201)))
    print("  >> A  shaded hue {:.1f} (29.5+-6) {} | sat {:.3f} (<=.50) {} | columns hue {:.1f} (24.5+-4) {} sat {:.3f} (.55-.65) {}".format(
        sh1["hue"], ok(abs(sh1["hue"] - 29.5) <= 6), sh1["sat"], ok(sh1["sat"] <= 0.50),
        c1["hue"], ok(abs(c1["hue"] - 24.5) <= 4), c1["sat"], ok(0.55 <= c1["sat"] <= 0.65)))
    print("  >> F  shaded lum {:.1f} (103.5-126.5) {}   [before {:.1f}]".format(
        sh1["lum"], ok(103.5 <= sh1["lum"] <= 126.5), sh0["lum"]))
    print("  >> B  reflection lum {:.1f} (124-208) {} | R-B {:+.1f} (>=35) {} | hue {:.1f} (25-45) {} | refl/attic {:.2f} (photo 0.88)".format(
        w1["lum"], ok(124 <= w1["lum"] <= 208), w1["rb"], ok(w1["rb"] >= 35), w1["hue"],
        ok(25 <= w1["hue"] <= 45), w1["lum"] / a["lum"]))
    print("  >> C  near water lum {:.1f} (79-131) {} | hue {:.1f} (185-200) {} | sat {:.3f} (.22-.32) {}".format(
        n1["lum"], ok(79 <= n1["lum"] <= 131), n1["hue"], ok(185 <= n1["hue"] <= 200),
        n1["sat"], ok(0.22 <= n1["sat"] <= 0.32)))


def seam(off, on, label=""):
    a0 = np.asarray(Image.open(off).convert("RGB")).astype(np.float64)
    a1 = np.asarray(Image.open(on).convert("RGB")).astype(np.float64)
    d = lum(a1) - lum(a0)
    moved = np.abs(d) > 3.0
    raw = max(np.abs(np.diff(d, axis=1)).max(), np.abs(np.diff(d, axis=0)).max())
    # A seam is a COHERENT edge along the mask boundary, so it survives a blur; a one-pixel jump at a geometry
    # edge (where the two neighbouring pixels are different surfaces with different ratios) and Eevee's TAA noise
    # do not.  The seam metric is therefore the largest gradient of the 2 px-blurred difference.
    k = np.exp(-0.5 * (np.arange(-6, 7) / 2.0) ** 2); k /= k.sum()
    db = d
    for ax in (0, 1):
        pad = [(0, 0), (0, 0)]; pad[ax] = (6, 6)
        pp = np.pad(db, pad, mode="edge")
        acc = np.zeros_like(db)
        for i, w in enumerate(k):
            sl = [slice(None), slice(None)]; sl[ax] = slice(i, i + db.shape[ax])
            acc += w * pp[tuple(sl)]
        db = acc
    step = max(np.abs(np.diff(db, axis=1)).max(), np.abs(np.diff(db, axis=0)).max())
    print(f"[seam] {label or Path(on).stem}  {a0.shape[1]}x{a0.shape[0]}")
    print(f"  peak |delta lum| {np.abs(d).max():6.2f}   pixels moved > 3 lum {100 * moved.mean():5.2f} %   "
          f"mean |delta| where moved {np.abs(d)[moved].mean() if moved.any() else 0.0:5.2f}")
    print(f"  largest single-pixel step, raw {raw:5.2f} lum (geometry edges + TAA)   "
          f"BLURRED (the seam metric) {step:5.3f} lum / px")
    if moved.any():
        ys, xs = np.where(moved)
        print(f"  changed region rows {ys.min()}-{ys.max()} cols {xs.min()}-{xs.max()}; "
              f"row-std of the difference across that band {d[ys.min():ys.max() + 1].mean(axis=1).std():.3f}")


def coffer(path):
    a = np.asarray(Image.open(path).convert("RGB")).astype(np.float64)
    H, W = a.shape[:2]
    c = a[int(H * 0.20):int(H * 0.80), int(W * 0.28):int(W * 0.72)]
    g = lum(c)
    v = g.ravel()
    q1, q3 = np.percentile(v[v > 1], 25), np.percentile(v[v > 1], 75)
    field = c[g >= q3]
    rim = c[(g <= q1) & (g > 1)]
    print(f"[coffer] {Path(path).name}  saucer {c.shape[1]}x{c.shape[0]}")
    for nm, sel, ref in (("field (light quarter)", field, 0.427), ("rim (dark quarter)", rim, 0.438)):
        s = stats(sel[None, :, :])
        print(f"  {nm:22s} lum {s['lum']:6.1f}  hue {s['hue']:5.1f}  sat {s['sat']:.3f}  (ref 083 {ref:.3f}, "
              f"QA-07-9 window 0.38-0.50)  {'PASS' if 0.38 <= s['sat'] <= 0.50 else 'FAIL'}")
    print(f"  dark/light luminance ratio {lum(rim.mean(axis=0)) / lum(field.mean(axis=0)):.3f} (ref 083 0.265)  "
          f"field std {g[g >= q3].std():.1f}")


def cam05(path):
    a = np.asarray(Image.open(path).convert("RGB")).astype(np.float64)
    H, W = a.shape[:2]
    s = stats(a[int(0.86 * H):int(0.99 * H), int(0.35 * W):int(0.75 * W)])
    print(f"[cam05] band lum {s['lum']:6.1f} hue {s['hue']:5.1f} sat {s['sat']:.3f} R-B {s['rb']:+6.1f}   "
          f"window lum 70-117 {'PASS' if 70 <= s['lum'] <= 117 else 'FAIL'}, sat >= 0.24 "
          f"{'PASS' if s['sat'] >= 0.24 else 'FAIL'} (ref 0.306)")


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "hero":
        hero(sys.argv[2], sys.argv[3])
    elif cmd == "seam":
        lb = sys.argv[sys.argv.index("--label") + 1] if "--label" in sys.argv else ""
        seam(sys.argv[2], sys.argv[3], lb)
    elif cmd == "coffer":
        coffer(sys.argv[2])
    elif cmd == "cam05":
        cam05(sys.argv[2])
    else:
        raise SystemExit(__doc__)
