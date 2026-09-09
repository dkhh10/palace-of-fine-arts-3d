"""Round-14 comparison sheet: the four cameras' SHADE, before / after / reference, with the numbers burnt in.

Rows
  1  cam01 hero      the HOLD: the r12/r13 shade window and the sunlit windows must not move
  2  cam03 walk      QA-06-2's cam03 half + QA-06-7's outer row (ratio to the sunlit rotunda)
  3  cam06 aerial    QA-06-2's roofs / plaza / trees and the frame's violet fraction
  4  cam02 + cam05   the shaded stone that never flooded, and the two water boxes that did

Reference column: ref 169 warped into the hero frame for row 1 (the only mapping where render and photo share
pixels); for rows 2-4 the reference is the round-05 render -- the last build before the r12 tint -- with the
photograph's own numbers quoted in the caption, because no registered warp exists for those cameras.
"""
import sys, argparse
from pathlib import Path
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import light_r10_measure as m10
import light_r14_measure as M14
from light_r13_sheet import cell, row, stack, crop, CELL_W

ROOT = M14.ROOT
QA = ROOT / "renders" / "previews" / "qa"

HERO_CROP = (600, 150, 1600, 900)
CAM03_CROP = (0, 0, 1280, 720)
CAM06_CROP = (0, 0, 1280, 460)
CAM02_CROP = (0, 60, 1280, 720)


def _m(p, cam):
    got = M14.measure(p)
    if got is None or got[0] != cam:
        # the file name does not carry the camera id; measure it as `cam` anyway
        import numpy as np
        spec = M14.BOXES[cam]
        a = M14.load(p, spec["size"])
        out = {k: m10.stats(a[y0:y1, x0:x1]) for k, (x0, y0, x1, y1) in spec["boxes"].items()}
        if cam == "03":
            den = max(1e-6, out["sunlit_rotunda"]["lum"])
            for k in ("walk", "shaft_flank", "outer_row", "near_shaft"):
                out[k]["ratio"] = out[k]["lum"] / den
        return out
    return got[1]


def f01(p, panel=None):
    m = m10.measure(p, panel=panel)
    s, a = m["attic_shaded"], m["attic_sunlit"]
    return [f"SHADED attic  lum {s['lum']:.1f}  hue {s['hue']:.1f}  sat {s['sat']:.3f}   window 103-127 / 23.5-35.5 / <=0.50",
            f"sunlit attic  lum {a['lum']:.1f}  sat {a['sat']:.3f}  R-B {a['rb']:.1f}   window 178-201 / >=0.50 / >=110",
            f"columns {m['columns']['lum']:.1f} hue {m['columns']['hue']:.1f}   sky_top {m['sky_top']['lum']:.1f} "
            f"hue {m['sky_top']['hue']:.1f}",
            f"water reflection lum {m['water_refl']['lum']:.1f} hue {m['water_refl']['hue']:.1f} "
            f"R-B {m['water_refl']['rb']:+.1f}   (QA-06-3: R-B >= +35)"]


def f03(p):
    m = _m(p, "03")
    return [f"WALK  lum {m['walk']['lum']:.1f}  hue {m['walk']['hue']:.1f}  sat {m['walk']['sat']:.3f}"
            f"   QA window hue 25-60",
            f"shaft flank / sunlit {m['shaft_flank']['ratio']:.3f}  hue {m['shaft_flank']['hue']:.1f}"
            f"   (window 0.30-0.70)",
            f"OUTER ROW / sunlit {m['outer_row']['ratio']:.3f}  hue {m['outer_row']['hue']:.1f}"
            f"   (QA-06-7 test >= 0.15)",
            f"sunlit rotunda {m['sunlit_rotunda']['lum']:.1f} hue {m['sunlit_rotunda']['hue']:.1f}"]


def f06(p):
    m = _m(p, "06")
    return [f"ROOFS  hue {m['roofs']['hue']:.1f} sat {m['roofs']['sat']:.3f}   (round 05: 37.3 / 0.431)",
            f"PLAZA  hue {m['plaza']['hue']:.1f} sat {m['plaza']['sat']:.3f}   (round 05: 36.6 / 0.505)",
            f"TREES  hue {m['trees']['hue']:.1f} sat {m['trees']['sat']:.3f}   (round 05: 37.6 / 0.472)",
            f"frame median hue {m['frame']['hue']:.1f}   pixels in hue 200-300: {100*m['frame']['violet']:.1f} %",
            f"horizon crop mean {m['horizon']['lum']:.1f}"]


def f02(p):
    m = _m(p, "02")
    return [f"shaded pier  hue {m['shade_pier']['hue']:.1f} sat {m['shade_pier']['sat']:.3f}  lum {m['shade_pier']['lum']:.1f}",
            f"shaded soffit hue {m['shade_soffit']['hue']:.1f} sat {m['shade_soffit']['sat']:.3f}",
            f"shaded balustrade hue {m['shade_balus']['hue']:.1f} sat {m['shade_balus']['sat']:.3f}",
            f"WATER  hue {m['water']['hue']:.1f} sat {m['water']['sat']:.3f} lum {m['water']['lum']:.1f}"
            f"   (round 05: 41.3 / 0.461)"]


def f05(p):
    m = _m(p, "05")
    w = m["water_band"]
    return [f"WATER band lum {w['lum']:.1f} hue {w['hue']:.1f} sat {w['sat']:.3f}",
            f"   ref 063: 93.4 / 64.9 / 0.306   (QA-06-3: hue 40-80, sat >= 0.24)",
            f"attic band lum {m['attic_band']['lum']:.1f} hue {m['attic_band']['hue']:.1f} "
            f"sat {m['attic_band']['sat']:.3f}"]


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    for k in ("hero_before", "hero_after", "c03_before", "c03_after", "c06_before", "c06_after",
              "c02_before", "c02_after", "c05_before", "c05_after"):
        ap.add_argument("--" + k.replace("_", "-"), required=True)
    ap.add_argument("--out", default=str(ROOT / "renders" / "qa_comparisons" / "light_r14_sheet.png"))
    a = ap.parse_args()

    rows = [
        row([cell(crop(a.hero_before, size=(1920, 1080), box=HERO_CROP), "BEFORE  r13 rig (master as saved)",
                  f01(a.hero_before)),
             cell(crop(a.hero_after, size=(1920, 1080), box=HERO_CROP), "AFTER  r14 rig", f01(a.hero_after)),
             cell(crop(m10.ALIGNED, panel=1, panels=3, box=HERO_CROP), "REF 169 warped into the render frame",
                  f01(str(m10.ALIGNED), panel=1))],
            "cam01 HERO -- the HOLD. The r12/r13 shade window and the sunlit windows must survive the fix."),
        row([cell(crop(a.c03_before, size=(1280, 720), box=CAM03_CROP), "BEFORE  r13 rig", f03(a.c03_before)),
             cell(crop(a.c03_after, size=(1280, 720), box=CAM03_CROP), "AFTER  r14 rig", f03(a.c03_after)),
             cell(crop(QA / "round05_03_colonnade_walk.png", size=(1280, 720), box=CAM03_CROP),
                  "ROUND 05 -- the last build before the tint", f03(str(QA / "round05_03_colonnade_walk.png")))],
            "cam03 -- QA-06-2 (walk hue 222.6, window 25-60) and QA-06-7 (outer row 0.066 of sunlit, test >= 0.15)"),
        row([cell(crop(a.c06_before, size=(1280, 720), box=CAM06_CROP), "BEFORE  r13 rig", f06(a.c06_before)),
             cell(crop(a.c06_after, size=(1280, 720), box=CAM06_CROP), "AFTER  r14 rig", f06(a.c06_after)),
             cell(crop(QA / "round05_06_aerial.png", size=(1280, 720), box=CAM06_CROP),
                  "ROUND 05 -- the last build before the tint", f06(str(QA / "round05_06_aerial.png")))],
            "cam06 -- QA-06-2's blocker: roofs 36.6 -> 253.4, ground 39.3 -> 268.8, trees 35.8 -> 239.9"),
        row([cell(crop(a.c02_before, size=(1280, 720), box=CAM02_CROP), "BEFORE  cam02, r13 rig", f02(a.c02_before)),
             cell(crop(a.c02_after, size=(1280, 720), box=CAM02_CROP), "AFTER  cam02, r14 rig", f02(a.c02_after)),
             cell(crop(a.c05_after, size=(1280, 720), box=CAM02_CROP), "AFTER  cam05 (its own boxes)",
                  f05(a.c05_after) + [""] + f05(a.c05_before)[:1] + ["   (last line = BEFORE)"])],
            "cam02 / cam05 -- the shaded STONE never flooded (it is the WATER that did): the hand-off to materials"),
    ]
    sheet = stack(rows)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    sheet.save(a.out)
    print(f"[r14_sheet] {a.out}  {sheet.width}x{sheet.height}")
