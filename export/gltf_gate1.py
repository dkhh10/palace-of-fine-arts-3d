"""Gate 1 step 5a: write one glTF per class from gate1_set.blend (arch / orn / env / ground).

    scripts/blender_run.sh 900 -- --background export/out/gate1/gate1_set.blend --python export/gltf_gate1.py

Materials at Gate 1 are the neutral greys the export set carries, plus - for every ORN prototype whose bake
queue job finished - the hi->lo tangent normal map and the AO map. The AO rides in glTF's own occlusionTexture
(UV1): the Blender exporter reads it from a node group literally named "glTF Material Output" with an
"Occlusion" input, which is the only way to write that slot from a Principled tree.

The four files are separate so the viewer can stream them by class (arch and ground first, orn and env after).
`export/gltf_pack.sh --gate1` turns the PNGs into KTX2 and each .gltf into a meshopt .glb.
"""
import bpy
import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gate0_common as g0  # noqa: E402
import gate1_common as g1  # noqa: E402

g1.ensure_dirs()
scene = bpy.context.scene
report = {"classes": {}}
jobs = json.loads((g1.OUT / "bake_jobs.json").read_text())["jobs"]

# clear tex_gltf so a stale PNG from an earlier run is never fed to toktx (Gate 0 review finding 10)
texdir = g1.OUT / "tex_gltf"
for f in texdir.glob("*"):
    f.unlink()


def occlusion_group():
    """The node group the glTF exporter recognises as the occlusion/ORM sink."""
    name = "glTF Material Output"
    grp = bpy.data.node_groups.get(name)
    if grp is None:
        grp = bpy.data.node_groups.new(name, "ShaderNodeTree")
        grp.interface.new_socket("Occlusion", in_out="INPUT", socket_type="NodeSocketFloat")
        grp.nodes.new("NodeGroupInput")
    return grp


def load_img(path, colorspace):
    im = bpy.data.images.load(str(path), check_existing=True)
    im.colorspace_settings.name = colorspace
    return im


# ---------------------------------------------------------------- ORN materials get normal + AO
step = g0.Step("gltf_gate1:materials")
grp = occlusion_group()
orn_mat_report = {}
for job in jobs:
    me = bpy.data.meshes.get(job["lo"])
    if me is None or not me.materials:
        continue
    mat = me.materials[0]
    nrm_p = g1.TEX / os.path.basename(job["normal"])
    ao_p = g1.TEX / os.path.basename(job["ao"])
    if not nrm_p.exists() or not ao_p.exists():
        orn_mat_report[job["id"]] = "bake missing - exported grey"
        continue
    nt = mat.node_tree
    bsdf = next((n for n in nt.nodes if n.bl_idname == "ShaderNodeBsdfPrincipled"), None)
    if bsdf is None:
        continue
    uv = nt.nodes.new("ShaderNodeUVMap")
    uv.uv_map = g1.UV1
    n_img = nt.nodes.new("ShaderNodeTexImage")
    n_img.image = load_img(nrm_p, "Non-Color")
    nt.links.new(uv.outputs["UV"], n_img.inputs["Vector"])
    nmap = nt.nodes.new("ShaderNodeNormalMap")
    nmap.uv_map = g1.UV1
    nt.links.new(n_img.outputs["Color"], nmap.inputs["Color"])
    nt.links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])
    a_img = nt.nodes.new("ShaderNodeTexImage")
    a_img.image = load_img(ao_p, "Non-Color")
    nt.links.new(uv.outputs["UV"], a_img.inputs["Vector"])
    gnode = nt.nodes.new("ShaderNodeGroup")
    gnode.node_tree = grp
    nt.links.new(a_img.outputs["Color"], gnode.inputs["Occlusion"])
    orn_mat_report[job["id"]] = dict(normal=nrm_p.name, ao=ao_p.name, size=job["size"])
report["orn_materials"] = orn_mat_report
step.done(**{"with_maps": sum(1 for v in orn_mat_report.values() if isinstance(v, dict)),
             "grey_only": sum(1 for v in orn_mat_report.values() if not isinstance(v, dict))})

# ---------------------------------------------------------------- UV1 probe on the grey materials
# Blender's glTF exporter only writes a TEXCOORD_n attribute for a UV layer some texture actually uses. At
# Gate 1 the grey materials carry no texture, so UV1 would not reach the glb at all. Wire an 8x8 mid-grey
# base-colour image on UV1 to every grey material: the glb then has the same attribute layout Gate 2 will
# produce, and the viewer sees the same neutral grey. UV2 (TEXCOORD_1) deliberately stays out until Gate 3
# attaches the lightmap - that is the same exporter rule, recorded per class in `texcoord_sets` below.
step = g0.Step("gltf_gate1:uv1_probe")
probe_path = g1.TEX / "uv1_probe_grey.png"
if not probe_path.exists():
    pim = bpy.data.images.new("uv1_probe_grey", 8, 8, alpha=False, float_buffer=False, is_data=False)
    pim.generated_color = (0.5, 0.5, 0.5, 1.0)
    pim.filepath_raw = str(probe_path)
    pim.file_format = "PNG"
    pim.save()
# ---------------------------------------------------------------- Gate 2 hand-off: the backdrop UV1 layer
# The ten merged backdrop meshes shipped Gate 1 with no UV layer at all (they are flat-colour city blocks and
# were never baked). The Gate 2 bake generated one and wrote the exact loop UVs to
# export/out/gate2/backdrop_uv1.npz (float32 [loops, 2] per Gate 1 mesh name, branch phase6-bake a9794e8).
# Read it back here so env.glb carries the SAME layer as TEXCOORD_0 and the Gate 2 textures land where the
# bake put them. Loop counts are asserted per mesh: a mismatch means the two gates are looking at different
# geometry and nothing may ship.
step = g0.Step("gltf_gate1:backdrop_uv1")
import numpy as np  # noqa: E402
npz_path = g1.MAIN_ROOT / "export" / "out" / "gate2" / "backdrop_uv1.npz"
backdrop_uv = {}
if npz_path.exists():
    z = np.load(str(npz_path))
    for mn in z.files:
        me = bpy.data.meshes.get(mn)
        assert me is not None, f"{npz_path.name} names {mn}, which is not in the Gate 1 export set"
        arr = np.asarray(z[mn], dtype=np.float32)
        assert arr.shape == (len(me.loops), 2), \
            f"{mn}: Gate 2 wrote {arr.shape[0]} loop UVs, the Gate 1 mesh has {len(me.loops)} loops"
        lay = me.uv_layers.get(g1.UV1) or me.uv_layers.new(name=g1.UV1)
        try:
            lay.uv.foreach_set("vector", arr.reshape(-1))
        except (AttributeError, TypeError):
            lay.data.foreach_set("uv", arr.reshape(-1))
        lay.active_render = True
        me.uv_layers.active = lay
        me.update()
        backdrop_uv[mn] = dict(loops=int(arr.shape[0]),
                               u=[round(float(arr[:, 0].min()), 5), round(float(arr[:, 0].max()), 5)],
                               v=[round(float(arr[:, 1].min()), 5), round(float(arr[:, 1].max()), 5)])
report["backdrop_uv1"] = dict(source=str(npz_path), meshes=backdrop_uv, count=len(backdrop_uv))
step.done(meshes=len(backdrop_uv), source=npz_path.name if npz_path.exists() else "MISSING")

# ---------------------------------------------------------------- Gate 3 hand-off 1: the re-laid UV2
# Gate 1's UV2 on seven merged masses is margin-dominated (the south colonnade packs 0.0095 of its 2K map =
# 38 cm per lightmap texel, which cannot carry a shadow edge). Gate 3 re-unwrapped those seven IN ITS OWN BAKE
# BLEND, baked every lightmap against the new layout and handed the exact loop UVs over in
# export/out/gate3/lightmap_uv2.npz (float32 [loops, 2] per Gate 1 MESH name) - the same hand-off shape as
# Gate 2's backdrop_uv1.npz. Load it onto the SAME UV2 layer, never a third one: TEXCOORD_n follows the UV
# layer order, so a third layer would ship as TEXCOORD_2 and the lightmap would land on the wrong set. Loop
# counts are asserted per mesh; a mismatch means the two gates are looking at different geometry and the
# export stops rather than shipping a lightmap on a layout it was not baked against.
step = g0.Step("gltf_gate1:gate3_uv2")
G3 = g1.MAIN_ROOT / "export" / "out" / "gate3"


def uv_array(me, layer):
    arr = np.empty(len(me.loops) * 2, dtype=np.float32)
    try:
        layer.uv.foreach_get("vector", arr)
    except (AttributeError, TypeError):
        layer.data.foreach_get("uv", arr)
    return arr.reshape(-1, 2)


def uv_set(me, layer, arr):
    try:
        layer.uv.foreach_set("vector", arr.reshape(-1))
    except (AttributeError, TypeError):
        layer.data.foreach_set("uv", arr.reshape(-1))


def uv_area_fraction(me, layer):
    """Island-area fraction of the unit square: sum |UV triangle area| over the mesh's triangles. This is the
    bake's `uv2_coverage` / `lightmap_assets[*].uv2_coverage` metric, and is what cm-per-texel is derived
    from; it counts overlap twice, which is correct for a lightmap (an overlapping island is a bake defect)."""
    if hasattr(me, "calc_loop_triangles"):
        me.calc_loop_triangles()
    n = len(me.loop_triangles)
    if n == 0:
        return 0.0
    tl = np.empty(n * 3, dtype=np.int32)
    me.loop_triangles.foreach_get("loops", tl)
    t = uv_array(me, layer)[tl].reshape(-1, 3, 2)
    a, b, c = t[:, 0], t[:, 1], t[:, 2]
    cross = (b[:, 0] - a[:, 0]) * (c[:, 1] - a[:, 1]) - (c[:, 0] - a[:, 0]) * (b[:, 1] - a[:, 1])
    return float(np.abs(cross).sum() * 0.5)


uv2_npz = G3 / "lightmap_uv2.npz"
uv2_relay = {}
if uv2_npz.exists():
    z2 = np.load(str(uv2_npz))
    for mn in z2.files:
        me = bpy.data.meshes.get(mn)
        assert me is not None, f"{uv2_npz.name} names {mn}, which is not in the Gate 1 export set"
        arr = np.asarray(z2[mn], dtype=np.float32)
        assert arr.shape == (len(me.loops), 2), \
            f"{mn}: Gate 3 wrote {arr.shape[0]} loop UVs, the Gate 1 mesh has {len(me.loops)} loops"
        lay = me.uv_layers.get(g1.UV2)
        assert lay is not None, f"{mn} has no {g1.UV2} layer to relay the Gate 3 layout onto"
        idx = list(me.uv_layers.keys()).index(g1.UV2)
        assert idx == 1, (f"{mn}: {g1.UV2} is UV layer {idx}; it must be the second layer or it will not ship "
                          f"as TEXCOORD_1 ({list(me.uv_layers.keys())})")
        old = uv_array(me, lay).copy()
        before = uv_area_fraction(me, lay)
        uv_set(me, lay, arr)
        me.update()
        after = uv_area_fraction(me, lay)
        delta = float(np.abs(uv_array(me, lay) - old).max())
        assert delta > 1e-5, f"{mn}: the Gate 3 UV2 is identical to the Gate 1 layer (max delta {delta})"
        uv2_relay[mn] = dict(loops=int(arr.shape[0]), uv_layer_index=idx,
                             coverage_gate1=round(before, 5), coverage_gate3=round(after, 5),
                             gain=round(after / max(before, 1e-9), 2), max_uv_delta=round(delta, 5),
                             u=[round(float(arr[:, 0].min()), 5), round(float(arr[:, 0].max()), 5)],
                             v=[round(float(arr[:, 1].min()), 5), round(float(arr[:, 1].max()), 5)])
        assert after > before, f"{mn}: the Gate 3 UV2 packs {after:.5f}, worse than Gate 1's {before:.5f}"
report["gate3_uv2"] = dict(source=str(uv2_npz), meshes=uv2_relay, count=len(uv2_relay))
step.done(meshes=len(uv2_relay),
          worst_coverage=min([v["coverage_gate3"] for v in uv2_relay.values()], default=None))

# ---------------------------------------------------------------- Gate 3 hand-off 2: near-tree COLOR_0
# The 20 near trees have no UV2 that could carry a lightmap (0.07-0.19 m per vertex is finer than their leaf
# cards, so Gate 3 baked them to VERTEX_COLORS). out/gate3/vertex_irradiance.npz is uint8 per vertex per mesh
# and is ALREADY the gamma-2 code the manifest declares: irradiance/pi = (code/255)^2 * range, range = 64
# (`lightmaps.vertex_irradiance.encode/range`). So COLOR_0 carries code/255 - a value in [0,1] that gltfpack's
# default 8-bit colour quantisation reproduces exactly - and the viewer decodes c*c*range*lightmap_scale.
# FLOAT_COLOR/POINT is used deliberately: a BYTE_COLOR attribute is sRGB in Blender and the exporter would
# linearise it, which would silently change every value. Vertex counts are asserted per mesh.
step = g0.Step("gltf_gate1:gate3_color0")
vi_npz = G3 / "vertex_irradiance.npz"
VI_RANGE = 64.0
vi_report = {}
vi_skip = None
if vi_npz.exists():
    z3 = np.load(str(vi_npz))
    # The Gate 3 code review (docs/reviews/phase6_bake_gate3_review.md, findings 3-4) found the first
    # vertex_irradiance.npz shipped as uint8 gamma-2 codes at ONE shared range of 64, not the float32
    # scene-linear per mesh the manifest and the README promise, and the bake is re-writing it. The export
    # refuses to encode COLOR_0 from anything but the float32 file: the encoding that ships depends on the
    # real per-mesh range, and a wrong one is invisible in the glb and wrong in every frame.
    dts = sorted({str(np.asarray(z3[f]).dtype) for f in z3.files})
    if dts != ["float32"]:
        vi_skip = (f"vertex_irradiance.npz is {dts}, not float32 scene-linear (Gate 3 review findings 3-4): "
                   f"COLOR_0 is NOT exported and lightmaps.vertex_irradiance.in_glb stays false")
        print("[gate1] gate3_color0 SKIPPED - " + vi_skip)
        z3 = {"files": []}
        z3 = type("Empty", (), {"files": []})()
    for mn in z3.files:
        me = bpy.data.meshes.get(mn)
        assert me is not None, f"{vi_npz.name} names {mn}, which is not in the Gate 1 export set"
        codes = np.asarray(z3[mn])
        assert codes.dtype == np.uint8, f"{mn}: vertex irradiance is {codes.dtype}, the gamma2 codes are uint8"
        assert codes.shape == (len(me.vertices), 3), \
            f"{mn}: Gate 3 wrote {codes.shape[0]} vertex colours, the Gate 1 mesh has {len(me.vertices)} verts"
        pre = [a.name for a in me.color_attributes]
        assert not pre, f"{mn} already carries colour attributes {pre}; COLOR_0 would not be the irradiance"
        ca = me.color_attributes.new(name="irradiance", type="FLOAT_COLOR", domain="POINT")
        rgba = np.ones((len(me.vertices), 4), dtype=np.float32)
        rgba[:, :3] = codes.astype(np.float32) / 255.0
        ca.data.foreach_set("color", rgba.reshape(-1))
        for attr in ("active_color_index", "render_color_index"):
            try:
                setattr(me.color_attributes, attr, 0)
            except (AttributeError, TypeError):
                pass
        me.update()
        lin = (codes.astype(np.float64) / 255.0) ** 2 * VI_RANGE
        vi_report[mn] = dict(verts=int(codes.shape[0]), attribute=ca.name, domain="POINT", type="FLOAT_COLOR",
                             encode="gamma2", range=VI_RANGE,
                             code_mean=round(float(codes.mean()), 4), code_max=int(codes.max()),
                             color0_mean=round(float((codes / 255.0).mean()), 6),
                             linear_mean=round(float(lin.mean()), 6), linear_max=round(float(lin.max()), 4))
# Any OTHER mesh carrying colour attributes would also reach the glb now that the pack keeps source
# attributes (-kv), and standard glTF multiplies COLOR_0 into the base colour. On the ORN prototypes that
# attribute is `cavity` (scripts/orn_lib.py vertex_cavity): the ornament material reads it for recess dust and
# the Gate 2 albedo bake ALREADY contains it, so shipping it as COLOR_0 would apply the dust twice. The lead's
# call (docs/decisions.md 2026-09-16): strip colour attributes from the export copies - never from the source
# blend, and this script only ever reads gate1_set.blend - so orn.glb can be packed with -kv for its
# TEXCOORD_1 and carry no COLOR_0 at all. Only the near-tree irradiance attribute this script just created
# survives.
stripped = {}
for me in bpy.data.meshes:
    if me.name in vi_report or not me.color_attributes:
        continue
    names = [a.name for a in me.color_attributes]
    for n in names:
        me.color_attributes.remove(me.color_attributes[n])
    stripped[me.name] = names
other_colour = sorted(me.name for me in bpy.data.meshes
                      if me.color_attributes and me.name not in vi_report)
assert not other_colour, f"colour attributes survived the strip on {other_colour[:6]}"
report["gate3_color0"] = dict(source=str(vi_npz), meshes=vi_report, count=len(vi_report), skipped=vi_skip,
                              other_meshes_with_colour_attributes=len(other_colour),
                              stripped_colour_attributes={k: v for k, v in list(stripped.items())[:8]},
                              stripped_count=len(stripped),
                              stripped_note="ORN `cavity` (vertex_cavity) and any other source colour "
                                            "attribute: already inside the Gate 2 albedo bake, removed from "
                                            "the export copies only (docs/decisions.md 2026-09-16)",
                              note="COLOR_0 = gamma2 code/255; irradiance = c*c*64*lightmap_scale. Standard "
                                   "glTF multiplies COLOR_0 into base colour: the viewer must consume it as "
                                   "irradiance (manifest lightmaps.vertex_irradiance), not as a tint.")
step.done(meshes=len(vi_report), other_meshes_with_colour=len(other_colour))

probe = load_img(probe_path, "sRGB")
# QA round 11 blocker 1: ten backdrop meshes have NO UV layer (they are merged flat-colour city blocks and are
# never baked), and attaching the probe to their material made the exporter write
# baseColorTexture.texCoord = -1. three.js compiles that into `uv18446744073709552000`, the program fails to
# link, and all ten materials - 151 737 placed triangles, the whole backdrop - draw at no station. A material
# only gets the probe when EVERY mesh that uses it has UV1; the rest keep a flat baseColorFactor.
mats_uvless = set()
for mn, m in json.loads((g1.OUT / "export_set.json").read_text())["meshes"].items():
    me = bpy.data.meshes.get(mn)
    if me is None:
        continue
    if g1.UV1 not in me.uv_layers:
        mats_uvless.add(m["material"])
n_probe = 0
for mat in bpy.data.materials:
    if not mat.name.startswith("MAT_EXP_") or not mat.use_nodes:
        continue
    if mat.name in mats_uvless:
        continue
    nt = mat.node_tree
    bsdf = next((n for n in nt.nodes if n.bl_idname == "ShaderNodeBsdfPrincipled"), None)
    if bsdf is None or bsdf.inputs["Base Color"].is_linked:
        continue
    uvn = nt.nodes.new("ShaderNodeUVMap")
    uvn.uv_map = g1.UV1
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = probe
    nt.links.new(uvn.outputs["UV"], tex.inputs["Vector"])
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    n_probe += 1
report["uv1_probe"] = dict(image=probe_path.name, materials=n_probe,
                           skipped_uvless_materials=sorted(mats_uvless),
                           note="8x8 mid-grey on UV1 so TEXCOORD_0 reaches every glb; UV2 appears at Gate 3 "
                                "with the lightmap, per the exporter's use-a-texture rule")
step.done(probe_path, materials=n_probe)

# ---------------------------------------------------------------- the four class selections
GROUND_KINDS = {"ground"}
sets = {"arch": [], "orn": [], "env": [], "ground": []}
setjson = json.loads((g1.OUT / "export_set.json").read_text())
for name, a in setjson["assets"].items():
    ob = bpy.data.objects.get(name)
    if ob is None:
        continue
    if a["cls"] == "ARCH":
        sets["arch"].append(ob)
    elif a["cls"] == "ORN":
        sets["orn"].append(ob)
    elif a.get("kind") in GROUND_KINDS:
        sets["ground"].append(ob)
    else:
        sets["env"].append(ob)

want = dict(export_format="GLTF_SEPARATE", use_selection=True, export_yup=True, export_apply=True,
            export_tangents=True, export_normals=True, export_texcoords=True, export_materials="EXPORT",
            export_image_format="AUTO", export_keep_originals=False, export_cameras=False,
            export_lights=False, export_extras=False, export_animations=False, export_skins=False,
            export_morph=False, export_texture_dir="tex_gltf",
            # Gate 3: the near trees' COLOR_0. True is already the exporter's default (orn.gltf carries the
            # ORN meshes' COLOR_0/COLOR_1 with these same args), stated explicitly so the hand-off does not
            # depend on a default: "export all vertex colours, even if no material uses them".
            export_all_vertex_colors=True)
rna = bpy.ops.export_scene.gltf.get_rna_type().properties
props = set(rna.keys())
base_kwargs = {k: v for k, v in want.items() if k in props}
report["gltf_export_args"] = dict(
    used=sorted(base_kwargs), dropped=sorted(set(want) - set(base_kwargs)),
    vertex_colour_rna={k: str(getattr(rna[k], "default", None)) for k in
                       ("export_vertex_color", "export_all_vertex_colors", "export_vertex_color_when_no_material")
                       if k in props})

for cls, objs in sets.items():
    step = g0.Step(f"gltf_gate1:{cls}")
    for o in bpy.context.selected_objects:
        o.select_set(False)
    for o in objs:
        o.hide_viewport = False
        o.hide_render = False
        o.select_set(True)
    if not objs:
        continue
    bpy.context.view_layer.objects.active = objs[0]
    path = g1.OUT / f"{cls}.gltf"
    bpy.ops.export_scene.gltf(filepath=str(path), **base_kwargs)
    doc = json.loads(path.read_text())
    tris = sum(setjson["assets"][o.name]["tris"] for o in objs if o.name in setjson["assets"])
    report["classes"][cls] = dict(path=path.name, bytes=path.stat().st_size, objects=len(objs),
                                  placed_tris=tris, meshes=len(doc.get("meshes", [])),
                                  nodes=len(doc.get("nodes", [])),
                                  materials=len(doc.get("materials", [])),
                                  images=[i.get("uri") for i in doc.get("images", [])],
                                  texcoord_sets=sorted({k for m in doc.get("meshes", [])
                                                        for p in m["primitives"] for k in p["attributes"]
                                                        if k.startswith("TEXCOORD")}))
    # which MESH carries which attribute, by name, while the names still exist (gltfpack drops them). This is
    # what export/gate3_relay_check.py and export/verify_glb.py test the packed glb against.
    attr_meshes = {}
    for m in doc.get("meshes", []):
        for p in m["primitives"]:
            for k in p["attributes"]:
                attr_meshes.setdefault(k, set()).add(m.get("name"))
    report["classes"][cls]["attribute_meshes"] = {k: len(v) for k, v in sorted(attr_meshes.items())}
    report["classes"][cls]["color0_meshes"] = sorted(x for x in attr_meshes.get("COLOR_0", set()) if x)
    report["classes"][cls]["texcoord1_meshes"] = sorted(x for x in attr_meshes.get("TEXCOORD_1", set()) if x)
    report["classes"][cls]["primitives"] = sum(len(m["primitives"]) for m in doc.get("meshes", []))
    report["classes"][cls]["color0_primitives"] = sum(
        1 for m in doc.get("meshes", []) for p in m["primitives"] if "COLOR_0" in p["attributes"])
    report["classes"][cls]["texcoord1_primitives"] = sum(
        1 for m in doc.get("meshes", []) for p in m["primitives"] if "TEXCOORD_1" in p["attributes"])
    # QA round 11b: the 127 ENV_treeboard_* quads shipped OPAQUE, so a viewer that did not know the material
    # name drew 16-26 % of every frame as grey slabs. Make the file honest on its own: MASK with cutoff 1.0
    # cuts every texel until the Gate 3 impostor atlas supplies an alpha. The material name stays
    # MAT_EXP_treeboard so the viewer's existing name test keeps working.
    patched = []
    for m in doc.get("materials", []):
        if m.get("name", "").startswith("MAT_EXP_treeboard"):
            m["alphaMode"] = "MASK"
            m["alphaCutoff"] = 1.0
            # the base-colour alpha has to BE 0, not just be declared cut: with an alpha of 1 gltfpack reasons
            # "MASK over an always-opaque material == OPAQUE" and drops alphaMode again (measured at cutoff
            # 1.0, 0.99 and 0.5). alpha 0 < cutoff 1.0 discards every fragment, which is the Gate 1 contract
            # until the Gate 3 impostor atlas supplies a real alpha.
            pbr = m.setdefault("pbrMetallicRoughness", {})
            bcf = list(pbr.get("baseColorFactor", [1.0, 1.0, 1.0, 1.0]))[:3] + [0.0]
            pbr["baseColorFactor"] = bcf
            patched.append(m["name"])
    if patched:
        path.write_text(json.dumps(doc))
        doc = json.loads(path.read_text())
        report["classes"].setdefault(cls, {})
    report.setdefault("treeboard_alpha_mask", []).extend(patched)
    # QA-11c-1: 1379 shrub nodes were written with NO transform and their meshes are local, so the whole
    # planting drew stacked at the origin. A mesh node may legitimately have no transform only when its
    # Blender object's transform is identity (the merged ARCH/ENV groups carry world-space geometry).
    identity_objs = {o.name for o in objs if o.matrix_world.translation.length < 1e-6
                     and (o.matrix_world.to_3x3() - __import__("mathutils").Matrix.Identity(3)).median_scale < 1e-6}
    mesh_nodes = [nd for nd in doc.get("nodes", []) if "mesh" in nd]
    untransformed = [nd.get("name", "?") for nd in mesh_nodes
                     if "matrix" not in nd and not any(k in nd for k in ("translation", "rotation", "scale"))]
    report["classes"][cls]["materials_expected"] = sorted(
        {sl.name for o in objs for sl in o.data.materials if sl})
    report["classes"][cls]["mesh_nodes"] = len(mesh_nodes)
    report["classes"][cls]["untransformed_nodes"] = len(untransformed)
    report["classes"][cls]["identity_objects"] = len(identity_objs)
    assert len(mesh_nodes) == len(objs), \
        f"{cls}.gltf has {len(mesh_nodes)} mesh nodes for {len(objs)} exported objects"
    assert len(untransformed) <= len(identity_objs), (
        f"{cls}.gltf: {len(untransformed)} mesh nodes carry no transform but only {len(identity_objs)} of the "
        f"{len(objs)} objects have an identity transform - e.g. {untransformed[:6]}")
    bad = []
    for mi, m in enumerate(doc.get("materials", [])):
        for slot in ("baseColorTexture", "metallicRoughnessTexture"):
            t = (m.get("pbrMetallicRoughness") or {}).get(slot)
            if t is not None and int(t.get("texCoord", 0)) < 0:
                bad.append((m.get("name", mi), slot, t.get("texCoord")))
        for slot in ("normalTexture", "occlusionTexture", "emissiveTexture"):
            t = m.get(slot)
            if t is not None and int(t.get("texCoord", 0)) < 0:
                bad.append((m.get("name", mi), slot, t.get("texCoord")))
    report["classes"][cls]["invalid_texcoords"] = bad
    assert not bad, (f"{cls}.gltf has materials whose texture texCoord is negative (three.js compiles that "
                     f"into an undeclared uv attribute and the whole program fails to link): {bad}")
    step.done(path, objects=len(objs), tris=tris, meshes=len(doc.get("meshes", [])))

# second assertion (QA-11c-1): nothing may sit stacked at the world origin unless the export set says so
near = {}
for name, a in setjson["assets"].items():
    loc = a.get("location_blender")
    if loc and (loc[0] ** 2 + loc[1] ** 2 + loc[2] ** 2) ** 0.5 < 1.0:
        near.setdefault(a["cls"], []).append(name)
report["near_origin"] = {k: len(v) for k, v in near.items()}
for cls_, names_ in near.items():
    assert len(names_) <= 1, (f"{len(names_)} {cls_} objects sit within 1 m of the world origin: {names_[:8]}")

assert report.get("treeboard_alpha_mask"), \
    "MAT_EXP_treeboard never reached a glTF: the far-tree boards would ship opaque again"

# ---------------------------------------------------------------- Gate 3: the two hand-offs reached a glTF
uv2_written = {m for c in report["classes"].values() for m in c.get("texcoord1_meshes", [])}
missing_uv2 = sorted(set(uv2_relay) - uv2_written)
assert not missing_uv2, (f"the Gate 3 UV2 was loaded onto {missing_uv2} but no class glTF carries their "
                         f"TEXCOORD_1 - the lightmap would have no UV set to land on")
col_written = {m for c in report["classes"].values() for m in c.get("color0_meshes", [])}
missing_col = sorted(set(vi_report) - col_written)
assert not missing_col, (f"{len(missing_col)} near-tree meshes carry the irradiance colour attribute but no "
                         f"class glTF wrote their COLOR_0 (exporter args {report['gltf_export_args']}): "
                         f"{missing_col[:6]}")
report["gate3_in_gltf"] = dict(uv2_meshes=sorted(uv2_relay), color0_meshes=sorted(vi_report),
                               color0_unexpected=sorted(col_written - set(vi_report)))

# ---------------------------------------------------------------- UV1 atlas check
# The UV1 atlas was packed by one multi-object smart project per group. If that had failed, every mesh in the
# group would sit on the full [0,1] square and the Gate 2 bake would overwrite itself. Measure it: per group,
# the per-mesh UV1 bounding box and the worst pairwise box overlap.
step = g0.Step("gltf_gate1:uv1_atlas")
groups = {}
for mn, m in setjson["meshes"].items():
    me = bpy.data.meshes.get(mn)
    if me is None or g1.UV1 not in me.uv_layers:
        continue
    if m["cls"] not in ("ARCH", "ORN") and m.get("kind") != "ground":
        continue
    uv = me.uv_layers[g1.UV1].uv
    us = [uv[i].vector[0] for i in range(len(uv))]
    vs = [uv[i].vector[1] for i in range(len(uv))]
    if not us:
        continue
    groups.setdefault(m["material"], []).append(
        (mn, [round(min(us), 4), round(min(vs), 4), round(max(us), 4), round(max(vs), 4)]))
atlas = {}
for mat, rows in sorted(groups.items()):
    worst = 0.0
    for i in range(len(rows)):
        for j in range(i + 1, len(rows)):
            a1, b1 = rows[i][1], rows[j][1]
            ox = max(0.0, min(a1[2], b1[2]) - max(a1[0], b1[0]))
            oy = max(0.0, min(a1[3], b1[3]) - max(a1[1], b1[1]))
            area = max(1e-9, min((a1[2] - a1[0]) * (a1[3] - a1[1]), (b1[2] - b1[0]) * (b1[3] - b1[1])))
            worst = max(worst, ox * oy / area)
    atlas[mat] = dict(meshes=len(rows), worst_box_overlap_frac=round(worst, 4),
                      boxes={r[0]: r[1] for r in rows})
report["uv1_atlas"] = atlas
report["uv1_atlas_worst"] = sorted(((v["worst_box_overlap_frac"], k) for k, v in atlas.items()),
                                   reverse=True)[:5]
step.done(groups=len(atlas), worst=report["uv1_atlas_worst"][:3])

# ---------------------------------------------------------------- draw calls inside the cam01 frustum
step = g0.Step("gltf_gate1:cam01_frustum")
from mathutils import Vector  # noqa: E402
cam = bpy.data.objects[g0.HERO_CAM]
scene.camera = cam
dg = bpy.context.evaluated_depsgraph_get()
from bpy_extras.object_utils import world_to_camera_view  # noqa: E402


def visible(ob):
    """Conservative bbox test in normalised camera space (world_to_camera_view: u,v in [0,1] inside the frame,
    z = distance in front). Reject only when every corner fails the SAME test."""
    cs = [world_to_camera_view(scene, cam, ob.matrix_world @ Vector(c)) for c in ob.bound_box]
    if all(c.z <= cam.data.clip_start for c in cs):
        return False
    if all(c.x < 0 for c in cs) or all(c.x > 1 for c in cs):
        return False
    if all(c.y < 0 for c in cs) or all(c.y > 1 for c in cs):
        return False
    return True


vis_batches, vis_objs, vis_tris = set(), 0, 0
for name, a in setjson["assets"].items():
    ob = bpy.data.objects.get(name)
    if ob is None or not visible(ob):
        continue
    vis_objs += 1
    vis_tris += a["tris"]
    for slot in (ob.data.materials or [None]):
        vis_batches.add((ob.data.name, slot.name if slot else "-"))
report["cam01_visible"] = dict(batches=len(vis_batches), objects=vis_objs, placed_tris=vis_tris,
                               camera=g0.HERO_CAM,
                               note="bounding-box test against the six camera planes; one batch per "
                                    "(mesh, material slot), which is what EXT_mesh_gpu_instancing draws")
step.done(batches=len(vis_batches), objects=vis_objs, tris=vis_tris)

(g1.OUT / "gltf_gate1.json").write_text(json.dumps(report, indent=1) + "\n")
print("[gate1] gltf per class:", json.dumps({k: (v["bytes"], v["meshes"], v["texcoord_sets"])
                                             for k, v in report["classes"].items()}))
