"""Round-15 lighting measurement (QA-07-1 / -5 / -7 / -11). Plain python3 + PIL/numpy, no Blender.

It is `light_r14_measure` with three changes, each of which is a round-15 brief item:

  * cam02 was RE-STATIONED for round 08 (lead, qa_cameras.py: SSE 75 m / 24 mm -> NNE (-79.8, 24.4, 1.55) / 40 mm).
    Every round-14 cam02 box therefore lands on unrelated pixels and is replaced here. The new station is a close
    three-quarter of the rotunda from below with NO WATER IN FRAME, so the old `water` box is RETIRED rather than
    moved: there is nothing on cam02 to measure it on. The boxes below were picked on
    renders/previews/lighting/r15b_r14BEFORE_02e.png and are listed in docs/lighting_notes.md 25.1.
  * cam01 gains `flank`, QA-07-1's own box (100 900 400 960), which round 14 measured in prose without a script,
    and `dark_frac` / `flank` are printed with their QA-07 windows.
  * cam03 gains the frame's black fraction (QA-07-5's second half: <= 20 % of the frame under lum 10).

    python3 scripts/light_r15_measure.py --shade renders/previews/lighting/r15b_*.png
"""
import sys, os, json, argparse
from pathlib import Path
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import light_r10_measure as m10
import light_r14_measure as m14

ROOT = Path(__file__).resolve().parents[1]

BOXES = {k: dict(size=v["size"], boxes=dict(v["boxes"])) for k, v in m14.BOXES.items()}

# ---- cam01: QA-07-1's open-lagoon flank, which is not one of QA's round-03 boxes
BOXES["01"]["boxes"]["flank"] = (100, 900, 400, 960)

# ---- cam02, RE-BASED on the round-08 NNE station (see the module docstring)
BOXES["02"] = dict(size=(1280, 720), boxes={
    # the shaded fluted column shafts under the two near arches: QA-07-11's "shade pier" on this station, and
    # the surfaces the anti-sun shade fill lands on most directly (they face the camera, i.e. NNE, i.e. the
    # SHADE_FILL NNE lamp's own axis).
    "shade_pier":   (573, 227, 653, 387),
    "shade_pier_r": (700, 240, 760, 380),
    # the arch soffits -- the deep coffered vaults over the two openings
    "shade_soffit": (400, 280, 520, 355),
    # the shaded relief frieze of the attic zone, high in frame
    "shade_frieze": (250, 40, 420, 110),
    # the SUNLIT pier base at the left edge: the denominator / warm reference for the boxes above
    "sunlit_pier":  (273, 340, 350, 500),
    # a clear patch of visible sky, upper left: a HOLD (camera rays, which no round-15 socket touches)
    "sky":          (60, 40, 200, 140),
})

WIN = dict(m14.WIN)
WIN.pop(("02", "water"), None)
WIN[("02", "shade_pier")] = dict(hue_qa=(25.0, 60.0), sat=(0.0, 0.35), ref="QA-07-11; r05 41.6")
WIN[("02", "shade_pier_r")] = dict(hue_qa=(25.0, 60.0), sat=(0.0, 0.35), ref="QA-07-11")
WIN[("01", "near_water_sky")] = dict(hue=(185.0, 200.0), lum=(79.1, 131.8), ref="QA-07-1: ref 105.4 / 190.0 / 0.248")
WIN[("01", "flank")] = dict(hue=(0.0, 210.0), lum=(114.3, 190.5), ref="QA-07-1: ref 152.4 / 200.3")
WIN[("01", "shaded_attic")] = dict(hue=(23.5, 35.5), sat=(0.0, 0.50), lum=(103.5, 126.5), ref="QA-07-7: ref 118.8")
WIN[("01", "sunlit_attic")] = dict(lum=(178.0, 201.0), ref="HOLD")
WIN[("01", "water_refl")] = dict(hue=(25.0, 45.0), ref="HOLD, R-B >= +35")
WIN[("05", "water_band")] = dict(lum=(70.0, 117.0), sat=(0.24, 1.0), ref="QA-07-1: ref 063 93.4")
WIN[("03", "outer_row")] = dict(hue_qa=(25.0, 60.0), ref="QA-07-5: ratio >= 0.15")


def cam_of(name):
    stem = Path(name).stem
    tail = stem.split("_")[-1]
    if len(tail) >= 2 and tail[:2] in BOXES:
        return tail[:2]
    for k in BOXES:
        if f"_{k}" in stem:
            return k
    return None


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
                            dark=float((a.max(2) < 10.0).mean()))     # QA-07-5: <= 20 %
    if cam == "02":
        den = max(1e-6, out["sunlit_pier"]["lum"])
        for k in ("shade_pier", "shade_pier_r", "shade_soffit", "shade_frieze"):
            out[k]["ratio"] = out[k]["lum"] / den
    return cam, out


def verdict(cam, k, s):
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
                  f"R-B {s['rb']:+7.1f}{extra}{verdict(cam, k, s)}")
        res[Path(f).name] = out
    if a.json:
        Path(a.json).write_text(json.dumps(res, indent=1))
        print(f"\n[r15] wrote {a.json}")
