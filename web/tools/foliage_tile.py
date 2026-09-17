#!/usr/bin/env python3
"""100 % tiles for the 6c foliage judgement: the SAME box, side by side, at full resolution.

    python3 web/tools/foliage_tile.py --tag round16b

Two sheets, both written full-res to renders/web/tiles/<tag>/ (gitignored) and at 960 px to
renders/web/960/ (committed, the CLAUDE.md image rule):

  <tag>_cam02_tree_tile   the Cycles reference, the previous round and this one, over the box the
                          user's close-up is about (`700 660 1240 950`, the far tree that fills the
                          middle of cam02) - the tile the round-1 notes called "an 85 px atlas frame
                          magnified into a blue-green blob".
  <tag>_walkin_tile       the two walk-in headings at 3 m from that same tree, cropped to the crown.

A tile is never downscaled before it is judged: each panel is a 1:1 crop, and the 960 px copy exists
only so the sheet can be committed and linked.  Panels are labelled in the alpha-free top-left corner
by a 2 px rule, not by text, so nothing is drawn over the pixels being judged.
"""
import argparse
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
WEB = ROOT / "renders" / "web"
MAIN = Path("/Users/dk/Projects/3d render blender 3rd attempt building")
REF_CAM02 = MAIN / "renders/previews/qa/round13_02_lagoon_ne_threequarter_cycles.png"
TREE_BOX = (700, 660, 1240, 950)


def crop(path, box, at=(1920, 1080)):
    if not Path(path).exists():
        return None
    im = Image.open(path).convert("RGB")
    if im.size != at:
        im = im.resize(at, Image.LANCZOS)
    return im.crop(box)


def sheet(panels, out, gap=8):
    panels = [p for p in panels if p is not None]
    if not panels:
        return None
    h = max(p.height for p in panels)
    w = sum(p.width for p in panels) + gap * (len(panels) - 1)
    im = Image.new("RGB", (w, h), (24, 26, 30))
    x = 0
    for p in panels:
        im.paste(p, (x, 0))
        x += p.width + gap
    out.parent.mkdir(parents=True, exist_ok=True)
    im.save(out)
    return im


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="round16b")
    ap.add_argument("--prev", default="round16")
    a = ap.parse_args()
    tiles = WEB / "tiles" / a.tag
    small = WEB / "960"
    small.mkdir(parents=True, exist_ok=True)

    made = []
    s = sheet([crop(REF_CAM02, TREE_BOX),
               crop(WEB / f"{a.prev}_cam02.png", TREE_BOX),
               crop(WEB / f"{a.tag}_cam02.png", TREE_BOX)],
              tiles / f"{a.tag}_cam02_tree_tile.png")
    if s:
        made.append((f"{a.tag}_cam02_tree_tile", s))

    walk = sorted(WEB.glob(f"{a.tag}_walkin*_h*.png"))
    if walk:
        panels = []
        for p in walk[:2]:
            im = Image.open(p).convert("RGB")
            w, h = im.size
            panels.append(im.crop((w // 2 - 480, h // 2 - 300, w // 2 + 480, h // 2 + 300)))
        s = sheet(panels, tiles / f"{a.tag}_walkin_tile.png")
        if s:
            made.append((f"{a.tag}_walkin_tile", s))

    for name, im in made:
        c = im.copy()
        c.thumbnail((960, 10000), Image.LANCZOS)
        c.save(small / f"{name}.jpg", quality=88)
        print(f"{name}: {im.width}x{im.height} full-res -> {tiles}, 960 px -> {small}")
    if not made:
        print("foliage_tile.py: nothing to tile (no cam02 / walk-in frames for this tag)")


if __name__ == "__main__":
    main()
