#!/usr/bin/env python3
"""ENV round-5 composite: the QA-03-10 wing band and the QA-03-13 cam-05 silhouette, before | after | reference.

    python3 scripts/env_sheet_r5.py

"Before" is the merged master (ENV round 4) the lead built as renders/logs/lead_build_r4b.log; "after" is the
same build with ENV round 5 linked instead.  Both were rendered by scripts/env_r5_hero.py at Cycles 64 spp from
the same LIGHT r09 / MAT r5 / ORN r4 assets, so the only difference in each pair is ENV.
"""
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
MAIN = Path("/Users/dk/Projects/3d render blender 3rd attempt building")
PREV = ROOT / "renders" / "previews" / "environment"
OUT = ROOT / "renders" / "qa_comparisons" / "env_r5_sheet.png"

BAND = (60, 480, 560, 600)              # QA-03-10 on the 1920x1080 hero
BAND_REF = (269, 465, 651, 557)         # the same band on the raw ref-169 file (QA's mapping)
SIL = (301, 27, 998, 713)               # QA-03-13 cam-05 rotunda silhouette on 1280x720
PANEL_W = 430


def font(sz):
    for p in ("/System/Library/Fonts/SFNSMono.ttf", "/System/Library/Fonts/Supplemental/Arial.ttf"):
        if Path(p).exists():
            try:
                return ImageFont.truetype(p, sz)
            except OSError:
                pass
    return ImageFont.load_default()


def lum(a):
    return 0.2126 * a[:, :, 0] + 0.7152 * a[:, :, 1] + 0.0722 * a[:, :, 2]


def crop(path, box, pad=0):
    im = Image.open(path).convert("RGB")
    x0, y0, x1, y1 = box
    return im.crop((max(0, x0 - pad), max(0, y0 - pad), min(im.width, x1 + pad), min(im.height, y1 + pad)))


def band_stats(path, box):
    a = np.asarray(Image.open(path).convert("RGB")).astype(np.float32)
    x0, y0, x1, y1 = box
    v = lum(a[y0:y1, x0:x1])
    return float(v.mean()), float(100 * (v < 60).mean())


def panel(img, title, lines, w=PANEL_W):
    """One column: the crop scaled to `w`, a title above it and the numbers under it."""
    s = img.resize((w, max(1, round(w * img.height / img.width))), Image.LANCZOS)
    fh, fs = font(15), font(13)
    head, body = 22, 17 * len(lines) + 8
    out = Image.new("RGB", (w, head + s.height + body), (22, 22, 24))
    d = ImageDraw.Draw(out)
    d.text((4, 3), title, font=fh, fill=(245, 240, 225))
    out.paste(s, (0, head))
    for i, ln in enumerate(lines):
        d.text((4, head + s.height + 4 + 17 * i), ln, font=fs,
               fill=(150, 235, 150) if ln.strip().startswith("PASS") else
                    ((240, 150, 130) if ln.strip().startswith("FAIL") else (205, 205, 205)))
    return out


def row(panels, gap=10):
    w = sum(p.width for p in panels) + gap * (len(panels) - 1)
    h = max(p.height for p in panels)
    out = Image.new("RGB", (w, h), (22, 22, 24))
    x = 0
    for p in panels:
        out.paste(p, (x, 0))
        x += p.width + gap
    return out


def main():
    before = PREV / "r5_master_hero.png"          # merged master, ENV round 4
    after = PREV / "r5k_hero.png"                 # same build, ENV round 5 (final)
    ref = MAIN / "reference" / "photos" / "raw" / "ref_169_main_Palace_of_Fine_Arts_16794p.jpg"
    ref_al = PREV / "ref169_aligned_cam01.png"

    b_lum, b_dark = band_stats(before, BAND)
    a_lum, a_dark = band_stats(after, BAND)
    r_lum, r_dark = band_stats(ref, BAND_REF)
    al_lum, al_dark = band_stats(ref_al, BAND)

    def verdict(v):
        ok_raw, ok_al = abs(v / r_lum - 1) <= 0.25, abs(v / al_lum - 1) <= 0.25
        return ("PASS" if (ok_raw and ok_al) else "FAIL") + \
            f" raw {v / r_lum:.2f} / aligned {v / al_lum:.2f}  (0.75-1.25)"

    rows = [row([
        panel(crop(before, BAND, 40), "QA-03-10 wing band - before (ENV r4 master)",
              [f"band lum {b_lum:5.1f}   dark<60 {b_dark:4.1f} %", verdict(b_lum),
               "foliage 39.5 % of box (ray-cast), sky 7.0 %"]),
        panel(crop(after, BAND, 40), "after (ENV r5, same light/materials)",
              [f"band lum {a_lum:5.1f}   dark<60 {a_dark:4.1f} %", verdict(a_lum),
               "foliage 30.5 % of box, sky 11.6 %"]),
        panel(crop(ref, BAND_REF, 32), "ref 169 (raw file, QA's mapped box)",
              [f"band lum {r_lum:5.1f}   dark<60 {r_dark:4.1f} %",
               f"aligned panel: lum {al_lum:5.1f}  dark {al_dark:4.1f} %",
               "the two ref panels differ by 25 % themselves"]),
    ])]

    b5, a5 = PREV / "r5_cam05_before.png", PREV / "r5_cam05_after.png"
    if b5.exists() and a5.exists():
        rows.append(row([
            panel(crop(b5, SIL), "QA-03-13 cam 05 silhouette - before (ENV r4)",
                  ["foliage 6.5 % of the silhouette box", "architecture 60.5 %"]),
            panel(crop(a5, SIL), "after (ENV r5, hand-placed pinned)",
                  ["foliage 6.6 % of the silhouette box", "architecture 60.4 %",
                   "unchanged: the peninsula bed stays put"]),
            panel(crop(after, (60, 300, 1860, 1010)), "ENV r5 hero (context for both bands)",
                  ["cam 01, Cycles 64 spp, 1920x1080", "master rebuilt from the merged assets"]),
        ]))

    gap, pad = 12, 12
    W = max(r.width for r in rows) + 2 * pad
    H = sum(r.height for r in rows) + gap * (len(rows) - 1) + 2 * pad + 26
    sheet = Image.new("RGB", (W, H), (22, 22, 24))
    d = ImageDraw.Draw(sheet)
    d.text((pad, 6), "ENV round 5 - QA-03-10 wing band and QA-03-13 cam-05 silhouette, before | after | reference",
           font=font(17), fill=(245, 240, 225))
    y = 26 + pad
    for r in rows:
        sheet.paste(r, (pad, y))
        y += r.height + gap
    OUT.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(OUT)
    print(f"[env_sheet_r5] {OUT}  {sheet.width}x{sheet.height}")
    print(f"  band before {b_lum:.1f} ({b_lum / r_lum:.2f} raw, {b_lum / al_lum:.2f} aligned) dark {b_dark:.1f} %")
    print(f"  band after  {a_lum:.1f} ({a_lum / r_lum:.2f} raw, {a_lum / al_lum:.2f} aligned) dark {a_dark:.1f} %")
    print(f"  ref raw {r_lum:.1f} dark {r_dark:.1f} % | ref aligned {al_lum:.1f} dark {al_dark:.1f} %")


if __name__ == "__main__":
    main()
