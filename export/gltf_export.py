"""Gate 0 step 6a: build the baked materials and write export/out/gate0/gate0.gltf (+ separate textures).

    scripts/blender_run.sh 900 -- --background export/out/gate0/gate0_set.blend --python export/gltf_export.py

Only the GATE0 collection is exported (the GATE0_REF hi-poly originals and the lights stay behind). Materials are
rebuilt from the baked maps: baseColor = albedo (sRGB), metallic 0, roughness = the roughness bake, normal = the
hi->lo tangent normal, all on UV1.

The lightmap rides in the **emissive** slot on UV2. Why: glTF has no lightmap slot, and the exporter only writes a
TEXCOORD_1 attribute for a UV layer some texture actually uses. The emissive slot is the one slot that is certain
to survive both the Blender exporter and gltfpack, and it carries its own texCoord index. The viewer MUST set
`material.emissive` to black, take `material.emissiveMap` as `material.lightMap` (channel 1) and decode RGBM8;
the manifest says so per asset. Only ARCH_rotunda_column_00_LOD0's placement has a lightmap at Gate 0, so the
column exists as two materials (GATE0_column_lit for placement 00, GATE0_column for the other 15).

`export_yup=True`: Blender +Y -> glTF -Z, Blender +Z -> glTF +Y. The viewer never re-rotates the scene.
"""
import bpy
import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gate0_common as g0  # noqa: E402
import common  # noqa: E402

g0.ensure_dirs()
scene = bpy.context.scene
step = g0.Step("gltf_export")
tex = g0.OUT / "tex"
report = {}


def img(path, colorspace):
    p = str(tex / path)
    assert os.path.exists(p), f"missing baked texture {p}"
    im = bpy.data.images.load(p, check_existing=True)
    im.colorspace_settings.name = colorspace
    return im


def baked_material(name, key, lightmap):
    m = bpy.data.materials.get(name)
    if m:
        bpy.data.materials.remove(m)
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    bsdf.inputs["Metallic"].default_value = 0.0
    uv1 = nt.nodes.new("ShaderNodeUVMap"); uv1.uv_map = g0.UV1
    a = nt.nodes.new("ShaderNodeTexImage"); a.image = img(f"gate0_{key}_albedo.png", "sRGB")
    nt.links.new(uv1.outputs["UV"], a.inputs["Vector"])
    nt.links.new(a.outputs["Color"], bsdf.inputs["Base Color"])
    r = nt.nodes.new("ShaderNodeTexImage"); r.image = img(f"gate0_{key}_roughness.png", "Non-Color")
    nt.links.new(uv1.outputs["UV"], r.inputs["Vector"])
    nt.links.new(r.outputs["Color"], bsdf.inputs["Roughness"])
    n = nt.nodes.new("ShaderNodeTexImage"); n.image = img(f"gate0_{key}_normal.png", "Non-Color")
    nmap = nt.nodes.new("ShaderNodeNormalMap")
    nt.links.new(uv1.outputs["UV"], n.inputs["Vector"])
    nt.links.new(n.outputs["Color"], nmap.inputs["Color"])
    nt.links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])
    if lightmap:
        uv2 = nt.nodes.new("ShaderNodeUVMap"); uv2.uv_map = g0.UV2
        lm = nt.nodes.new("ShaderNodeTexImage"); lm.image = img(lightmap, "Non-Color")
        nt.links.new(uv2.outputs["UV"], lm.inputs["Vector"])
        em_in = bsdf.inputs.get("Emission Color") or bsdf.inputs.get("Emission")
        nt.links.new(lm.outputs["Color"], em_in)
        if "Emission Strength" in bsdf.inputs:
            bsdf.inputs["Emission Strength"].default_value = 1.0
    return m


mats = {
    "column_lit": baked_material("GATE0_column_lit", "column", "gate0_column_lightmap_rgbm8.png"),
    "column": baked_material("GATE0_column", "column", None),
    "capital": baked_material("GATE0_capital", "capital", "gate0_capital_lightmap_rgbm8.png"),
    "ground": baked_material("GATE0_ground_mat", "ground", "gate0_ground_lightmap_rgbm8.png"),
}

gate0 = bpy.data.collections[g0.GATE0_COLL]
assets = {}
for ob in list(gate0.objects):
    if ob.name.startswith(g0.LO_COLUMN):
        idx = int(ob.name.rsplit("_", 1)[1])
        if idx == 0:
            ob.data = ob.data.copy()        # placement 00 gets its own mesh so it can carry the lit material
            ob.data.name = "GATE0_column_lit_mesh"
        ob.data.materials.clear()
        ob.data.materials.append(mats["column_lit"] if idx == 0 else mats["column"])
    elif ob.name == g0.LO_CAPITAL:
        ob.data.materials.clear()
        ob.data.materials.append(mats["capital"])
    elif ob.name == "GATE0_ground":
        ob.data.materials.clear()
        ob.data.materials.append(mats["ground"])
    ob.hide_viewport = False
    ob.hide_render = False
    tris = sum(len(p.vertices) - 2 for p in ob.data.polygons)
    assets[ob.name] = dict(mesh=ob.data.name, tris=tris,
                           material=ob.data.materials[0].name,
                           uv=[u.name for u in ob.data.uv_layers],
                           location_blender=[round(v, 6) for v in ob.matrix_world.translation],
                           lightmap=("column_lightmap" if ob.name.endswith("_00") and ob.name.startswith(g0.LO_COLUMN)
                                     else "capital_lightmap" if ob.name == g0.LO_CAPITAL
                                     else "ground_lightmap" if ob.name == "GATE0_ground" else None))

# select only the export set
for o in bpy.context.selected_objects:
    o.select_set(False)
for ob in gate0.objects:
    ob.select_set(True)
bpy.context.view_layer.objects.active = list(gate0.objects)[0]

gltf = g0.OUT / "gate0.gltf"
want = dict(filepath=str(gltf), export_format="GLTF_SEPARATE", use_selection=True,
            export_yup=True, export_apply=True, export_tangents=True, export_normals=True,
            export_texcoords=True, export_materials="EXPORT", export_image_format="AUTO",
            export_keep_originals=False, export_cameras=False, export_lights=False,
            export_extras=False, export_animations=False, export_skins=False, export_morph=False,
            export_texture_dir="tex_gltf")
props = set(bpy.ops.export_scene.gltf.get_rna_type().properties.keys())
kwargs = {k: v for k, v in want.items() if k in props}
dropped = sorted(set(want) - set(kwargs))
if dropped:
    print(f"[gate0] glTF exporter in this Blender has no {dropped}; using its defaults")
report["gltf_export_args"] = dict(used=sorted(kwargs), dropped=dropped)
bpy.ops.export_scene.gltf(**kwargs)
doc = json.loads(gltf.read_text())
report["gltf"] = dict(path=str(gltf), bytes=gltf.stat().st_size,
                      meshes=len(doc.get("meshes", [])), nodes=len(doc.get("nodes", [])),
                      materials=[m.get("name") for m in doc.get("materials", [])],
                      images=[i.get("uri") for i in doc.get("images", [])],
                      texcoord_sets=sorted({k for m in doc.get("meshes", []) for p in m["primitives"]
                                            for k in p["attributes"] if k.startswith("TEXCOORD")}),
                      emissive_texcoord=[m.get("emissiveTexture", {}).get("texCoord", 0)
                                         for m in doc.get("materials", []) if "emissiveTexture" in m],
                      total_tris=sum(a["tris"] for a in assets.values()))
assert "TEXCOORD_1" in report["gltf"]["texcoord_sets"], \
    f"UV2 did not reach the glTF: {report['gltf']['texcoord_sets']}"
(g0.OUT / "gltf_export.json").write_text(json.dumps(dict(assets=assets, **report), indent=1) + "\n")
g0.manifest_merge(assets=assets, gltf=report["gltf"] | dict(
    lightmap_slot="emissiveTexture (texCoord 1)",
    viewer_action="set material.emissive = 0x000000, material.lightMap = material.emissiveMap "
                  "(channel 1), decode RGBM8 with the range in textures.<key>.rgbm_range, "
                  "lightMapIntensity 1.0, and make the sun DirectionalLight specular-only"))
step.done(gltf, tris=report["gltf"]["total_tris"])
print("[gate0] gltf_export done:", report["gltf"]["texcoord_sets"], report["gltf"]["materials"])
