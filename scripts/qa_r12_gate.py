#!/usr/bin/env python3
"""QA round 12: the Phase 6 Gate 2 composite -> renders/web/round12_gate.png (960 px).

Row 1-2: the six Gate 2 stations (pbr materials, direct lighting, both placeholder sets hidden).
Row 3  : the blocking defect, QA-12-1 - cam05 pier face, viewer | Phase 5, 100 % crops.
Row 4  : QA-12-2 the dome cap and QA-12-3 the south-colonnade back wall, viewer | Phase 5.

    python3 scripts/qa_r12_gate.py        # no Blender, no Chrome
"""
from pathlib import Path

from PIL import Image, ImageDraw

R = Path(__file__).resolve().parent.parent
OUT = R / "renders/web/round12_gate.png"
W, BG, FG, HI = 960, (17, 17, 19), (238, 233, 223), (240, 176, 96)
REF = {
    1: "renders/previews/qa/round10b_01_lagoon_hero_cycles.png",
    5: "renders/previews/qa/round09_05_south_lawn.png",
}


def fit(im, w):
    return im.resize((w, round(im.height * w / im.width)), Image.LANCZOS)


def viewer(st):
    return Image.open(R / f"renders/web/gate2_cam{st:02d}.png").convert("RGB")


def ref(st, size):
    return Image.open(R / REF[st]).convert("RGB").resize(size, Image.LANCZOS)


def pair(st, box, w):
    v, r = viewer(st), ref(st, viewer(st).size)
    a, b = v.crop(box), r.crop(box)
    s = Image.new("RGB", (a.width * 2 + 6, a.height), BG)
    s.paste(a, (0, 0)); s.paste(b, (a.width + 6, 0))
    return fit(s, w)


def main():
    gap = 6
    tw = (W - 2 * gap) // 3
    thumbs = [fit(viewer(st), tw) for st in range(1, 7)]
    th = thumbs[0].height

    p1 = pair(5, (1100, 500, 1420, 720), W)                  # QA-12-1, the blocker
    half = (W - gap) // 2
    p2 = pair(1, (870, 70, 1070, 170), half)                 # QA-12-2 dome cap
    p3 = pair(1, (1560, 540, 1760, 640), half)               # QA-12-3 colonnade wall

    caps = [
        "QA-12-1 BLOCKER  cam05 pier face 100 % (viewer | Phase 5): mid-band 5-21 px 2.68 vs 10.11 = 0.27x, std 12.3 vs 38.3.",
        "The albedo is a DIFFUSE colour-only bake and 7 of 12 ARCH/ground sets ship normal.texture = null, so the bump-driven",
        "streaking of the Phase 5 concrete is in neither map: ARCH stone reads smooth plastic from 15-25 m.  Owner: bake.",
        "QA-12-2 cam01 dome cap: sat 0.334 vs 0.464 = 0.64x (QA-10-8 carried, now flatter).   QA-12-3 cam01 S colonnade back",
        "wall: hp9 0.6-0.8 against 13-19 on the rotunda attic in the same frame; that atlas packs 16 % UV coverage.  The",
        "Phase 5 panels are 1280x720 upscaled (cam05, cam03) and are in shade at QA-12-3: read them for texture, not for level.",
        "Sunlit stone is RIGHT: sunlit attic hue +1.9 deg, sat 0.97x of the Phase 5 hero; whole-building sat 0.84x of the r10b",
        "render = 1.02x of photograph 169 (r10b was 1.22x).  Everything darker than that is the missing shade, not the albedo.",
        "VERDICT: GATE 2 FAIL on one row - cam05 Material realism 3.5 -> 2.5 (-1.0, parity window 0.5).  All other rows within 0.5.",
    ]
    ch = 14 * len(caps) + 22
    H = 30 + 2 * (th + gap) + 20 + p1.height + 20 + max(p2.height, p3.height) + ch
    out = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(out)
    d.text((8, 8), "QA round 12 - Phase 6 Gate 2: the PBR set alone, materials=pbr, lighting=direct (sun + PMREM, no "
                   "lightmaps, no shadows).", fill=FG)
    y = 30
    for i, t in enumerate(thumbs):
        out.paste(t, ((i % 3) * (tw + gap), y + (i // 3) * (th + gap)))
    y += 2 * (th + gap) + 4
    d.text((8, y), "cam01-06, 1920x1080, capture 2026-09-15 19:09", fill=(150, 148, 142))
    y += 16
    out.paste(p1, (0, y)); y += p1.height + 4
    d.text((8, y), "QA-12-1  cam05 (1100,500)-(1420,720): viewer | Phase 5 round-09", fill=HI)
    y += 16
    out.paste(p2, (0, y)); out.paste(p3, (half + gap, y))
    d.text((8, y + p2.height + 2), "QA-12-2 dome cap", fill=HI)
    d.text((half + gap + 8, y + p3.height + 2), "QA-12-3 S colonnade back wall", fill=HI)
    y += max(p2.height, p3.height) + 18
    for c in caps:
        d.text((8, y), c, fill=FG if not c.startswith("VERDICT") else HI)
        y += 14
    OUT.parent.mkdir(parents=True, exist_ok=True)
    out.save(OUT)
    print(OUT, out.size)


if __name__ == "__main__":
    main()
