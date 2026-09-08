"""Round-5 materials comparison sheet.

    python3 scripts/mat_r5_sheet.py

Three rows, each before / after / reference:

  1. QA-03-15 capitals -- Cycles from the hero station at 8x the hero's angular resolution (400 mm at 768 px against
     the hero's 20 mm at 1920 px), plus the same render downsampled by 8 and blown back up nearest-neighbour, which
     IS the hero at 1:1: a capital is 12 px wide there and that is where "two readable leaf tiers" has to survive.
  2. cam 06 far field -- the 250-450 m canopy and the new city fill, against ref 105's tree masses.
  3. cam 04 coffer ribs -- Eevee at LOD1 (the viewport LOD, where architecture's coffers now render), against
     ref 083's straight-up shot of the saucer.

Writes renders/qa_comparisons/mat_r5_sheet.png.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
REF = Path("/Users/dk/Projects/3d render blender 3rd attempt building/reference/photos")
PREV = ROOT / "renders/previews/materials"
OUT = ROOT / "renders/qa_comparisons/mat_r5_sheet.png"

PAD, LABEL_H, BG, FG, DIM = 10, 19, (22, 22, 24), (238, 238, 232), (150, 150, 146)
PANEL_W = 560


def font(sz):
    for p in ("/System/Library/Fonts/SFNSMono.ttf", "/System/Library/Fonts/Menlo.ttc",
              "/System/Library/Fonts/Supplemental/Courier New.ttf"):
        if Path(p).exists():
            try:
                return ImageFont.truetype(p, sz)
            except Exception:
                pass
    return ImageFont.load_default()


def fit(im, w=PANEL_W, h=None):
    if h is None:
        h = round(im.height * w / im.width)
    return im.resize((w, h), Image.LANCZOS)


def hero_1to1(im, factor=8, show=4):
    """The capital render at the hero's own pixel scale, then nearest-neighbour x`show` so it can be seen."""
    small = im.resize((im.width // factor, im.height // factor), Image.LANCZOS)
    return small.resize((small.width * show, small.height * show), Image.NEAREST)


def load(p, fallback_text=None):
    p = Path(p)
    if p.exists():
        return Image.open(p).convert("RGB")
    im = Image.new("RGB", (PANEL_W, PANEL_W // 2), (40, 30, 30))
    ImageDraw.Draw(im).text((8, 8), fallback_text or f"missing {p.name}", fill=(220, 120, 120), font=font(13))
    return im


def build_rows():
    f13 = font(13)
    cap_b = load(PREV / "r5before_scene_capital.png")
    cap_a = load(PREV / "r5after_scene_capital.png")
    cap_ref = Image.open(REF / "ornament_crops/corinthian_capital_1.jpg").convert("RGB")
    a06_b = load(PREV / "r5before_scene_cam06.png")
    a06_a = load(PREV / "r5after_scene_cam06.png")
    ref105 = Image.open(REF / "raw/ref_105_main_Aerial_view_of_The_Palace_of_Fine_Arts.jpg").convert("RGB")
    ceil_b = load(PREV / "r5before_scene_ceiling.png")
    ceil_a = load(PREV / "r5after_scene_ceiling.png")
    ref083 = Image.open(REF / "ornament_crops/coffered_ceiling_1.jpg").convert("RGB")

    rows = []
    # 1. capital, 8x
    rows.append(("QA-03-15  capital, Cycles from the hero station at 8x hero resolution (400 mm / 768 px)",
                 [("before  round-4 library (cavity attribute inert)", fit(cap_b)),
                  ("after  round-5: `cavity` + ORN_AO/ORN_NORMAL", fit(cap_a)),
                  ("reference  corinthian_capital_1", fit(cap_ref))]))
    # 2. capital at the hero's own scale
    rows.append(("...the same two renders at the HERO's pixel scale (downsampled 8x, then nearest x4): "
                 "a capital is 12 px wide in the hero",
                 [("before  hero 1:1", fit(hero_1to1(cap_b), 380)),
                  ("after  hero 1:1", fit(hero_1to1(cap_a), 380)),
                  ("reference (for shape only)", fit(cap_ref, 380))]))
    # 3. cam06 far field
    rows.append(("cam 06 far field: the 250-450 m canopy (MAT_backdrop_forest) and the city fill "
                 "(new MAT_backdrop_asphalt / _roof_tile)",
                 [("before  bright, yellow canopy; city on placeholders", fit(a06_b)),
                  ("after  round-5 forest + tile/asphalt", fit(a06_a)),
                  ("reference  ref 105 (hazy afternoon aerial)", fit(ref105.crop((1000, 200, 1920, 1040))))]))
    # 4. cam04 ribs
    rows.append(("cam 04 rotunda ceiling, Eevee at LOD1: are the coffer ribs darker than the panels? "
                 "(MAT_plaster_ceiling `Rib Grime` 0.85)",
                 [("before  round-4 library", fit(ceil_b)),
                  ("after  round-5 library", fit(ceil_a)),
                  ("reference  ref 083 / coffered_ceiling_1", fit(ref083))]))
    return rows


def main(numbers):
    rows = build_rows()
    f, fs = font(15), font(13)
    width = PAD + sum(im.width + PAD for _, im in rows[0][1])
    width = max(width, PAD + 3 * (PANEL_W + PAD))
    heights = []
    for title, panels in rows:
        heights.append(LABEL_H + 4 + LABEL_H + max(im.height for _, im in panels) + PAD)
    nh = LABEL_H + 4 + 15 * len(numbers) + PAD
    sheet = Image.new("RGB", (width, PAD + sum(heights) + nh), BG)
    d = ImageDraw.Draw(sheet)
    y = PAD
    for (title, panels), h in zip(rows, heights):
        d.text((PAD, y), title, fill=FG, font=f)
        y += LABEL_H + 4
        x = PAD
        for cap, im in panels:
            d.text((x, y), cap, fill=DIM, font=fs)
            sheet.paste(im, (x, y + LABEL_H))
            d.rectangle([x, y + LABEL_H, x + im.width - 1, y + LABEL_H + im.height - 1], outline=(70, 70, 74))
            x += im.width + PAD
        y += h
    d.text((PAD, y), "measured (same boxes in before and after; see docs/materials_notes.md round 5)", fill=FG, font=f)
    y += LABEL_H + 4
    for line in numbers:
        d.text((PAD, y), line, fill=DIM, font=fs)
        y += 15
    OUT.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(OUT)
    print(f"[mat_r5_sheet] wrote {OUT} ({sheet.width}x{sheet.height})")


if __name__ == "__main__":
    nums_file = ROOT / "renders/qa_comparisons/mat_r5_numbers.txt"
    numbers = nums_file.read_text().splitlines() if nums_file.exists() else ["(no measurements yet)"]
    main(numbers)
