"""Round-6 composite for the lead: renders/qa_comparisons/env_r6_sheet.png.

Pure Pillow, no Blender.  Five rows, each `before | after | reference` where a reference exists, with the
measured numbers burned onto every panel:

  1  QA-04-4  hero shoreline           cam 01 crop 500-1400 x 560-760 (QA's shrub band 700 640 1200 720 is inside it)
  2  QA-04-6  hero north-wing band     cam 01 box 1360 480 1860 600, ref 169 raw box 1262 465 1644 557
  3  QA-03-13 cam 05 podium band       the Greek-key course (rows 526-554) and the rotunda body above it
  4  QA-04-13 cam 06 horizon crop      rows 0-220
  5  QA-04-14 cam 02 foreground strip  rows 634-720 (the bottom 12 %)

    python3 scripts/env_sheet_r6.py
"""
import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
MAIN = Path("/Users/dk/Projects/3d render blender 3rd attempt building")
PREV = ROOT / "renders/previews/environment"
QA = MAIN / "renders/previews/qa"
REF169 = MAIN / "reference/photos/raw/ref_169_main_Palace_of_Fine_Arts_16794p.jpg"
OUT = ROOT / "renders/qa_comparisons/env_r6_sheet.png"

W = 820                      # panel width
PAD, LABEL_H, ROW_GAP = 10, 68, 18


def font(size):
    for p in ("/System/Library/Fonts/Supplemental/Arial Bold.ttf",
              "/System/Library/Fonts/Helvetica.ttc"):
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except OSError:
                pass
    return ImageFont.load_default()


F_T, F_L, F_N = font(26), font(17), font(15)


def ref_box(x0, y0, x1, y1):
    """A cam-01 1920x1080 box carried onto the raw ref-169 file by the round-02 align transform."""
    return (int(x0 * 0.7640 + 223.2), int(y0 * 0.7667 + 97.0),
            int(x1 * 0.7640 + 223.2), int(y1 * 0.7667 + 97.0))


def panel(path, box, label, numbers, mark=None):
    im = Image.open(path).convert("RGB").crop(box)
    h = max(1, int(round(W * im.height / im.width)))
    im = im.resize((W, h), Image.LANCZOS)
    out = Image.new("RGB", (W, h + LABEL_H), (18, 18, 20))
    out.paste(im, (0, 0))
    d = ImageDraw.Draw(out)
    if mark:                                    # (x0, y0, x1, y1) in the ORIGINAL image, drawn on the crop
        sx = W / (box[2] - box[0])
        sy = h / (box[3] - box[1])
        d.rectangle([(mark[0] - box[0]) * sx, (mark[1] - box[1]) * sy,
                     (mark[2] - box[0]) * sx, (mark[3] - box[1]) * sy], outline=(255, 70, 70), width=2)
    d.rectangle([0, 0, W - 1, 20], fill=(0, 0, 0))
    d.text((6, 2), label, font=F_L, fill=(255, 214, 120))
    for i, line in enumerate(numbers):
        d.text((6, h + 4 + i * 19), line, font=F_N, fill=(226, 226, 226))
    return out


def row(title, panels):
    ph = max(p.height for p in panels)
    band = Image.new("RGB", (W * len(panels) + PAD * (len(panels) - 1), ph + 30), (18, 18, 20))
    d = ImageDraw.Draw(band)
    d.text((4, 4), title, font=F_T, fill=(255, 255, 255))
    for i, p in enumerate(panels):
        band.paste(p, (i * (W + PAD), 30))
    return band


def main():
    b_hero = QA / "round04_01_lagoon_hero_cycles.png"
    a_hero = PREV / "r6_hero.png"
    rows = []

    # ---- 1. QA-04-4 hero shoreline
    box = (500, 560, 1400, 760)
    rows.append(row("QA-04-4  hero shoreline (cam 01, crop 500 560 1400 760; QA's band 700 640 1200 720 marked)", [
        panel(b_hero, box, "BEFORE  round 04 master (Cycles 128 spp)",
              ["shrub p10 0.50 / p90 1.20 m, tallest inside r 54 m 1.13 m (flat cap)",
               "podium-base box 620 648 1300 684: 22 % hidden, 78 % bare stone",
               "shore band ray-cast: foliage 8.7 %  architecture 68.7 %"], mark=(700, 640, 1200, 720)),
        panel(a_hero, box, "AFTER  round 06 (ENV r6 on the same master, 64 spp)",
              ["shrub p10 0.82 / median 1.57 / p90 2.83 m, tallest 3.59 m, spread 3.44:1",
               "podium base 78 % hidden (QA wants >= 60 %); spacing sd/mean 66 %",
               "shore band ray-cast: foliage 52.8 %  architecture 34.9 %"], mark=(700, 640, 1200, 720)),
        panel(REF169, ref_box(*box), "REFERENCE  ref 169 (round-02 align transform)",
              ["2-4 m mounded shrubs, willow crowns, the base hidden between the piers",
               "shore band lum 107.2  std 51.0  dark<60 17.9 %  sat 0.635",
               "render after: lum 72.9 std 44.9 dark 48.4 % - foliage albedo, see notes"]),
    ]))

    # ---- 2. QA-04-6 hero north-wing band
    box2 = (1300, 440, 1920, 620)
    rows.append(row("QA-04-6  hero frame-right (north) wing band, box 1360 480 1860 600 marked", [
        panel(b_hero, box2, "BEFORE  round 04",
              ["band lum 91.6 = 0.63 of ref (REGRESSION, was 0.77)",
               "ray-cast: foliage 74.6 %  architecture 24.2 %  sky 1.2 %",
               "dark<60 36.2 %"], mark=(1360, 480, 1860, 600)),
        panel(a_hero, box2, "AFTER  round 06",
              ["band lum 146.0 = 1.00 of ref 145.9",
               "ray-cast: foliage 37.8 %  architecture 53.4 %  sky 8.8 %",
               "dark<60 19.7 %  (screen height cap + new frame band)"], mark=(1360, 480, 1860, 600)),
        panel(REF169, ref_box(*box2), "REFERENCE  ref 169",
              ["band lum 145.9  std 71.0  dark<60 16.2 %",
               "the colonnade is clear from about frame x 0.75 rightwards",
               "trees only at the far left of the box and through the bays"]),
    ]))

    # ---- 3. cam 05 band check
    box3 = (280, 430, 1030, 640)
    rows.append(row("QA-03-13 carried  cam 05: the Greek-key course (rows 526-554, marked) must stay legible", [
        panel(QA / "round04_05_south_lawn.png", box3, "BEFORE  round 04",
              ["shore shrubs capped at 1.2 m by radius; band trivially clear",
               "rotunda body (301 27 998 520): foliage 6.5 %",
               "QA's own 'podium band' box 320 566 1000 624 is the shore strip, not the band"],
              mark=(330, 526, 990, 554)),
        panel(PREV / "r6_cam05.png", box3, "AFTER  round 06",
              ["Greek-key course visible over 93.6 % of its length (QA wants >= 60 %)",
               "band box area: architecture 58.9 %, foliage 41.1 % (all tree crowns, no shrub)",
               "rotunda body: foliage 4.5 % - no crown inside the silhouette"],
              mark=(330, 526, 990, 554)),
    ]))

    # ---- 4. cam 06 horizon
    box4 = (0, 0, 1280, 220)
    rows.append(row("QA-04-13  cam 06 horizon crop (rows 0-220)", [
        panel(QA / "round04_06_aerial.png", box4, "BEFORE  round 04",
              ["one Presidio footprint per cluster, one roof material per cluster",
               "ground samples: asphalt 488, gravel 83",
               "crop lum 101.4  std 23.5   dome/far-shore 1.30:1"]),
        panel(PREV / "r6_cam06.png", box4, "AFTER  round 06",
              ["roof colours in the crop 8 (>= 3), distinct roof footprints 13 (>= 2)",
               "ground samples: asphalt 780, gravel 164 (three more Presidio ways)",
               "crop lum 103.0  std 24.8   dome/far-shore 1.27:1 - the rest is mist (lighting)"]),
    ]))

    # ---- 5. cam 02 foreground
    box5 = (0, 600, 1280, 720)
    rows.append(row("QA-04-14  cam 02 foreground strip (bottom 12 % = rows 634-720)", [
        panel(QA / "round04_02_lagoon_ne_threequarter.png", box5, "BEFORE  round 04",
              ["flat water; ray-cast of the strip would resolve to water only",
               "columns carrying a dark silhouette: 48.0 %",
               "strip lum 93.7  std 53.2"]),
        panel(PREV / "r6_cam02.png", box5, "AFTER  round 06",
              ["ray-cast: foliage 35.1 %  rip-rap/stone 14.1 %  water 50.8 %",
               "columns carrying a dark silhouette: 78.8 %",
               "strip lum 60.5  std 41.6 - emergent reeds + up-scaled rip-rap"]),
    ]))

    width = max(r.width for r in rows)
    height = sum(r.height for r in rows) + ROW_GAP * (len(rows) - 1) + 54
    sheet = Image.new("RGB", (width, height), (12, 12, 14))
    d = ImageDraw.Draw(sheet)
    d.text((10, 12), "ENV round 6 - QA-04-4 / -6 / -8 / -13 / -14.  Renders: Cycles from a master built in the "
                     "environment worktree (ENV r6 + ARCH + ORN + LIGHT r10).", font=F_T, fill=(255, 255, 255))
    y = 50
    for r in rows:
        sheet.paste(r, (0, y))
        y += r.height + ROW_GAP
    OUT.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(OUT)
    print(f"[env_sheet_r6] wrote {OUT} ({sheet.width}x{sheet.height})")


if __name__ == "__main__":
    main()
