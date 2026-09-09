"""Round-13 comparison sheet: before / after / reference for the round's three items and the carried water cell.
Plain python3 + PIL, no Blender.

Rows
  1  item 1  hero shaded attic in EEVEE      r12 bake | r13 rig | the CYCLES frame of the same rig | ref 169
  2  item 2  cam06 horizon crop              compositor as shipped | compositor retuned | compositor OFF
  3  item 3  hero wings and shore band       shipped sky term | the sky term raised | ref 169
  4  carry   near water (r12 review find. 4) r12 ship (sat 0.418) | this master | ref 169
"""
import pathlib, tempfile
import sys, argparse
from pathlib import Path
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import light_r10_measure as m10
import light_r13_measure as M13

ROOT = M13.ROOT
P = ROOT / "renders" / "previews" / "lighting"

CELL_W = 560
PAD, HEAD, CAP = 10, 26, 46
BG, FG, HI = (18, 18, 20), (232, 232, 232), (255, 214, 120)

ATTIC_CROP = (860, 170, 1420, 500)      # the shaded north attic box (1110,225)-(1150,260) with context
WING_CROP = (0, 420, 1920, 780)         # both wing bands (y 480-600) and the shore band (y 600-740)
WATER_CROP = (820, 700, 1520, 1080)     # water_refl (900,760-1020,840) and near_water_sky (1150,1000-1450,1050)


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


def f_attic(p, panel=None, ref=None):
    m = m10.measure(p, panel=panel)
    s, a = m["attic_shaded"], m["attic_sunlit"]
    out = [f"SHADED attic lum {s['lum']:.1f} hue {s['hue']:.1f} sat {s['sat']:.3f}",
           f"sunlit attic lum {a['lum']:.1f} hue {a['hue']:.1f} sat {a['sat']:.3f}",
           f"entablature {m['entablature']['lum']:.1f}   sky_top {m['sky_top']['lum']:.1f} "
           f"hue {m['sky_top']['hue']:.1f}"]
    if ref is not None:
        r = m10.measure(ref)["attic_shaded"]
        out.append(f"vs Cycles: d_lum {100*(s['lum']-r['lum'])/max(1e-6,r['lum']):+.1f}% (<=15) "
                   f"d_hue {s['hue']-r['hue']:+.1f} (<=6) d_sat {s['sat']-r['sat']:+.3f} (<=0.10)")
    return out


def f_cam06(p):
    import env_r7_measure as env
    L = env.load(str(p), 1280)
    c = L[0:220, 0:1280]
    kf, _ = env.count_lines(L[0:110, 0:1280])
    return [f"horizon crop (rows 0-220)  mean {c.mean():.1f}   STD {c.std():.1f}   test std >= 35",
            f"far-shore lines in rows 0-110: {kf}   (env_r7_measure.count_lines)"]


def f_wings(p, panel=None):
    m = M13._hero(p) if panel is None else None
    if m is None:
        im = crop(p, panel=panel, panels=3)
        tmp = pathlib.Path(tempfile.gettempdir()) / "_r13_sheet_tmp.png"   # r13 review carry 11: not P/ (tracked)
        im.save(tmp)
        m = M13._hero(str(tmp))
    w = m["wings"]
    return [f"SOUTH wing band {w['south_wing']['lum']:.1f}   (>= 82 raw / >= 103 aligned; ref 109.5)",
            f"north wing band {w['north_wing']['lum']:.1f}   ({w['north_wing']['lum']/146.5:.2f}x of 146.5)",
            f"SHORE band {m['shore_band']['lum']:.1f}   (environment's box, ref 115.6)",
            f"sunlit attic {m['attic_sunlit']['lum']:.1f} sat {m['attic_sunlit']['sat']:.3f} "
            f"R-B {m['attic_sunlit']['rb']:.1f}   (178.2-201 / >=0.50 / >=110)"]


def f_water(p, panel=None):
    m = m10.measure(p, panel=panel)
    n, r = m["near_water_sky"], m["water_refl"]
    return [f"near water sat {n['sat']:.3f}  hue {n['hue']:.1f}  lum {n['lum']:.1f}",
            f"   QA-05-4 window sat 0.22-0.32, hue 185-200 (ref 0.270 / 192.1)",
            f"water reflection lum {r['lum']:.1f} sat {r['sat']:.3f}  (ref 168.9 / 0.339)",
            f"lagoon flank sat {m['lagoon_flank']['sat']:.3f}  (ref 0.279)"]


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--eevee-before", required=True)
    ap.add_argument("--eevee-after", required=True)
    ap.add_argument("--cycles", required=True)          # the Cycles frame of the shipped r13 rig (item 1's target)
    ap.add_argument("--cam06-ship", required=True)
    ap.add_argument("--cam06-after", required=True)
    ap.add_argument("--cam06-nocomp", required=True)
    ap.add_argument("--hero-sky-raised", required=True)
    ap.add_argument("--water-before", required=True)    # r12ship_base_01c.png
    ap.add_argument("--out", default=str(ROOT / "renders" / "qa_comparisons" / "light_r13_sheet.png"))
    a = ap.parse_args()

    rows = []
    rows.append(row([
        cell(crop(a.eevee_before, size=(1920, 1080), box=ATTIC_CROP), "BEFORE  Eevee, round-12 bake",
             f_attic(a.eevee_before, ref=a.cycles)),
        cell(crop(a.eevee_after, size=(1920, 1080), box=ATTIC_CROP), "AFTER  Eevee, r13 rig",
             f_attic(a.eevee_after, ref=a.cycles)),
        cell(crop(a.cycles, size=(1920, 1080), box=ATTIC_CROP), "TARGET  Cycles, same rig", f_attic(a.cycles)),
        cell(crop(m10.ALIGNED, panel=1, panels=3, box=ATTIC_CROP), "REF 169 warped into the render frame",
             f_attic(str(m10.ALIGNED), panel=1)),
    ], "ITEM 1  the Eevee preview must carry the round-12 shade: shaded attic within 6 deg hue / 0.10 sat / 15 % lum of Cycles"))

    rows.append(row([
        cell(crop(a.cam06_ship).crop((0, 0, 1280, 240)), "BEFORE  compositor as shipped", f_cam06(a.cam06_ship)),
        cell(crop(a.cam06_after).crop((0, 0, 1280, 240)), "AFTER  compositor retuned", f_cam06(a.cam06_after)),
        cell(crop(a.cam06_nocomp).crop((0, 0, 1280, 240)), "REFERENCE  compositor OFF (env's geometry)",
             f_cam06(a.cam06_nocomp)),
    ], "ITEM 2  QA-05-8 / ENV hand-off  cam06 horizon crop: the mist must not flatten the far-shore line"))

    rows.append(row([
        cell(crop(a.cycles, size=(1920, 1080), box=WING_CROP), "BEFORE  shipped sky term", f_wings(a.cycles)),
        cell(crop(a.hero_sky_raised, size=(1920, 1080), box=WING_CROP), "AFTER  sky term raised",
             f_wings(a.hero_sky_raised)),
        cell(crop(m10.ALIGNED, panel=1, panels=3, box=WING_CROP), "REF 169 warped into the render frame",
             f_wings(m10.ALIGNED, panel=1)),
    ], "ITEM 3  QA-05-5 south wing band (>= 103 aligned) and environment's shore band (ref 115.6), against the sunlit windows"))

    rows.append(row([
        cell(crop(a.water_before, size=(1920, 1080), box=WATER_CROP), "BEFORE  round-12 ship (Cycles)",
             f_water(a.water_before)),
        cell(crop(a.cycles, size=(1920, 1080), box=WATER_CROP), "AFTER  r13 on the materials-r7 master",
             f_water(a.cycles)),
        cell(crop(m10.ALIGNED, panel=1, panels=3, box=WATER_CROP), "REF 169 warped into the render frame",
             f_water(str(m10.ALIGNED), panel=1)),
    ], "CARRY  r12 review finding 4: the near-water cell the round-12 sheet never showed (QA-05-4)"))

    sheet = stack(rows)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    sheet.save(a.out)
    print(f"[r13_sheet] {a.out}  {sheet.width}x{sheet.height}")
