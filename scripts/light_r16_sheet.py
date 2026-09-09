"""Round-16 comparison sheet: three rows (hero cam01 Cycles, cam02 NNE Eevee, cam03 colonnade Eevee), three
columns (BEFORE = the master QA round 08 scored, AFTER = the round-16 rig, REFERENCE photo). ONE composite.

r15 review carry 6: the reference directory comes from `common.REFERENCE_DIR` / $PFA_REFERENCE_DIR, not from a
path hard-coded to this machine.

    python3 scripts/light_r16_sheet.py
"""
import sys, os
from pathlib import Path
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

ROOT = Path(__file__).resolve().parents[1]
PREV = ROOT / "renders" / "previews" / "lighting"
QAC = ROOT / "renders" / "qa_comparisons"
# `common` imports bpy, so this plain-python script reads the same environment variable common.REFERENCE_DIR
# reads instead of importing it (r15 review carry 6: no path hard-coded to one machine).
REF = Path(os.environ.get("PFA_REFERENCE_DIR",
                          "/Users/dk/Projects/3d render blender 3rd attempt building/reference")) / "photos" / "canonical"
OUT = QAC / "light_r16_sheet.png"

W = 640
ROWS = [
    ("cam01 hero (Cycles 64 spp)  sunlit attic sat 0.464 -> 0.489, R-B 105.7 -> 111.4 (target 0.53 / 120); "
     "shaded attic hue 34.6 -> 35.0 PASS; reflection R-B +46.0 -> +50.5",
     ROOT / "renders" / "previews" / "qa" / "round08_01_lagoon_hero_cycles.png", PREV / "r16_r16SHIP_01c.jpg",
     REF / "cam_01b_lagoon_hero_goldenhour_ref169.jpg"),
    ("cam02 NNE at the new 27 mm lens (Eevee)  boxes RE-BASED: shade_pier hue 28.1 PASS, frieze 28.8 PASS, "
     "shade_pier_r 301 and the arch soffit 261 FAIL; every ratio 0.22-0.48 (QA-08-2 asked <= 0.8)",
     PREV / "r16_r16BEFORE_02e.png", PREV / "r16_r16SHIP_02e.png",
     REF / "cam_02_ne_shore_threequarter.jpg"),
    ("cam03 colonnade (Eevee)  walk hue 88.9 -> 89.0: two lighting knobs moved it 0.1 deg (QA-08-7); "
     "outer row 0.188 -> 0.186 and frame black 4.5 -> 4.6 % both held",
     PREV / "r16_r16BEFORE_03e.png", PREV / "r16_r16SHIP_03e.png",
     REF / "cam_03_colonnade_walk.jpg"),
]
COLS = ("BEFORE (round-15 rig, QA round 08)", "AFTER (round-16 rig)", "REFERENCE photo")


def panel(path):
    if not path.exists():
        im = Image.new("RGB", (W, W * 9 // 16), (40, 40, 40))
        ImageDraw.Draw(im).text((12, 12), f"missing\n{path.name}", fill=(255, 120, 120))
        return im
    return Image.open(path).convert("RGB").resize((W, W * 9 // 16), Image.LANCZOS)


if __name__ == "__main__":
    ph, head, cap = W * 9 // 16, 26, 34
    sheet = Image.new("RGB", (3 * W, head + len(ROWS) * (ph + cap)), (18, 18, 18))
    d = ImageDraw.Draw(sheet)
    for c, name in enumerate(COLS):
        d.text((c * W + 10, 7), name, fill=(235, 235, 235))
    y = head
    for title, before, after, ref in ROWS:
        d.text((10, y + 3), title[:150], fill=(255, 210, 120))
        if len(title) > 150:
            d.text((10, y + 17), title[150:], fill=(255, 210, 120))
        y += cap
        for c, p in enumerate((before, after, ref)):
            sheet.paste(panel(p), (c * W, y))
        y += ph
    OUT.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(OUT)
    print(f"[r16] wrote {OUT}  ({sheet.size[0]}x{sheet.size[1]})")
