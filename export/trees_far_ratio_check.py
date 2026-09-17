"""Phase 6c item 2, review r1 finding 6: does `E_placement / E_bake` actually move the impostor's blue?

    python3 export/trees_far_ratio_check.py

CPU only, no Blender, no GPU. The lead's gate before the other 15 E_bake jobs are queued: the divisor is a
DIFFUSE IRRADIANCE ratio, and the measured blue may not be a diffuse response at all (the `sunonly` render
reads B exactly 0.000 although the rig carries blue fill lamps, while `skyonly` reads B 0.387). So take the
one placement the whole diagnosis was built on - `tree_far[0]` = TREEFAR_000, prototype
ENV_tree_broadleaf_s53_LOD1, the far tree on the axis of station 2 at 40.19 m - multiply the crown mean of the
atlas frame that station picks (col 1, row 7) by its own E_placement / E_bake, and see where B/G lands.

  before   the shipped atlas frame, linear     B/G 1.356   (impostor_diag_atlas.json)
  target   the same tree as a MESH in the Phase 5 Cycles reference at station 2, linear B/G 0.650
           (impostor_diag_ref.json `foliage_p80.b_over_g_linear`; its display-referred form is 0.648)

`foliage_p80` is a fixed quantile rather than a sky test (review r1 finding 9), so the target carries a bias
the 147 deg hue gap dwarfs; it is the direction and the size of the move that this test is for, not the third
decimal. PASS = B/G moves toward the target by at least half the gap and does not overshoot below it.
"""
import json
import os
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
MAIN = Path(os.environ.get("PFA_MAIN_ROOT", "/Users/dk/Projects/3d render blender 3rd attempt building"))
OUT = ROOT / "export" / "out" / "gate3"
TF = OUT / "trees_far"
REC = OUT / "bake"
PROTO = "ENV_tree_broadleaf_s53_LOD1"
PLACEMENT = "TREEFAR_000"


def hue_deg(rgb):
    r, g, b = [float(x) for x in rgb]
    mx, mn = max(r, g, b), min(r, g, b)
    d = mx - mn
    if d <= 0:
        return 0.0
    if mx == r:
        h = 60.0 * (((g - b) / d) % 6.0)
    elif mx == g:
        h = 60.0 * ((b - r) / d + 2.0)
    else:
        h = 60.0 * ((r - g) / d + 4.0)
    return round(h, 1)


def main():
    atlas = json.loads((OUT / "impostor_diag_atlas.json").read_text())["prototypes"][PROTO]
    frame = atlas["2048"]["cam02_frame"]
    ref = json.loads((OUT / "impostor_diag_ref.json").read_text())["foliage_p80"]
    eb = json.loads((REC / f"tfeb_{PROTO}.json").read_text())["items"][0]

    ep = None
    for f in sorted(REC.glob("tfirr_*.json")):
        rec = json.loads(f.read_text())
        for it in rec["results"]["shadow"]["items"]:
            if it["object"] == PLACEMENT:
                ep, ep_job = it, f.stem
    assert ep is not None, f"{PLACEMENT} is in no tfirr_* record yet"

    E_b = np.array(eb["mean_nonzero"], dtype=float)
    E_p = np.array(ep["mean_nonzero"], dtype=float)
    assert E_b.min() > 0, f"E_bake has a zero channel: {list(E_b)}"
    ratio = E_p / E_b
    before = np.array(frame["mean_rgb"], dtype=float)
    after = before * ratio

    bg_before = float(before[2] / before[1])
    bg_after = float(after[2] / after[1])
    bg_target = float(ref["b_over_g_linear"])
    gap = bg_before - bg_target
    moved = bg_before - bg_after
    passed = bool(moved >= 0.5 * gap and bg_after >= bg_target * 0.5)

    out = dict(
        test="review r1 finding 6: one placement, before the other 15 E_bake jobs",
        prototype=PROTO, placement=PLACEMENT, dist_m=atlas["nearest_cam02_m"],
        frame=dict(col=frame["col"], row=frame["row"]),
        E_bake=[round(x, 6) for x in E_b], E_bake_cov=eb["coverage"], E_bake_job=f"tfeb_{PROTO}",
        E_placement=[round(x, 6) for x in E_p], E_placement_cov=ep["coverage"], E_placement_job=ep_job,
        ratio=[round(float(x), 4) for x in ratio],
        ratio_bg=round(float((ratio[2] / ratio[1])), 4),
        crown_before=[round(x, 5) for x in before], crown_after=[round(float(x), 5) for x in after],
        hue_before=hue_deg(before), hue_after=hue_deg(after), hue_target=ref["hue_linear_deg"],
        b_over_g_before=round(bg_before, 4), b_over_g_after=round(bg_after, 4),
        b_over_g_target=round(bg_target, 4),
        gap_before=round(gap, 4), moved=round(float(moved), 4),
        moved_pct_of_gap=round(100.0 * float(moved) / gap, 1) if gap else None,
        r_over_g_before=round(float(before[0] / before[1]), 4),
        r_over_g_after=round(float(after[0] / after[1]), 4),
        r_over_g_target=round(float(ref["mean_linear"][0] / ref["mean_linear"][1]), 4),
        luminance_scale=round(float((after @ [0.2126, 0.7152, 0.0722])
                                    / (before @ [0.2126, 0.7152, 0.0722])), 4),
        verdict="PASS" if passed else "FAIL",
        note=("PASS = B/G closes at least half the gap to the reference without falling below half of it. "
              "The reference is impostor_diag_ref.json foliage_p80, a fixed quantile (review finding 9)."))
    (TF / "ratio_check.json").write_text(json.dumps(out, indent=1) + "\n")
    for k in ("E_bake", "E_placement", "ratio", "crown_before", "crown_after", "b_over_g_before",
              "b_over_g_after", "b_over_g_target", "moved_pct_of_gap", "hue_before", "hue_after",
              "hue_target", "luminance_scale", "verdict"):
        print(f"  {k:20s} {out[k]}")


main()
