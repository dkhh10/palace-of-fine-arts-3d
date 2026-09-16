#!/usr/bin/env python3
"""QA-14-4: the three boxes the bloom sweep is judged on, against the Phase 5 hero.

    python3 web/tools/bloom_boxes.py FRAME.png [...] [--labels a,b] [--ref R.png]

Boxes and metrics are QA's (scripts/qa_r13_probe.py + web/tools/qa12_boxes.py `mid_5_21`):
  capital row      1400 520 1900 556   std must be >= 0.85x of Cycles (contact shade)
  S-colonnade wall 1600 590 1670 635   mid_5_21 must be >= 0.7x
  sunlit attic     900 222 1020 256    mean per-pixel saturation must be >= 0.89x
"""
import argparse, os, sys
from pathlib import Path
import numpy as np
from PIL import Image
sys.path.insert(0, str(Path(__file__).parent))
from qa12_boxes import gaussian  # noqa: E402

MAIN = Path(os.environ.get("PFA_MAIN_ROOT") or "/Users/dk/Projects/3d render blender 3rd attempt building")
REF = MAIN / "renders/previews/qa/round10b_01_lagoon_hero_cycles.png"
AT = (1920, 1080)
LUMA = np.array([0.2126, 0.7152, 0.0722])
BOXES = {"capital row std": (1400, 520, 1900, 556, "std"),
         "S-colonnade mid": (1600, 590, 1670, 635, "mid"),
         "sunlit attic sat": (900, 222, 1020, 256, "sat")}


def load(p):
    im = Image.open(p).convert("RGB")
    return np.asarray(im if im.size == AT else im.resize(AT, Image.LANCZOS), dtype=np.float64)


def measure(a):
    L = a @ LUMA
    mid = gaussian(L, 2.5) - gaussian(L, 10.5)
    out = {}
    for name, (x0, y0, x1, y1, kind) in BOXES.items():
        if kind == "std":
            out[name] = float(L[y0:y1, x0:x1].std())
        elif kind == "mid":
            out[name] = float(mid[y0:y1, x0:x1].std())
        else:
            c = a[y0:y1, x0:x1]
            mx, mn = c.max(2), c.min(2)
            out[name] = float(np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0).mean())
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("frames", nargs="+")
    ap.add_argument("--ref", default=str(REF))
    ap.add_argument("--labels", default=None)
    a = ap.parse_args()
    labels = a.labels.split(",") if a.labels else [Path(f).stem for f in a.frames]
    r = measure(load(a.ref))
    print(f"{'frame':22s} " + " ".join(f"{k:>18s}" for k in BOXES))
    print(f"{'REFERENCE':22s} " + " ".join(f"{r[k]:18.3f}" for k in BOXES))
    for lab, f in zip(labels, a.frames):
        m = measure(load(f))
        print(f"{lab:22s} " + " ".join(f"{m[k]:10.3f} ({m[k]/r[k]:.2f}x)" for k in BOXES))


if __name__ == "__main__":
    main()
