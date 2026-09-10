"""Round-18 comparison sheet (QA-10-2: the rotunda interior fill on the hero).

Three bands, all 1:1 out of the Cycles frames -- only the reference photo is resampled, and it is resampled by
QA's own alignment, not by this script (panel 2 of renders/final/v2/round10_cam01_aligned_vs_ref169.png is
ref 169 already warped into the 1920x1080 hero grid, scale 1.3108 / dx -291.8 / dy -126.6).

  band 1  the great arch, BEFORE (r17 rig) / AFTER (r18 rig) / ref 169 aligned, with the two QA-10-2 boxes drawn
  band 2  the isolation ladder that set the level: f1v1 -> f1v0.35 -> f1v0 -> f0v0, and ref 169 again
  band 3  the acceptance + hold table, measured on the round-18 master

    python3 scripts/light_r18_sheet.py
"""
import sys, os, colorsys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
PREV = ROOT / "renders" / "previews" / "lighting"
QAC = ROOT / "renders" / "qa_comparisons"
ALIGNED = ROOT / "renders" / "final" / "v2" / "round10_cam01_aligned_vs_ref169.png"
OUT = QAC / "light_r18_sheet.png"

ARCH = (770, 290, 1200, 590)        # 430 x 300, 1:1 in the 1920x1080 hero frame
LADDER = (830, 330, 1150, 570)      # 320 x 240
BOXES = {"vault field": ((900, 380, 1010, 430), (120, 255, 120)),
         "jamb": ((872, 400, 892, 480), (255, 120, 255))}

BEFORE = PREV / "r18a_base_01c.png"           # the r17 rig, bordered on the arch (the band is fully rendered)
AFTER = PREV / "r18AFTER_ship_01c.png"        # the r18 rig, full frame


def stats(a, box):
    x0, y0, x1, y1 = box
    m = a[y0:y1, x0:x1].reshape(-1, 3).mean(0)
    r, g, b = m
    h, s, _ = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
    return dict(lum=0.2126 * r + 0.7152 * g + 0.0722 * b, hue=h * 360.0, sat=s, rb=r - b)


def frame(path, box, ref_panel=False):
    if not path.exists():
        im = Image.new("RGB", (box[2] - box[0], box[3] - box[1]), (40, 40, 40))
        ImageDraw.Draw(im).text((12, 12), f"missing\n{path.name}", fill=(255, 120, 120))
        return im
    im = Image.open(path).convert("RGB")
    off = 1920 if ref_panel else 0
    return im.crop((box[0] + off, box[1], box[2] + off, box[3]))


def draw_boxes(im, box):
    d = ImageDraw.Draw(im)
    for name, (b, col) in BOXES.items():
        d.rectangle((b[0] - box[0], b[1] - box[1], b[2] - box[0], b[3] - box[1]), outline=col)
    return im


def build(rows):
    W, H = ARCH[2] - ARCH[0], ARCH[3] - ARCH[1]
    LW, LH = LADDER[2] - LADDER[0], LADDER[3] - LADDER[1]
    head, cap = 26, 34
    width = max(3 * W, 4 * LW)
    height = head + cap + H + cap + LH + cap + 18 * (len(rows) + 1)
    sheet = Image.new("RGB", (width, height), (18, 18, 18))
    d = ImageDraw.Draw(sheet)
    d.text((10, 6), "LIGHT round 18 -- QA-10-2, the rotunda interior fill on the hero (Cycles 1920x1080 / 64 spp, "
                    "1:1 crops of the great arch)", fill=(235, 235, 235))
    y = head
    d.text((10, y + 6), "BEFORE  r17 rig (FILL 10214 W + 8 x VAULT_FILL 3564 W)      |      AFTER  r18 rig "
                        "(FILL 10214 W, VAULT_FILL 0 W)      |      ref 169, aligned by QA", fill=(255, 210, 120))
    y += cap
    sheet.paste(draw_boxes(frame(BEFORE, ARCH), ARCH), (0, y))
    sheet.paste(draw_boxes(frame(AFTER, ARCH), ARCH), (W, y))
    sheet.paste(draw_boxes(frame(ALIGNED, ARCH, ref_panel=True), ARCH), (2 * W, y))
    y += H
    d.text((10, y + 6), "the ladder that set the level -- vault field box lum:  f1 v1 102.9  |  f1 v0.35 79.3  |  "
                        "f1 v0 60.7 (SHIPPED)  |  f0 v0 43.9  |  ref 169 44.9", fill=(255, 210, 120))
    y += cap
    for i, p in enumerate([PREV / "r18a_base_01c.png", PREV / "r18b_mid_01c.png",
                           PREV / "r18a_v0_01c.png", PREV / "r18a_fv0_01c.png"]):
        sheet.paste(frame(p, LADDER), (i * LW, y))
    y += LH
    d.text((10, y + 6), "ROUND-18 ACCEPTANCE AND HOLDS, measured on the round-18 master (9687 objects)",
           fill=(255, 210, 120))
    y += cap
    for line in rows:
        d.text((14, y), line, fill=(220, 220, 220))
        y += 18
    OUT.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(OUT)
    print(f"[r18] wrote {OUT}  ({sheet.size[0]}x{sheet.size[1]})")


if __name__ == "__main__":
    rows = []
    before = np.asarray(Image.open(BEFORE).convert("RGB")).astype(float) if BEFORE.exists() else None
    after = np.asarray(Image.open(AFTER).convert("RGB")).astype(float) if AFTER.exists() else None
    ref = np.asarray(Image.open(ALIGNED).convert("RGB")).astype(float) if ALIGNED.exists() else None
    if before is not None and after is not None:
        rows.append(f"{'box':16s} {'BEFORE lum/hue/sat/R-B':30s} {'AFTER lum/hue/sat/R-B':30s} "
                    f"{'ref 169':24s} window")
        for name, (b, _c) in BOXES.items():
            sb, sa = stats(before, b), stats(after, b)
            sr = stats(ref, (b[0] + 1920, b[1], b[2] + 1920, b[3])) if ref is not None else None
            win = "45-65 lum" if name == "vault field" else "hue 25-60, R-B > 0"
            rr = (f"{sr['lum']:6.1f} {sr['hue']:5.1f} {sr['sat']:.3f} {sr['rb']:+6.1f}" if sr else "")
            rows.append(f"{name:16s} {sb['lum']:6.1f} {sb['hue']:6.1f} {sb['sat']:.3f} {sb['rb']:+7.1f}       "
                        f"{sa['lum']:6.1f} {sa['hue']:6.1f} {sa['sat']:.3f} {sa['rb']:+7.1f}       {rr}  {win}")
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        try:
            import light_r10_measure as m10
            for k in ("attic_sunlit", "attic_shaded", "sky_top", "sky_left", "water_refl"):
                sb, sa = stats(before, m10.BOXES[k]), stats(after, m10.BOXES[k])
                note = "" if before[m10.BOXES[k][1], m10.BOXES[k][0]].sum() > 0 else "(BEFORE outside the border)"
                rows.append(f"{k:16s} {sb['lum']:6.1f} {sb['hue']:6.1f} {sb['sat']:.3f} {sb['rb']:+7.1f}       "
                            f"{sa['lum']:6.1f} {sa['hue']:6.1f} {sa['sat']:.3f} {sa['rb']:+7.1f}       {note}")
        except Exception as e:
            rows.append(f"hero hold boxes unavailable: {e}")
    else:
        rows.append("hero frames missing")
    for extra in (QAC / "light_r18_holds.txt",):
        if extra.exists():
            rows += [l.rstrip() for l in extra.read_text().splitlines() if l.strip()]
    build(rows)
