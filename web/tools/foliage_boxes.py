#!/usr/bin/env python3
"""The foliage acceptance boxes of docs/briefs/phase6c_foliage.md, in the round-15 table's columns.

    python3 web/tools/foliage_boxes.py --ref cycles.png viewer_a.png[:label] viewer_b.png[:label] \
        --box "60 520 700 980:near trees" [--at 1920x1080]

Every frame is resampled to --at (the default is the first image's own size) and each box reports
the columns web/README.md "Item 1c" uses, so a 6c number is comparable with a round-15 one:

  rgb     mean sRGB 0-255 per channel      lum   Rec.709 luma of the mean
  hue     hue of the mean, degrees         sat   HSV saturation of the mean
  G>R     % of pixels with G > R           p10   10th percentile of the luma (the shade floor)

The hue is the one number the 6c pass is aimed at: the round-15 cards read 57.7 deg against the
Cycles reference's 102.4 deg.
"""
import argparse, colorsys
from pathlib import Path
import numpy as np
from PIL import Image

LUMA = np.array([0.2126, 0.7152, 0.0722])


def load(path, size):
    im = Image.open(path).convert('RGB')
    if size and im.size != size:
        im = im.resize(size, Image.LANCZOS)
    return np.asarray(im).astype(np.float64)


def stats(a):
    px = a.reshape(-1, 3)
    m = px.mean(0)
    h, s, _ = colorsys.rgb_to_hsv(*(m / 255.0))
    lum = px @ LUMA
    return dict(rgb=m, lum=float(m @ LUMA), hue=h * 360.0, sat=s,
                gr=float((px[:, 1] > px[:, 0]).mean() * 100.0), p10=float(np.percentile(lum, 10)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('images', nargs='+')
    ap.add_argument('--ref')
    ap.add_argument('--at')
    ap.add_argument('--box', action='append', required=True)
    a = ap.parse_args()

    first = Image.open(a.images[0].split(':')[0])
    size = tuple(int(x) for x in a.at.split('x')) if a.at else first.size

    frames = []
    if a.ref:
        frames.append(('reference', load(a.ref, size)))
    for spec in a.images:
        p, _, label = spec.partition(':')
        frames.append((label or Path(p).stem, load(p, size)))

    for box in a.box:
        coords, _, label = box.partition(':')
        x0, y0, x1, y1 = (int(v) for v in coords.split())
        print(f"\nbox {x0} {y0} {x1} {y1}" + (f"  ({label})" if label else ""))
        print(f"{'frame':<22} {'rgb':<22} {'lum':>7} {'hue':>7} {'sat':>6} {'G>R %':>6} {'p10':>7}")
        base = None
        for name, img in frames:
            s = stats(img[y0:y1, x0:x1])
            if base is None:
                base = s
            rgb = ' '.join(f'{v:6.1f}' for v in s['rgb'])
            ratio = f"  ({s['lum'] / base['lum']:.3f}x)" if base is not s else ''
            print(f"{name:<22} {rgb:<22} {s['lum']:7.1f} {s['hue']:7.1f} {s['sat']:6.3f} "
                  f"{s['gr']:6.1f} {s['p10']:7.1f}{ratio}")


if __name__ == '__main__':
    main()
