"""Round-15 comparison sheet (the three Cycles panels are the JPEG re-encodes of the frames the numbers
were measured on; the PNGs were dropped at 8 MB each, the measure stdout is in renders/logs/): four rows (hero cam01 Cycles, cam02, cam03, cam05), three columns
(BEFORE = the merged master as QA round 07 scored it, AFTER = the round-15 rig, REFERENCE photo),
each panel labelled with the boxes the round is judged on. Plain python3 + PIL, no Blender.

    python3 scripts/light_r15_sheet.py
"""
import sys, os
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
MAIN = Path("/Users/dk/Projects/3d render blender 3rd attempt building")   # the reference photos live only there
PREV = ROOT / "renders" / "previews" / "lighting"
REF = MAIN / "reference" / "photos" / "canonical"
OUT = ROOT / "renders" / "qa_comparisons" / "light_r15_sheet.png"

W = 640                       # panel width; rows are 16:9
ROWS = [
    ("cam01 hero (Cycles 64 spp)  near water 144.7/228 -> 107.7/209  flank 188.1/224 -> 145.2/210",
     PREV / "r15b_r14BEFORE_01c.jpg", PREV / "r15a_r15SHIP_01c.jpg",
     REF / "cam_01b_lagoon_hero_goldenhour_ref169.jpg"),
    ("cam02 NNE (Eevee, round-08 station)  shade pier hue 261 -> 260, UNRESOLVED (QA-07-11)",
     PREV / "r15b_r14BEFORE_02e.png", PREV / "r15f_SHIPPED_02e.png",
     REF / "cam_02_ne_shore_threequarter.jpg"),
    ("cam03 colonnade (Eevee)  outer row 0.120 -> 0.189 (>=0.15)   frame under lum 10  18.5 % -> 4.6 %",
     PREV / "r15b_r14BEFORE_03e.png", PREV / "r15f_SHIPPED_03e.png",
     REF / "cam_03_colonnade_walk.jpg"),
    ("cam05 south lawn  water band Eevee 128.5 -> 134.0 (FAIL), the same band in CYCLES 108.4 (PASS 70-117)",
     PREV / "r15b_r14BEFORE_05e.png", PREV / "r15p_r15SHIP_05c.jpg",
     REF / "cam_05_south_lawn.jpg"),
]
COLS = ("BEFORE (round-07 rig)", "AFTER (round-15 rig)", "REFERENCE photo")


def panel(path):
    if not path.exists():
        im = Image.new("RGB", (W, W * 9 // 16), (40, 40, 40))
        ImageDraw.Draw(im).text((12, 12), f"missing\n{path.name}", fill=(255, 120, 120))
        return im
    im = Image.open(path).convert("RGB")
    h = W * 9 // 16
    return im.resize((W, h), Image.LANCZOS)


if __name__ == "__main__":
    ph = W * 9 // 16
    head, cap = 26, 22
    sheet = Image.new("RGB", (3 * W, head + len(ROWS) * (ph + cap)), (18, 18, 18))
    d = ImageDraw.Draw(sheet)
    for c, name in enumerate(COLS):
        d.text((c * W + 10, 7), name, fill=(235, 235, 235))
    y = head
    for title, before, after, ref in ROWS:
        d.text((10, y + 4), title, fill=(255, 210, 120))
        y += cap
        for c, p in enumerate((before, after, ref)):
            sheet.paste(panel(p), (c * W, y))
        y += ph
    OUT.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(OUT)
    print(f"[r15] wrote {OUT}  ({sheet.size[0]}x{sheet.size[1]})")
