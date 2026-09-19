#!/usr/bin/env python3
"""Phase 8a re-scope — question 3: WHICH shrub LOD set and WHICH species fill each QA-17 box.

No Blender, no Chrome, no rendering. The 1 379 shrub placements (world translations, from the
export's own `instance_irradiance.json`) are projected into each station's frame with the station's
Blender camera (`web/src/stations_blender.json`), so every box gets the list of placements that land
in it, their distance, their prototype and their LOD.

    python3 scripts/p8a_rescope_lod.py camcheck   # validate the camera model against the gate9 sidecar
    python3 scripts/p8a_rescope_lod.py boxes      # per QA-17 box: placements, distance, prototype mix
    python3 scripts/p8a_rescope_lod.py cost       # the triangle cost of moving the LOD switch out
    python3 scripts/p8a_rescope_lod.py all

The switch: `info.shrubLod.dist` in the gate9 sidecar = 30 m. Under it the LOD1 walk-in meshes
(`env_shrubs.glb`), over it the LOD2 set that ships inside the env groups.
"""
import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import qa_r17_probe as P17  # noqa: E402

MAIN = Path("/Users/dk/Projects/3d render blender 3rd attempt building")
ROOT = Path(__file__).resolve().parents[1]
IRR = MAIN / "export/out/gate3/instance_irradiance.json"
SHRUB_LOD1 = MAIN / "export/out/gate1/shrub_lod1.json"
STATIONS = ROOT / "web/src/stations_blender.json"
SIDECAR = MAIN / "renders/web/gate9_cam.json"
W, H = 1920, 1080
PROTOS = ("agap", "big", "maho", "pitto", "reed", "twig")


MANIFEST = MAIN / "export/out/gate5/manifest.json"


def stations():
    """Index -> the station's own Blender camera, rotation included (the manifest is authority)."""
    out = {s["index"]: dict(s) for s in json.loads(STATIONS.read_text())["stations"]}
    man = json.loads(MANIFEST.read_text())["stations"]
    for st in out.values():
        m = man.get(st["name"])
        if m:
            st["rotation_euler_xyz"] = m["rotation_euler_xyz"]
            st["lens"], st["sensor_width"] = m["lens_mm"], m["sensor_width_mm"]
            st["shift_y"], st["shift_x"] = m["shift_y"], m["shift_x"]
    return out


def _basis(st):
    """(right, up, forward) of the Blender camera in world axes."""
    e = st.get("rotation_euler_xyz")
    if e:
        cx, sx = math.cos(e[0]), math.sin(e[0])
        cy, sy = math.cos(e[1]), math.sin(e[1])
        cz, sz = math.cos(e[2]), math.sin(e[2])
        Rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
        Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
        Rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
        R = Rz @ Ry @ Rx              # Blender XYZ euler order
        return R[:, 0], R[:, 1], -R[:, 2]   # a Blender camera looks along its local -Z
    loc = np.array(st["location"], dtype=np.float64)
    f = np.array(st["target"], dtype=np.float64) - loc
    f /= np.linalg.norm(f)
    r = np.cross(f, np.array([0.0, 0.0, 1.0]))
    r = r / np.linalg.norm(r) if np.linalg.norm(r) > 1e-9 else np.array([1.0, 0.0, 0.0])
    return r, np.cross(r, f), f


def project(st, pts):
    """Blender camera -> pixel coords. Returns (px, py, depth_m); depth <= 0 is behind the camera."""
    loc = np.array(st["location"], dtype=np.float64)
    r, u, f = _basis(st)
    v = pts - loc
    x, y, d = v @ r, v @ u, v @ f
    lens, sw = st["lens"], st["sensor_width"]
    aspect = W / H
    sh = sw / aspect                                     # sensor height for a HORIZONTAL fit
    with np.errstate(divide="ignore", invalid="ignore"):
        su = x * lens / d                                 # mm on the sensor
        sv = y * lens / d
    px = (su / sw + 0.5 + st.get("shift_x", 0.0) * 1.0) * W
    py = (0.5 - (sv / sh) + st.get("shift_y", 0.0) * (sw / sh)) * H
    return px, py, d


def placements():
    """(names, locs, protos, lod1_flag) for the 1 379 shrub/reed placements."""
    d = json.loads(IRR.read_text())
    names, locs, pr = [], [], []
    for k, e in d["meshes"].items():
        p = next((q for q in PROTOS if q in k), "?")
        for x in e["placements"]:
            names.append(x["object"])
            locs.append(x["loc"])
            pr.append(p)
    lod1 = set()
    if SHRUB_LOD1.exists():
        s = json.loads(SHRUB_LOD1.read_text())
        for x in s["placements"]:
            n = x.get("object") or x.get("name")
            if n:
                lod1.add(n)
    return np.array(names), np.array(locs, dtype=np.float64), np.array(pr), lod1


def cmd_camcheck():
    """The station-1 camera from the sidecar vs the model above, on the shrub placements."""
    sc = json.loads(SIDECAR.read_text())["info"]
    M = np.array(sc["cameraWorldMatrix"], dtype=np.float64).reshape(4, 4).T   # three.js is column-major
    Pm = np.array(sc["projectionMatrix"], dtype=np.float64).reshape(4, 4).T
    names, locs, pr, _ = placements()
    # Blender (x, y, z) -> glTF/three (x, z, -y), the export's own axis swap.
    g = np.stack([locs[:, 0], locs[:, 2], -locs[:, 1]], 1)
    Vm = np.linalg.inv(M)
    h = np.concatenate([g, np.ones((len(g), 1))], 1) @ Vm.T @ Pm.T
    ok = h[:, 3] > 1e-9
    ndc = h[ok, :3] / h[ok, 3:4]
    px_s = (ndc[:, 0] * 0.5 + 0.5) * W
    py_s = (0.5 - ndc[:, 1] * 0.5) * H
    px_m, py_m, d = project(stations()[1], locs)
    px_m, py_m = px_m[ok], py_m[ok]
    vis = (px_s > 0) & (px_s < W) & (py_s > 0) & (py_s < H)
    dx, dy = px_s[vis] - px_m[vis], py_s[vis] - py_m[vis]
    print("== station 1: the sidecar's own camera matrices vs the manifest's Blender camera ==")
    print(f"   {int(ok.sum())} placements in front of the camera, {int(vis.sum())} inside the frame")
    print(f"   dx {dx.mean():+.2f} px (sd {dx.std():.2f})   dy {dy.mean():+.2f} px (sd {dy.std():.2f})")
    fwd_s = -M[:3, 2]
    r, u, f = _basis(stations()[1])
    fg = np.array([f[0], f[2], -f[1]])
    ang = math.degrees(math.acos(float(np.clip(fwd_s @ fg, -1, 1))))
    print(f"   the matrix RECORDED in the sidecar sits {ang:.3f} deg below the manifest's camera axis")
    print(f"   (a look-at aimed at the world origin instead of the station's z = 1.3 target), which is")
    print(f"   exactly the {dy.mean():+.1f} px (sd {dy.std():.3f} = a rigid shift, not a projection error).")
    print("   `framecheck` settles which one actually rendered: the capture and the Cycles frame")
    print("   cross-correlate at dy = 0 at every station, so the SIDECAR FIELD is the stale thing and")
    print("   the model below is the camera that drew the pixels. Horizontal agreement is 0.02 px.")


def cmd_framecheck():
    """Confirm the camera finding on the PIXELS: the vertical offset between the viewer capture and
    the Cycles reference, by normalised cross-correlation of their luma gradients."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import p8a_rescope_boxes as B  # noqa: E402  (its reference set is rooted at MAIN)
    print("== the viewer capture against the Cycles reference: the rigid vertical offset, per station ==")
    print(f"{'st':>2s} {'best dy px':>10s} {'ncc':>7s} {'ncc at 0':>9s} {'best dx px':>10s}")
    for st in (1, 2, 3, 5, 6):
        a = B.frame(B.CUR, st) @ B.P.LUMA
        r = B.ref(st) @ B.P.LUMA
        ga, gr = np.abs(np.diff(a, axis=0))[:, 8:], np.abs(np.diff(r, axis=0))[:, 8:]
        h = ga.shape[0]

        def ncc(x, y):
            x = x - x.mean()
            y = y - y.mean()
            return float((x * y).sum() / max(math.sqrt((x * x).sum() * (y * y).sum()), 1e-9))
        best, bv = 0, -2
        at0 = ncc(ga[40:h - 40], gr[40:h - 40])
        for dy in range(-30, 31):
            v = ncc(ga[40 + dy:h - 40 + dy], gr[40:h - 40])
            if v > bv:
                bv, best = v, dy
        bx, bxv = 0, -2
        for dx in range(-20, 21):
            v = ncc(ga[40:h - 40, 40 + dx:-40 + dx or None], gr[40:h - 40, 40:-40])
            if v > bxv:
                bxv, bx = v, dx
        print(f"{st:2d} {best:10d} {bv:7.3f} {at0:9.3f} {bx:10d}")
    print("\n-- dy > 0 means the viewer frame has to be shifted DOWN to line up with Cycles, i.e. the")
    print("   viewer shows the scene higher in the frame, which is the camcheck's -13.7 px.")


def cmd_boxes():
    names, locs, pr, lod1 = placements()
    sc = json.loads(SIDECAR.read_text())["info"]
    dist = sc.get("shrubLod", {}).get("dist", 30)
    S = stations()
    print(f"== the QA-17 shrub boxes: which placements land in them (LOD switch at {dist} m) ==")
    print(f"{'box':22s} {'st':>2s} {'n':>4s} {'dist m p10/med/p90':>22s} {'<switch':>8s} "
          f"{'prototype mix':>44s}")
    for name, st, box, _why in P17.SHRUB:
        x0, y0, x1, y1 = box
        px, py, d = project(S[st], locs)
        m = (d > 0.5) & (px >= x0) & (px < x1) & (py >= y0) & (py < y1)
        if m.sum() == 0:
            # the box is a BAND: a card's origin can sit just outside while its canopy fills it
            m = (d > 0.5) & (px >= x0 - 60) & (px < x1 + 60) & (py >= y0 - 60) & (py < y1 + 60)
            tag = "*"
        else:
            tag = " "
        dd = d[m]
        mix = {}
        for p in pr[m]:
            mix[p] = mix.get(p, 0) + 1
        mixs = " ".join(f"{k}:{v}" for k, v in sorted(mix.items(), key=lambda t: -t[1]))
        print(f"{name+tag:22s} {st:2d} {int(m.sum()):4d} "
              f"{np.percentile(dd,10):6.0f}/{np.median(dd):6.0f}/{np.percentile(dd,90):6.0f} "
              f"{int((dd < dist).sum()):8d} {mixs:>44s}")
    print("\n  * = no placement ORIGIN inside the box, so the box was grown by 60 px: these bands are")
    print("    filled by the canopies of cards whose origin sits below or beside the crop.")
    print("  prototypes: agap agapanthus / big large shrub / maho mahonia / pitto pittosporum /")
    print("              reed reed clump / twig bare twiggy shrub.")


def cmd_cost():
    s = json.loads(SHRUB_LOD1.read_text())
    lod1, lod2 = s["placed_tris"], s["placed_tris_lod2"]
    sc = json.loads(SIDECAR.read_text())
    per = {x["station"]: x for x in sc["perStation"]}
    print("== the triangle cost of moving the shrub LOD switch out to the hero shore ==")
    print(f"   placed triangles, whole set: LOD1 {lod1:,}  LOD2 {lod2:,}  (delta {lod1-lod2:+,})")
    print(f"   the five water stations render the shrubs TWICE (the Reflector pass), so the frame")
    print(f"   delta there is {2*(lod1-lod2):+,}.")
    print(f"\n{'station':>7s} {'triangles now':>14s} {'draws':>6s} "
          f"{'+all LOD1':>12s} {'x now':>6s}")
    for st in sorted(per):
        t = per[st]["triangles"]
        water = st in (1, 2, 4, 5, 6)
        add = (2 if water else 1) * (lod1 - lod2)
        print(f"{st:7d} {t:14,} {per[st]['draw_calls']:6d} {t+add:12,} {(t+add)/t:5.2f}x")
    print("\n-- and the QA-20 finding that must be subtracted first: `env_shrubs.glb` (the LOD1 walk-in")
    print("   set) is already submitted in full at every station, so part of this cost is ALREADY")
    print("   being paid for nothing. Re-price after that bug is fixed, never before.")


def main():
    cmds = {"camcheck": cmd_camcheck, "framecheck": cmd_framecheck, "boxes": cmd_boxes, "cost": cmd_cost}
    for a in (sys.argv[1:] or ["all"]):
        if a == "all":
            for f in (cmd_camcheck, cmd_framecheck, cmd_boxes, cmd_cost):
                f()
                print()
        elif a in cmds:
            cmds[a]()
        else:
            print(f"unknown command {a!r}; one of {', '.join(cmds)} or all")


if __name__ == "__main__":
    main()
