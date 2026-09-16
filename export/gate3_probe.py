"""Gate 3 step 0: read-only inventory of the bake sources. No GPU, nothing saved.

    scripts/blender_run.sh 900 -- --background --python export/gate3_probe.py

Answers, with numbers, the questions the Gate 3 plan rests on:
  * what gate2_bake.blend actually holds (objects by class, lights, world, hidden objects, UV layers)
  * the 16 own-map UV2 assets: area, UV2 coverage, cm/texel at 2K
  * the 988 slot instances: pool, prototype, mesh, area, cm/texel at 248 px
  * the near trees and the terrain: vertex counts and the vertex spacing a VERTEX_COLORS bake would give
  * the 25 far-tree prototypes in master_delivery.blend: bbox, tris, instance rotations
  * the hero station and its mirror below the water plane
"""
import bpy
import os
import sys
import json
import math
import time
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gate0_common as g0      # noqa: E402
import gate2_common as g2      # noqa: E402

t_all = time.time()
OUT = g0.ROOT / "export" / "out" / "gate3"
OUT.mkdir(parents=True, exist_ok=True)
rep = {"started": time.strftime("%Y-%m-%dT%H:%M:%S")}

eset = json.loads((g2.GATE1_OUT / "export_set.json").read_text())
assets = eset["assets"]

# ---------------------------------------------------------------- 1. gate2_bake.blend
src = g2.OUT / "gate2_bake.blend"
t0 = time.time()
bpy.ops.wm.open_mainfile(filepath=str(src), load_ui=False)
rep["open_gate2_bake_s"] = round(time.time() - t0, 1)
sc = bpy.context.scene
rep["gate2_bake"] = dict(
    path=str(src), objects=len(bpy.data.objects), meshes=len(bpy.data.meshes),
    materials=len(bpy.data.materials), images=len(bpy.data.images),
    lights=[o.name for o in bpy.data.objects if o.type == "LIGHT"],
    cameras=[o.name for o in bpy.data.objects if o.type == "CAMERA"],
    world=(sc.world.name if sc.world else None),
    worlds=[w.name for w in bpy.data.worlds],
    engine=sc.render.engine,
    collections=[c.name for c in bpy.data.collections],
    hide_render=sum(1 for o in bpy.data.objects if o.type == "MESH" and o.hide_render),
    hide_viewport=sum(1 for o in bpy.data.objects if o.type == "MESH" and o.hide_viewport),
    view_transform=sc.view_settings.view_transform, look=sc.view_settings.look,
    exposure=round(sc.view_settings.exposure, 6),
    compositing_node_group=(sc.compositing_node_group.name if getattr(sc, "compositing_node_group", None) else None),
)
pref = {}
for o in bpy.data.objects:
    if o.type != "MESH":
        continue
    p = o.name.split("_")[0]
    pref[p] = pref.get(p, 0) + 1
rep["gate2_bake"]["by_prefix"] = dict(sorted(pref.items(), key=lambda kv: -kv[1]))

dg = bpy.context.evaluated_depsgraph_get()


def area_tris(ob):
    me = ob.data
    mw = ob.matrix_world
    a = 0.0
    for p in me.polygons:
        vs = [mw @ me.vertices[i].co for i in p.vertices]
        for k in range(1, len(vs) - 1):
            a += (vs[k] - vs[0]).cross(vs[k + 1] - vs[0]).length * 0.5
    return a


def uv_area(me, layer):
    lay = me.uv_layers.get(layer)
    if lay is None:
        return None
    uvs = [tuple(lay.data[li].uv) for li in range(len(me.loops))]
    a = 0.0
    for p in me.polygons:
        pts = [Vector(uvs[li]) for li in p.loop_indices]
        for k in range(1, len(pts) - 1):
            e1, e2 = pts[k] - pts[0], pts[k + 1] - pts[0]
            a += abs(e1.x * e2.y - e1.y * e2.x) * 0.5
    return a


# ---------------------------------------------------------------- 2. the 16 own-map assets
own = []
for name, r in assets.items():
    lm = r.get("lightmap") or {}
    if lm.get("mode") != "asset":
        continue
    ob = bpy.data.objects.get(name)
    if ob is None:
        own.append(dict(object=name, missing=True))
        continue
    me = ob.data
    a = area_tris(ob)
    ua = uv_area(me, g0.UV2)
    size = int(lm.get("size", 2048))
    cm_per_texel = None
    if ua and ua > 0:
        cm_per_texel = 100.0 * math.sqrt(a / (ua * size * size))
    own.append(dict(object=name, mesh=me.name, cls=r["cls"], tris=r["tris"], size=size,
                    area_m2=round(a, 1), uv2_coverage=round(ua, 4) if ua else None,
                    cm_per_texel=round(cm_per_texel, 2) if cm_per_texel else None,
                    uv_layers=[l.name for l in me.uv_layers],
                    materials=[m.name if m else None for m in me.materials],
                    hide_render=ob.hide_render, verts=len(me.vertices)))
rep["own_maps"] = sorted(own, key=lambda d: -(d.get("area_m2") or 0))

# ---------------------------------------------------------------- 3. the 988 slot instances
slots = {"orn": [], "arch_inst": []}
by_mesh_area = {}
for name, r in assets.items():
    lm = r.get("lightmap") or {}
    if lm.get("mode") != "slot":
        continue
    ob = bpy.data.objects.get(name)
    if ob is None:
        continue
    mn = ob.data.name
    if mn not in by_mesh_area:
        by_mesh_area[mn] = area_tris(ob)
    slots[lm["pool"]].append(dict(object=name, mesh=mn, atlas=lm["atlas"], slot=lm["slot"],
                                  area_m2=round(by_mesh_area[mn], 3), tris=r["tris"],
                                  material=r["material"]))
usable = 248
sl_sum = {}
for pool, lst in slots.items():
    lst.sort(key=lambda d: (d["atlas"], d["slot"]))
    cm = [100.0 * math.sqrt(d["area_m2"] / (usable * usable)) for d in lst if d["area_m2"] > 0]
    sl_sum[pool] = dict(n=len(lst), atlases=1 + max(d["atlas"] for d in lst) if lst else 0,
                        meshes=len({d["mesh"] for d in lst}),
                        cm_per_texel_min=round(min(cm), 2), cm_per_texel_max=round(max(cm), 2),
                        cm_per_texel_mean=round(sum(cm) / len(cm), 2),
                        uv2_present=all(bpy.data.meshes[d["mesh"]].uv_layers.get(g0.UV2) is not None for d in lst))
rep["slots_summary"] = sl_sum
rep["slots"] = slots

# ---------------------------------------------------------------- 4. near trees + terrain (VERTEX_COLORS)
vc = []
for name in [t["name"] for t in eset["tree_near_list"]] + ["ENV_terrain_ground"]:
    ob = bpy.data.objects.get(name)
    if ob is None:
        # the export renamed the near trees' meshes; find by mesh prefix
        cand = [o for o in bpy.data.objects if o.type == "MESH" and o.name.startswith(name)]
        ob = cand[0] if cand else None
    if ob is None:
        vc.append(dict(object=name, missing=True))
        continue
    me = ob.data
    a = area_tris(ob)
    n = len(me.vertices)
    vc.append(dict(object=ob.name, mesh=me.name, verts=n, tris=len(me.loop_triangles) or sum(len(p.vertices) - 2 for p in me.polygons),
                   area_m2=round(a, 1), m_per_vertex=round(math.sqrt(a / max(n, 1)), 3),
                   color_attributes=[c.name for c in me.color_attributes],
                   uv_layers=[l.name for l in me.uv_layers]))
rep["vertex_bake_candidates"] = vc

# ---------------------------------------------------------------- 5. stations / water
try:
    import common as pfa_common
    rep["water_z"] = float(pfa_common.WATER_Z)
except Exception as e:
    rep["water_z_error"] = str(e)
_man = json.loads((g2.OUT / "manifest.json").read_text())
rep["stations"] = {k: dict(location=v["location"], rot=v["rotation_euler_xyz"], lens=v["lens_mm"])
                   for k, v in _man["stations"].items()}
rep["hero_camera"] = _man["hero_camera"]

# ---------------------------------------------------------------- 6. the 25 far-tree prototypes, in master_delivery
protos = sorted({t["prototype"] for t in eset["tree_far_list"]})
rep["far_prototypes_requested"] = protos

t0 = time.time()
bpy.ops.wm.open_mainfile(filepath=str(g2.SRC_BLEND), load_ui=False)
rep["open_master_delivery_s"] = round(time.time() - t0, 1)
for o in bpy.data.objects:
    o.hide_viewport = False
bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get()

pinfo = []
for pn in protos:
    ob = bpy.data.objects.get(pn)
    if ob is None:
        pinfo.append(dict(prototype=pn, missing=True))
        continue
    ev = ob.evaluated_get(dg)
    me = ev.to_mesh()
    tris = sum(len(p.vertices) - 2 for p in me.polygons)
    # local-space bbox of the evaluated mesh, at the object's own scale
    co = [ob.matrix_world @ v.co for v in me.vertices]
    ev.to_mesh_clear()
    if not co:
        pinfo.append(dict(prototype=pn, empty=True))
        continue
    xs = [c.x for c in co]; ys = [c.y for c in co]; zs = [c.z for c in co]
    mats = [m.name if m else None for m in ob.data.materials]
    pinfo.append(dict(prototype=pn, tris=tris, verts=len(co),
                      dims_m=[round(max(xs) - min(xs), 3), round(max(ys) - min(ys), 3), round(max(zs) - min(zs), 3)],
                      base_z=round(min(zs), 3), loc=[round(v, 3) for v in ob.location],
                      rot_z_deg=round(math.degrees(ob.rotation_euler.z), 2),
                      scale=[round(v, 4) for v in ob.scale],
                      materials=mats, hide_render=ob.hide_render))
rep["far_prototypes"] = pinfo
rep["master"] = dict(objects=len(bpy.data.objects),
                     lights=[o.name for o in bpy.data.objects if o.type == "LIGHT"],
                     world=bpy.context.scene.world.name if bpy.context.scene.world else None)
rep["wall_s"] = round(time.time() - t_all, 1)
(OUT / "probe.json").write_text(json.dumps(rep, indent=1) + "\n")
print(f"[gate3] probe done in {rep['wall_s']} s -> {OUT/'probe.json'}")
