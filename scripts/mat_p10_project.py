"""Phase 10 r1, steps 6 + 7 -- multi-view projection of the registered photos into the UVBake atlas (numpy, no bpy).

    .venv-p10/bin/python scripts/mat_p10_project.py            # -> work/proj_g<g>.npz + work/proj_stats.json

Per atlas texel (work/atlas_g<g>.npz, per instance of the mesh -- the 16 columns share one region) and per registered
camera (cameras.json, edge residual <= 6 px): project; depth test against the rebuilt master's Z pass (ARCH + ORN +
ENV trees, work/depth_master, tolerance 0.05 m + 1 % of depth); weight = facing (n.v)^2 (0 below n.v 0.15) x border
feather (40 px) x registration (1 / (1 + (residual / 3 px)^2)) x resolution (photo px per metre / 30, 0.2..1);
bilinear sample of the linearised photo (the texel, 3-4 cm, is smaller than a photo pixel at these distances, so no
footprint blur is needed).  Instances of one texel seen by the same camera are averaged first (one sample per view).
Aggregation = the weighted median by luminance (the whole RGB of the median sample), in three delighting variants:
  raw    : the photos as they are
  (a)    : + per-photo, per-channel gain AND gamma in log space (exposure, white balance, tone curve) against the
           consensus, two iterations
  (d)    : + per-photo directional shading: log(L_k / L_consensus) fitted as a_k + b_k . n over the photo's texels
           (a sun / sky term per photo, the multi-view analogue of round 9's ratio method (c)), divided out
Metric (brief step 7): the robust inter-view std (1.4826 MAD) of log luminance per texel (>= 3 views), median over the attic panel texels
of faces 07 / 00 / 01, and over every texel; plus the residual sun gradient across the drum (the (d)-corrected drum
luminance regressed on the texel azimuth).
"""
import sys, json, math, time
import numpy as np
import cv2
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
import mat_p10_common as C

MAX_RES_PX = 6.0
DEPTH_DIR = C.WORK / "depth_master"


def srgb_to_lin(a):
    a = a.astype(np.float32) / 255.0
    return np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)


def bilinear(img, x, y):
    H, W = img.shape[:2]
    x = np.clip(x - 0.5, 0, W - 1.001); y = np.clip(y - 0.5, 0, H - 1.001)
    x0, y0 = x.astype(int), y.astype(int); fx, fy = (x - x0)[:, None], (y - y0)[:, None]
    return (img[y0, x0] * (1 - fx) * (1 - fy) + img[y0, x0 + 1] * fx * (1 - fy)
            + img[y0 + 1, x0] * (1 - fx) * fy + img[y0 + 1, x0 + 1] * fx * fy)


def lum(c):
    return c[..., 0] * 0.2126 + c[..., 1] * 0.7152 + c[..., 2] * 0.0722


def load_views():
    cams = C.load_cams()
    meta = json.loads((DEPTH_DIR / "meta.json").read_text())
    edges = json.loads((C.WORK / "edges.json").read_text())["per_image"]
    views = []
    for k in meta["cams"]:
        c = cams[k]
        r = edges.get(c["file"], 99.0)
        # usable: peak residual <= 6 px, physically plausible station, and a per-camera correction <= 1.5 deg (a larger
        # one means the peak search locked onto a different feature; the global error was ~0.9 deg)
        if r > MAX_RES_PX or not c.get("usable_physical", True) or c.get("refine_rot_deg", 0.0) > 1.5:
            continue
        d = C.read_passes(DEPTH_DIR / f"cam_{k:02d}.exr")
        Z = np.where(d["alpha"] > 0.5, d["z"], np.inf).astype(np.float32)
        img = srgb_to_lin(cv2.cvtColor(cv2.imread(str(C.WORK / "images" / c["file"])), cv2.COLOR_BGR2RGB))
        views.append(dict(k=k, c=c, Z=Z, img=img, res=r))
    return views


def sample_group(g, views, tris):
    a = np.load(C.WORK / f"atlas_g{g}.npz")
    mesh, lpos, lnrm = a["mesh"], a["lpos"], a["lnrm"]
    valid = mesh >= 0
    ids = mesh[valid]; lp = lpos[valid].astype(np.float64); ln = lnrm[valid].astype(np.float64)
    n = len(ids)
    mats, owner = tris["mats"], tris["mat_owner"]
    S = np.zeros((len(views), n, 3), np.float32)
    Wt = np.zeros((len(views), n), np.float32)
    Nw_first = np.zeros((n, 3)); Xw_first = np.zeros((n, 3))
    have_first = np.zeros(n, bool)
    for mi in np.unique(ids):
        pass
    for j, M in enumerate(mats):
        sel = ids == owner[j]
        if not sel.any():
            continue
        X = lp[sel] @ M[:3, :3].T + M[:3, 3]
        Nw = ln[sel] @ np.linalg.inv(M[:3, :3])
        Nw /= np.maximum(np.linalg.norm(Nw, axis=1, keepdims=True), 1e-12)
        first = sel.copy(); first[sel] = ~have_first[sel]
        idx_sel = np.nonzero(sel)[0]
        nf = ~have_first[idx_sel]
        Xw_first[idx_sel[nf]] = X[nf]; Nw_first[idx_sel[nf]] = Nw[nf]; have_first[idx_sel[nf]] = True
        for vi, v in enumerate(views):
            c = v["c"]; W, H = c["size"]
            uv, z = C.project(X, c)
            uv0, _ = C.project(X, c, distort=False)
            Zm = v["Z"]; h, w = Zm.shape
            xd = np.clip((uv0[:, 0] * w / W).astype(int), 0, w - 1); yd = np.clip((uv0[:, 1] * h / H).astype(int), 0, h - 1)
            inb = (z > 1) & (uv[:, 0] > 1) & (uv[:, 1] > 1) & (uv[:, 0] < W - 2) & (uv[:, 1] < H - 2)
            vis = inb & (z <= Zm[yd, xd] + 0.05 + 0.01 * z)
            Cc = np.asarray(c["centre"])
            vv = Cc - X; vv /= np.linalg.norm(vv, axis=1, keepdims=True)
            ndv = (Nw * vv).sum(1)
            wf = np.where(ndv > 0.15, ndv ** 2, 0.0)
            border = np.clip(np.minimum.reduce([uv[:, 0], uv[:, 1], W - uv[:, 0], H - uv[:, 1]]) / 40.0, 0, 1)
            wres = np.clip((c["K"][0][0] / np.maximum(z, 1)) / 30.0, 0.2, 1.0)
            wr = 1.0 / (1.0 + (v["res"] / 3.0) ** 2)
            w_ = np.where(vis, wf * border * wres * wr, 0.0)
            ok = w_ > 0
            if not ok.any():
                continue
            col = np.zeros((len(X), 3), np.float32)
            col[ok] = bilinear(v["img"], uv[ok, 0], uv[ok, 1])
            ii = idx_sel[ok]
            S[vi, ii] += (col[ok] * w_[ok, None]).astype(np.float32)
            Wt[vi, ii] += w_[ok].astype(np.float32)
    m = Wt > 0
    S[m] /= Wt[m][:, None]
    return dict(valid=valid, ids=ids, S=S, W=Wt, X=Xw_first, N=Nw_first)


def wmedian_pick(L, W):
    """Per texel (columns), the index of the weighted-median view by value L (views x texels)."""
    Lm = np.where(W > 0, L, np.inf)
    order = np.argsort(Lm, axis=0)
    Ws = np.take_along_axis(W, order, 0)
    cw = np.cumsum(Ws, 0)
    tot = cw[-1]
    k = (cw >= 0.5 * tot[None]).argmax(0)
    return order[k, np.arange(L.shape[1])], tot


def aggregate(S, W):
    L = lum(S)
    pick, tot = wmedian_pick(np.log(np.maximum(L, 1e-5)), W)
    col = S[pick, np.arange(S.shape[1])]
    return col, tot


def interview_std(S, W, sel):
    """Robust inter-view spread of log luminance per texel (1.4826 x the weighted MAD about the weighted median; a plain
    std is dominated by the views where a real tree / person / sky covers the texel), median over `sel` (>= 3 views)."""
    L = np.log(np.maximum(lum(S), 1e-5))
    nv = (W > 0).sum(0)
    m = sel & (nv >= 3)
    if not m.any():
        return float("nan"), 0
    Lm, Wm = L[:, m], W[:, m]
    pick, _ = wmedian_pick(Lm, Wm)
    med = Lm[pick, np.arange(Lm.shape[1])]
    dev = np.abs(Lm - med[None])
    pick2, _ = wmedian_pick(dev, Wm)
    mad = dev[pick2, np.arange(Lm.shape[1])]
    return float(np.median(1.4826 * mad)), int(m.sum())


def gains(S, W, cons):
    """Per photo and channel: log(cons) = a + b log(sample), i.e. an exposure gain AND a tone-curve gamma (the JPEGs
    carry different tone curves, which a pure gain cannot undo); b clipped to 0.6..1.6.  Returns the mapped stack."""
    out = S.copy()
    for k in range(S.shape[0]):
        m = (W[k] > 0) & (lum(cons) > 1e-3) & (lum(S[k]) > 1e-4)
        if m.sum() < 500:
            continue
        for ch in range(3):
            x = np.log(np.maximum(S[k, m, ch], 1e-5)); y = np.log(np.maximum(cons[m, ch], 1e-5))
            # robust line: two passes, the second on the half with the smallest residual
            b, a = np.polyfit(x, y, 1)
            r = np.abs(y - (a + b * x)); keep = r <= np.quantile(r, 0.5)
            b, a = np.polyfit(x[keep], y[keep], 1)
            b = float(np.clip(b, 0.6, 1.6))
            a = float(np.median(y[keep] - b * x[keep]))
            vals = np.maximum(S[k, :, ch], 1e-5)
            out[k, :, ch] = np.where(W[k] > 0, np.exp(a + b * np.log(vals)), 0.0)
    return out


def shading(S, W, cons, N):
    """Per photo: log(L_k / L_cons) = a + b . n  (weighted LSQ over the photo's texels) -> divide it out."""
    out = S.copy()
    fits = []
    for k in range(S.shape[0]):
        m = (W[k] > 0) & (lum(cons) > 1e-3)
        if m.sum() < 500:
            fits.append(None); continue
        y = np.log(np.maximum(lum(S[k, m]), 1e-5)) - np.log(np.maximum(lum(cons[m]), 1e-5))
        A = np.c_[np.ones(m.sum()), N[m]]
        w = np.sqrt(W[k, m])
        coef, *_ = np.linalg.lstsq(A * w[:, None], y * w, rcond=None)
        sh = np.exp(np.c_[np.ones(len(N)), N] @ coef).astype(np.float32)
        out[k] = S[k] / sh[:, None]
        fits.append(coef.tolist())
    return out, fits


if __name__ == "__main__":
    t0 = time.time()
    views = load_views()
    tris = np.load(C.WORK / "uvbake_tris.npz")
    names = list(tris["names"])
    print(f"[proj] {len(views)} views loaded ({time.time() - t0:.0f} s)")
    stats = dict(views=[v["c"]["file"] for v in views], groups={})
    for g in range(4):
        t1 = time.time()
        r = sample_group(g, views, tris)
        S, W, ids, N, X = r["S"], r["W"], r["ids"], r["N"], r["X"]
        nv = (W > 0).sum(0)
        az = np.degrees(np.arctan2(X[:, 1], -X[:, 0])) % 360
        d = np.abs((az - 82.0 + 180) % 360 - 180)
        facing = (N[:, 0] * -np.cos(np.radians(82)) + N[:, 1] * np.sin(np.radians(82))) > 0.2
        lagoon = (d <= 67.5) & facing & (np.abs(N[:, 2]) < 0.7)
        colmesh = np.array(["column" in names[i] or "colbase" in names[i] for i in ids])
        lagoon |= colmesh                                       # the columns: every instance, one region
        attic_panel = np.array(["attic_panel" in names[i] for i in ids])
        drum = np.array([names[i] == "ARCH_rotunda_drum" for i in ids])
        res = {}
        res["raw_std_panel"], npan = interview_std(S, W, attic_panel)
        res["raw_std_all"], nall = interview_std(S, W, np.ones(len(ids), bool))
        cons, tot = aggregate(S, W)
        Sa = gains(S, W, cons)
        for it in range(1):
            Sa = gains(S, W, aggregate(Sa, W)[0])
        res["a_std_panel"], _ = interview_std(Sa, W, attic_panel)
        res["a_std_all"], _ = interview_std(Sa, W, np.ones(len(ids), bool))
        cons_a, _ = aggregate(Sa, W)
        Sd, fits = shading(Sa, W, cons_a, N)
        for it in range(2):
            cons_d, _ = aggregate(Sd, W)
            Sd, fits = shading(Sa, W, cons_d, N)
        res["d_std_panel"], _ = interview_std(Sd, W, attic_panel)
        res["d_std_all"], _ = interview_std(Sd, W, np.ones(len(ids), bool))
        cons_d, tot = aggregate(Sd, W)
        cov = (tot > 0)
        res.update(texels=int(len(ids)), lagoon_texels=int(lagoon.sum()),
                   coverage_lagoon_pct=100.0 * float((cov & lagoon).sum()) / max(int(lagoon.sum()), 1),
                   coverage_all_pct=100.0 * float(cov.mean()),
                   median_views_lagoon=float(np.median(nv[lagoon & cov])) if (lagoon & cov).any() else 0.0,
                   panel_texels=int(npan))
        if drum.any():
            for tag, cc in (("a", cons_a), ("d", cons_d)):
                m = drum & (lum(cc) > 0) & cov & (np.abs(N[:, 2]) < 0.5)
                if m.sum() > 100:
                    dd = ((az[m] - 82 + 180) % 360) - 180
                    sl = np.polyfit(dd, np.log(lum(cc[m])), 1)[0]
                    res[f"drum_sun_gradient_{tag}_pct_per_10deg"] = float(100 * (math.exp(10 * sl) - 1))
        np.savez_compressed(C.WORK / f"proj_g{g}.npz", valid=r["valid"], col_raw=aggregate(S, W)[0],
                            col_a=cons_a, col_d=cons_d, weight=tot, views=nv, lagoon=lagoon)
        stats["groups"][g] = res
        print(f"[proj] group {g}: {json.dumps({k: (round(v, 3) if isinstance(v, float) else v) for k, v in res.items()})} "
              f"({time.time() - t1:.0f} s)", flush=True)
        del S, W, Sa, Sd
    (C.WORK / "proj_stats.json").write_text(json.dumps(stats, indent=1))
