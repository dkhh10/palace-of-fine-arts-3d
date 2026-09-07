"""Build a labelled side-by-side comparison sheet from renders / reference crops (materials agent).

    python3 scripts/mat_compare.py out.png "label:path[:x,y,w,h]" ...    # one tile per argument, ';' starts a new row

Crops are given in the SOURCE image's pixel coordinates (origin top-left). Every tile in a row is scaled to the same
height. Plain PIL (system python3), no Blender needed.
"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

TILE_H = 460
PAD = 8
LABEL_H = 22
BG = (24, 24, 26)
FG = (232, 232, 228)


def load(spec):
    parts = spec.split(":")
    label, path = parts[0], parts[1]
    if len(parts) > 2 and "," in parts[2]:
        path = ":".join(parts[1:-1])
        crop = parts[-1]
    else:
        path = ":".join(parts[1:])
        crop = None
    im = Image.open(path).convert("RGB")
    if crop:
        x, y, w, h = [int(v) for v in crop.split(",")]
        im = im.crop((x, y, x + w, y + h))
    scale = TILE_H / im.height
    im = im.resize((max(1, int(im.width * scale)), TILE_H), Image.LANCZOS)
    return label, im


def main():
    out = Path(sys.argv[1])
    rows, cur = [], []
    for spec in sys.argv[2:]:
        if spec == ";":
            rows.append(cur); cur = []
            continue
        cur.append(load(spec))
    if cur:
        rows.append(cur)
    W = max(sum(im.width for _, im in r) + PAD * (len(r) + 1) for r in rows)
    H = sum(TILE_H + LABEL_H + PAD for _ in rows) + PAD
    sheet = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 15)
    except Exception:
        font = ImageFont.load_default()
    y = PAD
    for r in rows:
        x = PAD
        for label, im in r:
            sheet.paste(im, (x, y + LABEL_H))
            d.text((x + 3, y + 3), label, fill=FG, font=font)
            x += im.width + PAD
        y += TILE_H + LABEL_H + PAD
    sheet.save(out)
    print("[mat_compare]", out, sheet.size)


if __name__ == "__main__":
    main()
