"""Round-11 comparison sheet: before / after / reference for the three items the lead asked to see, with the numbers
burned into every cell. Plain python3 + PIL, no Blender.

    python3 scripts/light_r11_sheet.py [--out renders/previews/lighting/light_r11_sheet.png]

Rows (each is before | after | reference):
  1  QA-04-2  cam03 colonnade shade      round-04 preview | the r11 rig | ref 128
  2  QA-04-1  cam04 rotunda vault, Eevee round-04 preview | the r11 rig | the Cycles frame it must match
  3  QA-04-2  cam01 shaded north attic   round-04 hero    | the r11 rig | ref 169 warped into the render frame
Worktree-safe: every path is derived from ROOT / light_r11_measure.REFERENCE_DIR.
"""
import sys, argparse
from pathlib import Path
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import light_r11_measure as M
import light_r10_measure as m10

ROOT = M.ROOT
P = ROOT / "renders" / "previews" / "lighting"
Q = ROOT / "renders" / "previews" / "qa"
REF128 = M.REFERENCE_DIR / "photos" / "raw" / "ref_128_main_Corinthian_columns_and_rotunda_Palace_of_Fine_Arts.jpg"

CELL_W = 560
PAD, HEAD, CAP = 10, 26, 46
BG, FG, HI = (18, 18, 20), (232, 232, 232), (255, 214, 120)


def crop(path, box=None, size=None, panel=None, panels=1):
    im = Image.open(path).convert("RGB")
    if panel is not None:
        w = im.width // panels
        im = im.crop((panel * w, 0, (panel + 1) * w, im.height))
    if size:
        im = im.resize(size, Image.LANCZOS)
    if box:
        im = im.crop(box)
    return im


def cell(im, title, lines):
    im = im.copy()
    im.thumbnail((CELL_W, 10000), Image.LANCZOS)
    h = HEAD + im.height + CAP + len(lines) * 14
    out = Image.new("RGB", (CELL_W, h), BG)
    out.paste(im, ((CELL_W - im.width) // 2, HEAD))
    d = ImageDraw.Draw(out)
    d.text((6, 7), title, fill=HI)
    y = HEAD + im.height + 8
    for ln in lines:
        d.text((6, y), ln, fill=FG)
        y += 14
    return out


def row(cells, label):
    h = max(c.height for c in cells) + 22
    out = Image.new("RGB", (CELL_W * len(cells) + PAD * (len(cells) + 1), h + PAD), BG)
    ImageDraw.Draw(out).text((PAD, 6), label, fill=HI)
    x = PAD
    for c in cells:
        out.paste(c, (x, 22))
        x += c.width + PAD
    return out


def stack(rows):
    w = max(r.width for r in rows)
    out = Image.new("RGB", (w, sum(r.height for r in rows)), BG)
    y = 0
    for r in rows:
        out.paste(r, (0, y))
        y += r.height
    return out


def f_cam03(p):
    m = M.measure_cam03(p)
    return [f"near shaft lum {m['near_shaft']['lum']:.1f} ({m['shaft_ratio']:.2f} of ref 128's 69.7)",
            f"  hue {m['near_shaft']['hue']:.1f}  sat {m['near_shaft']['sat']:.3f}  std {m['near_shaft']['std']:.1f}",
            f"ground lum {m['ground']['lum']:.1f}  hue {m['ground']['hue']:.1f}  std {m['ground']['std']:.1f}"]


def f_cam04(p):
    m = M.measure_cam04(p)
    return [f"own sky {m['own_sky']['lum']:.1f}   soffit W {m['soffit_w']['lum']:.1f} E {m['soffit_e']['lum']:.1f}",
            f"soffit/sky  W {m['r_soffit_w']:.3f}  E {m['r_soffit_e']:.3f}   (ref 083 0.405)",
            f"coffer/sky  {m['r_coffer']:.3f}   (ref 083 0.437, window 0.35-0.55)"]


def f_hero(p, panel=None):
    m = m10.measure(p, panel=panel)
    a, s, c = m["attic_sunlit"], m["attic_shaded"], m["columns"]
    return [f"sunlit attic lum {a['lum']:.1f} sat {a['sat']:.3f} R-B {a['rb']:.1f} hue {a['hue']:.1f}",
            f"SHADED attic lum {s['lum']:.1f} sat {s['sat']:.3f} hue {s['hue']:.1f}  (ref 115.0 / 0.425 / 29.5)",
            f"columns {c['lum']:.1f} ({c['lum']/95.8:.2f}x ref 95.8) hue {c['hue']:.1f}"]


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--cam03-after", default=str(P / "r11z_SHIP_03e.png"))
    ap.add_argument("--cam04-after", default=str(P / "r11z_SHIP_04e.png"))
    ap.add_argument("--cam04-cycles", default=str(P / "r11z_SHIP_04c.png"))
    ap.add_argument("--hero-after", default=str(P / "r11z_SHIP_01c.png"))
    ap.add_argument("--out", default=str(P / "light_r11_sheet.png"))
    a = ap.parse_args()

    HERO_CROP = (860, 170, 1420, 500)     # the shaded north attic box (1110,225)-(1150,260) with context
    rows = []

    rows.append(row([
        cell(crop(Q / "round04_03_colonnade_walk.png"), "BEFORE  round 04 Eevee", f_cam03(Q / "round04_03_colonnade_walk.png")),
        cell(crop(a.cam03_after), "AFTER  r11 rig, Eevee", f_cam03(a.cam03_after)),
        cell(crop(REF128).crop((0, 900, 1920, 1980)), "REF 128 (note: a MIDDAY photo)",
             ["QA's target 69.7 is measured on a photo with a", "blown sky and no cast shadows: it is not a",
              "golden-hour shade level. See notes section 20."]),
    ], "ITEM 1  QA-04-2  cam03 colonnade shade  (box 0,150-420,720)"))

    rows.append(row([
        cell(crop(Q / "round04_04_rotunda_ceiling.png"), "BEFORE  round 04 Eevee", f_cam04(Q / "round04_04_rotunda_ceiling.png")),
        cell(crop(a.cam04_after), "AFTER  r11 rig, Eevee", f_cam04(a.cam04_after)),
        cell(crop(a.cam04_cycles), "TARGET  the same frame in Cycles", f_cam04(a.cam04_cycles)),
    ], "ITEM 2  QA-04-1 / QA-04-7  cam04 rotunda vault  (Eevee must land within 0.15 of Cycles)"))

    rows.append(row([
        cell(crop(Q / "round04_01_lagoon_hero_cycles.png", size=(1920, 1080), box=HERO_CROP), "BEFORE  round 04 hero, Cycles",
             f_hero(Q / "round04_01_lagoon_hero_cycles.png")),
        cell(crop(a.hero_after, size=(1920, 1080), box=HERO_CROP), "AFTER  r11 rig, Cycles", f_hero(a.hero_after)),
        cell(crop(m10.ALIGNED, panel=1, panels=3, box=HERO_CROP), "REF 169 warped into the render frame",
             f_hero(str(m10.ALIGNED), panel=1)),
    ], "ITEM 3  QA-04-2 hero half + QA-04-5  shaded north attic and the column shafts"))

    sheet = stack(rows)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    sheet.save(a.out)
    print(f"[r11_sheet] {a.out}  {sheet.width}x{sheet.height}")
