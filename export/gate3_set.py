"""Gate 3 step 1: build the two bake blends and the job list. No GPU, nothing saved over master*.blend.

    scripts/blender_run.sh 2400 -- --background --python export/gate3_set.py

What it does, and why each step is here rather than assumed:

1. `gate2_bake.blend` is the base: it already carries the whole Gate 1 export set (2 600 objects, UV1 + UV2),
   the Phase 5 materials relinked per polygon, the full light rig, the world and the QA cameras.
2. The 33 EXPHI hi-poly ORN twins are asserted `hide_render` - a coincident hi twin self-shadows a bake
   (Gate 0 review finding 2: the 12-triangle ground went 461 s -> 299 s once its twin was hidden).
3. ORN instances carry the grey `MAT_EXP_ORN__*` placeholder in the Gate 2 blend, because Gate 2 baked ORN in a
   separate file. The lightmap pass is colour-off, so albedo only reaches the map through the BOUNCE - and a grey
   bounce off 436 ochre ornaments is wrong. `MAT_ornament_concrete` (the one source material all 33 prototypes
   use) is relinked onto them.
4. Occluders the export set does not contain but Phase 5 does: the lagoon water and the bay (the export ships a
   viewer plane instead) and the 127 FAR trees (the export ships billboard quads). A lightmap baked against a
   billboard quad has no tree shadow where Phase 5 has one, and tree shadow is most of the per-instance variation
   QA-12-4 asks for. The 127 `ENV_treeboard_*` quads are hidden from the rays in exchange.
5. Gate 1's UV2 on the merged masses is margin-dominated (see export/README.md "Re-laid UV2"): the south colonnade
   packs 0.0095 of its 2K map. Those assets get a new UV2 here, and the loop UVs are written to
   `lightmap_uv2.npz` as the hand-off to the export engineer.
6. `gate3_imp.blend` holds the 16 far-tree prototypes ALONE (always the LOD1 mesh, never the LOD2 blob the export
   picked for 46 of the 127 far trees: the impostor's cost is its atlas, not its triangles) plus the rig, the
   world and a camera-invisible lawn plane so the crowns get the ground bounce Phase 5 gives them.
"""
import bpy
import os
import sys
import json
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gate0_common as g0      # noqa: E402
import gate2_common as g2      # noqa: E402
import gate3_common as g3      # noqa: E402

t_all = time.time()
g3.ensure_dirs()
rep = {"started": time.strftime("%Y-%m-%dT%H:%M:%S")}
eset = json.loads((g3.GATE1_OUT / "export_set.json").read_text())
assets = eset["assets"]
man2 = json.loads((g3.GATE2_OUT / "manifest.json").read_text())

# ---------------------------------------------------------------- 1. the base blend
step = g0.Step("gate3_set:open_base")
bpy.ops.wm.open_mainfile(filepath=str(g3.BASE_BLEND), load_ui=False)
sc = bpy.context.scene
step.done(g3.BASE_BLEND, objects=len(bpy.data.objects))

# --- 2. the hi-poly twins must not be ray-visible
hi = [o for o in bpy.data.objects if o.name.startswith("EXPHI")]
bad = [o.name for o in hi if not o.hide_render]
if bad:
    for o in hi:
        o.hide_render = True
rep["exphi"] = dict(n=len(hi), were_visible=bad)

# --- 3. ORN materials
orn_src = sorted({m for j in json.loads((g3.GATE2_OUT / "bake_jobs.json").read_text())["jobs"]
                  if j["cls"] == "orn" for m in j["src_materials"]})
got, missing = g2.append_materials(orn_src)
assert not missing, f"ORN source materials missing from master_delivery: {missing}"
orn_mat = got[orn_src[0]]
n_orn_me = 0
for me in bpy.data.meshes:
    if me.name.startswith("EXPM_ORN_"):
        me.materials.clear()
        me.materials.append(orn_mat)
        n_orn_me += 1
rep["orn_relink"] = dict(material=orn_mat.name, meshes=n_orn_me)
print(f"[gate3] ORN relink: {n_orn_me} meshes -> {orn_mat.name}")

# --- 4. occluders from master_delivery
far = eset["tree_far_list"]
occ_names = sorted({t["source_tree"] for t in far}) + ["ENV_lagoon_water", "ENV_backdrop_bay"]
before_mats = {m.name for m in bpy.data.materials}
with bpy.data.libraries.load(str(g3.SRC_BLEND), link=False) as (dfrom, dto):
    missing_occ = [n for n in occ_names if n not in dfrom.objects]
    dto.objects = [n for n in occ_names if n in dfrom.objects]
occ_coll = bpy.data.collections.new("GATE3_OCCLUDER")
sc.collection.children.link(occ_coll)
n_occ = 0
for ob in dto.objects:
    if ob is None:
        continue
    occ_coll.objects.link(ob)
    ob.hide_render = ob.hide_viewport = False
    n_occ += 1
# de-duplicate the materials the append brought in as `<name>.001`
dupes = 0
for m in list(bpy.data.materials):
    if m.name in before_mats or "." not in m.name:
        continue
    base = m.name.rsplit(".", 1)[0]
    orig = bpy.data.materials.get(base)
    if orig is not None and orig is not m:
        m.user_remap(orig)
        bpy.data.materials.remove(m)
        dupes += 1
boards = [o for o in bpy.data.objects if o.name.startswith("ENV_treeboard_")]
for o in boards:
    o.hide_render = True
rep["occluders"] = dict(appended=n_occ, missing=missing_occ, material_dupes_merged=dupes,
                        treeboards_hidden=len(boards))
print(f"[gate3] occluders: +{n_occ} objects ({len(far)} far trees + water), {len(boards)} billboards hidden, "
      f"{dupes} duplicate materials merged")

# ---------------------------------------------------------------- 5. UV2 re-lay
from mathutils import Vector  # noqa: E402


def uv_area_and_loops(me, layer=g3.UV2):
    lay = me.uv_layers.get(layer)
    if lay is None:
        return None, None
    uv = np.empty(len(me.loops) * 2, dtype=np.float32)
    try:
        lay.uv.foreach_get("vector", uv)
    except Exception:
        lay.data.foreach_get("uv", uv)
    uv = uv.reshape(-1, 2)
    a = 0.0
    for p in me.polygons:
        pts = uv[list(p.loop_indices)]
        for k in range(1, len(pts) - 1):
            e1, e2 = pts[k] - pts[0], pts[k + 1] - pts[0]
            a += abs(float(e1[0] * e2[1] - e1[1] * e2[0])) * 0.5
    return a, uv


def world_area(ob):
    me, mw = ob.data, ob.matrix_world
    a = 0.0
    for p in me.polygons:
        vs = [mw @ me.vertices[i].co for i in p.vertices]
        for k in range(1, len(vs) - 1):
            a += (vs[k] - vs[0]).cross(vs[k + 1] - vs[0]).length * 0.5
    return a


own_assets = [(n, r) for n, r in assets.items() if (r.get("lightmap") or {}).get("mode") == "asset"]
own_rows, relaid_uv = [], {}
for name, r in sorted(own_assets):
    ob = bpy.data.objects.get(name)
    assert ob is not None, f"own-map asset {name} not in the bake blend"
    me = ob.data
    ob.hide_render = ob.hide_viewport = ob.hide_select = False
    area = world_area(ob)
    cov0, _ = uv_area_and_loops(me)
    size = g3.size_for_own(area)
    relaid, cov1, dt = False, cov0, 0.0
    if cov0 is not None and cov0 < g3.UV2_RELAY_THRESHOLD:
        t0 = time.time()
        # keep the frozen Gate 1 layout as its own layer: the glb still carries it, so a map baked against it
        # is the only thing the viewer can use before the re-export, and the diagnostic jobs need it.
        if me.uv_layers.get(g3.UV2_GATE1) is None:
            src = me.uv_layers[g3.UV2]
            keep = me.uv_layers.new(name=g3.UV2_GATE1)
            buf = np.empty(len(me.loops) * 2, dtype=np.float32)
            try:
                src.uv.foreach_get("vector", buf)
                keep.uv.foreach_set("vector", buf)
            except Exception:
                src.data.foreach_get("uv", buf)
                keep.data.foreach_set("uv", buf)
        me.uv_layers.active = me.uv_layers[g3.UV2]
        me.uv_layers[g3.UV2].active_render = True
        for o in bpy.context.selected_objects:
            o.select_set(False)
        ob.select_set(True)
        bpy.context.view_layer.objects.active = ob
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.uv.smart_project(angle_limit=g3.UV2_RELAY_ANGLE, island_margin=g3.UV2_RELAY_MARGIN,
                                 correct_aspect=True, scale_to_bounds=False)
        bpy.ops.object.mode_set(mode="OBJECT")
        dt = time.time() - t0
        cov1, uv = uv_area_and_loops(me)
        relaid = True
        relaid_uv[me.name] = uv.astype(np.float32)
    cm0 = 100.0 * (area / max(cov0 * size * size, 1e-9)) ** 0.5 if cov0 else None
    cm1 = 100.0 * (area / max(cov1 * size * size, 1e-9)) ** 0.5 if cov1 else None
    own_rows.append(dict(object=name, mesh=me.name, cls=r["cls"], tris=r["tris"], size=size,
                         area_m2=round(area, 1), coverage_gate1=round(cov0, 5), coverage=round(cov1, 5),
                         cm_per_texel_gate1=round(cm0, 2), cm_per_texel=round(cm1, 2),
                         uv2_relaid=relaid, relay_s=round(dt, 1)))
    print(f"[gate3] own {name}: area {area:.0f} m2 size {size} cov {cov0:.5f} -> {cov1:.5f} "
          f"({cm0:.2f} -> {cm1:.2f} cm/texel) relaid={relaid} {dt:.1f}s")
if relaid_uv:
    np.savez_compressed(str(g3.OUT / "lightmap_uv2.npz"), **relaid_uv)
rep["own_maps"] = own_rows
rep["uv2_relaid"] = sorted(relaid_uv)

# ---------------------------------------------------------------- 6. the final Cycles rig, bake-safe
lights = g0.apply_final_cycles_checked(sc)
c = sc.cycles
c.use_adaptive_sampling = False       # every bake in this pipeline is a fixed sample count
c.time_limit = 0.0                    # apply_final_cycles sets a wall-clock limit for the hero render
c.use_denoising = True
c.denoiser = "OPENIMAGEDENOISE"
sc.compositing_node_group = None      # 5.2: the only property that detaches the compositor
sc.render.film_transparent = False
rep["rig"] = dict(lights=len(lights), engine=sc.render.engine, samples=c.samples,
                  adaptive=c.use_adaptive_sampling, time_limit=c.time_limit,
                  diffuse_bounces=c.diffuse_bounces, max_bounces=c.max_bounces,
                  compositor=sc.compositing_node_group)

step = g0.Step("gate3_set:save_bake_blend")
g0.save_copy(g3.BAKE_BLEND)
step.done(g3.BAKE_BLEND, objects=len(bpy.data.objects))

# ---------------------------------------------------------------- 7. the impostor blend
# always the LOD1 prototype: 46 of the 127 far trees were exported against an LOD2 blob (1 200-1 800 tris),
# and an impostor costs its atlas, not its triangles.
proto_map = {}
for t in far:
    p = t["prototype"]
    proto_map[p] = p[:-5] + "_LOD1" if p.endswith("_LOD2") else p
protos = sorted(set(proto_map.values()))
rep["impostor_prototype_map"] = proto_map

step = g0.Step("gate3_set:impostor_blend")
bpy.ops.wm.open_mainfile(filepath=str(g3.SRC_BLEND), load_ui=False)
sc = bpy.context.scene
keep = set(protos)
for o in bpy.data.objects:
    o.hide_viewport = False
bpy.context.view_layer.update()
missing_p = [p for p in protos if bpy.data.objects.get(p) is None]
assert not missing_p, f"impostor prototypes missing: {missing_p}"
for o in list(bpy.data.objects):
    if o.type == "MESH" and o.name not in keep:
        bpy.data.objects.remove(o, do_unlink=True)
    elif o.type == "MESH":
        o.hide_render = o.hide_viewport = o.hide_select = False
# camera-invisible lawn so the crowns keep the ground bounce they have in Phase 5
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
proto_info = {}
dg = bpy.context.evaluated_depsgraph_get()
for p in protos:
    ob = bpy.data.objects[p]
    ev = ob.evaluated_get(dg)
    me = ev.to_mesh()
    co = np.array([list(ob.matrix_world @ v.co) for v in me.vertices], dtype=np.float64)
    tris = sum(len(pl.vertices) - 2 for pl in me.polygons)
    ev.to_mesh_clear()
    lo, hiv = co.min(axis=0), co.max(axis=0)
    proto_info[p] = dict(tris=int(tris), verts=int(co.shape[0]),
                         bbox_min=[round(float(v), 4) for v in lo],
                         bbox_max=[round(float(v), 4) for v in hiv],
                         dims_m=[round(float(v), 4) for v in (hiv - lo)],
                         centre=[round(float(v), 4) for v in (lo + hiv) * 0.5])
rep["impostor_prototypes"] = proto_info
g0.save_copy(g3.IMP_BLEND)
step.done(g3.IMP_BLEND, objects=len(bpy.data.objects), prototypes=len(protos))

# ---------------------------------------------------------------- 8. the job list
jobs = []
jobs.append(dict(id="sky_diffuse", kind="sky", blend="gate3_bake.blend", est_s=40))
jobs.append(dict(id="probe_hero", kind="probe", blend="gate3_bake.blend", est_s=500))

for row in sorted(own_rows, key=lambda r: -r["area_m2"]):
    jobs.append(dict(id="lm_" + row["object"], kind="own", blend="gate3_bake.blend",
                     object=row["object"], mesh=row["mesh"], size=row["size"],
                     uv2=g3.UV2, uv2_relaid=row["uv2_relaid"], est_s=350))

slots = man2["orn_slots"]
for pool in ("orn", "arch_inst"):
    by_atlas = {}
    for rec in slots[pool]:
        by_atlas.setdefault(rec["atlas"], []).append(rec)
    for atlas in sorted(by_atlas):
        items = sorted(by_atlas[atlas], key=lambda r: r["slot"])
        for b0 in range(0, len(items), g3.SLOT_BATCH):
            batch = items[b0:b0 + g3.SLOT_BATCH]
            jobs.append(dict(id=f"slot_{pool}_{atlas}_{b0 // g3.SLOT_BATCH:02d}", kind="slot",
                             blend="gate3_bake.blend", pool=pool, atlas=atlas,
                             items=[dict(object=r["object"], slot=r["slot"]) for r in batch],
                             est_s=int(len(batch) * 6 + 60)))

near = [t["name"] for t in eset["tree_near_list"]]
for i in range(0, len(near), 10):
    jobs.append(dict(id=f"vc_{i // 10:02d}", kind="vertex", blend="gate3_bake.blend",
                     objects=near[i:i + 10], est_s=300))

for p in protos:
    jobs.append(dict(id="imp_" + p, kind="impostor", blend="gate3_imp.blend", prototype=p,
                     bbox_min=proto_info[p]["bbox_min"], bbox_max=proto_info[p]["bbox_max"], est_s=300))

# diagnostic: two of the re-laid assets also baked on the frozen Gate 1 UV2, so the viewer has something to
# show before the re-export and the report can say what that layout is actually worth.
for row in own_rows:
    if row["uv2_relaid"] and row["object"] in ("ARCH_colonnade_south_concrete_colonnade_merged",
                                               "ARCH_rotunda_concrete_ochre_merged"):
        jobs.append(dict(id="lmg1_" + row["object"], kind="own_gate1uv2", blend="gate3_bake.blend",
                         object=row["object"], mesh=row["mesh"], size=row["size"],
                         uv2=g3.UV2_GATE1, est_s=350))

(g3.jobs_path()).write_text(json.dumps(dict(generator="export/gate3_set.py", jobs=jobs), indent=1) + "\n")
rep["jobs"] = dict(total=len(jobs), est_s=sum(j["est_s"] for j in jobs),
                   by_kind={k: sum(1 for j in jobs if j["kind"] == k) for k in
                            sorted({j["kind"] for j in jobs})})
rep["wall_s"] = round(time.time() - t_all, 1)
(g3.OUT / "gate3_set.json").write_text(json.dumps(rep, indent=1) + "\n")
print(f"[gate3] set done in {rep['wall_s']} s: {rep['jobs']}")
