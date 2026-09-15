#!/usr/bin/env python3
"""QA round 12 (Phase 6 Gate 2) measurement probe — no Blender, no Chrome.

    python3 scripts/qa_r12_probe.py tiles            # cam01 six 100 % tiles -> renders/web/tiles/gate2/
    python3 scripts/qa_r12_probe.py boxes            # round-10b hero boxes: viewer(pbr) vs the Cycles reference
    python3 scripts/qa_r12_probe.py crops            # two 100 % crops per station 02-06 -> tiles/gate2/
    python3 scripts/qa_r12_probe.py flat  X0 Y0 X1 Y1 [--img P]   # texture-presence test on one box

`boxes` reports lum / hue / sat / R-B for the viewer frame and the reference and the ratio.  Under Gate 2
lighting (full sun + PMREM irradiance, no lightmaps, no shadows) LUMINANCE IS NOT A MATERIAL METRIC: it is
printed and never scored.  Hue and saturation are the material metrics.

`flat` answers "is there a texture on this surface at all": the luminance standard deviation inside the box,
the high-pass energy (box minus a 9-px box blur) and the number of distinct quantised colours.  A baked albedo
on concrete gives std > 6 and hp > 1.5; a flat baseColorFactor gives std < 2.5 and hp < 0.5.
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
VIEWER = str(ROOT / "renders/web/gate2_cam%02d.png")
REF1 = str(ROOT / "renders/previews/qa/round10b_01_lagoon_hero_cycles.png")
TILEDIR = ROOT / "renders/web/tiles/gate2"

# round-10b acceptance boxes (docs/qa_round_10b.md item 3b), hero pixel space 1920x1080
BOXES = [
    ("sunlit attic", (900, 222, 1020, 256)),
    ("shaded attic", (1110, 225, 1150, 260)),
    ("entablature", (900, 262, 1020, 296)),
    ("columns", (680, 280, 1240, 470)),
    ("dome cap", (900, 90, 1020, 130)),
    ("whole building", (700, 160, 1240, 480)),
]
# Gate 2 additions: surfaces QA-11c-2 said were untextured, plus the vault field
EXTRA = [
    ("attic pedestals L", (700, 200, 780, 240)),
    ("colonnade pedestal", (1440, 560, 1560, 620)),
    ("vault field", (900, 380, 1010, 430)),
    ("podium band", (820, 520, 1100, 560)),
]
STATION_CROPS = {
    2: [("piers/entablature", (560, 90, 1200, 450)), ("backdrop hall", (760, 380, 1400, 740))],
    3: [("near column", (420, 120, 1060, 480)), ("walk + pedestals", (640, 560, 1280, 920))],
    4: [("coffers", (560, 200, 1200, 560)), ("rib + pendentive", (1100, 480, 1740, 840))],
    5: [("colonnade base", (500, 380, 1140, 740)), ("lawn + trees", (1100, 500, 1740, 860))],
    6: [("rotunda from above", (620, 260, 1260, 620)), ("backdrop city", (1180, 120, 1820, 480))],
}


def rgb(path, size=None):
    im = Image.open(path).convert("RGB")
    if size and im.size != size:
        im = im.resize(size, Image.LANCZOS)
    return np.asarray(im, dtype=np.float64)


def luma(a):
    return a @ np.array([0.2126, 0.7152, 0.0722])


def hsv(mean):
    mx, mn = float(mean.max()), float(mean.min())
    s = 0.0 if mx <= 0 else (mx - mn) / mx
    if mx == mn:
        h = 0.0
    elif mx == mean[0]:
        h = (60 * (mean[1] - mean[2]) / (mx - mn)) % 360
    elif mx == mean[1]:
        h = 60 * (mean[2] - mean[0]) / (mx - mn) + 120
    else:
        h = 60 * (mean[0] - mean[1]) / (mx - mn) + 240
    return h, s


def stats(a, box):
    x0, y0, x1, y1 = box
    px = a[y0:y1, x0:x1]
    m = px.reshape(-1, 3).mean(0)
    h, s = hsv(m)
    L = luma(px)
    return dict(lum=L.mean(), hue=h, sat=s, rb=m[0] - m[2], std=L.std())


def boxblur(L, k=9):
    pad = k // 2
    P = np.pad(L, pad, mode="edge")
    c = np.cumsum(np.cumsum(P, 0), 1)
    c = np.pad(c, ((1, 0), (1, 0)))
    H, W = L.shape
    return (c[k:k + H, k:k + W] - c[0:H, k:k + W] - c[k:k + H, 0:W] + c[0:H, 0:W]) / (k * k)


def flatness(a, box):
    x0, y0, x1, y1 = box
    px = a[y0:y1, x0:x1]
    L = luma(px)
    hp = np.abs(L - boxblur(L)).mean()
    ncol = len(np.unique((px // 4).astype(np.int32).reshape(-1, 3), axis=0))
    return L.std(), hp, ncol


def cmd_tiles():
    sys.path.insert(0, str(ROOT / "web/tools"))
    from gate1_sheets import make_tiles
    TILEDIR.mkdir(parents=True, exist_ok=True)
    out = make_tiles(VIEWER % 1, REF1, TILEDIR)
    for f in out:
        g = Path(f).with_name(Path(f).name.replace("gate1_", "gate2_"))
        Path(f).rename(g)
        print(g)


def cmd_crops():
    TILEDIR.mkdir(parents=True, exist_ok=True)
    for st, crops in STATION_CROPS.items():
        im = Image.open(VIEWER % st).convert("RGB")
        for i, (name, box) in enumerate(crops, 1):
            f = TILEDIR / f"gate2_cam{st:02d}_crop{i}.png"
            im.crop(box).save(f)
            print(f"{f}  {name} {box}")


def cmd_boxes():
    v = rgb(VIEWER % 1)
    r = rgb(REF1, (1920, 1080))
    print(f"{'box':22s} {'':26s} viewer (pbr, direct)          | reference (Cycles r10b)      | ratios")
    for name, box in BOXES + EXTRA:
        sv, sr = stats(v, box), stats(r, box)
        print(f"{name:22s} {str(box):26s} "
              f"lum {sv['lum']:6.1f} hue {sv['hue']:5.1f} sat {sv['sat']:.3f} R-B {sv['rb']:+6.1f} std {sv['std']:5.1f} | "
              f"lum {sr['lum']:6.1f} hue {sr['hue']:5.1f} sat {sr['sat']:.3f} R-B {sr['rb']:+6.1f} std {sr['std']:5.1f} | "
              f"sat {sv['sat'] / max(sr['sat'], 1e-6):5.2f}x  dhue {sv['hue'] - sr['hue']:+5.1f}  lum {sv['lum'] / max(sr['lum'], 1e-6):5.2f}x")
    print()
    print(f"{'flatness box':26s} {'':26s} viewer std / hp / colours     | reference std / hp / colours")
    for name, box in BOXES + EXTRA:
        a = flatness(v, box)
        b = flatness(r, box)
        print(f"{name:26s} {str(box):26s} {a[0]:6.2f} {a[1]:6.2f} {a[2]:7d}        | {b[0]:6.2f} {b[1]:6.2f} {b[2]:7d}")


def cmd_flat(argv):
    img = VIEWER % 1
    if "--img" in argv:
        i = argv.index("--img")
        img = argv[i + 1]
        argv = argv[:i] + argv[i + 2:]
    box = tuple(int(x) for x in argv[:4])
    a = rgb(img)
    s = stats(a, box)
    f = flatness(a, box)
    print(f"{img} {box}: lum {s['lum']:.1f} hue {s['hue']:.1f} sat {s['sat']:.3f} "
          f"R-B {s['rb']:+.1f} | std {f[0]:.2f} hp {f[1]:.2f} colours {f[2]}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "boxes"
    {"tiles": cmd_tiles, "crops": cmd_crops, "boxes": cmd_boxes}.get(cmd, lambda: cmd_flat(sys.argv[2:]))()
