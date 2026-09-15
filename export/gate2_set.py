"""Gate 2 step 1 (no GPU): build the two bake blends and the job manifest.

    scripts/blender_run.sh 1800 -- --background --python export/gate2_set.py

Three read-only opens, two saved copies:

  1. master_delivery.blend (the REGENERATED one, MAT r10) - collect, for every ENV ground / backdrop source object,
     the world centre and material of every polygon, because the Gate 1 merge flattened all of them onto one grey
     slot (`poly_material_index` is {0: n} on every ENV mesh) and the gravel paths, soil and asphalt would
     otherwise bake as lawn. Written to out/gate2/env_poly_src.npz.
  2. gate1_set.blend  -> out/gate2/gate2_bake.blend      (ARCH + ENV ground + ENV backdrop)
  3. gate1_bake.blend -> out/gate2/gate2_orn_bake.blend  (the 33 ORN lo/hi pairs)

In both bake blends every Gate 1 neutral grey `MAT_EXP_*` is replaced by the real Phase 5 material, appended by
name from master_delivery.blend. The appended `MAT_dome_membrane` is asserted to carry the MAT r10 28-panel ridge
input, which is the proof that the materials came from the regenerated file and not from the Gate 1 copy.

Why a representative placement and not the origin: `PFA_concrete` reads **Geometry > Position** (world space) for
its grey drift (`Grey Below Z` / `Grey Above Z`), `PFA_algae` puts the waterline band at world z = -1.3, and
`PFA_instance` reads **Object Info > Random / Location**. A shared mesh can only carry one instance's answer, so
each job bakes through the placement closest to a QA station, and the ORN lo/hi pair is moved onto that
placement's matrix (they stay coincident, so the cage is unchanged).

Nothing here bakes and nothing writes a master*.blend.
"""
import bpy
import json
import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gate0_common as g0  # noqa: E402
import gate1_common as g1  # noqa: E402
import gate2_common as g2  # noqa: E402

g2.ensure_dirs()
step_all = g0.Step("gate2_set")
eset = g2.read_export_set()
man1 = json.loads((g2.GATE1_OUT / "manifest.json").read_text())
probe = json.loads((g2.OUT / "probe.json").read_text())
rep = {"source_materials": str(g2.SRC_BLEND), "source_geometry": str(g2.SET_BLEND)}

STATIONS = [v["location"] for k, v in man1["stations"].items() if k.startswith("CAM_qa_")]
assert len(STATIONS) == 6, STATIONS

# ---------------------------------------------------------------- the groups, by class
group_meshes, group_src = {}, {}
for mname, mrec in eset["meshes"].items():
    grp = mrec.get("material")
    if not grp or g2.NO_BAKE_MATERIALS.match(grp):
        continue
    group_meshes.setdefault(grp, []).append(mname)
    group_src[grp] = mrec.get("src_material")


def cls_of(grp):
    if grp.startswith("MAT_EXP_ARCH_"):
        return g2.CLS_ARCH
    if grp.startswith("MAT_EXP_ENVBD__"):
        return g2.CLS_BACKDROP
    if grp.startswith("MAT_EXP_ENV__"):
        return g2.CLS_GROUND
    if grp.startswith("MAT_EXP_ORN__"):
        return g2.CLS_ORN
    raise SystemExit(f"[gate2] unclassified bake group {grp}")


def job_id(grp):
    return re.sub(r"[^A-Za-z0-9_]", "_", grp.replace("MAT_EXP_", "").replace("MAT_", ""))


GROUPS = {g: cls_of(g) for g in group_meshes}
rep["group_counts"] = {c: sum(1 for v in GROUPS.values() if v == c) for c in
                       (g2.CLS_ARCH, g2.CLS_GROUND, g2.CLS_BACKDROP, g2.CLS_ORN)}
print("[gate2] groups:", rep["group_counts"])

# which master_delivery objects feed each ENV group (the Gate 1 merge rule, inverted)
ENV_SRC_OBJ = {}
for grp, cls in GROUPS.items():
    if cls == g2.CLS_GROUND:
        tail = grp[len("MAT_EXP_ENV__"):]
        ENV_SRC_OBJ[grp] = ("riprap_prefix", "ENV_riprap") if tail == "riprap" else ("object", tail)
    elif cls == g2.CLS_BACKDROP:
        ENV_SRC_OBJ[grp] = ("slot0_material", group_src[grp])

# ---------------------------------------------------------------- 1. master_delivery.blend: ENV polygon sources
step = g0.Step("gate2_set:env_poly_src")
bpy.ops.wm.open_mainfile(filepath=str(g2.SRC_BLEND), load_ui=False)
import numpy as np  # noqa: E402

BACKDROP_PREFIXES = ("ENV_backdrop", "ENV_lamp", "ENV_bird")
env_src = {}            # group -> (centres float32 [n,3], material ids int32 [n], names [str])
for grp, (rule, key) in ENV_SRC_OBJ.items():
    objs = []
    for ob in bpy.data.objects:
        if ob.type != "MESH" or not ob.data.polygons:
            continue
        if rule == "object" and ob.name == key:
            objs.append(ob)
        elif rule == "riprap_prefix" and ob.name.startswith(key):
            objs.append(ob)
        elif rule == "slot0_material" and ob.data.materials and ob.data.materials[0] \
                and ob.data.materials[0].name == key:
            objs.append(ob)
    cents, mids, names = [], [], []
    name_ix = {}
    for ob in objs:
        me = ob.data
        slots = [m.name if m else None for m in me.materials] or [None]
        mw = ob.matrix_world
        for p in me.polygons:
            c = mw @ p.center
            cents.append((c.x, c.y, c.z))
            nm = slots[min(p.material_index, len(slots) - 1)]
            if nm not in name_ix:
                name_ix[nm] = len(names)
                names.append(nm)
            mids.append(name_ix[nm])
    env_src[grp] = (np.array(cents, dtype=np.float32), np.array(mids, dtype=np.int32), names)
    print(f"[gate2] env src {grp}: {len(objs)} objects, {len(cents)} polys, materials {names}")

np.savez_compressed(str(g2.OUT / "env_poly_src.npz"),
                    **{f"{k}__c": v[0] for k, v in env_src.items()},
                    **{f"{k}__m": v[1] for k, v in env_src.items()})
(g2.OUT / "env_poly_src_names.json").write_text(json.dumps({k: v[2] for k, v in env_src.items()}, indent=1) + "\n")
rep["env_poly_src"] = {k: dict(polys=int(len(v[0])), materials=v[2]) for k, v in env_src.items()}
step.done(g2.OUT / "env_poly_src.npz")

# every material the bake needs
need = set()
for grp, cls in GROUPS.items():
    if cls in (g2.CLS_ARCH,):
        need.add(group_src[grp])
    elif cls in (g2.CLS_GROUND, g2.CLS_BACKDROP):
        need.update(n for n in env_src[grp][2] if n)
    elif cls == g2.CLS_ORN:
        need.update(probe["orn_proto_materials"][grp]["materials"])
need = sorted(n for n in need if n)
rep["materials_needed"] = need
print(f"[gate2] materials needed: {len(need)}")


def relink_and_check():
    """Append every needed material from the regenerated master_delivery and prove it on MAT_dome_membrane."""
    got, missing = g2.append_materials(need)
    if missing:
        raise SystemExit(f"[gate2] materials missing from {g2.SRC_BLEND}: {missing}")
    dm = got.get("MAT_dome_membrane")
    proof = None
    if dm is not None:
        grp_nodes = [n for n in dm.node_tree.nodes if n.bl_idname == "ShaderNodeGroup" and n.node_tree]
        panels = None
        for n in grp_nodes:
            s = n.inputs.get("Panels")
            if s is not None:
                panels = float(s.default_value)
        proof = dict(node_group=grp_nodes[0].node_tree.name if grp_nodes else None, panels=panels,
                     n_nodes=len(dm.node_tree.nodes))
        if panels is None or abs(panels - 28.0) > 1e-6:
            raise SystemExit(f"[gate2] MAT_dome_membrane relink FAILED: Panels={panels} (expected 28)")
    return got, proof


def set_material(me, names):
    """Replace the mesh's slot list with the real materials, keeping every polygon's material_index valid."""
    me.materials.clear()
    for n in names:
        me.materials.append(bpy.data.materials[n])


def bbox_world(ob):
    from mathutils import Vector
    pts = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
    return sum(pts, Vector((0, 0, 0))) / 8.0


def nearest_station(p):
    from mathutils import Vector
    return min((Vector(s) - p).length for s in STATIONS)


# ---------------------------------------------------------------- 2. gate1_set.blend -> gate2_bake.blend
step = g0.Step("gate2_set:arch_env")
bpy.ops.wm.open_mainfile(filepath=str(g2.SET_BLEND), load_ui=False)
got, dome_proof = relink_and_check()
rep["dome_membrane_proof"] = dome_proof
print(f"[gate2] relinked {len(got)} materials; MAT_dome_membrane {dome_proof}")

# objects per mesh
obs_by_mesh = {}
for ob in bpy.data.objects:
    if ob.type == "MESH" and ob.data is not None:
        obs_by_mesh.setdefault(ob.data.name, []).append(ob)

from mathutils import Vector  # noqa: E402
from mathutils.kdtree import KDTree  # noqa: E402

jobs = []
backdrop_uv = {}
for grp in sorted(g for g, c in GROUPS.items() if c != g2.CLS_ORN):
    cls = GROUPS[grp]
    meshes = sorted(group_meshes[grp])
    slots_used = set()
    if cls == g2.CLS_ARCH:
        for mn in meshes:
            set_material(bpy.data.meshes[mn], [group_src[grp]])
        slots_used.add(group_src[grp])
    else:
        cents, mids, names = env_src[grp]
        if len(names) == 1:
            for mn in meshes:
                set_material(bpy.data.meshes[mn], [names[0]])
            slots_used.add(names[0])
        else:
            kd = KDTree(len(cents))
            for i, c in enumerate(cents):
                kd.insert(Vector((float(c[0]), float(c[1]), float(c[2]))), i)
            kd.balance()
            for mn in meshes:
                me = bpy.data.meshes[mn]
                ob0 = obs_by_mesh[mn][0]
                mw = ob0.matrix_world
                set_material(me, names)
                hist = {}
                for p in me.polygons:
                    _, i, _ = kd.find(mw @ p.center)
                    mi = int(mids[i])
                    p.material_index = mi
                    hist[names[mi]] = hist.get(names[mi], 0) + 1
                print(f"[gate2] {mn}: per-polygon materials restored {hist}")
                rep.setdefault("env_material_restore", {})[mn] = hist
            slots_used.update(names)

    # backdrop: the Gate 1 set has no UV1 at all
    uv1_in_glb = True
    if cls == g2.CLS_BACKDROP:
        objs = [obs_by_mesh[mn][0] for mn in meshes]
        for ob in objs:
            ob.hide_viewport = ob.hide_select = False
        if any(bpy.data.meshes[mn].uv_layers.get(g2.UV1) is None for mn in meshes):
            g2.smart_uv1(objs)
            uv1_in_glb = False
        for mn in meshes:
            me = bpy.data.meshes[mn]
            uvs = np.empty(len(me.loops) * 2, dtype=np.float32)
            lay = me.uv_layers[g2.UV1]
            if hasattr(lay, "uv"):
                lay.uv.foreach_get("vector", uvs)
            else:
                lay.data.foreach_get("uv", uvs)
            backdrop_uv[mn] = uvs.reshape(-1, 2)

    # the representative placement per mesh: closest to any QA station
    reps = []
    for mn in meshes:
        best, bd = None, 1e18
        for ob in obs_by_mesh[mn]:
            d = nearest_station(bbox_world(ob))
            if d < bd:
                best, bd = ob, d
        best.hide_viewport = best.hide_select = best.hide_render = False
        reps.append(dict(mesh=mn, object=best.name, station_d_m=round(bd, 2),
                         placements=len(obs_by_mesh[mn])))
    size = g2.size_for(cls)
    jobs.append(dict(id=job_id(grp), group=grp, cls=cls, size=size,
                     sizes=dict(albedo=size, roughness=min(size, 1024) if cls != g2.CLS_BACKDROP else size,
                                normal=size),
                     src_materials=sorted(slots_used), meshes=meshes, reps=reps,
                     uv1_in_glb=uv1_in_glb, blend="gate2_bake.blend",
                     metallic=sorted(m for m in slots_used
                                     if probe["materials"].get(m, {}).get("principled", {})
                                     and probe["materials"][m]["principled"].get("Metallic") not in (0.0, None)),
                     tris=sum(eset["meshes"][m]["tris"] for m in meshes),
                     area_m2=probe["groups"][grp]["area_m2"],
                     station_min_d_m=probe["groups"][grp]["station_min_d"],
                     hero_in_frame=probe["groups"][grp]["hero_in_frame"],
                     hero_min_d_m=probe["groups"][grp]["hero_min_d_in"]))

if backdrop_uv:
    np.savez_compressed(str(g2.OUT / "backdrop_uv1.npz"), **backdrop_uv)
    rep["backdrop_uv1"] = {k: int(v.shape[0]) for k, v in backdrop_uv.items()}

g0.save_copy(g2.OUT / "gate2_bake.blend")
step.done(g2.OUT / "gate2_bake.blend", jobs=len(jobs))

# ---------------------------------------------------------------- 3. gate1_bake.blend -> gate2_orn_bake.blend
step = g0.Step("gate2_set:orn")
# the representative INST matrix per prototype, read from the set before it is closed
orn_rep = {}
for grp, cls in GROUPS.items():
    if cls != g2.CLS_ORN:
        continue
    mn = group_meshes[grp][0]
    best, bd = None, 1e18
    for ob in obs_by_mesh.get(mn, []):
        d = nearest_station(bbox_world(ob))
        if d < bd:
            best, bd = ob, d
    orn_rep[grp] = dict(mesh=mn, object=best.name if best else None, station_d_m=round(bd, 2),
                        matrix=[list(r) for r in best.matrix_world] if best else None,
                        placements=len(obs_by_mesh.get(mn, [])))

bpy.ops.wm.open_mainfile(filepath=str(g2.BAKE_BLEND), load_ui=False)
got, dome_proof2 = relink_and_check()
jobs1 = {j["id"]: j for j in json.loads((g2.GATE1_OUT / "bake_jobs.json").read_text())["jobs"]}
orn_missing = []
for grp, cls in sorted(GROUPS.items()):
    if cls != g2.CLS_ORN:
        continue
    proto_mesh = grp[len("MAT_EXP_ORN__"):]
    mats = probe["orn_proto_materials"][grp]["materials"]
    j1 = next((j for j in jobs1.values() if j["prototype"] == proto_mesh), None)
    if j1 is None:
        orn_missing.append(grp)
        continue
    lo = bpy.data.objects.get(j1.get("lo_object", ""))
    hi = bpy.data.objects.get(j1["hi"])
    if lo is None or hi is None:
        orn_missing.append(grp)
        continue
    for ob in (lo, hi):
        set_material(ob.data, mats)
        ob.hide_viewport = ob.hide_select = False
    r = orn_rep[grp]
    size1 = int(j1["size"])
    jobs.append(dict(id=job_id(grp), group=grp, cls=g2.CLS_ORN, size=size1,
                     sizes=dict(albedo=size1, roughness=1024, normal=size1),
                     src_materials=mats, meshes=[group_meshes[grp][0]],
                     reps=[dict(mesh=group_meshes[grp][0], object=r["object"], station_d_m=r["station_d_m"],
                                placements=r["placements"])],
                     lo_object=lo.name, hi_object=hi.name, matrix=r["matrix"],
                     gate1_job=j1["id"], gate1_normal=os.path.basename(j1["normal"]),
                     gate1_ao=os.path.basename(j1["ao"]), max_dim_m=man1["meshes"][group_meshes[grp][0]]["max_dim_m"],
                     uv1_in_glb=True, blend="gate2_orn_bake.blend", metallic=[],
                     tris=eset["meshes"][group_meshes[grp][0]]["tris"],
                     area_m2=probe["groups"][grp]["area_m2"],
                     station_min_d_m=probe["groups"][grp]["station_min_d"],
                     hero_in_frame=probe["groups"][grp]["hero_in_frame"],
                     hero_min_d_m=probe["groups"][grp]["hero_min_d_in"]))
if orn_missing:
    raise SystemExit(f"[gate2] ORN lo/hi pair not found for {orn_missing}")
g0.save_copy(g2.OUT / "gate2_orn_bake.blend")
step.done(g2.OUT / "gate2_orn_bake.blend")

# ---------------------------------------------------------------- the job manifest
# cheap jobs first so a failure shows up early; the ORN block last (it carries the selected-to-active normal).
order = {g2.CLS_BACKDROP: 0, g2.CLS_GROUND: 1, g2.CLS_ARCH: 2, g2.CLS_ORN: 3}
jobs.sort(key=lambda j: (order[j["cls"]], j["id"]))
for j in jobs:
    for k in g2.MAPS:
        j.setdefault("out", {})[k] = f"tex/{g2.tex_name(j['id'], k)}"
rep["jobs"] = len(jobs)
(g2.jobs_path()).write_text(json.dumps(dict(generator="export/gate2_set.py", source=str(g2.SRC_BLEND),
                                            stations=len(STATIONS), jobs=jobs), indent=1) + "\n")
(g2.OUT / "gate2_set.json").write_text(json.dumps(rep, indent=1) + "\n")
step_all.done(g2.jobs_path(), g2.OUT / "gate2_set.json", jobs=len(jobs))
print(f"[gate2] set done: {len(jobs)} jobs")
