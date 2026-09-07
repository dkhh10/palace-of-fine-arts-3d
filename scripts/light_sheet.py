#!/usr/bin/env python3
"""Comparison-sheet builder for the Lighting & Rendering specialist (plain python3 + PIL, no Blender).

One composite per judgement, per CLAUDE.md's image discipline. Each panel is an image plus a caption block of
measured numbers, so the sheet carries its own evidence and nobody has to re-measure to read it.

    python3 scripts/light_sheet.py OUT.png --panel "caption|line 2|line 3" img.png [--panel ... img.png ...]
                                   [--cols 2] [--width 1800]

Captions are '|'-separated lines; the first line is the panel title.
"""
import argparse, textwrap
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

PAD = 14
BG = (22, 22, 24)
FG = (232, 232, 232)
DIM = (168, 168, 172)


def _font(size):
    for p in ("/System/Library/Fonts/Supplemental/Menlo.ttc", "/System/Library/Fonts/Menlo.ttc",
              "/System/Library/Fonts/SFNSMono.ttf"):
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            continue
    return ImageFont.load_default()


def build(out, panels, cols=2, width=1800):
    cell_w = (width - PAD * (cols + 1)) // cols
    title_f, body_f = _font(17), _font(14)
    rendered = []
    for caption, path in panels:
        im = Image.open(path).convert("RGB")
        im = im.resize((cell_w, round(im.height * cell_w / im.width)), Image.LANCZOS)
        raw = caption.split("|")
        # wrap to the panel width so a long line of numbers never runs off the sheet
        ncols = max(20, int((cell_w - 8) / (body_f.getlength("M") or 8.0)))   # NOT `cols`: that is the grid width
        lines = [raw[0]]
        for ln in raw[1:]:
            lines.extend(textwrap.wrap(ln, ncols) or [""])
        cap_h = PAD + 22 + 19 * (len(lines) - 1) + PAD // 2
        rendered.append((im, lines, cap_h))
    rows = [rendered[i:i + cols] for i in range(0, len(rendered), cols)]
    row_h = [max(im.height + cap_h for im, _, cap_h in r) for r in rows]
    sheet = Image.new("RGB", (width, PAD + sum(h + PAD for h in row_h)), BG)
    d = ImageDraw.Draw(sheet)
    y = PAD
    for r, h in zip(rows, row_h):
        x = PAD
        for im, lines, cap_h in r:
            sheet.paste(im, (x, y))
            ty = y + im.height + PAD // 2
            d.text((x + 2, ty), lines[0], font=title_f, fill=FG)
            for i, ln in enumerate(lines[1:]):
                d.text((x + 2, ty + 22 + 19 * i), ln, font=body_f, fill=DIM)
            x += cell_w + PAD
        y += h + PAD
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    print(f"[light_sheet] {out}  {sheet.size[0]}x{sheet.size[1]}  {len(rendered)} panels")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--panel", nargs=2, action="append", metavar=("CAPTION", "IMAGE"), required=True)
    ap.add_argument("--cols", type=int, default=2)
    ap.add_argument("--width", type=int, default=1800)
    a = ap.parse_args()
    build(a.out, [(c, i) for c, i in a.panel], cols=a.cols, width=a.width)
