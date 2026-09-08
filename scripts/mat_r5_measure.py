"""Round-5 measurements (plain python + PIL, no Blender).

    python3 scripts/mat_r5_measure.py [--tag r5after]

Reads the renders written by mat_scene_check.py and prints, for the same boxes in the before and the after:

  capital  QA-03-15: luminance spread inside the capital box, and the row profile through the two leaf tiers
           (a "readable tier" = a local minimum in the profile at least MIN_DIP below the crests around it).
  cam06    the 250-450 m canopy and a lawn reference in the same frame (MAT_backdrop_forest).
  ceiling  the coffered saucer: mean of the darkest quarter (ribs) over the mean of the lightest quarter (panels),
           the same statistic on ref 083 / coffered_ceiling_1, which is what "ribs darker than panels" means.

Writes renders/qa_comparisons/mat_r5_numbers.txt for mat_r5_sheet.py.
"""
import sys
import colorsys
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
PREV = ROOT / "renders/previews/materials"
REF = Path("/Users/dk/Projects/3d render blender 3rd attempt building/reference/photos")
OUT = ROOT / "renders/qa_comparisons/mat_r5_numbers.txt"

CAPITAL_BOX = (235, 225, 555, 500)          # the bell + both leaf tiers, 768x768 render
CAPITAL_STRIP = (300, 225, 470, 505)        # a vertical strip straight down the front of the bell
WALL_BOX = (60, 90, 200, 210)               # plain ochre wall behind: a control, must not move
FOREST_L = (10, 5, 320, 70)                 # cam06 960x540: canopy band at the top of frame
FOREST_R = (640, 5, 950, 85)
LAWN = (300, 390, 420, 430)
SAUCER = (330, 60, 1000, 600)               # cam04 1280x720: the coffered saucer
REF_SAUCER = None                           # filled from the reference's own size


def px(im, box):
    return list(im.crop(box).convert("RGB").getdata())


def lums(pixels):
    return sorted(0.2126 * r + 0.7152 * g + 0.0722 * b for r, g, b in pixels)


def pct(sorted_vals, p):
    return sorted_vals[min(len(sorted_vals) - 1, int(p * len(sorted_vals)))]


def mean(v):
    return sum(v) / max(1, len(v))


def std(v):
    m = mean(v)
    return (sum((x - m) ** 2 for x in v) / max(1, len(v))) ** 0.5


def colour(pixels):
    n = len(pixels)
    r = sum(p[0] for p in pixels) / n
    g = sum(p[1] for p in pixels) / n
    b = sum(p[2] for p in pixels) / n
    h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
    return r, g, b, 0.2126 * r + 0.7152 * g + 0.0722 * b, h * 360, s


def open_or_none(p):
    p = Path(p)
    return Image.open(p).convert("RGB") if p.exists() else None


def tier_profile(im, box, min_dip=4.0):
    """Row means down the front of the bell; count the dips deep enough to read as a tier boundary."""
    c = im.crop(box).convert("RGB")
    rows = []
    for y in range(c.height):
        row = [c.getpixel((x, y)) for x in range(c.width)]
        rows.append(mean([0.2126 * r + 0.7152 * g + 0.0722 * b for r, g, b in row]))
    # 5-row box smooth so single-pixel noise is not a "tier"
    sm = [mean(rows[max(0, i - 2):i + 3]) for i in range(len(rows))]
    dips = 0
    i = 1
    while i < len(sm) - 1:
        if sm[i] <= sm[i - 1] and sm[i] <= sm[i + 1]:
            left = max(sm[max(0, i - 25):i] or [sm[i]])
            right = max(sm[i + 1:i + 26] or [sm[i]])
            if min(left, right) - sm[i] >= min_dip:
                dips += 1
                i += 12
        i += 1
    return sm, dips


def report():
    lines = []

    def emit(s):
        print(s)
        lines.append(s)

    # ---- capital
    b = open_or_none(PREV / "r5before_scene_capital.png")
    a = open_or_none(PREV / "r5after_scene_capital.png")
    if b and a:
        emit("capital (768x768 Cycles, 400 mm from the hero station = 8x hero resolution, 48 spp)")
        for tag, im in (("before", b), ("after", a)):
            L = lums(px(im, CAPITAL_BOX))
            sm, dips = tier_profile(im, CAPITAL_STRIP)
            w = lums(px(im, WALL_BOX))
            emit(f"  {tag:6s} bell box lum mean {mean(L):6.1f} sd {std(L):5.1f}  p10 {pct(L,0.10):5.1f} "
                 f"p50 {pct(L,0.50):5.1f} p90 {pct(L,0.90):5.1f}  p10/p90 {pct(L,0.10)/max(1,pct(L,0.90)):5.3f}  "
                 f"readable tiers {dips}   [control wall lum {mean(w):6.1f}]")

    # ---- cam06 far field
    b = open_or_none(PREV / "r5before_scene_cam06.png")
    a = open_or_none(PREV / "r5after_scene_cam06.png")
    if b and a:
        emit("cam06 far field (960x540 Cycles 48 spp): the 250-450 m canopy vs a lawn in the same frame")
        for name, box in (("canopy left", FOREST_L), ("canopy right", FOREST_R), ("island lawn", LAWN)):
            row = f"  {name:13s}"
            for tag, im in (("before", b), ("after", a)):
                r, g, bl, lum, h, s = colour(px(im, box))
                row += f"   {tag} {r:5.1f},{g:5.1f},{bl:5.1f} lum {lum:5.1f} hue {h:5.1f} sat {s:5.3f}"
            emit(row)
        for tag, im in (("before", b), ("after", a)):
            lc = mean([colour(px(im, FOREST_L))[3], colour(px(im, FOREST_R))[3]])
            lw = colour(px(im, LAWN))[3]
            emit(f"  {tag:6s} canopy / lawn luminance ratio {lc / max(1e-6, lw):5.3f}   (ref 105: 0.85)")

    # ---- ceiling ribs
    b = open_or_none(PREV / "r5before_scene_ceiling.png")
    a = open_or_none(PREV / "r5after_scene_ceiling.png")
    ref = open_or_none(REF / "ornament_crops/coffered_ceiling_1.jpg")
    if b and a:
        emit("cam04 coffered saucer (1280x720 Eevee LOD1): mean of the darkest quarter (ribs) / lightest quarter (panels)")
        items = [("before", b, SAUCER), ("after", a, SAUCER)]
        if ref:
            W, H = ref.size
            items.append(("ref 083", ref, (int(W * 0.28), int(H * 0.06), int(W * 0.74), int(H * 0.94))))
        for tag, im, box in items:
            L = lums(px(im, box))
            q = len(L) // 4
            dark, light = mean(L[:q]), mean(L[-q:])
            emit(f"  {tag:8s} dark quarter {dark:6.1f}  light quarter {light:6.1f}  ratio {dark / max(1e-6, light):5.3f}"
                 f"   sd {std(L):5.1f}  median {pct(L,0.5):6.1f}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines) + "\n")
    print(f"\n[mat_r5_measure] wrote {OUT}")


if __name__ == "__main__":
    report()
