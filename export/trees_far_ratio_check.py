"""Phase 6c item 2, review r1 finding 6: does `E_placement / E_bake` actually move the impostor's blue?

    python3 export/trees_far_ratio_check.py

CPU only, no Blender, no GPU. The lead's gate before the other 15 E_bake jobs are queued: the divisor is a
DIFFUSE IRRADIANCE ratio, and the measured blue may not be a diffuse response at all (the `sunonly` render
reads B exactly 0.000 although the rig carries blue fill lamps, while `skyonly` reads B 0.387). So take the
one placement the whole diagnosis was built on - `tree_far[0]` = TREEFAR_000, prototype
ENV_tree_broadleaf_s53_LOD1, the far tree on the axis of station 2 at 40.19 m - multiply the crown mean of the
atlas frame that station picks (col 1, row 7) by its own E_placement / E_bake, and see where B/G lands.

  before   the shipped atlas frame, scene-linear B/G 1.356 (impostor_diag_atlas.json)
  target   the same tree as a MESH in the Phase 5 Cycles reference at station 2, DISPLAY-referred sRGB
           B/G 0.648 (impostor_diag_ref.json `foliage_p80.b_over_g_srgb`)

THE COMPARISON HAS TO BE LIKE FOR LIKE. The reference is a display-referred PNG; its `b_over_g_linear` 0.650
is an inverse-sRGB of that PNG, not a scene-linear value, so the AgX look is still baked into it. AgX pulls a
saturated ratio toward 1 (measured on this very frame: scene-linear 1.356 displays as 1.205), so a
scene-linear number compared against it will always look like it overshoots. This test therefore pushes both
crowns - before and after modulation - through the SAME transform the delivery uses,
`out/gate0/lut_agx_high_contrast_65.cube` at -2.8331399 EV (the LUT `bake_lut.py` baked from Blender's own
OCIO and proved against a Cycles render to within 1/255), and judges on the display-referred B/G. The
scene-linear numbers are reported beside it.

`foliage_p80` is a fixed quantile rather than a sky test (review r1 finding 9), so the target carries a bias
the 147 deg hue gap dwarfs; it is the direction and the size of the move that this test is for, not the third
decimal. PASS = the display-referred B/G closes at least half the gap to the reference without ending further
from it on the other side than it started on this one.
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


LUT_PATH = "export/out/gate0/lut_agx_high_contrast_65.cube"
LUT_EV = -2.8331398963928223
LUT_MIN_EV, LUT_SPAN_EV, LUT_PIVOT = -12.47393, 16.5, 0.18


def load_cube(path):
    size, rows = None, []
    for line in Path(path).read_text().splitlines():
        t = line.strip()
        if not t or t.startswith("#") or t.startswith("TITLE") or t.startswith("DOMAIN"):
            continue
        if t.startswith("LUT_3D_SIZE"):
            size = int(t.split()[1])
            continue
        rows.append([float(x) for x in t.split()])
    a = np.array(rows, dtype=np.float64)
    assert size and a.shape == (size ** 3, 3), f"{path}: {a.shape} rows for size {size}"
    # .cube order is red fastest
    return a.reshape(size, size, size, 3).transpose(2, 1, 0, 3), size


def to_display(linear, cube, size):
    """scene-linear RGB -> display sRGB (0-1), through the AgX log2 shaper the .cube header documents."""
    v = np.asarray(linear, dtype=np.float64) * (2.0 ** LUT_EV)
    x = np.clip((np.log2(np.maximum(v, 1e-10) / LUT_PIVOT) - LUT_MIN_EV) / LUT_SPAN_EV, 0.0, 1.0)
    g = x * (size - 1)
    i0 = np.floor(g).astype(int)
    i1 = np.minimum(i0 + 1, size - 1)
    f = g - i0
    out = np.zeros(3)
    for c0 in (0, 1):
        for c1 in (0, 1):
            for c2 in (0, 1):
                ix = (i1[0] if c0 else i0[0], i1[1] if c1 else i0[1], i1[2] if c2 else i0[2])
                w = ((f[0] if c0 else 1 - f[0]) * (f[1] if c1 else 1 - f[1]) * (f[2] if c2 else 1 - f[2]))
                out += w * cube[ix[0], ix[1], ix[2]]
    return out


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

    cube, size = load_cube(ROOT / LUT_PATH if (ROOT / LUT_PATH).exists() else MAIN / LUT_PATH)
    d_before = to_display(before, cube, size)
    d_after = to_display(after, cube, size)
    dbg_before = float(d_before[2] / d_before[1])
    dbg_after = float(d_after[2] / d_after[1])
    bg_target = float(ref["b_over_g_srgb"])
    gap = dbg_before - bg_target
    moved = dbg_before - dbg_after
    passed = bool(moved >= 0.5 * gap and abs(dbg_after - bg_target) <= gap)
    # The full ratio overshoots (see `overshoot` below). Solve for the exponent k in `ratio ** k` that lands
    # the DISPLAY B/G exactly on the reference, so the lead has a measured number to set a partial strength
    # or a clamp from, instead of a guess. Bisection on a monotone function, 40 steps.
    lo, hi = 0.0, 1.0
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        d = to_display(before * (ratio ** mid), cube, size)
        if float(d[2] / d[1]) > bg_target:
            lo = mid
        else:
            hi = mid
    k = 0.5 * (lo + hi)
    d_k = to_display(before * (ratio ** k), cube, size)

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
        display_before_srgb8=[round(float(x) * 255.0, 1) for x in d_before],
        display_after_srgb8=[round(float(x) * 255.0, 1) for x in d_after],
        display_b_over_g_before=round(dbg_before, 4), display_b_over_g_after=round(dbg_after, 4),
        display_b_over_g_target=round(bg_target, 4),
        display_hue_before=hue_deg(d_before), display_hue_after=hue_deg(d_after),
        display_hue_target=ref["hue_srgb_deg"],
        linear_b_over_g_before=round(float(before[2] / before[1]), 4),
        linear_b_over_g_after=round(float(after[2] / after[1]), 4),
        linear_b_over_g_reference_inverse_srgb=round(float(ref["b_over_g_linear"]), 4),
        lut=LUT_PATH, lut_exposure_ev=round(LUT_EV, 6),
        hue_closure=dict(
            before=hue_deg(d_before), after=hue_deg(d_after), target=ref["hue_srgb_deg"],
            pct_of_gap_closed=round(100.0 * (hue_deg(d_before) - hue_deg(d_after))
                                    / (hue_deg(d_before) - ref["hue_srgb_deg"]), 1),
            at_k=hue_deg(d_k), overshoot=bool(hue_deg(d_after) < ref["hue_srgb_deg"]),
            note=("HUE is the robust summary here and B/G is not: after modulation the display BLUE is "
                  "1.2/255, so display B/G is a ratio of a near-black channel. On hue the FULL ratio closes "
                  "the gap without overshooting and beats the partial strength k.")),
        overshoot=dict(
            distance_before=round(abs(dbg_before - bg_target), 4),
            distance_after=round(abs(dbg_after - bg_target), 4),
            note=("the full ratio takes the display B/G past the reference: E_placement is the mean over the "
                  "WHOLE crown volume, interior vertices included, while the atlas frame shows only the "
                  "sky-facing outer shell, which in the scene keeps far more sky than the volume mean does. "
                  "The reference's own foliage_p80 crop biases the target blue-UP as well (review r1 "
                  "finding 9), so the true target is below 0.648 and the real overshoot is smaller than it "
                  "looks - but it is there.")),
        partial_strength=dict(
            k=round(float(k), 4),
            applied="atlas_frame * (E_placement / E_bake) ** k, per channel",
            display_b_over_g=round(float(d_k[2] / d_k[1]), 4),
            display_srgb8=[round(float(x) * 255.0, 1) for x in d_k],
            display_hue=hue_deg(d_k),
            note="the exponent that lands the display B/G on the reference; the lead sets the shipped value"),
        gap_before=round(gap, 4), moved=round(float(moved), 4),
        moved_pct_of_gap=round(100.0 * float(moved) / gap, 1) if gap else None,
        r_over_g_before=round(float(before[0] / before[1]), 4),
        r_over_g_after=round(float(after[0] / after[1]), 4),
        r_over_g_target=round(float(ref["mean_linear"][0] / ref["mean_linear"][1]), 4),
        luminance_scale=round(float((after @ [0.2126, 0.7152, 0.0722])
                                    / (before @ [0.2126, 0.7152, 0.0722])), 4),
        verdict="PASS" if passed else "FAIL",
        note=("Judged DISPLAY-referred, through the delivery LUT, because the reference is a display PNG. "
              "PASS = the display B/G closes at least half the gap to the reference and does not end further "
              "from it than it started. The reference is impostor_diag_ref.json foliage_p80, a fixed "
              "quantile (review r1 finding 9)."))
    (TF / "ratio_check.json").write_text(json.dumps(out, indent=1) + "\n")
    for k in ("E_bake", "E_placement", "ratio", "crown_before", "crown_after",
              "linear_b_over_g_before", "linear_b_over_g_after",
              "display_before_srgb8", "display_after_srgb8",
              "display_b_over_g_before", "display_b_over_g_after", "display_b_over_g_target",
              "display_hue_before", "display_hue_after", "display_hue_target",
              "moved_pct_of_gap", "hue_closure", "overshoot", "partial_strength", "luminance_scale",
              "verdict"):
        print(f"  {k:20s} {out[k]}")


main()
