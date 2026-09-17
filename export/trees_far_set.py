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

THE PLACEMENT ANCHOR, and a defect in the export's own placement. trees_far.py does
`src.transform(ob.matrix_world)` and then places the mesh with `location = trunk_base, scale = s` - but it
never subtracts the prototype's own translation, so the mesh vertices still carry the tree library's world
position (x = -432 .. -600, y = -570 in master_delivery.blend) and a placed tree lands at
`trunk_base + s * library_position`, hundreds of metres from where it belongs. This script therefore places
with the anchor removed:

    matrix_world = Translation(trunk_base) @ Scale(s) @ Translation(-anchor_p)

where `anchor_p` is the prototype object's own world translation, read from gate3_imp.blend and cross-
checked against gate3_bake.blend (z asserted 0,
which is what makes `height_above_base_m` measurable from the bbox top). The bake is therefore correct
whatever the export does; the export's `env_trees.glb` needs the same subtraction (reported to the lead).
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

    # ---------------------------------------------------------------- 1. the nursery: anchors only
    # No blend is built here: the E_bake jobs open gate3_imp.blend as the impostor jobs did. What this pass
    # takes from it is the prototype ANCHOR - the object's own world translation, which trees_far.py baked
    # into the LOD2 mesh and never subtracted again (see the module docstring).
    step = g0.Step("trees_far_set:anchors")
    bpy.ops.wm.open_mainfile(filepath=str(g3.IMP_BLEND), load_ui=False)
    anchors, nursery = {}, {}
    for p in protos:
        ob = bpy.data.objects.get(p)
        assert ob is not None, f"{p} is not in {g3.IMP_BLEND.name}"
        t = ob.matrix_world.translation
        assert abs(t.z) < 1e-4, f"{p}: prototype origin z = {t.z}, the LOD2 mesh assumes z = 0 is its base"
        anchors[p] = [round(float(t.x), 6), round(float(t.y), 6), round(float(t.z), 6)]
        nursery[p] = dict(object=p, mesh=ob.data.name, verts=len(ob.data.vertices),
                          materials=[m.name if m else None for m in ob.data.materials])
    rep["ebake"] = dict(blend=g3.IMP_BLEND.name, prototypes=len(nursery),
                        lawn="GATE3_imp_lawn" in bpy.data.objects, anchors=anchors,
                        objects=nursery,
                        why="review r1 finding 5: the divisor is measured on the body that produced the atlas")
    step.done(g3.IMP_BLEND, objects=len(bpy.data.objects))

    # ---------------------------------------------------------------- 2. the E_placement blend (the site)
    step = g0.Step("trees_far_set:irr_blend")
    bpy.ops.wm.open_mainfile(filepath=str(g3.BAKE_BLEND), load_ui=False)
    for p in protos:                                   # the same anchors, cross-checked against the nursery
        ob = bpy.data.objects.get(p)
        assert ob is not None, f"{p} is not in {g3.BAKE_BLEND.name}"
        t = [round(float(x), 6) for x in ob.matrix_world.translation]
        assert max(abs(a - b) for a, b in zip(t, anchors[p])) < 1e-4, \
            f"{p}: anchor {t} in the bake blend != {anchors[p]} in the nursery"
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

    placed, worst = [], 0.0
    for row in topo["placements"]:
        p = row["prototype"]
        s = float(row["scale"])
        a = Vector(anchors[p])
        me = got[mesh_of[p]].data
        no = bpy.data.objects.new(row["object"], me)
        bpy.context.scene.collection.objects.link(no)
        no.matrix_world = (Matrix.Translation(Vector(row["loc"]))
                           @ Matrix.Diagonal((s, s, s, 1.0))
                           @ Matrix.Translation(-a))
        # the trunk base must land on `loc`: the anchor is the prototype's own origin and the LOD2 mesh's
        # z = 0 is its base plane, so (anchor.x, anchor.y, 0) maps to `loc` exactly.
        base = no.matrix_world @ Vector((a.x, a.y, 0.0))
        worst = max(worst, max(abs(base[i] - float(row["loc"][i])) for i in range(3)))
        top = float(row["loc"][2]) + topo["prototypes"][p]["height_above_base_m"] * s
        placed.append(dict(object=no.name, prototype=p, mesh=me.name, loc=row["loc"], scale=round(s, 6),
                           height_m=row["height_m"], walk_dist_m=row["walk_dist_m"],
                           source_tree=row["source_tree"], crown_top_z=round(top, 4)))
    assert worst < 1e-4, f"placement anchor residual {worst:.6f} m"
    assert len(placed) == 127, f"{len(placed)} placements"
    rep["irr"] = dict(blend=IRR_BLEND.name, placements=len(placed), templates_hidden=len(added),
                      source_trees_hidden=len(hidden_src), source_trees_missing=missing_src,
                      billboards_hidden=len(boards), worst_anchor_residual_m=round(worst, 8),
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
