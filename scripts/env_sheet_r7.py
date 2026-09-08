"""Round-7 composite for the lead: renders/qa_comparisons/env_r7_sheet.png.

Pure Pillow, no Blender.  Five rows, `before | after | reference`, numbers burned onto every panel:

  1  QA-05-5   hero SOUTH-wing band     cam 01 box 60 480 560 600
  2  QA-05-10  hero shore shrub band    cam 01 box 700 600 1200 740
  3  QA-05-11  cam 03 colonnade walk    the ground, rows 470-720
  4  QA-05-8   cam 06 horizon crop      rows 0-220
  5  site      NE shoreline check       satellite z18 vs the OSM lagoon polygon (env_r7_shoreline.png)

    python3 scripts/env_sheet_r7.py
"""
import json
import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
MAIN = Path("/Users/dk/Projects/3d render blender 3rd attempt building")
PREV = ROOT / "renders/previews/environment"
QA = MAIN / "renders/previews/qa"
REF169 = MAIN / "reference/photos/raw/ref_169_main_Palace_of_Fine_Arts_16794p.jpg"
REF128 = MAIN / "reference/photos/raw/ref_128_main_Corinthian_columns_and_rotunda_Palace_of_Fine_Arts.jpg"
SHORE = ROOT / "renders/qa_comparisons/env_r7_shoreline.png"
NUM = ROOT / "renders/previews/environment/r7_numbers.json"
OUT = ROOT / "renders/qa_comparisons/env_r7_sheet.png"

W = 820
PAD, LABEL_H, ROW_GAP = 10, 150, 18


def font(size):
    for p in ("/System/Library/Fonts/Supplemental/Arial Bold.ttf", "/System/Library/Fonts/Helvetica.ttc"):
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except OSError:
                pass
    return ImageFont.load_default()


F_T, F_L, F_N = font(26), font(17), font(15)
N = json.loads(NUM.read_text()) if NUM.exists() else {}


def n(key, default="-"):
    return N.get(key, default)


def ref_box(x0, y0, x1, y1):
    """A cam-01 1920x1080 box carried onto the raw ref-169 file by the round-02 align transform."""
    return (int(x0 * 0.7640 + 223.2), int(y0 * 0.7667 + 97.0),
            int(x1 * 0.7640 + 223.2), int(y1 * 0.7667 + 97.0))


def panel(path, box, label, numbers, mark=None):
    if not Path(path).exists():
        out = Image.new("RGB", (W, 200 + LABEL_H), (30, 30, 34))
        d = ImageDraw.Draw(out)
        d.text((8, 8), label, font=F_L, fill=(255, 214, 120))
        d.text((8, 40), f"missing: {path}", font=F_N, fill=(220, 120, 120))
        for i, line in enumerate(numbers):
            d.text((6, 204 + i * 19), line, font=F_N, fill=(226, 226, 226))
        return out
    im = Image.open(path).convert("RGB")
    if box:
        im = im.crop(box)
    h = max(1, int(round(W * im.height / im.width)))
    im = im.resize((W, h), Image.LANCZOS)
    out = Image.new("RGB", (W, h + LABEL_H), (18, 18, 20))
    out.paste(im, (0, 0))
    d = ImageDraw.Draw(out)
    if mark and box:
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
    b_hero = QA / "round05_01_lagoon_hero_cycles.png"
    a_hero = PREV / "r7_hero.png"
    rows = []

    # ---- 1. QA-05-5 south wing band
    box = (0, 430, 640, 660)
    rows.append(row("QA-05-5  hero SOUTH (frame-left) wing band, box 60 480 560 600 marked", [
        panel(b_hero, box, "BEFORE  QA round 05 master (Cycles 128 spp)", [
            "band lum 86.0  med 52.0  std 63.9  dark<60 55.9 %",
            f"ray-cast  {n('b_band_cast')}",
            f"sun reach {n('b_band_sun')}"], mark=(60, 480, 560, 600)),
        panel(a_hero, box, "AFTER  ENV r7 (master built in the worktree, Cycles 64 spp)", [
            f"band lum {n('a_band_lum')}",
            f"ray-cast  {n('a_band_cast')}",
            f"sun reach {n('a_band_sun')}"], mark=(60, 480, 560, 600)),
        panel(REF169, ref_box(*box), "REFERENCE  ref 169 (round-02 align transform)", [
            "aligned band lum 113.3  med 102.2  std 66.6  dark<60 26.2 %",
            "south face bears 47.2 deg, so at az 118.5 the sun rakes it at cos 0.32",
            "(north wing 0.99) - and 118.5 IS this photo's own sun (solar position",
            "for 2020-02-01 at el 7 = 118.3 deg).  Fit lum = A + k cos on both bands:",
            "this build A 61.7 k 76.5   ref 169 A 97.9 k 48.4 -> it is the sky fill,",
            "36 lum short.  A 62 -> 79 alone clears QA's >= 103.  LIGHTING (= QA-05-1)."]),
    ]))

    # ---- 2. QA-05-10 shore band
    box2 = (560, 540, 1340, 780)
    rows.append(row("QA-05-10  hero shore shrub band, box 700 600 1200 740 marked", [
        panel(b_hero, box2, "BEFORE  QA round 05", [
            f"band lum {n('b_shore_lum', '71.7')}   (QA: 0.63 of the photo's 114)",
            f"{n('b_shore_hue')}",
            f"ray-cast  {n('b_shore_cast')}",
            f"sun reach {n('b_shore_sun')}"], mark=(700, 600, 1200, 740)),
        panel(a_hero, box2, "AFTER  ENV r7", [
            f"band lum {n('a_shore_lum')}",
            f"{n('a_shore_hue')}",
            f"ray-cast  {n('a_shore_cast')}",
            f"sun reach {n('a_shore_sun')}"], mark=(700, 600, 1200, 740)),
        panel(REF169, ref_box(*box2), "REFERENCE  ref 169", [
            "aligned crop lum 115.6  sat 0.663  hue 40.7 (build 71.7 / 0.769 / 42.9)",
            "deciles ratio ref/build 1.89 1.86 1.84 1.81 1.77 1.75 1.68 1.59 1.46:",
            "a uniform level deficit, NOT an occlusion - nothing in the band is black.",
            "hue already in QA's 40-60 window, saturation 16 % high.  MATERIALS +",
            "LIGHTING (same ambient/direct split as QA-05-5).  Note: closing the belt",
            "further over the pale bank would make this number WORSE, not better.",
            f"{n('shore_note', '')}"]),
    ]))

    # ---- 3. QA-05-11 cam 03 ground
    box3 = (0, 440, 1280, 720)
    rows.append(row("QA-05-11  cam 03 colonnade walk - the ground (rows 470-720)", [
        panel(QA / "round05_03_colonnade_walk.png", box3, "BEFORE  QA round 05", [
            f"ground std {n('b_c03_std', '15.7')}   ground/sunlit {n('b_c03_ratio', '0.197')}",
            f"ray-cast  {n('b_c03_cast')}",
            "one flat gravel plane: no joints, no planting edge"]),
        panel(PREV / "r7_cam03.png", box3, "AFTER  ENV r7", [
            f"ground std {n('a_c03_std')}   ground/sunlit {n('a_c03_ratio')}",
            f"ray-cast  {n('a_c03_cast')}",
            f"{n('c03_note', '')}"]),
        panel(REF128, (0, 1400, 1920, 2560), "REFERENCE  ref 128 (lower half: the walk and its planting)", [
            "gravel/paved walk with joints and pale sunlit patches, a continuous planting",
            "edge at the column bases and shrub masses between the columns",
            "acceptance: ground std >= 12 at a level within 30 % of the shade window"]),
    ]))

    # ---- 4. QA-05-8 cam 06 horizon
    box4 = (0, 0, 1280, 220)
    rows.append(row("QA-05-8  cam 06 horizon crop (rows 0-220)", [
        panel(QA / "round05_06_aerial.png", box4, "BEFORE  QA round 05", [
            f"crop lum {n('b_c06_lum')}   dark street lines found {n('b_c06_lines', '0')}",
            f"ray-cast  {n('b_c06_cast')}",
            "no road grid, no block structure: one beige plane"]),
        panel(PREV / "r7_cam06.png", box4, "AFTER  ENV r7", [
            f"crop lum {n('a_c06_lum')}   dark street lines found {n('a_c06_lines')}",
            f"ray-cast  {n('a_c06_cast')}",
            f"{n('c06_note', '')}"]),
    ]))

    # ---- 5. shoreline check
    rows.append(row("Site check (decisions.md QA-04-11 flag): is the OSM NE shoreline short?", [
        panel(SHORE, None, "satellite_z18 vs site_local.json lagoon0", [
            "the polygon follows the visible water edge along the whole NE arm",
            "the ref-062 fitted station world (-73, 55) is over open water on the tile too",
            "FINDING: OSM is not short - polygon unchanged (extent world X -135..107, Y -20..118)"]),
    ]))

    width = max(r.width for r in rows)
    height = sum(r.height for r in rows) + ROW_GAP * (len(rows) - 1) + 54
    sheet = Image.new("RGB", (width, height), (12, 12, 14))
    d = ImageDraw.Draw(sheet)
    d.text((10, 12), "ENV round 7 - QA-05-5 / -8 / -10 / -11 + the NE shoreline flag.  AFTER renders: Cycles from a "
                     "master built in the environment worktree (ENV r7 + ARCH + ORN + MAT r6 + LIGHT r11).",
           font=F_T, fill=(255, 255, 255))
    y = 50
    for r in rows:
        sheet.paste(r, (0, y))
        y += r.height + ROW_GAP
    OUT.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(OUT)
    print(f"[env_sheet_r7] wrote {OUT} ({sheet.width}x{sheet.height})")


if __name__ == "__main__":
    main()
