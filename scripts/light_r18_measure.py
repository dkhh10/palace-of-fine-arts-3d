"""Round-18 lighting measurement. `light_r17_measure` plus the three things round 18 has to answer:

  * **the hero's two QA-10-2 boxes** -- `vault_field` (900 380 1010 430, acceptance 45-65 lum against ref 169's
    44.9) and `jamb` (872 400 892 480, acceptance hue 25-60 with a positive R-B against ref 169's 22.2 / +58.9).
    They are added to the cam01 box set so one command produces the blocker's verdict with the holds.
  * **the coffer FIELD's own colour on cam02** (QA-10-13). `light_r17_measure` reports the soffit box's mean hue
    and its rib/field luminance CONTRAST, and QA-10-13's point is that a large contrast is not a pass if the dark
    half is blue: "a chrome-yellow rim on an indigo coffer field". `field_hue` / `field_sat` are therefore the mean
    hue and saturation of the DARKEST QUARTILE of the same box -- the coffer panels themselves, not the ribs --
    measured on the same pixels the `rib_field` number is taken from.
  * **cam04's ratios in the engine the hold was set in.** docs/lighting_notes.md 27.6's cam04 row was measured on
    an EEVEE frame (`r17AFTER_AFTER_04e.png`), so a Cycles cam04 is not comparable with it. `--engine` is only a
    label here; the caller must pass frames from the same engine on both sides, and the printed header says which.

    python3 scripts/light_r18_measure.py --shade renders/previews/lighting/r18AFTER_*.png
"""
import sys, os, argparse, colorsys
from pathlib import Path
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import light_r10_measure as m10
import light_r14_measure as m14
import light_r17_measure as m17

ROOT = Path(__file__).resolve().parents[1]

BOXES = {k: dict(size=v["size"], boxes=dict(v["boxes"])) for k, v in m17.BOXES.items()}
# QA-10-2, in the 1920x1080 hero grid (the round-05..10 alignment maps ref 169 onto the same pixels)
BOXES["01"]["boxes"]["vault_field"] = (900, 380, 1010, 430)
BOXES["01"]["boxes"]["jamb"] = (872, 400, 892, 480)

WIN = dict(m17.WIN)
WIN[("01", "vault_field")] = dict(ref="QA-10-2: ref 169 44.9 lum / hue 4.5 / sat 0.318; acceptance 45-65 lum")
WIN[("01", "jamb")] = dict(hue_qa=(25.0, 60.0),
                           ref="QA-10-2: ref 169 95.7 lum / hue 22.2 / sat 0.466 / R-B +58.9")

TESTS = dict(m17.TESTS)
TESTS[("01", "vault_field", "lum")] = (45.0, 65.0, "QA-10-2 acceptance: the hero's deepest shade")
TESTS[("02", "soffit_l", "field_hue")] = (25.0, 60.0, "QA-10-13: the coffer FIELD must not be blue")
TESTS[("02", "soffit_r", "field_hue")] = (25.0, 60.0, "QA-10-13: the coffer FIELD must not be blue")


def quartile_colour(sub, top=False):
    """Mean hue / saturation / luminance of the darkest (or brightest) quarter of a box, selected on luminance.
    The same split `light_r17_measure.rib_field` uses, but reported as a COLOUR rather than a level."""
    lum = sub.max(2).ravel()
    n = max(1, lum.size // 4)
    idx = np.argsort(lum)
    sel = idx[-n:] if top else idx[:n]
    m = sub.reshape(-1, 3)[sel].mean(0)
    h, s, _ = colorsys.rgb_to_hsv(m[0] / 255.0, m[1] / 255.0, m[2] / 255.0)
    return h * 360.0, s, float(0.2126 * m[0] + 0.7152 * m[1] + 0.0722 * m[2])


def measure(path):
    cam = m17.cam_of(path)
    if cam is None:
        return None
    got = m17.measure(path)
    if got is None:
        return None
    _c, out = got
    a = m14.load(path, BOXES[cam]["size"])
    if cam == "01":
        for k in ("vault_field", "jamb"):
            x0, y0, x1, y1 = BOXES["01"]["boxes"][k]
            out[k] = m10.stats(a[y0:y1, x0:x1])
            out[k]["p95"] = float(np.percentile(a[y0:y1, x0:x1].max(2), 95))
            out[k]["max"] = float(a[y0:y1, x0:x1].max())
    if cam == "02":
        for k in ("shade_arch", "soffit_l", "soffit_r"):
            x0, y0, x1, y1 = BOXES["02"]["boxes"][k]
            sub = a[y0:y1, x0:x1]
            fh, fs, fl = quartile_colour(sub, top=False)
            rh, rs, rl = quartile_colour(sub, top=True)
            out[k].update(field_hue=fh, field_sat=fs, field_lum=fl, rib_hue=rh, rib_sat=rs, rib_lum=rl)
    return cam, out


def report(paths, label=""):
    print(f"[r18] {label}")
    for p in paths:
        got = measure(p)
        if got is None:
            print(f"  {Path(p).name}: no box set for this camera")
            continue
        cam, out = got
        print(f"  {Path(p).name}  (cam {cam})")
        for k, s in sorted(out.items()):
            extra = ""
            if "ratio" in s:
                extra += f"  ratio {s['ratio']:.3f}"
            if "rib_field" in s:
                extra += f"  rib-field {s['rib_field']:.1f}"
            if "field_hue" in s:
                extra += f"  FIELD hue {s['field_hue']:.1f} sat {s['field_sat']:.3f} lum {s['field_lum']:.1f}"
                extra += f"  RIB hue {s['rib_hue']:.1f} lum {s['rib_lum']:.1f}"
            if "ridge_floor" in s:
                extra += f"  ridge-floor {s['ridge_floor']:.1f} p95 {s['p95']:.1f}"
            if "dark" in s:
                extra += f"  under10 {100 * s['dark']:.1f} %"
            verd = ""
            for (c, box, key), (lo, hi, why) in TESTS.items():
                if (c, box) == (cam, k) and key in s:
                    verd += f"  [{key} {'PASS' if lo <= s[key] <= hi else 'FAIL'} {lo:g}-{hi:g}]"
            print(f"    {k:18s} lum {s['lum']:6.1f} hue {s['hue']:6.1f} sat {s['sat']:.3f} "
                  f"R-B {s['rb']:+7.1f}{extra}{verd}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--shade", nargs="+", required=True)
    ap.add_argument("--label", default="round-18 frames")
    a = ap.parse_args()
    report(a.shade, a.label)
