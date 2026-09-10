"""Round-17 lighting measurement (QA-09-6 cam02 soffit, QA-09-5 / ARCH-r8 cam03 near column, the hero holds).

It is `light_r16_measure` with three additions, and ONE deliberate non-change:

  * **cam02's boxes are NOT re-based in pixels.** Round-16 picked them on the 27 mm frame of the round-08 NNE
    station and the station and lens have not moved; what moved is the GEOMETRY behind `shade_arch` (ARCH r8
    replaced the chord-triangle plate inside the arch with the real coffered barrel). Round-17 brief item 0 asks
    for the before / after of the SAME box on the SAME rig, so the pixel rectangles are held fixed on purpose and
    the r16 row in docs/lighting_notes.md 26.6 is directly comparable. (`shade_arch` is renamed nowhere; it now
    lands on the coffered soffit instead of on a flat plate 2 m in front of it.)
  * **cam03 grows the near-column boxes** (ARCH r8 hand-off: `ARCH_colonnade_south_column_028` enters the frame at
    x 857 and runs off the right edge, 423 px = 33 % of the width, mean luminance 3.7 / p95 12.1 / max 30.9).
    `near_column` is that shaft; `flute` reports the modulation ACROSS it, which is the brief's acceptance:
    p95 >= 25 lum and ridge - floor >= 8 lum. `near_shaft` (the old x 0-420 box) is kept and reported so the
    round-14..16 rows stay readable.
  * **cam04 grows the ceiling boxes** (`light_measure.REGIONS["ceiling"]` fractions, evaluated on the 1280x720
    frame): the coffer field, the two vault-soffit bands and the frame's own sky, as ratios. Round-17's lever for
    cam02's soffit is the two warm interior fills, whose hold is exactly these ratios (QA-02-12 / QA-04-7).

    python3 scripts/light_r17_measure.py --shade renders/previews/lighting/r17_*.png
"""
import sys, os, json, argparse
from pathlib import Path
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import light_r10_measure as m10
import light_r14_measure as m14
import light_r16_measure as m16
import light_measure as lm

ROOT = Path(__file__).resolve().parents[1]

BOXES = {k: dict(size=v["size"], boxes=dict(v["boxes"])) for k, v in m16.BOXES.items()}

# ---- cam03: the near column ARCH r8 handed over, plus the flute-modulation band inside it.
# The shaft's visible silhouette is x 857 -> 1280 (it runs off the right edge). 900-1270 is ARCH's own window, kept
# so their 3.7 / 12.1 / 30.9 and this script's numbers are the same measurement.
BOXES["03"]["boxes"]["near_column"] = (900, 150, 1270, 700)
# the band the flute profile is taken across: mid-shaft, clear of the base (z 0.4 + 0.9 m plinth) and of the
# foliage clumps ENV parks at the top of the frame.
BOXES["03"]["boxes"]["flute_band"] = (900, 330, 1270, 470)

# ---- cam04: the ceiling ratios, from light_measure's fractional regions at 1280x720
CEIL = {k: (int(round(x * 1280)), int(round(y * 720)), int(round((x + w) * 1280)), int(round((y + h) * 720)))
        for k, (x, y, w, h) in lm.REGIONS["ceiling"].items()}
BOXES["04"] = dict(size=(1280, 720), boxes=dict(CEIL))

WIN = dict(m16.WIN)
WIN[("03", "near_column")] = dict(ref="ARCH r8: mean 3.7 / p95 12.1 / max 30.9; brief p95 >= 25")
WIN[("02", "shade_arch")] = dict(hue_qa=(25.0, 60.0), sat=(0.0, 0.35), ref="QA-09-6 Cycles 249.5; brief hue 25-60")

# brief item 1 / 2 acceptance, checked in code so the verdict cannot drift from the text
TESTS = {
    ("03", "near_column", "p95"): (25.0, 1e9, "brief: flute modulation visible"),
    ("03", "flute_band", "ridge_floor"): (8.0, 1e9, "brief: flute ridge - flute floor >= 8 lum"),
    ("02", "shade_arch", "rib_field"): (15.0, 1e9, "brief: coffer rib / field contrast >= 15 lum"),
}

cam_of = m16.cam_of


def profile_stats(a):
    """Flute modulation across a shaft: the per-column mean luminance profile, and the gap between the bright
    quarter (flute ridges / arrises) and the dark quarter (flute hollows) of that profile. Measured on the
    profile, not on the raw pixels, so vertical texture and noise average out first."""
    lum = a.max(2)
    prof = lum.mean(0)
    if prof.size < 8:
        return dict(p95=float(np.percentile(lum, 95)), ridge_floor=0.0, ridge=0.0, floor=0.0)
    n = max(1, prof.size // 4)
    s = np.sort(prof)
    floor, ridge = float(s[:n].mean()), float(s[-n:].mean())
    return dict(p95=float(np.percentile(lum, 95)), ridge=ridge, floor=floor, ridge_floor=ridge - floor)


def measure(path):
    cam = cam_of(path)
    if cam is None:
        return None
    spec = BOXES[cam]
    a = m14.load(path, spec["size"])
    out = {}
    for k, (x0, y0, x1, y1) in spec["boxes"].items():
        sub = a[y0:y1, x0:x1]
        out[k] = m10.stats(sub)
        lum = sub.max(2)
        out[k]["p95"] = float(np.percentile(lum, 95))
        out[k]["max"] = float(lum.max())
    if cam == "03":
        den = max(1e-6, out["sunlit_rotunda"]["lum"])
        for k in ("walk", "shaft_flank", "outer_row", "near_shaft", "near_column"):
            out[k]["ratio"] = out[k]["lum"] / den
        for k in ("near_column", "flute_band"):
            x0, y0, x1, y1 = spec["boxes"][k]
            out[k].update(profile_stats(a[y0:y1, x0:x1]))
        out["frame"] = dict(lum=float(a.max(2).mean()), hue=0.0, sat=0.0, rb=0.0,
                            dark=float((a.max(2) < 10.0).mean()), p95=0.0, max=0.0)
    if cam == "02":
        den = max(1e-6, out["sunlit_pier"]["lum"])
        for k in ("shade_pier", "shade_pier_r", "shade_arch", "shade_frieze"):
            out[k]["ratio"] = out[k]["lum"] / den
        # coffer readability inside the arch: the rib / field split of the soffit box, taken as the bright and dark
        # quarters of its own luminance histogram (the ribs are the bright lattice, the coffer fields the dark
        # panels between them). Flat plate -> ~0; a lit coffered barrel -> tens of lum.
        x0, y0, x1, y1 = spec["boxes"]["shade_arch"]
        lum = np.sort(a[y0:y1, x0:x1].max(2).ravel())
        n = max(1, lum.size // 4)
        out["shade_arch"]["rib_field"] = float(lum[-n:].mean() - lum[:n].mean())
    if cam == "04":
        den = max(1e-6, out["own_sky"]["lum"])
        for k in out:
            out[k]["ratio"] = out[k]["lum"] / den
    return cam, out


def _verdict(cam, k, s):
    out = m16._verdict(cam, k, s)
    for (c, box, key), (lo, hi, why) in TESTS.items():
        if (c, box) == (cam, k) and key in s:
            out += f"  {key} {'PASS' if lo <= s[key] <= hi else 'FAIL'}[>={lo:g}]"
    return out


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
            extra += f"  p95 {s['p95']:.1f}" if s.get("p95") else ""
            extra += f"  ridge/floor {s['ridge']:.1f}/{s['floor']:.1f} d {s['ridge_floor']:.1f}" if "ridge" in s else ""
            extra += f"  rib-field {s['rib_field']:.1f}" if "rib_field" in s else ""
            print(f"   {k:15s} lum {s['lum']:6.1f}  hue {s['hue']:6.1f}  sat {s['sat']:.3f}  "
                  f"R-B {s['rb']:+7.1f}{extra}{_verdict(cam, k, s)}")
        res[Path(f).name] = out
    if a.json:
        Path(a.json).write_text(json.dumps(res, indent=1))
        print(f"\n[r17] wrote {a.json}")
