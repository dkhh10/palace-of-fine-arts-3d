#!/usr/bin/env python3
"""The Phase 6 gate composite -> renders/web/round1{3,4}_gate.png (960 px).

    python3 scripts/qa_r13_gate.py              # round 13, the Gate 3 lightmap composite
    python3 scripts/qa_r13_gate.py --round 14   # round 14, the Gate 4 viewer composite

Round 13 (below, unchanged): the six round13b stations, QA-13-1 and QA-13-2 at 100 %.

Row 1-2  the six round13b stations (manifest v4, lighting=baked, post OFF, both placeholder sets hidden).
Row 3    the verdict crop: the cam01 north colonnade at 100 %, baked | Gate 2 | Phase 5 — QA-13-1.
Row 4    the cam04 rotunda ceiling, baked | Phase 5 — QA-13-2, the one map that must be re-baked,
         beside the cam01 rotunda at 100 %, which is what the lightmaps bought.

The frames live on branch phase6-viewer; PFA_VIEWER_WEB overrides where they are read from.

    python3 scripts/qa_r13_gate.py        # no Blender, no Chrome
"""
import os
from pathlib import Path

from PIL import Image, ImageDraw

R = Path(__file__).resolve().parent.parent
VIEW = Path(os.environ.get("PFA_VIEWER_WEB", R / ".claude/worktrees/phase6-viewer/renders/web"))
OUT = R / "renders/web/round13_gate.png"
W, BG, FG, HI, DIM = 960, (17, 17, 19), (238, 233, 223), (240, 176, 96), (150, 148, 142)
BAD = (232, 120, 110)
REF = {
    1: "renders/previews/qa/round10b_01_lagoon_hero_cycles.png",
    4: "renders/previews/qa/round09_04_rotunda_ceiling_cycles.png",
}
# Round 14 references: the hero as always, the compositor-on Cycles frames for 2-6.
REF14 = {
    1: "renders/previews/qa/round10b_01_lagoon_hero_cycles.png",
    4: "renders/previews/qa/round13_04_rotunda_ceiling_cycles.png",
}


def fit(im, w):
    return im.resize((w, round(im.height * w / im.width)), Image.LANCZOS)


def frame(tag, st):
    return Image.open(VIEW / f"{tag}_cam{st:02d}.png").convert("RGB")


def strip(images, w, gap=6):
    images = [im for im in images]
    h = images[0].height
    s = Image.new("RGB", (sum(i.width for i in images) + gap * (len(images) - 1), h), BG)
    x = 0
    for im in images:
        s.paste(im, (x, 0))
        x += im.width + gap
    return fit(s, w)


def main_r14():
    """Gate 4: the six round14 stations, the two closed defects and the water at 100 %."""
    gap = 6
    tw = (W - 2 * gap) // 3
    thumbs = [fit(frame("round14", st), tw) for st in range(1, 7)]
    th = thumbs[0].height
    refs = {st: Image.open(R / REF14[st]).convert("RGB").resize((1920, 1080), Image.LANCZOS)
            for st in (1, 4)}

    box_n = (20, 520, 340, 645)                       # QA-13-1, the north colonnade bays
    row3 = strip([frame("round14", 1).crop(box_n), frame("round13b", 1).crop(box_n),
                  refs[1].crop(box_n)], W)
    box_c = (560, 180, 1200, 560)                     # QA-13-2, the cam04 coffer field
    row4 = strip([frame("round14", 4).crop(box_c), frame("round13b", 4).crop(box_c),
                  refs[4].crop(box_c)], W)
    box_w = (700, 700, 1300, 1000)                    # QA-14-1, the water
    row5 = strip([frame("round14", 1).crop(box_w), refs[1].crop(box_w)], W)

    lines = [
        ("QA round 14 — Phase 6 Gate 4, the viewer proper (baked + probe + impostors + water + post=all)", HI),
        ("ONE MORE ROUND.  Scores 3.61 / 2.94 / 2.56 / 2.88 / 2.83 / 2.56 — every station within 0.5 of", FG),
        ("Phase 5 (-0.06 / 0.00 / 0.00 / +0.07 / -0.23 / -0.11) and none below 2.5.  No blocker.", FG),
        ("CLOSED: QA-13-1 the blue bays  23.0 % -> 0.2 % of the band B>R+20 (Cycles 0.0 %), hue 220 -> 40 deg.", HI),
        ("CLOSED: QA-13-2 the coffer field  0.40x -> 1.02x, p10 0.00 -> 29.5 (ref 28.6), below luma 8  37.8 -> 0.02 %.", HI),
        ("CLOSED at cam06: QA-12b-1 olive  20.2 -> 1.5 % G>R (ref 1.4 %); cam02 19.7 -> 7.4 % (ref 2.2 %), still 3.4x.", HI),
        ("QA-14-1 WATER, the worst box of the round: the ripple does not exist.  Row high-pass in the open", BAD),
        ("lagoon 0.97 vs the reference's 13.23 (0.07x), row/col 0.72 vs 3.24; open water 66.8 vs 118.0 (0.57x),", BAD),
        ("hue 200 vs 145 deg, sat 0.326 vs 0.041; the near-edge Fresnel flattens to 41 where the reference falls", BAD),
        ("96 -> 60.  The rotunda DOES reflect (arch and shafts legible), so the 6a criterion itself passes.", BAD),
        ("QA-14-2 cam03 has no deep shade: frame 1.67x, p10 39.8 vs 7.3 (5.5x); post moves it 80.6 -> 81.8.", BAD),
        ("QA-14-3 cam06 lower frame crushed: p10 9.7 vs 65.6 (0.15x), near ground 0.53x, far terrain sat 3.7x.", BAD),
        ("QA-14-4 bloom flattens the hero: capital-row std 0.93x -> 0.69x, S-colonnade mid 0.40x, vault field", DIM),
        ("0.76x -> 1.25x, sunlit-attic sat hold 0.89x -> 0.80x, and a halo around the dome cap at 100 %.", DIM),
        ("QA-14-5 near foliage at 100 %: flat angular leaf cut-outs with black gaps; cam02 hue -45.9 deg vs Cycles.", DIM),
        ("Perf 28.9 ms = 34.6 fps at 1440p (45 only at cam04), resident 1 678 MB: 45 fps NOT met, attributed.", DIM),
        ("Walk 24/24 probes out of the lagoon; 3 stand at -1.225 m, 25 mm below the WATER_Z + 0.1 clamp floor.", DIM),
    ]
    lh = 15
    txt = Image.new("RGB", (W, lh * len(lines) + 12), BG)
    d = ImageDraw.Draw(txt)
    for i, (t, c) in enumerate(lines):
        d.text((6, 6 + i * lh), t, fill=c)

    labels = 16
    H = labels * 4 + th * 2 + gap * 5 + row3.height + row4.height + row5.height + txt.height
    out = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(out)
    d.text((6, 3), "round14: stations 1-6, lighting=baked, probe + impostors + water + post=all, t=0", fill=DIM)
    y = labels
    for r in range(2):
        for c in range(3):
            out.paste(thumbs[r * 3 + c], (c * (tw + gap), y))
        y += th + gap
    for label, colour, row in (("QA-13-1 CLOSED  cam01 north colonnade at 100 %:  round14 | round13b | Cycles", HI, row3),
                               ("QA-13-2 CLOSED  cam04 coffer field at 100 %:  round14 | round13b | Cycles", HI, row4),
                               ("QA-14-1 OPEN  cam01 water at 100 %:  round14 | Cycles — no ripple, no Fresnel", BAD, row5)):
        d.text((6, y + 2), label, fill=colour)
        y += labels
        out.paste(row, (0, y))
        y += row.height + gap
    out.paste(txt, (0, y))
    o = R / "renders/web/round14_gate.png"
    o.parent.mkdir(parents=True, exist_ok=True)
    out.save(o)
    print(o, out.size)


def main():
    gap = 6
    tw = (W - 2 * gap) // 3
    thumbs = [fit(frame("round13b", st), tw) for st in range(1, 7)]
    th = thumbs[0].height

    box_n = (20, 520, 340, 645)                       # the north colonnade, QA-13-1
    ref1 = Image.open(R / REF[1]).convert("RGB").resize((1920, 1080), Image.LANCZOS)
    row3 = strip([frame("round13b", 1).crop(box_n),
                  frame("gate2", 1).crop(box_n),
                  ref1.crop(box_n)], W)

    box_c = (560, 180, 1200, 560)                     # the cam04 coffer field, QA-13-2
    ref4 = Image.open(R / REF[4]).convert("RGB").resize((1920, 1080), Image.LANCZOS)
    half = (W - gap) // 2
    row4 = strip([frame("round13b", 4).crop(box_c), ref4.crop(box_c)], W)
    box_r = (760, 120, 1180, 400)                     # what the lightmaps bought, cam01 rotunda
    row5 = strip([frame("round13b", 1).crop(box_r), ref1.crop(box_r)], W)

    lines = [
        ("QA round 13 — Phase 6 Gate 3, the lightmaps alone (post off, water on, impostors out)", HI),
        ("LIGHTMAPS ACCEPTED with one re-bake: ARCH_rotunda_plaster_ceiling_merged", FG),
        ("16/16 own maps + 988/988 slots applied, match err <= 0.019 m.  Hero frame 117.5 -> 135.99 vs Cycles", DIM),
        ("139.98 (0.971x), p10 52.9 vs 52.2; MAE vs the reference falls at all six stations (hero 36.7 -> 29.9).", DIM),
        ("Boxes, Gate 2 -> baked vs Phase 5:  shade band 1.18x -> 0.93x  |  S-colonnade wall 1.44x -> 1.23x,", FG),
        ("hp9 5.83 -> 27.71 (ref 26.32)  |  capital row 1.25x -> 1.11x  |  cam05 pier std 23.6 -> 29.4 (ref 38.1).", FG),
        ("QA-13-2 cam04 coffer field 0.40x Phase 5, p10 0.00, 37.8 % of pixels below luma 8 (Phase 5 0.0 %):", BAD),
        ("the plaster-shell map maxes at 0.72 over 4.9 % of its texels. RE-BAKE (split the visible shell).", BAD),
        ("QA-13-1 the north colonnade reads as blue rectangles: 23.0 % of the band is B>R+20 (Gate 2 3.9 %,", BAD),
        ("Phase 5 0.0 %), 96.4 % of them bit-identical with the lightmaps OFF -> not the bake, find the surface.", BAD),
        ("QA-12b-1 olive NOT closed: cam02 16.0 -> 19.7 %, cam06 21.9 -> 20.2 % G>R (Phase 5 0.1 / 9.7 %);", DIM),
        ("per-luma-bin it is 30.9 % vs 2.3 % at 40-60, so it is not a brightness artefact.  QA-12-4 shaft CV", DIM),
        ("0.041/0.133 -> 0.088/0.187 (Phase 5 0.469/0.539).  Sunlit-attic sat hold BREAKS: 0.94x -> 0.89x.", DIM),
        ("Expected, not scored: post, far-tree impostors, near-tree vertex irradiance (blue foliage), mist.", DIM),
    ]
    lh = 15
    txt = Image.new("RGB", (W, lh * len(lines) + 12), BG)
    d = ImageDraw.Draw(txt)
    for i, (t, c) in enumerate(lines):
        d.text((6, 6 + i * lh), t, fill=c)

    labels = 16
    H = labels + th * 2 + gap * 5 + row3.height + row4.height + row5.height + txt.height + labels * 3
    out = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(out)
    y = 0
    d.text((6, 3), "round13b: stations 1-6, manifest v4, lighting=baked, post=none, placeholders hidden",
           fill=DIM)
    y = labels
    for r in range(2):
        for c in range(3):
            out.paste(thumbs[r * 3 + c], (c * (tw + gap), y))
        y += th + gap
    d.text((6, y + 2), "QA-13-1  cam01 north colonnade at 100 %:  baked | Gate 2 | Phase 5 Cycles", fill=BAD)
    y += labels
    out.paste(row3, (0, y))
    y += row3.height + gap
    d.text((6, y + 2), "QA-13-2  cam04 coffer field at 100 %:  baked | Phase 5 Cycles", fill=BAD)
    y += labels
    out.paste(row4, (0, y))
    y += row4.height + gap
    d.text((6, y + 2), "what the lightmaps bought:  cam01 rotunda, baked | Phase 5 Cycles", fill=HI)
    y += labels
    out.paste(row5, (0, y))
    y += row5.height + gap
    out.paste(txt, (0, y))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    out.save(OUT)
    print(OUT, out.size)


if __name__ == "__main__":
    import sys
    if "--round" in sys.argv and sys.argv[sys.argv.index("--round") + 1] == "14":
        main_r14()
    else:
        main()
