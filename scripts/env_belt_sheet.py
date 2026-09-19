"""Phase 8d belt r2 comparison sheet: before (the icosphere belt QA 22 rejected) | after (real far trees) | ref 169.

    python3 scripts/env_belt_sheet.py <before_cam01.png> <after_cam01.png> <before_cam05.png> <after_cam05.png>

960 px wide, so every crop below the full frame is pasted at 100 % (1:1 render pixels) and can be judged for
silhouette at native scale. ref 169 is registered to the cam-01 frame with `qa_r22_probe.REF_XF` (the round-02
align transform) and resampled to the crop's own size, so the three cells in a row show the same subject.
No Blender, no GPU.
"""
import sys, os
from PIL import Image, ImageDraw

REF_XF = (0.7640, 223.2, 0.7667, 97.0)
REF169 = ("/Users/dk/Projects/3d render blender 3rd attempt building/reference/photos/raw/"
          "ref_169_main_Palace_of_Fine_Arts_16794p.jpg")
OUT = ("/Users/dk/Projects/3d render blender 3rd attempt building/.claude/worktrees/phase8d-env/"
       "renders/qa_comparisons/phase8d_belt_r2_960.jpg")

# (label, station, box in 1920x1080 frame px) - the QA-22 backdrop bands, cropped to 300 px of width
ROWS = [
    ("cam01 frame-left band (QA 22 'N')", 1, (60, 505, 360, 695)),
    ("cam01 frame-right band (QA 22 'S')", 1, (1560, 505, 1860, 695)),
    ("cam05 backdrop band", 5, (700, 645, 1000, 835)),
]
CW, GAP, PAD, LH = 300, 15, 10, 15


def ref_crop(box, size):
    sx, dx, sy, dy = REF_XF
    x0, y0, x1, y1 = box
    r = (int(x0 * sx + dx), int(y0 * sy + dy), int(x1 * sx + dx), int(y1 * sy + dy))
    return Image.open(REF169).convert("RGB").crop(r).resize(size, Image.LANCZOS)


def main(b1, a1, b5, a5):
    src = {(1, "before"): Image.open(b1).convert("RGB"), (1, "after"): Image.open(a1).convert("RGB"),
           (5, "before"): Image.open(b5).convert("RGB"), (5, "after"): Image.open(a5).convert("RGB")}
    hero = src[(1, "after")].resize((960 - 2 * PAD, int((960 - 2 * PAD) * 1080 / 1920)), Image.LANCZOS)
    ch = ROWS[0][2][3] - ROWS[0][2][1]
    H = PAD + LH + hero.size[1] + 6 + len(ROWS) * (LH + ch + 6) + PAD
    sheet = Image.new("RGB", (960, H), (22, 22, 24))
    d = ImageDraw.Draw(sheet)
    y = PAD
    d.text((PAD, y), "Phase 8d belt r2 - hall east-face belt: BEFORE (89 icosphere crowns, QA 22 blocker) | "
                     "AFTER (39 far trees) | ref 169.  Crops are 100 %.", fill=(235, 235, 235))
    y += LH
    sheet.paste(hero, (PAD, y))
    d.text((PAD + 4, y + 4), "cam01 after (Eevee preview harness: placeholder sun, AgX Base, -0.8 EV)",
           fill=(250, 250, 250))
    y += hero.size[1] + 6
    for (label, st, box) in ROWS:
        d.text((PAD, y), label, fill=(210, 210, 210))
        y += LH
        for i, kind in enumerate(("before", "after", "ref 169")):
            x = PAD + i * (CW + GAP)
            if kind == "ref 169":
                if st != 1:
                    d.rectangle([x, y, x + CW, y + ch], outline=(70, 70, 70))
                    d.text((x + 8, y + 8), "ref 169 is the cam-01 photograph:", fill=(180, 180, 180))
                    d.text((x + 8, y + 24), "no registered reference at cam05.", fill=(180, 180, 180))
                    continue
                im = ref_crop(box, (CW, ch))
            else:
                im = src[(st, kind)].crop(box)
            sheet.paste(im, (x, y))
            d.text((x + 4, y + 4), kind, fill=(255, 255, 90))
        y += ch + 6
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    sheet.save(OUT, quality=92)
    print("[belt_sheet] wrote", OUT, sheet.size)


if __name__ == "__main__":
    main(*sys.argv[1:5])
