"""Phase 6 read-only inventory of master_delivery.blend (lead probe; writes nothing to the .blend).

    scripts/blender_run.sh 600 -- --background master_delivery.blend --python export/inventory.py -- --out export/inventory.json

Per prefix (ARCH/ORN/ENV/LIGHT/other) and LOD suffix: objects, unique meshes, evaluated triangles (modifiers applied,
per LOD level via common.set_lod so hidden LODs are evaluated too), materials with their texture kinds, world/sky
summary, view settings, cameras. Used for docs/briefs/phase6_budget.md.
"""
import bpy, sys, os, json, re, collections
sys.path.insert(0, os.path.join(os.path.dirname(bpy.data.filepath) or os.getcwd(), "scripts"))
import common  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
out = argv[argv.index("--out") + 1] if "--out" in argv else "export/inventory.json"
LOD_RE = re.compile(r"_LOD(\d)$")


def prefix(name):
    m = re.match(r"([A-Z]+)_", name)
    return m.group(1) if m else "other"


def lod_of(obj):
    m = LOD_RE.search(obj.name)
    if m:
        return int(m.group(1))
    for c in obj.users_collection:
        m = LOD_RE.search(c.name)
        if m:
            return int(m.group(1))
    return None


def tri_counts(level):
    """Evaluated tri count per object with the viewport at LOD<level> (unrelated objects unchanged)."""
    common.set_lod(viewport=level, render=0)
    dg = bpy.context.evaluated_depsgraph_get()
    res = {}
    for ob in bpy.data.objects:
        if ob.type != "MESH" or ob.hide_viewport or not ob.visible_get():
            continue
        me = ob.evaluated_get(dg).to_mesh()
        res[ob.name] = sum(len(p.vertices) - 2 for p in me.polygons)
        ob.evaluated_get(dg).to_mesh_clear()
    return res


scene = bpy.context.scene
inv = {"file": bpy.data.filepath, "objects_total": len(bpy.data.objects), "meshes_total": len(bpy.data.meshes),
       "materials_total": len(bpy.data.materials), "images_total": len(bpy.data.images),
       "view": dict(engine=scene.render.engine, view_transform=scene.view_settings.view_transform,
                    look=scene.view_settings.look, exposure=scene.view_settings.exposure,
                    gamma=scene.view_settings.gamma, res=(scene.render.resolution_x, scene.render.resolution_y),
                    frame_range=(scene.frame_start, scene.frame_end), fps=scene.render.fps),
       "cameras": {o.name: dict(loc=list(o.location), rot=list(o.rotation_euler), lens=o.data.lens,
                                shift=(o.data.shift_x, o.data.shift_y), sensor=o.data.sensor_width)
                   for o in bpy.data.objects if o.type == "CAMERA"},
       "water_z": common.WATER_Z}

# world
w = scene.world
inv["world"] = {"name": w.name if w else None, "nodes": []}
if w and w.use_nodes:
    for n in w.node_tree.nodes:
        d = {"name": n.name, "type": n.bl_idname}
        if n.bl_idname == "ShaderNodeTexSky":
            d.update({k: getattr(n, k) for k in ("sky_type", "sun_disc", "sun_size", "sun_intensity", "sun_elevation",
                                                  "sun_rotation", "altitude", "air_density", "aerosol_density",
                                                  "ozone_density")})
        if n.bl_idname in ("ShaderNodeBackground", "ShaderNodeMixShader", "ShaderNodeLightPath", "ShaderNodeMath"):
            d["inputs"] = {i.name: (list(i.default_value) if hasattr(i.default_value, "__len__") else i.default_value)
                           for i in n.inputs if hasattr(i, "default_value") and not i.is_linked}
        inv["world"]["nodes"].append(d)

# lights
inv["lights"] = {o.name: dict(type=o.data.type, energy=o.data.energy, color=list(o.data.color),
                              angle=getattr(o.data, "angle", None), hide_render=o.hide_render,
                              rot=list(o.rotation_euler), collection=[c.name for c in o.users_collection])
                 for o in bpy.data.objects if o.type == "LIGHT"}

# tri counts per LOD level
tris = {lvl: tri_counts(lvl) for lvl in (0, 1, 2)}
common.set_lod(viewport=1, render=0)

by = collections.defaultdict(lambda: dict(objects=0, meshes=set(), tris=0, hidden_render=0, materials=set()))
per_object = []
for ob in bpy.data.objects:
    if ob.type != "MESH":
        continue
    p, l = prefix(ob.name), lod_of(ob)
    key = f"{p}_LOD{l}" if l is not None else f"{p}_noLOD"
    t = tris[l if l is not None else 1].get(ob.name, tris[0].get(ob.name, tris[2].get(ob.name, 0)))
    b = by[key]
    b["objects"] += 1; b["meshes"].add(ob.data.name); b["tris"] += t
    b["hidden_render"] += int(ob.hide_render)
    for s in ob.material_slots:
        if s.material:
            b["materials"].add(s.material.name)
    per_object.append(dict(name=ob.name, mesh=ob.data.name, lod=l, tris=t, users=ob.data.users,
                           mods=[m.type for m in ob.modifiers], mats=[s.material.name for s in ob.material_slots if s.material],
                           hide_render=ob.hide_render, coll=[c.name for c in ob.users_collection],
                           dims=[round(v, 2) for v in ob.dimensions], loc=[round(v, 2) for v in ob.location]))
inv["by_prefix_lod"] = {k: dict(objects=v["objects"], unique_meshes=len(v["meshes"]), tris=v["tris"],
                                hidden_render=v["hidden_render"], materials=sorted(v["materials"]))
                        for k, v in sorted(by.items())}

# materials: texture kinds
mats = {}
for m in bpy.data.materials:
    if not m.use_nodes:
        mats[m.name] = {"nodes": 0, "images": [], "procedural": []}
        continue
    imgs, proc, kinds = [], [], collections.Counter()
    for n in m.node_tree.nodes:
        kinds[n.bl_idname] += 1
        if n.bl_idname == "ShaderNodeTexImage" and n.image:
            imgs.append(dict(image=n.image.name, size=list(n.image.size), packed=bool(n.image.packed_file),
                             colorspace=n.image.colorspace_settings.name))
        elif n.bl_idname.startswith("ShaderNodeTex"):
            proc.append(n.bl_idname)
    bsdf = [n for n in m.node_tree.nodes if n.bl_idname == "ShaderNodeBsdfPrincipled"]
    mats[m.name] = {"nodes": len(m.node_tree.nodes), "images": imgs, "procedural": sorted(set(proc)),
                    "users": m.users, "principled": len(bsdf), "has_displacement": "ShaderNodeDisplacement" in kinds,
                    "emission": any(n.bl_idname == "ShaderNodeEmission" for n in m.node_tree.nodes),
                    "blend_method": getattr(m, "surface_render_method", None)}
inv["materials"] = mats
inv["per_object"] = per_object

os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
with open(out, "w") as f:
    json.dump(inv, f, indent=1, default=str)
tot = {k: v["tris"] for k, v in inv["by_prefix_lod"].items()}
print("[inventory] wrote", out, "objects", inv["objects_total"], "tris by prefix/lod", tot)
