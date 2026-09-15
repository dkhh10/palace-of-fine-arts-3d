#!/usr/bin/env python3
"""QA round 11c: the Gate 1 composite -> renders/web/round11c_gate.png (960 px).

Row 1-2: the six clean stations (?billboards=0&treeboards=0), viewer only.
Row 3  : the three pieces of evidence this round turns on -
         cam01 at the projected WORLD ORIGIN (the shrub pile), the cam01 main-arch opening,
         and the cam04 QA-11-9 box 11b -> 11c (the decimation shard gone, the near shrub left).
No Blender, no Chrome.
"""
import json, sys
from PIL import Image, ImageDraw

R = "/Users/dk/Projects/3d render blender 3rd attempt building"
OUT = f"{R}/renders/web/round11c_gate.png"
W = 960
BG = (17, 17, 19)
FG = (238, 233, 223)


def ref_of(st):
    return json.load(open(f"{R}/renders/web/gate1_pair_cam{st:02d}.png.json"))["reference"]["path"]


def fit(im, w):
    return im.resize((w, round(im.height * w / im.width)), Image.LANCZOS)


def crop(im, box, k=2):
    w, h = box[2] - box[0], box[3] - box[1]
    return im.crop(box).resize((w * k, h * k), Image.NEAREST)


def main(old_dir=None):
    st_w = (W - 4 * 6) // 3
    tiles = []
    for st in range(1, 7):
        v = Image.open(f"{R}/renders/web/gate1_cam{st:02d}.png").convert("RGB")
        tiles.append(fit(v, st_w))
    th = tiles[0].height
    ev_w = (W - 4 * 6) // 3
    v1 = Image.open(f"{R}/renders/web/gate1_cam01.png").convert("RGB")
    r1 = Image.open(f"{R}/{ref_of(1)}").convert("RGB").resize(v1.size, Image.LANCZOS)
    v4 = Image.open(f"{R}/renders/web/gate1_cam04.png").convert("RGB")
    ev = []
    # 1: cam01 around the projected world origin (960,655): viewer | reference
    b = (900, 592, 1020, 672)
    ev.append(("cam01 world origin: the 1379-shrub pile | Phase 5", [crop(v1, b), crop(r1, b)]))
    # 2: cam01 main arch opening: viewer | reference
    b = (890, 430, 1040, 650)
    ev.append(("cam01 main arch: sky + far side, no near vault | Phase 5", [crop(v1, b, 1), crop(r1, b, 1)]))
    # 3: cam04 QA-11-9 box, 11b (if available) | 11c
    b = (420, 60, 700, 380)
    pair = []
    if old_dir:
        try:
            pair.append(crop(Image.open(f"{old_dir}/old_cam04.png").convert("RGB"), b, 1))
        except OSError:
            pass
    pair.append(crop(v4, b, 1))
    ev.append(("cam04 QA-11-9: 11b shard | 11c as modelled (shrub left)", pair))
    evs = []
    for cap, ims in ev:
        strip = Image.new("RGB", (sum(i.width for i in ims) + 4 * (len(ims) - 1),
                                  max(i.height for i in ims)), BG)
        x = 0
        for i in ims:
            strip.paste(i, (x, 0)); x += i.width + 4
        evs.append((cap, fit(strip, ev_w)))
    eh = max(s.height for _, s in evs)
    H = 34 + 2 * (th + 16) + eh + 18
    out = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(out)
    d.text((8, 8), "QA round 11c - Phase 6 Gate 1, third check. Export 2c1c7fe, both placeholder sets hidden "
                   "(?billboards=0&treeboards=0). Measured board coverage 0 %.", fill=FG)
    d.text((8, 20), "GATE 1 FAIL - 1379 ENV_shrub_*_LOD2 nodes export with no transform and draw stacked at the "
                    "world origin; the site planting is absent at all six stations. Owner: export.", fill=(255, 150, 140))
    y = 34
    for r in range(2):
        for c in range(3):
            i = r * 3 + c
            x = 6 + c * (st_w + 6)
            out.paste(tiles[i], (x, y + 12))
            d.text((x + 2, y + 1), f"cam{i+1:02d}", fill=FG)
        y += th + 16
    for c, (cap, s) in enumerate(evs):
        x = 6 + c * (ev_w + 6)
        out.paste(s, (x, y + 12))
        d.text((x + 2, y + 1), cap[:62], fill=FG)
    out.save(OUT)
    print(f"[qa_r11c_gate] {OUT} {out.size}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
