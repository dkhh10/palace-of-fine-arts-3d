#!/usr/bin/env python3
"""The QA round 16 gate composite -> renders/web/round16b_gate.png (960 px).

    python3 scripts/qa_r16_gate.py        # no Blender, no Chrome

An extension of `scripts/qa_r13_gate.py` (imported for `fit` / `frame` / `strip`), unmodified.

Row 1-2  the six round16b stations (the 6c delivery look, every 6c default on, t=0).
Row 3    what 6c fixed: the station-2 fill tree at 100 %, round15 | round16b | Cycles.
Row 4    what 6c did not: the station-5 shore at 100 %, round15 | round16b | Cycles — flat-lit
         crowns over straw-pale shrub cards where the reference has dark, dense, species-distinct
         planting.
Row 5    the 3 m walk-in at station 2 at 100 % — the tile that decides "credible at 3 m".
Row 6    the hero's own left-shore planting at 100 %, round16b over Cycles — unmoved by 6c.
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import qa_r13_gate as G  # noqa: E402

R, VIEW, W = G.R, G.VIEW, G.W
BG, FG, HI, DIM, BAD = G.BG, G.FG, G.HI, G.DIM, G.BAD
GOOD = (150, 210, 140)
REF = {
    1: R / "renders/previews/qa/round10b_01_lagoon_hero_cycles.png",
    2: R / "renders/previews/qa/round13_02_lagoon_ne_threequarter_cycles.png",
    5: R / "renders/previews/qa/round13_05_south_lawn_cycles.png",
}


def ref(st):
    im = Image.open(REF[st]).convert("RGB")
    return im if im.size == (1920, 1080) else im.resize((1920, 1080), Image.LANCZOS)


def main():
    gap = 6
    tw = (W - 2 * gap) // 3
    thumbs = [G.fit(G.frame("round16b", st), tw) for st in range(1, 7)]
    th = thumbs[0].height

    b2 = (700, 660, 1240, 950)                       # the far tree that fills cam02
    row3 = G.strip([G.frame("round15", 2).crop(b2), G.frame("round16b", 2).crop(b2),
                    ref(2).crop(b2)], W)
    b5 = (200, 560, 740, 900)                        # the station-5 lawn tree and shore band
    row4 = G.strip([G.frame("round15", 5).crop(b5), G.frame("round16b", 5).crop(b5),
                    ref(5).crop(b5)], W)
    # The committed 3 m walk-in tile is two 964 px panels side by side; the left one is the tree.
    row5 = G.fit(Image.open(VIEW / "tiles/round16b/round16b_walkin_tile.png")
                 .convert("RGB").crop((0, 0, 964, 600)), W)
    b1 = (40, 612, 620, 700)                         # the hero's left shore planting
    hero = Image.new("RGB", (580, 182), BG)
    hero.paste(G.frame("round16b", 1).crop(b1), (0, 0))
    hero.paste(ref(1).crop(b1), (0, 94))
    row6 = G.fit(hero, W)

    lines = [
        ("QA round 16 — the Phase 6c foliage gate.  The stated acceptance PASSES: no station drops,", HI),
        ("station 2 rises +0.13, every frame time is within +3 ms of round 15 (hero +1.9).  The tiles", HI),
        ("say 6c's own goal — foliage credible at 3 m — is not met: ONE MORE ROUND (the brief allows two).", HI),
        ("Scores 3.72 / 3.13 / 2.56 / 2.88 / 2.94 / 2.83 vs round 15 +0.00 / +0.13 / 0 / 0 / 0 / 0.", FG),
        ("CLOSED: the blue impostor.  cam02 fill tree 1.41x -> 1.28x, hue 68.2 -> 54.3 (ref 45.5), sat", GOOD),
        ("0.100 -> 0.594 (ref 0.530); near trees G>R 37.4 -> 66.2 % (ref 70.9), hue 57.7 -> 70.8; the hero's", GOOD),
        ("far-tree roofline 1.12x -> 1.01x, hue 137.5 -> 75.3 (ref 76.9).  MAE 23.11 -> 20.48 at cam02.", GOOD),
        ("OPEN 1, the shrub/reed cards (export).  Frame-normalised level against Cycles: st1 1.70x,", BAD),
        ("st2 1.47x, st3 1.34x, st5 1.34x, with 2-8x the reference's hard-edge share.  The tinted albedo", BAD),
        ("fixed the hue (st2 G>R 4.2 -> 58.8 %) and pushed the level FURTHER out (st2 1.44x -> 1.62x,", BAD),
        ("st3 2.13x -> 2.20x, st5 1.31x -> 1.35x); post=off is the same, so it is albedo, not post.", BAD),
        ("OPEN 2, crowns with no interior (viewer).  cam02 fill tree centre/edge 0.504 vs the reference's", BAD),
        ("0.364, gradient 5.44 vs 8.51, p90-p10 over mean 2.05 vs 3.12; cam05 crown 1.26 vs 1.77 and p10", BAD),
        ("58.9 vs 31.7.  The crowns read as smooth balloons; 6c's soft edges flattened cam05 a further 6 %.", BAD),
        ("OPEN 3, the 3 m walk-in (row 5 left, export).  The LOD2 crown at 3 m is a handful of magnified", BAD),
        ("cream cut-outs and bare sticks over open sky — it does not read as a tree.  It wants its LOD1.", BAD),
        ("Perf 30.1 / 33.5 / 32.7 / 22.7 / 31.8 / 33.5 ms at 1440p (worst +1.9).  Resident 1 800.6 MB by", DIM),
        ("the committed sidecar = 1.50x the 1 200 MB Gate 1 budget (README and decisions.md say 1 717).", DIM),
        ("Name sweep: 0 new to explain.  Bare URL = the station-1 preset (luma 1.0002x, 0 page errors).", DIM),
        ("Carried, not 6c: cam03 has no deep shade (1.64x), cam06's water moires at grazing incidence,", DIM),
        ("the S-colonnade and backdrop walls are untextured fields, the lagoon teal away from the reflection.", DIM),
    ]
    lh = 15
    txt = Image.new("RGB", (W, lh * len(lines) + 12), BG)
    d = ImageDraw.Draw(txt)
    for i, (t, c) in enumerate(lines):
        d.text((6, 6 + i * lh), t, fill=c)

    lab = 16
    H = lab * 5 + th * 2 + gap * 6 + row3.height + row4.height + row5.height + row6.height + txt.height
    out = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(out)
    d.text((6, 3), "round16b: stations 1-6, every 6c default on (impmod=full, fartreemesh 12 m, "
                   "treemesh 40 m, shrub LOD1 30 m), t=0", fill=DIM)
    y = lab
    for r in range(2):
        for c in range(3):
            out.paste(thumbs[r * 3 + c], (c * (tw + gap), y))
        y += th + gap
    for label, colour, row in (
        ("FIXED, at 100 %:  the cam02 fill tree, round15 | round16b | Cycles — the blue is gone, "
         "the mass is not", GOOD, row3),
        ("NOT FIXED, at 100 %:  the cam05 shore, round15 | round16b | Cycles — balloon crowns over "
         "straw-pale cards", BAD, row4),
        ("the 3 m walk-in at station 2, at 100 %:  does the tree a walker stands at read as a tree?", BAD, row5),
        ("the hero's own left-shore planting at 100 %:  round16b over Cycles — unmoved by 6c, 1.61x", BAD, row6),
    ):
        d.text((6, y + 2), label, fill=colour)
        y += lab
        out.paste(row, (0, y))
        y += row.height + gap
    out.paste(txt, (0, y))
    o = R / "renders/web/round16b_gate.png"
    o.parent.mkdir(parents=True, exist_ok=True)
    out.save(o)
    print(o, out.size)


if __name__ == "__main__":
    main()
