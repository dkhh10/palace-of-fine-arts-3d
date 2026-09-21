#!/usr/bin/env python3
"""QA round 26 tile / composite builder (no Blender, no Chrome).

    python3 scripts/qa_r26_tiles.py tiles [st ...]  # 3x2 100 % tiles per station, gate14 (the gate rule)
    python3 scripts/qa_r26_tiles.py hero [x y]      # the 4K hero band at 100 % (right colonnade entablature)
    python3 scripts/qa_r26_tiles.py heroviewer      # the same band in gate14 cam01, 100 % and x2
    python3 scripts/qa_r26_tiles.py gate            # renders/web/gate14_gate.png, the committed 960 px sheet

Tiles are cut at 100 % from the delivered 1920x1080 PNGs (`renders/web/gate14_cam0N.png`) and from the
4K hero (`renders/final/hero_cam01_3840x2160_128spp.png`); they are viewing fixtures, never committed.
"""
import os
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "renders" / "web"
P9 = ROOT / "renders/qa_comparisons/cycles_p9"
HERO4K = ROOT / "renders/final/hero_cam01_3840x2160_128spp.png"
REF105 = None  # resolved lazily: the cam06 aerial reference
CUR, PREV = "gate14", "gate13"
OUT = Path(os.environ.get("PFA_QA_TMP", "/tmp")) / "r26"


def _f(tag, st):
    return Image.open(str(WEB / f"{tag}_cam{st:02d}.png")).convert("RGB")


def _cyc(st):
    return Image.open(str(P9 / f"cam{st:02d}_1080_32spp.png")).convert("RGB")


def _ref105():
    import glob
    g = sorted(glob.glob(str(ROOT / "reference/photos/raw/ref_105_*")))
    return Image.open(g[0]).convert("RGB") if g else None


def cmd_tiles(args):
    OUT.mkdir(parents=True, exist_ok=True)
    for st in [int(a) for a in args] or list(range(1, 7)):
        im = _f(CUR, st)
        for r in range(2):
            for c in range(3):
                im.crop((c * 640, r * 540, (c + 1) * 640, (r + 1) * 540)).save(
                    str(OUT / f"{CUR}_cam{st:02d}_r{r}c{c}.png"))
        print(f"[tiles] cam{st:02d} -> {OUT}/{CUR}_cam{st:02d}_r?c?.png (6 x 640x540 at 100 %)")


def cmd_hero(args):
    """100 % crops of the 4K hero around the reported dark band above the right colonnade entablature."""
    OUT.mkdir(parents=True, exist_ok=True)
    im = Image.open(str(HERO4K)).convert("RGB")
    boxes = {"right_ent": (2400, 700, 3040, 1240), "right_ent_hi": (2600, 820, 2920, 1090),
             "left_ent": (700, 700, 1340, 1240), "mid": (1600, 600, 2240, 1140)}
    if len(args) >= 2:
        x, y = int(args[0]), int(args[1])
        boxes = {f"at_{x}_{y}": (x, y, x + 640, y + 540)}
    for k, b in boxes.items():
        t = im.crop(b)
        t.save(str(OUT / f"hero4k_{k}.png"))
        print(f"[hero] {k} {b} -> {OUT}/hero4k_{k}.png {t.size}")


def cmd_heroviewer(_a=()):
    OUT.mkdir(parents=True, exist_ok=True)
    im = _f(CUR, 1)
    b = (1200, 350, 1520, 620)
    t = im.crop(b)
    t.save(str(OUT / "gate14_cam01_rightent.png"))
    t.resize((t.width * 2, t.height * 2), Image.NEAREST).save(str(OUT / "gate14_cam01_rightent_x2.png"))
    print(f"[heroviewer] {b} -> {OUT}/gate14_cam01_rightent{{,_x2}}.png")


def _row(imgs, labels):
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


CITY = (1290, 20, 1890, 300)          # cam06 city band ("06 city r1c3"), frame px (1920x1080)


def cmd_gate(_a=()):
    """renders/web/gate14_gate.png -- cam06 city band at 100 %: gate13 | gate14 | Cycles | ref 105."""
    OUT.mkdir(parents=True, exist_ok=True)
    ims = [_f(PREV, 6).crop(CITY), _f(CUR, 6).crop(CITY), _cyc(6).crop(CITY)]
    labs = ["gate13 (deploy 13, no tiles)", "gate14 (ENV R3 tiles)", "cycles p9 (pre-R3 refs)"]
    r = _ref105()
    if r is not None:
        ims.append(r.resize((1920, 1080), Image.LANCZOS).crop(CITY))
        labs.append("ref 105 (resampled, not registered)")
    strip = _row(ims[:2] + ims[2:], labs)
    # two rows of two so the sheet stays legible at 960 px
    top = _row(ims[:2], labs[:2])
    bot = _row(ims[2:], labs[2:])
    w = 960
    rs = [i.resize((w, max(1, round(i.height * w / i.width))), Image.LANCZOS) for i in (top, bot)]
    out = Image.new("RGB", (w, sum(i.height for i in rs) + 34), (16, 16, 16))
    d = ImageDraw.Draw(out)
    d.text((6, 4), "QA 26 / gate14 - cam06 city band at 100 %  (top: viewer before | after)",
           fill=(255, 235, 140))
    y = 18
    for i in rs:
        out.paste(i, (0, y))
        y += i.height + 8
    p = WEB / "gate14_gate.png"
    out.save(str(p))
    print(f"[gate] {p} {out.size}  strip {strip.size}")


if __name__ == "__main__":
    CMDS = {"tiles": cmd_tiles, "gate": cmd_gate, "hero": cmd_hero, "heroviewer": cmd_heroviewer}
    a = sys.argv[1:] or ["tiles"]
    CMDS[a[0]](a[1:])
