#!/usr/bin/env python3
"""Phase 8 far-tree A/B tiles: the station-2 crown at 100 % and the hero crown at 200 %.

    python3 web/tools/p8_lod_tiles.py --out p8lod --panels "2K+0.15 card=p8lodA" "LOD2 @ 60 m=p8lodB" ...

Panel 0 is always the Cycles reference for that station, read from MAIN. The boxes are QA 17's own
crown boxes (web/tools/r3_crown_tile.py CROWN), so a tile and a table are the same pixels.
"""
import argparse, os
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
W = ROOT / "renders" / "web"
MAIN = Path(os.environ.get("PFA_MAIN_ROOT", "/Users/dk/Projects/3d render blender 3rd attempt building"))
REF = {1: MAIN / "renders/previews/qa/round10b_01_lagoon_hero_cycles.png",
       2: MAIN / "renders/previews/qa/round13_02_lagoon_ne_threequarter_cycles.png",
       5: MAIN / "renders/previews/qa/round13_05_south_lawn_cycles.png"}
BOX = {1: (760, 545, 1000, 690), 2: (700, 660, 1240, 950), 5: (300, 580, 500, 870)}


def crop(path, st, zoom):
    im = Image.open(path).convert("RGB")
    if im.size != (1920, 1080):
        im = im.resize((1920, 1080), Image.LANCZOS)
    c = im.crop(BOX[st])
    return c if zoom == 1 else c.resize((c.width * zoom, c.height * zoom), Image.NEAREST)


def sheet(st, zoom, panels, out_png, out_jpg):
    crops = [("Cycles", crop(REF[st], st, zoom))]
    for label, tag in panels:
        p = W / f"{tag}_cam{st:02d}.png"
        if not p.exists():
            print(f"  (missing {p.name})")
            continue
        crops.append((label, crop(p, st, zoom)))
    gap, lab = 8, 18
    im = Image.new("RGB", (sum(c.width for _, c in crops) + gap * (len(crops) - 1),
                           crops[0][1].height + lab), (24, 26, 30))
    d = ImageDraw.Draw(im)
    x = 0
    for label, c in crops:
        im.paste(c, (x, lab))
        d.text((x + 4, 4), label, fill=(220, 220, 210))
        x += c.width + gap
    out_png.parent.mkdir(parents=True, exist_ok=True)
    out_jpg.parent.mkdir(parents=True, exist_ok=True)
    im.save(out_png)
    s = im.copy()
    s.thumbnail((960, 10000), Image.LANCZOS)
    s.save(out_jpg, quality=88)
    print(f"{out_png} ({im.width}x{im.height}) -> {out_jpg}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="tag for the output names")
    ap.add_argument("--panels", nargs="+", required=True, help='"label=tag" pairs, in panel order')
    a = ap.parse_args()
    panels = [tuple(p.split("=", 1)) for p in a.panels]
    sheet(2, 1, panels, W / "tiles" / a.out / f"{a.out}_cam02_crown_100.png", W / "960" / f"{a.out}_cam02_crown.jpg")
    sheet(1, 2, panels, W / "tiles" / a.out / f"{a.out}_cam01_crown_200.png", W / "960" / f"{a.out}_cam01_crown.jpg")


if __name__ == "__main__":
    main()
