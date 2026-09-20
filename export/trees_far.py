"""Phase 6c item A: a real MESH for each of the 16 far-tree prototypes, instanced at every
`tree_far` placement (127 at 6c, 166 after the 8d belt), as its own lazily loaded glb. TWO SETS, one code path (`SETS` / `PFA_TREES_SET`):

    # item A - the far set, 8 k per prototype, with the item-B vertex AO: env_trees.glb
    scripts/blender_run.sh 900 -- --background master_delivery.blend --python export/trees_far.py
    export/gltf_pack.sh --trees          # KTX2 (shared tex_ktx2) + gltfpack -cc -mi -> env_trees.glb

    # round-3 item 2 - the WALK-UP set, 30 k per prototype, no vertex AO: env_trees_lod1.glb
    PFA_TREES_SET=walkup scripts/blender_run.sh 900 -- --background master_delivery.blend \
        --python export/trees_far.py
    export/gltf_pack.sh --trees-lod1

The walk-up set exists because a tree the walker is 3 m from is the one thing an 8 k mesh cannot carry, and
it shares this file so that it cannot drift from the far set's anchor, placement rule or ROW ORDER - the
viewer reuses env_trees.glb's placement rows and its per-placement irradiance for it, and after
`gltfpack -mi` the only key left is the row's position in its mesh's instancing buffer. That sameness is
asserted, not assumed: `instance_order_check` below reads both written glTFs and compares them node name by
node name and translation by translation, and verify_glb's `trees_lod1_order_check` compares the two packed
glbs' node, row and material sequence.

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
import belt_rule as br  # noqa: E402
import foliage_uv as fuv  # noqa: E402
import gate0_common as g0  # noqa: E402
import gate1_common as g1  # noqa: E402
import read_alpha  # noqa: E402  (cut_chain / png_has_alpha; the discovery run is guarded by __main__)

SCHEMA = "pfa-phase6c/trees-far/1"

# ---------------------------------------------------------------- the two sets this script builds
# Round 3 item 2 adds a WALK-UP set: the same 16 prototypes, the same anchor and the same 127 placements in
# the same order, reduced to 30 k instead of 8 k, for the few trees a walker is within ~15 m of. It is the
# same code path on purpose - a second script would be a second anchor, a second placement rule and a second
# way for the two glbs to disagree about where a tree stands, which is the one thing the viewer cannot
# recover once gltfpack has dropped the node names and left only the positional join.
#
# `far` reproduces round 2 EXACTLY (every value below is the constant it replaces), so the default run and
# env_trees.glb are unchanged; `PFA_TREES_SET=walkup` builds the other one. Same pattern as
# gate4_instance_order.py's SETS / PFA_ORDER_SET.
SETS = {
    "far": dict(
        tri_target=8000,          # brief item A: <= 8 k triangles per prototype
        branch_min=1500,          # a trunk under this reads as a wire at 3 m
        branch_max=4600,          # ... and over this there is nothing left for the crown
        card_scale_max=1.6,       # 1/sqrt(keep) capped: seen from ~3 m, not only at 40 m
        gltf_name="env_trees", mesh_prefix="EXPM_treefar_",
        uv_tile=True,             # PHASE 8e: the leaf-card UV tiling below, this set only
        # PHASE 9: the distance the VIEWER draws this set at, which is what the billboard-only rule
        # below measures against. The far set is what MOBILE loads (device.js `walkupMesh: '0'`,
        # `farTreeMesh: 45`), so a far row can be a mesh out to 45 m + the fade band.
        draw_within_m=45.0,
        color0=True, hand_off=True, report="trees_far.json", order_against=None),
    "walkup": dict(
        # 30 k is the brief's budget. The source _LOD1 meshes are 25.6 k-45.2 k triangles, so this is a
        # reduction of at most 0.66 and two prototypes need none at all.
        tri_target=30000,
        # the branch clamps are the `far` ones scaled by the same 30000/8000, so the pro-rata split between
        # trunk and crown behaves identically at the larger budget
        branch_min=5625, branch_max=17250,
        # NO GROW. `far` scales the surviving cards by 1/sqrt(keep) because it drops 70-80 % of them and the
        # crown would go see-through; at 30 k the keep fraction is 0.7-1.0 and a grown card is a visibly
        # wrong leaf at the 3 m this mesh exists for. 1.0 makes min(scale_max, 1/sqrt(keep)) == 1.0 always.
        card_scale_max=1.0,
        gltf_name="env_trees_lod1", mesh_prefix="EXPM_treewalk_",
        # NO UV TILING. This set is what DESKTOP draws (device.js leaves `walkupMesh` null, so the viewer
        # picks trees.walkup_mesh), and 8e is a mobile item: desktop's cards keep their UVs inside 0-1, which
        # is also what lets the REPEAT sampler patch on env_trees.glb be a no-op for every other root.
        uv_tile=False,
        # PHASE 9: desktop draws THIS set and `trees.walkup_mesh.draw_within_m` is 15 m
        # (manifest_v4.py, `WALKUP_DIST_M` in web/src/foliageLazy.js), so a walk-up row can be a mesh
        # out to 15 m + the fade band - a third of the far set's reach, which is why the two sets
        # keep a different number of belt rows.
        draw_within_m=15.0,
        # no vertex AO: the brief gives the viewer's interior term the job, and there is no bake for this
        # topology (the AO npz is addressed by vertex index against the `far` meshes' revision).
        color0=False, hand_off=False, report="trees_far_lod1.json", order_against="env_trees"),
}
SET_NAME = os.environ.get("PFA_TREES_SET", "far")
assert SET_NAME in SETS, f"PFA_TREES_SET={SET_NAME!r}, expected one of {sorted(SETS)}"
SET = SETS[SET_NAME]
TRI_TARGET = SET["tri_target"]
BRANCH_MIN = SET["branch_min"]
BRANCH_MAX = SET["branch_max"]
CARD_SCALE_MAX = SET["card_scale_max"]
GLTF_NAME = SET["gltf_name"]
MESH_PREFIX = SET["mesh_prefix"]
UV_TILE = SET.get("uv_tile", False)
# ---------------------------------------------------------------- PHASE 8e: the leaf-card UV tiling
# QA 19 finding 4(a): on the mobile close orbit the far crowns' leaves read as "~40 px wide gold/black
# duotone blades" at 37 m. Measured (docs/briefs/phase8e_analysis.md, export/p8e_leaf_probe.py): ONE card
# carries a centred vertical strip of the whole 1024 px cluster texture - u 0.18-0.85 by species, v 0-1, one
# texture tile = 0.88-1.02 m of prototype world - so at 20-30 texels per screen pixel the mip merges the
# painted leaves (0.05-0.11 m, 4-10 px, plausible) and the alpha MASK re-hardens the mush into blades of
# 17-22 px (p90) / 22-28 px (max) at 40 m, against 9-13 px for a believable foliage clump.
#
# The lever: scale the card's UVs about its own UV centre so the card samples the texture k times over. It
# needs REPEAT samplers (patched into the written glTF below) and it moves no vertex, so the vertex AO and
# the instance rows are untouched.
#
# WHY (1.0, 2.5) AND NOT THE ISOTROPIC 2.0 OF THE ANALYSIS. The analysis assumed the alpha coverage - the
# share of the card the cut leaves opaque, i.e. the crown's leaf area - is invariant under the scale. It is
# not, in u: the card's u window is the cluster's DENSE CORE (coverage 0.45-0.56), and widening it by k pulls
# in the radially faded rim. Measured, per species, at 40 m, as (coverage vs today) / blade p90 / blade max:
#   isotropic k=2:      0.62-0.76x   10-13 px / 14-17 px      <- 24-38 % of the crown's leaf area gone
#   ku=1.0, kv=2.5:     0.96-1.00x   11-14 px / 14-20 px      <- the same blade, no opacity change
#   ku=1.0, kv=3.0:     0.97-1.03x    8-13 px / 11-17 px
# v is free because the card's v window is the FULL texture height, so k periods of it average exactly what
# one period averages; u is not. Shipping the isotropic form would have thinned every far crown by a third -
# the 6c see-through defect Phase 7 exists to undo - as a silent side effect of a leaf-size fix. So the
# tiling is v-only, at the kv that reproduces the approved k=2.0 blade size. kv=3.0 is the next step if QA
# still reads the leaves large; a u factor is NOT (its cost is the table above).
# WHAT THE REVIEW FOUND (docs/reviews/phase8_export_r2_review.md finding 2, re-measured here with
# `export/p8e_leaf_probe.py`'s `run_width`): a v-only tiling shrinks the blade's THICKNESS and not its
# WIDTH, and QA 19 said "~40 px WIDE". Horizontal run width p90 at 40 m, shipped -> kv 2.5:
# broadleaf 35.7 -> 36.2, cypress 26.7 -> 26.7, eucalyptus 30.6 -> 30.9, pine 22.5 -> 22.5. The width of
# a blade at 40 m IS the card's own width for every species but the broadleaf - the cards are 12-31 px
# wide and the mip cannot break a mask inside them - and the broadleaf's 40 px card is exactly the crown
# in the user's orbit frames (TREEFAR_000 / _001 at 36.7 / 38.5 m). Narrowing THAT needs the u window
# widened (ku > 1), which costs coverage, which is bought back by lowering the leaf alphaCutoff in this
# glTF alone. Measured at 40 m with the per-MATERIAL cutoff the glTF can actually carry:
#   MODE            broadleaf run/thick/cov   worst other        cutoffs
#   kv2.5 (shipped)      36.2 / 11.2 / 0.98   euc 30.9/14.0      unchanged
#   iso k=2 at 0.50      16.9 / 10.3 / 0.76   redwood cov 0.62   unchanged   <- a third of the crown gone
#   iso_cut (below)      18.4 /  8.4 / 0.93   euc 25.3/14.0      0.27/0.21/0.10/0.12
# `iso_cut` holds the coverage to 0.93-1.07x at 40 m and 0.82-1.03x at 2.5 m (the mobile walk-up, where
# the mip is near-native and a lower cut only adds the painted leaves' antialiased rims, measured, not
# assumed). `iso_cut` IS WHAT env_trees.glb NOW SHIPS (lead's call, exported 2026-09-19: 3 768 500 B);
# `kv25` is the first 8e export, kept so the A/B is one string (`PFA_UV_TILE_MODE=kv25`).
UV_TILE_MODE = os.environ.get("PFA_UV_TILE_MODE", "iso_cut")
# The ku/kv/cutoff tables live in export/foliage_uv.py, which the ENV shrub export and the CPU probe
# import too, so `python3 export/p8e_leaf_probe.py` prints the mode that actually ships (review r3
# finding 1) and there is one place where a mode is defined.
assert UV_TILE_MODE in fuv.UV_TILE_MODES, \
    f"PFA_UV_TILE_MODE={UV_TILE_MODE!r}, expected {sorted(fuv.UV_TILE_MODES)}"
MODE = fuv.UV_TILE_MODES[UV_TILE_MODE]
# r3 finding 3: ku is PER SPECIES like kv. A species with no entry is exported UNTILED at (1.0, 1.0) and
# named in the report - never at the global ku 2.0, which would widen its u window off the dense core at
# the unmodified Phase 5 cutoff (the 0.62-0.76x crown thinning this mode exists to avoid). 8d adds
# backdrop and hall-belt trees, so this is the likeliest next trip.
UV_TILE_U, UV_TILE_V = MODE["u"], MODE["v"]
UV_TILE_DEFAULT = (1.0, 1.0)
# The leaf alphaCutoff this glTF ships, overriding the blend's own cut chain for the tiled cards only.
# Frozen materials: nothing is written back to master_delivery.blend, and env.glb / env_trees_lod1.glb
# (desktop) keep the Phase 5 cuts 0.42-0.50. An unlisted MAT_leaf_* keeps its Phase 5 cut, which is only
# safe because an unlisted SPECIES is also untiled (above) - asserted in the tiling call.
LEAF_CUTOFF = MODE["cutoff"]
# r3 finding 4: `off` is a TRUE baseline - no scale, no per-card v offset, no REPEAT patch, no cutoff
# patch - so `PFA_UV_TILE_MODE=off` reproduces the pre-8e asset.
UV_TILE_V_OFFSET_ON = MODE["v_offset"]
UV_TILE_WRAP = MODE["wrap"]
UV_TILE = UV_TILE and (bool(UV_TILE_U) or bool(UV_TILE_V) or UV_TILE_WRAP)
UV_TILE_V_OFFSET = fuv.V_OFFSET
CROWN_TOP_TOL_REL = 0.08   # LOD2 crown top vs the impostor quad's top, as a fraction of the tallest far tree
PLACE_TOL_M = 0.001        # exported glTF node translation vs to_gltf(trunk_base), per row
ANCHOR_TOL_M = 0.02        # reconstructed prototype bbox/radius vs the manifest's own impostor numbers
# WHICH CARDS THE THINNING KEEPS. This is part of the vertex-AO contract, not a style choice: the bake
# computes one AO value per vertex of the mesh THIS script built, addressed by index, so changing the
# surviving subset silently re-points every value. `stride` is correct (review item 3: `block` leaves bald
# branches); `block` is what out/gate3/trees_far/vertex_ao.npz was baked against. Flipping this to `stride`
# REQUIRES the 16 AO jobs to be re-baked - the COLOR_0 attach below refuses the mismatch rather than
# shipping trees lit by another vertex's occlusion.
CARD_SELECT = "stride"     # "stride" | "block"
# TOPOLOGY REVISION. Bumped whenever anything changes WHICH vertices these meshes have, because the vertex
# AO is addressed by index. rev 1 = CARD_SELECT "block" with no trunk protection (what the first
# vertex_ao.npz was baked against); rev 2 = the stride plus the trunk-base protection below. The COLOR_0
# attach refuses an npz whose `topology_rev` is not this one.
TOPOLOGY_REV = 2
# Decimate COLLAPSE run over a whole branch mesh finds the TRUNK-BASE rings the cheapest edges to remove,
# so two prototypes lost 3.65 m / 4.48 m of trunk and their crowns floated (README item 45). The lowest
# band goes into a vertex group the modifier is told to preserve. A band split was measured and rejected:
# the trunk is long vertical quads, so at 2 m no face lies wholly inside the band at all, and splitting at
# 5 m regressed a prototype that was fine.
# Band chosen by sweeping (band, factor) over the two failures plus a control and a willow: 1 m at factor
# 1.0 puts all four at zmin - base_z = 0.000 for 11-21 extra branch triangles, and the control does not
# move. Wider bands cost more (5 m: +1 304 on the control) for no further gain.
BASE_BAND_M = 1.0
DECIMATE_VG_FACTOR = 1.0   # Decimate `vertex_group_factor`

# ---------------------------------------------------------------- PHASE 9 item 1: BILLBOARD-ONLY ROWS
# QA 23 residual 3 / QA 24 item 3: cam03 submits +1 301 870 triangles and +28 draw calls because THREE of
# the 39 hall-east belt trees (8d r2, note tag HB) stand within the viewer's batch-cull limit of the
# station, and `buildDistanceCull` submits a batch whole as soon as ONE of its rows is inside. The belt is
# a backdrop planting on the hall's east face: 36 of the 39 are never a mesh at any station, so they are
# paying for a close-up nobody takes.
#
# THE RULE, per set: a TAGGED row keeps its mesh only if some QA station could actually DRAW it as a mesh -
# trunk base within `SET["draw_within_m"] + FADE_BAND_M` of a station eye. Every other tagged row is
# BILLBOARD-ONLY: it stays in `tree_far` and keeps its impostor, and simply gets no instance row in this
# set's glb. The radius is the set's own draw distance because the two sets are drawn at different ones
# (desktop walk-up 15 m, mobile far 45 m), so they legitimately keep different numbers of belt rows and the
# walk-up rows are a SUBSET of the far rows (`instance_order_check` below checks exactly that).
#
# WHY NOT ALL 39 (the README's own "billboard-only for the HB rows" pricing). Measured from the cam03
# station (81.0, 12.04, 1.7), 18 mm on 36 mm, 16:9: `ENV_tree_cypress_33` stands 6.5 m from the eye and
# fills ndc x [-2.27, 0.10] and the whole frame height, `ENV_tree_cypress_34` 10.4 m away fills
# x [-1.74, -0.38]. At 1920 px wide that is one impostor atlas texel (81 inner px per frame, 1 K atlas)
# blown up to 17.9 and 11.9 SCREEN pixels - the magnified-card defect Phase 7 built the walk-up set to
# cure. Those two, and the two other rows inside the radius, keep their meshes.
#
# WHAT THE VIEWER MUST DO WITH A BILLBOARD-ONLY ROW (hand-off, not done here). `foliageLazy.js` builds its
# impostor complement from the MESH placements (`placements.find( q => q.billboard === t.id )`, then
# `activateImpostorMeshes`), so a row with no mesh placement gets neither `iNear = 1` - which is right, its
# impostor must never fade out - nor `iIrr`, which is WRONG: it would lose the QA-23 E_placement / E_bake
# modulation and the belt (median ratio 0.2424, it stands in the hall's shade) would draw ~4x too bright.
# The manifest keeps a lighting row for ALL `tree_far` trees (manifest_v4 `trees_lighting_block`) and names
# the excluded rows in `trees.<set>.billboard_only`, so the viewer fix is to set `irr` without `near`.
# The rule itself lives in `export/belt_rule.py`, which imports no bpy, so it can be measured and
# self-tested on CPU (`python3 export/belt_rule.py`) instead of only inside a Blender run.
BELT_TAG = br.BELT_TAG
FADE_BAND_M = br.FADE_BAND_M



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


def collapse(me, target, tmp_coll, protect_below=None):
    """gate1_set.exp_mesh's COLLAPSE path (weld, then iterate the ratio), without the voxel fallback:
    a remeshed branch skeleton is a blob and these meshes are seen close up.

    `protect_below`: a world z. Vertices at or under it go into a vertex group the Decimate modifier is
    told to preserve (`vertex_group` + `vertex_group_factor`), which is what keeps the trunk reaching the
    ground - see BASE_BAND_* above. It is an INFLUENCE, not a hard keep, so the triangle budget still
    holds; the group is remapped by Blender across each modifier apply.
    """
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
    vg_name = None
    if protect_below is not None:
        # MEASURED SEMANTICS: Decimate's vertex group marks what GETS decimated (weight 1 = full ratio,
        # weight 0 = left alone), not what is protected - assigning the base band weight 1 left the whole
        # upper trunk untouched at 10 727 tris against a 2 631 target. So the group holds EVERYTHING ABOVE
        # the band, and the band, at weight 0, is what survives. Membership rather than
        # `invert_vertex_group`, so this does not depend on a flag's meaning.
        idx = [i for i, v in enumerate(me.vertices) if v.co.z > protect_below]
        if idx and len(idx) < len(me.vertices):
            vg = tob.vertex_groups.new(name="DECIMATE_ABOVE_BASE")
            vg.add(idx, 1.0, "REPLACE")
            vg_name = vg.name
    for _ in range(4):
        cur = tris_of(me)
        if cur <= target * 1.05:
            break
        m = tob.modifiers.new("decimate", "DECIMATE")
        m.decimate_type = "COLLAPSE"
        m.ratio = max(1e-4, float(target) / float(cur))
        m.use_collapse_triangulate = True
        if vg_name:
            m.vertex_group = vg_name
            m.vertex_group_factor = DECIMATE_VG_FACTOR
        bpy.ops.object.modifier_apply(modifier=m.name)
        if tris_of(me) >= cur:
            break
    out = tob.data
    tmp_coll.objects.unlink(tob)
    bpy.data.objects.remove(tob, do_unlink=True)
    return out


def thin_and_grow(me, target_tris, scale_max, protect_below=None):
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
    drop, kept, forced = [], [], 0
    for i, c in enumerate(cards):
        # STRIDE vs BLOCK (CARD_SELECT). The components come back in bmesh order, which is broadly spatial,
        # so `(i % 1000) >= keep_pct` keeps the first keep_pct of every run of 1000 - one contiguous block of
        # foliage kept and the rest of the run stripped, i.e. bald branches wherever a run boundary falls
        # (visible at 18-31 % keep, which is where the big crowns land). 997 is coprime with 1000, so the
        # stride is a bijection mod 1000: exactly as many cards survive, scattered through the crown.
        k = (i * 997) % 1000 if CARD_SELECT == "stride" else i % 1000
        # The lowest cards are force-kept whatever the stride says. On the two willows the lowest geometry
        # is hanging fronds BELOW the trunk base, and any subsampling of 9-12 % takes them, which lifts the
        # mesh off the bottom of its own impostor. There are only a handful of them.
        low = protect_below is not None and min(v.co.z for f in c for v in f.verts) <= protect_below
        if low:
            forced += 1
        if k >= keep_pct and not low:
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
                cards_forced_low=forced,
                keep_fraction=round(keep_fraction, 4), card_scale=round(scale, 4),
                leaf_area_m2_before=round(float(area_before), 4),
                leaf_area_m2_after=round(float(area_after), 4),
                leaf_area_kept=round(float(area_after / area_before), 4) if area_before > 0 else None,
                leaf_area_kept_modelled=round(min(1.0, keep_fraction * scale * scale), 4),
                leaf_area_note="leaf_area_kept is measured (sum f.calc_area() after the grow / before the "
                               "thin); leaf_area_kept_modelled is the old keep_fraction * scale^2 estimate, "
                               "kept only so the two can be compared")


def species_of(proto):
    """`ENV_tree_cypress_column_s2_LOD1` -> `cypress_column`: the key UV_TILE_V is written in."""
    assert proto.startswith("ENV_tree_"), proto
    return proto[len("ENV_tree_"):].rsplit("_s", 1)[0]


def tile_card_uvs(me, ku, kv, leaf_slots, v_offset=True):
    """PHASE 8e. Scale every LEAF card's UVs about its own UV centre by (ku, kv) and give it a
    deterministic v offset, so the card shows kv stacked copies of the cluster instead of one.

    Geometry is not touched - no vertex is added, moved or removed - which is what keeps
    out/gate3/trees_far/vertex_ao.npz (POINT domain, addressed by index at `topology_rev`) and the
    instance rows valid. Only faces whose material is a leaf material are eligible, asserted rather than
    assumed: `split_cards` calls a component of <= 2 faces a card, and the bark has such components too
    (a stray decimated twig), and a bark card with tiled UVs would be a striped trunk.
    """
    bm = bmesh.new()
    bm.from_mesh(me)
    uvl = bm.loops.layers.uv.active or bm.loops.layers.uv.get("UVMap")
    assert uvl is not None, f"{me.name} has no UV layer to tile"
    comps = components(bm)
    tiled, skipped, before, after = 0, 0, [], []
    for i, c in enumerate(comps):
        if len(c) > 2 or not all(f.material_index in leaf_slots for f in c):
            skipped += 1
            continue
        loops = [lp for f in c for lp in f.loops]
        cu = sum(lp[uvl].uv.x for lp in loops) / len(loops)
        cv = sum(lp[uvl].uv.y for lp in loops) / len(loops)
        ov = (i * UV_TILE_V_OFFSET) % 1.0 if v_offset else 0.0
        for lp in loops:
            uv = lp[uvl].uv
            before.append((uv.x, uv.y))
            uv.x = cu + (uv.x - cu) * ku
            uv.y = cv + (uv.y - cv) * kv + ov
            after.append((uv.x, uv.y))
        tiled += 1
    bm.to_mesh(me)
    bm.free()
    me.update()
    b = np.array(before) if before else np.zeros((1, 2))
    a = np.array(after) if after else np.zeros((1, 2))
    return dict(uv_tile_u=ku, uv_tile_v=kv, v_offset=bool(v_offset),
                cards_tiled=tiled, components_skipped=skipped,
                uv_before=[round(float(v), 4) for v in (b.min(0)[0], b.max(0)[0], b.min(0)[1], b.max(0)[1])],
                uv_after=[round(float(v), 4) for v in (a.min(0)[0], a.max(0)[0], a.min(0)[1], a.max(0)[1])],
                uv_note="u_min u_max v_min v_max; the tiled v range leaves 0-1 by design and is served by "
                        "the REPEAT samplers this script patches into the written glTF")


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
    # carry 6: bmesh can hand back geometry the exporter will silently drop or mis-index (loose verts,
    # duplicate faces, bad loops). validate() repairs it and returns whether it changed anything.
    # MEASURED: it returns True on all 16 prototypes while the vertex and face counts are unchanged and the
    # packed env_trees.glb is byte-identical (sha256 7e17167d...), so on these meshes it is normalising
    # something that is not geometry. A bare True is therefore not an alarm; the COUNTS are. They are
    # recorded before and after so a real repair - which would move every vertex index and invalidate the
    # vertex AO - is visible as a number rather than a flag.
    before = (len(out.vertices), len(out.polygons))
    fixed = bool(out.validate(verbose=False, clean_customdata=False))
    after = (len(out.vertices), len(out.polygons))
    return out, dict(returned=fixed, verts=before[0], faces=before[1],
                     verts_after=after[0], faces_after=after[1],
                     geometry_changed=(before != after))


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
    # PHASE 9 item 1: the tag and the stations the billboard-only rule measures against
    belt, belt_p, belt_doc = br.belt_indices(man)
    eyes = br.station_eyes(man)
    assert br.DRAW_WITHIN_M[SET_NAME] == SET["draw_within_m"], (
        f"belt_rule.DRAW_WITHIN_M[{SET_NAME!r}] is {br.DRAW_WITHIN_M[SET_NAME]} and this set says "
        f"{SET['draw_within_m']} - the analysis and the export would place different rows")

    rep = dict(schema=SCHEMA, generated=time.strftime("%Y-%m-%dT%H:%M:%S"),
               generator="export/trees_far.py", source_blend=bpy.data.filepath,
               set=SET_NAME, set_params={k: v for k, v in SET.items()},
               manifest=str(man_p), tri_target=TRI_TARGET, branch_min=BRANCH_MIN, branch_max=BRANCH_MAX,
               card_scale_max=CARD_SCALE_MAX)

    tmp = bpy.data.collections.new("EXP_TREEFAR_TMP")
    bpy.context.scene.collection.children.link(tmp)
    exp = bpy.data.collections.new("EXP_TREEFAR")
    bpy.context.scene.collection.children.link(exp)

    dg = bpy.context.evaluated_depsgraph_get()
    step = g0.Step("trees_far:meshes")
    protos_out, rejected, untiled_species = {}, {}, {}
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
        src.name = f"{MESH_PREFIX}{p}_src"
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
        # the band is measured from the SOURCE's own base (== the manifest's base_z_m, asserted above),
        # so the willows' fronds below the trunk base are inside it.
        base_z = float(slo[2])
        protect_below = base_z + BASE_BAND_M
        branch = collapse(branch, branch_target, tmp, protect_below=protect_below)
        branch_tris = tris_of(branch)
        card_budget = max(0, TRI_TARGET - branch_tris)
        cst = thin_and_grow(cards, card_budget, CARD_SCALE_MAX, protect_below=protect_below)
        # PHASE 8e, after the thin and the grow (so it sees exactly the cards that ship) and before the
        # join (so the bark cannot be reached): the leaf-card UV tiling, `far` set only.
        uvt = None
        if UV_TILE:
            leaf_slots = {i for i, m in enumerate(materials) if m and m.name.startswith("MAT_leaf")}
            assert leaf_slots, f"{p}: no MAT_leaf_* material slot to tile"
            sp = species_of(p)
            known = sp in UV_TILE_U and sp in UV_TILE_V
            ku, kv = (UV_TILE_U[sp], UV_TILE_V[sp]) if known else UV_TILE_DEFAULT
            if not known:
                untiled_species[sp] = untiled_species.get(sp, 0) + 1
            uvt = tile_card_uvs(cards, ku, kv, leaf_slots,
                                v_offset=UV_TILE_V_OFFSET_ON and known)
            uvt["species"] = sp
            uvt["species_known"] = known
            assert known or (ku, kv) == (1.0, 1.0), \
                f"{p}: species {sp!r} is not in mode {UV_TILE_MODE!r} and must export untiled"
            assert uvt["cards_tiled"] > 0 or not known, f"{p}: the UV tiling matched no leaf card"
        me, mesh_repaired = join(branch, cards, f"{MESH_PREFIX}{p}", materials)
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
            mesh_validate=mesh_repaired,
            base_z_m=round(float(slo[2]), 4), protect_below_z=round(float(protect_below), 4),
            bbox_min_z_over_base_m=round(float(lo[2]) - float(slo[2]), 4),
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
            reduction=dict(**st, **cst),
            uv_tiling=uvt)
    step.done(prototypes=len(protos_out),
              tris=sum(v["tris"] for v in protos_out.values()),
              worst=max(v["tris"] for v in protos_out.values()))
    rep["prototypes"] = protos_out
    rep["lod2_objects_rejected"] = rejected

    # ---------------------------------------------------------------- the placements
    # PHASE 9 item 1: a TAGGED row (HB, the 8d hall-east belt) is placed only if a QA station could draw it
    # as a mesh at all - see the BILLBOARD-ONLY ROWS note at the top of this file. Everything else is
    # untouched, and the row INDEX is still the `tree_far` index, so `TREEFAR_###` names, the manifest
    # placements' `index` and the cross-set order check all stay keyed to the same list.
    step = g0.Step("trees_far:placements")
    keep_radius_m = float(SET["draw_within_m"]) + FADE_BAND_M
    placements, far_kept, billboard_only, worst_dev = [], [], [], 0.0
    for i, row in enumerate(far):
        if i in belt:
            s_name, s_d = br.nearest_station(eyes, row["trunk_base"])
            if s_d > keep_radius_m:
                billboard_only.append(dict(
                    index=i, tag=BELT_TAG, billboard=row["billboard"], source_tree=row["source_tree"],
                    prototype=proto_map[row["prototype"]], source_prototype=row["prototype"],
                    loc=[round(float(v), 4) for v in row["trunk_base"]],
                    height_m=row["height_m"], walk_dist_m=row["walk_dist_m"],
                    nearest_station=s_name, nearest_station_m=round(s_d, 2)))
                continue
            # a tagged row inside the radius falls through and is placed like any other
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
        pl = dict(index=i, object=no.name, prototype=p, mesh=me.name,
                  source_prototype=row["prototype"], source_tree=row["source_tree"],
                  billboard=row["billboard"],
                  loc=[round(float(v), 4) for v in row["trunk_base"]],
                  scale=round(s, 6), height_m=row["height_m"],
                  walk_dist_m=row["walk_dist_m"])
        if i in belt:
            pl["tag"] = BELT_TAG
            pl["nearest_station"], _d = br.nearest_station(eyes, row["trunk_base"])
            pl["nearest_station_m"] = round(_d, 2)
        placements.append(pl)
        far_kept.append(row)
    # 8d r2: the far list grows with the scene (the hall-east belt took it 127 -> 166). What has to hold
    # is that EVERY far row got a placement here, not a fixed count; the count itself is reported and
    # checked against the manifest the placements were read from.
    assert len(placements) + len(billboard_only) == len(far), (
        f"{len(placements)} placements + {len(billboard_only)} billboard-only rows for {len(far)} far rows "
        f"- every far tree must be either placed or explicitly excluded")
    assert {pl["index"] for pl in placements}.isdisjoint({b["index"] for b in billboard_only}), \
        "a far row is both placed and billboard-only"
    assert all(b["index"] in belt for b in billboard_only), \
        "only a TAGGED row may be billboard-only: an untagged far tree lost its mesh"
    # r5 finding 6: and `far` itself is pinned against the EXPORT SET, not against itself, so a manifest
    # left behind by an earlier run cannot quietly shrink this block.
    _eset = next((q for q in (g1.OUT / "export_set.json", g0.MAIN_ROOT / "export/out/gate1/export_set.json")
                  if q.exists()), None)
    if _eset is not None:
        _want = json.loads(_eset.read_text())["tree_rule"]["far_billboards"]
        assert len(far) == _want, (f"the manifest has {len(far)} far trees and export_set.json "
                                   f"{_want} - manifest_v4 has not been re-run for this export set")

    # ---- THE PLACED MESH, IN WORLD SPACE, AGAINST THE IMPOSTOR QUAD (per row).
    # This is the check the export did not have: `no.location` was right all along, but the mesh under it
    # carried the prototype's own world position, so the tree DREW ~300 m away while every assert passed.
    # Nothing here is derived from `no.location`; it is the evaluated world bounding box of the geometry.
    bpy.context.view_layer.update()
    worst_xy, worst_xy_row, worst_top, worst_top_row = 0.0, None, 0.0, None
    for pl, row in zip(placements, far_kept):
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
    step.done(placements=len(placements), billboard_only=len(billboard_only),
              worst_crown_top_dev_mm=round(worst_dev * 1000, 1))
    rep["placements"] = placements
    rep["billboard_only"] = billboard_only
    rep["billboard_only_rule"] = dict(
        tag=BELT_TAG, tagged_rows=len(belt), placed=len(belt) - len(billboard_only),
        excluded=len(billboard_only), far_rows=len(far), placements=len(placements),
        radius_m=keep_radius_m, draw_within_m=float(SET["draw_within_m"]), fade_band_m=FADE_BAND_M,
        stations={k: [round(v, 3) for v in e] for k, e in sorted(eyes.items())},
        tag_source=str(belt_p), tag_source_count=int(belt_doc["count"]),
        rule=(f"a row tagged {BELT_TAG!r} keeps its mesh only if its trunk base is within "
              f"draw_within_m ({SET['draw_within_m']} m, this set's own viewer distance) + the fade band "
              f"({FADE_BAND_M} m) of a QA station eye; beyond that the fragment dissolve discards every "
              f"fragment, so no station can ever see the mesh and the row ships as its impostor alone"),
        excluded_tris=sum(protos_out[b["prototype"]]["tris"] for b in billboard_only),
        viewer_hand_off=("a billboard-only row has no mesh placement, so foliageLazy.js's impostor "
                         "complement skips it: it correctly keeps iNear = 0 but also loses iIrr, the "
                         "QA-23 E_placement / E_bake modulation. `trees.far_mesh.lighting` still carries a "
                         "row for every tree_far tree and `billboard_only` names the excluded ones, so the "
                         "viewer fix is to set irr without near."))
    rep["placement_check"] = dict(
        rule="s = tree_far[i].height_m / impostors.prototypes[p].height_above_base_m, translation = "
             "trunk_base, rotation ignored - manifest `impostors.placement`, verbatim",
        translation=("asserted AFTER the export: every env_trees.gltf node translation against "
                     "to_gltf(trunk_base) = (x, z, -y), and every node scale against s, on every row "
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
    # Only the `far` set. The AO npz is addressed by VERTEX INDEX against the meshes the `far` reduction
    # builds at its own topology revision, so there is nothing valid to attach to a 30 k walk-up mesh; the
    # brief gives the viewer's interior term that job instead.
    step = g0.Step(f"trees_far:color0:{SET_NAME}")
    ao_rep = {}
    ao_p = None if not SET["color0"] else next((q for q in (OUT3 / "vertex_ao.npz",
                             g0.MAIN_ROOT / "export/out/gate3/trees_far/vertex_ao.npz") if q.exists()),
                                                None)
    # THE TOPOLOGY REVISION GATE. The AO is addressed BY VERTEX INDEX, so an npz is only valid for the
    # exact meshes the hand-off blend carried. Both of this round's fixes - the card-thinning stride and the
    # trunk-base protection - change WHICH vertices exist, and the stride keeps the same card COUNT, so the
    # shape check below cannot see the difference. The npz therefore has to name the revision it was baked
    # against: `topology_rev` inside the npz, or in a sibling vertex_ao.json. A mismatch is NOT fatal - the
    # export still has to be able to publish a new revision for the bake to work from - but it never
    # attaches, and it says so loudly and in the report.
    ao_rev, ao_rev_src = None, None
    if ao_p is not None:
        try:
            zz = np.load(str(ao_p))
            if "topology_rev" in zz.files:
                ao_rev, ao_rev_src = int(np.asarray(zz["topology_rev"]).reshape(-1)[0]), ao_p.name
        except Exception:
            pass
        side = ao_p.with_suffix(".json")
        if ao_rev is None and side.exists():
            ao_rev, ao_rev_src = (json.loads(side.read_text()) or {}).get("topology_rev"), side.name
        if ao_rev != TOPOLOGY_REV:
            print(f"[trees_far] REFUSING to attach COLOR_0: {ao_p.name} declares topology_rev "
                  f"{ao_rev!r} (from {ao_rev_src or 'nothing - it predates the field'}), this export builds "
                  f"rev {TOPOLOGY_REV} (CARD_SELECT={CARD_SELECT!r}, trunk-base protection on). Every AO "
                  f"value would land on a different vertex. Re-bake the 16 jobs against this run's "
                  f"trees_far_lod2.blend and stamp them topology_rev {TOPOLOGY_REV}.", file=sys.stderr)
            rep["color0_refused"] = dict(npz=str(ao_p), npz_topology_rev=ao_rev,
                                         export_topology_rev=TOPOLOGY_REV, card_select=CARD_SELECT)
            ao_p = None
    if ao_p is not None:
        z = np.load(str(ao_p))
        dts = sorted({str(np.asarray(z[f]).dtype) for f in z.files if f != "topology_rev"})
        assert dts == ["float32"], f"{ao_p.name} is {dts}, the contract is float32 (gltf_gate1.py's rule)"
        rng = float(np.float32(max((float(np.asarray(z[f]).max()) for f in z.files
                                    if f != "topology_rev"), default=1.0))) or 1.0
        for mn in [f for f in z.files if f != "topology_rev"]:
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
                             topology_rev=TOPOLOGY_REV,
                             encode="COLOR_0 = sqrt(linear / range); viewer decodes linear = COLOR_0^2 * range")
    else:
        rep["color0"] = dict(
            source=None, topology_rev=TOPOLOGY_REV,
            note=("this set ships no COLOR_0 by design (brief item 2): the viewer's interior term carries "
                  "the occlusion, and the AO npz is addressed by vertex index against the `far` meshes"
                  if not SET["color0"] else
                  "out/gate3/trees_far/vertex_ao.npz (item B) not present or not at this topology "
                  "revision: env_trees.glb ships without COLOR_0, re-run this script and "
                  "gltf_pack.sh --trees when the bake lands"))
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
    # ---- PHASE 8e: REPEAT samplers on the leaf maps, this glTF only.
    # The tiled cards' v leaves 0-1, and the shipped samplers are CLAMP_TO_EDGE (Blender writes 33071 for
    # an image node set to EXTEND), which would smear the texture's edge texel over every tile past the
    # first. Patched HERE, in the written glTF, rather than by touching the image nodes: the MAT_leaf_*
    # materials and their textures are frozen (Phase 5 look), master_delivery.blend is opened read-only,
    # and the patch then cannot reach env.glb / env_trees_lod1.glb, whose leaf UVs are all inside 0-1
    # (verified) and which include the TIER-0 group env_t0.glb - that file must stay byte-identical.
    # ---- PHASE 8e r2 finding 2: the leaf alphaCutoff the TILED cards ship with.
    # Widening the u window (ku > 1) is what narrows a blade, and it costs coverage; the cut bought it
    # back. Per MATERIAL, because that is what a glTF material carries, and in this glTF only.
    cutoff_patch = {}
    if UV_TILE and UV_TILE_WRAP and LEAF_CUTOFF:
        for m in doc.get("materials", []):
            want = LEAF_CUTOFF.get(m.get("name"))
            if want is None:
                continue
            assert m.get("alphaMode") == "MASK", \
                f"{gltf_p.name}: {m.get('name')} is {m.get('alphaMode')}, not MASK - a cutoff means nothing"
            cutoff_patch[m["name"]] = [m.get("alphaCutoff"), want]
            m["alphaCutoff"] = want
        assert len(cutoff_patch) == len(LEAF_CUTOFF), \
            f"{gltf_p.name}: patched {sorted(cutoff_patch)} of {sorted(LEAF_CUTOFF)}"
    # ---- PHASE 8e: REPEAT samplers on the leaf maps, this glTF only (export/foliage_uv.py does the
    # patch: it clones a sampler shared with any texture outside the tiled set, never patches it, and
    # asserts that nothing else moved). `off` skips it, so that mode is the pre-8e asset.
    wrap_patch = None
    if UV_TILE and UV_TILE_WRAP:
        leaf_mats = [m.get("name") for m in doc.get("materials", [])
                     if (m.get("name") or "").startswith("MAT_leaf")]
        assert leaf_mats, f"{gltf_p.name}: no MAT_leaf_* material to patch"
        wrap_patch = fuv.patch_samplers(doc, leaf_mats, gltf_p.name)
    if alpha_mats or wrap_patch or cutoff_patch:
        gltf_p.write_text(json.dumps(doc))
        doc = json.loads(gltf_p.read_text())
    # ---- r2 finding 4: the "every other root's leaf UVs are inside 0-1" claim, as a check instead of
    # prose. The NON-tiled set is what desktop draws and what lets the REPEAT patch above stay a no-op
    # for env.glb / env_trees_lod1.glb; if a future Sapling change or a new prototype ever leaves 0-1
    # there, it must fail here rather than smear in a viewer nobody is watching.
    uv_range = fuv.leaf_uv_range(doc, gltf_p)
    if not UV_TILE:
        assert uv_range and uv_range["min"] >= -1e-4 and uv_range["max"] <= 1 + 1e-4, \
            (f"{gltf_p.name}: leaf TEXCOORD_0 is {uv_range} - the {SET_NAME} set is not UV-tiled, so its "
             f"cards must stay inside 0-1 (CLAMP samplers everywhere else depend on it)")
    # ---- the placement check that can fail: the EXPORTED node translations, per row.
    # `no.location` was assigned from `trunk_base`, so comparing the two in Blender proves nothing. This
    # crosses the exporter boundary - the Z-up -> Y-up swap (x, y, z) -> (x, z, -y), `export_apply`, and the
    # float32 round trip - which is where a placement can really move, and it is the same key the
    # per-placement irradiance join uses after gltfpack drops the node names.
    nodes = {n.get("name"): n for n in doc.get("nodes", []) if "mesh" in n}
    assert len(nodes) == len(placements), \
        f"{gltf_p.name} has {len(nodes)} mesh nodes, the export placed {len(placements)}"
    worst_t, worst_s, worst_row = 0.0, 0.0, None
    for pl, row in zip(placements, far_kept):
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
    # ---- SAME INSTANCE ORDER AS THE OTHER SET, asserted against the file, not assumed from the code.
    # The brief's requirement is that the viewer can reuse `env_trees.glb`'s placement rows and its
    # per-placement irradiance for this glb. After gltfpack -mi the node NAMES are gone and the only key
    # left is the row's position in its mesh's instancing buffer, so "same order" has to mean: the same
    # mesh-node sequence, name for name, translation for translation. Both sets build it from the same
    # `far` list in the same loop, but that is the kind of invariant that holds until somebody sorts
    # something, so it is read back out of the two written glTFs and compared row by row.
    order_check = None
    other = SET.get("order_against")
    if other:
        op = g1.OUT / f"{other}.gltf"
        assert op.exists(), (f"{gltf_p.name}: the {other} set's glTF is not at {op} - build it first "
                             f"(PFA_TREES_SET={next(k for k, v in SETS.items() if v['gltf_name'] == other)}"
                             f"), because this set's rows must match its order")
        odoc = json.loads(op.read_text())
        orows = [n for n in odoc.get("nodes", []) if "mesh" in n]
        mrows = [nodes[pl["object"]] for pl in placements]
        # PHASE 9 item 1: the two sets no longer hold the SAME rows. The billboard-only radius is each
        # set's own draw distance (walk-up 15 m, far 45 m), so the walk-up set keeps FEWER belt rows and
        # its rows are a SUBSEQUENCE of the far set's. That is the invariant the viewer needs - it joins a
        # row to a placement by translation, and it reads its placement list from THIS set's own manifest
        # block - plus the one it cannot check: a row that is in both sets must stand in the same place
        # and in the same relative order. Equality would be the stronger claim, and it is asserted whenever
        # neither set excluded anything.
        opos = {n.get("name"): i for i, n in enumerate(orows)}
        assert len(mrows) <= len(orows), \
            f"{gltf_p.name} has {len(mrows)} mesh nodes, {op.name} only {len(orows)} - this set is the subset"
        worst_o, worst_o_row, last = 0.0, None, -1
        for i, b in enumerate(mrows):
            nm = b.get("name")
            j = opos.get(nm)
            assert j is not None, (
                f"row {i}: {gltf_p.name} has node {nm!r}, which {op.name} does not - this set placed a row "
                f"the other one dropped, so the two billboard-only rules disagree about which rows exist")
            assert j > last, (
                f"row {i}: {nm!r} is at position {j} in {op.name} but the previous row was at {last} - the "
                f"two sets are not in the same instance order and the placement rows cannot be reused")
            last = j
            a = orows[j]
            d = max(abs(float(x) - float(y))
                    for x, y in zip(a.get("translation", (0, 0, 0)), b.get("translation", (0, 0, 0))))
            if d > worst_o:
                worst_o, worst_o_row = d, nm
        assert worst_o < PLACE_TOL_M, (
            f"{gltf_p.name}: worst translation difference against {op.name} is {worst_o * 1000:.3f} mm on "
            f"{worst_o_row}")
        order_check = dict(against=op.name, rows=len(mrows), rows_other=len(orows),
                           subset=len(mrows) < len(orows),
                           only_in_other=sorted(set(opos) - {n.get("name") for n in mrows}),
                           worst_translation_delta_m=round(worst_o, 6), worst_row=worst_o_row,
                           rule="every node of this set is a node of the other set's glTF, in the same "
                                "relative order and at the same translation; this set may hold FEWER rows "
                                "(its billboard-only radius is its own draw distance) but never a row the "
                                "other set does not have - the positional join is the only key that "
                                "survives gltfpack -mi")
    # ---- COLOR_0 MUST BE THE AO, AND IT IS CHECKED IN THE DATA, NOT BY NAME.
    # These meshes carry exactly ONE colour layer ('irradiance'), but the exporter writes TWO attributes:
    # a CONSTANT WHITE COLOR_0 (unsigned byte, from the material side) and the real layer as COLOR_1
    # (unsigned short). env.gltf's near trees come out with a single COLOR_0, so this is specific to the
    # far-tree materials. Shipping that as-is is worse than shipping no AO at all: three.js multiplies
    # COLOR_0 into base colour, so every far tree would be multiplied by white - the AO silently doing
    # nothing - while every "COLOR_0 present" check passed. So: decode each colour attribute, require
    # exactly one that is not constant, promote it to COLOR_0 and drop the rest.
    if ao_rep:
        bin_uri = doc["buffers"][0]["uri"]
        blob = (gltf_p.parent / bin_uri).read_bytes()
        comp = {5121: ("u1", 255.0), 5123: ("u2", 65535.0), 5126: ("f4", 1.0)}

        def is_constant(ai):
            acc = doc["accessors"][ai]
            bv = doc["bufferViews"][acc["bufferView"]]
            fmt, norm = comp[acc["componentType"]]
            n = acc["count"] * (4 if acc["type"] == "VEC4" else 3)
            off = bv.get("byteOffset", 0) + acc.get("byteOffset", 0)
            v = np.frombuffer(blob, dtype=np.dtype(fmt), count=n, offset=off).astype(np.float64) / norm
            return bool(v.max() - v.min() < 1e-6), float(v.min()), float(v.max())

        promoted, dropped, kept_stats = 0, 0, {}
        for m_ in doc.get("meshes", []):
            for pr in m_["primitives"]:
                at = pr["attributes"]
                cols = sorted(k for k in at if k.startswith("COLOR_"))
                if not cols:
                    continue
                live = [(k, is_constant(at[k])) for k in cols]
                varying = [(k, st) for k, st in live if not st[0]]
                assert len(varying) == 1, (
                    f"{m_.get('name')}: {len(varying)} non-constant colour attributes out of {cols} "
                    f"({[(k, round(st[1], 4), round(st[2], 4)) for k, st in live]}). Exactly one is the "
                    f"vertex AO; this export cannot tell which one the viewer should use.")
                keep, st = varying[0]
                for k in cols:
                    if k != keep:
                        del at[k]
                        dropped += 1
                if keep != "COLOR_0":
                    at["COLOR_0"] = at.pop(keep)
                    promoted += 1
                kept_stats[m_.get("name")] = [round(st[1], 5), round(st[2], 5)]
        gltf_p.write_text(json.dumps(doc))
        doc = json.loads(gltf_p.read_text())
        rep["color0"]["gltf_fixup"] = dict(
            promoted_to_color0=promoted, constant_attributes_dropped=dropped,
            kept_range_per_mesh=kept_stats,
            why="the exporter emitted a CONSTANT WHITE COLOR_0 beside the real layer; three.js multiplies "
                "COLOR_0 into base colour, so shipping it would have made the AO a no-op while every "
                "presence check passed. The surviving attribute is chosen by DECODING the buffer and "
                "requiring exactly one non-constant colour attribute per primitive.")

    attr = {}
    for m_ in doc.get("meshes", []):
        for pr in m_["primitives"]:
            for k in pr["attributes"]:
                attr.setdefault(k, set()).add(m_.get("name"))
    assert not ao_rep or not attr.get("COLOR_1"), \
        f"COLOR_1 survived on {len(attr['COLOR_1'])} meshes after the fixup"
    assert not ao_rep or len(attr.get("COLOR_0", ())) == len(protos_out), \
        f"COLOR_0 on {len(attr.get('COLOR_0', ()))} meshes, expected all {len(protos_out)}"
    rep["gltf"] = dict(
        path=gltf_p.name, bytes=gltf_p.stat().st_size, nodes=len(doc.get("nodes", [])),
        meshes=len(doc.get("meshes", [])), materials=[m.get("name") for m in doc.get("materials", [])],
        images=[i.get("uri") for i in doc.get("images", [])],
        placed_tris=sum(protos_out[pl["prototype"]]["tris"] for pl in placements),
        unique_tris=sum(v["tris"] for v in protos_out.values()),
        attributes={k: len(v) for k, v in sorted(attr.items())},
        color0_meshes=sorted(x for x in attr.get("COLOR_0", set()) if x),
        instance_order_check=order_check,
        gltf_translation_check=dict(
            rows=len(placements), tol_m=PLACE_TOL_M,
            worst_translation_residual_m=round(worst_t, 6), worst_translation_row=worst_row,
            worst_scale_residual=round(worst_s, 9),
            rule="every node translation == to_gltf(trunk_base) = (x, z, -y), every node scale == "
                 "height_m / height_above_base_m, read back out of the written glTF"),
        alpha_mask_materials=alpha_mats,
        leaf_uv_range=uv_range,
        uv_tiling=(dict(set=SET_NAME, mode=UV_TILE_MODE, u=UV_TILE_U, v=UV_TILE_V,
                        v_offset=UV_TILE_V_OFFSET, leaf_cutoff=cutoff_patch,
                        species_not_tiled=untiled_species, wrap_patch=wrap_patch,
                        samplers=[{k: v for k, v in s.items() if k.startswith("wrap")}
                                  for s in doc.get("samplers", [])])
                   if UV_TILE else dict(set=SET_NAME, applied=False)),
        alpha_mode_materials={m.get("name"): [m.get("alphaMode"), m.get("alphaCutoff")]
                              for m in doc.get("materials", []) if m.get("alphaMode")},
        args=sorted(kwargs))
    step.done(gltf_p, bytes=gltf_p.stat().st_size, nodes=len(doc.get("nodes", [])))

    # ---------------------------------------------------------------- the bake hand-off blend
    # `far` only: it exists so the bake can compute the vertex AO against these exact meshes. The walk-up
    # set has no bake, and writing it here would OVERWRITE the `far` set's topology.json and
    # trees_far_lod2.blend - the two files the AO's revision gate is keyed on.
    if not SET["hand_off"]:
        rep["hand_off"] = dict(written=False,
                               why="the walk-up set has no vertex-AO bake; writing topology.json here "
                                   "would overwrite the `far` set's hand-off and invalidate its revision "
                                   "gate")
        rep["wall_s"] = round(time.time() - t_start, 1)
        (g1.OUT / SET["report"]).write_text(json.dumps(rep, indent=1) + "\n")
        print(f"[trees_far:{SET_NAME}] {len(protos_out)} prototypes "
              f"{min(v['tris'] for v in protos_out.values())}-"
              f"{max(v['tris'] for v in protos_out.values())} tris, {len(placements)} placements "
              f"(+{len(billboard_only)} {BELT_TAG} rows billboard-only beyond {keep_radius_m:.0f} m), "
              f"{gltf_p.stat().st_size} B glTF -> {g1.OUT / SET['report']}")
        return
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
                topology_rev=TOPOLOGY_REV,
                topology_rev_note=("rev 1 = CARD_SELECT 'block', no trunk-base protection (what the FIRST "
                                   "vertex_ao.npz was baked against). rev 2 = the (i*997)%1000 stride plus "
                                   "the Decimate vertex-group protection of the lowest band, so the trunk "
                                   "reaches the ground. The AO is addressed by VERTEX INDEX: an npz is only "
                                   "valid for the revision it was baked against, and rev 2 keeps the same "
                                   "card COUNT as rev 1, so a count check cannot tell them apart. Stamp the "
                                   "npz with `topology_rev` (an npz key, or a sibling vertex_ao.json); "
                                   "export/trees_far.py refuses to attach any other value. Per-prototype "
                                   "vertex counts are `prototypes[p].verts`."),
                vertex_counts={k: v["verts"] for k, v in sorted(protos_out.items())},
                card_select_note="which leaf cards the thinning keeps. The vertex AO is addressed by vertex "
                                 "index, so an npz baked against this blend is only valid while this value "
                                 "is unchanged; export/trees_far.py refuses to attach across a change.",
                lod2_objects_rejected=rejected,
                billboard_only=billboard_only,
                billboard_only_rule=rep["billboard_only_rule"],
                billboard_only_note=("these `tree_far` rows have NO mesh in this set (Phase 9 item 1) and "
                                     "therefore no entry in `placements` below. The per-placement "
                                     "irradiance bake still covers every `tree_far` row - trees_far_set.py "
                                     "iterates the manifest, not this list - which is what keeps the "
                                     "impostors of the excluded rows modulated."),
                anchor_note=("`anchor` is the point in PROTOTYPE WORLD SPACE that this export subtracts "
                             "from the mesh, so that a placement is exactly `location = trunk_base, "
                             "scale = s`. It is the impostor's own axis: the prototype bbox XY centre at "
                             "z = 0 (manifest `impostors.placement`), verified per prototype by "
                             "reproducing `radius_m` - see `anchor_check`. Anything baked against these "
                             "meshes must subtract the SAME anchor."),
                prototypes={k: {**{kk: v[kk] for kk in
                                   ("mesh", "tris", "verts", "materials", "uv_layers", "bbox_min",
                                    "bbox_max", "height_above_base_m", "src_tris", "reduction")},
                                "anchor": v["anchor_check"]["anchor"],
                                "anchor_check": v["anchor_check"]}
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
    (g1.OUT / SET["report"]).write_text(json.dumps(rep, indent=1) + "\n")
    print(f"[trees_far] {len(protos_out)} prototypes "
          f"{min(v['tris'] for v in protos_out.values())}-{max(v['tris'] for v in protos_out.values())} tris, "
          f"{len(placements)} placements (+{len(billboard_only)} {BELT_TAG} rows billboard-only beyond "
          f"{keep_radius_m:.0f} m) -> {g1.OUT / SET['report']}")


if __name__ == "__main__":
    main()
