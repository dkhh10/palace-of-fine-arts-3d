"""Phase 10 r1, step 4 -- position / normal atlases per UVBake group, rasterised in numpy (no bpy).

    .venv-p10/bin/python scripts/mat_p10_atlas.py [--res 2048]

Input work/uvbake_tris.npz (mat_p10_meshdump.py uvbake: local triangles, UVBake corners, corner normals, instances).
Output work/atlas_g<g>.npz: mesh (res,res) int16 (-1 = empty), lpos / lnrm (res,res,3) float32 in the mesh's LOCAL
space (texel centre, barycentric; normals from the corner normals).  World positions are per instance
(uvbake_tris.npz mats): the 16 columns share one region.  This is the brief's Cycles position / normal bake done
exactly on the texel centres; Blender's UV convention (v up) -> row iy = v * res - 0.5, flipped when saved as PNG.
Also prints per group: atlas fill and the texel size in metres on weight-1 faces.
"""
import sys, time
import numpy as np
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
import mat_p10_common as C

RES = int(sys.argv[sys.argv.index("--res") + 1]) if "--res" in sys.argv else 2048


def raster(P, N, UV, O, res):
    mesh = np.full((res, res), -1, np.int16)
    lpos = np.zeros((res, res, 3), np.float32)
    lnrm = np.zeros((res, res, 3), np.float32)
    T = UV.astype(np.float64) * res - 0.5
    for i in range(len(T)):
        t = T[i]
        x0, y0 = np.floor(t.min(0)).astype(int); x1, y1 = np.ceil(t.max(0)).astype(int)
        x0, y0 = max(x0, 0), max(y0, 0); x1, y1 = min(x1, res - 1), min(y1, res - 1)
        if x1 < x0 or y1 < y0:
            continue
        xs, ys = np.meshgrid(np.arange(x0, x1 + 1), np.arange(y0, y1 + 1))
        (ax, ay), (bx, by), (cx, cy) = t
        den = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if abs(den) < 1e-14:
            continue
        l1 = ((by - cy) * (xs - cx) + (cx - bx) * (ys - cy)) / den
        l2 = ((cy - ay) * (xs - cx) + (ax - cx) * (ys - cy)) / den
        l3 = 1 - l1 - l2
        ins = (l1 >= -1e-9) & (l2 >= -1e-9) & (l3 >= -1e-9)
        if not ins.any():
            continue
        yy, xx = ys[ins], xs[ins]
        b = np.stack([l1[ins], l2[ins], l3[ins]], 1)
        mesh[yy, xx] = O[i]
        lpos[yy, xx] = b @ P[i]
        n = b @ N[i]
        lnrm[yy, xx] = n / np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
    return mesh, lpos, lnrm


if __name__ == "__main__":
    d = np.load(C.WORK / "uvbake_tris.npz")
    for g in np.unique(d["G"]):
        t0 = time.time()
        m = d["G"] == g
        mesh, lpos, lnrm = raster(d["P"][m], d["N"][m], d["UV"][m], d["O"][m], RES)
        np.savez_compressed(C.WORK / f"atlas_g{g}.npz", mesh=mesh, lpos=lpos, lnrm=lnrm, res=RES)
        print(f"[atlas] group {g}: {m.sum()} triangles, fill {100 * (mesh >= 0).mean():.1f} % at {RES}, "
              f"{time.time() - t0:.0f} s")
