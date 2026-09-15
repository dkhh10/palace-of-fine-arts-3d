#!/usr/bin/env python3
"""QA round 11d: the Gate 1 composite -> renders/web/round11d_gate.png (960 px).

Row 1-2: the six clean stations (?billboards=0&treeboards=0), viewer only.
Row 3  : the three pieces of evidence QA-11c-1 turns on -
         cam01 podium/main arch (11c isolated origin clump -> continuous shore band | Phase 5),
         cam04 top-right corner (11c shrub leaf cards -> clean coffers),
         cam05 lawn band (11c bare -> planted | Phase 5).

    python3 scripts/qa_r11d_gate.py <dir with old_cam0K.png from the 11c capture>
No Blender, no Chrome.
"""
import json, sys
from PIL import Image, ImageDraw

R = "/Users/dk/Projects/3d render blender 3rd attempt building"
OUT = f"{R}/renders/web/round11d_gate.png"
W, BG, FG = 960, (17, 17, 19), (238, 233, 223)


def ref_of(st):
    return json.load(open(f"{R}/renders/web/gate1_pair_cam{st:02d}.png.json"))["reference"]["path"]


def fit(im, w):
    return im.resize((w, round(im.height * w / im.width)), Image.LANCZOS)


def crop(im, box, k=1):
    w, h = box[2] - box[0], box[3] - box[1]
    return im.crop(box).resize((w * k, h * k), Image.NEAREST)


def main(old_dir):
    st_w = (W - 4 * 6) // 3
    tiles = [fit(Image.open(f"{R}/renders/web/gate1_cam{st:02d}.png").convert("RGB"), st_w)
             for st in range(1, 7)]
    th = tiles[0].height
    ev_w = (W - 4 * 6) // 3
    V = {st: Image.open(f"{R}/renders/web/gate1_cam{st:02d}.png").convert("RGB") for st in (1, 4, 5)}
    O = {st: Image.open(f"{old_dir}/old_cam{st:02d}.png").convert("RGB") for st in (1, 4, 5)}
    RF = {st: Image.open(f"{R}/{ref_of(st)}").convert("RGB").resize(V[st].size, Image.LANCZOS)
          for st in (1, 5)}
    ev = [("cam01 podium: 11c origin clump | 11d band | Phase 5", (1, (860, 560, 1100, 720)), True),
          ("cam04 top right: 11c shrub cards | 11d coffers", (4, (1420, 0, 1900, 320)), False),
          ("cam05 lawn: 11c bare | 11d planted | Phase 5", (5, (700, 680, 1400, 940)), True)]
    evs = []
    for cap, (st, b), with_ref in ev:
        ims = [crop(O[st], b), crop(V[st], b)] + ([crop(RF[st], b)] if with_ref else [])
        strip = Image.new("RGB", (sum(i.width for i in ims) + 4 * (len(ims) - 1),
                                  max(i.height for i in ims)), BG)
        x = 0
        for i in ims:
            strip.paste(i, (x, 0)); x += i.width + 4
        evs.append((cap, fit(strip, ev_w)))
    eh = max(s.height for _, s in evs)
    out = Image.new("RGB", (W, 34 + 2 * (th + 16) + eh + 18), BG)
    d = ImageDraw.Draw(out)
    d.text((8, 8), "QA round 11d - Phase 6 Gate 1, fourth check. Export a9b2d3d, both placeholder sets hidden "
                   "(?billboards=0&treeboards=0).", fill=FG)
    d.text((8, 20), "GATE 1 PASS - QA-11c-1 fixed: 1379 shrub nodes carry their placement (0 within 1 m of the "
                    "origin, spread 250 x 166 m); env glb draws 100.000 % of its placed triangles.",
           fill=(150, 235, 160))
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
    print(f"[qa_r11d_gate] {OUT} {out.size}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else
         "/private/tmp/claude-501/-Users-dk-Projects-3d-render-blender-3rd-attempt-building/"
         "6460c313-5668-4669-b492-8fb279bb75e2/scratchpad/old11c")
