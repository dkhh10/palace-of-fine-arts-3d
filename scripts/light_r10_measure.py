"""Round-10 lighting measurement. Plain python3 + PIL/numpy, no Blender.

    python3 scripts/light_r10_measure.py <hero_1920x1080.png> [more.png ...] [--json out.json]
    python3 scripts/light_r10_measure.py --ref            # print the reference row and exit

Uses the QA round-03 hero boxes (docs/qa_round_03.md "Measurements", identical to scripts/mat_r4_measure.BOXES) PLUS
lighting's own sky_top / sky_left boxes, so one command produces every number the round-10 brief asks for:

  item 1  attic_sunlit sat / R-B / lum, attic_shaded hue
  item 2  columns (masked) luminance
  item 3  near_water_sky sat / hue
  item 4  sky_left / sky_top luminance ratio (ref 169: 1.17)

The reference row is measured with the SAME boxes on panel 1 of
renders/qa_comparisons/round03_cam01_aligned_vs_ref169.png (ref 169 warped into the render frame by QA's align
transform), so render and reference are always compared on matched pixels.
"""
import sys, json, argparse
from pathlib import Path
import numpy as np
from PIL import Image

# Worktree-safe (round-10 review nit): ROOT is this checkout exactly as common.ROOT computes it, and the reference
# tree honours $PFA_REFERENCE_DIR the way common.REFERENCE_DIR does. renders/qa_comparisons is git-tracked, so the
# aligned panel is present in every worktree that has merged main.
import os
ROOT = Path(__file__).resolve().parents[1]
# reference PHOTOS are gitignored and live in the MAIN checkout only (CLAUDE.md); tracked renders live here.
MAIN_ROOT = Path(os.environ.get("PFA_MAIN_ROOT", "/Users/dk/Projects/3d render blender 3rd attempt building"))
REFERENCE_DIR = Path(os.environ.get("PFA_REFERENCE_DIR", str(MAIN_ROOT / "reference")))
ALIGNED = ROOT / "renders" / "qa_comparisons" / "round03_cam01_aligned_vs_ref169.png"

# (x0, y0, x1, y1) in the 1920x1080 hero frame
BOXES = {
    "attic_sunlit":   (900, 222, 1020, 256),
    "attic_string":   (880, 214, 1040, 222),
    "entablature":    (900, 262, 1020, 296),
    "dome_cap":       (920, 95, 1000, 120),
    "attic_shaded":   (1110, 225, 1150, 260),
    "water_refl":     (900, 760, 1020, 840),
    "near_water_sky": (1150, 1000, 1450, 1050),
    "lagoon_flank":   (100, 900, 400, 960),
    # lighting's sky boxes (light_measure.REGIONS["hero"], converted to pixels at 1920x1080)
    "sky_top":        (1210, 22, 1690, 76),
    "sky_left":       (38, 92, 192, 157),
}
COL_BOX = (680, 280, 1240, 470)          # columns mask: hue < 32 and sat > 0.30 inside this box

# reference row, measured on ALIGNED panel 1 (filled in by --ref, cached here so a render can be judged offline)
REF = {
    "attic_sunlit":   dict(lum=189.6, hue=40.3, sat=0.588, rb=136.1),
    "attic_string":   dict(lum=181.9, hue=39.3, sat=0.580, rb=129.4),
    "entablature":    dict(lum=146.4, hue=34.0, sat=0.604, rb=115.1),
    "dome_cap":       dict(lum=215.6, hue=42.7, sat=0.288, rb=67.4),
    "attic_shaded":   dict(lum=115.0, hue=29.5, sat=0.425, rb=60.0),
    "water_refl":     dict(lum=168.9, hue=33.7, sat=0.339, rb=65.8),
    "near_water_sky": dict(lum=107.7, hue=192.1, sat=0.270, rb=-32.1),
    "lagoon_flank":   dict(lum=155.2, hue=200.7, sat=0.279, rb=-49.7),
    "columns":        dict(lum=95.8, hue=24.5, sat=0.588, rb=79.4),
}


def stats(a):
    m = a.reshape(-1, 3).mean(axis=0)
    r, g, b = m
    lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
    mx, mn = float(max(m)), float(min(m))
    d = mx - mn
    if d < 1e-6:
        hue = 0.0
    elif mx == r:
        hue = 60 * (((g - b) / d) % 6)
    elif mx == g:
        hue = 60 * ((b - r) / d + 2)
    else:
        hue = 60 * ((r - g) / d + 4)
    return dict(rgb=[float(v) for v in m], lum=float(lum), hue=float(hue),
                sat=float(d / mx if mx > 0 else 0.0), rb=float(r - b))


def px_hs(a):
    mx = a.max(axis=-1); mn = a.min(axis=-1); d = mx - mn
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    dd = np.where(d == 0, 1, d)
    im = a.argmax(axis=-1)
    hue = np.where(im == 0, 60 * (((g - b) / dd) % 6),
                   np.where(im == 1, 60 * ((b - r) / dd + 2), 60 * ((r - g) / dd + 4)))
    hue = np.where(d > 1e-6, hue, 0.0)
    sat = np.where(mx > 0, d / np.where(mx == 0, 1, mx), 0.0)
    return hue, sat


def measure(path, panel=None):
    im = Image.open(path).convert("RGB")
    a = np.asarray(im, dtype=np.float64)
    if panel is not None:
        a = a[:, panel * 1920:(panel + 1) * 1920]
    if a.shape[1] != 1920 or a.shape[0] != 1080:
        im2 = Image.fromarray(a.astype(np.uint8)).resize((1920, 1080), Image.LANCZOS)
        a = np.asarray(im2, dtype=np.float64)
    out = {}
    for name, (x0, y0, x1, y1) in BOXES.items():
        out[name] = stats(a[y0:y1, x0:x1])
    x0, y0, x1, y1 = COL_BOX
    sub = a[y0:y1, x0:x1]
    hue, sat = px_hs(sub)
    mask = (hue < 32) & (sat > 0.30)
    out["columns"] = stats(sub[mask]) if mask.sum() > 100 else dict(rgb=[0, 0, 0], lum=0, hue=0, sat=0, rb=0)
    out["columns"]["px"] = int(mask.sum())
    out["sky_ratio"] = out["sky_left"]["lum"] / max(1e-6, out["sky_top"]["lum"])
    return out


TARGETS = """item 1 attic sat >= 0.53, R-B >= 120, lum 0.94-1.06 x ref (178.2-201.0), shade hue within 6 deg of 29.5
item 2 columns lum -> ref 95.8 (render was 153.2 = 1.60x)
item 3 near_water_sky sat 0.22-0.32, hue 185-200
item 4 sky_left/sky_top -> 1.17 +- 10 % (1.05-1.29); sky_top lum 149-182"""


def report(path, m, label=""):
    print(f"\n=== {label or path} ===")
    print(f"  {'region':16s} {'sRGB':>15s} {'lum':>7s} {'hue':>6s} {'sat':>6s} {'R-B':>7s}   ref lum/hue/sat/R-B")
    for k in list(BOXES) + ["columns"]:
        v = m[k]
        r = REF.get(k)
        rs = (f"  {r['lum']:6.1f} {r['hue']:5.1f} {r['sat']:.3f} {r['rb']:6.1f}" if r else "")
        print(f"  {k:16s} {int(round(v['rgb'][0])):3d},{int(round(v['rgb'][1])):3d},{int(round(v['rgb'][2])):3d}"
              f"   {v['lum']:6.1f} {v['hue']:6.1f} {v['sat']:6.3f} {v['rb']:7.1f}{rs}")
    print(f"  sky_left/sky_top {m['sky_ratio']:.3f}   (ref 169: 1.170)")
    a = m["attic_sunlit"]
    print(f"  >> item1 attic sat {a['sat']:.3f} (>=0.53) R-B {a['rb']:.1f} (>=120) lum {a['lum']:.1f} (178.2-201.0)"
          f" | shade hue {m['attic_shaded']['hue']:.1f} (29.5+-6)")
    print(f"  >> item2 columns lum {m['columns']['lum']:.1f} (ref 95.8, ratio {m['columns']['lum']/95.8:.2f})")
    print(f"  >> item3 near water sat {m['near_water_sky']['sat']:.3f} (0.22-0.32) hue {m['near_water_sky']['hue']:.1f} (185-200)")
    print(f"  >> item4 sky_left/top {m['sky_ratio']:.3f} (1.05-1.29) sky_top {m['sky_top']['lum']:.1f} (149-182)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("images", nargs="*")
    ap.add_argument("--panel", type=int, default=None)
    ap.add_argument("--ref", action="store_true")
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    print(TARGETS)
    allm = {}
    if a.ref:
        m = measure(ALIGNED, panel=1)
        report(str(ALIGNED), m, "REF 169 warped into the render frame (panel 1)")
        allm["ref169"] = m
    for p in a.images:
        m = measure(p, panel=a.panel)
        report(p, m)
        allm[Path(p).name] = m
    if a.json:
        Path(a.json).write_text(json.dumps(allm, indent=1))
