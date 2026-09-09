"""Round-14 lighting measurement (QA-06-2 / -7 / -13). Plain python3 + PIL/numpy, no Blender.

The four-camera SHADE table is the round's deliverable, so every box is declared here, once, with what it is and
where its window comes from. The hero's boxes are QA's own (light_r10_measure.BOXES); the cam02 / 03 / 05 / 06
boxes are stated here because QA round 06 reported those numbers in prose without a script.

    python3 scripts/light_r14_measure.py --shade before/ after/            # a directory or a list of frames
    python3 scripts/light_r14_measure.py --frames a_01c.png a_03e.png ...
"""
import sys, os, json, argparse
from pathlib import Path
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import light_r10_measure as m10

ROOT = Path(__file__).resolve().parents[1]

# ------------------------------------------------------------------ the boxes, per camera, at the stated size
# cam01 (1920x1080): QA's own round-03 boxes, via light_r10_measure.
# cam02 / 03 / 05 / 06 are measured at 1280x720 (the preview size QA renders them at).
BOXES = {
    "01": dict(size=(1920, 1080), boxes={
        # the round's HOLD: the shade window r12/r13 landed and r14 may not break
        "shaded_attic":   (1110, 225, 1150, 260),
        "sunlit_attic":   (900, 222, 1020, 256),
        "entablature":    (900, 262, 1020, 296),
        "columns":        (680, 280, 1240, 470),
        "water_refl":     (900, 760, 1020, 840),
        "near_water_sky": (1150, 1000, 1450, 1050),
        "sky_top":        (1210, 22, 1690, 76),
        "sky_left":       (38, 92, 192, 157),
        "south_wing":     (60, 480, 560, 600),
        "north_wing":     (1360, 480, 1860, 600),
        "shore_band":     (700, 600, 1200, 740),
    }),
    "02": dict(size=(1280, 720), boxes={
        # the shaded stone on cam02 -- the rotunda's shaded pier flank and the shaded soffit under the arch
        "shade_pier":     (600, 110, 660, 200),
        "shade_soffit":   (360, 205, 470, 245),
        "shade_balus":    (180, 470, 420, 520),
        "water":          (300, 640, 900, 715),      # QA-06-2's cam02 number (hue 39.4 -> 265.5) lives here
    }),
    "03": dict(size=(1280, 720), boxes={
        "walk":           (420, 560, 900, 720),      # QA-06-2: hue 222.6, window 25-60
        "shaft_flank":    (480, 150, 560, 600),      # QA-06's re-based shade test (0.30-0.70 of sunlit)
        "outer_row":      (880, 120, 1200, 600),     # QA-06-7: >= 0.15 of sunlit, hue 25-60
        "near_shaft":     (0, 150, 420, 720),        # the retired, sky-occluded box, reported only
        "sunlit_rotunda": (560, 0, 880, 320),        # the denominator of every cam03 ratio
    }),
    "05": dict(size=(1280, 720), boxes={
        # QA-06-3's cam05 band, in fractions of the frame: 0.35-0.75 w x 0.86-0.99 h
        "water_band":     (448, 619, 960, 713),
        "attic_band":     (430, 150, 860, 230),
    }),
    "06": dict(size=(1280, 720), boxes={
        "roofs":          (120, 150, 320, 190),      # the north wing's colonnade roof run
        "plaza":          (760, 90, 1100, 180),      # the near ground / apron QA calls "near ground"
        "trees":          (180, 40, 420, 140),       # the tree mass behind the north wing
        "horizon":        (0, 0, 1280, 220),         # environment's crop (mean / std only)
    }),
}

# windows. `hue_shade` is the lead's brief for round 14 (a neutral cool grey-blue, 195-230 at sat <= 0.35);
# `hue_qa` is QA-06-2's acceptance for the same box (warm, within 15 deg of the round-05 / ref-105 neutrals).
# They disagree, so BOTH are printed and neither is silently chosen. See docs/lighting_notes.md 24.2.
WIN = {
    ("01", "shaded_attic"): dict(hue=(23.5, 35.5), sat=(0.0, 0.50), lum=(103.5, 126.5), ref="ref 169 115.0/29.5/0.425"),
    ("03", "walk"):         dict(hue_qa=(25.0, 60.0), hue_brief=(195.0, 230.0), sat=(0.0, 0.35), ref="r05 38.4"),
    ("02", "shade_pier"):   dict(hue_qa=(25.0, 60.0), hue_brief=(195.0, 230.0), sat=(0.0, 0.35), ref="r05 41.6"),
    ("06", "roofs"):        dict(hue_qa=(22.3, 52.3), hue_brief=(195.0, 230.0), sat=(0.0, 0.35), ref="r05 37.3"),
    ("06", "plaza"):        dict(hue_qa=(21.6, 51.6), hue_brief=(195.0, 230.0), sat=(0.0, 0.35), ref="r05 36.6"),
    ("06", "trees"):        dict(hue_qa=(22.6, 52.6), hue_brief=(195.0, 230.0), sat=(0.0, 0.35), ref="r05 37.6"),
    ("05", "water_band"):   dict(hue_qa=(40.0, 80.0), sat=(0.24, 1.0), ref="ref 063 93.4/64.9/0.306"),
    ("02", "water"):        dict(hue_qa=(185.0, 200.0), ref="r05 41.3"),
}


def cam_of(name):
    """'r14_A_03e.png' -> '03'. The sweep writes <prefix>_<tag>_<NN><engine>.png."""
    stem = Path(name).stem
    for tail in (stem.split("_")[-1],):
        if len(tail) >= 2 and tail[:2] in BOXES:
            return tail[:2]
    for k in BOXES:
        if f"_{k}" in stem:
            return k
    return None


def load(path, size):
    a = np.asarray(Image.open(path).convert("RGB"), dtype=np.float64)
    if (a.shape[1], a.shape[0]) != size:
        a = np.asarray(Image.fromarray(a.astype(np.uint8)).resize(size, Image.LANCZOS), dtype=np.float64)
    return a


def measure(path):
    cam = cam_of(path)
    if cam is None:
        return None
    spec = BOXES[cam]
    a = load(path, spec["size"])
    out = {}
    for k, (x0, y0, x1, y1) in spec["boxes"].items():
        out[k] = m10.stats(a[y0:y1, x0:x1])
    if cam == "03":
        den = max(1e-6, out["sunlit_rotunda"]["lum"])
        for k in ("walk", "shaft_flank", "outer_row", "near_shaft"):
            out[k]["ratio"] = out[k]["lum"] / den
    if cam == "06":
        v = a.max(2)
        mx, mn = a.max(2), a.min(2)
        d = mx - mn
        r, g, b = a[:, :, 0], a[:, :, 1], a[:, :, 2]
        h = np.zeros_like(mx)
        m = (d > 0) & (mx == r); h[m] = (60 * ((g - b)[m] / d[m])) % 360
        m = (d > 0) & (mx == g); h[m] = 60 * ((b - r)[m] / d[m]) + 120
        m = (d > 0) & (mx == b); h[m] = 60 * ((r - g)[m] / d[m]) + 240
        out["frame"] = dict(lum=float(v.mean()), hue=float(np.median(h)),
                            sat=float(np.median(np.where(mx > 0, d / np.maximum(mx, 1e-9), 0))), rb=0.0,
                            violet=float(((h > 200) & (h < 300)).mean()))
    if cam == "01":
        v = a.max(2)
        out["frame"] = dict(lum=float(v.mean()), hue=0.0, sat=0.0, rb=0.0, violet=0.0)
    return cam, out


def verdict(cam, k, s):
    w = WIN.get((cam, k))
    if not w:
        return ""
    bits = []
    if "hue" in w:
        lo, hi = w["hue"]; bits.append(f"hue {'PASS' if lo <= s['hue'] <= hi else 'FAIL'}[{lo:.0f}-{hi:.0f}]")
    if "hue_qa" in w:
        lo, hi = w["hue_qa"]; bits.append(f"QA {'PASS' if lo <= s['hue'] <= hi else 'FAIL'}[{lo:.0f}-{hi:.0f}]")
    if "hue_brief" in w:
        lo, hi = w["hue_brief"]; bits.append(f"brief {'PASS' if lo <= s['hue'] <= hi else 'FAIL'}[{lo:.0f}-{hi:.0f}]")
    if "sat" in w:
        lo, hi = w["sat"]; bits.append(f"sat {'PASS' if lo <= s['sat'] <= hi else 'FAIL'}")
    if "lum" in w:
        lo, hi = w["lum"]; bits.append(f"lum {'PASS' if lo <= s['lum'] <= hi else 'FAIL'}")
    return "  " + " ".join(bits)


def frames_of(paths):
    out = []
    for p in paths:
        p = Path(p)
        out.extend(sorted(p.glob("*.png")) if p.is_dir() else [p])
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--shade", nargs="+", required=True)
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    res = {}
    for f in frames_of(a.shade):
        m = measure(f)
        if m is None:
            continue
        cam, out = m
        print(f"\n-- {Path(f).name}   (cam {cam}, boxes at {BOXES[cam]['size'][0]}x{BOXES[cam]['size'][1]})")
        for k, s in out.items():
            extra = f"  ratio {s['ratio']:.3f}" if "ratio" in s else ""
            extra += f"  violet {100*s['violet']:.1f}%" if "violet" in s else ""
            print(f"   {k:16s} lum {s['lum']:6.1f}  hue {s['hue']:6.1f}  sat {s['sat']:.3f}  "
                  f"R-B {s['rb']:+7.1f}{extra}{verdict(cam, k, s)}")
        res[Path(f).name] = out
    if a.json:
        Path(a.json).write_text(json.dumps(res, indent=1))
        print(f"\n[r14] wrote {a.json}")
