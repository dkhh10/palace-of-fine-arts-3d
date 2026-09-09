"""Round-12 comparison sheet: before / after / reference for the round's three items, numbers burned into every cell.
Plain python3 + PIL, no Blender.

    python3 scripts/light_r12_sheet.py --cam03-after ... --hero-after ... --cam04-cycles ... --cam04-eevee ...

Rows (each is before | after | reference):
  1  QA-05-1  cam03 colonnade shade   round-05 preview | the r12 rig | ref 128, with the RATIO test stated
  2  QA-05-1  hero shaded attic       round-05 hero    | the r12 rig | ref 169 warped into the render frame
  3  QA-05-3  cam04 vault, Cycles     round-05 Cycles  | the r12 rig | ref 083
"""
import sys, argparse
from pathlib import Path
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import light_r12_measure as M
import light_r11_measure as m11
import light_r10_measure as m10

ROOT = M.ROOT
P = ROOT / "renders" / "previews" / "lighting"
Q = ROOT / "renders" / "previews" / "qa"
REF = m11.REFERENCE_DIR / "photos" / "raw"
REF128 = REF / "ref_128_main_Corinthian_columns_and_rotunda_Palace_of_Fine_Arts.jpg"
REF083 = REF / "ref_083_rotunda_San_Francisco_40326830584.jpg"

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
    n = m["near_shaft"]
    return [f"near shaft lum {n['lum']:.1f}  hue {n['hue']:.1f}  sat {n['sat']:.3f}",
            f"sunlit rotunda in frame {m['sunlit_rotunda']['lum']:.1f}",
            f"SHADE / SUNLIT {m['shade_ratio']:.3f}   window 0.30-0.70 (ref 169 0.607)",
            f"ground / sunlit {m['ground_ratio']:.3f}"]


def f_cam04(p):
    m = m11.measure_cam04(p)
    q = M.quarter_ratio(p)
    return [f"own sky {m['own_sky']['lum']:.1f}   soffit W {m['soffit_w']['lum']:.1f} E {m['soffit_e']['lum']:.1f}",
            f"soffit/sky  W {m['r_soffit_w']:.3f}  E {m['r_soffit_e']:.3f}  (ref 083 0.405)",
            f"COFFER/sky  {m['r_coffer']:.3f}   window 0.35-0.55 (ref 083 0.437)",
            f"dark/light quarter {q['ratio']:.3f}   test >= 0.20 (ref 083 0.265)"]


def f_hero(p, panel=None):
    m = m10.measure(p, panel=panel)
    a, s, c = m["attic_sunlit"], m["attic_shaded"], m["columns"]
    return [f"SHADED attic lum {s['lum']:.1f} hue {s['hue']:.1f} sat {s['sat']:.3f}  (ref 115.0 / 29.5 / 0.425)",
            f"sunlit attic lum {a['lum']:.1f} sat {a['sat']:.3f} R-B {a['rb']:.1f}  (ref 189.6 / 0.588 / 136)",
            f"shade/sunlit {s['lum']/max(1e-6, a['lum']):.3f} (ref 0.607)   columns {c['lum']/95.8:.2f}x",
            f"sky_top {m['sky_top']['lum']:.1f}  sky_l/t {m['sky_ratio']:.3f}  water sat {m['near_water_sky']['sat']:.3f}"]


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--cam03-after", required=True)
    ap.add_argument("--hero-after", required=True)
    ap.add_argument("--cam04-cycles", required=True)
    ap.add_argument("--cam04-eevee", default=None)
    ap.add_argument("--out", default=str(P / "light_r12_sheet.png"))
    a = ap.parse_args()

    HERO_CROP = (860, 170, 1420, 500)     # the shaded north attic box (1110,225)-(1150,260) with context
    rows = []

    rows.append(row([
        cell(crop(Q / "round05_03_colonnade_walk.png"), "BEFORE  round 05 Eevee (QA)",
             f_cam03(Q / "round05_03_colonnade_walk.png")),
        cell(crop(a.cam03_after), "AFTER  r12 rig", f_cam03(a.cam03_after)),
        cell(crop(REF128).crop((0, 900, 1920, 1980)), "REF 128 (a MIDDAY photo: structure only)",
             ["QA round 05 retired ref 128's absolute 69.7 and re-based",
              "the test on the ratio measured INSIDE the cam03 frame,",
              "anchored on ref 169's golden-hour shade/sunlit = 0.607.",
              "Window 0.30-0.70, shade hue 25-42, sat <= 0.55."]),
    ], "ITEM 1  QA-05-1  cam03 colonnade shade  (near shaft 0,150-420,720 over sunlit rotunda 560,0-880,320)"))

    rows.append(row([
        cell(crop(Q / "round05_01_lagoon_hero_cycles.png", size=(1920, 1080), box=HERO_CROP),
             "BEFORE  round 05 hero, Cycles", f_hero(Q / "round05_01_lagoon_hero_cycles.png")),
        cell(crop(a.hero_after, size=(1920, 1080), box=HERO_CROP), "AFTER  r12 rig, Cycles", f_hero(a.hero_after)),
        cell(crop(m10.ALIGNED, panel=1, panels=3, box=HERO_CROP), "REF 169 warped into the render frame",
             f_hero(str(m10.ALIGNED), panel=1)),
    ], "ITEM 2  QA-05-1 hero half  shaded north attic (1110,225-1150,260) and the sunlit attic it is measured against"))

    third = (cell(crop(a.cam04_eevee), "EEVEE  r12 rig (QA-05-9 gap)", f_cam04(a.cam04_eevee))
             if a.cam04_eevee else
             cell(crop(REF083), "REF 083", ["soffit/sky 0.405   coffer/sky 0.437",
                                            "dark/light quarter 0.265   field std 31.2"]))
    rows.append(row([
        cell(crop(Q / "round05_04_rotunda_ceiling_cycles.png"), "BEFORE  round 05 Cycles (QA)",
             f_cam04(Q / "round05_04_rotunda_ceiling_cycles.png")),
        cell(crop(a.cam04_cycles), "AFTER  r12 rig, Cycles", f_cam04(a.cam04_cycles)),
        third,
    ], "ITEM 3  QA-05-3  cam04 vault on the MERGED master (coffer 0.35-0.55, dark/light quarter >= 0.20)"))

    sheet = stack(rows)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    sheet.save(a.out)
    print(f"[r12_sheet] {a.out}  {sheet.width}x{sheet.height}")
