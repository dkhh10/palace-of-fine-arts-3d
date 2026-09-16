#!/usr/bin/env python3
"""QA-14-1: the cam01 water metrics, on any viewer frame, against the Phase 5 hero.

    python3 web/tools/water_probe.py frame.png [frame2.png ...] [--labels a,b] [--ref R.png]

The crops and the definitions are QA's (scripts/qa_r13_probe.py `water`), reproduced here so the
viewer can iterate on the shader without a QA round:

  refl mass   700 700 1300 950    the reflected building
  open water  300 900 1600 1060   the near water, where the ripple must live
  rowHF/colHF mean |diff| across rows / across columns.  A real lagoon's ripple is HORIZONTAL
              high-frequency energy, so row/col separates STREAKS (high) from a blur (~1.0) and from
              a mirror (both near zero).
  Fresnel     mean luma of 40 px rows from the far shore (y=760) to the near edge (y=1060), which
              must fall smoothly; a collapse means the reflection is being cut rather than faded.
"""
import argparse, json, os, sys
from pathlib import Path
import numpy as np
from PIL import Image

MAIN = Path(os.environ.get("PFA_MAIN_ROOT") or "/Users/dk/Projects/3d render blender 3rd attempt building")
DEFAULT_REF = MAIN / "renders/previews/qa/round10b_01_lagoon_hero_cycles.png"
AT = (1920, 1080)
LUMA = np.array([0.2126, 0.7152, 0.0722])
CROPS = [("refl mass", (700, 700, 1300, 950)), ("open water", (300, 900, 1600, 1060))]


def rgb(path):
    im = Image.open(path).convert("RGB")
    if im.size != AT:
        im = im.resize(AT, Image.LANCZOS)
    return np.asarray(im, dtype=np.float64)


def hue_sat(mean):
    r, g, b = mean / 255.0
    mx, mn = max(r, g, b), min(r, g, b)
    d = mx - mn
    if d < 1e-9:
        return 0.0, 0.0
    if mx == r:
        h = 60 * (((g - b) / d) % 6)
    elif mx == g:
        h = 60 * ((b - r) / d + 2)
    else:
        h = 60 * ((r - g) / d + 4)
    return h, d / mx


def measure(a, box):
    x0, y0, x1, y1 = box
    c = a[y0:y1, x0:x1]
    L = c @ LUMA
    h, s = hue_sat(c.reshape(-1, 3).mean(axis=0))
    row = float(np.abs(np.diff(L, axis=0)).mean())
    col = float(np.abs(np.diff(L, axis=1)).mean())
    return {"lum": float(L.mean()), "std": float(L.std()), "hue": h, "sat": s,
            "rb": float((c[..., 0] - c[..., 2]).mean()), "rowHF": row, "colHF": col,
            "row_col": row / max(col, 1e-6)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("frames", nargs="+")
    ap.add_argument("--ref", default=str(DEFAULT_REF))
    ap.add_argument("--labels", default=None)
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    labels = a.labels.split(",") if a.labels else [Path(f).stem for f in a.frames]
    if len(labels) != len(a.frames):
        sys.exit("water_probe.py: one label per frame")
    ref = rgb(a.ref)
    imgs = [rgb(f) for f in a.frames]
    out = {"ref": a.ref, "crops": {}, "fresnel": {}}

    for name, box in CROPS:
        rm = measure(ref, box)
        out["crops"][name] = {"ref": rm, "frames": {}}
        print(f"\n{name}  {box}")
        print(f"  {'frame':14s} {'lum':>7s} {'std':>7s} {'hue':>7s} {'sat':>7s} {'rowHF':>7s} {'colHF':>7s} {'row/col':>8s}")
        for l, im in zip(labels, imgs):
            m = measure(im, box)
            out["crops"][name]["frames"][l] = m
            print(f"  {l:14s} {m['lum']:7.1f} {m['std']:7.2f} {m['hue']:7.1f} {m['sat']:7.3f} "
                  f"{m['rowHF']:7.2f} {m['colHF']:7.2f} {m['row_col']:8.2f}")
        print(f"  {'REFERENCE':14s} {rm['lum']:7.1f} {rm['std']:7.2f} {rm['hue']:7.1f} {rm['sat']:7.3f} "
              f"{rm['rowHF']:7.2f} {rm['colHF']:7.2f} {rm['row_col']:8.2f}")

    print("\nFresnel ladder: mean luma of 40 px rows, far shore -> near edge (x 700..1300)")
    for l, im in list(zip(labels, imgs)) + [("REFERENCE", ref)]:
        L = im @ LUMA
        prof = [float(L[y:y + 40, 700:1300].mean()) for y in range(760, 1060, 40)]
        out["fresnel"][l] = prof
        mono = all(prof[i] >= prof[i + 1] - 0.5 for i in range(len(prof) - 1))
        print(f"  {l:14s} " + " ".join(f"{v:6.1f}" for v in prof)
              + f"   fall {prof[0] - prof[-1]:6.1f}  {'monotone' if mono else 'NOT monotone'}")
    if a.json:
        Path(a.json).write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
