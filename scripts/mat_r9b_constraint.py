"""What actually blocks QA-07-2, measured: the SHADED attic's sat ceiling, not "a negative albedo".

    python3 scripts/mat_r9b_constraint.py <hero.png>        # the shipped hero Cycles frame

docs/reviews/mat_r9_review.md finding 2: round 9 concluded that closing the sunlit attic's saturation
0.461 -> 0.53 "would need a scene-blue cut of order -120 %, i.e. a negative albedo".  That was read off a chart
patch's ABSOLUTE saturation, and only the transfer's SLOPE carries from a chart patch to the hero's own pixel.
The review asked for the real binding constraint to be measured instead.  This is that measurement.

The lever is `Albedo Tint`'s blue channel (`mat_build.PHOTO_TINT`, currently 0.7582 = -24.2 %), a global multiply
on the finished albedo of MAT_concrete_ochre / MAT_ornament_concrete / MAT_drum_band.  Its END-TO-END response was
measured on this master in round 9, on the same two boxes, with everything in the path included (AgX at the
shipped look, the compositor's haze, the specular sky term, bounce):

    albedo blue x0.758  ->  sunlit attic display blue -2.2 %,  shaded attic display blue -12.2 %
    t_B(sunlit) = ln(0.978)/ln(0.758) = 0.080          t_B(shaded) = ln(0.878)/ln(0.758) = 0.470

(Both are far below the view transform's own chroma transfer at those levels -- 0.31 and ~0.98 from
`scripts/mat_r9b_agx.py` -- because the terms that do NOT scale with this albedo, the haze and the mirrored sky,
are themselves blue and so dilute the blue channel much harder than they dilute luminance, where the same
comparison gives 0.88 and 0.71.  They are used here as measured numbers, not as a model.)

Scan the tint exponent p (albedo blue = 0.7582 ** p, p = 1 is what ships) and print what each box does.  R and G
are held: the correction is a blue cut, and both boxes' R is what sets their saturation denominator.
"""
import sys
from pathlib import Path
import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mat_r7_measure import BOXES

TINT_B = 0.7582                     # mat_build.PHOTO_TINT[2], from projection_meta.json M_chroma
T_B = dict(attic_sunlit=0.0803, attic_shaded=0.4695)      # end-to-end, round 9, on this master
WIN = dict(sunlit_sat=(0.53, 0.62), sunlit_rb=120.0, shaded_sat=0.50, shaded_hue=(23.5, 35.5))


def hue(c):
    import colorsys
    mx = max(c) / 255.0
    h, _, _ = colorsys.rgb_to_hls(c[0] / 255.0, c[1] / 255.0, c[2] / 255.0)
    return h * 360.0


def main(path):
    a = np.asarray(Image.open(path).convert("RGB")).astype(np.float64)
    box = {k: a[BOXES[k][1]:BOXES[k][3], BOXES[k][0]:BOXES[k][2]].reshape(-1, 3).mean(axis=0)
           for k in ("attic_sunlit", "attic_shaded")}
    print(f"[con] {Path(path).name}")
    for k, c in box.items():
        print(f"[con]   {k:14s} RGB {c[0]:6.1f} {c[1]:6.1f} {c[2]:6.1f}  sat {(c.max() - c.min()) / c.max():.3f}  "
              f"R-B {c[0] - c[2]:+6.1f}  hue {hue(c):5.1f}  (t_B {T_B[k]:.4f})")
    print(f"[con] {'p':>5s} {'albedo B':>9s} | {'sunlit B':>9s} {'sat':>6s} {'R-B':>7s} | "
          f"{'shaded B':>9s} {'sat':>6s} {'hue':>6s} | verdict")
    for p in [0.0, 0.5, 1.0, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0, 4.0]:
        ab = TINT_B ** p
        row = {}
        for k, c in box.items():
            # the box as it would render at exponent p, relative to the SHIPPED frame (which is already at p = 1)
            b = c[2] * (ab / TINT_B) ** T_B[k]
            cc = np.array([c[0], c[1], b])
            row[k] = (b, (cc.max() - cc.min()) / cc.max(), cc[0] - cc[2], hue(cc))
        su, sh = row["attic_sunlit"], row["attic_shaded"]
        ok_sh = sh[1] <= WIN["shaded_sat"] and WIN["shaded_hue"][0] <= sh[3] <= WIN["shaded_hue"][1]
        ok_su = WIN["sunlit_sat"][0] <= su[1] <= WIN["sunlit_sat"][1] and su[2] >= WIN["sunlit_rb"]
        print(f"[con] {p:5.2f} {ab:9.4f} | {su[0]:9.1f} {su[1]:6.3f} {su[2]:+7.1f} | "
              f"{sh[0]:9.1f} {sh[1]:6.3f} {sh[3]:6.1f} | "
              f"shade {'ok' if ok_sh else 'OVER'}  sunlit {'ok' if ok_su else 'short'}")
    # the exact p at which the shaded ceiling binds: sat_shaded(p) = WIN
    c = box["attic_shaded"]
    b_max = c[0] * (1.0 - WIN["shaded_sat"])                  # blue that puts the shaded box exactly at sat 0.50
    p_max = np.log((b_max / c[2]) ** (1.0 / T_B["attic_shaded"]) * TINT_B) / np.log(TINT_B)
    ab = TINT_B ** p_max
    s = box["attic_sunlit"]
    b_su = s[2] * (ab / TINT_B) ** T_B["attic_sunlit"]
    print(f"[con] the shaded sat 0.50 ceiling binds at exponent p {p_max:.3f}, i.e. albedo blue x{ab:.4f} "
          f"({100 * (ab - 1):.1f} %)")
    print(f"[con] at that ceiling the SUNLIT box reaches sat {(max(s[0], s[1], b_su) - min(s[0], s[1], b_su)) / max(s[0], s[1], b_su):.3f} "
          f"and R-B {s[0] - b_su:+.1f}, against the windows 0.53-0.62 and >= 120 -- "
          f"{'INSIDE' if s[0] - b_su >= 120 else 'STILL SHORT'}")
    print(f"[con] shipped p 1.00 spends {100 * (np.log(TINT_B) / np.log(ab)):.0f} % of that margin")
    # ... and the shaded HUE window binds BEFORE the saturation ceiling does
    lo, hi = 1.0, 6.0
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        b = c[2] * (TINT_B ** mid / TINT_B) ** T_B["attic_shaded"]
        (lo, hi) = (mid, hi) if hue(np.array([c[0], c[1], b])) <= WIN["shaded_hue"][1] else (lo, mid)
    b_su = s[2] * (TINT_B ** lo / TINT_B) ** T_B["attic_sunlit"]
    mx = max(s[0], s[1], b_su); mn = min(s[0], s[1], b_su)
    print(f"[con] the shaded HUE window (<= {WIN['shaded_hue'][1]} deg) binds FIRST, at p {lo:.3f} "
          f"(albedo blue x{TINT_B ** lo:.4f}); there the sunlit box is sat {(mx - mn) / mx:.3f} R-B {s[0] - b_su:+.1f}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else
         "renders/previews/materials/r9b_cycles_01_lagoon_hero.png")
