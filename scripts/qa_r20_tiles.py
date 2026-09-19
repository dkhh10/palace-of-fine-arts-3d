#!/usr/bin/env python3
"""QA round 20 tile cutter: the full-resolution tile review and the round's comparison strips.

No Blender, no Chrome. Writes into --out (a scratch dir by default; nothing in the repo but the
960 px gate composite, which `gate` writes).

    python3 scripts/qa_r20_tiles.py stations --out DIR   # 6 x (3x2) 100 % tiles per station
    python3 scripts/qa_r20_tiles.py strips   --out DIR   # gate7 | gate8 | reference, 100 %, per box
    python3 scripts/qa_r20_tiles.py zoom     --out DIR    # 200 % crown crops (the halftone check)
    python3 scripts/qa_r20_tiles.py gate --gate renders/web/gate8_gate.png
"""
import argparse
import sys
from pathlib import Path

from PIL import Image, ImageDraw

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

# (label, station, box) — the round's comparison strips, all QA-17 boxes plus the 8c columns.
STRIPS = [
    ("shrub_01_shore", 1, (0, 600, 660, 720)),
    ("shrub_01_shoreS", 1, (1260, 580, 1900, 700)),
    ("shrub_02_shore", 2, (40, 840, 660, 1070)),
    ("shrub_02_reedSE", 2, (1360, 860, 1870, 1075)),
    ("shrub_05_shore", 5, (200, 820, 1200, 940)),
    ("shrub_05_W", 5, (1300, 690, 1900, 910)),
    ("shrub_03_cards", 3, (840, 600, 1290, 760)),
    ("crown_01_hero", 1, (740, 530, 1010, 700)),
    ("crown_02_fill", 2, (690, 650, 1250, 960)),
    ("crown_05_lawn", 5, (290, 570, 510, 880)),
    ("col_03_nearR", 3, (1390, 170, 1810, 850)),
    ("col_03_nearL", 3, (500, 210, 800, 730)),
]
ZOOMS = [("crown_01_hero_200", 1, (800, 560, 960, 660)),
         ("crown_02_fill_200", 2, (820, 700, 1060, 850))]


def _open(p):
    im = Image.open(p).convert("RGB")
    return im if im.size == SIZE else im.resize(SIZE, Image.LANCZOS)


def _label(im, text):
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, 9 * len(text) + 10, 20], fill=(0, 0, 0))
    d.text((5, 5), text, fill=(255, 255, 0))
    return im


def cmd_stations(out, tag):
    for st in range(1, 7):
        a = _open(WEB / f"{tag}_cam{st:02d}.png")
        for r in range(2):
            for c in range(3):
                box = (c * 640, r * 540, (c + 1) * 640, (r + 1) * 540)
                a.crop(box).save(out / f"{tag}_cam{st:02d}_r{r + 1}c{c + 1}.png")
    print(f"36 tiles -> {out}")


def cmd_strips(out, tag, prev):
    for name, st, box in STRIPS:
        ims = []
        for lbl, src in ((prev, WEB / f"{prev}_cam{st:02d}.png"),
                         (tag, WEB / f"{tag}_cam{st:02d}.png"), ("reference", REF[st])):
            ims.append(_label(_open(src).crop(box), lbl))
        w = sum(i.width for i in ims) + 2 * 8
        sheet = Image.new("RGB", (w, ims[0].height), (20, 20, 20))
        x = 0
        for i in ims:
            sheet.paste(i, (x, 0))
            x += i.width + 8
        sheet.save(out / f"strip_{name}.png")
    print(f"{len(STRIPS)} strips -> {out}")


def cmd_zoom(out, tag, prev):
    for name, st, box in ZOOMS:
        ims = []
        for lbl, src in ((prev, WEB / f"{prev}_cam{st:02d}.png"),
                         (tag, WEB / f"{tag}_cam{st:02d}.png"), ("reference", REF[st])):
            c = _open(src).crop(box)
            ims.append(_label(c.resize((c.width * 2, c.height * 2), Image.NEAREST), lbl))
        w = sum(i.width for i in ims) + 2 * 8
        sheet = Image.new("RGB", (w, ims[0].height), (20, 20, 20))
        x = 0
        for i in ims:
            sheet.paste(i, (x, 0))
            x += i.width + 8
        sheet.save(out / f"zoom_{name}.png")
    print(f"{len(ZOOMS)} zooms -> {out}")


def cmd_gate(out, tag, prev, dest):
    """The 960 px round composite: three rows — 8a shrub band, 8b crowns, 8c column.

    Each row is three ~314 px panels (before | after | reference) so the sheet is close to 1:1 at
    960 px and the dither, the tufting and the shaft grain survive the downscale.
    """
    rows = [
        ("A  8a shrub band, cam01 shore at 2x — gate7 | gate8 | Cycles reference",
         1, (100, 628, 257, 702), 2),
        ("B  8b far-tree crown, cam01 hero shore crown at 2x — gate7 | gate8 | Cycles reference",
         1, (800, 556, 957, 660), 2),
        ("C  8c near column, cam03 right shaft at 1:1 — gate7 | gate8 | Cycles reference",
         3, (1430, 230, 1744, 500), 1),
    ]
    panels = []
    for title, st, box, z in rows:
        cells = []
        for lbl, src in ((prev, WEB / f"{prev}_cam{st:02d}.png"),
                         (tag, WEB / f"{tag}_cam{st:02d}.png"), ("reference", REF[st])):
            c = _open(src).crop(box)
            if z > 1:
                c = c.resize((c.width * z, c.height * z), Image.NEAREST)
            cells.append(_label(c, lbl))
        h = max(c.height for c in cells)
        w = sum(c.width for c in cells) + 4 * (len(cells) - 1)
        band = Image.new("RGB", (w, h + 20), (16, 16, 16))
        x = 0
        for c in cells:
            band.paste(c, (x, 20))
            x += c.width + 4
        ImageDraw.Draw(band).text((6, 4), title, fill=(255, 220, 90))
        panels.append(band)
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
    ap.add_argument("--out", default="/tmp/qa_r20")
    ap.add_argument("--tag", default="gate8")
    ap.add_argument("--prev", default="gate7")
    ap.add_argument("--gate", default=str(WEB / "gate8_gate.png"))
    a = ap.parse_args()
    outd = Path(a.out)
    outd.mkdir(parents=True, exist_ok=True)
    for c in a.cmd:
        if c == "stations":
            cmd_stations(outd, a.tag)
        elif c == "strips":
            cmd_strips(outd, a.tag, a.prev)
        elif c == "zoom":
            cmd_zoom(outd, a.tag, a.prev)
        elif c == "gate":
            cmd_gate(outd, a.tag, a.prev, a.gate)
        else:
            sys.exit(f"unknown: {c}")
