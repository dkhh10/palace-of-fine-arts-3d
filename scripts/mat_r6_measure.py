"""Round-6 derived acceptance tests for QA-04-3 / -7 (plain python + PIL, no Blender).

    python3 scripts/mat_r6_measure.py cornice   <hero.png> [--panel N]
    python3 scripts/mat_r6_measure.py waterline <hero.png> [--panel N]
    python3 scripts/mat_r6_measure.py coffer    <ceiling.png>

The chroma / std-dev boxes stay in `mat_r4_measure.py` (same yardstick as rounds 4 and 5). What is here is the
three tests QA-04 wrote in prose and no script measured yet:

  cornice   "a streak visibly darker than its field by >= 15 lum under the cornice over >= 30 % of its length".
            For every column of the sunlit entablature (and of the attic string course) the mean luminance of the
            band immediately below the projection is compared with the field 20-30 px lower down; the score is the
            fraction of columns that clear 15 levels.
  waterline "a 0.3-0.6 m band >= 20 lum darker than the wall above it along the waterline".  The water surface is
            found per column from its own hue (170-240 deg), then the 12 px above it are compared with the 22 px
            above that.  At the shore's ~60-90 m the hero runs 3-4 cm/px, so 12 px is ~0.4 m.
  coffer    ref 083's robust statistic: mean of the darkest quarter over mean of the lightest quarter across the
            saucer, plus the coffer-field std-dev QA-04-7 wants at >= 60 % of ref 083's.  Re-measured 2026-09-09
            by running this function on ref_083 itself with its own default box: ratio 0.265, std 31.2 (the
            0.439 / 36.3 pair printed through round 6 came from a different crop and is what made the round-6
            note read "0.195 vs ref 083's 0.439").  light_measure.py:194's coffer/sky 0.39 is lighting's file and
            is still unreconciled with the notes' 0.437 -- hand-off, not edited here.
"""
import sys
import numpy as np
from PIL import Image


def load(path, panel=0):
    a = np.asarray(Image.open(path).convert("RGB")).astype(np.float32)
    H, W = a.shape[:2]
    n = max(1, round(W / 1920)) if W % 1920 == 0 else 1
    if n > 1:
        w = W // n
        a = a[:, panel * w:(panel + 1) * w]
    return a


def lum(a):
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def hue_sat(a):
    mx = a.max(axis=-1); mn = a.min(axis=-1); d = mx - mn
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    dd = np.where(d == 0, 1, d)
    im = a.argmax(axis=-1)
    h = np.where(im == 0, 60 * (((g - b) / dd) % 6), np.where(im == 1, 60 * ((b - r) / dd + 2), 60 * ((r - g) / dd + 4)))
    return np.where(d > 1e-6, h, 0.0), np.where(mx > 0, d / np.where(mx == 0, 1, mx), 0.0)


# (name, box) in the 1920x1080 hero frame: plain wall faces that sit directly under a horizontal projection.
# The attic panel is under the attic's upper cornice, the entablature box under the corona.
STREAK_BOXES = [
    ("attic_under_cornice", (900, 222, 1020, 256)),
    ("entablature_frieze",  (900, 262, 1020, 296)),
]


def cornice(a):
    """QA-04-3b: "a streak visibly darker than its field by >= 15 lum under the cornice over >= 30 % of its
    length".  "its length" is the cornice's, i.e. the horizontal run, so the statistic is columnwise: the mean
    luminance of each column of the band below the projection against the band's own median column.  A clean CAD
    wall has every column on the median; a run-off streak takes a run of columns 15+ levels below it.  This is
    resolution- and alignment-independent, which the absolute row numbers of the ledge are not."""
    print("  QA-04-3b  under-ledge run-off (test: >= 15 lum below the field over >= 30 % of the length)")
    g = lum(a)
    for name, (x0, y0, x1, y1) in STREAK_BOXES:
        c = g[y0:y1, x0:x1].mean(axis=0)
        field = float(np.median(c))
        frac = float((c <= field - 15.0).mean())
        deep = float((c <= field - 25.0).mean())
        print(f"    {name:20s} field {field:6.1f}  col sd {c.std():5.1f}  min {c.min():6.1f}"
              f"  cols <= -15: {frac * 100:5.1f} %  <= -25: {deep * 100:4.1f} %")
    print("    ref 169 on the same boxes: attic sd 19.4, 19.2 % / 10.0 %; entablature sd 13.8, 14.2 % / 7.5 %")


def waterline(a, box=None, band=12, gap=3, above=22):
    """QA-04-3c: "a 0.3-0.6 m band >= 20 lum darker than the wall above it along the waterline".  The water edge is
    found per column as the highest row whose colour is water (blue-green hue, or simply much darker and less warm
    than the stone above); `band` px above it are compared with `above` px higher still.  On the hero the shore is
    60-90 m out, ~3-4 cm/px, so 12 px is ~0.4 m -- inside the 0.3-0.6 m the test names."""
    print("  QA-04-3c  waterline band (test: >= 20 lum darker than the wall above)")
    x0, y0, x1, y1 = box or (700, 520, 1170, 800)
    h, s = hue_sat(a)
    g = lum(a)
    iswater = ((h > 150) & (h < 260) & (s > 0.06)) | (g < 45)
    drops = []
    for x in range(x0, x1):
        col = iswater[y0:y1, x]
        idx = np.flatnonzero(col)
        if idx.size < 15:
            continue
        yw = y0 + int(idx.min())
        if yw - (band + gap + above) < y0:
            continue
        b = g[yw - band:yw, x].mean()
        aov = g[yw - band - gap - above:yw - band - gap, x].mean()
        drops.append(aov - b)
    if not drops:
        print("    no water edge found in the crop")
        return
    d = np.array(drops)
    print(f"    columns with an edge {len(d):4d}   mean drop {d.mean():5.1f}   median {np.median(d):5.1f}"
          f"   cols >= 20: {(d >= 20).mean() * 100:5.1f} %  {'PASS' if (d >= 20).mean() >= 0.30 else 'fail'}")


def coffer(a, box=None):
    g = lum(a)
    H, W = g.shape
    if box is None:                          # the saucer fills the middle of the ceiling camera
        box = (int(W * 0.28), int(H * 0.20), int(W * 0.72), int(H * 0.80))
    x0, y0, x1, y1 = box
    v = g[y0:y1, x0:x1].ravel()
    v = v[v > 1.0]
    if v.size < 100:
        print("    coffer box is black")
        return
    q1, q3 = np.percentile(v, 25), np.percentile(v, 75)
    dark, light = v[v <= q1].mean(), v[v >= q3].mean()
    print(f"  QA-04-7   coffer field: dark quarter {dark:6.1f}  light quarter {light:6.1f}  ratio {dark / light:.3f}"
          f"  (ref 083 0.265)   std {v.std():5.1f}  (ref 31.2, test >= 18.7)   mean {v.mean():6.1f}")


def main():
    what = sys.argv[1]
    path = sys.argv[2]
    panel = int(sys.argv[sys.argv.index("--panel") + 1]) if "--panel" in sys.argv else 0
    a = load(path, panel)
    print(f"{path} panel {panel} -> {a.shape[1]}x{a.shape[0]}")
    {"cornice": cornice, "waterline": waterline, "coffer": coffer}[what](a)


if __name__ == "__main__":
    main()
