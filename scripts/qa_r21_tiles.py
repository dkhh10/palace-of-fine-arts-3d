#!/usr/bin/env python3
"""QA round 21 tile cutter: the full-resolution tile review and the round's comparison sheets.

No Blender, no Chrome. Writes into --out (a scratch dir by default); the only repo file it writes is
the 960 px gate composite (`gate`).

    python3 scripts/qa_r21_tiles.py stations --out DIR  # 6 x (3x2) 100 % tiles per station
    python3 scripts/qa_r21_tiles.py crown3   --out DIR  # Cycles | gate8 (2K) | gate9 (band), 100 %
    python3 scripts/qa_r21_tiles.py sky      --out DIR  # every far crown against the sky, 100 %
    python3 scripts/qa_r21_tiles.py zoom     --out DIR  # 200 % crown crops (the dot-grid check)
    python3 scripts/qa_r21_tiles.py willow   --out DIR  # the hero willow bodies, 100 % and 200 %
    python3 scripts/qa_r21_tiles.py gate --gate renders/web/gate9_gate.png
"""
import argparse
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import qa_r21_probe as Q  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "renders" / "web"
REF = {
    1: ROOT / "renders/previews/qa/round10b_01_lagoon_hero_cycles.png",
    2: ROOT / "renders/previews/qa/round13_02_lagoon_ne_threequarter_cycles.png",
    3: ROOT / "renders/previews/qa/round13_03_colonnade_walk_cycles.png",
    4: ROOT / "renders/previews/qa/round13_04_rotunda_ceiling_cycles.png",
    5: ROOT / "renders/previews/qa/round13_05_south_lawn_cycles.png",
    6: ROOT / "renders/previews/qa/round13_06_aerial_cycles.png",
}
SIZE = (1920, 1080)
CUR, PREV = Q.CUR, Q.PREV

# The station-2 crown the band was bought for (the QA-17 / diag_ref fill-tree box), plus the crown
# tiles the QA-20 tile pass flagged for the ordered dot grid.
CROWN3 = [("02_fill_crown", 2, (700, 620, 1260, 980)),
          ("01_hero_crown", 1, (740, 520, 1020, 700)),
          ("05_lawn_crown", 5, (280, 560, 520, 880))]
ZOOMS = [("01_hero_crown_200", 1, (800, 556, 960, 660)),
         ("02_fill_crown_200", 2, (820, 700, 1060, 850)),
         ("05_left_crown_200", 5, (0, 480, 200, 620))]
WILLOWS = [("01_willow_shore_C", 1, (800, 535, 975, 710)),
           ("01_willow_shore_W", 1, (640, 535, 815, 710))]


def _open(p):
    im = Image.open(p).convert("RGB")
    return im if im.size == SIZE else im.resize(SIZE, Image.LANCZOS)


def _label(im, text):
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, 7 * len(text) + 10, 18], fill=(0, 0, 0))
    d.text((5, 4), text, fill=(255, 255, 0))
    return im


def _row(cells, title=None, pad=6):
    h = max(c.height for c in cells)
    w = sum(c.width for c in cells) + pad * (len(cells) - 1)
    top = 18 if title else 0
    band = Image.new("RGB", (w, h + top), (16, 16, 16))
    x = 0
    for c in cells:
        band.paste(c, (x, top))
        x += c.width + pad
    if title:
        ImageDraw.Draw(band).text((6, 4), title, fill=(255, 220, 90))
    return band


def _three(st, box, zoom=1, order=("cycles", PREV, CUR)):
    src = {"cycles": REF[st], PREV: WEB / f"{PREV}_cam{st:02d}.png", CUR: WEB / f"{CUR}_cam{st:02d}.png"}
    lbl = {"cycles": "Cycles", PREV: f"{PREV} (2K oct, share .15)", CUR: f"{CUR} (band, share .10)"}
    out = []
    for k in order:
        c = _open(src[k]).crop(box)
        if zoom > 1:
            c = c.resize((c.width * zoom, c.height * zoom), Image.NEAREST)
        out.append(_label(c, lbl[k]))
    return out


def cmd_stations(out):
    for st in range(1, 7):
        a = _open(WEB / f"{CUR}_cam{st:02d}.png")
        for r in range(2):
            for c in range(3):
                a.crop((c * 640, r * 540, (c + 1) * 640, (r + 1) * 540)).save(
                    out / f"{CUR}_cam{st:02d}_r{r + 1}c{c + 1}.png")
    print(f"36 tiles -> {out}")


def cmd_crown3(out):
    for name, st, box in CROWN3:
        _row(_three(st, box), f"{name}: Cycles | {PREV} 2K | {CUR} band, 100 %").save(
            out / f"crown3_{name}.png")
    print(f"{len(CROWN3)} three-way strips -> {out}")


def cmd_sky(out):
    for name, st, box, why in Q.SKY_CROWNS:
        tag = name.replace(" ", "_")
        _row(_three(st, box), f"{name} ({why}), 100 %").save(out / f"sky_{tag}.png")
    print(f"{len(Q.SKY_CROWNS)} sky-crown strips -> {out}")


def cmd_zoom(out):
    for name, st, box in ZOOMS:
        _row(_three(st, box, zoom=2), f"{name}: Cycles | {PREV} | {CUR}, 200 %").save(
            out / f"zoom_{name}.png")
    print(f"{len(ZOOMS)} zooms -> {out}")


def cmd_willow(out):
    for name, st, box in WILLOWS:
        _row(_three(st, box), f"{name}, 100 %").save(out / f"willow_{name}.png")
        _row(_three(st, box, zoom=2), f"{name}, 200 %").save(out / f"willow_{name}_200.png")
    print(f"{2 * len(WILLOWS)} willow strips -> {out}")


def cmd_gate(dest):
    """The 960 px round composite the brief asks for: the station-2 three-way crown strip, the hero
    crown at 200 %, one willow body."""
    rows = [
        ("A  8b station-2 crown at 100 % — Cycles | gate8 (2K, share .15) | gate9 (band, share .10)",
         _row(_three(2, (760, 640, 1120, 950)))),
        ("B  the hero crown at 200 % — the QA-20 ordered dot grid check",
         _row(_three(1, (812, 556, 940, 650), zoom=2))),
        ("C  a hero-shore willow body at 200 % — the band's 1.6 % clipped texels",
         _row(_three(1, (660, 552, 800, 660), zoom=2))),
    ]
    panels = []
    for title, band in rows:
        p = Image.new("RGB", (band.width, band.height + 18), (16, 16, 16))
        p.paste(band, (0, 18))
        ImageDraw.Draw(p).text((6, 4), title, fill=(255, 220, 90))
        panels.append(p)
    scaled = [p.resize((960, max(1, round(p.height * 960 / p.width))), Image.LANCZOS) for p in panels]
    sheet = Image.new("RGB", (960, sum(s.height for s in scaled) + 8 * (len(scaled) - 1)), (10, 10, 10))
    y = 0
    for s in scaled:
        sheet.paste(s, (0, y))
        y += s.height + 8
    Path(dest).parent.mkdir(parents=True, exist_ok=True)
    sheet.save(dest)
    print(f"-> {dest} {sheet.size}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", nargs="+")
    ap.add_argument("--out", default="/tmp/qa_r21")
    ap.add_argument("--gate", default=str(WEB / f"{CUR}_gate.png"))
    a = ap.parse_args()
    outd = Path(a.out)
    outd.mkdir(parents=True, exist_ok=True)
    for c in a.cmd:
        if c == "gate":
            cmd_gate(a.gate)
        else:
            {"stations": cmd_stations, "crown3": cmd_crown3, "sky": cmd_sky, "zoom": cmd_zoom,
             "willow": cmd_willow}[c](outd)
