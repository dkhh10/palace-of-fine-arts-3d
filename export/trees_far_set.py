"""Phase 6c item 2 (bake): build the blend the far-tree irradiance bake needs, and queue its 36 jobs.

    scripts/blender_run.sh 900 -- --background --python export/trees_far_set.py

CPU only (it opens and saves blends; nothing is rendered). Writes, under export/out/gate3/trees_far/:

  trees_far_irr.blend     gate3_bake.blend with the export's 16 LOD2 prototype meshes placed at the 127
                          `tree_far` placements
                          and the 127 `source_tree` objects hidden from render - i.e. the scene as it ships
                          once the far trees are meshes. That is the geometry the mesh path's `_IRRADIANCE`
                          and vertex AO belong to.

E_bake needs no blend of its own. Review r1 finding 5: the divisor must describe THE BODY THAT PRODUCED THE
ATLAS, which is the `_LOD1` prototype object in gate3_imp.blend that job `imp_<proto>` rendered - not the
export's LOD2 reduction. The 16 E_bake jobs therefore run on gate3_imp.blend itself, on those objects, with
every other mesh but the lawn hidden exactly as the impostor job hides it, at the same rig. Both sides of the
ratio use the same reducer (`mean_nonzero` over the cov mask, gate3_instance_compose.py:84) and the same
shadow-ray cut-out override, so what does NOT cancel is only the LOD1 -> LOD2 crown density, which is
reported per prototype as `cov`.

THE PLACEMENT ANCHOR IS THE EXPORT'S, READ AND NOT RECOMPUTED (review r2 finding 1). A far tree is placed

    matrix_world = Translation(trunk_base) @ Scale(s) @ Translation(-anchor_p)

where `anchor_p` = `topology.json prototypes[p].anchor` - the LOD2 mesh's bbox XY centre at z = 0, the point
the impostor rotates about, which `export/trees_far.py` subtracts from the mesh and asserts against the
manifest's `radius_m` / `base_z_m`. There is exactly one anchor and exactly one place it is computed. This
script's FIRST run derived its own - the prototype object's world translation - which is a different point
(up to (3.44, 2.66) m; over 1 m on six prototypes), so the first E_placement set was baked with trees metres
from where `env_trees.glb` draws them; those four `tfirr_*` jobs were re-run. The assert is on the placed
mesh's world bbox, never on the transform algebra, because the algebraic form is an identity that passes
whatever anchor it is given - which is exactly how the first run's error survived.
"""
import bpy
import json
import os
import sys
import time

from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gate0_common as g0      # noqa: E402
import gate3_common as g3      # noqa: E402

TF = g3.OUT / "trees_far"
LOD2_BLEND = TF / "trees_far_lod2.blend"
IRR_BLEND = TF / "trees_far_irr.blend"
SPP_AO = 64            # brief item 2
SPP_IRR = 128          # g3.SAMPLES_VERTEX - the same as the shrub instance bake, so the two are comparable
IRR_JOBS = 4


def pick(rel):
    for base in (g3.ROOT, g3.MAIN_ROOT):
        p = base / rel
        if p.exists():
            return p
    raise FileNotFoundError(rel)


def append_objects(src):
    """Append every object of `src` into the open file and link it to the scene collection."""
    with bpy.data.libraries.load(str(src)) as (df, dt):
        dt.objects = list(df.objects)
        names = list(df.objects)
    out = []
    for ob in dt.objects:
        if ob is None:
            continue
        bpy.context.scene.collection.objects.link(ob)
        out.append(ob)
    assert len(out) == len(names), f"appended {len(out)} of {len(names)} objects from {src}"
    return out


def dedupe_materials():
    """An append brings MAT_leaf_broadleaf in as MAT_leaf_broadleaf.001 beside the one this blend already
    has. Remap the copies onto the originals: the bake must use the blend's OWN (Gate 2 relinked) materials,
    and the shadow-ray override has to wrap one datablock, not two."""
    remapped = []
    for m in list(bpy.data.materials):
        base, _, suf = m.name.rpartition(".")
        if not base or not suf.isdigit():
            continue
        orig = bpy.data.materials.get(base)
        if orig is None or orig is m:
            continue
        m.user_remap(orig)
        remapped.append(m.name)
        bpy.data.materials.remove(m)
    return remapped


def main():
    t0 = time.time()
    TF.mkdir(parents=True, exist_ok=True)
    topo = json.loads((TF / "topology.json").read_text())
    man = json.loads(pick("export/out/gate3/manifest.json").read_text())
    imp = man["impostors"]
    protos = sorted(topo["prototypes"])
    assert len(protos) == 16, f"{len(protos)} prototypes in topology.json"
    mesh_of = {p: topo["prototypes"][p]["mesh"] for p in protos}
    rep = dict(generated=time.strftime("%Y-%m-%dT%H:%M:%S"), generator="export/trees_far_set.py",
               prototypes=len(protos), placements=len(topo["placements"]))

    # ---------------------------------------------------------------- 1. the anchor, and the nursery
    # THE ANCHOR IS THE EXPORT'S AND IS READ, NEVER RECOMPUTED (review r2 finding 1, lead's decision).
    # `export/trees_far.py` subtracts `anchor` = the LOD2 mesh's bbox XY centre at z = 0 - the point the
    # impostor rotates about, asserted there against the manifest's radius_m / base_z_m - and writes it into
    # topology.json. The bake's first run used the prototype OBJECT's world translation instead, which is a
    # different point (up to (3.44, 2.66) m on pine_s7 / pine_s29, over 1 m on six prototypes), so it baked
    # E_placement with trees metres from where env_trees.glb draws them. One source of truth, no second
    # derivation: if topology.json does not carry `anchor`, this stops.
    missing_anchor = [p for p in protos if "anchor" not in topo["prototypes"][p]]
    assert not missing_anchor, (
        f"topology.json carries no `anchor` for {len(missing_anchor)} prototypes ({missing_anchor[:3]}). "
        "Re-run export/trees_far.py (phase6-export) first: the bake must not invent its own anchor.")
    anchors = {p: [float(v) for v in topo["prototypes"][p]["anchor"]] for p in protos}
    for p, a in anchors.items():
        assert len(a) == 3 and abs(a[2]) < 1e-6, f"{p}: anchor {a} - z must be 0 (the trunk-base plane)"

    # No blend is built for E_bake: those jobs open gate3_imp.blend as the impostor jobs did, on the `_LOD1`
    # prototype objects, and need no anchor at all.
    step = g0.Step("trees_far_set:nursery")
    bpy.ops.wm.open_mainfile(filepath=str(g3.IMP_BLEND), load_ui=False)
    nursery = {}
    for p in protos:
        ob = bpy.data.objects.get(p)
        assert ob is not None, f"{p} is not in {g3.IMP_BLEND.name}"
        nursery[p] = dict(object=p, mesh=ob.data.name, verts=len(ob.data.vertices),
                          materials=[m.name if m else None for m in ob.data.materials],
                          object_translation=[round(float(x), 4) for x in ob.matrix_world.translation])
    rep["ebake"] = dict(blend=g3.IMP_BLEND.name, prototypes=len(nursery),
                        lawn="GATE3_imp_lawn" in bpy.data.objects, anchors=anchors,
                        anchor_source="topology.json prototypes[p].anchor (export/trees_far.py)",
                        objects=nursery,
                        why="review r1 finding 5: the divisor is measured on the body that produced the atlas")
    step.done(g3.IMP_BLEND, objects=len(bpy.data.objects))

    # ---------------------------------------------------------------- 2. the E_placement blend (the site)
    step = g0.Step("trees_far_set:irr_blend")
    bpy.ops.wm.open_mainfile(filepath=str(g3.BAKE_BLEND), load_ui=False)
    added = append_objects(LOD2_BLEND)
    got = {o.name: o for o in added}
    for o in added:                                    # the templates themselves never render
        o.hide_render = True
    hidden_src, missing_src = [], []
    for row in man["tree_far"]:
        ob = bpy.data.objects.get(row["source_tree"])
        if ob is None:
            missing_src.append(row["source_tree"])
            continue
        if not ob.hide_render:
            ob.hide_render = True
            hidden_src.append(ob.name)
    boards = [o.name for o in bpy.data.objects if o.name.startswith("ENV_treeboard")]
    for n in boards:
        bpy.data.objects[n].hide_render = True

    # THE PLACEMENT ASSERT IS ON THE PLACED MESH'S WORLD BBOX (review r2 finding 2). The old one -
    # `matrix_world @ (anchor.x, anchor.y, 0)` against `loc` - is an algebraic identity for
    # `T(loc) @ S @ T(-anchor)`, so `worst_anchor_residual_m = 0` proved nothing about where the vertices
    # actually land. That is why the wrong anchor went unnoticed. This one reads the bbox back and compares
    # it with `topology.json`'s own `placed_bbox_min` / `placed_bbox_max`, which export/trees_far.py computes
    # independently, plus the bottom against `loc.z + bbox_min.z * s`. It fails on a wrong anchor - and note
    # that "XY centre == trunk_base" would NOT be the right test: the anchor is the SOURCE mesh's bbox XY
    # centre (the impostor's axis), and the reduction then shifts the reduced crown's own centre off it by
    # `placed_xy_offset_m` (0.10-2.83 m over the 127, median 0.28), which is the export's business, not a
    # placement error.
    BBOX_TOL, Z_TOL = 0.005, 0.05          # topology.json rounds its bboxes to 4 dp
    placed, worst_bbox, worst_z = [], 0.0, 0.0
    for row in topo["placements"]:
        p = row["prototype"]
        s = float(row["scale"])
        me = got[mesh_of[p]].data
        no = bpy.data.objects.new(row["object"], me)
        bpy.context.scene.collection.objects.link(no)
        # The export has ALREADY subtracted the anchor from the mesh, so the placement is the impostor's
        # verbatim: `location = trunk_base, scale = s`, rotation ignored. Subtracting `anchor` again here
        # would be the first run's error with the sign flipped.
        no.matrix_world = Matrix.Translation(Vector(row["loc"])) @ Matrix.Diagonal((s, s, s, 1.0))
        corners = [no.matrix_world @ Vector(c) for c in no.bound_box]
        wlo = [min(c[i] for c in corners) for i in range(3)]
        whi = [max(c[i] for c in corners) for i in range(3)]
        # THE ASSERT IS A CROSS-CHECK AGAINST THE EXPORT'S OWN PUBLISHED BBOX, not against the transform
        # algebra (review r2 finding 2). topology.json carries `placed_bbox_min` / `placed_bbox_max` computed
        # independently by export/trees_far.py; if the blend this appended from is not the anchored one, or
        # the anchor moved, these disagree by metres and this stops. The old assert -
        # `matrix_world @ (anchor.x, anchor.y, 0)` against `trunk_base` - is an identity and passed anyway.
        d_bbox = max(max(abs(wlo[i] - float(row["placed_bbox_min"][i])) for i in range(3)),
                     max(abs(whi[i] - float(row["placed_bbox_max"][i])) for i in range(3)))
        assert d_bbox <= BBOX_TOL, (
            f"{no.name} ({p}): placed world bbox [{[round(v, 3) for v in wlo]}, "
            f"{[round(v, 3) for v in whi]}] is {d_bbox:.3f} m from the export's own "
            f"[{row['placed_bbox_min']}, {row['placed_bbox_max']}] - this blend's mesh is not the anchored "
            "one the glb ships")
        want_z = float(row["loc"][2]) + float(topo["prototypes"][p]["bbox_min"][2]) * s
        d_z = abs(wlo[2] - want_z)
        assert d_z <= Z_TOL, (
            f"{no.name} ({p}): placed bbox bottom z {wlo[2]:.3f} is {d_z:.3f} m from "
            f"loc.z + bbox_min.z * s = {want_z:.3f}")
        worst_bbox, worst_z = max(worst_bbox, d_bbox), max(worst_z, d_z)
        top = float(row["loc"][2]) + topo["prototypes"][p]["height_above_base_m"] * s
        placed.append(dict(object=no.name, prototype=p, mesh=me.name, loc=row["loc"], scale=round(s, 6),
                           height_m=row["height_m"], walk_dist_m=row["walk_dist_m"],
                           source_tree=row["source_tree"], crown_top_z=round(top, 4),
                           bbox_centre_xy=[round((wlo[i] + whi[i]) * 0.5, 4) for i in (0, 1)],
                           bbox_min_z=round(float(wlo[2]), 4),
                           residual_bbox_m=round(float(d_bbox), 5), residual_z_m=round(float(d_z), 5),
                           # the export's own measure of how far the reduced crown's bbox centre sits from
                           # the impostor axis: the reduction's, not the placement's
                           placed_xy_offset_m=row.get("placed_xy_offset_m")))
    # r5 finding 4: the count comes from the manifest's own far list, not from a literal (the 8d belt took
    # it 127 -> 166). Every far row must be placed in the irradiance blend, or the bake would silently
    # cover only part of the set.
    assert len(placed) == len(man["tree_far"]), \
        f"{len(placed)} placements for {len(man['tree_far'])} far rows in the manifest"
    rep["irr"] = dict(blend=IRR_BLEND.name, placements=len(placed), templates_hidden=len(added),
                      source_trees_hidden=len(hidden_src), source_trees_missing=missing_src,
                      billboards_hidden=len(boards),
                      anchor_source="topology.json prototypes[p].anchor (export/trees_far.py)",
                      assert_on=("the placed mesh's WORLD bbox against topology.json's own placed_bbox_*, "
                                 "not the transform algebra (r2 finding 2)"),
                      tol_bbox_m=BBOX_TOL, tol_z_m=Z_TOL,
                      worst_residual_bbox_m=round(worst_bbox, 5), worst_residual_z_m=round(worst_z, 5),
                      remapped_materials=dedupe_materials())
    (TF / "irr_scope.json").write_text(json.dumps(
        dict(note="override scope for the shadow-ray cut-out wrap: every far-tree placement, so no value "
                  "depends on how the 127 were split across jobs",
             objects=[dict(object=d["object"], mesh=d["mesh"]) for d in placed]), indent=1) + "\n")
    (TF / "placements.json").write_text(json.dumps(
        dict(generated=rep["generated"], anchors=anchors, placements=placed), indent=1) + "\n")
    g0.save_copy(IRR_BLEND)
    step.done(IRR_BLEND, objects=len(bpy.data.objects))

    # ---------------------------------------------------------------- 3. the jobs
    jobs = []
    for p in protos:
        jobs.append(dict(id=f"tfao_{p}", kind="proto", blend=f"trees_far/{LOD2_BLEND.name}",
                         group="tfao", objects=[mesh_of[p]], isolate=[], world="white", lights="off",
                         samples=SPP_AO, direct=True, indirect=True, override="shadow",
                         out="trees_far/ao", est_s=120))
    for p in protos:
        jobs.append(dict(id=f"tfeb_{p}", kind="proto", blend=g3.IMP_BLEND.name,
                         group="tfeb", objects=[p], isolate=["GATE3_imp_lawn"], world="scene",
                         lights="scene", samples=SPP_IRR, direct=True, indirect=True, override="shadow",
                         out="trees_far/ebake", est_s=300))
    per = (len(placed) + IRR_JOBS - 1) // IRR_JOBS
    for k in range(IRR_JOBS):
        part = [d["object"] for d in placed[k * per:(k + 1) * per]]
        if not part:
            continue
        jobs.append(dict(id=f"tfirr_{k:02d}", kind="instance", blend=f"trees_far/{IRR_BLEND.name}",
                         objects=part, chunk=16, variants=["shadow"],
                         override_scope="trees_far/irr_scope.json", est_s=400))
    rep["jobs"] = [j["id"] for j in jobs]
    (TF / "trees_far_jobs.json").write_text(json.dumps(
        dict(generated=rep["generated"], samples=dict(ao=SPP_AO, irradiance=SPP_IRR),
             jobs=jobs), indent=1) + "\n")

    # merge into the gate 3 queue file, replacing any previous run of these ids
    qp = g3.jobs_path()
    q = json.loads(qp.read_text())
    ids = {j["id"] for j in jobs}
    q["jobs"] = [j for j in q["jobs"] if j["id"] not in ids] + jobs
    qp.write_text(json.dumps(q, indent=1) + "\n")
    rep["queue_total"] = len(q["jobs"])
    rep["wall_s"] = round(time.time() - t0, 1)
    (TF / "trees_far_set.json").write_text(json.dumps(rep, indent=1) + "\n")
    print(f"[trees_far_set] {len(jobs)} jobs queued ({rep['queue_total']} in the file), "
          f"{len(placed)} placements, {rep['wall_s']} s")


main()
