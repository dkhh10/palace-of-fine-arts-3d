"""Phase 10 r1, steps 8 (maps) + 10 -- the projected atlas -> the shader's ratio map and mask (numpy, no bpy).

    .venv-p10/bin/python scripts/mat_p10_texture.py      # -> assets/textures/projection2/PFA_p10_ratio.png, PFA_p10_mask.png

The shader multiplies the finished procedural albedo by `ratio` (x confidence x weight), so the map carries only
SPATIAL structure, mean 1 by construction:
  reference  per material class (column meshes vs concrete) x normal bin (soffit nz < -0.5 / wall / top nz > 0.5):
             the weighted median colour of the projected atlas over its well-seen texels (>= 5 views).  Dividing per
             normal bin keeps the photos' shade in soffits and on tops out of the map (the render shades those itself).
  bands      LF = masked Gaussian at 0.75 m, MF = 0.22 m (round 9's 10 / 3 hero px), HF (the fine grain) is NOT
             carried -- the procedural keeps its own; ratio = LF_c x (MF / LF)^0.5, per channel, clipped 0.65..1.55
             (LF) and 0.62..1.62 (MF).  The global chroma stays round 9's `Albedo Tint` (M_chroma) on the base albedo.
  mask       R = confidence = clip(sum of view weights) x clip((views - 1) / 4) x (the LF ratio stayed inside its clip),
             G = views / 20, B = texel covered.
Layout: the four groups are the 1024 quadrants (g % 2, g // 2) of one 2048 image, exactly UVBake's quadrant layout
(inset 1 %, so the corner (0, 0) that meshes WITHOUT UVBake sample is empty and has confidence 0).  PNG rows are
top-down (Blender's v = 0 is the bottom row).  Stored ratio / 2 (decode x2), 8-bit, Non-Color, as round 9's map.
Empty texels are dilated 6 px so bilinear lookups at island edges never mix in black.
"""
import sys, json
import numpy as np
import cv2
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
import mat_p10_common as C

VARIANT = {0: "col_d", 1: "col_a", 2: "col_d", 3: "col_a"}      # the lower robust inter-view spread per group
TPM = {0: 21.5, 1: 25.0, 2: 32.0, 3: 68.0}                      # texels per metre on weight-1 faces at 1024
LF_M, MF_M = 0.75, 0.22
LF_LO, LF_HI, MF_LO, MF_HI = 0.65, 1.55, 0.62, 1.62
Q = 1024


def mblur(img, m, sigma):
    k = int(3 * sigma) * 2 + 1
    num = cv2.GaussianBlur(img * m[..., None], (k, k), sigma)
    den = cv2.GaussianBlur(m.astype(np.float32), (k, k), sigma)
    return num / np.maximum(den, 1e-6)[..., None], den


def wmed(x, w):
    o = np.argsort(x); cw = np.cumsum(w[o]); return float(x[o][np.searchsorted(cw, 0.5 * cw[-1])])


def dilate(img, m, n):
    img = img.copy(); m = m.copy()
    for _ in range(n):
        s, d = mblur(img, m.astype(np.float32), 1.0)
        grow = (~m) & (d > 0.05)
        img[grow] = s[grow]; m |= grow
    return img, m


if __name__ == "__main__":
    tris = np.load(C.WORK / "uvbake_tris.npz")
    names = list(tris["names"])
    ratio_img = np.ones((2 * Q, 2 * Q, 3), np.float32)
    mask_img = np.zeros((2 * Q, 2 * Q, 3), np.float32)
    stats = {}
    for g in range(4):
        a = np.load(C.WORK / f"atlas_g{g}.npz"); p = np.load(C.WORK / f"proj_g{g}.npz")
        valid = p["valid"]; ids = a["mesh"][valid]
        nz = a["lnrm"][valid][:, 2]
        col = p[VARIANT[g]].astype(np.float32); wsum = p["weight"]; views = p["views"]
        seen = (wsum > 0) & (col.sum(1) > 0)
        is_col = np.array(["column" in names[i] or "colbase" in names[i] for i in ids])
        nbin = np.where(nz < -0.5, 0, np.where(nz > 0.5, 2, 1))
        ref = np.ones_like(col)
        for c_ in (False, True):
            for b in (0, 1, 2):
                m = (is_col == c_) & (nbin == b) & seen & (views >= 5)
                if m.sum() < 200:
                    m = (is_col == c_) & seen & (views >= 5)
                if m.sum() < 200:
                    continue
                r = np.array([wmed(col[m, ch], wsum[m]) for ch in range(3)], np.float32)
                ref[(is_col == c_) & (nbin == b)] = r
        rel = np.where(seen[:, None], col / np.maximum(ref, 1e-5), 1.0)
        # to image space
        R = np.ones((Q, Q, 3), np.float32); M = np.zeros((Q, Q), bool)
        R[valid] = rel; M[valid] = seen
        lf, _ = mblur(R, M, LF_M * TPM[g]); mf, _ = mblur(R, M, MF_M * TPM[g])
        lf_c = np.clip(lf, LF_LO, LF_HI)
        ratio = lf_c * np.clip(mf / np.maximum(lf, 1e-4), MF_LO / LF_HI, MF_HI / LF_LO) ** 0.5
        ratio = np.clip(ratio, MF_LO, MF_HI)
        inclip = np.exp(-np.abs(np.log(np.maximum(lf.mean(-1), 1e-4) / np.maximum(lf_c.mean(-1), 1e-4))) / 0.1)
        Wimg = np.zeros((Q, Q), np.float32); Vimg = np.zeros((Q, Q), np.float32)
        Wimg[valid] = wsum; Vimg[valid] = views
        conf = np.clip(Wimg / 1.0, 0, 1) * np.clip((Vimg - 1) / 4.0, 0, 1) * inclip * M
        ratio, Md = dilate(np.where(M[..., None], ratio, 1.0), M.copy(), 6)
        ratio[~Md] = 1.0
        qx, qy = g % 2, g // 2
        ys = slice(qy * Q, (qy + 1) * Q); xs = slice(qx * Q, (qx + 1) * Q)
        ratio_img[ys, xs] = ratio
        mask_img[ys, xs, 0] = conf; mask_img[ys, xs, 1] = np.clip(Vimg / 20.0, 0, 1); mask_img[ys, xs, 2] = M
        L = lambda x: x[..., 0] * 0.2126 + x[..., 1] * 0.7152 + x[..., 2] * 0.0722
        m = M & (conf > 0.5)
        stats[g] = dict(ref_concrete=ref[~is_col][0].tolist() if (~is_col).any() else None,
                        ref_column=ref[is_col][0].tolist() if is_col.any() else None,
                        conf_gt_half_pct_of_texels=100.0 * float(m.sum()) / max(int(valid.sum()), 1),
                        ratio_lum_mean=float(L(ratio[m]).mean()) if m.any() else None,
                        ratio_lum_std=float(L(ratio[m]).std()) if m.any() else None)
        print(f"[tex] group {g}: {json.dumps(stats[g])}")
    ratio_img[0:4, 0:4] = 1.0; mask_img[0:4, 0:4] = 0.0          # the (0, 0) corner: never a texel (inset)
    out = C.P2
    cv2.imwrite(str(out / "PFA_p10_ratio.png"), (np.clip(ratio_img / 2.0, 0, 1)[::-1, :, ::-1] * 255 + 0.5).astype(np.uint8))
    cv2.imwrite(str(out / "PFA_p10_mask.png"), (np.clip(mask_img, 0, 1)[::-1, :, ::-1] * 255 + 0.5).astype(np.uint8))
    (C.WORK / "texture_stats.json").write_text(json.dumps(stats, indent=1))
    mb = sum((out / f).stat().st_size for f in ("PFA_p10_ratio.png", "PFA_p10_mask.png")) / 1e6
    print(f"[tex] wrote PFA_p10_ratio.png + PFA_p10_mask.png ({2 * Q}x{2 * Q}), {mb:.1f} MB")
