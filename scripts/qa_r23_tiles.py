#!/usr/bin/env python3
"""QA round 23 tile / composite builder (no Blender, no Chrome).

    python3 scripts/qa_r23_tiles.py belt     # the 100 % belt strips at 1 / 2 / 5 + the reflection
    python3 scripts/qa_r23_tiles.py hero     # the six full-resolution hero tiles (the gate rule)
    python3 scripts/qa_r23_tiles.py shore    # the 8a shore band at 1 / 3 / 5 (regression only)
    python3 scripts/qa_r23_tiles.py walk     # 8e: the 2.5 m walk-up pair + the close orbit crown
    python3 scripts/qa_r23_tiles.py grid     # a labelled 960 px grid over a station (box picking)
    python3 scripts/qa_r23_tiles.py gate     # renders/web/gate11_gate.png, the 960 px round sheet

Strips are cut at 100 % from the delivered PNGs.  The Phase 8 Cycles references only survive at
960 px (`renders/qa_comparisons/cycles_p8/960/cam0N_960.jpg`; the full-resolution PNGs are
gitignored and the phase8d-env worktree is gone), so where a Cycles row appears in a 100 % strip it
is upscaled 2x from that JPEG and is a COLOUR / SILHOUETTE reference only, never a sharpness one.
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "renders" / "web"
REF169 = ROOT / "reference/photos/raw/ref_169_main_Palace_of_Fine_Arts_16794p.jpg"
REF105 = ROOT / "reference/photos/raw/ref_105_main_Aerial_view_of_The_Palace_of_Fine_Arts.jpg"
P8 = ROOT / "renders/qa_comparisons/cycles_p8/960"
CUR, PREV = "gate11", "gate10"
OUT = Path("/tmp")

# the Phase 5 Cycles frames the earlier rounds used (qa_r13_probe REF)
CYCLES5 = {
    1: ROOT / "renders/previews/qa/round10b_01_lagoon_hero_cycles.png",
    3: ROOT / "renders/previews/qa/round13_03_colonnade_walk_cycles.png",
    5: ROOT / "renders/previews/qa/round13_05_south_lawn_cycles.png",
    6: ROOT / "renders/previews/qa/round13_06_aerial_cycles.png",
}

# 8d r2: where the hall-east belt is drawn.  The three bands the QA-22 blocker named, plus the
# lagoon reflection of the hero band (the belt is reflected, so a shard shows twice).
BELT = [
    ("01 belt N (r2c1)", 1, (0, 500, 640, 680)),
    ("01 belt S", 1, (1280, 500, 1900, 680)),
    ("01 belt reflection", 1, (0, 700, 900, 860)),
    ("02 belt band", 2, (0, 380, 960, 700)),
    ("05 belt band", 5, (0, 620, 1920, 800)),
]
CAM06_CITY = (1280, 60, 1920, 300)
SHORE = [
    ("01 shore band", 1, (0, 590, 640, 700)),
    ("03 shrub cards", 3, (820, 600, 1300, 760)),
    ("05 shore band", 5, (200, 820, 1200, 940)),
]
ORBIT = [("h253 crown R", "h02530", (700, 634, 1080, 944)),
         ("h215 crown L", "h02150", (158, 1056, 607, 1478))]
WALKUP = [("walk-up h000", "h00000"), ("walk-up h090", "h00900")]
REF_XF = (0.7640, 223.2, 0.7667, 97.0)


def _im(p):
    return Image.open(str(p)).convert("RGB")


def _p8(st, box=None):
    """The Phase 8 Cycles reference, upscaled 2x to the delivered frame's pixel grid."""
    im = _im(P8 / f"cam{st:02d}_960.jpg").resize((1920, 1080), Image.LANCZOS)
    return im.crop(box) if box else im


def _label(canvas, x, y, text):
    ImageDraw.Draw(canvas).text((x + 4, y - 14), text, fill=(255, 255, 255))


def _stack(rows, pad=18, bg=(18, 18, 18)):
    w = max(im.width for im, _ in rows)
    h = sum(im.height + pad for im, _ in rows) + 6
    out = Image.new("RGB", (w, h), bg)
    y = 18
    for im, lab in rows:
        out.paste(im, (0, y))
        _label(out, 0, y, lab)
        y += im.height + pad
    return out


def _ref169(box):
    sx, dx, sy, dy = REF_XF
    x0, y0, x1, y1 = box
    return _im(REF169).crop((int(x0 * sx + dx), int(y0 * sy + dy),
                             int(x1 * sx + dx), int(y1 * sy + dy))).resize(
        (x1 - x0, y1 - y0), Image.LANCZOS)


def cmd_belt():
    for i, (name, st, box) in enumerate(BELT):
        rows = [(_im(WEB / f"{PREV}_cam{st:02d}.png").crop(box), f"{PREV} (r1 shards)  {name}"),
                (_im(WEB / f"{CUR}_cam{st:02d}.png").crop(box), f"{CUR} (belt r2)  {name}"),
                (_p8(st, box), f"CYCLES Phase 8 (960 px upscaled)  {name}")]
        if st == 1 and "reflection" not in name:
            rows.append((_ref169(box), f"ref 169 registered  {name}"))
        p = OUT / f"r23_belt_{i}_cam{st:02d}.png"
        _stack(rows).save(p)
        print(p)
    rows = [(_im(WEB / f"{PREV}_cam06.png").crop(CAM06_CITY), f"{PREV} cam06 city"),
            (_im(WEB / f"{CUR}_cam06.png").crop(CAM06_CITY), f"{CUR} cam06 city"),
            (_p8(6, CAM06_CITY), "CYCLES Phase 8"),
            (_im(REF105).crop(CAM06_CITY), "ref 105")]
    p = OUT / "r23_city.png"
    _stack(rows).save(p)
    print(p)


def cmd_hero():
    im = _im(WEB / f"{CUR}_cam01.png")
    for r in range(2):
        for c in range(3):
            p = OUT / f"r23_hero_r{r + 1}c{c + 1}.png"
            im.crop((c * 640, r * 540, (c + 1) * 640, (r + 1) * 540)).save(p)
            print(p)


def cmd_shore():
    for name, st, box in SHORE:
        rows = [(_im(WEB / f"{PREV}_cam{st:02d}.png").crop(box), f"{PREV}  {name}"),
                (_im(WEB / f"{CUR}_cam{st:02d}.png").crop(box), f"{CUR}  {name}"),
                (_p8(st, box), f"CYCLES Phase 8  {name}")]
        p = OUT / f"r23_shore_{st:02d}.png"
        _stack(rows).save(p)
        print(p)


def cmd_walk():
    rows = []
    for name, head in WALKUP:
        im = _im(WEB / f"{CUR}_walkup_{head}.png")
        w, h = im.size
        rows.append((im.crop((0, h // 3, min(w, 1100), h // 3 + 900)), f"{CUR} {name}  ({w}x{h})"))
    _stack(rows).save(OUT / "r23_walkup.png")
    print(OUT / "r23_walkup.png")
    for name, head, box in ORBIT:
        rows = [(_im(WEB / f"{PREV}_orbit_{head}.png").crop(box), f"{PREV}_orbit {name}"),
                (_im(WEB / f"{CUR}_orbit_{head}.png").crop(box), f"{CUR}_orbit {name}")]
        p = OUT / f"r23_orbit_{head}.png"
        _stack(rows).save(p)
        print(p)


def cmd_grid():
    """A 960 px view of each station with a labelled 10 % grid, so boxes are picked, not guessed."""
    for st in (1, 2, 5):
        im = _im(WEB / f"{CUR}_cam{st:02d}.png").resize((960, 540), Image.LANCZOS)
        d = ImageDraw.Draw(im)
        for i in range(1, 10):
            d.line([(i * 96, 0), (i * 96, 540)], fill=(255, 0, 0), width=1)
            d.line([(0, i * 54), (960, i * 54)], fill=(255, 0, 0), width=1)
            d.text((i * 96 + 2, 2), str(i * 192), fill=(255, 255, 0))
            d.text((2, i * 54 + 2), str(i * 108), fill=(0, 255, 255))
        p = OUT / f"r23_grid_{st:02d}.jpg"
        im.save(p, quality=92)
        print(p)


def cmd_gate():
    """The round sheet: the hero N belt band (gate10 | gate11 | Cycles P8 | ref 169), the cam05
    belt band, the cam06 city, and the 2.5 m walk-up. 960 px wide as the image rule requires."""
    panels = []
    name, st, box = BELT[0]
    panels.append(_stack([(_im(WEB / f"{PREV}_cam01.png").crop(box), f"{PREV} hero belt N (r1)"),
                          (_im(WEB / f"{CUR}_cam01.png").crop(box), f"{CUR} hero belt N (r2)"),
                          (_p8(1, box), "CYCLES Phase 8"),
                          (_ref169(box), "ref 169 registered")]))
    box5 = (350, 600, 1000, 800)
    panels.append(_stack([(_im(WEB / f"{PREV}_cam05.png").crop(box5), f"{PREV} cam05 belt (shards)"),
                          (_im(WEB / f"{CUR}_cam05.png").crop(box5), f"{CUR} cam05 belt (r2)"),
                          (_p8(5, box5), "CYCLES Phase 8")]))
    panels.append(_stack([(_im(WEB / f"{PREV}_cam06.png").crop(CAM06_CITY), f"{PREV} cam06 city"),
                          (_im(WEB / f"{CUR}_cam06.png").crop(CAM06_CITY), f"{CUR} cam06 city"),
                          (_p8(6, CAM06_CITY), "CYCLES Phase 8"),
                          (_im(REF105).crop(CAM06_CITY), "ref 105")]))
    wu = _im(WEB / f"{CUR}_walkup_h00000.png")
    w, h = wu.size
    panels.append(_stack([(wu.crop((0, h // 3, min(w, 1100), h // 3 + 560)),
                           f"{CUR} 2.5 m walk-up (8e close cards)"),
                          (_im(WEB / f"{CUR}_orbit_h02530.png").crop(ORBIT[0][2]),
                           f"{CUR}_orbit crown")]))
    cw = 474
    panels = [p.resize((cw, max(1, round(p.height * cw / p.width))), Image.LANCZOS) for p in panels]
    rh = [max(panels[0].height, panels[1].height), max(panels[2].height, panels[3].height)]
    sheet = Image.new("RGB", (cw * 2 + 12, rh[0] + rh[1] + 12), (18, 18, 18))
    for i, p in enumerate(panels):
        sheet.paste(p, ((i % 2) * (cw + 12), 0 if i < 2 else rh[0] + 12))
    out = WEB / f"{CUR}_gate.png"
    sheet.save(out)
    print(out, sheet.size)


if __name__ == "__main__":
    for a in (sys.argv[1:] or ["belt"]):
        {"belt": cmd_belt, "hero": cmd_hero, "shore": cmd_shore, "walk": cmd_walk,
         "grid": cmd_grid, "gate": cmd_gate}[a]()
