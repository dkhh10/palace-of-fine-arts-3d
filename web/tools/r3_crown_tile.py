#!/usr/bin/env python3
"""6c round 3 — the three QA crown boxes at 100 %, reference | round16b | candidate, one sheet.

    web/tools/r3_crown_tile.py --tag r3i090015 [--boxes crown|shrub]

Every panel is a 1:1 crop of the box QA measures (scripts/qa_r16_probe.py CROWN / FOLIAGE16), so the
sheet and the table are the same pixels.  Full-res to renders/web/tiles/<tag>/, 960 px copy to
renders/web/960/ for committing.
"""
import argparse
import os
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
WEB = ROOT / "renders" / "web"
# the reference frames live in the MAIN checkout only (CLAUDE.md); a worktree reads them by that path
MAIN = Path(os.environ.get("PFA_MAIN_ROOT", "/Users/dk/Projects/3d render blender 3rd attempt building"))
REF = {
    1: MAIN / "renders/previews/qa/round10b_01_lagoon_hero_cycles.png",
    2: MAIN / "renders/previews/qa/round13_02_lagoon_ne_threequarter_cycles.png",
    3: MAIN / "renders/previews/qa/round13_03_colonnade_walk_cycles.png",
    5: MAIN / "renders/previews/qa/round13_05_south_lawn_cycles.png",
}
CROWN = [("01", 1, (760, 545, 1000, 690)), ("02", 2, (700, 660, 1240, 950)), ("05", 5, (300, 580, 500, 870))]
SHRUB = [("01", 1, (0, 620, 640, 700)), ("02", 2, (40, 860, 640, 1060)),
         ("03", 3, (860, 620, 1280, 750)), ("05", 5, (200, 840, 1200, 930))]


def crop(path, box):
    if not Path(path).exists():
        return None
    im = Image.open(path).convert("RGB")
    if im.size != (1920, 1080):
        im = im.resize((1920, 1080), Image.LANCZOS)
    return im.crop(box)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True)
    ap.add_argument("--prev", default="round16b")
    ap.add_argument("--boxes", default="crown")
    a = ap.parse_args()
    rows = CROWN if a.boxes == "crown" else SHRUB
    gap = 8
    panels = []
    for name, st, box in rows:
        row = [crop(REF[st], box), crop(WEB / f"{a.prev}_cam{st:02d}.png", box),
               crop(WEB / f"{a.tag}_cam{st:02d}.png", box)]
        if any(p is None for p in row):
            continue
        w = sum(p.width for p in row) + gap * 2
        h = max(p.height for p in row)
        im = Image.new("RGB", (w, h), (24, 26, 30))
        x = 0
        for p in row:
            im.paste(p, (x, 0))
            x += p.width + gap
        panels.append(im)
    if not panels:
        print("r3_crown_tile: nothing to tile")
        return
    W = max(p.width for p in panels)
    H = sum(p.height for p in panels) + gap * (len(panels) - 1)
    sheet = Image.new("RGB", (W, H), (24, 26, 30))
    y = 0
    for p in panels:
        sheet.paste(p, (0, y))
        y += p.height + gap
    out = WEB / "tiles" / a.tag / f"{a.tag}_{a.boxes}_tile.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    small = WEB / "960"
    small.mkdir(parents=True, exist_ok=True)
    c = sheet.copy()
    c.thumbnail((960, 10000), Image.LANCZOS)
    c.save(small / f"{a.tag}_{a.boxes}_tile.jpg", quality=88)
    print(f"{out} ({sheet.width}x{sheet.height}); 960 px copy in {small}")
    print("panel order per row: Cycles reference | " + a.prev + " | " + a.tag)


if __name__ == "__main__":
    main()
