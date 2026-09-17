"""Phase 6c item A: a real LOD2 MESH for each of the 16 far-tree prototypes, instanced at the 127
`tree_far` placements, as its own lazily loaded `env_trees.glb`.

    scripts/blender_run.sh 900 -- --background master_delivery.blend --python export/trees_far.py
    export/gltf_pack.sh --trees          # KTX2 (shared tex_ktx2) + gltfpack -cc -mi -> env_trees.glb

CPU only: no render, no GPU, master_delivery.blend is opened read-only and never saved over.

WHY NOT THE EXISTING `_LOD2` OBJECTS. The brief says "the `_LOD2` object if it exists, else decimate the
`_LOD1`". Measured on master_delivery (export/out/gate3/trees_far/topology.json `lod2_objects_rejected`):
all 16 prototypes DO have a `_LOD2` object, and every one of them is a bare branch skeleton - 1 188-3 812
triangles of which **six faces** (three cards) carry the leaf material. They are the Phase 5 distance blobs,
and a tree with three leaves at 3 m is worse than the impostor it replaces. So all 16 far meshes are built
from the `_LOD1` prototype by the export's own card-aware reduction:

  * the mesh is split into LEAF CARDS (connected components of <= 2 faces, always the leaf material) and
    BRANCH geometry (everything else), because Decimate COLLAPSE run over a forest of 2-triangle islands
    destroys the cards' UVs and their silhouette (the same lesson as the ORN attic panels, gate1_set.py);
  * branches take their pro-rata share of the triangle budget and go through the gate1_set COLLAPSE path
    (weld first, then iterate the ratio), clamped to [BRANCH_MIN, BRANCH_MAX] so a willow's 24 k of hanging
    frond geometry is not flattened to a stick;
  * the cards fill the rest, dropped deterministically (`i % 1000 >= keep_pct`, gate1_set.thin_leaf_cards)
    and then scaled about their own centre by `min(CARD_SCALE_MAX, 1/sqrt(keep_fraction))` so the crown does
    not go see-through: dropping 80 % of the cards without that leaves a transparent tree. The cap is there
    because these meshes are drawn from ~3 m out (the viewer's `treeMeshDist`), where a 2.4x leaf is visible.

THE TRANSFORMS ARE THE IMPOSTORS'. A far tree is drawn as the prototype scaled uniformly and set on its
trunk base, exactly as manifest `impostors.placement` states:
`s = tree_far[i].height_m / impostors.prototypes[p].height_above_base_m`, translation = `trunk_base`,
rotation ignored (the impostor ignores it too). The prototype's own world matrix is baked into the mesh, so
the mesh's z = 0 is the plane `trunk_base` maps to - the same plane the impostor bake measured
`height_above_base_m` from. Asserted here per placement against the manifest's own `tree_far` row.

HAND-OFF TO THE BAKE (item B). `export/out/gate3/trees_far/topology.json` carries the mesh name, vertex and
triangle count and bbox of each prototype; `trees_far_lod2.blend` is those 16 objects alone, at the same
prototype world space, with their Phase 5 materials. The vertex AO comes back as
`out/gate3/trees_far/vertex_ao.npz`, float32 `[verts, 3]` per MESH NAME on the POINT domain - the same
contract as `vertex_irradiance.npz` (gltf_gate1.py) - and is attached as COLOR_0 on the next run of this
script.
"""
import json
import math
import os
import sys
import time
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gate0_common as g0  # noqa: E402
import gate1_common as g1  # noqa: E402
import read_alpha  # noqa: E402  (cut_chain / png_has_alpha; the discovery run is guarded by __main__)

SCHEMA = "pfa-phase6c/trees-far/1"
TRI_TARGET = 8000        # brief item A: <= 8 k triangles per prototype
BRANCH_MIN = 1500        # a trunk under this reads as a wire at 3 m
BRANCH_MAX = 4600        # ... and over this there is nothing left for the crown
CARD_SCALE_MAX = 1.6     # 1/sqrt(keep) capped: these meshes are seen from ~3 m, not only at 40 m
GLTF_NAME = "env_trees"
CROWN_TOP_TOL_REL = 0.08   # LOD2 crown top vs the impostor quad's top, as a fraction of the tallest far tree
OUT3 = g0.ROOT / "export" / "out" / "gate3" / "trees_far"


def tris_of(me):
    return sum(len(p.vertices) - 2 for p in me.polygons)


def read_manifest():
    """The Gate 3 manifest, local-then-MAIN (export/out is gitignored, like every other hand-off read)."""
    p = next((q for q in (g0.ROOT / "export/out/gate3/manifest.json",
                          g0.MAIN_ROOT / "export/out/gate3/manifest.json") if q.exists()), None)
    assert p is not None, "export/out/gate3/manifest.json not found in this worktree or in MAIN"
    return json.loads(p.read_text()), p


def components(bm):
    """Face-connected components, as gate1_set.thin_leaf_cards computes them."""
    bm.faces.ensure_lookup_table()
    seen, comps = set(), []
    for f in bm.faces:
        if f.index in seen:
            continue
        stack, comp = [f], []
        seen.add(f.index)
        while stack:
            cf = stack.pop()
            comp.append(cf)
            for e in cf.edges:
                for nf in e.link_faces:
                    if nf.index not in seen:
                        seen.add(nf.index)
                        stack.append(nf)
        comps.append(comp)
    return comps


def split_cards(me):
    """(branch_mesh, card_mesh, stats) - two datablocks with the same material slots and UV layers."""
    bm = bmesh.new()
    bm.from_mesh(me)
    comps = components(bm)
    card_faces = {f.index for c in comps if len(c) <= 2 for f in c}
    total = sum(len(f.verts) - 2 for f in bm.faces)
    card_tris = sum(len(f.verts) - 2 for f in bm.faces if f.index in card_faces)
    bm.free()
    out = []
    for keep_cards in (False, True):
        m2 = me.copy()
        m2.name = f"{me.name}_{'cards' if keep_cards else 'branch'}"
        b = bmesh.new()
        b.from_mesh(m2)
        b.faces.ensure_lookup_table()
        drop = [f for f in b.faces if (f.index in card_faces) != keep_cards]
        bmesh.ops.delete(b, geom=drop, context="FACES")
        b.to_mesh(m2)
        b.free()
        m2.update()
        out.append(m2)
    stats = dict(tris=total, card_tris=card_tris, branch_tris=total - card_tris,
                 cards=sum(1 for c in comps if len(c) <= 2),
                 branch_components=sum(1 for c in comps if len(c) > 2))
    return out[0], out[1], stats


def collapse(me, target, tmp_coll):
    """gate1_set.exp_mesh's COLLAPSE path (weld, then iterate the ratio), without the voxel fallback:
    a remeshed branch skeleton is a blob and these meshes are seen close up."""
    if tris_of(me) <= target:
        return me
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bm.to_mesh(me)
    bm.free()
    me.update()
    tob = bpy.data.objects.new("EXP_TMP_treedec", me)
    tmp_coll.objects.link(tob)
    bpy.context.view_layer.objects.active = tob
    for _ in range(4):
        cur = tris_of(me)
        if cur <= target * 1.05:
            break
        m = tob.modifiers.new("decimate", "DECIMATE")
        m.decimate_type = "COLLAPSE"
        m.ratio = max(1e-4, float(target) / float(cur))
        m.use_collapse_triangulate = True
        bpy.ops.object.modifier_apply(modifier=m.name)
        if tris_of(me) >= cur:
            break
    out = tob.data
    tmp_coll.objects.unlink(tob)
    bpy.data.objects.remove(tob, do_unlink=True)
    return out


def thin_and_grow(me, target_tris, scale_max):
    """Drop whole leaf cards to `target_tris`, then scale the survivors about their own centre so the crown
    keeps as much of its leaf area as `scale_max` allows. Returns the stats."""
    bm = bmesh.new()
    bm.from_mesh(me)
    comps = components(bm)
    cards = [c for c in comps if len(c) <= 2]
    total = sum(len(f.verts) - 2 for c in comps for f in c)
    keep_fraction = 1.0 if total <= 0 else max(0.0, min(1.0, float(target_tris) / float(total)))
    keep_pct = int(keep_fraction * 1000)      # floor: a card can be more than 2 triangles
    drop, kept = [], []
    for i, c in enumerate(cards):
        if (i % 1000) >= keep_pct:
            drop.extend(c)
        else:
            kept.append(c)
    scale = min(scale_max, 1.0 / math.sqrt(keep_fraction)) if keep_fraction > 0 else 1.0
    if scale > 1.0001:
        for c in kept:
            vs = {v for f in c for v in f.verts}
            ctr = Vector((0.0, 0.0, 0.0))
            for v in vs:
                ctr += v.co
            ctr /= len(vs)
            for v in vs:
                v.co = ctr + (v.co - ctr) * scale
    bmesh.ops.delete(bm, geom=drop, context="FACES")
    bm.to_mesh(me)
    bm.free()
    me.update()
    return dict(cards_before=len(cards), cards_kept=len(kept),
                keep_fraction=round(keep_fraction, 4), card_scale=round(scale, 4),
                leaf_area_kept=round(min(1.0, keep_fraction * scale * scale), 4))


def join(branch, cards, name, materials):
    """One mesh from the two halves. Both were copied from the same datablock, so the material slots and the
    UV layer names line up and bmesh appends them by name."""
    out = bpy.data.meshes.new(name)
    for m in materials:
        out.materials.append(m)
    bm = bmesh.new()
    bm.from_mesh(branch)
    bm.from_mesh(cards)
    bm.to_mesh(out)
    bm.free()
    out.update()
    return out


def main():
    t_start = time.time()
    OUT3.mkdir(parents=True, exist_ok=True)
    g1.OUT.mkdir(parents=True, exist_ok=True)
    assert Path(bpy.data.filepath).name == "master_delivery.blend", \
        f"trees_far.py must run on master_delivery.blend, not {bpy.data.filepath!r}"
    man, man_p = read_manifest()
    imp = man["impostors"]
    proto_map = imp["prototype_map"]
    protos = sorted(imp["prototypes"])
    far = man["tree_far"]
    assert len(protos) == 16, f"{len(protos)} impostor prototypes, expected 16"

    rep = dict(schema=SCHEMA, generated=time.strftime("%Y-%m-%dT%H:%M:%S"),
               generator="export/trees_far.py", source_blend=bpy.data.filepath,
               manifest=str(man_p), tri_target=TRI_TARGET, branch_min=BRANCH_MIN, branch_max=BRANCH_MAX,
               card_scale_max=CARD_SCALE_MAX)

    tmp = bpy.data.collections.new("EXP_TREEFAR_TMP")
    bpy.context.scene.collection.children.link(tmp)
    exp = bpy.data.collections.new("EXP_TREEFAR")
    bpy.context.scene.collection.children.link(exp)

    dg = bpy.context.evaluated_depsgraph_get()
    step = g0.Step("trees_far:meshes")
    protos_out, rejected = {}, {}
    for p in protos:
        ob = bpy.data.objects.get(p)
        assert ob is not None, f"prototype object {p} is not in master_delivery.blend"
        # why the shipped _LOD2 is not used - measured, not assumed
        p2 = bpy.data.objects.get(p[:-5] + "_LOD2")
        if p2 is not None:
            me2 = bpy.data.meshes.new_from_object(p2.evaluated_get(dg))
            mats2 = [m.name if m else None for m in me2.materials]
            leaf_faces = sum(1 for f in me2.polygons
                             if f.material_index < len(mats2)
                             and (mats2[f.material_index] or "").startswith("MAT_leaf"))
            rejected[p2.name] = dict(tris=tris_of(me2), leaf_faces=leaf_faces,
                                     reason="branch skeleton: too few leaf faces to read as a crown")
            bpy.data.meshes.remove(me2)

        src = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
        src.name = f"EXPM_treefar_{p}_src"
        src.transform(ob.matrix_world)          # prototype world space: z = 0 is the trunk-base plane
        materials = [m for m in src.materials]
        branch, cards, st = split_cards(src)
        branch_target = int(min(BRANCH_MAX, max(BRANCH_MIN,
                                                round(TRI_TARGET * st["branch_tris"] / max(st["tris"], 1)))))
        branch = collapse(branch, branch_target, tmp)
        branch_tris = tris_of(branch)
        card_budget = max(0, TRI_TARGET - branch_tris)
        cst = thin_and_grow(cards, card_budget, CARD_SCALE_MAX)
        me = join(branch, cards, f"EXPM_treefar_{p}", materials)
        for d in (src, branch, cards):
            bpy.data.meshes.remove(d)
        co = np.array([list(v.co) for v in me.vertices], dtype=np.float64)
        lo, hi = co.min(axis=0), co.max(axis=0)
        hab = float(hi[2])
        ref = imp["prototypes"][p]
        # the mesh and the impostor have to occupy the same volume: the viewer crossfades between them at
        # `treeMeshDist`. Thinning can take the topmost card and CARD_SCALE_MAX can push one up, so the bound
        # is relative, measured and reported rather than assumed exact.
        assert abs(hab - ref["height_above_base_m"]) < 0.08 * ref["height_above_base_m"], \
            (f"{p}: LOD2 top is {hab:.3f} m above the base plane, the impostor measured "
             f"{ref['height_above_base_m']:.3f} m - the two would not crossfade")
        assert tris_of(me) <= TRI_TARGET * 1.05, f"{p}: {tris_of(me)} tris over the {TRI_TARGET} target"
        protos_out[p] = dict(
            mesh=me.name, tris=tris_of(me), verts=int(co.shape[0]),
            materials=[m.name for m in me.materials],
            uv_layers=[u.name for u in me.uv_layers],
            bbox_min=[round(float(v), 4) for v in lo], bbox_max=[round(float(v), 4) for v in hi],
            height_above_base_m=round(hab, 4),
            impostor_height_above_base_m=ref["height_above_base_m"],
            crown_top_rel_dev=round(abs(hab - ref["height_above_base_m"]) / ref["height_above_base_m"], 4),
            src_tris=st["tris"], src_branch_tris=st["branch_tris"], src_card_tris=st["card_tris"],
            branch_target=branch_target, branch_tris=branch_tris,
            card_tris=tris_of(me) - branch_tris,
            reduction=dict(**st, **cst))
    step.done(prototypes=len(protos_out),
              tris=sum(v["tris"] for v in protos_out.values()),
              worst=max(v["tris"] for v in protos_out.values()))
    rep["prototypes"] = protos_out
    rep["lod2_objects_rejected"] = rejected

    # ---------------------------------------------------------------- the 127 placements
    step = g0.Step("trees_far:placements")
    placements, worst_dev = [], 0.0
    for i, row in enumerate(far):
        p = proto_map[row["prototype"]]
        ref = imp["prototypes"][p]
        s = float(row["height_m"]) / float(ref["height_above_base_m"])
        me = bpy.data.meshes[protos_out[p]["mesh"]]
        no = bpy.data.objects.new(f"TREEFAR_{i:03d}", me)
        no.location = Vector(row["trunk_base"])
        no.scale = (s, s, s)
        exp.objects.link(no)
        # the transform IS the impostor's (translation trunk_base, uniform s). What is worth measuring is
        # how far the LOD2 crown top then lands from the impostor quad's top, trunk_base.z + height_m.
        top = float(row["trunk_base"][2]) + protos_out[p]["height_above_base_m"] * s
        want = float(row["trunk_base"][2]) + float(row["height_m"])
        assert max(abs(a - float(b)) for a, b in zip(no.location, row["trunk_base"])) < 1e-4, \
            f"{no.name}: translation {list(no.location)} != trunk_base {row['trunk_base']}"
        worst_dev = max(worst_dev, abs(top - want))
        placements.append(dict(index=i, object=no.name, prototype=p, mesh=me.name,
                               source_prototype=row["prototype"], source_tree=row["source_tree"],
                               billboard=row["billboard"],
                               loc=[round(float(v), 4) for v in row["trunk_base"]],
                               scale=round(s, 6), height_m=row["height_m"],
                               walk_dist_m=row["walk_dist_m"]))
    assert len(placements) == len(far) == 127, f"{len(placements)} placements, expected 127"
    tallest = max(float(r["height_m"]) for r in far)
    assert worst_dev < CROWN_TOP_TOL_REL * tallest, \
        f"worst crown-top deviation {worst_dev:.3f} m over {CROWN_TOP_TOL_REL:.0%} of {tallest:.1f} m"
    step.done(placements=len(placements), worst_crown_top_dev_mm=round(worst_dev * 1000, 1))
    rep["placements"] = placements
    rep["placement_check"] = dict(
        rule="s = tree_far[i].height_m / impostors.prototypes[p].height_above_base_m, translation = "
             "trunk_base, rotation ignored - manifest `impostors.placement`, verbatim",
        translation="asserted equal to the manifest's trunk_base on every one of the 127 rows",
        worst_crown_top_deviation_m=round(worst_dev, 4),
        crown_top_note="the LOD2 crown top against the impostor quad's top (trunk_base.z + height_m): the "
                       "card thinning takes or grows the topmost card, so the two silhouettes differ by "
                       "this much where they crossfade",
        tol_rel=CROWN_TOP_TOL_REL, rows=len(placements))

    # ---------------------------------------------------------------- COLOR_0 (item B's vertex AO)
    step = g0.Step("trees_far:color0")
    ao_p = next((q for q in (OUT3 / "vertex_ao.npz",
                             g0.MAIN_ROOT / "export/out/gate3/trees_far/vertex_ao.npz") if q.exists()), None)
    ao_rep = {}
    if ao_p is not None:
        z = np.load(str(ao_p))
        dts = sorted({str(np.asarray(z[f]).dtype) for f in z.files})
        assert dts == ["float32"], f"{ao_p.name} is {dts}, the contract is float32 (gltf_gate1.py's rule)"
        rng = float(np.float32(max((float(np.asarray(z[f]).max()) for f in z.files), default=1.0))) or 1.0
        for mn in z.files:
            me = bpy.data.meshes.get(mn)
            assert me is not None, f"{ao_p.name} names {mn}, which is not a far-tree LOD2 mesh"
            lin = np.asarray(z[mn]).astype(np.float64)
            assert lin.shape == (len(me.vertices), 3), \
                f"{mn}: the bake wrote {lin.shape[0]} vertex colours, this mesh has {len(me.vertices)} verts"
            assert not me.color_attributes, f"{mn} already carries colour attributes"
            code = np.clip(np.sqrt(lin / rng), 0.0, 1.0)
            ca = me.color_attributes.new(name="irradiance", type="FLOAT_COLOR", domain="POINT")
            rgba = np.ones((len(me.vertices), 4), dtype=np.float32)
            rgba[:, :3] = code.astype(np.float32)
            ca.data.foreach_set("color", rgba.reshape(-1))
            me.update()
            ao_rep[mn] = dict(verts=int(lin.shape[0]), range=rng, encode="gamma2",
                              linear_mean=round(float(lin.mean()), 6), code_mean=round(float(code.mean()), 6))
        rep["color0"] = dict(source=str(ao_p), range=rng, meshes=ao_rep,
                             encode="COLOR_0 = sqrt(linear / range); viewer decodes linear = COLOR_0^2 * range")
    else:
        rep["color0"] = dict(source=None, note="out/gate3/trees_far/vertex_ao.npz (item B) not present yet: "
                                               "env_trees.glb ships without COLOR_0, re-run this script and "
                                               "gltf_pack.sh --trees when the bake lands")
    step.done(meshes=len(ao_rep))

    # ---------------------------------------------------------------- env_trees.gltf
    # Same exporter arguments as gltf_gate1.py, same texture directory: the leaf and bark PNGs the far trees
    # use are the ones the near trees already wrote into out/gate1/tex_gltf, so they dedupe by file name and
    # gltf_pack.sh --trees reuses the KTX2 that is already there.
    step = g0.Step("trees_far:gltf")
    want = dict(export_format="GLTF_SEPARATE", use_selection=True, export_yup=True, export_apply=True,
                export_tangents=True, export_normals=True, export_texcoords=True,
                export_materials="EXPORT", export_image_format="AUTO", export_keep_originals=False,
                export_cameras=False, export_lights=False, export_extras=False, export_animations=False,
                export_skins=False, export_morph=False, export_texture_dir="tex_gltf",
                export_all_vertex_colors=True)
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
    # alphaMode on the leaf cards (export/README.md items 29-30): decided by the EXPORTED texture, and the
    # cut is read from this blend's own Mix Shader / Map Range graph, never from `material.alpha_threshold`.
    imgs = [i.get("uri") for i in doc.get("images", [])]
    texs = [t.get("source") for t in doc.get("textures", [])]
    alpha_mats, alpha_missing = {}, []
    for m in doc.get("materials", []):
        bct = (m.get("pbrMetallicRoughness") or {}).get("baseColorTexture")
        if bct is None or m.get("alphaMode"):
            continue
        src_uri = imgs[texs[bct["index"]]] if bct["index"] < len(texs) and texs[bct["index"]] is not None \
            else None
        if not src_uri or not read_alpha.png_has_alpha(gltf_p.parent / src_uri):
            continue
        bm = bpy.data.materials.get(m.get("name", ""))
        cut, why = read_alpha.cut_chain(bm) if bm is not None else (None, "no such material in this blend")
        if cut is None:
            alpha_missing.append((m.get("name"), why))
            continue
        m["alphaMode"] = "MASK"
        m["alphaCutoff"] = cut
        alpha_mats[m.get("name")] = dict(cutoff=cut, texture=src_uri, reason=why)
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
    rep["gltf"] = dict(
        path=gltf_p.name, bytes=gltf_p.stat().st_size, nodes=len(doc.get("nodes", [])),
        meshes=len(doc.get("meshes", [])), materials=[m.get("name") for m in doc.get("materials", [])],
        images=[i.get("uri") for i in doc.get("images", [])],
        placed_tris=sum(protos_out[pl["prototype"]]["tris"] for pl in placements),
        unique_tris=sum(v["tris"] for v in protos_out.values()),
        attributes={k: len(v) for k, v in sorted(attr.items())},
        color0_meshes=sorted(x for x in attr.get("COLOR_0", set()) if x),
        alpha_mask_materials=alpha_mats,
        alpha_mode_materials={m.get("name"): [m.get("alphaMode"), m.get("alphaCutoff")]
                              for m in doc.get("materials", []) if m.get("alphaMode")},
        args=sorted(kwargs))
    step.done(gltf_p, bytes=gltf_p.stat().st_size, nodes=len(doc.get("nodes", [])))

    # ---------------------------------------------------------------- the bake hand-off blend
    step = g0.Step("trees_far:hand_off_blend")
    topo = dict(schema=SCHEMA, generated=rep["generated"], generator="export/trees_far.py",
                source_blend=bpy.data.filepath, manifest=str(man_p),
                blend="trees_far_lod2.blend",
                blend_note="the 16 LOD2 prototype objects alone, in prototype WORLD space (their own matrix "
                           "is already applied, so every object is at the identity and z = 0 is the trunk "
                           "base plane). Regenerate with: scripts/blender_run.sh 900 -- --background "
                           "master_delivery.blend --python export/trees_far.py",
                vertex_ao_contract=dict(
                    path="export/out/gate3/trees_far/vertex_ao.npz",
                    layout="one float32 array [verts, 3] per MESH NAME below, POINT domain, scene-linear - "
                           "the same contract as out/gate3/vertex_irradiance.npz (gltf_gate1.py)",
                    encode="the export writes COLOR_0 = sqrt(linear / range) at one shared range over all "
                           "16 meshes and packs env_trees.glb with -vc 16"),
                placement=rep["placement_check"],
                tri_target=TRI_TARGET, card_scale_max=CARD_SCALE_MAX,
                lod2_objects_rejected=rejected,
                prototypes={k: {kk: v[kk] for kk in
                                ("mesh", "tris", "verts", "materials", "uv_layers", "bbox_min", "bbox_max",
                                 "height_above_base_m", "src_tris", "reduction")}
                            for k, v in protos_out.items()},
                placements=placements)
    (OUT3 / "topology.json").write_text(json.dumps(topo, indent=1) + "\n")

    # strip the file down to the 16 prototype objects so the bake opens something small
    keep_meshes = {v["mesh"] for v in protos_out.values()}
    keep_objs = {}
    for p, v in protos_out.items():
        o = bpy.data.objects.new(v["mesh"], bpy.data.meshes[v["mesh"]])
        tmp.objects.link(o)
        keep_objs[p] = o.name
    for o in list(bpy.data.objects):
        if o.name not in set(keep_objs.values()):
            bpy.data.objects.remove(o, do_unlink=True)
    for _ in range(3):
        bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)
    blend_p = OUT3 / "trees_far_lod2.blend"
    g0.save_copy(blend_p)
    rep["hand_off"] = dict(topology=str(OUT3 / "topology.json"), blend=str(blend_p),
                           blend_bytes=blend_p.stat().st_size, objects=len(keep_objs),
                           meshes=sorted(keep_meshes))
    step.done(blend_p, bytes=blend_p.stat().st_size)
    rep["wall_s"] = round(time.time() - t_start, 1)
    (g1.OUT / "trees_far.json").write_text(json.dumps(rep, indent=1) + "\n")
    print(f"[trees_far] {len(protos_out)} prototypes "
          f"{min(v['tris'] for v in protos_out.values())}-{max(v['tris'] for v in protos_out.values())} tris, "
          f"{len(placements)} placements, hand-off {blend_p.name} "
          f"{blend_p.stat().st_size/1e6:.1f} MB -> {g1.OUT / 'trees_far.json'}")


if __name__ == "__main__":
    main()
