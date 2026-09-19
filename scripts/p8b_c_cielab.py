#!/usr/bin/env python3
"""Phase 8b item c — the CIELAB measurement of the cam02 shaded stone, as a script.

r3 review 6: item c's numbers (docs/briefs/phase8b_viewer_fix_report.md "## c") were the strongest
evidence that round produced and had no committed tool.  This is it.  No Blender, no Chrome: it reads
frames that are already on disk.

    python3 scripts/p8b_c_cielab.py                          # Cycles + photo (both committed)
    python3 scripts/p8b_c_cielab.py viewer=renders/web/gate9_cam02.png
    python3 scripts/p8b_c_cielab.py --cam 02 --json out.json  a=x.png b=y.png

Fixture: `scripts/light_r16_measure.BOXES[cam]` — the same boxes every lighting round since 16 uses,
so nothing here invents a region.  Each frame is resampled to the fixture's own size (1280x720 for
cam02) exactly as `light_r14_measure.load` does it, the box is cropped, and CIELAB is taken PER PIXEL
(sRGB EOTF -> linear -> XYZ D65 -> L*a*b*, D65 white) and averaged over the box: that is the method
the published table used, and it reproduces it to 0.01.  The Lab of the box's MEAN COLOUR is printed
beside it as `b*(mean)`, because the two are not the same number on a high-contrast box (shade_pier
-5.01 against -4.68) and a later round should know which one it is quoting.

Published table (report ## c, b*): shade_pier viewer -2.73 / Cycles -5.01 / photo +10.89;
shade_pier_r -10.97 / -18.35 / +10.99; shade_arch +0.19 / -3.29 / +5.33;
shade_frieze (control) +11.44 / +12.24 / +11.07.

REPRODUCED: the Cycles column exactly (-5.01 / -18.34 / -3.28 / +12.25) and the VIEWER column
exactly (-2.72 / -10.97 / +0.19 / +11.44) from a fresh Phase 8a desktop capture, which also shows
that the 8a card relight moves no stone box at all (`?cardsun=0` and the adopted default agree to the
second decimal on every box here).
NOT REPRODUCED, and this is a finding: the PHOTO column.  ref_062 is a different camera at a
different framing, so the cam02 fixture does not land on the same stone there; resampled into the
fixture it reads +14.10 / +13.22 / +7.49 / +10.50 against the published +10.89 / +10.99 / +5.33 /
+11.07.  The published photo numbers therefore came from a box set placed on the photograph itself,
which was never written down — so the photo column of item c is NOT reproducible from what is in the
tree, and a later round must re-place those boxes (and say where) before quoting it.  Pass any cam02 capture as `viewer=...`.
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

MAIN = Path("/Users/dk/Projects/3d render blender 3rd attempt building")
sys.path.insert(0, str(MAIN / "scripts"))
import light_r16_measure as L16  # noqa: E402
import light_r14_measure as L14  # noqa: E402

DEFAULT_FRAMES = {
    "cycles": MAIN / "renders/previews/qa/round13_02_lagoon_ne_threequarter_cycles.png",
    "photo": MAIN / "reference/photos/raw/ref_062_rotunda_Palace_of_Fine_Arts_View_of_Rotunda_from_north_eas.jpg",
}
# sRGB D65 -> XYZ (IEC 61966-2-1), and the D65 white the Lab conversion is relative to
M_RGB2XYZ = np.array([[0.4124564, 0.3575761, 0.1804375],
                      [0.2126729, 0.7151522, 0.0721750],
                      [0.0193339, 0.1191920, 0.9503041]])
WHITE_D65 = np.array([0.9504559, 1.0, 1.0890578])


def srgb_to_lab(rgb255):
    """(..., 3) sRGB 0-255 -> (..., 3) CIELAB.  Works on one colour or a whole crop."""
    c = np.asarray(rgb255, dtype=np.float64) / 255.0
    lin = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    xyz = lin @ M_RGB2XYZ.T
    t = xyz / WHITE_D65
    f = np.where(t > (6 / 29) ** 3, np.cbrt(t), t / (3 * (6 / 29) ** 2) + 4 / 29)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]),
                     200 * (f[..., 1] - f[..., 2])], axis=-1)


def measure(path, cam):
    spec = L16.BOXES[cam]
    a = L14.load(str(path), spec["size"])
    out = {}
    for name, (x0, y0, x1, y1) in spec["boxes"].items():
        crop = a[y0:y1, x0:x1].reshape(-1, 3)
        lab = srgb_to_lab(crop).mean(0)                 # the published method
        mean_lab = srgb_to_lab(crop.mean(0))            # the Lab of the mean colour, for comparison
        chroma = float(np.hypot(lab[1], lab[2]))
        hab = float(np.degrees(np.arctan2(lab[2], lab[1])) % 360.0)
        rgb = crop.mean(0)
        out[name] = dict(rgb=[float(v) for v in rgb], L=float(lab[0]), a=float(lab[1]),
                         b=float(lab[2]), chroma=chroma, h_ab=hab, b_of_mean=float(mean_lab[2]),
                         r_minus_b=float(rgb[0] - rgb[2]))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cam", default="02")
    ap.add_argument("--json", default=None)
    ap.add_argument("frames", nargs="*", help="label=path; the defaults are cycles= and photo=")
    args = ap.parse_args()
    frames = dict(DEFAULT_FRAMES)
    for f in args.frames:
        if "=" not in f:
            print(f"ignored {f!r}: frames are label=path")
            continue
        k, v = f.split("=", 1)
        frames[k] = Path(v)
    data = {}
    names = list(L16.BOXES[args.cam]["boxes"])
    print(f"== cam{args.cam} CIELAB (D65), boxes light_r16_measure.BOXES['{args.cam}'] ==")
    print(f"{'box':14s} {'frame':10s} {'L*':>7s} {'a*':>7s} {'b*':>7s} {'C*':>7s} {'h_ab':>7s} "
          f"{'b*(mean)':>9s} {'R-B':>7s}")
    for lbl, path in frames.items():
        if not Path(path).exists():
            print(f"{'':14s} {lbl:10s} MISSING {path}")
            continue
        data[lbl] = measure(path, args.cam)
    for box in names:
        for lbl in data:
            r = data[lbl][box]
            print(f"{box if lbl == list(data)[0] else '':14s} {lbl:10s} {r['L']:7.2f} {r['a']:7.2f} "
                  f"{r['b']:7.2f} {r['chroma']:7.2f} {r['h_ab']:7.1f} {r['b_of_mean']:9.2f} "
                  f"{r['r_minus_b']:7.1f}")
    print("\n  b* > 0 is warm stone; the item-c defect is b* going NEGATIVE (blue-violet) in the shade.")
    print("  The acceptance the report proposed for the upstream fix: b* >= +5, h_ab 40-80 deg,")
    print("  R-B >= +10 on the three shade boxes, with shade_frieze held at +11.4 +- 1.5.")
    if args.json:
        Path(args.json).write_text(json.dumps(data, indent=1))
        print(f"  wrote {args.json}")


if __name__ == "__main__":
    main()
