#!/usr/bin/env python3
"""Phase 8a — the 100 % shore-band tiles: Cycles | cardsun 0 | the relit capture.

    python3 web/tools/p8a_tiles.py --relit p8a_v30 [--base p8a_cs0] [--out renders/web/tiles/p8a]

One composite per station (1, 3, 5), each a vertical stack of three 1:1 crops of the SAME box in the
same order, separated by a 3 px rule (no text over the judged pixels: the order is fixed and stated
here).  Full resolution into renders/web/tiles/ (gitignored) and one 960 px JPEG contact sheet into
renders/web/ for the report.
"""
import argparse
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parents[2]
MAIN = Path("/Users/dk/Projects/3d render blender 3rd attempt building")
WEB = HERE / "renders" / "web"
REF = {   # the QA reference set (qa_r13_probe.REF_R14): the Phase 5 Cycles frames
    1: MAIN / "renders/previews/qa/round10b_01_lagoon_hero_cycles.png",
    3: MAIN / "renders/previews/qa/round13_03_colonnade_walk_cycles.png",
    5: MAIN / "renders/previews/qa/round13_05_south_lawn_cycles.png",
}
BOX = {                      # the QA-17 shrub boxes, widened a little vertically to show the band
    1: (0, 595, 640, 700),
    3: (860, 610, 1280, 755),
    5: (200, 830, 1200, 935),
}


def crop(path, box):
    im = Image.open(path).convert("RGB")
    if im.size != (1920, 1080):
        im = im.resize((1920, 1080), Image.LANCZOS)
    return im.crop(box)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--relit", required=True)
    ap.add_argument("--base", default="p8a_cs0")
    ap.add_argument("--out", default=str(WEB / "tiles" / "p8a"))
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    sheets = []
    for st, box in BOX.items():
        panels = [crop(REF[st], box),
                  crop(WEB / f"{a.base}_cam{st:02d}.png", box),
                  crop(WEB / f"{a.relit}_cam{st:02d}.png", box)]
        w = max(p.width for p in panels)
        h = sum(p.height for p in panels) + 3 * (len(panels) - 1)
        sheet = Image.new("RGB", (w, h), (255, 0, 255))
        y = 0
        for p in panels:
            sheet.paste(p, (0, y))
            y += p.height + 3
        f = out / f"p8a_tile_cam{st:02d}_{a.relit}.png"
        sheet.save(f)
        print(f"wrote {f} ({sheet.width}x{sheet.height}) — Cycles / {a.base} / {a.relit}")
        sheets.append(sheet)
    w = max(s.width for s in sheets)
    h = sum(s.height for s in sheets) + 8 * (len(sheets) - 1)
    all_ = Image.new("RGB", (w, h), (0, 255, 255))
    y = 0
    for s in sheets:
        all_.paste(s, (0, y))
        y += s.height + 8
    f = out / f"p8a_tiles_{a.relit}.png"
    all_.save(f)
    print(f"wrote {f} ({all_.width}x{all_.height})")


if __name__ == "__main__":
    main()
