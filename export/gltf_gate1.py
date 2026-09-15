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

(g1.OUT / "gltf_gate1.json").write_text(json.dumps(report, indent=1) + "\n")
print("[gate1] gltf per class:", json.dumps({k: (v["bytes"], v["meshes"], v["texcoord_sets"])
                                             for k, v in report["classes"].items()}))
