#!/usr/bin/env python3
"""Phase 8b, item (a)+(b): READ-ONLY probe of the composed far-tree impostor atlases.

No Blender, no GPU, no writes outside --out. Answers: where does the far-tree crown's
opacity come from - the bake's alpha, the 2K->1K reduction, the viewer's 0.33 alpha test,
or the 3-frame octahedral blend?

Sources (read-only):
  <atlas-dir>/gate3_imp_<proto>_albedo_{1024,2048}.png   straight alpha in A (bake_lm.py `impostor`)
  export/out/gate3/impostor_diag_atlas.json              the cam02 frame (col,row) per prototype
  export/out/gate3/impostor_diag_ref.json                the Cycles crown box at station 2
  renders/previews/qa/round13_02_lagoon_ne_threequarter_cycles.png

Usage:
  python3 export/p8_atlas_probe.py [--atlas-dir DIR] [--out DIR] [--crops]
"""
import argparse, json, os, sys
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
MAIN = "/Users/dk/Projects/3d render blender 3rd attempt building"

GRID = 12                       # gate3_common.IMP_GRID
GUTTER_2K = 4                   # gate3_common.IMP_GUTTER_PX at IMP_FRAME_PX = 170
ALPHA_TEST = 0.33               # web/src/impostors.js ALPHA_TEST
PROTOS = ["ENV_tree_broadleaf_s53_LOD1", "ENV_tree_cypress_s3_LOD1", "ENV_tree_pine_s7_LOD1"]


def frame_geom(px):
    """(frame size, gutter, inner size) for an atlas of `px`; 2048 -> 170/4/162, 1024 -> 85/2/81."""
    f = 170 if px == 2048 else 85
    g = GUTTER_2K if px == 2048 else GUTTER_2K // 2
    return f, g, f - 2 * g


def frame_alpha(atlas, px, col, row):
    """Alpha of one octahedral frame's INNER region (the gutter is bake padding, never sampled)."""
    f, g, _ = frame_geom(px)
    y0, x0 = row * f, col * f
    return atlas[y0 + g:y0 + f - g, x0 + g:x0 + f - g, 3].astype(np.float32) / 255.0


def bands(a):
    """Thirds of the frame's OCCUPIED vertical extent: (crown top, crown whole, trunk band).
    The atlas is written bottom-up (bake_lm.py), so row 0 of the array is the trunk."""
    occ = np.where((a > 0.01).any(axis=1))[0]
    if occ.size == 0:
        return None, None, None
    lo, hi = int(occ[0]), int(occ[-1])
    n = max((hi - lo + 1) // 3, 1)
    return a[hi - n + 1:hi + 1], a[lo + n:hi + 1], a[lo:lo + n]


def hist(a):
    """The alpha histogram the brief asks for, as shares of the band's texels."""
    n = a.size
    if n == 0:
        return {}
    return dict(
        texels=int(n),
        mean=round(float(a.mean()), 4),
        empty_pct=round(float((a <= 0.0).mean()) * 100, 2),
        semi_pct=round(float(((a > 0.0) & (a < 1.0)).mean()) * 100, 2),
        opaque_pct=round(float((a >= 1.0).mean()) * 100, 2),
        # of the texels that carry anything at all:
        covered_semi_pct=round(float(((a > 0.0) & (a < 1.0)).sum() / max((a > 0.0).sum(), 1)) * 100, 2),
        # what the viewer's hard cut does to them:
        cut_to_sky_pct=round(float(((a > 0.0) & (a < ALPHA_TEST)).mean()) * 100, 2),
        forced_opaque_pct=round(float(((a >= ALPHA_TEST) & (a < 1.0)).mean()) * 100, 2),
    )


def interior_open_pct(a, thr):
    """Share of SKY inside the silhouette: per row, the texels between the first and last covered
    texel that are below `thr`. This is the 'sky through the twigs' the Cycles reference shows."""
    inside = tot = 0
    for r in a:
        occ = np.where(r > 0.01)[0]
        if occ.size < 2:
            continue
        seg = r[occ[0]:occ[-1] + 1]
        tot += seg.size
        inside += int((seg < thr).sum())
    return (round(100.0 * inside / tot, 2), tot) if tot else (0.0, 0)


def transitions_per_100px(mask, scale=1.0):
    """Silhouette detail density: foliage<->gap crossings per 100 SCREEN px, per row.
    `scale` is how many screen px one column of `mask` covers. This is the one number that
    compares an atlas frame with a Cycles crop directly: it is resolution-independent."""
    rows = [r for r in mask if r.any()]
    if not rows:
        return 0.0
    tr = sum(int(np.abs(np.diff(r.astype(np.int8))).sum()) for r in rows)
    span = sum(int(np.where(r)[0][-1] - np.where(r)[0][0] + 1) for r in rows) * scale
    return round(100.0 * tr / max(span, 1e-6), 2)


def octa_dir(col, row):
    u = col / (GRID - 1.0) * 2.0 - 1.0
    v = row / (GRID - 1.0) * 2.0 - 1.0
    z = 1.0 - abs(u) - abs(v)
    d = np.array([u, v, z]) if z >= 0 else np.array(
        [(1 - abs(v)) * (1 if u >= 0 else -1), (1 - abs(u)) * (1 if v >= 0 else -1), z])
    return d / np.linalg.norm(d)


def blend3(atlas, px, col, row):
    """The viewer blends the octahedral cell's THREE frames (impostors.js, 12 taps over 3 frames).
    Equal weights is the cell centre - the worst case for a silhouette, and the honest average."""
    cells = [(col, row), (min(col + 1, GRID - 1), row), (col, min(row + 1, GRID - 1))]
    return np.mean([frame_alpha(atlas, px, c, r) for c, r in cells], axis=0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--atlas-dir", default=os.path.join(
        MAIN, ".claude/worktrees/phase6-bake/export/out/gate3/impostor"))
    ap.add_argument("--gate3", default=os.path.join(MAIN, "export/out/gate3"))
    ap.add_argument("--out", default=None)
    ap.add_argument("--crops", action="store_true", help="write the 100 %% crop pair (item b)")
    args = ap.parse_args()

    diag = json.load(open(os.path.join(args.gate3, "impostor_diag_atlas.json")))
    ref = json.load(open(os.path.join(args.gate3, "impostor_diag_ref.json")))
    report = {"alpha_test": ALPHA_TEST, "grid": GRID, "prototypes": {}}

    for proto in PROTOS:
        e = diag["prototypes"][proto]
        col, row = e["1024"]["cam02_frame"]["col"], e["1024"]["cam02_frame"]["row"]
        pr = {"cam02_frame": [col, row], "nearest_cam02_m": e["nearest_cam02_m"],
              "baked_dir": e["1024"]["cam02_frame"]["baked_dir"], "res": {}}
        for px in (2048, 1024):
            p = os.path.join(args.atlas_dir, f"gate3_imp_{proto}_albedo_{px}.png")
            atlas = np.asarray(Image.open(p).convert("RGBA"))
            a = frame_alpha(atlas, px, col, row)
            top, crown, trunk = bands(a)
            f, g, inner = frame_geom(px)
            b = blend3(atlas, px, col, row)
            _, bcrown, _ = bands(b)
            # one atlas texel covers this many screen px at the station-2 crown, 1920x1080
            scale = (2.0 * ref["radius_px"]) / float(inner)
            pr["res"][str(px)] = {
                "frame_px": f, "inner_px": inner, "texel_screen_px_at_cam02": round(scale, 2),
                "crown_body_texels": int((a > ALPHA_TEST).sum()),
                "frame_all": hist(a), "crown_top": hist(top), "trunk_band": hist(trunk),
                "crown_interior_sky_pct": interior_open_pct(crown, ALPHA_TEST)[0],
                "crown_interior_texels": interior_open_pct(crown, ALPHA_TEST)[1],
                "crown_interior_sky_pct_after_3frame_blend": interior_open_pct(bcrown, ALPHA_TEST)[0],
                "blend3_crown": hist(bcrown),
                "crown_transitions_per_100_screen_px": transitions_per_100px(crown > ALPHA_TEST, scale),
                "crown_transitions_per_100_texels": transitions_per_100px(crown > ALPHA_TEST, 1.0),
                # item (c) option 4: does raising the cut in the compose buy back silhouette detail?
                "cut_sweep": {str(c): {
                    "opaque_pct": round(float((crown >= c).mean()) * 100, 2),
                    "interior_sky_pct": interior_open_pct(crown, c)[0],
                    "transitions_per_100_screen_px": transitions_per_100px(crown > c, scale),
                } for c in (0.20, 0.33, 0.50, 0.70)},
            }
        report["prototypes"][proto] = pr

    # ---- item (b): the Cycles reference crown at station 2, same box as impostor_diag_ref
    rp = os.path.join(MAIN, "renders/previews/qa/round13_02_lagoon_ne_threequarter_cycles.png")
    img = np.asarray(Image.open(rp).convert("RGB")).astype(np.float32)
    x0, y0, x1, y1 = ref["box"]
    crop = img[y0:y1, x0:x1]
    lum = crop @ np.array([0.2126, 0.7152, 0.0722])
    report["cycles_ref"] = {
        "png": os.path.basename(rp), "render_px": list(img.shape[1::-1]),
        "prototype": ref["prototype"], "dist_m": ref["dist_m"],
        "crown_box_px": ref["box"], "crown_box_wh": [x1 - x0, y1 - y0],
        "crown_radius_px": ref["radius_px"],
        # foliage is sRGB ~18 (diag_ref foliage_p80); anything over 80 in this box is sky/backlight
        "sky_through_crown_pct_lum_gt_80": round(float((lum > 80).mean()) * 100, 2),
        "sky_through_crown_pct_lum_gt_120": round(float((lum > 120).mean()) * 100, 2),
        "lum_p10": round(float(np.percentile(lum, 10)), 1),
        "lum_p50": round(float(np.percentile(lum, 50)), 1),
        "lum_p90": round(float(np.percentile(lum, 90)), 1),
        # the crown's own silhouette detail: foliage is sRGB ~18 (diag_ref foliage_p80), every gap
        # (sky, backlit leaf, the pale colonnade behind) is brighter. Same measure as the atlas frame's.
        "foliage_transitions_per_100_screen_px_lum_lt_40":
            transitions_per_100px(lum < 40, 1.0),
        "foliage_transitions_per_100_screen_px_lum_lt_60":
            transitions_per_100px(lum < 60, 1.0),
        "foliage_pct_lum_lt_40": round(float((lum < 40).mean()) * 100, 2),
    }
    # magnification: the bake maps the bounding-sphere diameter to `inner` px of the frame
    for px in (2048, 1024):
        _, _, inner = frame_geom(px)
        mag = (2.0 * ref["radius_px"]) / float(inner)
        report["cycles_ref"][f"magnification_{px}_at_1920x1080"] = round(mag, 2)
        report["cycles_ref"][f"magnification_{px}_at_2560x1440"] = round(mag * 2560 / 1920.0, 2)

    out = args.out or os.path.join(ROOT, "export", "out", "p8")
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "p8_atlas_probe.json"), "w") as fh:
        json.dump(report, fh, indent=1)

    if args.crops:
        # 100 % crop pair: the Cycles crown, and the cam02 atlas frame at the SAME screen size
        proto = ref["prototype"]
        e = diag["prototypes"][proto]["1024"]["cam02_frame"]
        atlas = np.asarray(Image.open(os.path.join(
            args.atlas_dir, f"gate3_imp_{proto}_albedo_1024.png")).convert("RGBA"))
        f, g, _ = frame_geom(1024)
        fr = atlas[e["row"] * f + g:(e["row"] + 1) * f - g, e["col"] * f + g:(e["col"] + 1) * f - g]
        h, w = crop.shape[:2]
        fi = Image.fromarray(fr).resize((w, h), Image.NEAREST)
        # alpha as a mask next to it, so the silhouette is legible
        am = Image.fromarray(np.repeat(fr[..., 3:4], 3, axis=2)).resize((w, h), Image.NEAREST)
        sheet = Image.new("RGB", (w * 3 + 16, h), (24, 24, 24))
        sheet.paste(Image.fromarray(crop.astype(np.uint8)), (0, 0))
        sheet.paste(fi.convert("RGB"), (w + 8, 0))
        sheet.paste(am, (w * 2 + 16, 0))
        sheet.save(os.path.join(out, "p8_crownpair_100pct.png"))

    json.dump(report, sys.stdout, indent=1)
    print()


if __name__ == "__main__":
    main()
