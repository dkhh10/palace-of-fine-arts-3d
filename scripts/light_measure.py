"""Lighting measurement tool (Lighting & Rendering specialist). Plain python3 + numpy/PIL, no Blender needed.

    python3 scripts/light_measure.py --regions hero renders/previews/qa/roundlb_01_lagoon_hero.png
    python3 scripts/light_measure.py --rect 0.40,0.30,0.06,0.03 img.png [img2.png ...]
    python3 scripts/light_measure.py --grid img.png out.jpg          # 10 % grid overlay, 960 px wide, for picking rects
    python3 scripts/light_measure.py --pair render.png ref.jpg out.jpg --regions hero   # side-by-side + grid + rects

Rectangles are FRACTIONAL (x, y, w, h) of the image, y down, so the same region definition applies to a render and to a
reference photo of the same framing. Prints per region: sRGB 0-255 mean, scene-relative linear luminance Y (sRGB
primaries), hue angle in degrees, and saturation (max-min)/max. Region sets live in REGIONS below; ratios in RATIOS.
"""
import sys, json, argparse
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
MAIN_ROOT = Path("/Users/dk/Projects/3d render blender 3rd attempt building")
REF = MAIN_ROOT / "reference" / "photos" / "raw"

# --------------------------------------------------------------------------- region sets (fractional x, y, w, h)
REGIONS = {
    # ---- cam01 hero, RENDER framing (rotunda x 0.325-0.65, dome y 0.04-0.14, attic band y 0.14-0.26) ----
    "hero": {
        "attic_sunlit":    [0.355, 0.175, 0.030, 0.055],
        "attic_sunlit_b":  [0.485, 0.145, 0.045, 0.030],
        "sky_top":         [0.630, 0.020, 0.250, 0.050],
        "sky_left":        [0.020, 0.085, 0.080, 0.060],
        "colonnade_far":   [0.030, 0.435, 0.090, 0.030],
        "water_centre":    [0.330, 0.780, 0.100, 0.060],
        "shade_north":     [0.575, 0.185, 0.025, 0.045],
    },
    # ---- ref 169, PHOTO framing (rotunda x 0.375-0.60, dome y 0.13-0.19, attic band y 0.20-0.29) ----
    "hero_ref169": {
        "attic_sunlit":    [0.390, 0.215, 0.030, 0.050],
        "attic_sunlit_b":  [0.485, 0.215, 0.045, 0.030],
        "sky_top":         [0.200, 0.020, 0.250, 0.050],
        "sky_left":        [0.060, 0.150, 0.080, 0.060],
        "colonnade_far":   [0.050, 0.400, 0.090, 0.030],
        "water_centre":    [0.400, 0.750, 0.120, 0.050],
        "shade_north":     [0.555, 0.225, 0.020, 0.040],
    },
    # ---- cam04 rotunda ceiling: same central coffer field in the render and in ref 083 ----
    "ceiling": {
        "coffer_field":    [0.400, 0.400, 0.200, 0.200],
        "coffer_field_w":  [0.250, 0.430, 0.100, 0.140],
        "vault_ring":      [0.430, 0.180, 0.140, 0.070],
        # QA-02-12: the two barrel-vault soffit bands flanking the coffered octagon, and the frame's own sky (the
        # blue wedge in the bottom-left corner, seen out past the vault). These three boxes reproduce QA's round-02
        # numbers on round02_04_rotunda_ceiling.png: soffit 25.7 / 28.1, sky 130.4, ratio 0.197 / 0.215 vs QA's 0.20.
        "vault_soffit_w":  [0.075, 0.280, 0.075, 0.220],
        "vault_soffit_e":  [0.800, 0.300, 0.075, 0.220],
        "own_sky":         [0.005, 0.830, 0.045, 0.120],
    },
    # ---- cam06 aerial (render): dome cap and the lawn west of the lagoon ----
    "aerial": {
        "dome_top":        [0.435, 0.165, 0.050, 0.040],
        "lawn":            [0.060, 0.090, 0.100, 0.060],
    },
    # ---- cam06 aerial, QA-02-8: does distance still separate things, and is the veil warm rather than grey-olive?
    # On round02_06_aerial.png these give sat 0.081-0.091 at hue 57-70 everywhere and dome/far-shore contrast 1.00:1,
    # which is exactly the collapse QA measured.
    "aerial_haze": {
        "far_shore":       [0.250, 0.085, 0.220, 0.045],
        "far_hills":       [0.560, 0.055, 0.180, 0.040],
        "dome_cap":        [0.700, 0.135, 0.045, 0.035],
        "rotunda_attic":   [0.690, 0.230, 0.060, 0.030],
        "lagoon_far":      [0.300, 0.155, 0.150, 0.040],
        "trees_far":       [0.120, 0.150, 0.100, 0.050],
    },
    "aerial_ref105": {
        "dome_top":        [0.676, 0.836, 0.020, 0.018],
        "lawn":            [0.735, 0.880, 0.040, 0.035],
    },
    # ---- dome cap seen from the lagoon, render / ref 169 (golden-hour photometric check for QA-01-20) ----
    "dome_hero":       {"dome_cap": [0.455, 0.055, 0.060, 0.035]},
    "dome_hero_ref169": {"dome_cap": [0.455, 0.145, 0.055, 0.030]},
}
RATIOS = {}


def srgb_to_linear(c):
    c = np.asarray(c, dtype=np.float64)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def load(path):
    im = Image.open(path).convert("RGB")
    return np.asarray(im, dtype=np.float64) / 255.0


def stats(arr, rect):
    h, w = arr.shape[:2]
    x, y, rw, rh = rect
    x0, y0 = int(round(x * w)), int(round(y * h))
    x1, y1 = max(x0 + 1, int(round((x + rw) * w))), max(y0 + 1, int(round((y + rh) * h)))
    patch = arr[y0:y1, x0:x1]
    m = patch.reshape(-1, 3).mean(axis=0)
    lin = srgb_to_linear(m)
    Y = float(0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2])
    mx, mn = float(m.max()), float(m.min())
    sat = 0.0 if mx <= 0 else (mx - mn) / mx
    # hue angle of the sRGB mean
    r, g, b = m
    d = mx - mn
    if d <= 1e-9:
        hue = 0.0
    elif mx == r:
        hue = (60 * ((g - b) / d)) % 360
    elif mx == g:
        hue = 60 * ((b - r) / d) + 120
    else:
        hue = 60 * ((r - g) / d) + 240
    return dict(srgb=[round(float(v) * 255, 1) for v in m], Y=Y, hue=round(hue, 1), sat=round(sat, 3),
                px=[x0, y0, x1, y1], std=round(float(patch.reshape(-1, 3).std()) * 255, 1))


def measure(path, regions):
    arr = load(path)
    return {name: stats(arr, rect) for name, rect in regions.items()}


def report(path, regions, label=""):
    res = measure(path, regions)
    print(f"--- {label or Path(path).name}")
    for k, v in res.items():
        print(f"    {k:26s} sRGB {v['srgb'][0]:5.1f},{v['srgb'][1]:5.1f},{v['srgb'][2]:5.1f}  Y {v['Y']:.4f}  hue {v['hue']:5.1f}  sat {v['sat']:.3f}  sd {v['std']:.1f}")
    return res


def grid_overlay(path, out, width=960, regions=None, step=0.05):
    im = Image.open(path).convert("RGB")
    W, H = im.size
    sc = width / W
    im = im.resize((width, int(round(H * sc))), Image.LANCZOS)
    d = ImageDraw.Draw(im)
    w, h = im.size
    for i in range(1, int(1 / step)):
        f = i * step
        col = (255, 60, 60) if abs(f * 100 % 10) < 1e-6 else (90, 90, 90)
        d.line([(f * w, 0), (f * w, h)], fill=col, width=1)
        d.line([(0, f * h), (w, f * h)], fill=col, width=1)
        if abs(f * 100 % 10) < 1e-6:
            d.text((f * w + 2, 2), f"{int(f*100)}", fill=(255, 220, 0))
            d.text((2, f * h + 2), f"{int(f*100)}", fill=(255, 220, 0))
    if regions:
        for name, (x, y, rw, rh) in regions.items():
            d.rectangle([x * w, y * h, (x + rw) * w, (y + rh) * h], outline=(0, 255, 255), width=2)
            d.text((x * w + 3, y * h - 11), name, fill=(0, 255, 255))
    im.save(out, quality=88)
    return out


def pair(render, ref, out, regions=None, width=1400, labels=("render", "reference")):
    """Side by side, both resized to the same height, with the region boxes drawn on each."""
    ims = []
    for p, lab in zip((render, ref), labels):
        im = Image.open(p).convert("RGB")
        ims.append(im)
    h = 540
    outs = []
    for im, lab in zip(ims, labels):
        W, H = im.size
        im = im.resize((int(round(W * h / H)), h), Image.LANCZOS)
        d = ImageDraw.Draw(im)
        if regions:
            w2, h2 = im.size
            for name, (x, y, rw, rh) in regions.items():
                d.rectangle([x * w2, y * h2, (x + rw) * w2, (y + rh) * h2], outline=(0, 255, 255), width=2)
                d.text((x * w2 + 3, max(0, y * h2 - 11)), name, fill=(0, 255, 255))
        d.text((6, 6), lab, fill=(255, 255, 0))
        outs.append(im)
    tw = sum(i.size[0] for i in outs) + 8
    canvas = Image.new("RGB", (tw, h), (20, 20, 20))
    x = 0
    for im in outs:
        canvas.paste(im, (x, 0)); x += im.size[0] + 8
    canvas.save(out, quality=88)
    return out


# --------------------------------------------------------------------------- round-09 acceptance summaries
# Display-referred luminance of an sRGB 0-255 mean (this is what QA's numbers and lighting_notes 17 quote as "lum";
# it is NOT the scene-linear Y above). ref 169 / ref 083 targets are baked in so one call answers "does it pass?".
def disp_lum(srgb):
    return 0.2126 * srgb[0] + 0.7152 * srgb[1] + 0.0722 * srgb[2]


# ref 169 measured with REGIONS["hero_ref169"]: attic_sunlit_b 232.7/189.1/98.6, sky_top 116.0/174.4/226.1,
# shade_north 147.5/112.1/78.0. Windows are QA's: attic lum -10 %, sky top +-10 %, shade -20 %, R-B >= 110.
HERO_TARGETS = dict(attic_lum=(172.6, None), attic_rb=(110.0, None), sky_lum=(149.1, 182.3), shade_lum=(93.8, None))
HERO_REF = dict(attic_lum=191.8, attic_rb=134.1, sky_lum=165.7, shade_lum=117.2)
# ref 083 (rotunda ceiling): vault soffit / the frame's own sky 0.58, coffer field / own sky 0.39.
CEILING_REF = dict(soffit=0.58, coffer=0.39)


def summary(path, kind="hero"):
    if kind == "hero":
        m = measure(path, REGIONS["hero"])
        a, sk, sh = m["attic_sunlit_b"]["srgb"], m["sky_top"]["srgb"], m["shade_north"]["srgb"]
        out = dict(attic_lum=disp_lum(a), attic_rb=a[0] - a[2], sky_lum=disp_lum(sk), shade_lum=disp_lum(sh),
                   attic_srgb=a)
        print(f"--- {Path(path).name}")
        for k in ("attic_lum", "attic_rb", "sky_lum", "shade_lum"):
            lo, hi = HERO_TARGETS[k]
            ok = (out[k] >= lo) and (hi is None or out[k] <= hi)
            print(f"    {k:10s} {out[k]:6.1f}   ref {HERO_REF[k]:6.1f}   target "
                  f"{lo:.1f}{'-' + format(hi, '.1f') if hi else '+':>8s}   {'PASS' if ok else 'fail'}")
        print(f"    attic sRGB {a[0]:.1f}, {a[1]:.1f}, {a[2]:.1f}")
        return out
    m = measure(path, REGIONS["ceiling"])
    sky = disp_lum(m["own_sky"]["srgb"])
    sw, se = disp_lum(m["vault_soffit_w"]["srgb"]), disp_lum(m["vault_soffit_e"]["srgb"])
    cof = disp_lum(m["coffer_field"]["srgb"])
    out = dict(soffit_w=sw / sky, soffit_e=se / sky, soffit=(sw + se) / (2 * sky), coffer=cof / sky, sky=sky)
    print(f"--- {Path(path).name}")
    print(f"    own_sky lum {sky:6.1f}")
    for k in ("soffit", "coffer"):
        r = CEILING_REF[k]
        print(f"    {k:8s}/sky {out[k]:.3f}   ref 083 {r:.2f}   delta {out[k] - r:+.3f}   "
              f"{'PASS' if abs(out[k] - r) <= 0.08 else 'fail'}")
    print(f"    soffit W/E {out['soffit_w']:.3f} / {out['soffit_e']:.3f}   soffit/coffer {out['soffit'] / out['coffer']:.3f}")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--summary", choices=["hero", "ceiling"])
    ap.add_argument("images", nargs="*")
    ap.add_argument("--regions")
    ap.add_argument("--rect", action="append", default=[])
    ap.add_argument("--grid", nargs=2)
    ap.add_argument("--pair", nargs=3)
    ap.add_argument("--json")
    a = ap.parse_args()
    regs = dict(REGIONS.get(a.regions, {})) if a.regions else {}
    for i, r in enumerate(a.rect):
        regs[f"rect{i}"] = [float(v) for v in r.split(",")]
    if a.grid:
        print(grid_overlay(a.grid[0], a.grid[1], regions=regs))
    if a.pair:
        print(pair(a.pair[0], a.pair[1], a.pair[2], regions=regs))
    out = {}
    for p in a.images:
        out[p] = summary(p, a.summary) if a.summary else report(p, regs)
    if a.json:
        Path(a.json).write_text(json.dumps(out, indent=1))
