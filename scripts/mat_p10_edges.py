"""Phase 10 r1, step 2 acceptance -- model-edge reprojection into the registered photos, and the chamfer refinement.

    .venv-p10/bin/python scripts/mat_p10_edges.py check  <depthdir> [--sheet out.jpg]   # median edge offset per photo
    .venv-p10/bin/python scripts/mat_p10_edges.py refine <depthdir>                      # 7-DOF world correction

Model edges: pixels of the Position pass (mat_p10_depth.py, ARCH LOD0 rendered from the recovered camera) where the
surface jumps (depth step > 0.25 m + 1 % of depth, or silhouette against the sky) or creases (normal turn > 35 deg).
Their WORLD positions are projected into the 1600 px photo (with k1) and compared with the photo's Canny edges through
a distance transform: offset = distance to the nearest photo edge.  Median over the edge pixels, per photo.
Caveat: trees / people / sky edges in the photo can only LOWER a model->photo chamfer; ornament ARCH does not model
(capitals, reliefs) is absent from the model edges.  The number is therefore a lower-biased registration residual; the
overlay sheet is the check that it is not a coincidence.
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


def model_edges(d):
    pos, nrm, a = d["pos"], d["nrm"], d["alpha"] > 0.5
    z = np.where(a, d["z"], 1e6)
    e = np.zeros(a.shape, bool)
    for dy, dx in ((0, 1), (1, 0)):
        z2 = np.roll(np.roll(z, -dy, 0), -dx, 1)
        n2 = np.roll(np.roll(nrm, -dy, 0), -dx, 1)
        jump = np.abs(z - z2) > 0.25 + 0.01 * np.minimum(z, z2)
        crease = (a & np.roll(np.roll(a, -dy, 0), -dx, 1)) & ((nrm * n2).sum(-1) < math.cos(math.radians(35)))
        near_self = z <= z2                            # keep the nearer side of a jump (the occluding contour)
        e |= (jump & near_self & a) | crease
    e[:, -1] = e[-1, :] = False
    ys, xs = np.nonzero(e)
    return d["pos"][ys, xs].astype(np.float64)


def photo_dt(c):
    img = cv2.imread(str(C.WORK / "images" / c["file"]), cv2.IMREAD_GRAYSCALE)
    H, W = img.shape
    assert [W, H] == c["size"], (c["file"], img.shape, c["size"])
    g = cv2.GaussianBlur(img, (0, 0), 1.2)
    ed = cv2.Canny(g, 40, 110)
    dt = cv2.distanceTransform((ed == 0).astype(np.uint8), cv2.DIST_L2, 5)
    return img, ed, dt


def sample(dt, uv):
    H, W = dt.shape
    x = np.clip(uv[:, 0] - 0.5, 0, W - 1.001); y = np.clip(uv[:, 1] - 0.5, 0, H - 1.001)
    x0, y0 = x.astype(int), y.astype(int); fx, fy = x - x0, y - y0
    return (dt[y0, x0] * (1 - fx) * (1 - fy) + dt[y0, x0 + 1] * fx * (1 - fy)
            + dt[y0 + 1, x0] * (1 - fx) * fy + dt[y0 + 1, x0 + 1] * fx * fy)


def load(depthdir):
    meta = json.loads((depthdir / "meta.json").read_text())
    cams = C.load_cams()
    out = []
    for k in meta["cams"]:
        c = cams[k]
        E = model_edges(C.read_passes(depthdir / f"cam_{k:02d}.exr"))
        img, ed, dt = photo_dt(c)
        out.append((k, c, E, img, ed, dt))
    return out


def D_apply(p, X):
    s = math.exp(p[0]); R = Rot.from_rotvec(p[1:4]).as_matrix()
    return s * X @ R.T + p[4:7]


def offsets(data, p=None, full=False):
    res = {}
    for k, c, E, img, ed, dt in data:
        X = E if p is None else D_apply(p, E)
        uv, z = C.project(X, c)
        H, W = dt.shape
        ok = (z > 0) & (uv[:, 0] > 2) & (uv[:, 1] > 2) & (uv[:, 0] < W - 2) & (uv[:, 1] < H - 2)
        if full:                                   # fixed length for the optimiser: off-frame = the truncation
            d = np.full(len(uv), 12.0); d[ok] = sample(dt, uv[ok]); res[k] = (uv, d)
        else:
            res[k] = (uv[ok], sample(dt, uv[ok]))
    return res


def sheet(data, res, path):
    tiles = []
    for (k, c, E, img, ed, dt) in data[:12]:
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


HZ_W = 3.0
if __name__ == "__main__":
    from pathlib import Path
    cmd, dd = sys.argv[1], Path(sys.argv[2])
    data = load(dd)
    res = offsets(data)
    meds = report(res, "as registered")
    if cmd == "refine":
        rng = np.random.default_rng(0)
        sub = [(k, c, E[rng.choice(len(E), min(4000, len(E)), replace=False)], img, ed, dt)
               for k, c, E, img, ed, dt in data]
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
    if "--sheet" in sys.argv:
        sheet(data, res, sys.argv[sys.argv.index("--sheet") + 1])
