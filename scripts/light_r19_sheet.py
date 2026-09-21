#!/usr/bin/env python3
"""Round-19 composite sheet: the cam02 shaded shafts BEFORE / AFTER / photo, and the hero attic BEFORE / AFTER.

No Blender.  Reads frames already on disk and writes ONE 960 px JPEG, which is the only image the round
asks anybody to look at (CLAUDE.md's image discipline).  The crops are the measurement boxes themselves --
`light_r17_measure.BOXES` for the render frames, resampled into the fixture's own 1280x720 exactly as
`light_r14_measure.load` does it -- so what the eye is shown and what the table reports are the same pixels.

The photo panel is ref_062 resampled into the SAME cam02 fixture.  That is not the same stone (062 is a
different camera at a different framing; see the docstring of scripts/p8b_c_cielab.py, which measures the
resampled photo at b* +14.10 / +13.22 / +7.49 / +10.50 against a published column of +10.89 / +10.99 /
+5.33 / +11.07 that nothing in the tree can reproduce).  It is in the sheet as the COLOUR reference for
shaded rotunda stone at this sun, not as a geometry match, and the caption says so.

    python3 scripts/light_r19_sheet.py --before <cam02 BEFORE> --after <cam02 AFTER> \
        --hero-before <cam01 BEFORE> --hero-after <cam01 AFTER> --out <sheet.jpg>
"""
import argparse
import sys
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import light_r14_measure as m14  # noqa: E402
import light_r17_measure as m17  # noqa: E402

MAIN = Path("/Users/dk/Projects/3d render blender 3rd attempt building")
PHOTO = MAIN / "reference/photos/raw/ref_062_rotunda_Palace_of_Fine_Arts_View_of_Rotunda_from_north_eas.jpg"
SHAFTS = ("shade_pier", "shade_arch", "shade_pier_r", "shade_frieze")   # cam02, left to right + the control
HERO = ("shaded_attic", "columns")                                      # cam01, the boxes the hold is read on
PAD, LABEL_H, TITLE_H = 6, 16, 22


def crops(path, cam, boxes, height):
    """The fixture's own boxes, cropped from the frame resampled to the fixture size, each scaled to `height`."""
    import numpy as np
    a = m14.load(str(path), m17.BOXES[cam]["size"])
    out = []
    for k in boxes:
        x0, y0, x1, y1 = m17.BOXES[cam]["boxes"][k]
        im = Image.fromarray(np.asarray(a[y0:y1, x0:x1], dtype="uint8"))
        w = max(1, int(round(im.width * height / im.height)))
        out.append((k, im.resize((w, height), Image.LANCZOS)))
    return out


def row(panels, y, sheet, d, title):
    x = PAD
    d.text((PAD, y), title, fill=(230, 230, 230))
    y += TITLE_H
    for k, im in panels:
        sheet.paste(im, (x, y))
        d.text((x + 2, y + im.height + 2), k, fill=(200, 200, 200))
        x += im.width + PAD
    return y + panels[0][1].height + LABEL_H + PAD


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--before", required=True)
    ap.add_argument("--after", required=True)
    ap.add_argument("--hero-before", required=True)
    ap.add_argument("--hero-after", required=True)
    ap.add_argument("--after-label", default="AFTER")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    h = 150
    rows = [
        (f"cam02 BEFORE (shipped world)", crops(a.before, "02", SHAFTS, h)),
        (f"cam02 {a.after_label}", crops(a.after, "02", SHAFTS, h)),
        ("ref 062 resampled into the cam02 fixture -- COLOUR reference only, not the same stone",
         crops(PHOTO, "02", SHAFTS, h)),
        ("cam01 hero BEFORE / AFTER (the hold)",
         crops(a.hero_before, "01", HERO, h) + crops(a.hero_after, "01", HERO, h)),
    ]
    width = max(sum(im.width + PAD for _, im in panels) + PAD for _, panels in rows)
    height = sum(h + TITLE_H + LABEL_H + PAD for _ in rows) + PAD
    sheet = Image.new("RGB", (width, height), (20, 20, 22))
    d = ImageDraw.Draw(sheet)
    y = PAD
    for title, panels in rows:
        y = row(panels, y, sheet, d, title)
    if sheet.width > 960:
        sheet = sheet.resize((960, int(round(sheet.height * 960 / sheet.width))), Image.LANCZOS)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    sheet.save(a.out, quality=90)
    print(f"[r19] sheet -> {a.out}  {sheet.width}x{sheet.height}")


main()
