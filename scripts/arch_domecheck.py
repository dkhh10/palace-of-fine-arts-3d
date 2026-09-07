#!/usr/bin/env python3
"""ARCH: analytic dome-visibility metric for the QA cameras (no Blender; numpy only).

QA-02-1 needs "how much of the dome + drum rises above the attic cornice, seen from CAM_qa_05".
`qa_silhouette.measure` cannot answer it: from an oblique, low station its `corner_top` (median of the outer 12 %
of the crop) lands on the RECEDING attic edge and its `apex` (min over the central 30 %) lands on the NEAR attic
corner block, so it reports a rise that is not the dome at all (measured 0.179 on round02_05 where the eye sees a
sliver). This module projects the actual parameterised solids instead:

    attic top ring   = entablature_plan() offset outward by the attic cornice projection, at z = ATTIC_Z1
    drum + dome      = surfaces of revolution from arch_params

and reports, per image column, attic_top_y - dome_top_y (positive = dome visible above the attic cornice).

    python3 scripts/arch_domecheck.py                 # current params, all cameras
    python3 scripts/arch_domecheck.py --set ATTIC_Z1=37.6 DOME_BASE_R=17.4
    python3 scripts/arch_domecheck.py --sweep          # sensitivity table

Metrics printed per camera:
    W_rot        on-screen width (px) of the attic top ring  (the "on-screen rotunda width")
    rise_px      max (attic_top_y - dome_top_y) over the columns
    rise_over_W  rise_px / W_rot          <- QA-02-1 acceptance: >= 0.09 at cam05
    cover        fraction of W_rot where the dome/drum is above the attic cornice  <- >= 0.60 at cam05
    apex_y       screen row of the dome apex (for the cam01 arbitration)
"""
import argparse, math, os, sys
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import arch_params as P

# ------------------------------------------------------------------ cameras (mirrors scripts/qa_cameras.py)
CAMS = {
    "01": dict(loc=(-14.1, 100.0, 1.6), target=(0.0, 0.0, 1.6), lens=20.0, shift_y=0.06, res=(1280, 720)),
    "02": dict(loc=(-45.0, 52.0, 1.3), target=(0.0, 0.0, 22.0), lens=20.0, shift_y=0.0, res=(1280, 720)),
    "05": dict(loc=(45.0, 55.0, 1.4), target=(0.0, 0.0, 20.0), lens=20.0, shift_y=0.0, res=(1280, 720)),
    "06": dict(loc=(-205.0, 143.0, 120.0), target=(0.0, 0.0, 15.0), lens=50.0, shift_y=0.0, res=(1280, 720)),
}


class Cam:
    def __init__(self, spec):
        self.loc = np.array(spec["loc"], float)
        f = np.array(spec["target"], float) - self.loc
        self.fwd = f / np.linalg.norm(f)
        r = np.cross(self.fwd, (0.0, 0.0, 1.0))
        self.right = r / np.linalg.norm(r)
        self.up = np.cross(self.right, self.fwd)
        self.rx, self.ry = spec["res"]
        self.f = self.rx * spec["lens"] / 36.0           # sensor_fit HORIZONTAL, sensor_width 36
        # Blender: +shift_y moves the rendered content DOWN, i.e. the principal point moves down the image.
        self.cx, self.cy = self.rx / 2.0, self.ry / 2.0 + spec.get("shift_y", 0.0) * self.rx

    def project(self, pts):
        """pts (N,3) -> (N,2) pixel coords; points behind the camera get x = nan."""
        d = np.asarray(pts, float) - self.loc
        z = d @ self.fwd
        x = d @ self.right
        y = d @ self.up
        out = np.empty((len(d), 2))
        with np.errstate(divide="ignore", invalid="ignore"):
            out[:, 0] = self.cx + self.f * x / z
            out[:, 1] = self.cy - self.f * y / z
        out[z <= 0.05] = np.nan
        return out


# ------------------------------------------------------------------ geometry from arch_params
def _bump(k, along, r_ch):
    """VertexFrame.bump for pier k, replicated without bpy."""
    az = P.VERTEX_AZ0 + 45 * k
    v = np.array(P.az_dir(az))
    V = v * P.WALL_CIRCUMRADIUS
    nA = np.array(P.az_dir(P.FACE_AZ0 + 45 * k))
    nB = np.array(P.az_dir(P.FACE_AZ0 + 45 * (k - 1)))
    out = []
    for n in (nA, nB):
        C = n * P.WALL_APOTHEM
        u = C - V
        u /= np.linalg.norm(u)
        w = V + u * along
        out.append(w + v * (r_ch - float(w @ v)))
    return out[1], out[0]          # cB, cA (B side first, matching entablature_plan order)


def attic_top_ring(z=None, out=0.74, dense=900):
    """Top edge of the attic cornice: the bumped octagon offset `out` outward, at z = ATTIC_Z1."""
    z = P.ATTIC_Z1 if z is None else z
    pts = []
    for k in range(8):
        cB, cA = _bump(k, P.RESSAUT_ALONG, P.CHAMFER_CIRCUMRADIUS + out)
        az = P.VERTEX_AZ0 + 45 * k
        v = np.array(P.az_dir(az))
        V = v * P.WALL_CIRCUMRADIUS
        for n in (np.array(P.az_dir(P.FACE_AZ0 + 45 * (k - 1))), np.array(P.az_dir(P.FACE_AZ0 + 45 * k))):
            pass
        # wall points on both faces, offset outward by `out`
        wB = _wall_pt(k, "B", P.RESSAUT_ALONG, out)
        wA = _wall_pt(k, "A", P.RESSAUT_ALONG, out)
        pts += [wB, cB, cA, wA]
    # densify each edge so the per-column min is accurate
    ring = []
    n = len(pts)
    for i in range(n):
        a, b = np.array(pts[i]), np.array(pts[(i + 1) % n])
        for t in np.linspace(0, 1, dense, endpoint=False):
            ring.append(a + (b - a) * t)
    return np.column_stack([np.array(ring), np.full(len(ring), z)])


def _wall_pt(k, side, along, out):
    az = P.VERTEX_AZ0 + 45 * k
    v = np.array(P.az_dir(az))
    V = v * P.WALL_CIRCUMRADIUS
    n = np.array(P.az_dir(P.FACE_AZ0 + 45 * (k if side == "A" else k - 1)))
    C = n * P.WALL_APOTHEM
    u = C - V
    u /= np.linalg.norm(u)
    return V + u * along + n * out


def dome_drum_surface(nseg=900, nprof=120):
    """(r, z) profile of drum cornice + dome, revolved."""
    prof = [(P.DRUM_CORNICE_R, P.DRUM_Z1 - 0.15), (P.DRUM_CORNICE_R - 0.25, P.DRUM_Z1),
            (P.DOME_BASE_R + 0.25, P.DRUM_Z1)]
    th0 = math.asin(min(1.0, P.DOME_BASE_R / P.DOME_SPHERE_R))
    for i in range(nprof + 1):
        th = th0 * (1 - i / nprof)
        prof.append((P.DOME_SPHERE_R * math.sin(th), P.DOME_SPHERE_CZ + P.DOME_SPHERE_R * math.cos(th)))
    a = np.linspace(0, 2 * math.pi, nseg, endpoint=False)
    ca, sa = np.cos(a), np.sin(a)
    pts = []
    for r, z in prof:
        pts.append(np.column_stack([r * ca, r * sa, np.full(nseg, z)]))
    return np.vstack(pts)


def drum_wall_surface(nseg=900):
    """The plain drum wall + guilloche band below the cornice (what shows as a 'sliver')."""
    a = np.linspace(0, 2 * math.pi, nseg, endpoint=False)
    ca, sa = np.cos(a), np.sin(a)
    pts = []
    for z in np.linspace(P.DRUM_Z0, P.DRUM_Z1 - 0.15, 12):
        r = P.DRUM_BAND_R + 0.55
        pts.append(np.column_stack([r * ca, r * sa, np.full(nseg, z)]))
    return np.vstack(pts)


# ------------------------------------------------------------------ metric
def top_profile(cam, pts, width):
    """min screen y per integer column."""
    uv = cam.project(pts)
    ok = np.isfinite(uv[:, 0])
    uv = uv[ok]
    col = np.floor(uv[:, 0]).astype(int)
    prof = np.full(width, np.inf)
    inb = (col >= 0) & (col < width)
    np.minimum.at(prof, col[inb], uv[inb, 1])
    return prof


def measure(camkey):
    cam = Cam(CAMS[camkey])
    W = cam.rx
    attic = top_profile(cam, attic_top_ring(), W)
    dome = top_profile(cam, dome_drum_surface(), W)
    drum = top_profile(cam, drum_wall_surface(), W)
    upper = np.minimum(dome, drum)
    cols = np.where(np.isfinite(attic))[0]
    if len(cols) == 0:
        return None
    x0, x1 = cols[0], cols[-1]
    w_rot = x1 - x0
    d = attic[x0:x1 + 1] - upper[x0:x1 + 1]        # >0 : upper mass above the attic cornice
    d = np.where(np.isfinite(d), d, -np.inf)
    rise = float(d.max())
    cover = float((d > 1.0).sum()) / max(1, w_rot)
    dcap = attic[x0:x1 + 1] - dome[x0:x1 + 1]
    cap_cover = float((np.where(np.isfinite(dcap), dcap, -np.inf) > 1.0).sum()) / max(1, w_rot)
    apex_y = float(np.nanmin(dome[np.isfinite(dome)])) if np.isfinite(dome).any() else float("nan")
    return dict(cam=camkey, W_rot=int(w_rot), x0=int(x0), x1=int(x1), rise_px=round(rise, 1),
                rise_over_W=round(rise / w_rot, 4), cover=round(cover, 3), dome_cap_cover=round(cap_cover, 3),
                apex_y=round(apex_y, 1), apex_frac_h=round(apex_y / cam.ry, 4))


def apply_set(assignments):
    for a in assignments:
        k, v = a.split("=")
        setattr(P, k, float(v))
    # re-derive everything downstream of the assignments
    P.ATTIC_Z1 = P.ATTIC_Z0 + P.ATTIC_H if "ATTIC_Z1" not in [a.split("=")[0] for a in assignments] else P.ATTIC_Z1
    P.DRUM_Z0 = P.ATTIC_Z1 if "DRUM_Z0" not in [a.split("=")[0] for a in assignments] else P.DRUM_Z0
    P.DRUM_H = P.DRUM_PLAIN_H + P.DRUM_BAND_H + P.DRUM_CORNICE_H
    P.DRUM_Z1 = P.DRUM_Z0 + P.DRUM_H
    P.DOME_APEX_Z = P.DRUM_Z1 + P.DOME_RISE
    P.DOME_SPHERE_R = (P.DOME_BASE_R ** 2 + P.DOME_RISE ** 2) / (2 * P.DOME_RISE)
    P.DOME_SPHERE_CZ = P.DOME_APEX_Z - P.DOME_SPHERE_R


def custom(loc, target=(0.0, 0.0, 20.0), lens=20.0, shift_y=0.0, res=(1280, 720), key=None):
    """measure() for an arbitrary station; returns the same dict plus clear_over_W (dome apex above the HIGHEST
    attic point, i.e. the near corner block -- the number that says whether a dome cap reads at all)."""
    CAMS["_tmp"] = dict(loc=loc, target=target, lens=lens, shift_y=shift_y, res=res)
    r = measure("_tmp")
    cam = Cam(CAMS["_tmp"])
    attic = top_profile(cam, attic_top_ring(), cam.rx)
    dome = top_profile(cam, dome_drum_surface(), cam.rx)
    r["clear_over_W"] = round((np.nanmin(attic[np.isfinite(attic)]) - np.nanmin(dome[np.isfinite(dome)])) / r["W_rot"], 4)
    r["cam"] = key or "custom"
    return r


def fit_photo(photo, xr=(500, 1620), start=(104.5, 115.0, 1.5, 40.0, 20.0)):
    """Least-median fit of (azimuth, distance, height, lens, target_z) so the parameterised silhouette matches a
    photograph's measured top profile. Used to establish which station a reference photo was taken from before
    blaming the model for a silhouette mismatch (QA-02-1)."""
    import qa_silhouette as QS
    img = QS.load(photo)
    H, W = img.shape[:2]
    pp = QS.profile(QS.building_mask(img), 0, 0, W, min(H, 600)).astype(float)
    pp[pp < 0] = np.nan
    allpts = np.vstack([attic_top_ring(), dome_drum_surface(), drum_wall_surface()])

    def cost(q):
        az, dist, h, lens, tz = q
        if not (60 < az < 200 and 40 < dist < 300 and 0.3 < h < 15 and 8 < lens < 140 and 5 < tz < 60):
            return 1e9
        x, y = P.az_to_xy(az, dist)
        cam = Cam(dict(loc=(x, y, h), target=(0.0, 0.0, tz), lens=lens, shift_y=0.0, res=(W, H)))
        mp = top_profile(cam, allpts, W)
        xs = np.arange(*xr)
        a, b = mp[xs], pp[xs]
        ok = np.isfinite(a) & np.isfinite(b)
        if ok.sum() < 200:
            return 1e9
        r = a[ok] - b[ok]
        med = np.median(r)
        return float(np.median(np.abs(r - med)) + abs(med))

    q = list(start)
    steps = [8.0, 20.0, 2.0, 10.0, 8.0]
    while max(steps) > 1e-3:
        moved = False
        for i in range(5):
            for s in (steps[i], -steps[i]):
                t = list(q)
                t[i] += s
                if cost(t) < cost(q) - 1e-6:
                    q, moved = t, True
        if not moved:
            steps = [s * 0.5 for s in steps]
    return dict(az=round(q[0], 1), dist=round(q[1], 1), height=round(q[2], 2), lens=round(q[3], 1),
                target_z=round(q[4], 1), cost_px=round(cost(q), 1), loc=tuple(round(v, 1) for v in P.az_to_xy(q[0], q[1])))


def overlay(photo, q, out):
    """Draw the parameterised silhouette (red) on a photograph at the fitted station."""
    from PIL import Image, ImageDraw
    im = Image.open(photo).convert("RGB")
    W, H = im.size
    x, y = P.az_to_xy(q["az"], q["dist"])
    cam = Cam(dict(loc=(x, y, q["height"]), target=(0.0, 0.0, q["target_z"]), lens=q["lens"], shift_y=0.0, res=(W, H)))
    allpts = np.vstack([attic_top_ring(), dome_drum_surface(), drum_wall_surface()])
    mp = top_profile(cam, allpts, W)
    d = ImageDraw.Draw(im)
    pts = [(i, mp[i]) for i in range(W) if np.isfinite(mp[i]) and 0 <= mp[i] < H]
    for i in range(len(pts) - 1):
        if abs(pts[i + 1][0] - pts[i][0]) <= 2:
            d.line([pts[i], pts[i + 1]], fill=(255, 40, 40), width=3)
    im.save(out)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", nargs="*", default=[])
    ap.add_argument("--cams", default="01,05,02")
    ap.add_argument("--fit", help="photograph to fit a camera station to")
    ap.add_argument("--overlay", help="write the fitted silhouette overlay here")
    a = ap.parse_args()
    if a.set:
        apply_set(a.set)
    print(f"# ATTIC_Z1={P.ATTIC_Z1:.2f} DRUM_Z1={P.DRUM_Z1:.2f} DOME_BASE_R={P.DOME_BASE_R:.2f} "
          f"DOME_RISE={P.DOME_RISE:.2f} APEX={P.DOME_APEX_Z:.2f} SPHERE_R={P.DOME_SPHERE_R:.2f}")
    for c in a.cams.split(","):
        print(measure(c))
    if a.fit:
        q = fit_photo(a.fit)
        print("fit:", q)
        print("model at the fitted station:", custom((q["loc"][0], q["loc"][1], q["height"]),
              target=(0.0, 0.0, q["target_z"]), lens=q["lens"], res=Image.open(a.fit).size, key="fitted"))
        if a.overlay:
            print("wrote", overlay(a.fit, q, a.overlay))
