"""Round-4 materials measurement (plain python + PIL, no Blender).

    python3 scripts/mat_r4_measure.py <image.png> [--panel N] [--only a,b,c]

Measures the QA round-03 hero boxes (see docs/qa_round_03.md "Measurements") and prints
mean sRGB / luminance / HSV hue+sat / R-B, plus the derived metrics QA's acceptances name:
  * columns  - masked mean inside x 680-1240 y 280-470 over pixels with hue < 32 and sat > 0.30
  * entab_sd - luminance std-dev over the entablature box (QA-03-4 wants >= 60 % of the photo's)
  * shaft_cycles - modulation cycles across a front shaft row profile (QA-03-4 flute test; architecture's)
  * ripple   - mean horizontal run length (px) of above/below-median luminance in the near-water crop
               (QA-03-7 wants <= 15 px; the photo breaks up at ~10)

`--panel N` slices a horizontal N-panel montage (the QA aligned sheets are 3 x 1920 px:
0 = render, 1 = ref 169 warped into the render frame, 2 = overlay), so the identical box
list can be run against the photo.
"""
import sys
from PIL import Image
import numpy as np

BOXES = {  # name: (x0, y0, x1, y1) in the 1920x1080 hero frame
    "attic_sunlit":  (900, 222, 1020, 256),
    "attic_string":  (880, 214, 1040, 222),
    "entablature":   (900, 262, 1020, 296),
    "dome_cap":      (920, 95, 1000, 120),
    "attic_shaded":  (1110, 225, 1150, 260),
    "water_refl":    (900, 760, 1020, 840),
    "near_water_sky": (1150, 1000, 1450, 1050),
    "lagoon_flank":  (100, 900, 400, 960),
}
COL_BOX = (680, 280, 1240, 470)
NEAR_WATER_RIPPLE = (760, 1000, 1160, 1060)


def stats(arr):
    """arr: float array (...,3) in 0-255 sRGB. Returns mean rgb, lum, hue, sat, R-B."""
    m = arr.reshape(-1, 3).mean(axis=0)
    r, g, b = m
    lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
    mx, mn = max(m), min(m)
    d = mx - mn
    if d < 1e-6:
        hue = 0.0
    elif mx == r:
        hue = 60 * (((g - b) / d) % 6)
    elif mx == g:
        hue = 60 * ((b - r) / d + 2)
    else:
        hue = 60 * ((r - g) / d + 4)
    sat = d / mx if mx > 0 else 0.0
    return m, lum, hue, sat, r - b


def px_hsv(a):
    mx = a.max(axis=-1); mn = a.min(axis=-1); d = mx - mn
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    hue = np.zeros_like(mx)
    nz = d > 1e-6
    im = a.argmax(axis=-1)
    with np.errstate(invalid="ignore", divide="ignore"):
        h_r = 60 * (((g - b) / np.where(d == 0, 1, d)) % 6)
        h_g = 60 * ((b - r) / np.where(d == 0, 1, d) + 2)
        h_b = 60 * ((r - g) / np.where(d == 0, 1, d) + 4)
    hue = np.where(im == 0, h_r, np.where(im == 1, h_g, h_b))
    hue = np.where(nz, hue, 0.0)
    sat = np.where(mx > 0, d / np.where(mx == 0, 1, mx), 0.0)
    return hue, sat, mx


def line(name, arr):
    m, lum, hue, sat, rb = stats(arr)
    print(f"  {name:16s} {int(round(m[0])):3d},{int(round(m[1])):3d},{int(round(m[2])):3d}"
          f"  lum {lum:6.1f}  hue {hue:5.1f}  sat {sat:.3f}  R-B {rb:5.1f}  ({arr.shape[1]}x{arr.shape[0]} px)")
    return lum, hue, sat, rb


def run_lengths(g):
    """mean horizontal run length of pixels above/below the row median."""
    runs = []
    for row in g:
        s = row > np.median(row)
        n = 1
        for i in range(1, len(s)):
            if s[i] == s[i - 1]:
                n += 1
            else:
                runs.append(n); n = 1
        runs.append(n)
    return float(np.mean(runs)) if runs else 0.0


def main():
    path = sys.argv[1]
    panel = 0
    only = None
    if "--panel" in sys.argv:
        panel = int(sys.argv[sys.argv.index("--panel") + 1])
    if "--only" in sys.argv:
        only = set(sys.argv[sys.argv.index("--only") + 1].split(","))
    im = Image.open(path).convert("RGB")
    a = np.asarray(im).astype(np.float32)
    H, W = a.shape[:2]
    n_panels = max(1, round(W / 1920)) if W % 1920 == 0 else 1
    if n_panels > 1:
        w = W // n_panels
        a = a[:, panel * w:(panel + 1) * w]
    print(f"{path} panel {panel} -> {a.shape[1]}x{a.shape[0]}")
    for name, (x0, y0, x1, y1) in BOXES.items():
        if only and name not in only:
            continue
        line(name, a[y0:y1, x0:x1])
    if not only or "entab_sd" in only:
        box = a[262:296, 900:1020]
        g = 0.2126 * box[..., 0] + 0.7152 * box[..., 1] + 0.0722 * box[..., 2]
        box2 = a[222:256, 900:1020]
        g2 = 0.2126 * box2[..., 0] + 0.7152 * box2[..., 1] + 0.0722 * box2[..., 2]
        print(f"  {'entab_lum_sd':16s} {g.std():5.2f}      attic_lum_sd {g2.std():5.2f}")
    if not only or "columns" in only:
        x0, y0, x1, y1 = COL_BOX
        box = a[y0:y1, x0:x1]
        hue, sat, mx = px_hsv(box)
        mask = (hue < 32) & (sat > 0.30)
        if mask.sum() > 50:
            sel = box[mask]
            m, lum, h, s, rb = stats(sel)
            print(f"  {'columns(mask)':16s} {int(round(m[0])):3d},{int(round(m[1])):3d},{int(round(m[2])):3d}"
                  f"  lum {lum:6.1f}  hue {h:5.1f}  sat {s:.3f}  R-B {rb:5.1f}  ({int(mask.sum())} px)")
        else:
            print(f"  columns(mask)    only {int(mask.sum())} px matched")
    if not only or "ripple" in only:
        x0, y0, x1, y1 = NEAR_WATER_RIPPLE
        box = a[y0:y1, x0:x1]
        g = 0.2126 * box[..., 0] + 0.7152 * box[..., 1] + 0.0722 * box[..., 2]
        print(f"  {'ripple_run_px':16s} {run_lengths(g):5.1f}")
    if only and "shaft" in only:
        g = shaft_profile(a)
        print("  shaft profile (y 330-380, x 780-1240):")
        print("   ", " ".join(f"{v:.0f}" for v in g))


def shaft_profile(a, y0=330, y1=380, x0=780, x1=1240):
    """Horizontal luminance profile across the front shafts: count local minima and their contrast."""
    box = a[y0:y1, x0:x1]
    g = (0.2126 * box[..., 0] + 0.7152 * box[..., 1] + 0.0722 * box[..., 2]).mean(axis=0)
    return g


if __name__ == "__main__":
    main()
