#!/usr/bin/env python3
"""One composite for the ENV polish round (python3 + numpy + PIL, no Blender).

    python3 scripts/env_sheet.py --out renders/qa_comparisons/env_r3_sheet.png \
        --hero renders/previews/qa/round_env3_01_..._cycles.png \
        --before renders/previews/qa/round02_01_lagoon_hero_cycles.png \
        --cam renders/previews/qa/roundenv3_02_....png ...

Top row: the round-02 hero, this round's hero and the aligned ref-169 panel, with the QA-02-7 / QA-02-6
measurement boxes drawn on all three. Bottom strip: the other cameras. Caption carries the measured numbers so
the sheet and the report cannot drift.
"""
import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import env_measure as M

ROOT = Path(__file__).resolve().parent.parent
FONTS = ["/System/Library/Fonts/Supplemental/Arial Bold.ttf", "/System/Library/Fonts/Supplemental/Arial.ttf",
         "/System/Library/Fonts/Helvetica.ttc"]
BOX_COLOR = {"left_wing": (255, 210, 80), "right_wing": (255, 210, 80),
             "water_flank": (110, 220, 255), "water_near": (110, 220, 255)}


def font(size):
    for f in FONTS:
        if Path(f).exists():
            try:
                return ImageFont.truetype(f, size)
            except Exception:
                pass
    return ImageFont.load_default()


def panel(path, title, w, boxes=True):
    im = Image.open(path).convert("RGB")
    if boxes:
        d = ImageDraw.Draw(im)
        for name, (x0, y0, x1, y1) in M.BOXES.items():
            d.rectangle([x0, y0, x1, y1], outline=BOX_COLOR[name], width=3)
    h = round(im.height * w / im.width)
    im = im.resize((w, h), Image.LANCZOS)
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, w, 26], fill=(0, 0, 0))
    d.text((6, 4), title, font=font(17), fill=(255, 235, 150))
    return im


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--hero", required=True)
    ap.add_argument("--before", required=True)
    ap.add_argument("--cam", action="append", default=[], metavar="TITLE=PATH")
    ap.add_argument("--caption", default="")
    a = ap.parse_args()

    W = 640
    top = [panel(a.before, "BEFORE  round 02 hero", W),
           panel(a.hero, "AFTER  ENV round 3 hero", W),
           panel(M.REF_PANEL, "PHOTO  ref 169 (aligned)", W)]
    cams = []
    for spec in a.cam:
        title, _, path = spec.partition("=")
        if Path(path).exists():
            cams.append(panel(path, title, 480, boxes=False))

    pad = 6
    th = max(p.height for p in top)
    ch = max((p.height for p in cams), default=0)
    cap_h = 118 if a.caption else 0
    Wtot = 3 * W + 4 * pad
    Htot = pad + th + (pad + ch if cams else 0) + pad + cap_h
    sheet = Image.new("RGB", (Wtot, Htot), (16, 16, 18))
    for i, p in enumerate(top):
        sheet.paste(p, (pad + i * (W + pad), pad))
    if cams:
        x = pad
        for p in cams:
            sheet.paste(p, (x, pad + th + pad))
            x += p.width + pad
    if a.caption:
        d = ImageDraw.Draw(sheet)
        y = Htot - cap_h + 4
        for line in a.caption.split("\n"):
            d.text((pad + 2, y), line, font=font(15), fill=(225, 225, 225))
            y += 19
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    print(f"[env_sheet] wrote {out} ({sheet.width}x{sheet.height})")


if __name__ == "__main__":
    main()
