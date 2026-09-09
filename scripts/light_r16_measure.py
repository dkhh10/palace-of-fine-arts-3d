"""Round-16 lighting measurement (QA-08-2 / -3 / -7). Plain python3 + PIL/numpy, no Blender.

It is `light_r15_measure` with ONE change, which is round-16 brief item 0: **cam02's boxes are re-based again**.
The lead changed cam02's lens from 40 mm to 27 mm after QA round 08 (commit 7fb6dd4, QA-08-1: the 40 mm frame
clipped the dome), so the round-15 box set -- which was itself picked on the 40 mm frame of the round-08 NNE
station -- lands on unrelated pixels: `sunlit_pier` falls on foreground planting and `shade_frieze` on open sky
(`/tmp` overlay of r16_r16BEFORE_02e.png, docs/lighting_notes.md 26.1). Every cam02 box below is NEW.

    python3 scripts/light_r16_measure.py --shade renders/previews/lighting/r16_*.png
"""
import sys, os, json, argparse
from pathlib import Path
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import light_r10_measure as m10
import light_r14_measure as m14
import light_r15_measure as m15

ROOT = Path(__file__).resolve().parents[1]

BOXES = {k: dict(size=v["size"], boxes=dict(v["boxes"])) for k, v in m15.BOXES.items()}

# ---- cam02, RE-BASED on the 27 mm frame of the round-08 NNE station (-79.8, 24.4, 1.55)
BOXES["02"] = dict(size=(1280, 720), boxes={
    # the two fluted shaft clusters of the camera-facing (NNE) rotunda face, left and right of the near arches.
    # These are QA-08-2's "camera-facing side": they face straight down the LIGHT_shade_fill NNE lamp's axis.
    "shade_pier":   (405, 265, 465, 395),
    "shade_pier_r": (875, 255, 930, 385),
    # the deep shade inside the left arch -- the darkest, most saturated part of the defect
    "shade_arch":   (580, 275, 690, 355),
    # the entablature / frieze band across the front of the rotunda, above the arches
    "shade_frieze": (500, 150, 700, 200),
    # the SUNLIT denominator: the warm north-colonnade wall to the right of the rotunda, the one large surface in
    # this frame that takes direct sun (lum 165.5 / hue 45.6 / sat 0.384 on the BEFORE frame). The round-15
    # `sunlit_pier` box is foreground planting at 27 mm, and a box 50 px higher is half sky: hue 159 at sat 0.055,
    # i.e. QA-08-2's `shade_pier_r / sunlit_pier = 1.046` was a ratio against a piece of sky, not against stone.
    "sunlit_pier":  (950, 465, 1090, 510),
    # clear sky, upper left: a HOLD (camera rays; no lighting socket of rounds 15-16 touches them)
    "sky":          (60, 40, 200, 140),
})

WIN = dict(m15.WIN)
for k in ("shade_pier", "shade_pier_r", "shade_arch", "shade_frieze"):
    WIN[("02", k)] = dict(hue_qa=(25.0, 60.0), sat=(0.0, 0.35), ref="QA-08-2: ref 062 warm pink-grey")
WIN[("01", "shaded_attic")] = dict(hue=(23.5, 35.5), sat=(0.0, 0.50), lum=(103.5, 126.5), ref="QA-08-7 / r16 hold")
WIN[("01", "sunlit_attic")] = dict(lum=(178.0, 201.0), sat=(0.53, 0.62), ref="QA-08-3: ref 0.582 / R-B 134.2")
WIN[("01", "columns")] = dict(hue_brief=(20.5, 28.5), ref="QA-08-3 brief: hue 24.5 +- 4")
WIN[("03", "walk")] = dict(hue_qa=(25.0, 60.0), sat=(0.0, 0.35), ref="QA-08-7: was 92.1 / 0.138")

cam_of = m15.cam_of


def measure(path):
    cam = cam_of(path)
    if cam is None:
        return None
    spec = BOXES[cam]
    a = m14.load(path, spec["size"])
    out = {}
    for k, (x0, y0, x1, y1) in spec["boxes"].items():
        out[k] = m10.stats(a[y0:y1, x0:x1])
    if cam == "03":
        den = max(1e-6, out["sunlit_rotunda"]["lum"])
        for k in ("walk", "shaft_flank", "outer_row", "near_shaft"):
            out[k]["ratio"] = out[k]["lum"] / den
        out["frame"] = dict(lum=float(a.max(2).mean()), hue=0.0, sat=0.0, rb=0.0,
                            dark=float((a.max(2) < 10.0).mean()))
    if cam == "02":
        den = max(1e-6, out["sunlit_pier"]["lum"])
        for k in ("shade_pier", "shade_pier_r", "shade_arch", "shade_frieze"):
            out[k]["ratio"] = out[k]["lum"] / den
    return cam, out


verdict = m15.verdict


def _verdict(cam, k, s):
    w = WIN.get((cam, k))
    if not w:
        return ""
    bits = []
    for key, label in (("hue", "hue"), ("hue_qa", "QA"), ("hue_brief", "brief")):
        if key in w:
            lo, hi = w[key]
            bits.append(f"{label} {'PASS' if lo <= s['hue'] <= hi else 'FAIL'}[{lo:.0f}-{hi:.0f}]")
    for key in ("sat", "lum"):
        if key in w:
            lo, hi = w[key]
            bits.append(f"{key} {'PASS' if lo <= s[key] <= hi else 'FAIL'}[{lo:g}-{hi:g}]")
    return "  " + " ".join(bits)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--shade", nargs="+", required=True)
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    res = {}
    for f in m14.frames_of(a.shade):
        m = measure(f)
        if m is None:
            continue
        cam, out = m
        print(f"\n-- {Path(f).name}   (cam {cam}, boxes at {BOXES[cam]['size'][0]}x{BOXES[cam]['size'][1]})")
        for k, s in out.items():
            extra = f"  ratio {s['ratio']:.3f}" if "ratio" in s else ""
            extra += f"  dark {100*s['dark']:.1f}%" if "dark" in s else ""
            print(f"   {k:15s} lum {s['lum']:6.1f}  hue {s['hue']:6.1f}  sat {s['sat']:.3f}  "
                  f"R-B {s['rb']:+7.1f}{extra}{_verdict(cam, k, s)}")
        res[Path(f).name] = out
    if a.json:
        Path(a.json).write_text(json.dumps(res, indent=1))
        print(f"\n[r16] wrote {a.json}")
