#!/usr/bin/env python3
"""The QA round 15 gate composite -> renders/web/round15_gate.png (960 px).

    python3 scripts/qa_r15_gate.py        # no Blender, no Chrome

An extension of `scripts/qa_r13_gate.py` (imported for `fit` / `strip`), which is not modified.

Row 1-2  the six round15 stations (Gate 4 look: baked + probe + impostors + water + post=all, t=0).
Row 3    QA-14-1 at 100 %: the open-water strip, viewer over Cycles — what the ripple rebuild did
         and the one thing it did not (a flat saturated teal slab outside the reflection mass).
Row 4    QA-14-1 at 100 %: the reflection mass, round15 | round14 | Cycles.
Row 5    the two defects the numbers under-report: the S-colonnade wall (QA-12b-2, a flat cream
         field with hard leaf cards on it) and the shore planting, viewer | Cycles.
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import qa_r13_gate as G  # noqa: E402

R, VIEW, W = G.R, G.VIEW, G.W
BG, FG, HI, DIM, BAD = G.BG, G.FG, G.HI, G.DIM, G.BAD
GOOD = (150, 210, 140)
REF1 = R / "renders/previews/qa/round10b_01_lagoon_hero_cycles.png"


def main():
    gap = 6
    tw = (W - 2 * gap) // 3
    thumbs = [G.fit(G.frame("round15", st), tw) for st in range(1, 7)]
    th = thumbs[0].height
    ref = Image.open(REF1).convert("RGB").resize((1920, 1080), Image.LANCZOS)

    ow = (300, 900, 1600, 1060)                       # the open water, away from the reflection
    a, b = G.frame("round15", 1).crop(ow), ref.crop(ow)
    row3 = Image.new("RGB", (a.width, a.height * 2 + gap), BG)
    row3.paste(a, (0, 0))
    row3.paste(b, (0, a.height + gap))
    row3 = G.fit(row3, W)

    box_w = (700, 700, 1300, 1000)                    # the reflection mass
    row4 = G.strip([G.frame("round15", 1).crop(box_w), G.frame("round14", 1).crop(box_w),
                    ref.crop(box_w)], W)

    box_s = (1420, 520, 1900, 700)                    # the S-colonnade wall and the leaf cards
    row5 = G.strip([G.frame("round15", 1).crop(box_s), ref.crop(box_s)], W)

    lines = [
        ("QA round 15 — Phase 6 Gate 4, round two.  6a PARITY REACHED on all five parity criteria;", HI),
        ("the >= 45 fps target is still not met (35.5 fps at the hero, attributed and on record).", HI),
        ("Scores 3.72 / 3.00 / 2.56 / 2.88 / 2.94 / 2.83 vs Phase 5 +0.05 / +0.06 / 0.00 / +0.07 / -0.12 / +0.17:", FG),
        ("every station inside the 0.5 window, none below 2.5 (cam03 2.56 is the floor).  MAE falls at all six.", FG),
        ("QA-14-1 WATER largely closed.  Open-water row high-pass 0.97 -> 6.92 (ref 13.23, inside the 0.5-2x", GOOD),
        ("acceptance), row/col 0.72 -> 3.71 (ref 3.24); reflection mass 0.85x -> 1.00x, hue within 2.8 deg;", GOOD),
        ("Fresnel now falls 95.5 -> 65.1 where the reference falls 87.8 -> 60.4 (round 14 was flat at 41), and", GOOD),
        ("the hard reflection line is gone.  RESIDUAL: open water hue 195.6 vs 144.8 deg, sat 0.363 vs 0.041,", BAD),
        ("lum 0.75x — outside the reflection the lagoon is a flat saturated teal slab with no crests (row 3).", BAD),
        ("QA-14-3 cam06 CLOSED: near half 0.53x -> 0.98x, p10 3.6 -> 69.1 (ref 58.0), frame 0.75x -> 1.00x,", GOOD),
        ("MAE 37.1 -> 18.7.  Residual far-terrain sat 3.7x -> 2.0x (bake/export).  QA-14-4 bloom at its ceiling:", GOOD),
        ("capital-row std 0.69x -> 0.85x (gate 0.85x PASS), dome halo +12.0 -> +5.1, attic sat 0.80x -> 0.87x", GOOD),
        ("(post-off ceiling 0.887x, so the rest is pre-post).  QA-14-5 half: cam02 tree level 0.99x, cyan gone,", FG),
        ("1 379/1 379 placements bound — hue still -44.7 deg (albedo, bake/export).  QA-14-2 cam03 FLAT:", BAD),
        ("near p10 53.1 vs 17.0, frame 1.80x — surfaces with no baked light on a single-point probe. Post-6a.", BAD),
        ("Minors closed: walk floor 0/24 below WATER_Z + 0.1 (probe now 6 s / 19 m, not 30 s / 96 m); loading", DIM),
        ("bar 640.1 / 640.1 MB = 100.0 % (was 122.3 %); README QA notes back.  NEW: the probe-lit backdrop wall", DIM),
        ("1.00x -> 1.26x.  Tiles: flat cream S-colonnade wall with hard leaf cards (row 5), blue-grey impostor", BAD),
        ("blobs and black alpha gaps at the shore, leaf-edge bloom specks, backdrop wall one untextured field.", BAD),
    ]
    lh = 15
    txt = Image.new("RGB", (W, lh * len(lines) + 12), BG)
    d = ImageDraw.Draw(txt)
    for i, (t, c) in enumerate(lines):
        d.text((6, 6 + i * lh), t, fill=c)

    lab = 16
    H = lab * 4 + th * 2 + gap * 5 + row3.height + row4.height + row5.height + txt.height
    out = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(out)
    d.text((6, 3), "round15: stations 1-6, lighting=baked, probe + impostors + water + post=all, reflset=orn, t=0",
           fill=DIM)
    y = lab
    for r in range(2):
        for c in range(3):
            out.paste(thumbs[r * 3 + c], (c * (tw + gap), y))
        y += th + gap
    for label, colour, row in (
        ("QA-14-1 open water at 100 % (300,900-1600,1060):  round15 over Cycles — the residual teal slab", BAD, row3),
        ("QA-14-1 reflection mass at 100 %:  round15 | round14 | Cycles — the ripple rebuild", GOOD, row4),
        ("carried, visible only at 100 %:  S-colonnade wall + shore cards, round15 | Cycles", BAD, row5),
    ):
        d.text((6, y + 2), label, fill=colour)
        y += lab
        out.paste(row, (0, y))
        y += row.height + gap
    out.paste(txt, (0, y))
    o = R / "renders/web/round15_gate.png"
    o.parent.mkdir(parents=True, exist_ok=True)
    out.save(o)
    print(o, out.size)


if __name__ == "__main__":
    main()
