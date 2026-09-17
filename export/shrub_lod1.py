"""Phase 6c item E: the shrub/reed card meshes at LOD1, at the same placements as the LOD2 set
(25 of the 28 meshes and 1 376 of the 1 379 placements - see the skip below).

    scripts/blender_run.sh 900 -- --background master_delivery.blend --python export/shrub_lod1.py
    export/gltf_pack.sh --shrubs                       # -> out/gate1/env_shrubs.glb
    node web/tools/instance_rows.mjs export/out/gate1/env_shrubs.glb \\
         export/out/gate3/instance_rows_shrub_lod1.json
    PFA_ORDER_SET=shrub_lod1 python3 export/gate4_instance_order.py
    python3 export/verify_glb.py && python3 export/manifest_v4.py && export/sync_main.sh

CPU only: no render, no GPU. master_delivery.blend is opened read-only and never saved over.

WHY A SEPARATE GLB AND NOT `env.glb` (a deviation from the brief - lead, please read). Putting the LOD1
meshes *inside* env.glb means re-running `gate1_set.py`, and that script rebuilds the whole export set
including the **UV1 atlases** that every Gate 2 PBR bake and every Gate 3 lightmap is pinned to
(export/README.md QA-12-1, items 14-15, 28). A re-pack of env.glb also invalidates
`out/gate3/instance_order.json` and forces arch/orn/ground back through gltfpack. None of that risk buys
anything the viewer can see: `env_shrubs.glb` carries the same meshes at the same transforms, loads
lazily beside `env_trees.glb`, and its rows join to the SAME `instance_irradiance.json` placements - which is
exactly the brief's "extend the join so both LODs share the placement's irradiance", done by pointing both
LODs' row orders at one irradiance file rather than by widening one glb.

The placements are not re-derived: they are the `placement_from` LOD1 OBJECTS the Gate 1 export already used
for the LOD2 cards (`export_set.json` assets, kind `shrub`), with the same full TRS decomposition
gate1_set.py applies, and every one of them is asserted against the Gate 1 asset's recorded world bbox
centre.
"""
import json
import os
import sys
import time
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gate0_common as g0  # noqa: E402
import gate1_common as g1  # noqa: E402
import read_alpha  # noqa: E402

SCHEMA = "pfa-phase6c/shrub-lod1/1"
GLTF_NAME = "env_shrubs"
PLACE_TOL_M = 0.01       # against the Gate 1 asset's own `location_blender` bbox centre


def tris_of(me):
    return sum(len(p.vertices) - 2 for p in me.polygons)


def main():
    t0 = time.time()
    assert Path(bpy.data.filepath).name == "master_delivery.blend", \
        f"shrub_lod1.py must run on master_delivery.blend, not {bpy.data.filepath!r}"
    sp = next((q for q in (g1.OUT / "export_set.json",
                           g1.MAIN_ROOT / "export" / "out" / "gate1" / "export_set.json") if q.exists()), None)
    assert sp is not None, "export/out/gate1/export_set.json not found in this worktree or in MAIN"
    eset = json.loads(sp.read_text())
    g1.OUT.mkdir(parents=True, exist_ok=True)

    all_assets = {k: v for k, v in eset["assets"].items() if v.get("kind") == "shrub"}
    all_meshes = {k: v["placement_from"] for k, v in eset["meshes"].items() if v.get("kind") == "shrub"}
    assert len(all_meshes) == 28, f"{len(all_meshes)} shrub meshes in the Gate 1 set, expected 28"
    assert len(all_assets) == 1379, f"{len(all_assets)} shrub placements, expected 1379"
    # THREE of the 28 have no LOD1 at all: their `placement_from` mesh is itself a `_LOD2`
    # (EXPM_ENV_src_{maho2,pitto5,reed1}_LOD2, one placement each - the same three gltfpack merged inside
    # env.glb, export/README.md item 31). Re-exporting them here would ship a byte-for-byte copy of the card
    # env.glb already draws, and - because each is a lone one-placement mesh - gltfpack MERGES two of them
    # into a single node, which collapses two placements into ONE instance row and makes the per-placement
    # irradiance join unrecoverable (measured: 1 378 rows for 1 379 placements). They are skipped; those three
    # shrubs keep their env.glb card at every distance, which is the same geometry either way.
    lod1_of_mesh = {k: v for k, v in all_meshes.items() if v.endswith("_LOD1")}
    skipped = {k: v for k, v in all_meshes.items() if not v.endswith("_LOD1")}
    shrub_assets = {k: v for k, v in all_assets.items() if v["mesh"] in lod1_of_mesh}
    assert all(eset["meshes"][k]["placements"] == 1 for k in skipped), \
        f"a skipped shrub mesh has more than one placement: {skipped}"

    rep = dict(schema=SCHEMA, generated=time.strftime("%Y-%m-%dT%H:%M:%S"),
               generator="export/shrub_lod1.py", source_blend=bpy.data.filepath, export_set=str(sp),
               skipped_meshes={k: dict(placement_from=v, placements=eset["meshes"][k]["placements"],
                                       reason="no _LOD1 in the source: `placement_from` is itself a _LOD2, so "
                                              "a LOD1 copy would be the same card env.glb already draws, and a "
                                              "lone one-placement mesh is merged by gltfpack into another "
                                              "node, collapsing two placements into one instance row")
                               for k, v in skipped.items()},
               placements_without_lod1=sorted(set(all_assets) - set(shrub_assets)))
    exp = bpy.data.collections.new("EXP_SHRUB_LOD1")
    bpy.context.scene.collection.children.link(exp)

    # ---------------------------------------------------------------- the 28 LOD1 meshes
    step = g0.Step("shrub_lod1:meshes")
    meshes = {}
    for lod2_mesh, lod1_mesh in sorted(lod1_of_mesh.items()):
        src = bpy.data.meshes.get(lod1_mesh)
        assert src is not None, f"{lod2_mesh}: its placement_from mesh {lod1_mesh} is not in master_delivery"
        me = src.copy()                     # datablock copy: shrubs carry no modifiers (gate1_set.py, step 6)
        me.name = f"EXPM_{lod1_mesh}"
        co = np.array([list(v.co) for v in me.vertices], dtype=np.float64) if len(me.vertices) else \
            np.zeros((1, 3))
        meshes[lod2_mesh] = dict(
            lod1_mesh=lod1_mesh, mesh=me.name, tris=tris_of(me), verts=len(me.vertices),
            lod2_tris=eset["meshes"][lod2_mesh]["tris"],
            materials=[m.name if m else None for m in me.materials],
            uv_layers=[u.name for u in me.uv_layers],
            bbox_min=[round(float(v), 4) for v in co.min(axis=0)],
            bbox_max=[round(float(v), 4) for v in co.max(axis=0)],
            placements=0)
    step.done(meshes=len(meshes), tris=sum(v["tris"] for v in meshes.values()))

    # ---------------------------------------------------------------- the 1 379 placements
    step = g0.Step("shrub_lod1:placements")
    placements, worst = [], 0.0
    for name, a in sorted(shrub_assets.items()):
        src_ob = bpy.data.objects.get(a["placement_from"])
        assert src_ob is not None, f"{name}: placement source {a['placement_from']} is not in the blend"
        m = meshes[a["mesh"]]
        me = bpy.data.meshes[m["mesh"]]
        no = bpy.data.objects.new(a["placement_from"], me)
        loc, rot, scl = src_ob.matrix_world.decompose()
        no.rotation_mode = "QUATERNION"
        no.location, no.rotation_quaternion, no.scale = loc, rot, scl
        exp.objects.link(no)
        m["placements"] += 1
        placements.append(dict(object=no.name, lod2_object=name, mesh=me.name, lod2_mesh=a["mesh"],
                               loc=[round(float(v), 4) for v in loc]))
    bpy.context.view_layer.update()
    for pl, (name, a) in zip(placements, sorted(shrub_assets.items())):
        no = bpy.data.objects[pl["object"]]
        cs = [no.matrix_world @ Vector(c) for c in no.bound_box]
        ctr = sum(cs, Vector()) / 8.0
        # LOD1 and LOD2 are different meshes, so only the TRANSLATION is comparable, not the bbox centre;
        # the Gate 1 asset's own translation is what the instance join keys on.
        d = (no.matrix_world.translation - Vector(a["location_blender"])).length
        pl["bbox_centre"] = [round(v, 4) for v in ctr]
        pl["gate1_bbox_centre"] = a["location_blender"]
        pl["centre_delta_m"] = round(d, 4)
        worst = max(worst, (no.matrix_world.translation
                            - bpy.data.objects[a["placement_from"]].matrix_world.translation).length)
    assert worst < PLACE_TOL_M, f"worst placement error {worst:.5f} m"
    assert all(m["placements"] == eset["meshes"][k]["placements"] for k, m in meshes.items()), \
        "a LOD1 mesh got a different placement count than its LOD2 twin"
    lone = {k: m["placements"] for k, m in meshes.items() if m["placements"] < 2}
    assert not lone, (f"{lone} has a single placement: gltfpack merges lone one-placement meshes into another "
                      f"node and two placements then share one instance row, which the per-placement "
                      f"irradiance join cannot undo")
    step.done(placements=len(placements), worst_m=round(worst, 6))
    rep["meshes"] = meshes
    rep["placements"] = placements
    rep["placed_tris"] = sum(m["tris"] * m["placements"] for m in meshes.values())
    rep["placed_tris_lod2"] = sum(m["lod2_tris"] * m["placements"] for m in meshes.values())

    # ---------------------------------------------------------------- env_shrubs.gltf
    step = g0.Step("shrub_lod1:gltf")
    want = dict(export_format="GLTF_SEPARATE", use_selection=True, export_yup=True, export_apply=True,
                export_tangents=True, export_normals=True, export_texcoords=True, export_materials="EXPORT",
                export_image_format="AUTO", export_keep_originals=False, export_cameras=False,
                export_lights=False, export_extras=False, export_animations=False, export_skins=False,
                export_morph=False, export_texture_dir="tex_gltf", export_all_vertex_colors=True)
    props = set(bpy.ops.export_scene.gltf.get_rna_type().properties.keys())
    kwargs = {k: v for k, v in want.items() if k in props}
    for o in bpy.context.selected_objects:
        o.select_set(False)
    objs = sorted(exp.objects, key=lambda o: o.name)
    for o in objs:
        o.hide_viewport = o.hide_render = False
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    gltf_p = g1.OUT / f"{GLTF_NAME}.gltf"
    bpy.ops.export_scene.gltf(filepath=str(gltf_p), **kwargs)
    doc = json.loads(gltf_p.read_text())
    imgs = [i.get("uri") for i in doc.get("images", [])]
    texs = [t.get("source") for t in doc.get("textures", [])]
    alpha_mats, alpha_missing = {}, []
    for m in doc.get("materials", []):
        bct = (m.get("pbrMetallicRoughness") or {}).get("baseColorTexture")
        if bct is None or m.get("alphaMode"):
            continue
        uri = imgs[texs[bct["index"]]] if bct["index"] < len(texs) and texs[bct["index"]] is not None else None
        if not uri or not read_alpha.png_has_alpha(gltf_p.parent / uri):
            continue
        bm = bpy.data.materials.get(m.get("name", ""))
        cut, why = read_alpha.cut_chain(bm) if bm is not None else (None, "no such material in this blend")
        if cut is None:
            alpha_missing.append((m.get("name"), why))
            continue
        m["alphaMode"] = "MASK"
        m["alphaCutoff"] = cut
        alpha_mats[m.get("name")] = dict(cutoff=cut, texture=uri, reason=why)
    assert not alpha_missing, (f"{gltf_p.name}: {alpha_missing} have an alpha-carrying baseColorTexture and "
                               f"no recognised cut chain - a card that ships OPAQUE is a solid rectangle")
    if alpha_mats:
        gltf_p.write_text(json.dumps(doc))
        doc = json.loads(gltf_p.read_text())
    attr = {}
    for m_ in doc.get("meshes", []):
        for pr in m_["primitives"]:
            for k in pr["attributes"]:
                attr.setdefault(k, set()).add(m_.get("name"))
    rep["gltf"] = dict(path=gltf_p.name, bytes=gltf_p.stat().st_size, nodes=len(doc.get("nodes", [])),
                       meshes=len(doc.get("meshes", [])),
                       materials=[m.get("name") for m in doc.get("materials", [])],
                       images=imgs, attributes={k: len(v) for k, v in sorted(attr.items())},
                       color0_meshes=sorted(x for x in attr.get("COLOR_0", set()) if x),
                       alpha_mask_materials=alpha_mats,
                       alpha_mode_materials={m.get("name"): [m.get("alphaMode"), m.get("alphaCutoff")]
                                             for m in doc.get("materials", []) if m.get("alphaMode")},
                       placed_tris=rep["placed_tris"], unique_tris=sum(m["tris"] for m in meshes.values()))
    step.done(gltf_p, bytes=gltf_p.stat().st_size, nodes=len(doc.get("nodes", [])))
    rep["wall_s"] = round(time.time() - t0, 1)
    (g1.OUT / "shrub_lod1.json").write_text(json.dumps(rep, indent=1) + "\n")
    print(f"[shrub_lod1] {len(meshes)} meshes {min(m['tris'] for m in meshes.values())}-"
          f"{max(m['tris'] for m in meshes.values())} tris, {len(placements)} placements, "
          f"{rep['placed_tris']} placed tris against the LOD2 set's {rep['placed_tris_lod2']} "
          f"({rep['placed_tris']/max(rep['placed_tris_lod2'],1):.1f}x) -> {gltf_p.name}")


if __name__ == "__main__":
    main()
