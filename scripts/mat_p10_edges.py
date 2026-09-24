"""Phase 10 r1, step 2 acceptance -- model-edge reprojection into the registered photos, and the chamfer refinement.

    .venv-p10/bin/python scripts/mat_p10_edges.py check  <depthdir> [--sheet out.jpg]   # per photo + control table -> work/edges.json
    .venv-p10/bin/python scripts/mat_p10_edges.py refine <depthdir>                      # 7-DOF world correction
    .venv-p10/bin/python scripts/mat_p10_edges.py cams   <depthdir>                      # per-camera rotation + focal

Metric (rewritten after docs/reviews/phase10_proj_r1_review_part1.md finding 1, whose control showed the first,
crease-inclusive, orientation-blind chamfer moving only 3.39 -> 3.49 px under a 20 px shift): OCCLUDING-CONTOUR edges
only (depth steps > 0.25 m + 1 % and the silhouette against the sky, from the ARCH LOD0 Position pass rendered from the
recovered camera), each with its image orientation; their world points projected into the 1600 px photo (with k1) and
matched to Canny edges of the SAME orientation (+-22 deg, 12 bins of 15 deg, one distance transform per bin, capped at
31 px).  Median over the edge pixels per photo.  `check` prints the control table (the model edges shifted 5 / 10 / 20 /
40 px in four directions) next to the residual, so the number's resolving power is stated with it.
`refine`: a similarity D near identity (7 DOF, about the rotunda axis) applied to the MODEL edge points, minimising the
truncated (12 px) chamfer over every photo; written to work/refine.json and folded into cameras.json by
`mat_p10_align.py cameras` (the world frame stays master's; the cameras move by D^-1).
"""
import sys, json, math
import numpy as np
import cv2
from scipy.spatial.transform import Rotation as Rot
from scipy.optimize import least_squares
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
import mat_p10_common as C


NB = 12                     # orientation bins of 15 deg (mod 180)
DT_CAP = 31.0


def model_edges(d):
    """Occluding-contour edges only (depth steps and the silhouette against the sky; creases in the LOD0 ornament sit in
    dense photo texture and made the first metric flat): world points + the image direction of the edge normal."""
    a = d["alpha"] > 0.5
    z = np.where(a, d["z"], 1e4)
    lz = np.log(np.maximum(z, 0.1)).astype(np.float32)
    e = np.zeros(a.shape, bool)
    for dy, dx in ((0, 1), (1, 0)):
        z2 = np.roll(np.roll(z, -dy, 0), -dx, 1)
        jump = np.abs(z - z2) > 0.25 + 0.01 * np.minimum(z, z2)
        e |= jump & (z <= z2) & a
        e |= np.roll(np.roll(jump & (z2 < z) & np.roll(np.roll(a, -dy, 0), -dx, 1), dy, 0), dx, 1)
    e[:, -1] = e[-1, :] = e[:, 0] = e[0, :] = False
    gx = cv2.Sobel(lz, cv2.CV_32F, 1, 0, ksize=3); gy = cv2.Sobel(lz, cv2.CV_32F, 0, 1, ksize=3)
    ys, xs = np.nonzero(e)
    ang = np.arctan2(gy[ys, xs], gx[ys, xs]) % np.pi
    return d["pos"][ys, xs].astype(np.float64), ang


def photo_dt(c):
    """Canny edges of the photo split into NB orientation bins (gradient direction mod 180); one distance transform
    per bin, capped at DT_CAP px and stored as uint8 (x8)."""
    img = cv2.imread(str(C.WORK / "images" / c["file"]), cv2.IMREAD_GRAYSCALE)
    H, W = img.shape
    assert [W, H] == c["size"], (c["file"], img.shape, c["size"])
    g = cv2.GaussianBlur(img, (0, 0), 1.2)
    ed = cv2.Canny(g, 40, 110)
    gf = g.astype(np.float32)
    ang = np.arctan2(cv2.Sobel(gf, cv2.CV_32F, 0, 1, ksize=3), cv2.Sobel(gf, cv2.CV_32F, 1, 0, ksize=3)) % np.pi
    b = np.minimum((ang / np.pi * NB).astype(int), NB - 1)
    dts = np.zeros((NB, H, W), np.uint8)
    for k in range(NB):
        m = (ed > 0) & (b == k)
        dt = cv2.distanceTransform((~m).astype(np.uint8), cv2.DIST_L2, 5)
        dts[k] = (np.minimum(dt, DT_CAP) * 8).astype(np.uint8)
    return img, ed, dts


def sample(dts, uv, ang):
    """Oriented chamfer: distance to the nearest photo edge whose orientation is within ~ +-22 deg of the model edge's
    (its own bin and the two neighbours), bilinear, in px (capped at DT_CAP)."""
    NBk, H, W = dts.shape
    x = np.clip(uv[:, 0] - 0.5, 0, W - 1.001); y = np.clip(uv[:, 1] - 0.5, 0, H - 1.001)
    x0, y0 = x.astype(int), y.astype(int); fx, fy = x - x0, y - y0
    b = np.minimum((ang / np.pi * NBk).astype(int), NBk - 1)
    best = np.full(len(uv), DT_CAP)
    for o in (-1, 0, 1):
        k = (b + o) % NBk
        v = (dts[k, y0, x0] * (1 - fx) * (1 - fy) + dts[k, y0, x0 + 1] * fx * (1 - fy)
             + dts[k, y0 + 1, x0] * (1 - fx) * fy + dts[k, y0 + 1, x0 + 1] * fx * fy) / 8.0
        best = np.minimum(best, v)
    return best


def load(depthdir, cams_sel=None):
    meta = json.loads((depthdir / "meta.json").read_text())
    cams = C.load_cams()
    out = []
    for k in meta["cams"]:
        if cams_sel is not None and k not in cams_sel:
            continue
        c = cams[k]
        E, A = model_edges(C.read_passes(depthdir / f"cam_{k:02d}.exr"))
        img, ed, dts = photo_dt(c)
        out.append((k, c, (E, A), img, ed, dts))
    return out


def D_apply(p, X):
    s = math.exp(p[0]); R = Rot.from_rotvec(p[1:4]).as_matrix()
    return s * X @ R.T + p[4:7]


def offsets(data, p=None, full=False, shift=(0.0, 0.0)):
    res = {}
    for k, c, (E, A), img, ed, dt in data:
        X = E if p is None else D_apply(p, E)
        uv, z = C.project(X, c)
        uv = uv + np.asarray(shift)
        H, W = dt.shape[1:]
        ok = (z > 0) & (uv[:, 0] > 2) & (uv[:, 1] > 2) & (uv[:, 0] < W - 2) & (uv[:, 1] < H - 2)
        if full:                                   # fixed length for the optimiser: off-frame = the truncation
            d = np.full(len(uv), 12.0); d[ok] = sample(dt, uv[ok], A[ok]); res[k] = (uv, d)
        else:
            res[k] = (uv[ok], sample(dt, uv[ok], A[ok]))
    return res


def control_table(data, p=None):
    """The calibration the review asked for: the same metric with the model edges shifted by a KNOWN amount (four
    directions averaged).  A usable metric must at least double between 0 and 10-20 px."""
    rows = {}
    for s_ in (0, 5, 10, 20, 40):
        vals = []
        for dx, dy in ((s_, 0), (-s_, 0), (0, s_), (0, -s_)) if s_ else ((0, 0),):
            r = offsets(data, p, shift=(dx, dy))
            vals.append(np.median([np.median(v[1]) for v in r.values()]))
        rows[s_] = float(np.mean(vals))
    print("[edges] control shift (px) -> median of per-photo medians: " +
          ", ".join(f"{k}: {v:.2f}" for k, v in rows.items()) + f"   ratio 10px/0 {rows[10] / rows[0]:.2f}, 20px/0 {rows[20] / rows[0]:.2f}")
    return rows


def sheet(data, res, path):
    tiles = []
    for (k, c, EA, img, ed, dt) in data[:12]:
        uv, dd = res[k]
        rgb = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR) // 2
        rgb[ed > 0] = (80, 80, 80)
        for (x, y), v in zip(uv[::2].astype(int), dd[::2]):
            rgb[y, x] = (0, 255, 0) if v <= 4 else (0, 0, 255)
        h = 480; w = int(rgb.shape[1] * h / rgb.shape[0])
        t = cv2.resize(rgb, (w, h), interpolation=cv2.INTER_AREA)
        cv2.putText(t, f"{k} {c['file'][4:20]} med {np.median(dd):.1f}px", (8, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7,
                    (255, 255, 255), 2)
        tiles.append(t)
    rows = []
    for i in range(0, len(tiles), 4):
        row = tiles[i:i + 4]
        rows.append(np.hstack(row + [np.zeros((480, 10, 3), np.uint8)]))
    Wm = max(r.shape[1] for r in rows)
    rows = [np.pad(r, ((0, 0), (0, Wm - r.shape[1]), (0, 0))) for r in rows]
    cv2.imwrite(str(path), np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 88])


def report(res, tag):
    meds = {k: float(np.median(v[1])) for k, v in res.items()}
    allv = np.concatenate([v[1] for v in res.values()])
    print(f"[edges] {tag}: per-photo median offset " + ", ".join(f"{k}:{m:.1f}" for k, m in meds.items()))
    print(f"[edges] {tag}: median of per-photo medians {np.median(list(meds.values())):.2f} px; all edge pixels median "
          f"{np.median(allv):.2f} px, <= 4 px {100 * (allv <= 4).mean():.0f} %")
    return meds


def photo_grad(c):
    img = cv2.imread(str(C.WORK / "images" / c["file"]), cv2.IMREAD_GRAYSCALE).astype(np.float32)
    g = cv2.GaussianBlur(img, (0, 0), 1.5)
    gx = cv2.Sobel(g, cv2.CV_32F, 1, 0, ksize=3); gy = cv2.Sobel(g, cv2.CV_32F, 0, 1, ksize=3)
    m = np.hypot(gx, gy); s = float(np.percentile(m, 90)) + 1e-6
    return gx / s, gy / s


def bil(a, x, y):
    H, W = a.shape
    x = np.clip(x - 0.5, 0, W - 1.001); y = np.clip(y - 0.5, 0, H - 1.001)
    x0, y0 = x.astype(int), y.astype(int); fx, fy = x - x0, y - y0
    return (a[y0, x0] * (1 - fx) * (1 - fy) + a[y0, x0 + 1] * fx * (1 - fy)
            + a[y0 + 1, x0] * (1 - fx) * fy + a[y0 + 1, x0 + 1] * fx * fy)


def peak_offset(c, E, A, shift=(0.0, 0.0), R=40, npts=6000, seed=0):
    """Direct 2D registration residual: the image shift (dx, dy) that maximises the photo's gradient ALONG the model
    contour normal, summed over the projected contour points; searched on +-R px (step 2, then +-2 at 0.5).  The model
    is registered to the photo by (dx, dy); |(dx, dy)| is the residual in px.  Self-calibrating: a control shift s of the
    model moves the peak by -s.  Returns (dx, dy, sharpness = peak / median score, n points)."""
    gx, gy = photo_grad(c)
    uv, z = C.project(E, c)
    uv = uv + np.asarray(shift)
    H, W = gx.shape
    ok = (z > 0) & (uv[:, 0] > R + 3) & (uv[:, 1] > R + 3) & (uv[:, 0] < W - R - 3) & (uv[:, 1] < H - R - 3)
    uv, A = uv[ok], A[ok]
    if len(uv) < 200:
        return float("nan"), float("nan"), 0.0, len(uv)
    i = np.random.default_rng(seed).choice(len(uv), min(npts, len(uv)), replace=False)
    uv, ca, sa = uv[i], np.cos(A[i]), np.sin(A[i])
    def score(dx, dy):
        return float(np.abs(bil(gx, uv[:, 0] + dx, uv[:, 1] + dy) * ca + bil(gy, uv[:, 0] + dx, uv[:, 1] + dy) * sa).mean())
    grid = np.arange(-R, R + 0.1, 2.0)
    S = np.array([[score(dx, dy) for dx in grid] for dy in grid])
    iy, ix = np.unravel_index(S.argmax(), S.shape)
    bx, by = grid[ix], grid[iy]
    fine = np.arange(-2, 2.01, 0.5)
    F = np.array([[score(bx + dx, by + dy) for dx in fine] for dy in fine])
    jy, jx = np.unravel_index(F.argmax(), F.shape)
    return float(bx + fine[jx]), float(by + fine[jy]), float(S.max() / np.median(S)), len(uv)


def cmd_peak(dd, cams_sel=None, controls=(0, 10, 20, 40), write=True):
    meta = json.loads((dd / "meta.json").read_text())
    cams = C.load_cams()
    rows, per = [], {}
    for k in meta["cams"]:
        if cams_sel is not None and k not in cams_sel:
            continue
        c = cams[k]
        E, A = model_edges(C.read_passes(dd / f"cam_{k:02d}.exr"))
        dx, dy, sh, n = peak_offset(c, E, A)
        ctl = {}
        for s_ in controls[1:]:
            cx, cy, _, _ = peak_offset(c, E, A, shift=(s_, 0.0))
            ctl[s_] = float(math.hypot(cx, cy))
        rows.append((k, dx, dy, sh, n, ctl))
        per[c["file"]] = dict(dx=dx, dy=dy, residual=float(math.hypot(dx, dy)), sharpness=sh, control=ctl)
        print(f"[peak] cam {k:2d} {c['file'][:26]:26s} offset ({dx:+5.1f}, {dy:+5.1f}) |{math.hypot(dx, dy):5.1f}| px  "
              f"sharpness {sh:4.2f}  control " + " ".join(f"{s_}:{v:5.1f}" for s_, v in ctl.items()), flush=True)
    res = np.array([math.hypot(r[1], r[2]) for r in rows])
    print(f"[peak] median residual {np.nanmedian(res):.2f} px over {len(rows)} photos; <= 4 px {int((res <= 4).sum())}, "
          f"<= 6 px {int((res <= 6).sum())}; control medians " +
          ", ".join(f"{s_} px -> {np.nanmedian([r[5][s_] for r in rows]):.1f}" for s_ in controls[1:]))
    if write:
        (C.WORK / "edges.json").write_text(json.dumps(dict(
            metric="peak of the photo gradient along the model's occluding contour (mat_p10_edges.py peak)",
            per_image={f: v["residual"] for f, v in per.items()}, detail=per), indent=1))
    return per


HZ_W = 3.0
if __name__ == "__main__":
    from pathlib import Path
    cmd, dd = sys.argv[1], Path(sys.argv[2])
    if cmd == "peakfix":
        # per camera: the rotation about its centre that moves the projection by the measured peak offset
        # (du = f * theta_y, dv = f * phi_x); composed onto any refine_cams.json already on disk (iterate).
        per = cmd_peak(dd, None, controls=(0,), write=False)
        cams = {c["file"]: c for c in C.load_cams()}
        rc = C.WORK / "refine_cams.json"
        old = json.loads(rc.read_text()) if rc.exists() else {}
        out = {}
        for f, v in per.items():
            prev = old.get(f, dict(rotvec=[0.0, 0.0, 0.0], fscale=1.0))
            if not np.isfinite(v["dx"]) or v["residual"] > 60:
                out[f] = prev; continue
            fx = cams[f]["K"][0][0]
            d = Rot.from_rotvec([-v["dy"] / fx, v["dx"] / fx, 0.0])
            out[f] = dict(rotvec=(d * Rot.from_rotvec(prev["rotvec"])).as_rotvec().tolist(), fscale=prev["fscale"])
        rc.write_text(json.dumps(out, indent=1))
        print(f"[peakfix] wrote {len(out)} per-camera rotations to refine_cams.json")
        raise SystemExit(0)
    if cmd == "peak":
        sel = {int(x) for x in sys.argv[sys.argv.index("--cams") + 1].split(",")} if "--cams" in sys.argv else None
        cmd_peak(dd, sel, write="--no-write" not in sys.argv)
        raise SystemExit(0)
    data = load(dd)
    res = offsets(data)
    meds = report(res, "as registered")
    if cmd == "check":
        ctl = control_table(data)
        cams_all = C.load_cams()
        per = {cams_all[k]["file"]: float(np.median(v[1])) for k, v in res.items()}
        (C.WORK / "edges_chamfer.json").write_text(json.dumps(dict(per_image=per, control_shift=ctl,
                                                           metric="oriented contour chamfer (mat_p10_edges.py)"), indent=1))
        print(f"[edges] wrote work/edges_chamfer.json ({len(per)} photos; the independent, weak check)")
    if cmd == "refine":
        rng = np.random.default_rng(0)
        sub = []
        for k, c, (E, A), img, ed, dt in data:
            i = rng.choice(len(E), min(4000, len(E)), replace=False)
            sub.append((k, c, (E[i], A[i]), img, ed, dt))
        # camera-height prior: the photographers stand on the east-shore lawn / path (docs/reference_sheet.md: -0.4 to
        # -0.8 m) at eye height -> median camera z = +1.0 m.  Without it the chamfer trades tilt against height
        # (a 2.3 deg tilt put the median camera 0.2 m below the lawn at -1.1 m).
        Cs = np.array([c["centre"] for c in C.load_cams()])
        def cam_z(p):
            s = math.exp(p[0]); R = Rot.from_rotvec(p[1:4]).as_matrix()
            return ((Cs - p[4:7]) @ R / s)[:, 2]                 # D^-1 applied to the camera centres
        def fun(p):
            r = []
            for k, (uv, d) in offsets(sub, p, full=True).items():
                r.append(np.minimum(d, 12.0) / math.sqrt(len(d)))
            r.append([HZ_W * (np.median(cam_z(p)) - 1.0)])
            return np.concatenate(r)
        sol = least_squares(fun, np.zeros(7), diff_step=1e-4, x_scale=[1e-3, 1e-3, 1e-3, 1e-3, 0.05, 0.05, 0.05])
        p = sol.x
        res2 = offsets(data, p)
        meds2 = report(res2, "after D")
        print(f"[edges] camera z after D: median {np.median(cam_z(p)):.2f} m, 5-95 % {np.percentile(cam_z(p), [5, 95]).round(2)}")
        print(f"[edges] D: scale {math.exp(p[0]):.5f}, rot {np.degrees(np.linalg.norm(p[1:4])):.3f} deg, "
              f"shift {np.round(p[4:7], 3)} m")
        (C.WORK / "refine.json").write_text(json.dumps(dict(p=p.tolist(), before=meds, after=meds2)))
        res = res2
    if cmd == "cams":
        # per camera: rotation about its centre (3) + focal scale (1), truncated chamfer + a prior (0.5 deg, 3 %).
        # Kept only when the camera's median offset drops.  Written to work/refine_cams.json (mat_p10_align cameras).
        out, rows = {}, []
        rng = np.random.default_rng(0)
        for k, c, (E, A), img, ed, dt in data:
            i = rng.choice(len(E), min(6000, len(E)), replace=False)
            Es, As = E[i], A[i]
            K0 = np.asarray(c["K"]); R0 = np.asarray(c["R"]); t0 = np.asarray(c["t"])
            def cam_of(q):
                dR = Rot.from_rotvec(q[:3]).as_matrix()
                cc = dict(c); K = K0.copy(); K[0, 0] *= math.exp(q[3]); K[1, 1] *= math.exp(q[3])
                cc["K"] = K; cc["R"] = dR @ R0; cc["t"] = dR @ t0
                return cc
            def dist_of(q, X, Ang):
                uv, z = C.project(X, cam_of(q))
                H, W = dt.shape[1:]
                ok = (z > 0) & (uv[:, 0] > 2) & (uv[:, 1] > 2) & (uv[:, 0] < W - 2) & (uv[:, 1] < H - 2)
                d = np.full(len(X), 12.0); d[ok] = sample(dt, uv[ok], Ang[ok])
                return d, ok
            def fun(q):
                d, _ = dist_of(q, Es, As)
                prior = [q[0] / math.radians(0.5), q[1] / math.radians(0.5), q[2] / math.radians(0.5), q[3] / 0.03]
                return np.concatenate([np.minimum(d, 12.0) / math.sqrt(len(d)), 1.0 * np.array(prior)])
            sol = least_squares(fun, np.zeros(4), diff_step=1e-3, x_scale=[1e-3, 1e-3, 1e-3, 1e-2])
            d0, ok0 = dist_of(np.zeros(4), E, A); d1, ok1 = dist_of(sol.x, E, A)
            m0, m1 = float(np.median(d0[ok0])), float(np.median(d1[ok1]))
            keep = m1 < m0
            if keep:
                out[c["file"]] = dict(rotvec=sol.x[:3].tolist(), fscale=float(math.exp(sol.x[3])))
            rows.append((k, m0, m1 if keep else m0, np.degrees(np.linalg.norm(sol.x[:3])), math.exp(sol.x[3]), keep))
        (C.WORK / "refine_cams.json").write_text(json.dumps(out, indent=1))
        a = np.array([(r[1], r[2]) for r in rows])
        for r in rows:
            print(f"[edges] cam {r[0]:2d}: {r[1]:.2f} -> {r[2]:.2f} px  rot {r[3]:.3f} deg  f x{r[4]:.4f}  {'kept' if r[5] else 'rejected'}")
        print(f"[edges] per-camera refine: median of per-photo medians {np.median(a[:, 0]):.2f} -> {np.median(a[:, 1]):.2f} px "
              f"over {len(rows)} photos; photos <= 4 px {int((a[:, 1] <= 4).sum())}")
    if "--sheet" in sys.argv:
        sheet(data, res, sys.argv[sys.argv.index("--sheet") + 1])
