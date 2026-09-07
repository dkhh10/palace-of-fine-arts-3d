#!/usr/bin/env python3
"""ENV round-4 comparison sheet: renders/qa_comparisons/env_r4_sheet.png.

    python3 scripts/env_sheet_r4.py

Three rows (before | after | reference) for the three defects that have a picture:
  QA-03-11  cam 06 aerial          round 03 master panel | ENV round 4 preview | ref 105 aerial
  QA-03-10  cam 01 left-wing band  round 03 master panel | ENV round 4 preview | aligned ref 169
  QA-03-13  cam 05 rotunda         round 03 master panel | ENV round 4 preview | ref 063
Each row carries the measured numbers.  The "before" panels come from the lead's round-03 comparison sheets, which
are master renders with the shipping light rig; the "after" panels are ENV previews with the placeholder sun, so
the rows are compared on structure and coverage, not on absolute luminance (which the numbers state separately).
"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
MAIN = Path("/Users/dk/Projects/3d render blender 3rd attempt building")
QA = MAIN / "renders" / "qa_comparisons"
PREV = ROOT / "renders" / "previews" / "environment"
REF = MAIN / "reference" / "photos" / "canonical"

CW, CH = 620, 349          # cell size (16:9)
PAD, HEAD, CAP = 10, 30, 74

ROWS = [
    dict(title="QA-03-11  cam 06 aerial - the far field past 150 m",
         before=(QA / "round03_cam06.png", (0, 0, 1280, 720)),
         after=(sorted(PREV.glob("*_06_aerial_r4g.png"))[-1], None),
         ref=(REF / "cam_06_aerial.jpg", None),
         caption=["horizon crop (0 0 1280 220) luminance std-dev  15.5 -> 30.5   (structure, not a flat plane)",
                  "rotunda / far-shore contrast  1.15:1 -> 1.45:1   (QA wants >= 1.5:1; the rest is the mist)",
                  "building volumes resolved in the crop  ~5 -> 37 objects (25 wall + 12 roof; fill runs carry 4 lots each)",
                  "ground in the crop: lawn / dry grass / soil / gravel walk / asphalt road, 13 materials, paths readable"]),
    dict(title="QA-03-10  cam 01 hero, left (south) colonnade band  x 60-560  y 480-600",
         before=(QA / "round03_cam01.png", (60, 400, 700, 760)),
         after=(sorted(PREV.glob("*_01_lagoon_hero_r4g.png"))[-1], (60, 400, 700, 760)),
         ref=(PREV / "ref169_aligned_cam01.png", (60, 400, 700, 760)),
         caption=["the eucalyptus that stood in front of the wing at frame x 0.11-0.18 moved 30 m to (88.7, 18.8),",
                  "behind the colonnade arc; the two user-image cypress spires went 26/24 m -> 16/13 m",
                  "band coverage by ray-cast: foliage 43.4 % -> 40.0 %, architecture 56.6 % -> 60.0 %",
                  "luminance is set by the light rig, not by ENV: verify the 0.63 ratio in master after the merge"]),
    dict(title="QA-03-13  cam 05 south lawn - crowns inside the rotunda silhouette",
         before=(QA / "round03_cam05.png", (0, 0, 1280, 720)),
         after=(sorted(PREV.glob("*_05_south_lawn_r4g.png"))[-1], None),
         ref=(REF / "cam_05_south_lawn.jpg", None),
         caption=["no crown inside the rotunda silhouette: foliage in the silhouette box 5.1 %, architecture 73.7 %",
                  "podium / Greek-key band box: 81.4 % architecture visible   (QA wants >= 60 % of the rotunda width)",
                  "QA-03-14 shore shrubs: size spread 1.5:1 -> 2.51:1, spacing sd/mean 62 % (>= 40 %),",
                  "tallest shrub inside the rostra radius 1.87 m -> 1.13 m (<= 1.2 m)"]),
    dict(title="QA-03-9 (ENV share)  cam 03 colonnade walk   +   carried: the hall aperture through the hero arch",
         before=(QA / "round03_cam03.png", (0, 225, 630, 1080)),
         after=(sorted(PREV.glob("*_03_colonnade_walk_r4g.png"))[-1], (0, 225, 630, 1080)),
         ref=(sorted(PREV.glob("*_01_lagoon_hero_r4g.png"))[-1], (800, 330, 1140, 660)),
         caption=["ground bands: gravel walk (colonnade +2 m) | soil planting bed (+2 to +5.5 m) | 1.5 m soil verge along every path | lawn",
                  "no shrub within 17 m of cam 03 (the black near cards); colonnade foundation planting moved to the pale / dry shrub families",
                  "crop (0 150 420 720): pixels below lum 12  29.8 % -> 0.1 %, luminance std-dev 14.7 -> 21.4 (both also move with the light rig)",
                  "third panel is NOT a reference: it is the hero arch in the round-4 preview - the hall aperture now has a backing slab + reveal, no hole"]),
]


def font(sz, bold=False):
    for p in ("/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else
              "/System/Library/Fonts/Supplemental/Arial.ttf",
              "/System/Library/Fonts/Helvetica.ttc"):
        try:
            return ImageFont.truetype(p, sz)
        except Exception:
            continue
    return ImageFont.load_default()


def cell(spec):
    path, box = spec
    im = Image.open(path).convert("RGB")
    if "round03_cam" in str(path):           # the lead's sheets are render | ref | ref, take panel 0
        im = im.crop((0, 0, im.width // 3, im.height))
    if box:
        sx, sy = im.width / 1920.0, im.height / 1080.0
        im = im.crop((int(box[0] * sx), int(box[1] * sy), int(box[2] * sx), int(box[3] * sy)))
    return im.resize((CW, CH), Image.LANCZOS)


def main():
    W = PAD + 3 * (CW + PAD)
    H = PAD + len(ROWS) * (HEAD + CH + CAP + PAD)
    sheet = Image.new("RGB", (W, H), (18, 18, 20))
    d = ImageDraw.Draw(sheet)
    f_t, f_h, f_c = font(19, True), font(15, True), font(14)
    y = PAD
    for row in ROWS:
        d.text((PAD, y + 5), row["title"], font=f_t, fill=(255, 214, 130))
        y += HEAD
        for k, (key, label) in enumerate((("before", "BEFORE  round 03"), ("after", "AFTER  ENV round 4"),
                                          ("ref", "REFERENCE"))):
            x = PAD + k * (CW + PAD)
            try:
                sheet.paste(cell(row[key]), (x, y))
            except Exception as e:
                d.text((x + 10, y + 10), f"missing: {e}", font=f_c, fill=(255, 90, 90))
            d.rectangle((x, y, x + CW - 1, y + 18), fill=(0, 0, 0))
            d.text((x + 6, y + 2), label, font=f_h, fill=(180, 220, 255))
        y += CH + 4
        for line in row["caption"]:
            d.text((PAD + 2, y), line, font=f_c, fill=(225, 225, 225))
            y += 17
        y += PAD
    out = ROOT / "renders" / "qa_comparisons" / "env_r4_sheet.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    print("wrote", out, sheet.size)


if __name__ == "__main__":
    main()
