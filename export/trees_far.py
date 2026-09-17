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
from mathutils import Matrix, Vector

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
PLACE_TOL_M = 0.001        # exported glTF node translation vs to_gltf(trunk_base), per row
ANCHOR_TOL_M = 0.02        # reconstructed prototype bbox/radius vs the manifest's own impostor numbers
# WHICH CARDS THE THINNING KEEPS. This is part of the vertex-AO contract, not a style choice: the bake
# computes one AO value per vertex of the mesh THIS script built, addressed by index, so changing the
# surviving subset silently re-points every value. `stride` is correct (review item 3: `block` leaves bald
# branches); `block` is what out/gate3/trees_far/vertex_ao.npz was baked against. Flipping this to `stride`
# REQUIRES the 16 AO jobs to be re-baked - the COLOR_0 attach below refuses the mismatch rather than
# shipping trees lit by another vertex's occlusion.
CARD_SELECT = "block"      # "stride" | "block"



def to_gltf(loc):
    """Blender Z-up world translation -> glTF Y-up, the exporter's own swap: (x, y, z) -> (x, z, -y).
    The same helper as export/gate4_instance_order.py, which is what the per-placement join keys on."""
    return (float(loc[0]), float(loc[2]), -float(loc[1]))
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
    area_before = sum(f.calc_area() for c in cards for f in c)
    drop, kept = [], []
    for i, c in enumerate(cards):
        # STRIDE vs BLOCK (CARD_SELECT). The components come back in bmesh order, which is broadly spatial,
        # so `(i % 1000) >= keep_pct` keeps the first keep_pct of every run of 1000 - one contiguous block of
        # foliage kept and the rest of the run stripped, i.e. bald branches wherever a run boundary falls
        # (visible at 18-31 % keep, which is where the big crowns land). 997 is coprime with 1000, so the
        # stride is a bijection mod 1000: exactly as many cards survive, scattered through the crown.
        k = (i * 997) % 1000 if CARD_SELECT == "stride" else i % 1000
        if k >= keep_pct:
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
    # MEASURED, not modelled: `keep_fraction * scale^2` assumes every card has the mean area and that the
    # grow is exact, and it is the number the crown's opacity actually depends on. calc_area() after the
    # grow, over the cards that survive, against every card's area before it.
    area_after = sum(f.calc_area() for c in kept for f in c)
    bmesh.ops.delete(bm, geom=drop, context="FACES")
    bm.to_mesh(me)
    bm.free()
    me.update()
    return dict(card_select=CARD_SELECT, cards_before=len(cards), cards_kept=len(kept),
                keep_fraction=round(keep_fraction, 4), card_scale=round(scale, 4),
                leaf_area_m2_before=round(float(area_before), 4),
                leaf_area_m2_after=round(float(area_after), 4),
                leaf_area_kept=round(float(area_after / area_before), 4) if area_before > 0 else None,
                leaf_area_kept_modelled=round(min(1.0, keep_fraction * scale * scale), 4),
                leaf_area_note="leaf_area_kept is measured (sum f.calc_area() after the grow / before the "
                               "thin); leaf_area_kept_modelled is the old keep_fraction * scale^2 estimate, "
                               "kept only so the two can be compared")


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
        # ---- THE ANCHOR. `src.transform(ob.matrix_world)` leaves the mesh at the prototype's own WORLD
        # position (x ~ -430, y ~ -570 for the s19 broadleaf). Placing it at `location = trunk_base` then
        # ADDS the placement on top of that, which put every far tree ~300 m off its trunk. Only z looked
        # right, because the prototype's own z = 0 already IS the base plane, which is why the crown-top
        # assert passed. The mesh is therefore re-anchored below so that the point the impostor rotates
        # about maps to the mesh origin, and `location = trunk_base` then means what it says.
        #
        # Which point is that? manifest `impostors.placement`: "the quad is a screen-facing square of side
        # 2*radius_m*s centred at trunk_base + (0,0, centre_z_m*s)" and both heights are measured from the
        # prototype's own z = 0. So the axis is the prototype's BBOX XY CENTRE at z = 0. That is not assumed:
        # radius_m is reproduced below from the bbox as hypot(half the XY diagonal, the greater z offset from
        # centre_z_m) and asserted against the manifest's own number for all 16 prototypes.
        sco = np.array([list(v.co) for v in src.vertices], dtype=np.float64)
        slo, shi = sco.min(axis=0), sco.max(axis=0)
        anchor = Vector(((slo[0] + shi[0]) * 0.5, (slo[1] + shi[1]) * 0.5, 0.0))
        ref0 = imp["prototypes"][p]
        half_xy = math.hypot((shi[0] - slo[0]) * 0.5, (shi[1] - slo[1]) * 0.5)
        cz = float(ref0["centre_z_m"])
        r_calc = math.hypot(half_xy, max(abs(float(shi[2]) - cz), abs(float(slo[2]) - cz)))
        anchor_check = dict(
            anchor=[round(float(v), 4) for v in anchor],
            bbox_m=[round(float(shi[0] - slo[0]), 4), round(float(shi[1] - slo[1]), 4),
                    round(float(shi[2] - slo[2]), 4)],
            manifest_bbox_m=ref0["bbox_m"], radius_m=round(r_calc, 4),
            manifest_radius_m=ref0["radius_m"], base_z_m=round(float(slo[2]), 4),
            manifest_base_z_m=ref0["base_z_m"],
            rule="anchor = (bbox XY centre, z = 0); radius reproduced as hypot(half the XY diagonal, the "
                 "greater |z - centre_z_m|) and asserted against the manifest")
        for key, got, wantv in (("bbox_m[0]", float(shi[0] - slo[0]), ref0["bbox_m"][0]),
                                ("bbox_m[1]", float(shi[1] - slo[1]), ref0["bbox_m"][1]),
                                ("radius_m", r_calc, float(ref0["radius_m"])),
                                ("base_z_m", float(slo[2]), float(ref0["base_z_m"]))):
            assert abs(got - wantv) < ANCHOR_TOL_M, (
                f"{p}: {key} reconstructed as {got:.4f} m, the impostor bake recorded {wantv:.4f} m. The "
                f"anchor this export places on is NOT the point the impostor rotates about, so the mesh and "
                f"the impostor would not land in the same place.")
        materials = [m for m in src.materials]
        branch, cards, st = split_cards(src)
        branch_target = int(min(BRANCH_MAX, max(BRANCH_MIN,
                                                round(TRI_TARGET * st["branch_tris"] / max(st["tris"], 1)))))
        branch = collapse(branch, branch_target, tmp)
        branch_tris = tris_of(branch)
        card_budget = max(0, TRI_TARGET - branch_tris)
        cst = thin_and_grow(cards, card_budget, CARD_SCALE_MAX)
        me = join(branch, cards, f"EXPM_treefar_{p}", materials)
        # the mesh origin becomes the impostor's own axis at the trunk-base plane, so a placement is exactly
        # `location = trunk_base, scale = s` - and the EXPORTED node translation is then to_gltf(trunk_base)
        # verbatim, which is what the per-row assert after the glTF write checks.
        me.transform(Matrix.Translation(-anchor))
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
            anchor_check=anchor_check,
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
        # NOT asserted here: `no.location` was assigned from `row["trunk_base"]` three lines up, so any
        # check of one against the other is a tautology that passes however wrong the export is. The
        # translation is asserted after the glTF is written, against the EXPORTED node - which is the only
        # place the exporter's Z-up -> Y-up swap and its float32 round trip can actually go wrong.
        worst_dev = max(worst_dev, abs(top - want))
        placements.append(dict(index=i, object=no.name, prototype=p, mesh=me.name,
                               source_prototype=row["prototype"], source_tree=row["source_tree"],
                               billboard=row["billboard"],
                               loc=[round(float(v), 4) for v in row["trunk_base"]],
                               scale=round(s, 6), height_m=row["height_m"],
                               walk_dist_m=row["walk_dist_m"]))
    assert len(placements) == len(far) == 127, f"{len(placements)} placements, expected 127"

    # ---- THE PLACED MESH, IN WORLD SPACE, AGAINST THE IMPOSTOR QUAD (per row).
    # This is the check the export did not have: `no.location` was right all along, but the mesh under it
    # carried the prototype's own world position, so the tree DREW ~300 m away while every assert passed.
    # Nothing here is derived from `no.location`; it is the evaluated world bounding box of the geometry.
    bpy.context.view_layer.update()
    worst_xy, worst_xy_row, worst_top, worst_top_row = 0.0, None, 0.0, None
    for pl, row in zip(placements, far):
        no = bpy.data.objects[pl["object"]]
        cs = [no.matrix_world @ Vector(c) for c in no.bound_box]
        bx = [min(c[k] for c in cs) for k in range(3)], [max(c[k] for c in cs) for k in range(3)]
        tb = [float(v) for v in row["trunk_base"]]
        # (1) the crown sits over its trunk: the drawn XY centre against trunk_base, tolerated at the
        #     impostor quad's own half-width so a tree can lean but cannot be in another postcode.
        cx, cy = (bx[0][0] + bx[1][0]) * 0.5, (bx[0][1] + bx[1][1]) * 0.5
        dxy = math.hypot(cx - tb[0], cy - tb[1])
        quad_r = float(imp["prototypes"][pl["prototype"]]["radius_m"]) * pl["scale"]
        assert dxy <= quad_r, (
            f"{pl['object']}: the placed mesh's XY centre is {dxy:.3f} m from trunk_base "
            f"{tb[:2]}, outside its own impostor quad (radius {quad_r:.3f} m). The mesh is anchored "
            f"somewhere other than the point the impostor rotates about.")
        # (2) the crown top against the impostor quad's top, measured on the drawn geometry
        dtop = abs(float(bx[1][2]) - (tb[2] + float(row["height_m"])))
        if dxy > worst_xy:
            worst_xy, worst_xy_row = dxy, pl["object"]
        if dtop > worst_top:
            worst_top, worst_top_row = dtop, pl["object"]
        pl["placed_bbox_min"] = [round(float(v), 4) for v in bx[0]]
        pl["placed_bbox_max"] = [round(float(v), 4) for v in bx[1]]
        pl["placed_xy_offset_m"] = round(dxy, 4)
        pl["placed_top_delta_m"] = round(dtop, 4)
    tallest = max(float(r["height_m"]) for r in far)
    assert worst_dev < CROWN_TOP_TOL_REL * tallest, \
        f"worst crown-top deviation {worst_dev:.3f} m over {CROWN_TOP_TOL_REL:.0%} of {tallest:.1f} m"
    step.done(placements=len(placements), worst_crown_top_dev_mm=round(worst_dev * 1000, 1))
    rep["placements"] = placements
    rep["placement_check"] = dict(
        rule="s = tree_far[i].height_m / impostors.prototypes[p].height_above_base_m, translation = "
             "trunk_base, rotation ignored - manifest `impostors.placement`, verbatim",
        translation=("asserted AFTER the export: every env_trees.gltf node translation against "
                     "to_gltf(trunk_base) = (x, z, -y), and every node scale against s, on all 127 rows "
                     "(`gltf_translation_check` below). The in-Blender assert this replaces compared "
                     "`no.location` with the value it had just been assigned and could not fail."),
        worst_crown_top_deviation_m=round(worst_dev, 4),
        crown_top_note="the LOD2 crown top against the impostor quad's top (trunk_base.z + height_m): the "
                       "card thinning takes or grows the topmost card, so the two silhouettes differ by "
                       "this much where they crossfade",
        placed_mesh_check=dict(
            rule="per row, on the EVALUATED world bounding box of the placed mesh (not on no.location): "
                 "the drawn XY centre is within the row's own impostor quad radius (radius_m * s) of "
                 "trunk_base, and the drawn top is measured against trunk_base.z + height_m",
            worst_xy_offset_m=round(worst_xy, 4), worst_xy_row=worst_xy_row,
            worst_top_delta_m=round(worst_top, 4), worst_top_row=worst_top_row,
            why="the round-1 export placed a mesh that carried the prototype's own world position on top of "
                "trunk_base, so every far tree drew ~300 m away while every assert passed"),
        tol_rel=CROWN_TOP_TOL_REL, rows=len(placements))

    # ---------------------------------------------------------------- COLOR_0 (item B's vertex AO)
    step = g0.Step("trees_far:color0")
    ao_p = next((q for q in (OUT3 / "vertex_ao.npz",
                             g0.MAIN_ROOT / "export/out/gate3/trees_far/vertex_ao.npz") if q.exists()), None)
    ao_rep = {}
    if ao_p is not None:
        # The AO is addressed BY VERTEX INDEX, so it is only valid for the exact mesh the hand-off blend
        # carried. `CARD_SELECT` decides WHICH leaf cards survive, so a change there re-points every value
        # onto a different vertex - and because the stride keeps the same NUMBER of cards, the shape check
        # below would not catch it. Pin it against the hand-off that produced this npz: topology.json's own
        # `card_select`, defaulting to "block" for the round-1 hand-off, which predates the field.
        prev_p = next((q for q in (OUT3 / "topology.json",
                                   g0.MAIN_ROOT / "export/out/gate3/trees_far/topology.json")
                       if q.exists()), None)
        prev_sel = "block"
        if prev_p is not None:
            prev_sel = (json.loads(prev_p.read_text()) or {}).get("card_select", "block")
        assert prev_sel == CARD_SELECT, (
            f"{ao_p.name} was baked against the hand-off built with CARD_SELECT={prev_sel!r}, this run uses "
            f"{CARD_SELECT!r}. The thinning keeps a DIFFERENT set of leaf cards, so every AO value would "
            f"land on a different vertex - and the two keep the same card COUNT, so the shape check below "
            f"cannot see it. Re-bake the 16 vertex-AO jobs against the new trees_far_lod2.blend, or put "
            f"CARD_SELECT back to {prev_sel!r}.")
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
        rep["color0"] = dict(source=str(ao_p), range=rng, meshes=ao_rep, card_select=CARD_SELECT,
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
    # ---- the placement check that can fail: the EXPORTED node translations, per row.
    # `no.location` was assigned from `trunk_base`, so comparing the two in Blender proves nothing. This
    # crosses the exporter boundary - the Z-up -> Y-up swap (x, y, z) -> (x, z, -y), `export_apply`, and the
    # float32 round trip - which is where a placement can really move, and it is the same key the
    # per-placement irradiance join uses after gltfpack drops the node names.
    nodes = {n.get("name"): n for n in doc.get("nodes", []) if "mesh" in n}
    assert len(nodes) == len(placements), \
        f"{gltf_p.name} has {len(nodes)} mesh nodes, the export placed {len(placements)}"
    worst_t, worst_s, worst_row = 0.0, 0.0, None
    for pl, row in zip(placements, far):
        nd = nodes.get(pl["object"])
        assert nd is not None, f"{gltf_p.name} has no node named {pl['object']!r}"
        want_t = to_gltf(row["trunk_base"])
        got_t = tuple(float(v) for v in nd.get("translation", (0.0, 0.0, 0.0)))
        dt = max(abs(g - w) for g, w in zip(got_t, want_t))
        got_s = tuple(float(v) for v in nd.get("scale", (1.0, 1.0, 1.0)))
        ds = max(abs(v - pl["scale"]) for v in got_s)
        if dt > worst_t:
            worst_t, worst_row = dt, pl["object"]
        worst_s = max(worst_s, ds)
    assert worst_t < PLACE_TOL_M, \
        f"{gltf_p.name}: worst node translation residual {worst_t*1000:.3f} mm on {worst_row} against " \
        f"to_gltf(trunk_base), tolerance {PLACE_TOL_M*1000:.0f} mm"
    assert worst_s < 1e-5, f"{gltf_p.name}: worst node scale residual {worst_s:.2e} against height_m / " \
                           f"height_above_base_m"
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
        gltf_translation_check=dict(
            rows=len(placements), tol_m=PLACE_TOL_M,
            worst_translation_residual_m=round(worst_t, 6), worst_translation_row=worst_row,
            worst_scale_residual=round(worst_s, 9),
            rule="every node translation == to_gltf(trunk_base) = (x, z, -y), every node scale == "
                 "height_m / height_above_base_m, read back out of the written glTF"),
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
                tri_target=TRI_TARGET, card_scale_max=CARD_SCALE_MAX, card_select=CARD_SELECT,
                card_select_note="which leaf cards the thinning keeps. The vertex AO is addressed by vertex "
                                 "index, so an npz baked against this blend is only valid while this value "
                                 "is unchanged; export/trees_far.py refuses to attach across a change.",
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
