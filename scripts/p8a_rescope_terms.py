#!/usr/bin/env python3
"""Phase 8a re-scope — question 2: WHERE the shrub cards' colour comes from.

No Blender, no Chrome, no rendering: the card albedo texture, the baked per-placement irradiance and
the viewer's own constants, read off disk and multiplied out by hand.

    python3 scripts/p8a_rescope_terms.py albedo      # the card albedo maps: sRGB / linear / after tint
    python3 scripts/p8a_rescope_terms.py irradiance  # the per-placement baked irradiance, per prototype
    python3 scripts/p8a_rescope_terms.py product     # albedo x irradiance x env, the predicted card colour
    python3 scripts/p8a_rescope_terms.py all

The viewer's card shading (web/src/foliage.js, read, not run):
  * the front SUN diffuse is removed (`specularOnlySun`): a card's diffuse is ONE baked scene-linear
    irradiance per PLACEMENT, added with no cosine (`export/out/gate3/instance_irradiance.json`);
  * the environment lobe is scaled by `CARD_ENV = 0.3` (diffuse probe + specular + sheen);
  * the translucent back lobe is OFF for cards by default (`trnShrubs`, `?leaftrn=shrubs`);
  * albedo = clip(source_linear * tint), tint from `export/out/gate3/foliage/foliage_tex.json`.
So the only chromatic inputs are the albedo map, the per-placement irradiance and the probe.
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

MAIN = Path("/Users/dk/Projects/3d render blender 3rd attempt building")
ROOT = Path(__file__).resolve().parents[1]
TEXDIR = ROOT / "assets" / "textures" / "foliage"
FOLIAGE_TEX = MAIN / "export/out/gate3/foliage/foliage_tex.json"
IRR = MAIN / "export/out/gate3/instance_irradiance.json"

CARD_ENV = 0.3        # web/src/foliage.js CARD_ENV
CARD_MATS = ["MAT_shrub", "MAT_shrub_light", "MAT_shrub_dry", "MAT_reeds"]
SHRUB_PROTO = ("agap", "big", "maho", "pitto", "reed", "twig")


def srgb_to_linear(x):
    x = np.asarray(x, dtype=np.float64) / 255.0
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)


def hsv(rgb):
    """(hue deg, sat, value) of a single RGB triple in any linear or display units."""
    rgb = np.asarray(rgb, dtype=np.float64)
    mx, mn = rgb.max(), rgb.min()
    s = 0.0 if mx <= 0 else (mx - mn) / mx
    if mx == mn:
        h = 0.0
    elif mx == rgb[0]:
        h = (60 * (rgb[1] - rgb[2]) / (mx - mn)) % 360
    elif mx == rgb[1]:
        h = 60 * (rgb[2] - rgb[0]) / (mx - mn) + 120
    else:
        h = 60 * (rgb[0] - rgb[1]) / (mx - mn) + 240
    return h, s, mx


def load_tex(name):
    """RGBA of a foliage source map, plus the covered (alpha >= cutoff) mask."""
    im = Image.open(TEXDIR / name).convert("RGBA")
    a = np.asarray(im, dtype=np.float64)
    return a[..., :3], a[..., 3] / 255.0


def cmd_albedo():
    tex = json.loads(FOLIAGE_TEX.read_text())["materials"]
    print("== the card albedo maps: the source image, the export tint, and the tinted linear colour ==")
    print(f"{'material':18s} {'source':22s} {'cov%':>5s} {'srgb mean RGB':>22s} "
          f"{'linear mean RGB':>26s} {'tint':>20s} {'tinted linear':>26s} {'hue':>6s} {'sat':>5s} {'val':>6s}")
    out = {}
    for m in CARD_MATS:
        e = tex[m]
        src = e["stats"]["source"]
        rgb, alpha = load_tex(src)
        cov = alpha >= e["stats"].get("alpha_cutoff", 0.5)
        px = rgb[cov]
        lin = srgb_to_linear(px)
        tint = np.array(e["stats"]["tint"], dtype=np.float64)
        tl = np.clip(lin.mean(0) * tint, 0, 1)
        h, s, v = hsv(tl)
        out[m] = dict(tinted=tl, hue=h, sat=s, val=v, cov=float(cov.mean()))
        print(f"{m:18s} {src:22s} {cov.mean()*100:4.1f}% {str(np.round(px.mean(0),1)):>22s} "
              f"{str(np.round(lin.mean(0),4)):>26s} {str(np.round(tint,2)):>20s} "
              f"{str(np.round(tl,4)):>26s} {h:6.1f} {s:5.3f} {v:6.3f}")
    print("\n-- the albedo is a GREEN map: hue 90-105 deg at saturation 0.45-0.60 in linear.")
    return out


def _proto(name):
    for p in SHRUB_PROTO:
        if p in name:
            return p
    return "?"


def cmd_irradiance():
    d = json.loads(IRR.read_text())
    print("== the baked per-placement irradiance that REPLACES the sun diffuse on every card ==")
    print(f"   units: scene-linear irradiance / pi (x pi = irradiance), {d['placements']} placements, "
          f"{d['meshes_n']} prototypes")
    print(f"{'prototype':10s} {'n':>5s} {'mean RGB (lin)':>28s} {'G/R':>6s} {'B/G':>6s} "
          f"{'hue':>6s} {'sat':>6s} {'lum':>7s} {'p10 lum':>8s} {'p90 lum':>8s}")
    rows, allrgb = {}, []
    for k, e in d["meshes"].items():
        p = _proto(k)
        rows.setdefault(p, []).extend([x["rgb"] for x in e["placements"]])
    LUMA = np.array([0.2126, 0.7152, 0.0722])
    for p, v in sorted(rows.items()):
        a = np.array(v, dtype=np.float64)
        allrgb.append(a)
        m = a.mean(0)
        h, s, _ = hsv(m)
        lum = a @ LUMA
        print(f"{p:10s} {len(a):5d} {str(np.round(m,4)):>28s} {m[1]/max(m[0],1e-9):6.3f} "
              f"{m[2]/max(m[1],1e-9):6.3f} {h:6.1f} {s:6.3f} {lum.mean():7.3f} "
              f"{np.percentile(lum,10):8.3f} {np.percentile(lum,90):8.3f}")
    a = np.concatenate(allrgb)
    m = a.mean(0)
    h, s, _ = hsv(m)
    print(f"{'ALL':10s} {len(a):5d} {str(np.round(m,4)):>28s} {m[1]/max(m[0],1e-9):6.3f} "
          f"{m[2]/max(m[1],1e-9):6.3f} {h:6.1f} {s:6.3f} {(a@LUMA).mean():7.3f}")
    print("\n-- G/R < 1 means the light the cards are multiplied by is WARM: it rotates the albedo's")
    print("   green hue toward yellow and it does it identically on every texel of the card, because")
    print("   there is no cosine and no shadow term left to make a shaded face.")
    return a


def cmd_product():
    alb = cmd_albedo()
    print()
    irr = cmd_irradiance()
    print("\n== albedo x irradiance: the card's scene-linear colour before the probe and the LUT ==")
    print(f"{'material':18s} {'x mean irradiance':>30s} {'hue':>6s} {'sat':>6s}  "
          f"{'x p10 irradiance':>28s} {'hue':>6s} {'sat':>6s}")
    LUMA = np.array([0.2126, 0.7152, 0.0722])
    lum = irr @ LUMA
    lo = irr[lum <= np.percentile(lum, 10)].mean(0)
    mid = irr.mean(0)
    for m, e in alb.items():
        a = e["tinted"]
        for tag, k in (("mean", mid), ("p10", lo)):
            c = a * k
            h, s, _ = hsv(c)
            if tag == "mean":
                head = f"{m:18s} {str(np.round(c,4)):>30s} {h:6.1f} {s:6.3f}  "
            else:
                print(head + f"{str(np.round(c,5)):>28s} {h:6.1f} {s:6.3f}")
    print("\n-- compare these hues with the leaf hue the capture measures in the shrub boxes")
    print("   (p8a_rescope_boxes.py decomp): the shift from the albedo's ~95 deg is the light's.")


def main():
    cmds = {"albedo": cmd_albedo, "irradiance": cmd_irradiance, "product": cmd_product}
    for a in (sys.argv[1:] or ["all"]):
        if a == "all":
            cmd_product()
        elif a in cmds:
            cmds[a]()
        else:
            print(f"unknown command {a!r}; one of {', '.join(cmds)} or all")


if __name__ == "__main__":
    main()
