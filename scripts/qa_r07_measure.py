#!/usr/bin/env python3
"""QA round-07 measurement tool (QA-owned; images only, no Blender).

One place for every number docs/qa_round_07.md quotes, so the report and the tool cannot drift.

  python3 scripts/qa_r07_measure.py box IMG name x0 y0 x1 y1 [name x0 y0 x1 y1 ...]
      per box: mean sRGB, lum, hue, sat, R-B, std of luminance, and the streak anisotropy
      (column-sd / row-sd of the box's row/column profiles; > 1 = vertical streaks, the photo's rain run-off).
  python3 scripts/qa_r07_measure.py mask IMG x0 y0 x1 y1 --hue-max 32 --sat-min 0.30
      per-pixel mask statistics (the columns test: hue < hue_max and sat > sat_min).
  python3 scripts/qa_r07_measure.py frac IMG --below 10        fraction of the frame under a luminance
  python3 scripts/qa_r07_measure.py rows IMG x0 y0 x1 y1       row-profile std (the entablature test)
  python3 scripts/qa_r07_measure.py alternation IMG x0 y0 x1 y1 --n 8
      counts luminance maxima along the row band (the capital / column alternation count, QA-06-6's half).
  python3 scripts/qa_r07_measure.py camheight --sheet ALIGNED.png --direct Y --refl Y --height M [--horizon Y]
      brief item 5: camera height over the water from a direct/reflected pair (see the derivation in the report).
"""
import argparse, colorsys, sys
import numpy as np
from PIL import Image


def load(p):
    return np.asarray(Image.open(p).convert("RGB")).astype(np.float32)


def lum(a):
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def boxstats(img, box):
    x0, y0, x1, y1 = box
    sub = img[y0:y1, x0:x1]
    m = sub.reshape(-1, 3).mean(axis=0)
    L = lum(sub)
    h, s, v = colorsys.rgb_to_hsv(*(m / 255.0))
    rows = L.mean(axis=1)           # one value per image row  -> variation down the box
    cols = L.mean(axis=0)           # one value per image column -> variation across the box
    col_sd, row_sd = float(cols.std()), float(rows.std())
    aniso = col_sd / row_sd if row_sd > 1e-6 else float("inf")
    return dict(mean=[round(float(c), 1) for c in m], lum=round(float(lum(m)), 1),
                hue=round(h * 360, 1), sat=round(s, 3), rb=round(float(m[0] - m[2]), 1),
                std=round(float(L.std()), 1), col_sd=round(col_sd, 1), row_sd=round(row_sd, 1),
                aniso=round(aniso, 2))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mode")
    ap.add_argument("img", nargs="?")
    ap.add_argument("rest", nargs="*")
    ap.add_argument("--hue-max", type=float, default=32.0)
    ap.add_argument("--sat-min", type=float, default=0.30)
    ap.add_argument("--below", type=float, default=10.0)
    ap.add_argument("--n", type=int, default=8)
    ap.add_argument("--frac", action="store_true")
    ap.add_argument("--sheet"); ap.add_argument("--direct", type=float); ap.add_argument("--refl", type=float)
    ap.add_argument("--height", type=float); ap.add_argument("--horizon", type=float)
    a = ap.parse_args()

    if a.mode == "mirror":
        # Find the mirror row M for one object distance: the water's row profile is the building's profile
        # reflected about M (exactly, for a flat water plane -- see the derivation in docs/qa_round_07.md item 5).
        # usage: mirror IMG x0 x1 ytop ybot wtop wbot   (building band ytop..ybot, water band wtop..wbot)
        img2 = load(a.img)
        x0, x1, yt, yb, wt, wb = [int(v) for v in a.rest[:6]]
        prof = lum(img2[:, x0:x1]).mean(axis=1)
        p = (prof - prof.mean()) / (prof.std() + 1e-6)
        best = None
        for M2 in range(2 * (yb + 4), 2 * (wb - 4)):        # M in half-pixel steps
            M = M2 / 2.0
            ys = np.arange(yt, yb)
            yr = np.round(2 * M - ys).astype(int)
            ok = (yr >= wt) & (yr < wb)
            if ok.sum() < 0.5 * len(ys):
                continue
            a1, b1 = p[ys[ok]], p[yr[ok]]
            c = float(np.corrcoef(a1, b1)[0, 1])
            if best is None or c > best[1]:
                best = (M, c, int(ok.sum()))
        print(f"mirror row M {best[0]:.1f}  corr {best[1]:.3f}  rows used {best[2]}")
        return

    if a.mode == "camheight":
        # u = y - horizon.  direct point at height H, distance d, camera height h:
        #   u_dir = -f (H - h)/d ,  u_refl = +f (H + h)/d
        #   => (u_dir + u_refl)/(u_refl - u_dir) = h / H        (independent of f, d)
        M = a.refl if a.refl is not None else None
        if M is None:
            raise SystemExit("camheight: pass --refl as the mirror row M (from mode 'mirror')")
        r = (M - a.horizon) / (M - a.direct)
        print(f"M {M:.1f} horizon {a.horizon:.1f} y_dir {a.direct:.1f} H {a.height} m -> "
              f"h/H {r:.4f}  camera height over water {a.height * r:.2f} m")
        return

    img = load(a.img)
    if a.mode == "box":
        vals = a.rest
        for i in range(0, len(vals), 5):
            name = vals[i]
            box = [float(v) for v in vals[i + 1:i + 5]]
            if a.frac:
                box = [box[0] * img.shape[1], box[1] * img.shape[0],
                       box[2] * img.shape[1], box[3] * img.shape[0]]
            box = [int(round(v)) for v in box]
            s = boxstats(img, box)
            print(f"{name:26s} {box} lum {s['lum']:6.1f} hue {s['hue']:6.1f} sat {s['sat']:.3f} "
                  f"R-B {s['rb']:+6.1f} std {s['std']:5.1f} colsd {s['col_sd']:5.1f} rowsd {s['row_sd']:5.1f} "
                  f"aniso {s['aniso']:.2f}")
    elif a.mode == "mask":
        x0, y0, x1, y1 = [int(v) for v in a.rest[:4]]
        sub = img[y0:y1, x0:x1] / 255.0
        mx, mn = sub.max(axis=2), sub.min(axis=2)
        sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0)
        r, g, b = sub[..., 0], sub[..., 1], sub[..., 2]
        hue = np.zeros_like(mx); d = mx - mn + 1e-9
        hue = np.where(mx == r, ((g - b) / d) % 6, np.where(mx == g, (b - r) / d + 2, (r - g) / d + 4)) * 60
        m = (hue < a.hue_max) & (sat > a.sat_min)
        n = int(m.sum())
        if n == 0:
            print("mask empty"); return
        px = (sub[m] * 255.0).mean(axis=0)
        hh, ss, vv = colorsys.rgb_to_hsv(*(px / 255.0))
        print(f"mask n {n} ({100.0 * n / m.size:.1f} % of box) mean {px.round(1).tolist()} "
              f"lum {lum(px):.1f} hue {hh * 360:.1f} sat {ss:.3f} R-B {px[0] - px[2]:+.1f}")
    elif a.mode == "shadowfrac":
        # QA-02-7 on a render: the share of a wing band that is in shadow. "Shadowed" = below half the band's own
        # 90th-percentile luminance (the sunlit stone sets the reference, so exposure cancels).
        vals = a.rest
        for i in range(0, len(vals), 5):
            name = vals[i]
            x0, y0, x1, y1 = [int(round(float(v))) for v in vals[i + 1:i + 5]]
            L = lum(img[y0:y1, x0:x1])
            p90 = float(np.percentile(L, 90))
            thr = 0.5 * p90
            print(f"{name:16s} [{x0},{y0},{x1},{y1}] p90 {p90:6.1f} thr {thr:6.1f} "
                  f"shadow share {100.0 * (L < thr).mean():5.1f} %  mean {L.mean():.1f}")
    elif a.mode == "frac":
        L = lum(img)
        print(f"frame {img.shape[1]}x{img.shape[0]}: below {a.below}: {100.0 * (L < a.below).mean():.1f} %")
    elif a.mode == "rows":
        x0, y0, x1, y1 = [int(v) for v in a.rest[:4]]
        rows = lum(img[y0:y1, x0:x1]).mean(axis=1)
        print(f"row-profile std {rows.std():.1f} over {y1 - y0} rows; min {rows.min():.1f} max {rows.max():.1f}")
    elif a.mode == "alternation":
        x0, y0, x1, y1 = [int(v) for v in a.rest[:4]]
        cols = lum(img[y0:y1, x0:x1]).mean(axis=0)
        k = np.ones(5) / 5.0
        sm = np.convolve(cols, k, mode="same")
        amp = sm.max() - sm.min()
        peaks = [i for i in range(2, len(sm) - 2)
                 if sm[i] == max(sm[max(0, i - 6):i + 7]) and sm[i] - min(sm[max(0, i - 12):i + 13]) > 0.08 * amp]
        # merge peaks closer than 6 px
        merged = []
        for p in peaks:
            if not merged or p - merged[-1] > 6:
                merged.append(p)
        print(f"alternation over {x1 - x0} px: {len(merged)} maxima at x {[x0 + p for p in merged]}; "
              f"amplitude {amp:.1f} (mean {sm.mean():.1f}, contrast {amp / max(sm.mean(), 1e-6):.3f})")
    else:
        print("unknown mode", a.mode); sys.exit(2)


if __name__ == "__main__":
    main()
