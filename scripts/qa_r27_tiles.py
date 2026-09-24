#!/usr/bin/env python3
"""QA round 27 tile / composite builder (no Blender, no Chrome). Plain python (PIL).

    /opt/homebrew/bin/python3.13 scripts/qa_r27_tiles.py tiles   # 3x2 tiles of 640x540 at 100 % per station (cycles_p10; hero at 64 spp),
                                                                  # delivered as viewing pairs (tile c0|c1, c2 alone) under PFA_QA_TMP/r27
    /opt/homebrew/bin/python3.13 scripts/qa_r27_tiles.py gate    # renders/qa_comparisons/round27_gate.png, the committed 960 px sheet:
                                                                  # hero crops before (cycles_p9) | after (cycles_p10 64 spp) | ref 169 (warped
                                                                  # into the hero frame, mat_projection.warp_ref169) for attic, column, trees, water,
                                                                  # plus the cam02 cypress row (p9 | p10 | ref 062 letterboxed, unregistered)
"""
import os
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
P9 = ROOT / "renders/qa_comparisons/cycles_p9"
P10 = ROOT / "renders/qa_comparisons/cycles_p10"
OUT = Path(os.environ.get("PFA_QA_TMP", "/tmp")) / "r27"


def frame(d, st, spp=32):
    return Image.open(str(d / f"cam{st:02d}_1080_{spp}spp.png")).convert("RGB")


def tiles():
    OUT.mkdir(parents=True, exist_ok=True)
    for st in range(1, 7):
        im = frame(P10, st, 64 if st == 1 else 32)
        for r in range(2):
            t = [im.crop((640 * c, 540 * r, 640 * (c + 1), 540 * (r + 1))) for c in range(3)]
            pair = Image.new("RGB", (1284, 540), (255, 0, 255))
            pair.paste(t[0], (0, 0)); pair.paste(t[1], (644, 0))
            pair.save(OUT / f"t_cam{st:02d}_r{r}_c01.png")
            t[2].save(OUT / f"t_cam{st:02d}_r{r}_c2.png")
    print("tiles ->", OUT)


# hero crops at 1920x1080 (x0, y0, x1, y1): the brief's four rows
CROPS = [("attic + drum", (700, 120, 1180, 330)), ("columns", (960, 330, 1440, 540)),
         ("trees NE mass", (1180, 260, 1660, 470)), ("water", (720, 740, 1200, 950))]


def gate():
    import mat_projection as MP
    ref = MP.warp_ref169()[0]
    ref = Image.fromarray(np.clip(ref, 0, 255).astype(np.uint8)) if not isinstance(ref, Image.Image) else ref
    if ref.size != (1920, 1080):
        ref = ref.resize((1920, 1080))
    a, b = frame(P9, 1), frame(P10, 1, 64)
    cw, ch, lab = 320, 140, 16
    rows = len(CROPS) + 1
    sheet = Image.new("RGB", (960, lab + rows * (ch + lab)), (20, 20, 20))
    d = ImageDraw.Draw(sheet)
    d.text((4, 2), "QA 27  hero crops: cycles_p9 (before) | cycles_p10 64 spp (after) | ref 169 warped   + cam02 row", fill=(230, 230, 230))
    y = lab
    for name, bx in CROPS:
        d.text((4, y + 1), name, fill=(255, 220, 120))
        for j, src in enumerate((a, b, ref)):
            sheet.paste(src.crop(bx).resize((cw, ch), Image.Resampling.LANCZOS), (j * cw, y + lab))
        y += ch + lab
    d.text((4, y + 1), "cam02: new columnar cypresses at the rotunda's left base (p9 | p10 | ref 062 left base, same size box, not registered)", fill=(255, 220, 120))
    c2 = (300, 280, 1060, 612)
    r062 = Image.open(str(ROOT / "reference/photos/canonical/cam_02_ne_shore_threequarter.jpg")).convert("RGB")
    r062 = r062.resize((1920, int(1920 * r062.height / r062.width)))
    oy = (r062.height - 1080) // 2
    r062 = r062.crop((0, oy, 1920, oy + 1080))
    for j, (src, bx) in enumerate(((frame(P9, 2), c2), (frame(P10, 2), c2), (r062, (40, 420, 800, 752)))):
        sheet.paste(src.crop(bx).resize((cw, ch), Image.Resampling.LANCZOS), (j * cw, y + lab))
    out = ROOT / "renders/qa_comparisons/round27_gate.png"
    sheet.save(out)
    print("sheet ->", out, sheet.size)


if __name__ == "__main__":
    for c in sys.argv[1:] or ["tiles"]:
        globals()[c]()
