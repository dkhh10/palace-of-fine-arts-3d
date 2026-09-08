"""Round-10 comparison sheet: before / after / reference for brief items 1, 2, 4 and 6, with the numbers.

    python3 scripts/light_r10_sheet.py

Row 1 (item 1)  sunlit attic + shaded north attic, cam01 hero      before | after | ref 169 (warped)
Row 2 (item 2)  the rotunda colonnade shafts, cam01 hero           before | after | ref 169 (warped)
Row 3 (item 4)  the sky band, cam01 hero                           before | after | ref 169 (raw, own framing)
Row 4 (item 6)  cam04 rotunda ceiling                              Eevee before | Eevee after | Cycles (the target)

"before" is the merged master exactly as the lead built it (r10_base_*); "after" is the same master with the round-10
rig applied in memory (r10f*/r10q*), which is what light_build.py now writes into assets/lighting.blend.
"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import light_r10_measure as M

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "renders" / "previews" / "lighting"
# Worktree-safe (round-10 review nit): the aligned panel is git-tracked so it lives in this checkout; only the
# reference PHOTOS are main-checkout-only, and they come from the same env var common.REFERENCE_DIR uses.
ALIGNED = M.ALIGNED
REF169 = M.REFERENCE_DIR / "photos" / "raw" / "ref_169_main_Palace_of_Fine_Arts_16794p.jpg"

BEFORE = P / "r10_base_01_hero_cycles.png"
AFTER = P / "r10fhero_SHIP.png"
E_BEFORE = P / "r10e04_fgi1_d60.png"
E_AFTER = P / "r10qv_f1_v1_sp45_E1_8_45_13_0_eevee.png"
C_TARGET = P / "r10_base_04_ceiling_cycles.png"

CELL_W = 620
ROWS = [
    ("item 1  sunlit attic (900,222)-(1020,256) and shaded north attic (1110,225)-(1150,260)", (850, 180, 1210, 310)),
    ("item 2  colonnade shafts, QA's mask box (680,280)-(1240,470)", (660, 265, 1260, 480)),
    ("item 4  sky: sky_top (1210,22)-(1690,76) vs sky_left (38,92)-(192,157)", (0, 0, 1920, 210)),
]


def load(p, panel=None):
    im = Image.open(p).convert("RGB")
    if panel is not None:
        im = im.crop((panel * 1920, 0, (panel + 1) * 1920, im.size[1]))
    if im.size != (1920, 1080):
        im = im.resize((1920, 1080), Image.LANCZOS)
    return im


def cell(im, box, w=CELL_W):
    c = im.crop(box)
    return c.resize((w, max(1, round(w * c.size[1] / c.size[0]))), Image.LANCZOS)


def main():
    before, after = load(BEFORE), load(AFTER)
    refw = load(ALIGNED, panel=1)
    mb, ma, mr = M.measure(BEFORE), M.measure(AFTER), M.REF

    def num(m, ref=False):
        if ref:
            return ["attic 231,187,95  sat 0.588  R-B 136  lum 190", "shade 141,111,81  hue 29.5  lum 115",
                    "columns lum 95.8", "sky_top 165.7 (raw)  sky_left/top 1.170", "near water sat 0.270  hue 192"]
        a, s, c, n = m["attic_sunlit"], m["attic_shaded"], m["columns"], m["near_water_sky"]
        g = lambda x: ",".join(str(int(round(v))) for v in x["rgb"])
        return [f"attic {g(a)}  sat {a['sat']:.3f}  R-B {a['rb']:.0f}  lum {a['lum']:.0f}",
                f"shade {g(s)}  hue {s['hue']:.1f}  lum {s['lum']:.0f}",
                f"columns lum {c['lum']:.1f}  ({c['lum']/95.8:.2f}x ref)",
                f"sky_top {m['sky_top']['lum']:.1f}  sky_left/top {m['sky_ratio']:.3f}",
                f"near water sat {n['sat']:.3f}  hue {n['hue']:.1f}"]

    cells = []
    for title, box in ROWS:
        cells.append((title, [cell(before, box), cell(after, box), cell(refw, box)]))
    # row 4: cam04, whole frame
    if E_AFTER.exists():
        row4 = [load(E_BEFORE), load(E_AFTER), load(C_TARGET)]
        cells.append(("item 6  cam04 rotunda ceiling: Eevee before | Eevee after | Cycles (the target)",
                      [c.resize((CELL_W, round(CELL_W * 1080 / 1920)), Image.LANCZOS) for c in row4]))

    head = 150
    rowgap = 30
    heights = [max(c.size[1] for c in cs) + rowgap + 20 for _, cs in cells]
    W = CELL_W * 3 + 40
    H = head + sum(heights) + 20
    sheet = Image.new("RGB", (W, H), (18, 18, 20))
    d = ImageDraw.Draw(sheet)
    d.text((12, 8), "PALACE OF FINE ARTS - lighting round 10 - cam01 Cycles 1920x1080 / 64 spp on the merged master "
                    "(arch p4r2, mat r4, env r4)", fill=(255, 255, 255))
    d.text((12, 24), "BEFORE = master as built (exposure -2.333, cam boost 1.50, glossy 3.75, one sky saturation 1.20)"
                     "   |   AFTER = -0.5 EV (bias 1.75->1.25), cam boost 2.10, glossy 5.25, glossy saturation 0.90",
           fill=(200, 200, 200))
    for i, (lab, lines) in enumerate((("BEFORE", num(mb)), ("AFTER", num(ma)), ("REF 169", num(None, ref=True)))):
        x = 12 + i * (CELL_W + 14)
        d.text((x, 46), lab, fill=(255, 220, 120))
        for j, ln in enumerate(lines):
            d.text((x, 62 + j * 15), ln, fill=(190, 210, 190) if i == 2 else (215, 215, 215))
    y = head
    for (title, cs), h in zip(cells, heights):
        d.text((12, y), title, fill=(255, 220, 120))
        for i, c in enumerate(cs):
            sheet.paste(c, (12 + i * (CELL_W + 14), y + 18))
        y += h
    out = P / "light_r10_sheet.png"
    sheet.save(out)
    print("wrote", out, sheet.size)


if __name__ == "__main__":
    main()
