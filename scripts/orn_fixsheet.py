"""One composite sheet for the lead covering the QA round 01 ornament fixes (QA-01-10/11/13/18).

Each row is render | reference crop, labelled with the defect id. Run after orn_build / orn_preview / orn_frieze_test:

    python3 scripts/orn_fixsheet.py
Writes renders/previews/ornament/qa01_ornament_fixes.png (PIL only, no Blender).
"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
MAIN = Path("/Users/dk/Projects/3d render blender 3rd attempt building")
CROPS = MAIN / "reference" / "photos" / "ornament_crops"
PREV = ROOT / "renders" / "previews" / "ornament"
OUT = PREV / "qa01_ornament_fixes.png"

# (label, render file in renders/previews/ornament, reference crop, crop box as fractions or None)
ROWS = [
    ("QA-01-10  Zimm attic panel design A (LOD0 | LOD1)", "fix01_attic_panel_v1.png", "zimm_panel_1.jpg", None),
    ("QA-01-10  design B / C", "fix01_attic_panel_v2.png", "zimm_panel_3.jpg", None),
    ("QA-01-11  rostra band: rosette_band unit arrayed on a frieze_run socket", "frieze_run_rostra_straight.png",
     "rostra_band_1.jpg", (0.0, 0.15, 0.62, 0.75)),
    ("QA-01-11  greek_key unit on ARCH socket 001 (straight) ", "frieze_run_straight.png", "rostra_band_2.jpg", None),
    ("QA-01-13  corner_scroll (paired volutes, 1.5 m)", "fix01_corner_scroll_v1.png", "attic_corner_figure_1.jpg", None),
    ("QA-01-13  maiden pose: arms on the rim, head bowed", "fix01_maiden_v1.png", "weeping_maidens_2.jpg", None),
    ("QA-01-18  the three rotunda capital variants side by side", "fix01_variants_capital_rotunda.png",
     "corinthian_capital_1.jpg", None),
]
W = 1400
ROW_H = 300


def load(path, box=None):
    if not path.exists():
        return None
    im = Image.open(path).convert("RGB")
    if box:
        im = im.crop((int(box[0] * im.width), int(box[1] * im.height), int(box[2] * im.width), int(box[3] * im.height)))
    return im


def fit(im, w, h):
    out = Image.new("RGB", (w, h), (18, 18, 20))
    if im is None:
        ImageDraw.Draw(out).text((10, h // 2), "missing", fill=(200, 90, 90))
        return out
    s = min(w / im.width, h / im.height)
    im = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.LANCZOS)
    out.paste(im, ((w - im.width) // 2, (h - im.height) // 2))
    return out


def main():
    rows = []
    for label, r, c, box in ROWS:
        rows.append((label, load(PREV / r), load(CROPS / c, box)))
    half = W // 2
    sheet = Image.new("RGB", (W, len(rows) * (ROW_H + 22)), (12, 12, 14))
    d = ImageDraw.Draw(sheet)
    y = 0
    for label, a, b in rows:
        d.text((8, y + 5), label + "        [ left: model    right: reference photo ]", fill=(255, 236, 180))
        sheet.paste(fit(a, half - 4, ROW_H), (0, y + 20))
        sheet.paste(fit(b, half - 4, ROW_H), (half, y + 20))
        y += ROW_H + 22
    OUT.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(OUT)
    print(f"[orn_fixsheet] {OUT}  ({sheet.size[0]}x{sheet.size[1]})")


if __name__ == "__main__":
    main()
