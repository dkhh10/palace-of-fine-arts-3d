#!/usr/bin/env python3
"""QA-14-1 item 1b: the open-water tile the lead judges, viewer beside the Phase 5 hero.

    python3 web/tools/water_tile.py VIEWER.png [--ref REF.png] [--out OUT.png]

Both panels are cut at 100 % (no resampling) from the SAME 960 x 160 window inside the
`open water` probe crop (300 900 1600 1060), centred on it, and stacked with labels, so the
composite is 960 px wide as the image rule requires while every pixel shown is a real pixel.
The full-resolution 1300 x 160 crops are also written next to --out under tiles/ (gitignored).
"""
import argparse, os
from pathlib import Path
from PIL import Image, ImageDraw

MAIN = Path(os.environ.get("PFA_MAIN_ROOT") or "/Users/dk/Projects/3d render blender 3rd attempt building")
DEFAULT_REF = MAIN / "renders/previews/qa/round10b_01_lagoon_hero_cycles.png"
AT = (1920, 1080)
BOX = (300, 900, 1600, 1060)            # the water_probe.py `open water` crop
WIN = (470, 900, 1430, 1060)            # 960 x 160 of it, centred, shown at 100 %
BAR = 26


def load(p):
    im = Image.open(p).convert("RGB")
    return im if im.size == AT else im.resize(AT, Image.LANCZOS)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("viewer")
    ap.add_argument("--ref", default=str(DEFAULT_REF))
    ap.add_argument("--out", default="renders/web/960/qa14_1_openwater_100pct.png")
    a = ap.parse_args()
    panels = [("VIEWER  " + Path(a.viewer).stem, load(a.viewer)),
              ("PHASE 5 CYCLES HERO  " + Path(a.ref).stem, load(a.ref))]
    w, h = WIN[2] - WIN[0], WIN[3] - WIN[1]
    out = Image.new("RGB", (w, (h + BAR) * len(panels)), (16, 16, 16))
    d = ImageDraw.Draw(out)
    tiles = Path(a.out).parent.parent / "tiles" / "round15"
    tiles.mkdir(parents=True, exist_ok=True)
    for i, (label, im) in enumerate(panels):
        y = i * (h + BAR)
        d.text((6, y + 7), f"{label}   100 % crop x{WIN[0]}-{WIN[2]} y{WIN[1]}-{WIN[3]}", fill=(235, 235, 235))
        out.paste(im.crop(WIN), (0, y + BAR))
        im.crop(BOX).save(tiles / f"openwater_{'viewer' if i == 0 else 'cycles'}.png")
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    out.save(a.out)
    print(f"[water_tile] {a.out}  {out.size[0]}x{out.size[1]} (both panels 100 %)")
    print(f"[water_tile] full {BOX[2]-BOX[0]}x{BOX[3]-BOX[1]} crops -> {tiles}")


if __name__ == "__main__":
    main()
