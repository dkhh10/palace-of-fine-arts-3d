#!/usr/bin/env python3
"""Crop-pair composites for QA decisions (python3 + PIL; images only).

  python3 scripts/qa_crops.py --a RENDER.png --b PHOTO.jpg --out OUT.png [--transform S DX DY] [--width 900]
      --crop name x0 y0 x1 y1 [--crop ...]  [--bcrop name x0 y0 x1 y1 ...]
  Each --crop is a box on image A. The matching box on B is either the --bcrop with the same name or, with
  --transform (the scale/dx/dy printed by qa_silhouette.py align: B pixel -> A pixel is p*S + D), the A box mapped
  back onto B. Every pair is rendered as A-crop | B-crop at the same on-screen scale, stacked vertically, with the
  pixel boxes and per-box mean sRGB / lum / hue / sat burnt in, so one image carries the decision and its numbers.
"""
import argparse, colorsys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

FONT = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"


def stats(im, box):
    a = np.asarray(im.crop(box).convert("RGB")).astype(np.float32).reshape(-1, 3).mean(axis=0)
    lum = 0.2126 * a[0] + 0.7152 * a[1] + 0.0722 * a[2]
    h, s, v = colorsys.rgb_to_hsv(*(a / 255.0))
    return f"{a[0]:.0f},{a[1]:.0f},{a[2]:.0f} lum {lum:.1f} hue {h*360:.1f} sat {s:.3f} R-B {a[0]-a[2]:.0f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", required=True); ap.add_argument("--b", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--transform", type=float, nargs=3, default=None, metavar=("S", "DX", "DY"))
    ap.add_argument("--crop", action="append", nargs=5, default=[], metavar=("NAME", "X0", "Y0", "X1", "Y1"))
    ap.add_argument("--bcrop", action="append", nargs=5, default=[], metavar=("NAME", "X0", "Y0", "X1", "Y1"))
    ap.add_argument("--width", type=int, default=900, help="on-screen width of each crop panel")
    ap.add_argument("--label-a", default="RENDER"); ap.add_argument("--label-b", default="PHOTO")
    a = ap.parse_args()
    A, B = Image.open(a.a).convert("RGB"), Image.open(a.b).convert("RGB")
    bmap = {c[0]: [int(float(v)) for v in c[1:]] for c in a.bcrop}
    font = ImageFont.truetype(FONT, 18)
    panels = []
    for c in a.crop:
        name, box = c[0], [int(float(v)) for v in c[1:]]
        if name in bmap:
            bbox = bmap[name]
        elif a.transform:
            s, dx, dy = a.transform
            bbox = [int(round((box[0] - dx) / s)), int(round((box[1] - dy) / s)),
                    int(round((box[2] - dx) / s)), int(round((box[3] - dy) / s))]
        else:
            raise SystemExit(f"no B box for {name}: give --bcrop or --transform")
        bbox = [max(0, bbox[0]), max(0, bbox[1]), min(B.width, bbox[2]), min(B.height, bbox[3])]
        ca, cb = A.crop(box), B.crop(bbox)
        w = a.width
        ca_s = ca.resize((w, int(ca.height * w / ca.width)), Image.LANCZOS)
        cb_s = cb.resize((w, int(cb.height * w / cb.width)), Image.LANCZOS)
        h = max(ca_s.height, cb_s.height) + 52
        p = Image.new("RGB", (2 * w + 10, h), (18, 18, 20))
        p.paste(ca_s, (0, 52)); p.paste(cb_s, (w + 10, 52))
        d = ImageDraw.Draw(p)
        d.text((4, 2), f"{a.label_a} {name} box {box}  {stats(A, box)}", font=font, fill=(255, 220, 120))
        d.text((w + 14, 2), f"{a.label_b} box {bbox}", font=font, fill=(140, 230, 255))
        d.text((4, 26), f"{a.label_a}", font=font, fill=(255, 220, 120))
        d.text((w + 14, 26), f"{a.label_b} {stats(B, bbox)}", font=font, fill=(140, 230, 255))
        panels.append(p)
        print(f"{name:14s} A {box} {stats(A, box)} | B {bbox} {stats(B, bbox)}")
    H = sum(p.height + 6 for p in panels)
    sheet = Image.new("RGB", (panels[0].width, H), (18, 18, 20))
    y = 0
    for p in panels:
        sheet.paste(p, (0, y)); y += p.height + 6
    sheet.save(a.out)
    print("wrote", a.out, sheet.size)


if __name__ == "__main__":
    main()
