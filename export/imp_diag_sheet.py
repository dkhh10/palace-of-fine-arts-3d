"""6c item 1, part D: the one composite the brief asks for.

    python3 export/imp_diag_sheet.py --proto <name> --col C --row R --index <tree_far index> \
        --out renders/web/960/6c_impostor_diag.png

2 rows x N/2 columns at 320 px, every panel display-referred (AgX High Contrast, -2.833 EV). Panel 1 is always
the tree as a MESH in the Phase 5 Cycles reference at station 2 (the ground truth); the rest are the display
PNGs imp_diag_view.py wrote, in --tags order:
  atlas    the SHIPPED atlas frame for the direction station 2 looks from
  asis     a fresh Cycles render of the same prototype at the same view, the blend's own world
  diffuse  the same with the world's DIFFUSE branch on every ray (the candidate re-bake)
  sunonly  the same with no world at all   skyonly  the same with every light hidden
"""
import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gate3_common as g3          # noqa: E402
import imp_diag_ref as dref        # noqa: E402

MAIN = Path("/Users/dk/Projects/3d render blender 3rd attempt building")
P = 320


def to_panel(rgb_u8, alpha=None, bg=90):
    """(h, w, 3) top-down uint8 -> a P x P panel, letterboxed on mid grey, nearest-neighbour."""
    h, w = rgb_u8.shape[:2]
    if alpha is not None:
        a = alpha[..., None].astype(np.float32)
        rgb_u8 = (rgb_u8.astype(np.float32) * a + bg * (1.0 - a)).astype(np.uint8)
    s = min(P / h, P / w)
    nh, nw = max(int(h * s), 1), max(int(w * s), 1)
    yi = (np.arange(nh) / s).astype(int).clip(0, h - 1)
    xi = (np.arange(nw) / s).astype(int).clip(0, w - 1)
    sc = rgb_u8[yi][:, xi]
    out = np.full((P, P, 3), bg, dtype=np.uint8)
    y0, x0 = (P - nh) // 2, (P - nw) // 2
    out[y0:y0 + nh, x0:x0 + nw] = sc
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--proto", required=True)
    ap.add_argument("--col", type=int, required=True)
    ap.add_argument("--row", type=int, required=True)
    ap.add_argument("--index", type=int, default=0)
    ap.add_argument("--ref", default=str(MAIN / "renders/previews/qa/round13_02_lagoon_ne_threequarter_cycles.png"))
    ap.add_argument("--tags", default="atlas,asis,diffuse,sunonly,skyonly")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    man = json.load(open(dref.MANIFEST))
    imp = man["impostors"]

    # ---- the reference crop, re-derived here so the sheet and the numbers cannot drift apart
    t = man["tree_far"][a.index]
    pr = imp["prototypes"][imp["prototype_map"][t["prototype"]]]
    s = t["height_m"] / pr["height_above_base_m"]
    ctr = np.array(t["trunk_base"], dtype=np.float64) + np.array([0.0, 0.0, pr["centre_z_m"] * s])
    st = man["stations"]["CAM_qa_02_lagoon_ne_threequarter"]
    cam = np.array(st["location"], dtype=np.float64)
    R = dref.euler_matrix(*st["rotation_euler_xyz"])
    right, up, fwd = R @ np.array([1., 0, 0]), R @ np.array([0, 1., 0]), R @ np.array([0, 0, -1.])
    img = dref.read_png_any(a.ref)
    H, W = img.shape[:2]
    tx = (st["sensor_width_mm"] * 0.5) / st["lens_mm"]
    ty = (st["sensor_width_mm"] * H / W * 0.5) / st["lens_mm"]

    def project(p):
        d = p - cam
        z = float(fwd @ d)
        return ((float(right @ d) / z / tx * 0.5 + 0.5) * W, (1.0 - (float(up @ d) / z / ty * 0.5 + 0.5)) * H)

    cxp, cyp = project(ctr)
    rpx = abs(project(ctr + right * pr["radius_m"] * s)[0] - cxp)
    x0, x1 = max(int(cxp - rpx), 0), min(int(cxp + rpx), W)
    y0, y1 = max(int(cyp - rpx), 0), min(int(cyp + rpx), H)
    panels = [to_panel(img[y0:y1, x0:x1, :3])]

    # ---- the three display PNGs imp_diag_view.py wrote (bottom-up; flip to top-down for the sheet)
    d = g3.OUT / "impostor"
    for tag in a.tags.split(","):
        p = d / f"diag_{a.proto}_{a.col}_{a.row}_{tag}.png"
        if not p.exists():
            panels.append(np.full((P, P, 3), 60, dtype=np.uint8))
            continue
        # Blender's PNG writer uses adaptive row filters, which gate3_common.read_png does not decode
        u8 = dref.read_png_any(p)
        al = u8[..., 3].astype(np.float32) / 255.0 if u8.shape[-1] == 4 else None
        panels.append(to_panel(u8[..., :3], al))
    cols = (len(panels) + 1) // 2
    while len(panels) < 2 * cols:
        panels.append(np.full((P, P, 3), 60, dtype=np.uint8))
    sheet = np.concatenate([np.concatenate(panels[:cols], axis=1),
                            np.concatenate(panels[cols:], axis=1)], axis=0)
    for i in range(1, cols):
        sheet[:, i * P - 1:i * P + 1] = 200
    sheet[P - 1:P + 1, :] = 200
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    g3.write_png_rgb8(out, np.ascontiguousarray(sheet[::-1]))
    print(f"[diag] wrote {out}  ({sheet.shape[1]}x{sheet.shape[0]})")


if __name__ == "__main__":
    main()
