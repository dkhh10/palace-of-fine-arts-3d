#!/usr/bin/env python3
"""QA round 11d: pixel proof that the ENV shrub layer is placed on the site, not stacked at the origin.

    python3 scripts/qa_r11d_probe.py nodes              # env.gltf transforms + shrub spread (no Blender)
    python3 scripts/qa_r11d_probe.py origin [old_dir]   # patches at the world-origin pixels: now / 11c / Phase 5
    python3 scripts/qa_r11d_probe.py bands  [old_dir]   # planting bands: foliage coverage now / 11c / Phase 5
    python3 scripts/qa_r11d_probe.py crops  [old_dir]   # write the origin-pixel crop strip for viewing
No Blender, no Chrome.
"""
import json, math, sys
import numpy as np
from PIL import Image

ROOT = "/Users/dk/Projects/3d render blender 3rd attempt building"
GLTF_ENV = f"{ROOT}/export/out/gate1/env.gltf"
OLD_DEFAULT = ("/private/tmp/claude-501/-Users-dk-Projects-3d-render-blender-3rd-attempt-building/"
               "6460c313-5668-4669-b492-8fb279bb75e2/scratchpad/old11c")

# world-origin projection per station, measured in round 11c (1920x1080 frames)
ORIGIN_PX = {1: (960, 655), 2: (960, 908), 4: None, 5: (960, 852), 6: (960, 654)}
# planting bands (x0,y0,x1,y1) in the 1920x1080 frame, from the Phase 5 renders
BANDS = {1: ("cam01 shore", (250, 560, 1700, 700)),
         2: ("cam02 shore", (200, 700, 1750, 980)),
         3: ("cam03 walk",  (0,   430, 1919, 900)),
         5: ("cam05 lawn",  (150, 620, 1800, 980)),
         6: ("cam06 site",  (150, 300, 1800, 900))}
REF = {1: "renders/previews/qa/round10b_01_lagoon_hero_cycles.png",
       2: "renders/previews/qa/round09_02_lagoon_ne_threequarter_cycles.png",
       3: "renders/previews/qa/round09_03_colonnade_walk.png",
       4: "renders/previews/qa/round09_04_rotunda_ceiling_cycles.png",
       5: "renders/previews/qa/round09_05_south_lawn.png",
       6: "renders/previews/qa/round09_06_aerial_nocomp.png"}


def rgb(path, size=(1920, 1080)):
    im = Image.open(path).convert("RGB")
    if im.size != size:
        im = im.resize(size, Image.LANCZOS)
    return np.asarray(im, dtype=np.float32)


def luma(a):
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def foliage_frac(a):
    """Fraction of pixels that read as foliage: green excess, or dark speckle under a leaf canopy."""
    g = a[..., 1] - 0.5 * (a[..., 0] + a[..., 2])
    return float(((g > 6) | ((luma(a) < 70) & (g > 1))).mean()) * 100


def patch(a, cx, cy, r=60):
    return a[max(0, cy - r):cy + r, max(0, cx - r):cx + r]


def cmd_nodes(_):
    d = json.load(open(GLTF_ENV))
    nodes = d["nodes"]
    def T(n):
        if "matrix" in n:
            m = n["matrix"]; return (m[12], m[13], m[14])
        if "translation" in n:
            return tuple(n["translation"])
        return None
    kinds = {}
    for n in nodes:
        name = n.get("name", "?")
        k = ("shrub" if "_shrub_" in name else "treeboard" if "treeboard" in name
             else "tree" if "_tree_" in name else "other")
        t = T(n)
        e = kinds.setdefault(k, {"n": 0, "notrans": 0, "near0": 0, "pts": []})
        e["n"] += 1
        if t is None:
            e["notrans"] += 1; e["near0"] += 1
        else:
            e["pts"].append(t)
            if math.dist(t, (0, 0, 0)) < 1.0:
                e["near0"] += 1
    print(f"{'class':>10} {'nodes':>6} {'no-xform':>9} {'within 1 m of origin':>21}  spread (x / y / z, m)")
    for k, e in sorted(kinds.items()):
        if e["pts"]:
            p = np.array(e["pts"])
            sp = " / ".join(f"{p[:, i].min():7.1f}..{p[:, i].max():6.1f}" for i in range(3))
        else:
            sp = "-"
        print(f"{k:>10} {e['n']:>6} {e['notrans']:>9} {e['near0']:>21}  {sp}")


def cmd_origin(argv):
    old = argv[0] if argv else OLD_DEFAULT
    print(f"{'st':>3} {'px':>12} | {'now L/std/fol%':>24} | {'11c L/std/fol%':>24} | "
          f"{'PhaseX L/std/fol%':>24} | now-vs-11c chg>4 %")
    for st, px in sorted((k, v) for k, v in ORIGIN_PX.items() if v):
        now = patch(rgb(f"{ROOT}/renders/web/gate1_cam{st:02d}.png"), *px)
        o = patch(rgb(f"{old}/old_cam{st:02d}.png"), *px)
        r = patch(rgb(f"{ROOT}/{REF[st]}"), *px)
        chg = float((np.abs(luma(now) - luma(o)) > 4).mean()) * 100
        def s(a):
            return f"{luma(a).mean():7.1f} {luma(a).std():6.1f} {foliage_frac(a):6.1f}"
        print(f"{st:>3} {str(px):>12} | {s(now):>24} | {s(o):>24} | {s(r):>24} | {chg:8.1f}")


def cmd_bands(argv):
    old = argv[0] if argv else OLD_DEFAULT
    print(f"{'st':>3} {'band':>12} {'box':>26} | foliage %% now / 11c / PhaseX")
    for st, (name, box) in sorted(BANDS.items()):
        x0, y0, x1, y1 = box
        def f(p):
            return foliage_frac(rgb(p)[y0:y1, x0:x1])
        print(f"{st:>3} {name:>12} {str(box):>26} | {f(f'{ROOT}/renders/web/gate1_cam{st:02d}.png'):6.1f} "
              f"{f(f'{old}/old_cam{st:02d}.png'):6.1f} {f(f'{ROOT}/{REF[st]}'):6.1f}")


def cmd_crops(argv):
    old = argv[0] if argv else OLD_DEFAULT
    out = []
    for st, px in sorted((k, v) for k, v in ORIGIN_PX.items() if v):
        row = [Image.fromarray(patch(rgb(p), *px).astype(np.uint8)) for p in
               (f"{ROOT}/renders/web/gate1_cam{st:02d}.png", f"{old}/old_cam{st:02d}.png", f"{ROOT}/{REF[st]}")]
        out.append(row)
    w, h = out[0][0].size
    sheet = Image.new("RGB", (3 * w + 16, len(out) * (h + 8)), (20, 20, 20))
    for i, row in enumerate(out):
        for j, im in enumerate(row):
            sheet.paste(im, (j * (w + 8), i * (h + 8)))
    p = f"{OLD_DEFAULT}/../origin_crops.png"
    sheet.save(p)
    print("wrote", p, sheet.size, "rows = stations 1,2,5,6; cols = now / 11c / Phase 5")


if __name__ == "__main__":
    cmds = {"nodes": cmd_nodes, "origin": cmd_origin, "bands": cmd_bands, "crops": cmd_crops}
    if len(sys.argv) < 2 or sys.argv[1] not in cmds:
        print(__doc__); sys.exit(2)
    cmds[sys.argv[1]](sys.argv[2:])
