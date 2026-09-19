"""Phase 8b step 1: rebuild the impostor nursery from MAIN master_delivery.blend and write the band job set.

    scripts/blender_run.sh 1800 -- --background --python-exit-code 1 --python export/band_set.py

This is export/gate3_set.py section 7 ("the impostor blend") re-run verbatim on the CURRENT
master_delivery.blend (rebuilt 2026-09-19 13:01 with the 8a environment), so the band frames come off the
same nursery, the same 16 `_LOD1` prototypes, the same camera-invisible lawn and the same final Cycles rig
as the shipped octahedral atlas. Every prototype's bounding box is then ASSERTED against the shipped
manifest's `impostors.prototypes` - radius, centre, base and height - because the band atlas replaces only
the albedo lookup: the viewer keeps the octahedral quad geometry, so any drift here would move the trees.

Writes: export/out/gate3/band_imp.blend, export/out/gate3/band/band_set.json.
"""
import json
import os
import sys
import time

import bpy
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gate0_common as g0      # noqa: E402
import gate3_common as g3      # noqa: E402
import band_common as bc       # noqa: E402

t_all = time.time()
TOL = 5e-4                     # the manifest rounds to 4 decimals
rep = dict(generator="export/band_set.py", started=time.strftime("%Y-%m-%dT%H:%M:%S"),
           src=str(g3.SRC_BLEND), src_mtime=time.strftime("%Y-%m-%dT%H:%M:%S",
                                                          time.localtime(g3.SRC_BLEND.stat().st_mtime)),
           src_bytes=g3.SRC_BLEND.stat().st_size)

imp = bc.manifest_impostors()
protos = sorted(imp["prototypes"])
assert len(protos) == 16, f"expected 16 prototypes, manifest has {len(protos)}"

step = g0.Step("band_set:open_master_delivery")
bpy.ops.wm.open_mainfile(filepath=str(g3.SRC_BLEND), load_ui=False)
sc = bpy.context.scene
step.done(objects=len(bpy.data.objects))

step = g0.Step("band_set:nursery")
for o in bpy.data.objects:
    o.hide_viewport = False
bpy.context.view_layer.update()
missing = [p for p in protos if bpy.data.objects.get(p) is None]
assert not missing, f"prototypes missing from master_delivery: {missing}"
keep = set(protos)
for o in list(bpy.data.objects):
    if o.type == "MESH" and o.name not in keep:
        bpy.data.objects.remove(o, do_unlink=True)
    elif o.type == "MESH":
        o.hide_render = o.hide_viewport = o.hide_select = False
# gate3_set.py: camera-invisible lawn so the crowns keep the ground bounce they have in Phase 5
lawn_mat = bpy.data.materials.get("MAT_lawn")
bpy.ops.mesh.primitive_plane_add(size=400.0, location=(-510.0, -570.0, 0.0))
lawn = bpy.context.active_object
lawn.name = "GATE3_imp_lawn"
if lawn_mat:
    lawn.data.materials.append(lawn_mat)
lawn.visible_camera = False
cam_data = bpy.data.cameras.new("GATE3_imp_cam")
cam = bpy.data.objects.new("GATE3_imp_cam", cam_data)
sc.collection.objects.link(cam)
sc.camera = cam
lights = g0.apply_final_cycles_checked(sc)
c = sc.cycles
c.use_adaptive_sampling = False
c.time_limit = 0.0
c.use_denoising = True
c.denoiser = "OPENIMAGEDENOISE"
sc.compositing_node_group = None
sc.render.film_transparent = True
for _ in range(3):
    bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)
rep["rig"] = dict(lights=len(lights), engine=sc.render.engine, samples=c.samples,
                  adaptive=c.use_adaptive_sampling, denoiser=c.denoiser,
                  world=sc.world.name if sc.world else None,
                  compositor=sc.compositing_node_group, lawn_mat=bool(lawn_mat))
step.done(objects=len(bpy.data.objects))

step = g0.Step("band_set:measure")
info, drift = {}, {}
dg = bpy.context.evaluated_depsgraph_get()
for p in protos:
    ob = bpy.data.objects[p]
    ev = ob.evaluated_get(dg)
    me = ev.to_mesh()
    co = np.array([list(ob.matrix_world @ v.co) for v in me.vertices], dtype=np.float64)
    ev.to_mesh_clear()
    lo, hi = co.min(axis=0), co.max(axis=0)
    centre = (lo + hi) * 0.5
    radius = max(float(np.linalg.norm(hi - lo) * 0.5), 1e-3)
    m = imp["prototypes"][p]
    got = dict(bbox_min=[round(float(v), 4) for v in lo], bbox_max=[round(float(v), 4) for v in hi],
               centre=[round(float(v), 4) for v in centre],
               radius_m=round(radius, 4), base_z_m=round(float(lo[2]), 4),
               centre_z_m=round(float(centre[2]), 4),
               height_above_base_m=round(float(hi[2] - max(lo[2], 0.0)), 4),
               depth_range_m=round(2.0 * radius, 4),
               bbox_m=[round(float(hi[i] - lo[i]), 4) for i in range(3)],
               range=m["range"], verts=int(co.shape[0]))
    bad = {k: [got[k], m[k]] for k in ("radius_m", "base_z_m", "centre_z_m", "height_above_base_m",
                                       "depth_range_m")
           if abs(got[k] - m[k]) > TOL}
    if any(abs(got["bbox_m"][i] - m["bbox_m"][i]) > TOL for i in range(3)):
        bad["bbox_m"] = [got["bbox_m"], m["bbox_m"]]
    if bad:
        drift[p] = bad
    info[p] = got
rep["prototypes"] = info
rep["manifest_drift"] = drift
assert not drift, ("the current master_delivery's prototypes no longer match the shipped "
                   f"impostors.prototypes; the band atlas would not sit on the octahedral quad: {drift}")
step.done(prototypes=len(info))

step = g0.Step("band_set:save")
g0.save_copy(bc.BAND_BLEND)
step.done(bc.BAND_BLEND, objects=len(bpy.data.objects))

rep["layout"] = dict(grid_az=bc.GRID_AZ, grid_el=bc.GRID_EL, atlas_px=[bc.ATLAS_W, bc.ATLAS_H],
                     frame_px=bc.FRAME_PX, gutter_px=bc.GUTTER_PX, inner_px=bc.INNER_PX,
                     elevations_deg=list(bc.ELEV_DEG), samples=bc.SAMPLES)
rep["jobs"] = protos
rep["wall_s"] = round(time.time() - t_all, 1)
bc.BAND_OUT.mkdir(parents=True, exist_ok=True)
(bc.BAND_OUT / "band_set.json").write_text(json.dumps(rep, indent=1) + "\n")
print(f"[band] set done in {rep['wall_s']} s: {len(protos)} prototypes, drift={drift or 'none'}")
