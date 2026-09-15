#!/usr/bin/env python3
"""QA round 11 gate composite: renders/web/round11_gate.png (960 px wide).

Six station pairs (viewer | Phase 5 render of the same station, from renders/web/gate1_pairs.json),
the cam01 tile defect list and the verdict. Analysis only: no Blender, no Chrome.

    python3 scripts/qa_r11_gate.py
"""
import json
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
W = 960
BG, FG, DIM, RED = (18, 18, 20), (234, 230, 222), (150, 148, 142), (232, 96, 84)

TILES = [
    ("r1c1 (0,0,640,540)", "colonnade-roof canopy thinned to sparse leaf clusters; (390,470)-(640,540)", "export"),
    ("r1c2 (640,0,1280,540)", "attic relief panels torn: black voids + speckle, (820,195)-(1000,285)", "export/ORN"),
    ("r1c3 (1280,0,1920,540)", "south colonnade canopy absent, (1280,440)-(1560,540)", "export"),
    ("r2c1 (0,540,640,1080)", "placeholder slabs over the colonnade shore, (430,540)-(640,900)", "viewer"),
    ("r2c1 (0,540,640,1080)", "water is a ripple-free mirror; slab reflections are hard rectangles", "viewer"),
    ("r2c2 (640,540,1280,1080)", "main-arch opening 37.4 % covered by placeholder quads, (917,465)-(1000,620)", "viewer"),
    ("r2c2 (640,540,1280,1080)", "shore planting + podium base hidden, (640,555)-(1280,900)", "viewer"),
    ("r2c3 (1280,540,1920,1080)", "colonnade stylobate + riprap a flat slab, (1280,540)-(1600,760)", "viewer"),
    ("off-tile cam04", "ORN decimation sliver across the ceiling coffers, (470,140)-(600,350)", "export/ORN"),
    ("off-tile all", "BLOCKER 10 MAT_EXP_ENVBD__* have baseColorTexture.texCoord -1: shader fails,", "export"),
    ("", "151,737 placed tris (19.1 % of ENV) never drawn at any station", "export"),
]

HEAD = [
    "QA round 11 - Phase 6 GATE 1 (geometry freeze). Verdict: FAIL.",
    "Blocker 1 (export): env.gltf ships 10 MAT_EXP_ENVBD__* materials with baseColorTexture.texCoord = -1.",
    "  three builds MAP_UV = uv18446744073709552000, the vertex shader fails, 151,737 tris never draw.",
    "Blocker 2 (export/ORN): the 3 voxel-remeshed attic panels read as torn relief at cam02 / cam05 / cam01.",
    "Budget PASS  ARCH 844,554 / ORN 1,099,194 / ENV 792,822 = 2,736,570 of 3.0 M; 154 batches, 140 at cam01.",
    "Perf  PASS   1440p: 255-269 draw calls, GPU 0.6-2.1 ms median, 16.6-16.8 ms presented = 60 fps vsync-capped",
    "             (uncapped 476-1667 fps). Resident 1.083 GB of the 1.2 GB plan. Name sweep 2540 objects, 0 hits.",
    "Silhouette   cam01 vs the Phase 5 Cycles hero: scale 1.0000, dx 0.0, dy 0.0, apex delta 0.00 %H,",
    "             profile mean |d| 0.81 px = 0.075 %H, p95 3 px. The decimation costs no silhouette.",
    "Not scored   grey materials, `direct` lighting; the glb probe/foliage albedos were written linear, not sRGB,",
    "             so every luma number in gate1_pairs.json is unusable this round.",
]


def main():
    sheets = json.loads((ROOT / "renders/web/gate1_pairs.json").read_text())["sheets"]
    pw = (W - 24) // 2
    rows = []
    for s in sheets:
        v = Image.open(ROOT / s["viewer"]["path"]).convert("RGB")
        r = Image.open(ROOT / s["reference"]["path"]).convert("RGB")
        ph = round(pw * v.height / v.width)
        rows.append((s, v.resize((pw, ph), Image.LANCZOS), r.resize((pw, ph), Image.LANCZOS)))

    line = 13
    head_h = 16 + line * len(HEAD) + 8
    row_h = rows[0][1].height + 16
    tile_h = 22 + line * (len(TILES) + 1) + 10
    img = Image.new("RGB", (W, head_h + row_h * 6 + tile_h + 8), BG)
    d = ImageDraw.Draw(img)

    y = 8
    for i, t in enumerate(HEAD):
        d.text((10, y), t, fill=RED if i in (1, 3) else FG)
        y += line
    y += 8
    for s, v, r in rows:
        d.text((10, y), "station %d  %s   |  viewer (gate 1 export, grey, direct)" % (s["station"], s["station_name"]),
               fill=FG)
        d.text((pw + 22, y), s["reference"]["label"], fill=DIM)
        y += 14
        img.paste(v, (8, y))
        img.paste(r, (pw + 16, y))
        y += v.height + 2
    y += 8
    d.text((10, y), "cam01 100 %% tile review (3 x 2 of 1920x1080) - %d defects" % len(TILES), fill=FG)
    y += 18
    for tile, what, owner in TILES:
        d.text((10, y), tile, fill=DIM)
        d.text((176, y), what, fill=RED if "BLOCKER" in what else FG)
        d.text((W - 62, y), owner, fill=DIM)
        y += line
    out = ROOT / "renders/web/round11_gate.png"
    img.save(out)
    print("wrote", out, img.size)


if __name__ == "__main__":
    main()
