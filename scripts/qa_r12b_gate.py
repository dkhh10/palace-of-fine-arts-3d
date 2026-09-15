#!/usr/bin/env python3
"""QA round 12b: the Phase 6 Gate 2 re-check composite -> renders/web/round12b_gate.png (960 px).

Row 1-2  the six Gate 2 stations (materials=pbr, lighting=direct, both placeholder sets hidden).
Row 3    QA-12-1 at 100 %: the cam05 pier face, viewer | Phase 5 — the box that failed round 12.
Row 4    the control pair that carries the verdict (a sunlit box, where the light is the same in both
         frames, beside a sun-less one) and QA-12b-1, the green cast on sun-less stone at cam02.

    python3 scripts/qa_r12b_gate.py        # no Blender, no Chrome
"""
from pathlib import Path

from PIL import Image, ImageDraw

R = Path(__file__).resolve().parent.parent
OUT = R / "renders/web/round12b_gate.png"
W, BG, FG, HI, DIM = 960, (17, 17, 19), (238, 233, 223), (240, 176, 96), (150, 148, 142)
REF = {
    1: "renders/previews/qa/round10b_01_lagoon_hero_cycles.png",
    5: "renders/previews/qa/round09_05_south_lawn.png",
}


def fit(im, w):
    return im.resize((w, round(im.height * w / im.width)), Image.LANCZOS)


def viewer(st):
    return Image.open(R / f"renders/web/gate2_cam{st:02d}.png").convert("RGB")


def pair(st, box, w, zoom=1):
    v = viewer(st)
    r = Image.open(R / REF[st]).convert("RGB").resize(v.size, Image.LANCZOS)
    a, b = v.crop(box), r.crop(box)
    if zoom > 1:
        a = a.resize((a.width * zoom, a.height * zoom), Image.NEAREST)
        b = b.resize((b.width * zoom, b.height * zoom), Image.NEAREST)
    s = Image.new("RGB", (a.width * 2 + 6, a.height), BG)
    s.paste(a, (0, 0))
    s.paste(b, (a.width + 6, 0))
    return fit(s, w)


def solo(st, box, w, zoom=1):
    a = viewer(st).crop(box)
    if zoom > 1:
        a = a.resize((a.width * zoom, a.height * zoom), Image.NEAREST)
    return fit(a, w)


def main():
    gap = 6
    tw = (W - 2 * gap) // 3
    thumbs = [fit(viewer(st), tw) for st in range(1, 7)]
    th = thumbs[0].height

    p1 = pair(5, (1100, 500, 1420, 720), W)                   # QA-12-1, the round-12 blocker
    half = (W - gap) // 2
    p2 = pair(1, (880, 210, 1040, 270), half)                 # sunlit control: same light both sides
    p3 = solo(2, (600, 60, 1000, 230), half)                  # QA-12b-1 green cast, sun-less faces

    caps = [
        "QA-12-1  cam05 pier face 787 373 853 453 at the reference's 1280x720 (viewer | Phase 5):",
        "  mid(5-21) 2.68 -> 7.05 (target >= 7.0, PASS), hp9 8.14, std 22.87 (target >= 25, short), mean 144.8 vs 145.4.",
        "  cam01 S-colonnade wall 1600 590 1670 635: hp9 0.6-0.8 -> 5.83 (target >= 4.0, PASS).  Grain is present at 100 %.",
        "THE CONTROL THAT DECIDES IT.  Where the sun reaches the surface in BOTH frames the material amplitude is at or",
        "above parity - sunlit attic mid 1.10x / std 1.17x, attic pedestals 1.33x / 1.49x, dome cap 0.99x / 0.91x.  Where",
        "the Phase 5 frame has shade and Gate 2's direct mode has none, it is 0.35-0.81x (cam05 pier 0.47x, colonnade",
        "pedestal 0.44x).  The residual is the shade/occlusion term, which Gate 3's lightmaps carry - not the albedo.",
        "QA-12b-1 NEW: sun-less stone reads olive-green - cam02 RGB 107/125/107, hue 119.4, sat 0.143; 16.0 % of the cam02",
        "building pixels and 21.9 % of cam06's have G > R, against 0.1 % in the Phase 5 hero and 0.0 % of the baked albedo",
        "itself (maiden and concrete_ochre albedos are R > G > B on 100 % of their pixels).  Owner: lighting path, Gate 3.",
        "VERDICT: GATE 2 PASS.  Every material row is within the 0.5 parity window; no row's residual is a material gap.",
    ]
    ch = 14 * len(caps) + 22
    H = 30 + 2 * (th + gap) + 20 + p1.height + 20 + max(p2.height, p3.height) + 20 + ch
    out = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(out)
    d.text((8, 8), "QA round 12b - Phase 6 Gate 2 re-check after QA-12-1: atlas split + tiling detail layer. "
                   "materials=pbr, lighting=direct.", fill=FG)
    y = 30
    for i, t in enumerate(thumbs):
        out.paste(t, ((i % 3) * (tw + gap), y + (i // 3) * (th + gap)))
    y += 2 * (th + gap) + 4
    d.text((8, y), "cam01-06, 1920x1080, capture 2026-09-15 21:4x (KTX2 detail set, gain 1, both placeholder sets hidden)",
           fill=DIM)
    y += 16
    out.paste(p1, (0, y))
    y += p1.height + 4
    d.text((8, y), "QA-12-1  cam05 (1100,500)-(1420,720) 100 %: viewer | Phase 5 round-09", fill=HI)
    y += 16
    out.paste(p2, (0, y))
    out.paste(p3, (half + gap, y))
    yy = y + max(p2.height, p3.height) + 2
    d.text((8, yy), "control: sunlit attic, viewer | Phase 5 - same light, material at parity", fill=HI)
    d.text((half + gap + 8, yy), "QA-12b-1: sun-less faces read olive-green (cam02)", fill=HI)
    y = yy + 20
    for c in caps:
        d.text((8, y), c, fill=HI if c.startswith(("VERDICT", "THE CONTROL")) else FG)
        y += 14
    OUT.parent.mkdir(parents=True, exist_ok=True)
    out.save(OUT)
    print(OUT, out.size)


if __name__ == "__main__":
    main()
