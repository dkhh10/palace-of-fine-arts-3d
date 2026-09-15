#!/usr/bin/env python3
"""QA round 11b gate composite: renders/web/round11b_gate.png (960 px wide).

Six station pairs (viewer | Phase 5 render of the same station, from renders/web/gate1_pairs.json),
the round-11 tile list restated FIXED / OPEN / GATE 4, the new defects and the verdict.
Analysis only: no Blender, no Chrome.    python3 scripts/qa_r11b_gate.py
"""
import json
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
W = 960
BG, FG, DIM, RED, GRN = (18, 18, 20), (234, 230, 222), (150, 148, 142), (232, 96, 84), (126, 196, 128)

TILES = [
    ("FIXED", "QA-11-11 backdrop never drew", "all 4 gltf: 0 negative texCoord; 12 programs (was 13), no shader error;"),
    ("", "", "city blocks + hill + forest + lawn visible at cam06 / cam05 / the cam01 horizon"),
    ("FIXED", "QA-11-2 / -10 attic panels torn", "lo from LOD1 (35.9k/35.7k/35.8k -> 7,999), voxel_remeshed []; r1c2,"),
    ("", "", "cam02 (640,120)-(940,340) and cam05 (680,110)-(1220,250) at 100 %: continuous relief, no voids"),
    ("OPEN", "QA-11-4/-6/-7/-8 slabs hide the shore", "NOT the viewer quads: 127 opaque ENV_treeboard_* in env.glb"),
    ("OPEN", "QA-11-9 ORN sliver on the cam04 ceiling", "unchanged: thin normal-mapped wedge + loose shard, (400,80)-(600,350)"),
    ("OPEN", "QA-11-1 / -3 colonnade-roof canopy", "far-tree list; bare until the Gate 3 impostor bake"),
    ("GATE 4", "QA-11-5 water is a ripple-free mirror", "viewer; the boards reflect as hard rectangles (r2c1, r2c3)"),
    ("NEW", "QA-11b-1 BLOCKER placeholder coverage", "cam01 16.0 %, 02 19.7 %, 03 23.2 %, 04 0 %, 05 25.5 %, 06 19.6 %;"),
    ("", "", "44.5 % of the cam01 main-arch opening box (917,465)-(1000,620); boards up to 42 x 31 m"),
    ("NEW", "QA-11b-2 the name sweep cannot see them", "pattern has no board|impostor|billboard term -> 127 objects pass as 0 hits"),
    ("NEW", "QA-11b-3 far trees drawn twice", "with ?billboards=1 (the default) the export boards AND the viewer quads draw"),
    ("NEW", "QA-11b-4 sRGB re-encode not observable", "cam04 pixel-identical to round 11 (frame mean 88.51 -> 88.52)"),
]

HEAD = [
    "QA round 11b - Phase 6 GATE 1 re-check (export ec4832b, capture 15:31, ?billboards=0). Verdict: FAIL.",
    "B1 backdrop texCoord = -1        FIXED - asserted in gltf_gate1.py, 151,737 tris draw again (cam05/cam06).",
    "B2 voxel-remeshed attic panels   FIXED - rebuilt from LOD1 at 7,999 tris; relief continuous at 100 % everywhere.",
    "BLOCKER (export): ?billboards=0 hides only the VIEWER's 127 quads. The export ships its own 127 opaque",
    "  ENV_treeboard_* boards inside env.glb - 16.0 % of cam01 and 44.5 % of the main-arch opening are still a",
    "  placeholder, so the shore, podium, riprap and stylobate STILL cannot be judged. 94 of 127 sit within 40 m.",
    "BLOCKER 2 (export/ORN): the cam04 ceiling sliver (QA-11-9) is unchanged - a decimation artefact on the building.",
    "Budget PASS  ARCH 844,554 / ORN 1,099,192 / ENV 792,822 = 2,736,568 of 3.0 M; 154 batches, 140 at cam01.",
    "Perf   PASS  1440p: 78-203 draw calls, GPU 0.5-1.5 ms median (hero 1.5 = 6.8 % of the 22.2 ms 45 fps budget),",
    "             presented 16.6-17.2 ms = 60 fps vsync-capped, uncapped 667-2000. Resident 1.016 GB of 1.2 GB.",
    "             info.render tris 2.57-5.39 M = ~1.9x placed: the planar water reflector draws the scene twice.",
    "Silhouette   cam01 vs the Phase 5 Cycles hero: scale 1.0000, dx 0.0, dy 0.0, apex delta 0.00 %H (apex row 84,",
    "             corner-top row 209 in both). Unchanged by the attic rebuild.",
    "Not scored   grey materials, `direct` lighting: every luma / ratio in gate1_pairs.json stays out of the score.",
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
        d.text((10, y), t, fill=GRN if i in (1, 2) else RED if i in (0, 3, 4, 5, 6) else FG)
        y += line
    y += 8
    for s, v, r in rows:
        d.text((10, y), "station %d  %s   |  viewer (gate 1 export, grey, direct, billboards off)"
               % (s["station"], s["station_name"]), fill=FG)
        d.text((pw + 22, y), s["reference"]["label"], fill=DIM)
        y += 14
        img.paste(v, (8, y))
        img.paste(r, (pw + 16, y))
        y += v.height + 2
    y += 8
    d.text((10, y), "round-11 tile list restated + new defects (cam01 tiles re-cut from the 15:31 frame)", fill=FG)
    y += 18
    for state, what, detail in TILES:
        d.text((10, y), state, fill=GRN if state == "FIXED" else RED if state in ("OPEN", "NEW") else DIM)
        d.text((58, y), what, fill=FG)
        d.text((300, y), detail, fill=DIM)
        y += line
    out = ROOT / "renders/web/round11b_gate.png"
    img.save(out)
    print("wrote", out, img.size)


if __name__ == "__main__":
    main()
