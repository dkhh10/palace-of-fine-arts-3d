"""Gate 2 step 0 (no GPU): read-only inventory of what has to be baked and with what.

    scripts/blender_run.sh 900 -- --background --python export/gate2_probe.py

Two read-only opens in one process:
  1. master_delivery.blend  - every material the export set references: node inventory, metallic, roughness,
     bump/normal detail, image textures, and the per-object material slot lists the Gate 1 merge flattened.
  2. gate1_set.blend        - per exported mesh: UV1 presence, surface area of ONE placement, bbox, the
     per-polygon material-index histogram, and the distance of every placement to the six QA stations.

Writes export/out/gate2/probe.json. Nothing is baked and nothing is saved.
"""
import bpy
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gate0_common as g0  # noqa: E402
import gate1_common as g1  # noqa: E402
import gate2_common as g2  # noqa: E402

g2.ensure_dirs()
step = g0.Step("gate2_probe")
eset = g2.read_export_set()
man1 = json.loads((g2.GATE1_OUT / "manifest.json").read_text())
report = {"source_materials": str(g2.SRC_BLEND), "source_geometry": str(g2.SET_BLEND)}

# ---------------------------------------------------------------- which materials the bake needs
need_mats = set()
group_src = {}          # group material name -> source material name (None for the ground / ORN groups)
group_meshes = {}
for mname, rec in eset["meshes"].items():
    grp = rec.get("material")
    if not grp or g2.NO_BAKE_MATERIALS.match(grp):
        continue
    group_meshes.setdefault(grp, []).append(mname)
    group_src[grp] = rec.get("src_material")
    if rec.get("src_material"):
        need_mats.add(rec["src_material"])

# ---------------------------------------------------------------- 1. master_delivery.blend
bpy.ops.wm.open_mainfile(filepath=str(g2.SRC_BLEND), load_ui=False)
print(f"[gate2] opened {g2.SRC_BLEND.name}: {len(bpy.data.materials)} materials, {len(bpy.data.objects)} objects")


def node_input_value(n, key):
    try:
        s = n.inputs[key]
    except Exception:
        return None
    if s.links:
        return "<linked:%s>" % s.links[0].from_node.bl_idname
    v = getattr(s, "default_value", None)
    if hasattr(v, "__len__"):
        return [round(float(x), 6) for x in v]
    return round(float(v), 6) if v is not None else None


def material_info(m):
    d = dict(name=m.name, use_nodes=bool(m.use_nodes), blend_method=getattr(m, "surface_render_method", None))
    if not m.use_nodes or m.node_tree is None:
        d["principled"] = None
        return d
    nt = m.node_tree
    kinds = {}
    for n in nt.nodes:
        kinds[n.bl_idname] = kinds.get(n.bl_idname, 0) + 1
    d["node_kinds"] = kinds
    d["n_nodes"] = len(nt.nodes)
    d["images"] = sorted({n.image.name for n in nt.nodes if n.bl_idname == "ShaderNodeTexImage" and n.image})
    d["has_uv_node"] = any(n.bl_idname in ("ShaderNodeUVMap", "ShaderNodeTexCoord") for n in nt.nodes)
    d["uv_maps_used"] = sorted({n.uv_map for n in nt.nodes if n.bl_idname == "ShaderNodeUVMap" and n.uv_map})
    bsdf = next((n for n in nt.nodes if n.bl_idname == "ShaderNodeBsdfPrincipled"), None)
    if bsdf:
        d["principled"] = {k: node_input_value(bsdf, k) for k in
                           ("Base Color", "Metallic", "Roughness", "IOR", "Alpha", "Normal",
                            "Specular IOR Level", "Coat Weight", "Emission Strength")}
    else:
        d["principled"] = None
        d["surface_node"] = next((ln.from_node.bl_idname for n in nt.nodes if n.bl_idname == "ShaderNodeOutputMaterial"
                                  for ln in n.inputs["Surface"].links), None)
    d["has_bump_or_normal"] = any(n.bl_idname in ("ShaderNodeBump", "ShaderNodeNormalMap",
                                                  "ShaderNodeDisplacement") for n in nt.nodes)
    d["has_displacement_out"] = any(len(n.inputs["Displacement"].links) > 0 for n in nt.nodes
                                    if n.bl_idname == "ShaderNodeOutputMaterial")
    # the round-9 photo projection and any other object/world-space driver
    d["coord_outputs"] = sorted({ln.from_socket.name for n in nt.nodes if n.bl_idname == "ShaderNodeTexCoord"
                                 for ln in n.outputs if False for _ in []}) or sorted(
        {o.name for n in nt.nodes if n.bl_idname == "ShaderNodeTexCoord" for o in n.outputs if o.links})
    d["node_groups"] = sorted({n.node_tree.name for n in nt.nodes if n.bl_idname == "ShaderNodeGroup" and n.node_tree})
    return d


mats = {}
for name in sorted(need_mats):
    m = bpy.data.materials.get(name)
    mats[name] = material_info(m) if m else {"name": name, "MISSING": True}

# the ORN prototypes' own materials (the Gate 1 group name carries the prototype mesh, not the material)
orn_proto_mat = {}
for grp in group_meshes:
    if not grp.startswith("MAT_EXP_ORN__"):
        continue
    proto_mesh = grp[len("MAT_EXP_ORN__"):]
    me = bpy.data.meshes.get(proto_mesh)
    slots = [s.name if s else None for s in (me.materials if me else [])]
    orn_proto_mat[grp] = dict(proto_mesh=proto_mesh, materials=slots, found=me is not None)
    for s in slots:
        if s and s not in mats:
            mm = bpy.data.materials.get(s)
            mats[s] = material_info(mm) if mm else {"name": s, "MISSING": True}

# the ground / backdrop objects' original slot lists (the Gate 1 merge flattened them to one grey)
src_obj_slots = {}
for ob in bpy.data.objects:
    if ob.type != "MESH":
        continue
    if ob.name.startswith(("ENV_ground", "ENV_terrain", "ENV_lagoon", "ENV_riprap", "ENV_backdrop")):
        src_obj_slots[ob.name] = [s.material.name if s.material else None for s in ob.material_slots]
        for s in src_obj_slots[ob.name]:
            if s and s not in mats:
                mm = bpy.data.materials.get(s)
                mats[s] = material_info(mm) if mm else {"name": s, "MISSING": True}

# MAT_dome_membrane proof: the regenerated file must carry the MAT r10 28-panel ridge inputs
dm = bpy.data.materials.get("MAT_dome_membrane")
dome = {"present": dm is not None}
if dm and dm.use_nodes:
    nodes = list(dm.node_tree.nodes)
    dome["n_nodes"] = len(nodes)
    dome["node_names"] = sorted(n.name for n in nodes)
    dome["labels"] = sorted({n.label for n in nodes if n.label})
    dome["groups"] = sorted({n.node_tree.name for n in nodes if n.bl_idname == "ShaderNodeGroup" and n.node_tree})
    # a "28" anywhere in a value socket or a node name is the panel count
    hits = []
    for n in nodes:
        for s in list(n.inputs) + list(n.outputs):
            v = getattr(s, "default_value", None)
            if isinstance(v, float) and abs(v - 28.0) < 1e-6:
                hits.append(f"{n.name}.{s.name}={v}")
        if "28" in n.name or "28" in (n.label or ""):
            hits.append(f"node:{n.name}/{n.label}")
    dome["panel_28_hits"] = hits
report["dome_membrane"] = dome
report["materials"] = mats
report["orn_proto_materials"] = orn_proto_mat
report["src_object_slots"] = src_obj_slots

# ---------------------------------------------------------------- 2. gate1_set.blend
bpy.ops.wm.open_mainfile(filepath=str(g2.SET_BLEND), load_ui=False)
print(f"[gate2] opened {g2.SET_BLEND.name}: {len(bpy.data.objects)} objects, {len(bpy.data.meshes)} meshes")

stations = man1["stations"]
hero = man1["hero_camera"]


def cam_basis(st):
    from mathutils import Euler, Vector
    loc = Vector(st["location"])
    rot = Euler(st["rotation_euler_xyz"], "XYZ").to_matrix()
    fwd = rot @ Vector((0.0, 0.0, -1.0))
    right = rot @ Vector((1.0, 0.0, 0.0))
    up = rot @ Vector((0.0, 1.0, 0.0))
    half_x = math.atan2(st["sensor_width_mm"] * 0.5, st["lens_mm"])
    half_y = math.atan2(st["sensor_width_mm"] * 0.5 * 9.0 / 16.0, st["lens_mm"])
    return loc, fwd, right, up, half_x, half_y


hero_basis = cam_basis(stations[hero])
station_basis = {k: cam_basis(v) for k, v in stations.items() if k.startswith("CAM_qa_")}

mesh_rows = {}
for mname, rec in eset["meshes"].items():
    me = bpy.data.meshes.get(mname)
    if me is None:
        mesh_rows[mname] = {"MISSING_IN_SET": True}
        continue
    area = sum(p.area for p in me.polygons)
    uv1 = me.uv_layers.get(g2.UV1)
    mi = {}
    for p in me.polygons:
        mi[p.material_index] = mi.get(p.material_index, 0) + 1
    bb = [list(v) for v in me.vertices[:0]]  # placeholder
    xs = [v.co for v in me.vertices]
    dims = [round(max(c[i] for c in xs) - min(c[i] for c in xs), 4) for i in range(3)] if xs else [0, 0, 0]
    mesh_rows[mname] = dict(area_m2=round(area, 3), uv1=uv1 is not None, uv2=me.uv_layers.get(g2.UV2) is not None,
                            uv_layers=[l.name for l in me.uv_layers], slots=[s.name if s else None for s in me.materials],
                            poly_material_index=mi, dims_m=dims, max_dim_m=round(max(dims), 4),
                            tris=rec["tris"], cls=rec["cls"], group=rec.get("material"), bb=bb)

# per placement: distance and in-frustum for the hero, min distance over the six stations
from mathutils import Vector  # noqa: E402


def frustum(basis, p, pad=0.0):
    loc, fwd, right, up, hx, hy = basis
    d = Vector(p) - loc
    z = d.dot(fwd)
    if z <= 0.01:
        return False, d.length
    ax = abs(math.atan2(d.dot(right), z))
    ay = abs(math.atan2(d.dot(up), z))
    return (ax <= hx + pad and ay <= hy + pad), d.length


group_stats = {}
for aname, arec in eset["assets"].items():
    grp = arec.get("material")
    if not grp or grp not in group_meshes:
        continue
    p = arec.get("location_blender")
    if not p:
        continue
    gs = group_stats.setdefault(grp, dict(placements=0, hero_in_frame=0, hero_min_d=1e9, hero_min_d_in=1e9,
                                          station_min_d=1e9, station_min_d_cam=None))
    gs["placements"] += 1
    inf, d = frustum(hero_basis, p, pad=0.05)
    gs["hero_min_d"] = min(gs["hero_min_d"], d)
    if inf:
        gs["hero_in_frame"] += 1
        gs["hero_min_d_in"] = min(gs["hero_min_d_in"], d)
    for cam, b in station_basis.items():
        i2, d2 = frustum(b, p, pad=0.05)
        if i2 and d2 < gs["station_min_d"]:
            gs["station_min_d"] = d2
            gs["station_min_d_cam"] = cam

for grp, gs in group_stats.items():
    meshes = group_meshes[grp]
    area = sum(mesh_rows[m].get("area_m2", 0.0) for m in meshes)
    gs["meshes"] = len(meshes)
    gs["area_m2"] = round(area, 2)
    gs["tris"] = sum(mesh_rows[m].get("tris", 0) for m in meshes)
    gs["max_dim_m"] = round(max([mesh_rows[m].get("max_dim_m", 0.0) for m in meshes] or [0.0]), 3)
    gs["src_material"] = group_src.get(grp)
    gs["uv1"] = all(mesh_rows[m].get("uv1") for m in meshes)
    for k in ("hero_min_d", "hero_min_d_in", "station_min_d"):
        gs[k] = None if gs[k] > 9e8 else round(gs[k], 2)
    # texel size at 2K if the whole atlas were filled by this group's area
    gs["m_per_texel_2k"] = round(math.sqrt(area) / 2048.0, 5) if area > 0 else None

report["groups"] = group_stats
report["meshes"] = mesh_rows
report["group_meshes"] = group_meshes
(g2.OUT / "probe.json").write_text(json.dumps(report, indent=1) + "\n")
step.done(g2.OUT / "probe.json", groups=len(group_stats), materials=len(mats))
print("[gate2] probe done")
