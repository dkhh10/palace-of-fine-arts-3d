"""ORN round 8, brief item 3 — commit the view the capital lay-out was measured on, so it can be re-measured.

The ref_002 reading in scripts/orn_r7_capital_layout.py quotes pixels ("face-centre column x~490 of 940,
astragal top y 785, abacus top y 385"), but the r7 review found that no committed file has that frame: the raw
photo is 1920x2561 and reference/photos/ornament_crops/corinthian_capital_1.jpg is 1920x1500. The 940-px view is
simply the raw photo resampled to 940 px wide (940x1254). This script regenerates it, plus an annotated copy
with the measured rules drawn on, from the raw photo in the MAIN checkout (raw photos are gitignored, 175 MB;
worktrees do not carry them). No bpy, no GPU.

    python3 scripts/orn_r8_ref002_crop.py [--ref <path to reference/>]

Writes reference/photos/ornament_crops/orn_r8_ref002_capital_940{,_measured}.jpg (both committed).
"""
import pathlib, sys

from PIL import Image, ImageDraw

RAW = "photos/raw/ref_002_rotunda_Corinthian_Order_Capital.jpg"
WIDTH = 940                      # the view every pixel number in the lay-out docstring refers to
OUT_DIR = "photos/ornament_crops"

# Two readings, both in the 940-px frame, both drawn on the annotated copy.
# r7 (cyan): the reading the lay-out was solved from - astragal top y 785, abacus top y 385, H = 400 px.
# r8 (yellow): re-measured on this committed view. At the FACE CENTRE y 385 lands in the entablature's
# egg-and-dart, above the capital; the abacus top edge crosses the centre at y 427 and its underside at y 472
# (the figure's head occludes the centre itself, so both are read immediately left and right of it). That puts
# H at 358 px = 119.3 px/m, and on that scale the volute eyes (y 508) sit at 0.774 H - which is where the
# round-8 preset puts the spiral centre (volute_z 0.762 H), an independent confirmation of that change.
# The tier fractions are NOT taken from either reading: they are Vignola's 0.30 / 0.30 H canon (raw here:
# 0.237 / 0.280 H), and the abacus is laid out at 0.100 H against 0.126 H raw, because in a view this steep the
# nearest element - the abacus, seen from under - is the most magnified thing in the frame.
X_FACE = 490                     # face-centre column of the pier capital
Y_BASE = 785                     # 0.000 H, astragal top (both readings agree)
R7 = [(385, "r7: abacus top, H = 400 px (lands in the entablature at the centre)"),
      (430, "r7: abacus bottom, 0.113 H raw"),
      (502, "r7: volute eye, 0.708 H on H = 400 px"),
      (600, "r7: upper acanthus top, 0.463 H raw"),
      (700, "r7: lower acanthus top, 0.213 H raw")]
R8 = [(427, "r8: abacus top at the face centre -> H = 358 px = 119.3 px/m"),
      (472, "r8: abacus underside, 0.126 H raw (laid out at 0.100 H)"),
      (508, "r8: volute eye, 0.774 H raw (preset volute_z 0.762 H)"),
      (600, "r8: upper acanthus top, 0.517 H raw -> tier 0.280 H raw, laid out 0.300 (Vignola)"),
      (700, "r8: lower acanthus top, 0.237 H raw, laid out 0.300 (Vignola)")]


def reference_dir():
    """`reference/` lives in the MAIN checkout only (CLAUDE.md). From a worktree, walk up past .claude/worktrees."""
    if "--ref" in sys.argv:
        return pathlib.Path(sys.argv[sys.argv.index("--ref") + 1])
    here = pathlib.Path(__file__).resolve()
    for p in here.parents:
        if (p / "reference" / RAW).exists():
            return p / "reference"
        if p.name == "worktrees" and (p.parent.parent / "reference" / RAW).exists():
            return p.parent.parent / "reference"
    raise SystemExit("[orn] ref_002 not found; pass --ref <path to the main checkout's reference/>")


def main():
    ref = reference_dir()
    src = ref / RAW
    im = Image.open(src)
    print(f"[orn] source {src} {im.size[0]}x{im.size[1]}")
    view = im.convert("RGB").resize((WIDTH, round(im.size[1] * WIDTH / im.size[0])), Image.LANCZOS)
    out = pathlib.Path(__file__).resolve().parent.parent / "reference" / OUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    plain = out / "orn_r8_ref002_capital_940.jpg"
    view.save(plain, quality=88)
    print(f"[orn] wrote {plain} {view.size[0]}x{view.size[1]}")

    ann = view.copy()
    d = ImageDraw.Draw(ann)
    for rules, colour, x0 in ((R7, (0, 220, 255), 60), (R8, (255, 235, 0), 60)):
        for y, label in rules:
            d.line([(x0, y), (WIDTH - 60, y)], fill=colour, width=1)
            d.text((x0 + 4, y + 2), f"y {y}  {label}", fill=colour)
    d.line([(X_FACE, 360), (X_FACE, Y_BASE + 30)], fill=(255, 80, 80), width=1)
    d.text((X_FACE + 4, 348), f"x {X_FACE}, face centre", fill=(255, 80, 80))
    d.line([(60, Y_BASE), (WIDTH - 60, Y_BASE)], fill=(255, 255, 255), width=1)
    d.text((64, Y_BASE + 4), f"y {Y_BASE}  astragal top = 0.000 H   (r7 H = 400 px, r8 H = "
                             f"{Y_BASE - R8[0][0]} px = {(Y_BASE - R8[0][0]) / 3.0:.1f} px/m)", fill=(255, 255, 255))
    meas = out / "orn_r8_ref002_capital_940_measured.jpg"
    ann.save(meas, quality=88)
    print(f"[orn] wrote {meas}")
    print("[orn] tiers read 0.237 / 0.280 H raw on the r8 scale; the lay-out uses Vignola's 0.30 / 0.30 H\n"
          "      canon instead, and the abacus 0.100 H against 0.126 H raw - a canon plus a hand reading,\n"
          "      not a measurement (ORN r7 review finding 3).")


if __name__ == "__main__":
    main()
