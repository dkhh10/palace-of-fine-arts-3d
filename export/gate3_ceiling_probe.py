"""Gate 3 QA-13-2 — why `ARCH_rotunda_plaster_ceiling_merged` bakes to max 0.72 / 4.9 % non-zero.

CPU only (ray-cast + numpy over the archival EXR); no render, no GPU.

Measures, on the exact bake state (`export/out/gate3/gate3_bake.blend`):
  1. which faces of the shell are visible from CAM_qa_04_rotunda_ceiling and CAM_qa_01_lagoon_hero
     (screen grid of rays + a per-face centroid ray with an occlusion test),
  2. the fraction of the asset's UV2 area those faces own,
  3. what the bake wrote on exactly those texels (non-zero fraction, min/max/mean/p99),
  4. whether the faces are oriented toward the camera, and whether the *shading* hemisphere
     (the +normal side, which is the only side a Cycles bake integrates) is open to the sky
     or enclosed - a cosine-hemisphere escape test on both sides.

Run:  scripts/blender_run.sh 1200 -- --background --python export/gate3_ceiling_probe.py
"""
import json
import math
import sys
import time
from pathlib import Path

import bpy
import numpy as np
from mathutils import Euler, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gate0_common as g0  # noqa: E402
import gate3_common as g3  # noqa: E402

SHELL = "ARCH_rotunda_plaster_ceiling_merged"
RIB = "ARCH_rotunda_plaster_ceiling_rib_merged"
GRID_W, GRID_H = 480, 270
HEMI_RAYS = 96
HEMI_FACES = 48
OUT_JSON = g3.OUT / "ceiling_probe.json"

# The two stations, copied from scripts/qa_cameras.py (CAMERAS[0] and CAMERAS[3]).
STATIONS = [
    dict(key="cam04", name="CAM_qa_04_rotunda_ceiling", loc=(0.0, 3.0, 1.6),
         target=(0.0, 3.0, 40.0), lens=15.0, shift_y=0.0, straight_up=True),
    dict(key="cam01", name="CAM_qa_01_lagoon_hero", loc=(-14.1, 100.0, 1.3),
         target=(0.0, 0.0, 1.3), lens=20.0, shift_y=0.06, straight_up=False),
]


def log(m):
    print(f"[ceilprobe] {m}", flush=True)


def make_cam(sc, spec):
    d = bpy.data.cameras.new(spec["name"] + "_probe")
    d.lens = spec["lens"]
    d.sensor_width = 36.0
    d.sensor_fit = "HORIZONTAL"
    d.clip_start = 0.1
    d.clip_end = 5000.0
    d.shift_y = spec["shift_y"]
    ob = bpy.data.objects.new(spec["name"] + "_probe", d)
    ob.location = spec["loc"]
    if spec["straight_up"]:
        ob.rotation_euler = Euler((math.pi, 0.0, 0.0))
    else:
        fwd = Vector(spec["target"]) - Vector(spec["loc"])
        ob.rotation_euler = fwd.to_track_quat("-Z", "Y").to_euler()
    sc.collection.objects.link(ob)
    return ob


# The bake record (out/gate3/bake/lm_<obj>.json) names the layer the bake job actually attached;
# the layer flagged active_render in the SAVED blend is not it (each job sets its own in its own process).
def baked_uv_layer(obj_name):
    rec = g3.OUT / "bake" / f"lm_{obj_name}.json"
    name = json.loads(rec.read_text())["uv"] if rec.exists() else g0.UV2
    return name


def loop_uvs(lay, n_loops):
    buf = np.empty(n_loops * 2, dtype=np.float32)
    try:
        lay.uv.foreach_get("vector", buf)
    except Exception:
        lay.data.foreach_get("uv", buf)
    return buf.reshape(-1, 2)


def tri_texels(uv0, uv1, uv2, size):
    """Texel (row, col) indices covered by one UV triangle. Rows are BOTTOM-UP (v = 0 -> row 0),
    matching gate3_common.read_exr32's return."""
    p = np.array([uv0, uv1, uv2], dtype=np.float64) * size
    x0 = int(max(0, math.floor(p[:, 0].min())))
    x1 = int(min(size - 1, math.ceil(p[:, 0].max())))
    y0 = int(max(0, math.floor(p[:, 1].min())))
    y1 = int(min(size - 1, math.ceil(p[:, 1].max())))
    if x1 < x0 or y1 < y0:
        return None
    xs = np.arange(x0, x1 + 1) + 0.5
    ys = np.arange(y0, y1 + 1) + 0.5
    gx, gy = np.meshgrid(xs, ys)
    d = ((p[1, 1] - p[2, 1]) * (p[0, 0] - p[2, 0]) + (p[2, 0] - p[1, 0]) * (p[0, 1] - p[2, 1]))
    if abs(d) < 1e-12:
        return None
    a = ((p[1, 1] - p[2, 1]) * (gx - p[2, 0]) + (p[2, 0] - p[1, 0]) * (gy - p[2, 1])) / d
    b = ((p[2, 1] - p[0, 1]) * (gx - p[2, 0]) + (p[0, 0] - p[2, 0]) * (gy - p[2, 1])) / d
    c = 1.0 - a - b
    m = (a >= -1e-9) & (b >= -1e-9) & (c >= -1e-9)
    if not m.any():
        # sub-texel triangle: take its centroid texel
        cx = int(np.clip(p[:, 0].mean(), 0, size - 1))
        cy = int(np.clip(p[:, 1].mean(), 0, size - 1))
        return np.array([cy]), np.array([cx])
    rr = (np.repeat(np.arange(y0, y1 + 1), x1 - x0 + 1).reshape(m.shape))[m]
    cc = (np.tile(np.arange(x0, x1 + 1), y1 - y0 + 1).reshape(m.shape))[m]
    return rr, cc


def main():
    t0 = time.time()
    blend = g3.OUT / "gate3_bake.blend"
    assert blend.exists(), blend
    bpy.ops.wm.open_mainfile(filepath=str(blend))
    sc = bpy.context.scene
    sc.render.resolution_x, sc.render.resolution_y = 1920, 1080
    sc.render.resolution_percentage = 100
    rep = {"blend": str(blend), "shell": SHELL}

    # The depsgraph a ray-cast walks obeys hide_viewport, the bake obeys hide_render.
    # Mirror render visibility onto the viewport so the rays see exactly what the bake saw.
    flipped = 0
    for ob in bpy.data.objects:
        if ob.type != "MESH":
            continue
        if ob.hide_viewport != ob.hide_render:
            ob.hide_viewport = ob.hide_render
            flipped += 1
    rep["hide_viewport_synced_to_hide_render"] = flipped
    log(f"visibility synced on {flipped} objects")

    shell = bpy.data.objects.get(SHELL)
    rib = bpy.data.objects.get(RIB)
    assert shell is not None, SHELL
    me = shell.data
    mw = shell.matrix_world
    nmat = mw.to_3x3().inverted().transposed()
    lay_name = baked_uv_layer(SHELL)
    lay = me.uv_layers[lay_name]
    rep["uv2_layer_baked"] = lay_name
    rep["uv2_layer_active_render_in_saved_blend"] = next(
        (ly.name for ly in me.uv_layers if ly.active_render), None)
    rep["uv2_layers"] = [ly.name for ly in me.uv_layers]
    rep["mesh"] = me.name
    rep["polys"] = len(me.polygons)
    rep["tris"] = sum(len(p.vertices) - 2 for p in me.polygons)

    uvs = loop_uvs(lay, len(me.loops))
    wco = [mw @ v.co for v in me.vertices]

    # per-face world area, uv area, centroid, world normal
    n_p = len(me.polygons)
    f_area = np.zeros(n_p)
    f_uvarea = np.zeros(n_p)
    f_cent = np.zeros((n_p, 3))
    f_nrm = np.zeros((n_p, 3))
    for i, p in enumerate(me.polygons):
        vs = [wco[k] for k in p.vertices]
        a = 0.0
        for k in range(1, len(vs) - 1):
            a += (vs[k] - vs[0]).cross(vs[k + 1] - vs[0]).length * 0.5
        f_area[i] = a
        pu = uvs[list(p.loop_indices)]
        ua = 0.0
        for k in range(1, len(pu) - 1):
            e1, e2 = pu[k] - pu[0], pu[k + 1] - pu[0]
            ua += abs(float(e1[0] * e2[1] - e1[1] * e2[0])) * 0.5
        f_uvarea[i] = ua
        c = mw @ p.center
        f_cent[i] = (c.x, c.y, c.z)
        nn = (nmat @ p.normal).normalized()
        f_nrm[i] = (nn.x, nn.y, nn.z)
    rep["world_area_m2"] = round(float(f_area.sum()), 1)
    rep["uv2_coverage"] = round(float(f_uvarea.sum()), 5)
    up = f_nrm[:, 2]
    rep["normals"] = {
        "area_normal_up_gt_0.5": round(float(f_area[up > 0.5].sum() / f_area.sum()), 4),
        "area_normal_down_lt_-0.5": round(float(f_area[up < -0.5].sum() / f_area.sum()), 4),
        "area_normal_side": round(float(f_area[np.abs(up) <= 0.5].sum() / f_area.sum()), 4),
    }

    dg = bpy.context.evaluated_depsgraph_get()

    def cast(orig, direc, dist=6000.0):
        return sc.ray_cast(dg, orig, direc, distance=dist)

    # ---------------------------------------------------------------- screen grids
    rep["stations"] = {}
    vis_faces = {}
    for spec in STATIONS:
        cam = make_cam(sc, spec)
        dg = bpy.context.evaluated_depsgraph_get()
        cmw = cam.matrix_world
        orig = cmw.translation.copy()
        fr = cam.data.view_frame(scene=sc)  # tr, br, bl, tl in camera space
        tr, br, bl, tl = fr
        hits = {}
        shell_px = {}
        n_rays = 0
        for iy in range(GRID_H):
            ty = (iy + 0.5) / GRID_H
            left = bl.lerp(tl, ty)
            right = br.lerp(tr, ty)
            for ix in range(GRID_W):
                tx = (ix + 0.5) / GRID_W
                p = cmw @ left.lerp(right, tx)
                d = (p - orig).normalized()
                n_rays += 1
                ok, loc, nrm, idx, ob, _ = cast(orig, d)
                if not ok or ob is None:
                    hits["<sky>"] = hits.get("<sky>", 0) + 1
                    continue
                nm = ob.original.name if ob.original else ob.name
                hits[nm] = hits.get(nm, 0) + 1
                if nm == SHELL:
                    shell_px[idx] = shell_px.get(idx, 0) + 1
        top = sorted(hits.items(), key=lambda kv: -kv[1])[:8]
        st = {
            "rays": n_rays,
            "top_hits_pct": {k: round(100.0 * v / n_rays, 2) for k, v in top},
            "shell_pixel_pct": round(100.0 * sum(shell_px.values()) / n_rays, 3),
            "shell_faces_hit": len(shell_px),
        }
        # per-face centroid visibility (in frustum + unoccluded), independent of pixel density
        import bpy_extras.object_utils as bou
        seen = []
        for i in range(n_p):
            c = Vector(f_cent[i])
            uvp = bou.world_to_camera_view(sc, cam, c)
            if not (0.0 <= uvp.x <= 1.0 and 0.0 <= uvp.y <= 1.0 and uvp.z > 0.0):
                continue
            d = (c - orig)
            dist = d.length
            d = d.normalized()
            ok, loc, nrm, idx, ob, _ = cast(orig, d, dist * 1.002)
            if not ok:
                continue
            nm = ob.original.name if ob.original else ob.name
            if nm == SHELL and (loc - c).length < max(0.05, 0.01 * dist):
                seen.append(i)
        seen = np.array(sorted(set(seen) | set(shell_px.keys())), dtype=int)
        vis_faces[spec["key"]] = seen
        if len(seen):
            st["visible_faces"] = int(len(seen))
            st["visible_area_m2"] = round(float(f_area[seen].sum()), 1)
            st["visible_area_frac_of_asset"] = round(float(f_area[seen].sum() / f_area.sum()), 4)
            st["visible_uv2_area"] = round(float(f_uvarea[seen].sum()), 5)
            st["visible_uv2_frac_of_map"] = round(float(f_uvarea[seen].sum()), 5)
            st["visible_uv2_frac_of_asset_uv2"] = round(
                float(f_uvarea[seen].sum() / max(f_uvarea.sum(), 1e-9)), 4)
            to_cam = (orig - Vector(f_cent[seen].mean(axis=0)))
            dots = []
            for i in seen:
                v = (orig - Vector(f_cent[i])).normalized()
                dots.append(float(Vector(f_nrm[i]).dot(v)))
            dots = np.array(dots)
            st["normal_dot_to_camera"] = {
                "mean": round(float(dots.mean()), 4),
                "faces_facing_away_dot_lt_0": int((dots < 0).sum()),
                "area_frac_facing_away": round(
                    float(f_area[seen][dots < 0].sum() / max(f_area[seen].sum(), 1e-9)), 4),
            }
        else:
            st["visible_faces"] = 0
        rep["stations"][spec["key"]] = st
        log(f"{spec['key']}: shell {st['shell_pixel_pct']} % of pixels, "
            f"{st.get('visible_faces', 0)} faces visible")
        if st.get("normal_dot_to_camera"):
            log(f"{spec['key']}: normals toward camera mean dot {st['normal_dot_to_camera']['mean']}, "
                f"area facing away {st['normal_dot_to_camera']['area_frac_facing_away']}")

    # ---------------------------------------------------------------- what the bake wrote there
    exr = g3.OUT / "tex" / f"gate3_lm_{SHELL}.exr"
    img = g3.read_exr32(exr)          # (h, w, 3), bottom-up
    size = img.shape[0]
    lum = img.mean(axis=2)
    rep["map"] = {"exr": str(exr.relative_to(g3.ROOT)), "size": size,
                  "nonzero_pct_whole_map": round(100.0 * float((lum > 0).mean()), 3),
                  "max_whole_map": round(float(lum.max()), 5)}

    face_texels = [None] * n_p
    for i, p in enumerate(me.polygons):
        pu = uvs[list(p.loop_indices)]
        rows, cols = [], []
        for k in range(1, len(pu) - 1):
            t = tri_texels(pu[0], pu[k], pu[k + 1], size)
            if t is None:
                continue
            rows.append(t[0])
            cols.append(t[1])
        if rows:
            face_texels[i] = (np.concatenate(rows), np.concatenate(cols))

    def map_stats(face_idx):
        rows, cols = [], []
        for i in face_idx:
            t = face_texels[i]
            if t is None:
                continue
            rows.append(t[0])
            cols.append(t[1])
        if not rows:
            return None
        rr, cc = np.concatenate(rows), np.concatenate(cols)
        key = rr.astype(np.int64) * size + cc.astype(np.int64)
        key = np.unique(key)
        rr, cc = (key // size).astype(int), (key % size).astype(int)
        v = lum[rr, cc]
        return {"texels": int(v.size),
                "texels_pct_of_map": round(100.0 * v.size / (size * size), 3),
                "nonzero_pct": round(100.0 * float((v > 0).mean()), 3),
                "min": round(float(v.min()), 6), "max": round(float(v.max()), 5),
                "mean": round(float(v.mean()), 6),
                "mean_nonzero": round(float(v[v > 0].mean()) if (v > 0).any() else 0.0, 6),
                "p50": round(float(np.percentile(v, 50)), 6),
                "p99": round(float(np.percentile(v, 99)), 5)}

    allf = np.arange(n_p)
    rep["map_on_faces"] = {"all_faces": map_stats(allf)}
    union = np.array(sorted(set(vis_faces["cam04"].tolist()) | set(vis_faces["cam01"].tolist())), dtype=int)
    for k, idx in (("cam04_visible", vis_faces["cam04"]), ("cam01_visible", vis_faces["cam01"]),
                   ("visible_union", union)):
        if len(idx):
            rep["map_on_faces"][k] = map_stats(idx)
    hidden = np.array(sorted(set(range(n_p)) - set(union.tolist())), dtype=int)
    if len(hidden):
        rep["map_on_faces"]["not_visible"] = map_stats(hidden)
        rep["map_on_faces"]["not_visible"]["faces"] = int(len(hidden))
        rep["map_on_faces"]["not_visible"]["area_frac"] = round(
            float(f_area[hidden].sum() / f_area.sum()), 4)

    # ---------------------------------------------------------------- is the +normal hemisphere open?
    # A Cycles bake integrates the hemisphere around the SHADING normal only. If the visible faces'
    # normals point into the enclosed dome cavity, the bake is black no matter how good the UV2 is.
    rng = np.random.default_rng(7)
    probe_idx = union if len(union) else allf
    sel = probe_idx[rng.choice(len(probe_idx), size=min(HEMI_FACES, len(probe_idx)), replace=False)]
    hemi = {}
    for side, sgn in (("plus_normal", 1.0), ("minus_normal", -1.0)):
        esc, tot, dists = 0, 0, []
        for i in sel:
            n = Vector(f_nrm[i]) * sgn
            t = Vector((1, 0, 0)) if abs(n.x) < 0.9 else Vector((0, 1, 0))
            u = n.cross(t).normalized()
            v = n.cross(u)
            o = Vector(f_cent[i]) + n * 0.01
            for _ in range(HEMI_RAYS):
                r1, r2 = rng.random(), rng.random()
                r = math.sqrt(r1)
                th = 2 * math.pi * r2
                d = (u * (r * math.cos(th)) + v * (r * math.sin(th)) + n * math.sqrt(max(0.0, 1 - r1)))
                ok, hloc, _, _, _, _ = cast(o, d.normalized(), 3000.0)
                tot += 1
                if not ok:
                    esc += 1
                    dists.append(3000.0)
                else:
                    dists.append(float((hloc - o).length))
        dd = np.array(dists)
        hemi[side] = {"faces": int(len(sel)), "rays": tot,
                      "cosine_weighted_sky_visibility": round(esc / max(tot, 1), 4),
                      "hit_dist_m_p50": round(float(np.percentile(dd, 50)), 3),
                      "hit_dist_m_mean": round(float(dd.mean()), 3),
                      "frac_rays_hitting_within_2m": round(float((dd < 2.0).mean()), 4)}
        log(f"hemisphere {side}: sky {hemi[side]['cosine_weighted_sky_visibility']}, "
            f"median hit {hemi[side]['hit_dist_m_p50']} m, "
            f"<2 m {hemi[side]['frac_rays_hitting_within_2m']}")
    rep["hemisphere_test"] = hemi

    # the rib mesh for comparison: same test on the faces cam04 sees
    if rib is not None:
        rme = rib.data
        rmw = rib.matrix_world
        rn = rmw.to_3x3().inverted().transposed()
        ups = []
        ar = []
        for p in rme.polygons:
            nn = (rn @ p.normal).normalized()
            vs = [rmw @ rme.vertices[k].co for k in p.vertices]
            a = 0.0
            for k in range(1, len(vs) - 1):
                a += (vs[k] - vs[0]).cross(vs[k + 1] - vs[0]).length * 0.5
            ups.append(nn.z)
            ar.append(a)
        ups, ar = np.array(ups), np.array(ar)
        rep["rib_reference"] = {
            "polys": len(ups),
            "area_normal_down_lt_-0.5": round(float(ar[ups < -0.5].sum() / ar.sum()), 4),
            "area_normal_up_gt_0.5": round(float(ar[ups > 0.5].sum() / ar.sum()), 4),
        }

    np.savez_compressed(str(g3.OUT / "ceiling_probe_faces.npz"),
                        area=f_area, uvarea=f_uvarea, cent=f_cent, nrm=f_nrm,
                        vis_cam04=vis_faces["cam04"], vis_cam01=vis_faces["cam01"], uvs=uvs)
    rep["elapsed_s"] = round(time.time() - t0, 1)
    OUT_JSON.write_text(json.dumps(rep, indent=1))
    log(f"wrote {OUT_JSON} in {rep['elapsed_s']} s")
    print(json.dumps(rep, indent=1), flush=True)


main()
