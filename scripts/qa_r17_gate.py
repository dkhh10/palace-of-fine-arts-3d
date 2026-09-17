#!/usr/bin/env python3
"""The QA round 17 gate composite -> renders/web/round17_gate.png (960 px).

    python3 scripts/qa_r17_gate.py        # no Blender, no Chrome

An extension of `scripts/qa_r13_gate.py` (imported for `fit` / `frame` / `strip`), unmodified.
The name is round17_gate, not round16c_gate: a 960 px `round16c_gate.jpg` already exists from the
viewer's own capture and this sheet is the critic's, not the engineer's.

Row 1-2  the six round16c stations (the 6c delivery look after round 3, every default on, t=0).
Row 3    what round 3 fixed: the station-2 fill tree at 100 %, round16b | round16c | Cycles.
Row 4    the station-5 shore at 100 %, round16b | round16c | Cycles — the crowns gain their interior,
         the shrub band drops to the reference LEVEL, the card STRUCTURE does not change.
Row 5    the 3 m walk-in at station 2 at 100 % — QA 16's open 3, now a canopy.
Row 6    the hero's own left-shore planting at 100 %, round16c over Cycles — 1.61x -> 1.36x, still cards.
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
    thumbs = [G.fit(G.frame("round16c", st), tw) for st in range(1, 7)]
    th = thumbs[0].height

    b2 = (700, 660, 1240, 950)                       # the far tree that fills cam02
    row3 = G.strip([G.frame("round16b", 2).crop(b2), G.frame("round16c", 2).crop(b2),
                    ref(2).crop(b2)], W)
    b5 = (200, 560, 740, 900)                        # the station-5 lawn tree and shore band
    row4 = G.strip([G.frame("round16b", 5).crop(b5), G.frame("round16c", 5).crop(b5),
                    ref(5).crop(b5)], W)
    row5 = G.fit(Image.open(VIEW / "tiles/round16c/round16c_walkin_tile.png")
                 .convert("RGB").crop((0, 0, 964, 600)), W)
    b1 = (40, 612, 620, 700)                         # the hero's left shore planting
    hero = Image.new("RGB", (580, 182), BG)
    hero.paste(G.frame("round16c", 1).crop(b1), (0, 0))
    hero.paste(ref(1).crop(b1), (0, 94))
    row6 = G.fit(hero, W)

    lines = [
        ("QA round 17 — the Phase 6c foliage gate, round two of two.  Verdict: 6c CLOSED WITH RESIDUALS.", HI),
        ("Three of the four acceptance conjuncts pass (no station drops; station 2 rises +0.25 on round 15;", HI),
        ("crowns carry their interior and the shrub boxes sit at the reference level).  The +3 ms frame-time", HI),
        ("conjunct FAILS on the cold pass of record at stations 1 and 2 (+4.2, +4.8) and is pending a same-", HI),
        ("session A/B; and the tiles still show card structure at 3 m — so: closed, with the residuals below.", HI),
        ("Scores 3.78 / 3.25 / 2.63 / 2.88 / 2.94 / 2.83; vs round 16 +0.06 / +0.12 / +0.07 / 0 / 0 / 0;", FG),
        ("vs round 15 +0.06 / +0.25 / +0.07 / 0 / 0 / 0.  None below 2.5, none within 0.5 of Phase 5 breached.", FG),
        ("CLOSED — crown interior (viewer, ?impint).  cam02 centre/edge 0.504 -> 0.393 (ref 0.364), p10 18.6", GOOD),
        ("-> 5.3 (ref 4.1); cam05 range/mean 1.260 -> 1.722 (ref 1.773); every crown box's level 0.94-1.05x.", GOOD),
        ("CLOSED — shrub LEVEL (viewer, ?cardenv 0.3).  Frame-normalised vs Cycles: st1 1.70 -> 1.47x,", GOOD),
        ("st2 1.48 -> 1.12x, st3 1.34 -> 0.94x, st5 1.33 -> 1.05x; hard-edge share falls at 7 boxes of 8.", GOOD),
        ("CLOSED — the 3 m walk-in (row 5).  The walk-up LOD1 set reads as a canopy: overlapping leaf cards,", GOOD),
        ("branches, sky through the gaps, where QA 16 found magnified cut-outs and bare sticks.", GOOD),
        ("RESIDUAL 1 — shrub STRUCTURE (export).  Row 4 and row 6: broad flat angular cards at 3 m and at 8 m", BAD),
        ("(cam03 1.53x, the worst box left); leaf-green share 10-15 % where Cycles has 18-33 %.", BAD),
        ("RESIDUAL 2 — the darkening overshoots (viewer).  st1 crown p10 20.9 vs ref 36.8 and centre/edge", BAD),
        ("0.491 vs 0.852; st5's whole frame 146.8 vs the reference's 151.2 and its probe MAE rises 20.4->21.3;", BAD),
        ("a pale halo now reads around the darker crowns (carried, but newly conspicuous).", BAD),
        ("RESIDUAL 3 — far-tree tops stay opaque (bake/export): cam02 r1c3 and cam03 r1c1 are solid cut-outs", BAD),
        ("where the reference shows sky through the twigs.  Unmoved by round 3.", BAD),
        ("Perf, 1440p: the COLD pass of record 32.4/37.0/35.1/22.1/32.2/34.0 ms = +4.2/+4.8/+2.2/-0.4/+1.8/+1.9", DIM),
        ("on round 15 (measured another day; a same-session A/B is pending).  Warm A 30.2/33.5/34.4/23.2/33.7/", DIM),
        ("35.1, warm B 32.9/37.4/37.2/21.9/32.1/34.8 — the three passes spread up to 3.9 ms.  Draws identical", DIM),
        ("to round16b at all six, triangles identical at five (cam03 +0.39 M = the walk-up set), so only cam03's", DIM),
        ("rise is demonstrably 6c's; stations 1 and 2 added no draws and no triangles.", DIM),
        ("Resident 1 931.4 MB = 1.61x the 1 200 MB Gate 1 budget, +130.8 on round16b, all walk-up geometry.", DIM),
        ("Walk clamp re-run at 30 s: 24/24 probes, lowest ground -0.750 m vs the -1.20 floor, 0 below.", DIM),
        ("Name sweep 0 new to explain.  Bare URL = the station-1 preset (luma 0.9999x, 0 page errors).", DIM),
        ("Carried, not 6c: cam03 has no deep shade and its column texture is visibly blurred at 100 %;", DIM),
        ("cam06's water moires at grazing incidence; the backdrop city blocks are flat untextured planes;", DIM),
        ("the hero's reflection is cooler and less saturated than Cycles and the open lagoon is a teal slab.", DIM),
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
    d.text((6, 3), "round16c: stations 1-6, every round-3 default on (crownint, cardint, leafgate 0.45, "
                   "impint 0.90/0.015, cardenv 0.3, walkup 15 m), t=0", fill=DIM)
    y = lab
    for r in range(2):
        for c in range(3):
            out.paste(thumbs[r * 3 + c], (c * (tw + gap), y))
        y += th + gap
    for label, colour, row in (
        ("CLOSED, at 100 %:  the cam02 fill tree, round16b | round16c | Cycles — the cloud becomes a crown "
         "with a dark core", GOOD, row3),
        ("PART-CLOSED, at 100 %:  the cam05 shore, round16b | round16c | Cycles — level yes, card structure "
         "no", BAD, row4),
        ("CLOSED:  the 3 m walk-in at station 2, at 100 %, both headings — the walk-up LOD1 set reads as a "
         "canopy", GOOD, row5),
        ("RESIDUAL:  the hero's left-shore planting at 100 %, round16c over Cycles — 1.61x -> 1.36x, still "
         "flat cards", BAD, row6),
    ):
        d.text((6, y + 2), label, fill=colour)
        y += lab
        out.paste(row, (0, y))
        y += row.height + gap
    out.paste(txt, (0, y))
    o = R / "renders/web/round17_gate.png"
    o.parent.mkdir(parents=True, exist_ok=True)
    out.save(o)
    print(o, out.size)


if __name__ == "__main__":
    main()
