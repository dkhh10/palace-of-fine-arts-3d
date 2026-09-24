"""Phase 10 r1, step 2 -- align the SfM model (probe model 2) to master world with a 7-DOF similarity.

    .venv-p10/bin/python scripts/mat_p10_align.py icp          # gravity + multi-start trimmed ICP -> work/sim.json
    .venv-p10/bin/python scripts/mat_p10_align.py cameras      # apply sim -> assets/textures/projection2/cameras.json

No bpy.  Inputs: work/sfm.npz (mat_p10_sfm.py dump) and work/arch_samples.npz (mat_p10_meshdump.py samples: area-
weighted samples of the rotunda's ARCH LOD0 surfaces in world metres).

Method (as run; see docs/materials_notes.md "Phase 10 r1", step-2 recipe = scripts/mat_p10_step2.sh)
  1. Gravity: the direction most orthogonal to the 71 cameras' RIGHT vectors (smallest singular vector).
  2. Axis: RANSAC circle through the sparse points at column-to-attic height.
  3. Grid search scale 14-20 m/unit x yaw 0-359 x tz 0/1/2 by inlier count; the octagon's 45-deg symmetry makes every
     sector score within 2 %, so the sector is FORCED by the camera-side prior (--sector=0: the photos are on the lagoon
     side, cameras centred on face 00 at az 82), then yaw-only and 7-DOF trimmed point-to-plane ICP.
  4. `cameras` writes cameras.json from the similarity, plus the edge refinements ONLY when named on the command line
     (--with-D: work/refine.json, --with-cams: work/refine_cams.json), and gates every camera on physical bounds
     (z -0.5..+6 m, 30-250 m from the rotunda axis) -> `usable` false.  `icp` deletes stale refine files.
The final similarity maps model x -> s R x + T (world).  The acceptance test is NOT this residual but the edge
reprojection (mat_p10_edges.py): the sparse cloud contains ornament ARCH does not model (capitals, relief panels).
"""
import sys, json, math
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation as Rot

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
WORK = ROOT / "assets" / "textures" / "projection2" / "work"
OUT = ROOT / "assets" / "textures" / "projection2"
FACE_AZ0 = 82.0


def az_dir(az):
    a = math.radians(az)
    return np.array([-math.cos(a), math.sin(a), 0.0])        # compass az -> world (x = south, y = east)


def load():
    d = np.load(WORK / "sfm.npz")
    a = np.load(WORK / "arch_samples.npz")
    return d, a


def model_frame(d):
    """Gravity from the cameras' RIGHT vectors (photographers level the horizon but pitch up at a 53 m building, so
    the image-up vectors lean back by the pitch -- the first attempt used them and was tilted 12.8 deg): gravity is
    the direction most orthogonal to all 71 right vectors (smallest singular vector)."""
    R = d["R"]
    rights = np.array([r[0] for r in R])
    ups = np.array([-r[1] for r in R])
    _, S, Vt = np.linalg.svd(rights)
    up = Vt[2] * np.sign(Vt[2] @ ups.mean(0))
    roll = np.degrees(np.arcsin(np.abs(rights @ up)))
    fws = np.array([r[2] for r in R])
    f = fws.mean(0); f -= up * (f @ up); f /= np.linalg.norm(f)
    return up, f, roll


def trimmed_icp(X, tree, Y, NY, s, Rm, T, iters=40, trim=0.6, free_tilt=False, yaw_only=True):
    """X model points (n,3). World = s Rm X + T.  Point-to-plane ICP on the `trim` fraction closest points.
    Unknowns: d(log s), rotation (yaw only or full), translation."""
    for it in range(iters):
        W = s * X @ Rm.T + T
        dist, j = tree.query(W)
        keep = dist <= np.quantile(dist, trim)
        P, Q, N = W[keep], Y[j[keep]], NY[j[keep]]
        r = ((P - Q) * N).sum(1)                                   # signed point-to-plane residual
        c = P.mean(0)
        Pc = P - c
        # linearise: P' = P + w x (P-c) + ds (P-c) + dt
        cols = []
        if yaw_only:
            cols.append(np.cross(np.array([0, 0, 1.0]), Pc))       # rotation about z through c
        else:
            for e in np.eye(3):
                cols.append(np.cross(e, Pc))
        cols.append(Pc)                                            # scale about c
        for e in np.eye(3):
            cols.append(np.broadcast_to(e, Pc.shape))
        A = np.stack([(col * N).sum(1) for col in cols], 1)
        x, *_ = np.linalg.lstsq(A, -r, rcond=None)
        k = 0
        if yaw_only:
            dR = Rot.from_rotvec([0, 0, x[0]]).as_matrix(); k = 1
        else:
            dR = Rot.from_rotvec(x[:3]).as_matrix(); k = 3
        ds = 1.0 + x[k]; dt = x[k + 1:k + 4]
        # new W = c + ds dR (W - c) + dt
        Rm = dR @ Rm
        T = c + ds * dR @ (T - c) + dt
        s = s * ds
        if np.abs(x).max() < 1e-7:
            break
    W = s * X @ Rm.T + T
    dist, _ = tree.query(W)
    keep = dist <= np.quantile(dist, trim)
    return s, Rm, T, float(np.sqrt((dist[keep] ** 2).mean())), dist


def circle_ransac(Q, rng, rmin, rmax, tol, iters=20000):
    best = (0, None)
    for _ in range(iters):
        (ax, ay), (bx, by), (cx, cy) = Q[rng.choice(len(Q), 3, replace=False)]
        dd = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
        if abs(dd) < 1e-9:
            continue
        ux = ((ax * ax + ay * ay) * (by - cy) + (bx * bx + by * by) * (cy - ay) + (cx * cx + cy * cy) * (ay - by)) / dd
        uy = ((ax * ax + ay * ay) * (cx - bx) + (bx * bx + by * by) * (ax - cx) + (cx * cx + cy * cy) * (bx - ax)) / dd
        r = math.hypot(ax - ux, ay - uy)
        if not rmin < r < rmax:
            continue
        n = int((np.abs(np.hypot(Q[:, 0] - ux, Q[:, 1] - uy) - r) < tol).sum())
        if n > best[0]:
            best = (n, (ux, uy, r))
    return best


def cmd_icp():
    for f in ("refine.json", "refine_cams.json", "edges.json"):          # stale against a new similarity
        (WORK / f).unlink(missing_ok=True)
    """1 gravity (right vectors); 2 the rotunda axis = RANSAC circle through the points at column-to-attic height;
    3 grid search of scale x heading x height by inlier count (points within 0.4 m of the ARCH surface samples,
    rotunda + site + colonnade, so the octagon's 45-degree symmetry is broken by the wings and the stairs);
    4 7-DOF trimmed point-to-plane ICP from the winner."""
    d, a = load()
    good = (d["err"] < 1.5) & (d["trk"] >= 3)
    X = d["xyz"][good]
    Y, NY = a["xyz"], a["nrm"]
    tree = cKDTree(Y)
    up, f, roll = model_frame(d)
    B = np.stack([np.cross(f, up), f, up])
    C = np.array([-r.T @ t for r, t in zip(d["R"], d["t"])])
    P = X @ B.T; Pc = C @ B.T
    h0 = np.median(Pc[:, 2])
    print(f"gravity from right vectors: roll residual median {np.median(roll):.2f} deg, max {roll.max():.2f}; "
          f"camera height spread (model units) {np.ptp(Pc[:, 2]):.3f}")
    rng = np.random.default_rng(0)
    band = (P[:, 2] - h0 > 0.35) & (P[:, 2] - h0 < 2.1)
    n, (ux, uy, r) = circle_ransac(P[band, :2], rng, 0.8, 2.0, 0.04)
    print(f"axis: circle through {n} of {band.sum()} band points, r {r:.3f} units")
    P -= [ux, uy, h0]; Pc -= [ux, uy, h0]
    sub = P[rng.choice(len(P), min(5000, len(P)), replace=False)]
    res = []
    for s in np.arange(14.0, 20.01, 0.25):
        for yaw in np.arange(0.0, 360.0, 1.0):
            Rz = Rot.from_euler("z", yaw, degrees=True).as_matrix()
            for tz in (0.0, 1.0, 2.0):
                W = s * sub @ Rz.T; W[:, 2] += tz
                dist, _ = tree.query(W, distance_upper_bound=0.4)
                res.append((int(np.isfinite(dist).sum()), float(s), float(yaw), tz))
    res.sort(reverse=True)
    def cam_az(s, yaw):
        Cw = s * Pc @ Rot.from_euler("z", yaw, degrees=True).as_matrix().T
        return float(np.median(np.degrees(np.arctan2(Cw[:, 1], -Cw[:, 0])) % 360))
    by_sector = {}
    for n_, s, yaw, tz in res:
        sec = int(((cam_az(s, yaw) - FACE_AZ0 + 22.5) % 360) // 45)
        if sec not in by_sector:
            by_sector[sec] = (n_, s, yaw, tz)
    for sec in sorted(by_sector):
        print(f"  best with the cameras centred on face {sec}: inliers {by_sector[sec][0]} "
              f"(s {by_sector[sec][1]}, yaw {by_sector[sec][2]}, tz {by_sector[sec][3]})")
    n_, s, yaw, tz = res[0]
    if SECTOR is not None:                     # hard camera-side prior: the photos are all on the lagoon side
        n_, s, yaw, tz = by_sector[SECTOR]
        res.insert(0, (n_, s, yaw, tz))
    print(f"search winner: inliers {n_} / {len(sub)}, s {s}, yaw {yaw}, tz {tz}, cameras centred at az {cam_az(s, yaw):.1f}")
    Rm = Rot.from_euler("z", yaw, degrees=True).as_matrix() @ B
    T = -s * Rm @ (B.T @ np.array([ux, uy, h0])) + np.array([0, 0, tz])
    s, Rm, T, rms, _ = trimmed_icp(X, tree, Y, NY, s, Rm, T, iters=40, trim=0.6)
    s, Rm, T, rms, dist = trimmed_icp(X, tree, Y, NY, s, Rm, T, iters=80, trim=0.5, yaw_only=False)
    Cw0 = s * C @ Rm.T + T
    az_med = float(np.median(np.degrees(np.arctan2(Cw0[:, 1], -Cw0[:, 0])) % 360))
    print(f"after ICP: cameras centred at az {az_med:.1f} (lagoon face {FACE_AZ0})")
    if SECTOR is not None and abs(((az_med - FACE_AZ0 + 180) % 360) - 180) > 22.5:
        raise SystemExit("[align] ICP left the lagoon sector: camera prior violated")
    tilt = math.degrees(math.acos(np.clip((Rm @ up) @ np.array([0, 0, 1.0]), -1, 1)))
    Cw = s * C @ Rm.T + T
    print(f"7-DOF ICP: s {s:.4f} m/unit, trimmed-50 RMS {rms:.3f} m, median |d| all points {np.median(dist):.3f} m, "
          f"inliers < 0.25 m {100 * (dist < 0.25).mean():.1f} %, tilt vs gravity {tilt:.2f} deg; camera z "
          f"{np.percentile(Cw[:, 2], [5, 50, 95]).round(2)}, distance {np.percentile(np.hypot(Cw[:, 0], Cw[:, 1]), [5, 50, 95]).round(1)}")
    json.dump(dict(s=s, R=Rm.tolist(), T=T.tolist(), icp_rms_trim50=rms, median_dist=float(np.median(dist)),
                   n_points=int(len(X)), tilt_deg=tilt, search=dict(winner=res[0], sectors=by_sector)),
              open(WORK / "sim.json", "w"), indent=1)


def ray_mesh(O, D, tris):
    """First hit of rays (O (3,), D (n,3) unit) on triangles (m,3,3). Moller-Trumbore, chunked numpy."""
    v0, e1, e2 = tris[:, 0], tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0]
    tv = O - v0
    q_all = np.cross(tv, e1)
    out = np.full(len(D), np.inf)
    for i, d in enumerate(D):
        p = np.cross(d, e2)
        det = (e1 * p).sum(1)
        ok = np.abs(det) > 1e-12
        inv = np.where(ok, 1.0 / np.where(ok, det, 1.0), 0.0)
        u = (tv * p).sum(1) * inv
        v = (q_all @ d) * inv
        t = (q_all * e2).sum(1) * inv
        hit = ok & (u >= 0) & (v >= 0) & (u + v <= 1) & (t > 0.5)
        if hit.any():
            out[i] = t[hit].min()
    return out


# the old cam01 station, the frame REF169_XF was fitted in (mat_build.PROJ_*)
PROJ_LOC = np.array([-14.1, 100.0, 1.6]); PROJ_TARGET = np.array([0.0, 0.0, 1.6])
PROJ_LENS, PROJ_SENSOR, PROJ_SHIFT_Y, PROJ_RES = 20.0, 36.0, 0.06, (1920, 1080)


def cmd_seed169():
    """3D-3D seed correspondences from ref 169: each sparse point observed in ref 169 -> the photo pixel ->
    REF169_XF -> the old cam01 render pixel -> a ray from that station -> its first hit on the ARCH rotunda.
    REF169_XF is a 2D scale+offset fit (QA round 05), so this is an approximation used ONLY to seed the ICP."""
    import arch_params as P
    d, a = load()
    names = list(d["names"])
    k = [i for i, n in enumerate(names) if n.startswith("ref_169")][0]
    obs = d["obs"]; o = obs[obs[:, 0] == k]
    pid_index = {int(p): i for i, p in enumerate(d["pid"])}
    S, DX, DY = P.REF169_XF
    raw_w = 1920.0; sc = raw_w / d["wh"][k][0]
    col = o[:, 2] * sc * S + DX; row = o[:, 3] * sc * S + DY
    fwd = PROJ_TARGET - PROJ_LOC; fwd /= np.linalg.norm(fwd)
    right = np.cross(fwd, [0, 0, 1.0]); right /= np.linalg.norm(right); up = np.cross(right, fwd)
    hx = PROJ_SENSOR / (2 * PROJ_LENS); hy = hx * PROJ_RES[1] / PROJ_RES[0]; dy = PROJ_SHIFT_Y * PROJ_SENSOR / PROJ_LENS
    u = col / PROJ_RES[0]; v = 1.0 - row / PROJ_RES[1]
    X = (u - 0.5) * 2 * hx; Y = (v - 0.5) * 2 * hy + dy
    D = fwd[None] + X[:, None] * right[None] + Y[:, None] * up[None]
    D /= np.linalg.norm(D, axis=1, keepdims=True)
    inside = (col > 0) & (col < 1920) & (row > 0) & (row < 1080)
    tris = a["tris"].astype(np.float64)
    tt = ray_mesh(PROJ_LOC, D[inside], tris)
    ok = np.isfinite(tt)
    W = PROJ_LOC + D[inside][ok] * tt[ok, None]
    M = d["xyz"][[pid_index[int(p)] for p in o[inside][ok, 1]]]
    np.savez(WORK / "seed169.npz", model=M, world=W)
    print(f"seed169: {len(o)} observations in ref 169, {inside.sum()} inside the frame, {ok.sum()} hit the rotunda")


def umeyama(A, B):
    """s, R, T with B ~ s R A + T (least squares)."""
    ma, mb = A.mean(0), B.mean(0)
    Ac, Bc = A - ma, B - mb
    U, S, Vt = np.linalg.svd(Bc.T @ Ac / len(A))
    Dm = np.eye(3); Dm[2, 2] = np.sign(np.linalg.det(U @ Vt))
    R = U @ Dm @ Vt
    s = (S * np.diag(Dm)).sum() / (Ac ** 2).sum(1).mean()
    return s, R, mb - s * R @ ma


def cmd_cameras():
    d, _ = load()
    sim = json.load(open(WORK / "sim.json"))
    s, Rs, Ts = sim["s"], np.array(sim["R"]), np.array(sim["T"])
    D = None
    rp = WORK / "refine.json"
    for flag, f in (("--with-D", rp), ("--with-cams", WORK / "refine_cams.json")):
        if flag in sys.argv and not f.exists():
            raise SystemExit(f"[align] {flag} given but {f.name} does not exist")
    if "--with-D" in sys.argv:
        p = json.load(open(rp))["p"]
        D = (math.exp(p[0]), Rot.from_rotvec(p[1:4]).as_matrix(), np.array(p[4:7]))
    PC = json.load(open(WORK / "refine_cams.json")) if "--with-cams" in sys.argv else {}
    cams = []
    for k, name in enumerate(d["names"]):
        R, t = d["R"][k], d["t"][k]
        # model: xc = R x + t;  world: X = s Rs x + Ts  ->  x = Rs^T (X - Ts)/s
        # xc = R Rs^T (X - Ts)/s + t  ;  metric camera coords = s xc = (R Rs^T) X + (s t - R Rs^T Ts)
        Rw = R @ Rs.T
        tw = s * t - Rw @ Ts
        Kk = d["K"][k].copy()
        if D is not None:                         # the chamfer world correction D (mat_p10_edges.py refine): the camera
            tw = (Rw @ D[2] + tw) / D[0]          # that sees mesh point X where the old one saw D(X) = s R X + T
            Rw = Rw @ D[1]
        pc = PC.get(str(name))
        if pc is not None:                        # per-camera rotation about its centre + focal scale
            dR = Rot.from_rotvec(pc["rotvec"]).as_matrix()
            Rw, tw = dR @ Rw, dR @ tw
            Kk[0, 0] *= pc["fscale"]; Kk[1, 1] *= pc["fscale"]
        rot_deg = float(np.degrees(np.linalg.norm(pc["rotvec"]))) if pc is not None else 0.0
        C = -Rw.T @ tw
        cams.append(dict(file=str(name), K=Kk.tolist(), k1=float(d["dist"][k]),
                         R=Rw.tolist(), t=tw.tolist(), centre=C.tolist(),
                         size=[int(d["wh"][k][0]), int(d["wh"][k][1])], refine_rot_deg=rot_deg))
    extra = {}
    ep = WORK / "edges.json"
    if ep.exists() and "--with-edges" in sys.argv:
        extra = json.load(open(ep))
        for c in cams:
            c["residual_px"] = extra.get("per_image", {}).get(c["file"])
    n_bad = 0
    for c in cams:                                  # physical gate (review part 1, finding 3)
        z = c["centre"][2]; r = math.hypot(c["centre"][0], c["centre"][1])
        c["usable_physical"] = bool(-0.5 <= z <= 6.0 and 30.0 <= r <= 250.0)
        n_bad += not c["usable_physical"]
    sim["world_correction_D"] = None if D is None else dict(s=D[0], R=D[1].tolist(), T=D[2].tolist())
    sim["per_camera_refined"] = len(PC)
    json.dump(dict(note="world = master metres (origin rotunda floor centre, +Y lagoon, +Z up). World-to-camera, COLMAP / "
                        "OpenCV axes (+x right, +y down, +z forward): pinhole x = K (R X + t), "
                        "then COLMAP SIMPLE_RADIAL: x_n *= 1 + k1 r^2 on normalised coords. size = the registered image "
                        "size (the probe's 1600 px thumbnail of reference/photos/raw/<src>).",
                   similarity=sim, cameras=cams), open(OUT / "cameras.json", "w"), indent=1)
    Cs = np.array([c["centre"] for c in cams])
    az = (np.degrees(np.arctan2(Cs[:, 1], -Cs[:, 0])) + 360) % 360
    rr = np.hypot(Cs[:, 0], Cs[:, 1])
    print(f"cameras.json: {n_bad} of {len(cams)} cameras fail the physical gate (z -0.5..6 m, r 30-250 m): "
          f"{[c['file'][:7] for c in cams if not c['usable_physical']]}")
    print(f"cameras.json: {len(cams)} cameras; distance {np.percentile(rr, [5, 50, 95]).round(1)} m, "
          f"azimuth {np.percentile(az, [5, 50, 95]).round(1)} deg, height {np.percentile(Cs[:, 2], [5, 50, 95]).round(1)} m")


SECTOR = None
if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[2].startswith("--sector"):
        SECTOR = int(sys.argv[2].split("=")[1])
    {"icp": cmd_icp, "cameras": cmd_cameras, "seed169": cmd_seed169}[sys.argv[1]]()
