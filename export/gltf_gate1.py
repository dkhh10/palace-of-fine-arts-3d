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
probe = load_img(probe_path, "sRGB")
n_probe = 0
for mat in bpy.data.materials:
    if not mat.name.startswith("MAT_EXP_") or not mat.use_nodes:
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
            export_morph=False, export_texture_dir="tex_gltf")
props = set(bpy.ops.export_scene.gltf.get_rna_type().properties.keys())
base_kwargs = {k: v for k, v in want.items() if k in props}
report["gltf_export_args"] = dict(used=sorted(base_kwargs), dropped=sorted(set(want) - set(base_kwargs)))

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
    step.done(path, objects=len(objs), tris=tris, meshes=len(doc.get("meshes", [])))

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
planes = []
mw = cam.matrix_world
frame = [mw @ v for v in cam.data.view_frame(scene=scene)]
origin = mw.translation
for i in range(4):
    a_, b_ = frame[i] - origin, frame[(i + 1) % 4] - origin
    planes.append((origin, b_.cross(a_).normalized()))
fwd = (mw.to_quaternion() @ Vector((0, 0, -1))).normalized()
planes.append((origin + fwd * cam.data.clip_start, fwd))
planes.append((origin + fwd * cam.data.clip_end, -fwd))


def visible(ob):
    cs = [ob.matrix_world @ Vector(c) for c in ob.bound_box]
    for p, n in planes:
        if all((c - p).dot(n) < 0 for c in cs):
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
