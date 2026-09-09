"""Round-8 water acceptance table (plain python, no Blender).

    python3 scripts/mat_r8_measure.py <png> [<png> ...]        # hero-grid frames (1920x1080 or a border crop of one)
    python3 scripts/mat_r8_measure.py --cam05 <png>            # cam05 lagoon band
    python3 scripts/mat_r8_measure.py --cam06 <png> [--box x0,y0,x1,y1]

Reuses the round-7 box definitions and statistics (`mat_r7_measure.stats`), and prints only the QA-06-3 rows plus
their windows, so a sweep case is one line per box.
"""
import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mat_r7_measure import load, stats, BOXES

# QA-06-3 (round-8 brief) windows and the ref-169 numbers behind them
ROWS = [
    ("water_refl",     "lum 124-208, R-B >= +30",  "ref 166.1 / h33.7 / s0.358 / R-B +69.0"),
    ("near_water_sky", "sat 0.22-0.32, hue ->185-200", "ref 0.261 / h191.1"),
    ("ripples",        "R-B -26 +- 10",            "ref -16.4"),
    ("lagoon_flank",   "lum ~153",                 "ref 153.4 / h200.4"),
]
CAM05_BAND = (0.35, 0.86, 0.75, 0.99)     # fractional (x0, y0, x1, y1); QA's cam05 lagoon band
CAM06_LAGOON = (60, 380, 340, 500)        # QA-02-6 open-water box on cam06 at 1280x720


def line(name, s):
    return (f"  {name:16s} lum {s['lum']:6.1f}  hue {s['hue']:6.1f}  sat {s['sat']:5.3f}  "
            f"R-B {s['rb']:+7.1f}  std {s['std']:5.1f}")


def main(argv):
    if "--cam05" in argv:
        p = argv[argv.index("--cam05") + 1]
        from PIL import Image
        a = np.asarray(Image.open(p).convert("RGB")).astype(np.float64)
        H, W = a.shape[:2]
        x0, y0, x1, y1 = (int(CAM05_BAND[0] * W), int(CAM05_BAND[1] * H),
                          int(CAM05_BAND[2] * W), int(CAM05_BAND[3] * H))
        print(f"{Path(p).name}  ({W}x{H})")
        print(line("cam05_lagoon", stats(a[y0:y1, x0:x1])) + "   [sat >= 0.25, hue 40-80, lum ~93.4]")
        return
    if "--cam06" in argv:
        p = argv[argv.index("--cam06") + 1]
        from PIL import Image
        a = np.asarray(Image.open(p).convert("RGB")).astype(np.float64)
        bx = CAM06_LAGOON
        if "--box" in argv:
            bx = tuple(int(v) for v in argv[argv.index("--box") + 1].split(","))
        H, W = a.shape[:2]
        sc = W / 1280.0
        x0, y0, x1, y1 = (int(bx[0] * sc), int(bx[1] * sc), int(bx[2] * sc), int(bx[3] * sc))
        print(f"{Path(p).name}  ({W}x{H})")
        print(line("cam06_lagoon", stats(a[y0:y1, x0:x1])) + "   [Cycles lum >= 0.7 x round-5 94.3 = 66.0]")
        return
    for p in [a for a in argv if not a.startswith("--")]:
        a = load(p)
        print(f"{Path(p).name}")
        for name, win, ref in ROWS:
            print(line(name, stats(a[BOXES[name][1]:BOXES[name][3], BOXES[name][0]:BOXES[name][2]]))
                  + f"   [{win}; {ref}]")


if __name__ == "__main__":
    main(sys.argv[1:])
