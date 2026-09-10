"""Round-17 comparison sheet. Unlike rounds 15-16 this one is built from 100 % TILES, not from downscaled frames:
both round-17 defects (a coffered soffit's chroma, a fluted shaft's modulation) live at a scale a 640 px panel
destroys, and CLAUDE.md's gate check now requires the tile pass anyway.

Four tile rows -- cam02 arch soffit, cam02 camera-facing shafts, cam03 near column, cam03 gallery walk -- each
BEFORE (the round-16 rig on ARCH r8's geometry) / AFTER (the round-17 rig) / REFERENCE, plus a fifth row holding
the hero hold table as text. Every crop is 1:1 out of the Cycles frame and only the reference photo is resampled.

    python3 scripts/light_r17_sheet.py
"""
import sys, os
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
PREV = ROOT / "renders" / "previews" / "lighting"
QAC = ROOT / "renders" / "qa_comparisons"
REF = Path(os.environ.get("PFA_REFERENCE_DIR",
                          "/Users/dk/Projects/3d render blender 3rd attempt building/reference")) / "photos" / "raw"
OUT = QAC / "light_r17_sheet.png"

TW, TH = 420, 300          # tile panel size; crops are pasted 1:1 and centred, never resampled
BEFORE = PREV / "r17BEFORE_BEFORE_{cam}c.png"
AFTER = PREV / "r17AFTER_AFTER_{cam}c.png"

ROWS = [
    ("cam02 arch soffit (Cycles 64 spp)  soffit_l / soffit_r saturation 0.413 / 0.378 -> 0.340 / 0.317 (window "
     "<= 0.35), hue 34.7 / 32.3 -> 36.3 / 33.9 (25-60), coffer rib-field 112 / 116 -> 111 / 115 lum",
     "02", (470, 250, 890, 550), "ref_062*"),
    ("cam02 camera-facing shafts (Cycles)  NOT fixed and not one knob: shade_pier 269.5 -> 269.8, shade_pier_r "
     "234.6 -> 235.3. LIGHT_shade_fill is a single az-25 el-2 sun lamp at colour (0.03, 0.02, 1.00) - see 27.3",
     "02", (860, 230, 1280, 530), "ref_062*"),
    ("cam03 near column ARCH_colonnade_south_column_028 (Cycles)  mean 3.3 -> 34.9 lum, p95 20 -> 89, flute "
     "ridge-floor 12.0 -> 33.2, ratio to the sunlit rotunda 0.029 -> 0.305 against ref 128's own 0.292",
     "03", (860, 200, 1280, 500), "ref_128*"),
    ("cam03 gallery walk (Cycles)  frame under 10 lum 39.9 % -> 6.6 %, outer row 0.030 -> 0.289 of sunlit, "
     "shaft_flank 0.510 -> 0.631 (QA-06: 0.30-0.70); walk hue 249.7 -> 16.5 but at sat 0.068, i.e. grey",
     "03", (380, 380, 800, 680), "ref_128*"),
]

HERO = [
    "HERO HOLDS (cam01, Cycles 1920x1080 / 64 spp, the same box set as docs/lighting_notes.md 26.6)",
]


def crop(path, box):
    if not path.exists():
        im = Image.new("RGB", (TW, TH), (40, 40, 40))
        ImageDraw.Draw(im).text((12, 12), f"missing\n{path.name}", fill=(255, 120, 120))
        return im
    return Image.open(path).convert("RGB").crop(box)


def ref_panel(pattern):
    hits = sorted(REF.glob(pattern))
    if not hits:
        im = Image.new("RGB", (TW, TH), (40, 40, 40))
        ImageDraw.Draw(im).text((12, 12), f"reference not found\n{pattern}", fill=(255, 120, 120))
        return im
    im = Image.open(hits[0]).convert("RGB")
    return im.resize((TW, int(TW * im.size[1] / im.size[0])), Image.LANCZOS).crop((0, 0, TW, TH))


def build(hero_rows):
    head, cap = 26, 34
    body = head + len(ROWS) * (TH + cap)
    foot = cap + 18 * (len(hero_rows) + 1)
    sheet = Image.new("RGB", (3 * TW, body + foot), (18, 18, 18))
    d = ImageDraw.Draw(sheet)
    for c, name in enumerate(("BEFORE  round-16 rig on ARCH r8 geometry", "AFTER  round-17 rig", "REFERENCE photo")):
        d.text((c * TW + 10, 7), name, fill=(235, 235, 235))
    y = head
    for title, cam, box, refpat in ROWS:
        for i in range(0, len(title), 130):
            d.text((10, y + 3 + 15 * (i // 130)), title[i:i + 130], fill=(255, 210, 120))
        y += cap
        sheet.paste(crop(Path(str(BEFORE).format(cam=cam)), box), (0, y))
        sheet.paste(crop(Path(str(AFTER).format(cam=cam)), box), (TW, y))
        sheet.paste(ref_panel(refpat), (2 * TW, y))
        y += TH
    d.text((10, y + 6), HERO[0], fill=(255, 210, 120))
    y += cap
    for line in hero_rows:
        d.text((14, y), line, fill=(220, 220, 220))
        y += 18
    OUT.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(OUT)
    print(f"[r17] wrote {OUT}  ({sheet.size[0]}x{sheet.size[1]})")


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import light_r17_measure as m
    rows = []
    b = m.measure(str(PREV / "r17BEFORE_BEFORE_01c.png"))
    a = m.measure(str(PREV / "r17AFTER_AFTER_01c.png"))
    if b and a:
        rows.append(f"{'box':16s} {'BEFORE lum/hue/sat/R-B':32s} {'AFTER lum/hue/sat/R-B':32s} window")
        WIN = {"sunlit_attic": "lum 178-201, sat 0.53-0.62 (capped ~0.49, 26.2)",
               "shaded_attic": "hue 23.5-35.5, sat <= 0.50, lum 103.5-126.5",
               "water_refl": "R-B >= +35, hue 25-45", "sky_top": "must not move", "sky_left": "must not move",
               "columns": "hue 24.5 +- 4 (FAIL before and after)",
               "south_wing": "colonnade, gallery fill's only hero effect",
               "north_wing": "colonnade, gallery fill's only hero effect"}
        for k, w in WIN.items():
            sb, sa = b[1].get(k), a[1].get(k)
            if not sb or not sa:
                continue
            rows.append(f"{k:16s} {sb['lum']:6.1f} {sb['hue']:6.1f} {sb['sat']:.3f} {sb['rb']:+7.1f}      "
                        f"{sa['lum']:6.1f} {sa['hue']:6.1f} {sa['sat']:.3f} {sa['rb']:+7.1f}      {w}")
    else:
        rows.append("hero frames missing")
    build(rows)
