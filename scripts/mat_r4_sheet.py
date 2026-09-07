"""Round-4 materials comparison sheet: before / after / ref 169 for QA-03-2, -03-4, -03-7, -03-9/-15.

    python3 scripts/mat_r4_sheet.py

Before  = renders/previews/materials/r4b_scene_hero.png (round-3 library on lighting's round-09 rig)
After   = renders/previews/materials/r4m_scene_hero.png (round-4 library, same rig, same exposure -2.3331)
Ref 169 = panel 1 of renders/qa_comparisons/round03_cam01_aligned_vs_ref169.png (the photo warped into the
          render frame by QA), so every crop below is the identical box in all three images.
Writes renders/qa_comparisons/mat_r4_sheet.png.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
BEFORE = ROOT / "renders/previews/materials/r4b_scene_hero.png"
AFTER = ROOT / "renders/previews/materials/r4m_scene_hero.png"
ALIGNED = ROOT / "renders/qa_comparisons/round03_cam01_aligned_vs_ref169.png"
OUT = ROOT / "renders/qa_comparisons/mat_r4_sheet.png"

ROWS = [
    ("QA-03-2 / -03-4  entablature + attic at 1:1", (760, 250, 1230, 460)),
    ("QA-03-2b / -03-9 / -03-15  shafts and capitals at 1:1", (820, 296, 1180, 446)),
    ("QA-03-7  near water", (1050, 940, 1650, 1070)),
]
NUMBERS = [
    "box (1920x1080 Cycles hero, exposure -2.3331, AgX High Contrast)      before -> after        ref 169 (aligned)",
    "attic sunlit   900 222 1020 256   236,188,130 -> 232,194,130    231,187, 95",
    "     hue 32.8 -> 37.7 (ref 40.3)   sat 0.452 -> 0.440 (0.588)   R-B 107 -> 102 (136)   lum 194 -> 198 (190)",
    "attic string   880 214 1040 222   hue 33.7 -> 38.6 (ref 39.3)",
    "entablature    900 262 1020 296   hue 33.1 -> 38.0 (ref 34.0)   lum sd 30.8 -> 32.8 (ref 63.8)",
    "dome cap       920  95 1000 120   hue 29.8 -> 36.6 (ref 42.7)   lum 206 -> 210 (216)   sat 0.283 -> 0.288 (0.288)",
    "shaded attic  1110 225 1150 260   hue 37.2 -> 42.5 (ref 29.5)   -- albedo cannot separate sunlit from shaded",
    "columns mask  x 680-1240 y 280-470   lum 186.4 -> 155.1 (ref 95.8)   hue 29.6 -> 30.1 (24.5)   sat 0.454 -> 0.649 (0.588)",
    "near water    1150 1000 1450 1050   sat 0.463 -> 0.486 (ref 0.270)   hue 204.8 -> 204.8 (192.1)   lum 109 -> 109 (108)",
    "lagoon flank   100  900  400  960   lum 158.2 -> 143.9 (ref 155.2 = 0.93)   sat 0.387 -> 0.450 (0.279)",
    "ripple runs    760 1000 1160 1060   19.3 -> 27.8 px (ref 15.3) -- the metric disagrees with the crop; see notes",
]
PAD, LABEL_H, BG, FG, DIM = 10, 20, (22, 22, 24), (238, 238, 232), (150, 150, 146)
COLS = ["before (round 3 library)", "after (round 4 library)", "ref 169 (aligned by QA)"]


def font(sz):
    for p in ("/System/Library/Fonts/SFNSMono.ttf", "/System/Library/Fonts/Menlo.ttc",
              "/System/Library/Fonts/Supplemental/Courier New.ttf"):
        if Path(p).exists():
            try:
                return ImageFont.truetype(p, sz)
            except Exception:
                pass
    return ImageFont.load_default()


def main():
    before = Image.open(BEFORE).convert("RGB")
    after = Image.open(AFTER).convert("RGB")
    ref = Image.open(ALIGNED).convert("RGB").crop((1920, 0, 3840, 1080))
    f, fs = font(15), font(13)
    tiles = []
    for title, box in ROWS:
        row = [im.crop(box) for im in (before, after, ref)]
        w, h = row[0].size
        scale = min(2.0, 600 / w)
        row = [t.resize((int(w * scale), int(h * scale)), Image.LANCZOS) for t in row]
        tiles.append((title, row))
    tw = max(sum(t.width for t in row) + 2 * PAD for _, row in tiles) + 2 * PAD
    th = sum(row[0].height + LABEL_H * 2 + PAD for _, row in tiles) + PAD
    nh = LABEL_H + len(NUMBERS) * 17 + 2 * PAD
    sheet = Image.new("RGB", (max(tw, 1180), th + nh), BG)
    d = ImageDraw.Draw(sheet)
    y = PAD
    for title, row in tiles:
        d.text((PAD, y), title, font=f, fill=FG)
        y += LABEL_H
        x = PAD
        for t, cl in zip(row, COLS):
            sheet.paste(t, (x, y))
            d.text((x + 2, y + t.height + 2), cl, font=fs, fill=DIM)
            x += t.width + PAD
        y += row[0].height + LABEL_H + PAD
    d.line([(0, y), (sheet.width, y)], fill=(70, 70, 74))
    y += PAD
    for i, ln in enumerate(NUMBERS):
        d.text((PAD, y), ln, font=fs, fill=FG if i == 0 else DIM)
        y += 17
    OUT.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(OUT)
    print("wrote", OUT, sheet.size)


if __name__ == "__main__":
    main()
