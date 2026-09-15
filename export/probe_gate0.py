"""Read-only probe of master_delivery.blend for the Gate 0 slice. Writes export/out/gate0/probe.json only.

    scripts/blender_run.sh 600 -- --background <master_delivery.blend> --python export/probe_gate0.py
"""
import bpy
import os
import sys
import json
import math

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gate0_common as g0  # noqa: E402
import common  # noqa: E402

g0.ensure_dirs()
scene = bpy.context.scene
out = {"file": bpy.data.filepath, "objects": len(bpy.data.objects)}

# --- the slice objects -------------------------------------------------------------------------------
def mesh_info(name):
    ob = bpy.data.objects.get(name)
    if ob is None:
        return {"missing": name}
    me = ob.data
    return dict(name=ob.name, mesh=me.name, verts=len(me.vertices), polys=len(me.polygons),
                tris=sum(len(p.vertices) - 2 for p in me.polygons),
                uv_layers=[u.name for u in me.uv_layers], active_uv=me.uv_layers.active.name if me.uv_layers.active else None,
                color_attrs=[c.name for c in me.color_attributes],
                mats=[m.name if m else None for m in me.materials],
                users=me.users, mods=[m.type for m in ob.modifiers],
                loc=list(ob.location), scale=list(ob.scale), rot=list(ob.rotation_euler),
                dims=[round(d, 3) for d in ob.dimensions],
                bbox_min_z=round(min((ob.matrix_world @ __import__("mathutils").Vector(c)).z for c in ob.bound_box), 3),
                bbox_max_z=round(max((ob.matrix_world @ __import__("mathutils").Vector(c)).z for c in ob.bound_box), 3))


out["column"] = mesh_info(g0.COLUMN_HI)
out["capital"] = mesh_info(g0.CAPITAL_HI)

# --- ground: downward ray cast from the column's base, ignoring ARCH_rotunda_column* -------------------
from mathutils import Vector  # noqa: E402

col = bpy.data.objects[g0.COLUMN_HI]
base_z = out["column"]["bbox_min_z"]
origin = Vector((col.location.x, col.location.y, base_z - 0.02))
dg = bpy.context.evaluated_depsgraph_get()
hits = []
o = origin.copy()
for _ in range(12):
    ok, loc, nor, idx, hit_obj, mat = scene.ray_cast(dg, o, Vector((0, 0, -1)))
    if not ok:
        break
    hits.append(dict(obj=hit_obj.name, z=round(loc.z, 3), dist=round((loc - origin).length, 3),
                     mats=[m.name if m else None for m in hit_obj.data.materials] if hit_obj.type == "MESH" else []))
    o = loc + Vector((0, 0, -0.01))
out["ground_raycast_origin"] = [round(v, 3) for v in origin]
out["ground_raycast_hits"] = hits

# --- materials of the slice ---------------------------------------------------------------------------
def mat_info(name):
    m = bpy.data.materials.get(name)
    if m is None:
        return {"missing": name}
    nodes = []
    for n in m.node_tree.nodes:
        d = dict(name=n.name, type=n.bl_idname)
        if n.bl_idname == "ShaderNodeTexImage" and n.image:
            d["image"] = n.image.name
            d["size"] = list(n.image.size)
            d["colorspace"] = n.image.colorspace_settings.name
            d["packed"] = bool(n.image.packed_file)
        if n.bl_idname == "ShaderNodeUVMap":
            d["uv"] = n.uv_map
        if n.bl_idname == "ShaderNodeTexCoord":
            d["outs"] = [l.to_socket.node.name for o_ in n.outputs for l in o_.links]
        nodes.append(d)
    bsdf = next((n for n in m.node_tree.nodes if n.bl_idname == "ShaderNodeBsdfPrincipled"), None)
    return dict(name=m.name, nodes=len(m.node_tree.nodes), node_types=sorted(set(n["type"] for n in nodes)),
                images=[n for n in nodes if "image" in n], uv_nodes=[n for n in nodes if "uv" in n],
                has_bsdf=bool(bsdf), blend_method=getattr(m, "blend_method", None),
                displacement_linked=bool(m.node_tree.nodes.get("Material Output") and
                                         m.node_tree.nodes["Material Output"].inputs["Displacement"].links))


out["materials"] = {n: mat_info(n) for n in ("MAT_column_rose", "MAT_ornament_concrete")}

# --- world node tree: every link out of the Light Path node (for branch isolation) ---------------------
w = scene.world
wt = w.node_tree
lp_nodes = [n for n in wt.nodes if n.bl_idname == "ShaderNodeLightPath"]
links = []
for n in lp_nodes:
    for o_ in n.outputs:
        for l in o_.links:
            links.append(dict(from_node=n.name, from_socket=o_.name,
                              to_node=l.to_node.name, to_type=l.to_node.bl_idname, to_socket=l.to_socket.name,
                              to_socket_index=list(l.to_node.inputs).index(l.to_socket)))
out["world"] = dict(name=w.name, light_path_nodes=[n.name for n in lp_nodes], light_path_links=links,
                    nodes=len(wt.nodes))
sky = next((n for n in wt.nodes if n.bl_idname == "ShaderNodeTexSky"), None)
if sky:
    out["world"]["sky"] = dict(type=sky.sky_type, sun_elevation_deg=math.degrees(sky.sun_elevation),
                               sun_rotation_deg=math.degrees(sky.sun_rotation), sun_disc=sky.sun_disc,
                               air=sky.air_density, aerosol=sky.aerosol_density, ozone=sky.ozone_density)

# --- lights, view settings, cameras --------------------------------------------------------------------
suns = [o for o in bpy.data.objects if o.type == "LIGHT" and o.data.type == "SUN"]
out["suns"] = [dict(name=o.name, energy=o.data.energy, color=list(o.data.color), angle=o.data.angle,
                    rot=list(o.rotation_euler), hide_render=o.hide_render,
                    dir=[round(v, 5) for v in (o.matrix_world.to_quaternion() @ Vector((0, 0, -1)))])
               for o in suns]
out["lights_nonzero"] = [dict(name=o.name, type=o.data.type, energy=o.data.energy, hide_render=o.hide_render)
                         for o in bpy.data.objects if o.type == "LIGHT" and o.data.energy > 0 and not o.hide_render]
out["view"] = dict(view_transform=scene.view_settings.view_transform, look=scene.view_settings.look,
                   exposure=scene.view_settings.exposure, gamma=scene.view_settings.gamma,
                   display=scene.display_settings.display_device, use_compositor=scene.use_nodes,
                   engine=scene.render.engine)
out["water_z"] = common.WATER_Z
out["cameras"] = {o.name: dict(loc=list(o.location), rot=list(o.rotation_euler), lens=o.data.lens,
                               shift=[o.data.shift_x, o.data.shift_y], sensor=o.data.sensor_width,
                               sensor_fit=o.data.sensor_fit, clip=[o.data.clip_start, o.data.clip_end])
                  for o in bpy.data.objects if o.type == "CAMERA"}
out["ocio_python"] = {"has_bpy_ocio": hasattr(bpy.types, "ColorManagedViewSettings"),
                      "looks": [i.identifier for i in scene.view_settings.bl_rna.properties["look"].enum_items][:40],
                      "view_transforms": [i.identifier for i in scene.view_settings.bl_rna.properties["view_transform"].enum_items]}

p = g0.OUT / "probe.json"
p.write_text(json.dumps(out, indent=1) + "\n")
print(f"[gate0] probe written {p} {p.stat().st_size}B")
