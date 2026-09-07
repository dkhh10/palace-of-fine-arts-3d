#!/usr/bin/env python3
"""QA region / framing measurements (python3 + numpy + PIL). QA-owned; reads images only, never touches the scene.

  python3 scripts/qa_measure.py regions IMG --box name x0 y0 x1 y1 [--box ...]
      -> per box: mean sRGB, relative luminance (0-255 scale), hue angle (deg), saturation.
         Boxes may be given in pixels or, with --frac, as fractions of width/height.
  python3 scripts/qa_measure.py waterline IMG --x0 X0 --x1 X1 [--ymin Y] [--ymax Y]
      -> the row where the shore/water transition sits (median over columns of the first row below ymin whose
         downward run of 12 rows is "water": blue-dominant or dark and low-variance), as px and % of frame height.
  python3 scripts/qa_measure.py ev A B --box ... (same boxes on both images)
      -> luminance ratio B/A per box and the EV delta log2(B/A); use render as A and photo as B.

Hue is the HSV hue of the mean colour; "golden hour stone" in the reference photos sits at 35-42 deg.
"""
import sys, argparse, json, colorsys
import numpy as np
from PIL import Image


def load(path):
    return np.asarray(Image.open(path).convert("RGB")).astype(np.float32)


def stats(img, box):
    x0, y0, x1, y1 = box
    sub = img[y0:y1, x0:x1]
    m = sub.reshape(-1, 3).mean(axis=0)
    lum = 0.2126 * m[0] + 0.7152 * m[1] + 0.0722 * m[2]
    h, s, v = colorsys.rgb_to_hsv(*(m / 255.0))
    return dict(mean=[round(float(c), 1) for c in m], lum=round(float(lum), 1),
                hue=round(h * 360.0, 1), sat=round(s, 3))


def parse_boxes(args, w, h):
    out = []
    for b in args.box:
        name = b[0]
        v = [float(x) for x in b[1:]]
        if args.frac:
            v = [v[0] * w, v[1] * h, v[2] * w, v[3] * h]
        out.append((name, [int(round(x)) for x in v]))
    return out


def waterline(img, x0, x1, ymin, ymax):
    h, w = img.shape[:2]
    rows = []
    for x in range(x0, x1, max(1, (x1 - x0) // 120)):
        col = img[ymin:ymax, x] / 255.0
        for j in range(col.shape[0] - 12):
            seg = col[j:j + 12]
            r, g, b = seg[:, 0], seg[:, 1], seg[:, 2]
            if np.all(b > r - 0.02) and np.all(seg.max(axis=1) < 0.75):
                rows.append(ymin + j)
                break
    if not rows:
        return None
    return int(np.median(rows))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["regions", "waterline", "ev"])
    ap.add_argument("images", nargs="+")
    ap.add_argument("--box", action="append", nargs=5, default=[], metavar=("NAME", "X0", "Y0", "X1", "Y1"))
    ap.add_argument("--frac", action="store_true")
    ap.add_argument("--x0", type=int, default=0)
    ap.add_argument("--x1", type=int, default=0)
    ap.add_argument("--ymin", type=int, default=0)
    ap.add_argument("--ymax", type=int, default=0)
    a = ap.parse_args()

    if a.mode == "waterline":
        img = load(a.images[0])
        h, w = img.shape[:2]
        y = waterline(img, a.x0 or int(0.05 * w), a.x1 or int(0.95 * w), a.ymin, a.ymax or h)
        print(json.dumps(dict(image=a.images[0], waterline_y=y, frame_h=h,
                              frac=round(y / h, 3) if y is not None else None)))
    elif a.mode == "regions":
        img = load(a.images[0])
        h, w = img.shape[:2]
        res = {n: stats(img, b) for n, b in parse_boxes(a, w, h)}
        print(json.dumps(dict(image=a.images[0], size=[w, h], regions=res), indent=1))
    else:
        A, B = load(a.images[0]), load(a.images[1])
        for n, b in parse_boxes(a, A.shape[1], A.shape[0]):
            sa = stats(A, b)
            sb = stats(B, b)
            ratio = sb["lum"] / max(sa["lum"], 1e-6)
            print(f"{n:24s} A {sa['mean']} lum {sa['lum']:6.1f} hue {sa['hue']:5.1f} | "
                  f"B {sb['mean']} lum {sb['lum']:6.1f} hue {sb['hue']:5.1f} | B/A {ratio:5.3f} "
                  f"EV {np.log2(max(ratio, 1e-6)):+.2f}")
