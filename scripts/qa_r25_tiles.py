#!/usr/bin/env python3
"""QA round 25 tile / composite builder (no Blender, no Chrome).

    python3 scripts/qa_r25_tiles.py tiles [st ...]   # the 3x2 100 % tiles per station (the gate rule)
    python3 scripts/qa_r25_tiles.py gate             # renders/web/gate13_gate.png, the 960 px round sheet
    python3 scripts/qa_r25_tiles.py shade            # the cam02 shaded-shaft 100 % strip (tile evidence)
    python3 scripts/qa_r25_tiles.py col              # the cam03 near-column 100 % strip

Tiles are cut at 100 % from the delivered 1920x1080 PNGs (`renders/web/gate13_cam0N.png`), 640x540
each, written to the scratchpad -- they are viewing fixtures, never committed.  The Phase 9 Cycles
references (`renders/qa_comparisons/cycles_p9/cam0N_1080_32spp.png`) are full-resolution this time,
so a Cycles row in a 100 % strip is a true 1:1 crop.
"""
import os
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "renders" / "web"
P9 = ROOT / "renders/qa_comparisons/cycles_p9"
CUR, PREV = "gate13", "gate12"
REF062 = ROOT / "reference/photos/raw/ref_062_rotunda_Palace_of_Fine_Arts_View_of_Rotunda_from_north_eas.jpg"
OUT = Path(os.environ.get("PFA_QA_TMP", "/tmp")) / "r25"

# light_r16/r17 BOXES["02"] and BOXES["03"] are stated on a 1280x720 fixture; x1.5 to frame px.
S = 1.5
SHADE02 = {"shade_pier": (405, 265, 465, 395), "shade_arch": (580, 275, 690, 355),
           "shade_pier_r": (875, 255, 930, 385), "shade_frieze": (500, 150, 700, 200)}
NEAR03 = (900, 150, 1270, 700)


def _f(tag, st):
    return Image.open(str(WEB / f"{tag}_cam{st:02d}.png")).convert("RGB")


def _cyc(st):
    return Image.open(str(P9 / f"cam{st:02d}_1080_32spp.png")).convert("RGB")


def cmd_tiles(args):
    """3 x 2 tiles of 640x540 at 100 %, the CLAUDE.md gate rule, one station per call or all six."""
    OUT.mkdir(parents=True, exist_ok=True)
    for st in [int(a) for a in args] or list(range(1, 7)):
        im = _f(CUR, st)
        for r in range(2):
            for c in range(3):
                t = im.crop((c * 640, r * 540, (c + 1) * 640, (r + 1) * 540))
                t.save(str(OUT / f"{CUR}_cam{st:02d}_r{r}c{c}.png"))
        print(f"[tiles] cam{st:02d} -> {OUT}/{CUR}_cam{st:02d}_r?c?.png (6 x 640x540 at 100 %)")


def _row(imgs, labels, scale=1):
    w = sum(i.width for i in imgs)
    h = max(i.height for i in imgs)
    out = Image.new("RGB", (w, h + 16), (16, 16, 16))
    d = ImageDraw.Draw(out)
    x = 0
    for im, lab in zip(imgs, labels):
        out.paste(im, (x, 16))
        d.text((x + 4, 3), lab, fill=(255, 235, 140))
        x += im.width
    return out


def cmd_shade(_a=()):
    """cam02 shaded shafts at 100 %: gate12 | gate13 | Cycles p9 | ref 062 (fixture-resampled)."""
    OUT.mkdir(parents=True, exist_ok=True)
    box = (int(380 * S), int(140 * S), int(950 * S), int(400 * S))
    rows = [_f(PREV, 2).crop(box), _f(CUR, 2).crop(box), _cyc(2).crop(box)]
    ph = Image.open(str(REF062)).convert("RGB").resize((1920, 1080), Image.LANCZOS).crop(box)
    rows.append(ph)
    im = _row(rows, ["gate12", "gate13", "cycles p9", "ref 062 (resampled)"])
    im.save(str(OUT / "r25_cam02_shade.png"))
    print(f"[shade] {OUT}/r25_cam02_shade.png {im.size}")
    return im


def cmd_col(_a=()):
    """cam03 near_column at 100 %: gate12 | gate13 | Cycles p9."""
    OUT.mkdir(parents=True, exist_ok=True)
    box = tuple(int(v * S) for v in NEAR03)
    im = _row([_f(PREV, 3).crop(box), _f(CUR, 3).crop(box), _cyc(3).crop(box)],
              ["gate12", "gate13", "cycles p9"])
    im.save(str(OUT / "r25_cam03_col.png"))
    print(f"[col] {OUT}/r25_cam03_col.png {im.size}")
    return im


def cmd_gate(_a=()):
    """renders/web/gate13_gate.png -- the committed 960 px round sheet (two strips stacked)."""
    a, b = cmd_shade(), cmd_col()
    w = 960
    ims = [i.resize((w, max(1, round(i.height * w / i.width))), Image.LANCZOS) for i in (a, b)]
    out = Image.new("RGB", (w, sum(i.height for i in ims) + 34), (16, 16, 16))
    d = ImageDraw.Draw(out)
    d.text((6, 4), "QA 25 / gate13 - top: cam02 shaded shafts   bottom: cam03 near column",
           fill=(255, 235, 140))
    y = 18
    for i in ims:
        out.paste(i, (0, y))
        y += i.height + 8
    p = WEB / "gate13_gate.png"
    out.save(str(p))
    print(f"[gate] {p} {out.size}")


if __name__ == "__main__":
    CMDS = {"tiles": cmd_tiles, "gate": cmd_gate, "shade": cmd_shade, "col": cmd_col}
    a = sys.argv[1:] or ["tiles"]
    CMDS[a[0]](a[1:])
