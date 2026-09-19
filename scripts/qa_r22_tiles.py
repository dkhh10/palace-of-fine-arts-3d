#!/usr/bin/env python3
"""QA round 22 tile / composite builder (no Blender, no Chrome).

    python3 scripts/qa_r22_tiles.py tiles    # the 100 % strips the critic views one by one (/tmp)
    python3 scripts/qa_r22_tiles.py hero     # the six full-resolution hero tiles (the gate rule)
    python3 scripts/qa_r22_tiles.py gate     # renders/web/gate10_gate.png, the 960 px round sheet

Strips are cut at 100 % from the delivered PNGs; nothing is resampled except the final 960 px sheet.
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "renders" / "web"
REF169 = ROOT / "reference/photos/raw/ref_169_main_Palace_of_Fine_Arts_16794p.jpg"
REF105 = ROOT / "reference/photos/raw/ref_105_main_Aerial_view_of_The_Palace_of_Fine_Arts.jpg"
CUR, PREV = "gate10", "gate9"
OUT = Path("/tmp")

# the Phase 5 Cycles frames the probe uses as the reference (qa_r13_probe.REF_R14)
CYCLES = {
    1: ROOT / "renders/previews/qa/round10b_01_lagoon_hero_cycles.png",
    3: ROOT / "renders/previews/qa/round13_03_colonnade_walk_cycles.png",
    5: ROOT / "renders/previews/qa/round13_05_south_lawn_cycles.png",
    6: ROOT / "renders/previews/qa/round13_06_aerial_cycles.png",
}

# 8a / 8a-3: the shore band at stations 1, 3, 5 (the QA-17 shrub boxes, widened to a strip)
SHORE = [
    ("01 shore band", 1, (0, 590, 640, 700)),
    ("03 shrub cards", 3, (820, 600, 1300, 760)),
    ("05 shore band", 5, (200, 820, 1200, 940)),
]
# 8d: the hero backdrop band and the cam06 city
HERO_BAND_N = (0, 524, 640, 670)
HERO_BAND_S = (1280, 524, 1900, 670)
CAM06_CITY = (1280, 0, 1920, 400)
# cam-01 render px -> raw ref-169 px (scripts/env_r8_fit.py REF_XF)
REF_XF = (0.7640, 223.2, 0.7667, 97.0)
# 8e: the mobile close-orbit crowns (qa_r22_probe.BLADE_BOXES)
ORBIT = [("h253 crown R", "h02530", (700, 634, 1080, 944)),
         ("h215 crown L", "h02150", (158, 1056, 607, 1478))]


def _im(p):
    return Image.open(str(p)).convert("RGB")


def _label(canvas, x, y, text):
    ImageDraw.Draw(canvas).text((x + 4, y - 14), text, fill=(255, 255, 255))


def _stack(rows, pad=16, bg=(18, 18, 18)):
    w = max(im.width for im, _ in rows)
    h = sum(im.height + pad for im, _ in rows) + 4
    out = Image.new("RGB", (w, h), bg)
    y = 16
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


def cmd_tiles():
    for name, st, box in SHORE:
        rows = []
        if st in CYCLES and CYCLES[st].exists():
            rows.append((_im(CYCLES[st]).crop(box), f"CYCLES  {name}"))
        rows.append((_im(WEB / f"{PREV}_cam{st:02d}.png").crop(box), f"{PREV}  {name}"))
        rows.append((_im(WEB / f"{CUR}_cam{st:02d}.png").crop(box), f"{CUR}  {name}"))
        p = OUT / f"r22_shore_{st:02d}.png"
        _stack(rows).save(p)
        print(p)
    for tag, box in (("bandN", HERO_BAND_N), ("bandS", HERO_BAND_S)):
        rows = [(_im(WEB / f"{PREV}_cam01.png").crop(box), f"{PREV} hero {tag}"),
                (_im(WEB / f"{CUR}_cam01.png").crop(box), f"{CUR} hero {tag}"),
                (_ref169(box), f"ref 169 (registered) {tag}")]
        p = OUT / f"r22_hero_{tag}.png"
        _stack(rows).save(p)
        print(p)
    rows = [(_im(WEB / f"{PREV}_cam06.png").crop(CAM06_CITY), f"{PREV} cam06 city"),
            (_im(WEB / f"{CUR}_cam06.png").crop(CAM06_CITY), f"{CUR} cam06 city"),
            (_im(REF105).crop(CAM06_CITY), "ref 105 (same px, unregistered)")]
    p = OUT / "r22_city.png"
    _stack(rows).save(p)
    print(p)
    for name, head, box in ORBIT:
        rows = [(_im(WEB / f"gate7_orbit_{head}.png").crop(box), f"gate7_orbit {name}"),
                (_im(WEB / f"{CUR}_orbit_{head}.png").crop(box), f"{CUR}_orbit {name}")]
        p = OUT / f"r22_orbit_{head}.png"
        _stack(rows).save(p)
        print(p)


def cmd_hero():
    im = _im(WEB / f"{CUR}_cam01.png")
    for r in range(2):
        for c in range(3):
            p = OUT / f"r22_hero_r{r + 1}c{c + 1}.png"
            im.crop((c * 640, r * 540, (c + 1) * 640, (r + 1) * 540)).save(p)
            print(p)


def cmd_gate():
    """The round sheet: the cam05 shore band (Cycles | gate9 | gate10), the hero N band
    (gate9 | gate10 | ref 169), the cam06 city (gate9 | gate10 | ref 105) and one orbit crown
    (gate7 | gate10).  Downscaled to 960 px wide as the image rule requires."""
    panels = []
    name, st, box = SHORE[2]
    panels.append(_stack([(_im(CYCLES[st]).crop(box), "CYCLES cam05 shore band"),
                          (_im(WEB / f"{PREV}_cam{st:02d}.png").crop(box), f"{PREV}"),
                          (_im(WEB / f"{CUR}_cam{st:02d}.png").crop(box), f"{CUR}  (8a + 8a-3)")]))
    panels.append(_stack([(_im(WEB / f"{PREV}_cam01.png").crop(HERO_BAND_N), f"{PREV} hero N band"),
                          (_im(WEB / f"{CUR}_cam01.png").crop(HERO_BAND_N), f"{CUR}  (8d)"),
                          (_ref169(HERO_BAND_N), "ref 169 registered")]))
    panels.append(_stack([(_im(WEB / f"{PREV}_cam06.png").crop(CAM06_CITY), f"{PREV} cam06 city"),
                          (_im(WEB / f"{CUR}_cam06.png").crop(CAM06_CITY), f"{CUR}  (8d)"),
                          (_im(REF105).crop(CAM06_CITY), "ref 105")]))
    name, head, box = ORBIT[0]
    panels.append(_stack([(_im(WEB / f"gate7_orbit_{head}.png").crop(box), f"gate7_orbit {name}"),
                          (_im(WEB / f"{CUR}_orbit_{head}.png").crop(box), f"{CUR}_orbit  (8e)")]))
    h = max(p.height for p in panels)
    panels = [p if p.height == h else
              p.resize((max(1, round(p.width * h / p.height)), h), Image.LANCZOS) for p in panels]
    w = sum(p.width for p in panels) + 12 * (len(panels) - 1)
    sheet = Image.new("RGB", (w, h), (18, 18, 18))
    x = 0
    for p in panels:
        sheet.paste(p, (x, 0))
        x += p.width + 12
    sheet = sheet.resize((960, max(1, round(960 * h / w))), Image.LANCZOS)
    out = WEB / f"{CUR}_gate.png"
    sheet.save(out)
    print(out, sheet.size)


if __name__ == "__main__":
    for a in (sys.argv[1:] or ["tiles"]):
        {"tiles": cmd_tiles, "hero": cmd_hero, "gate": cmd_gate}[a]()
