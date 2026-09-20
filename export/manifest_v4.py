"""Gate 3 step 5: manifest v4 (`pfa-phase6/4`). Pure python3 - no Blender, no GPU.

    python3 export/manifest_v4.py

Everything in v3 is carried verbatim from out/gate2/manifest.json; out/gate2 and out/gate3 are siblings, so the
`../gate1/` and `../gate0/` paths it already carries stay correct and only the two bare `*_dir` keys are rerooted.
The schema of the three new blocks is export/README.md "manifest.json v4"; this writer is the only thing that
fills them and it never invents a number - every value comes from a bake record, compose.json or a file on disk.
"""
import hashlib
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gate3_common as g3  # noqa: E402

SCHEMA = "pfa-phase6/4"
QA12B_VIEWER_TEXTURE_MB = 953.5     # docs/qa_round_12b.md section 5, measured in the viewer at 1440p


def rec(jid):
    p = g3.REC / f"{jid}.json"
    return json.loads(p.read_text()) if p.exists() else None


def find(name):
    """out/gate3 in this worktree first, then the MAIN checkout (the bake branch syncs its files there)."""
    for base in (g3.OUT, g3.MAIN_ROOT / "export" / "out" / "gate3"):
        p = base / name
        if p.exists():
            return p
    return None


# The bake engineer's instance_irradiance.json schema ids this writer accepts. /2 adds a `prototypes`
# block (per-prototype E_bake for the impostor modulation, decisions.md 2026-09-17) on top of /1 and
# changes no field read here.
IRR_JOIN_TOL_M = 0.02   # the world-location join grid; also the residual tolerance below
IRR_SCHEMAS = ("pfa-phase6/gate4-instance-irradiance/1", "pfa-phase6/gate4-instance-irradiance/2")


def trees_lighting_block(tf, man=None):
    """`trees.far_mesh.lighting`: the far trees' per-placement irradiance and, for the IMPOSTORS, the
    per-prototype `E_bake` the atlas frame is divided by.

    The bake engineer's `out/gate3/trees_far/instance_irradiance.json` (schema /2). Two consumers, and they
    are not the same thing:
      * the far-tree MESH takes COLOR_0 (the vertex AO in the glb) times this file's per-placement `rgb`;
      * the IMPOSTOR beyond `treeMeshDist` is `atlas_frame * (E_placement / E_bake)` per channel
        (decisions.md 2026-09-17): the atlas was baked with each prototype alone under the whole unoccluded
        sky, which is where its blue cast comes from.
    BOTH SIDES OF THAT RATIO ARE RAW. `lightmaps.scale` (pi) is applied to NEITHER - scaling only the
    numerator would make every impostor pi times too bright. This writer therefore copies the numbers
    through verbatim and does not rescale, round or re-order them.

    PHASE 9 item 1: A ROW IS WRITTEN FOR EVERY `tree_far` TREE, not only for the ones that got a mesh. The
    billboard-only rule (export/belt_rule.py) leaves 17 / 35 tagged rows with no mesh placement, and the
    IMPOSTOR consumer above is exactly the one those rows still need: `farTreeIrradiance` joins this list to
    `tree_far` BY LOCATION, so a list cut down to the mesh placements would drop the modulation of the very
    trees that are now impostors at every distance - the belt, whose median E_placement / E_bake is 0.2424,
    would draw about four times too bright. Each row therefore carries `mesh: true|false`.
    """
    ip = next((q for q in (g3.OUT / "trees_far" / "instance_irradiance.json",
                           g3.MAIN_ROOT / "export/out/gate3/trees_far/instance_irradiance.json")
               if q.exists()), None)
    if ip is None:
        return dict(present=False,
                    note="out/gate3/trees_far/instance_irradiance.json not synced yet (bake branch)")
    irr = json.loads(ip.read_text())
    assert irr.get("schema") in IRR_SCHEMAS, \
        f"trees_far irr schema {irr.get('schema')!r}, expected one of {sorted(IRR_SCHEMAS)}"
    # 8d r2 / review r5 finding 2: the join is BY WORLD LOCATION, which is what the bake file itself
    # declares its key to be ("key": "WORLD TRANSLATION ... the object name is a label"). Joining by the
    # TREEFAR_### label was only ever incidentally right: the belt's 39 trees interleave into a name-sorted
    # list, which re-pointed 87 of the 127 existing labels, so a name join now silently mismatches trees.
    # A 0.02 m grid on the rounded location is exact here - no two far trees are within 0.2 m of each other
    # (asserted below) - and it is the same tolerance the residual check uses.
    def _key(loc):
        return tuple(round(float(v) / IRR_JOIN_TOL_M) for v in loc)
    rows = {}
    for m in irr["meshes"].values():
        for pl in m["placements"]:
            k = _key(pl["loc"])
            assert k not in rows, (f"two baked far-tree rows share the {IRR_JOIN_TOL_M} m location cell "
                                   f"{k}: {rows[k]['object']} and {pl['object']} - the world-location join "
                                   f"is not unique and the bake must be re-keyed")
            rows[k] = pl
    # every far tree, mesh or not: the mesh placements first, then the billboard-only rows, both in
    # `tree_far` index order so the list reads in the same order as every other far-tree list in the file.
    want = ([dict(pl, mesh=True) for pl in tf["placements"]]
            + [dict(b, object=f"TREEFAR_{b['index']:03d}", mesh=False)
               for b in tf.get("billboard_only", [])])
    want.sort(key=lambda d: d["index"])
    if man is not None and man.get("tree_far") is not None:
        assert len(want) == len(man["tree_far"]), (
            f"the far-tree lighting list would carry {len(want)} rows ({len(tf['placements'])} meshes + "
            f"{len(tf.get('billboard_only', []))} billboard-only) against {len(man['tree_far'])} tree_far "
            f"trees - every far tree needs an impostor irradiance row, mesh or not")
    per, missing, worst = [], [], 0.0
    for pl in want:
        r = rows.get(_key(pl["loc"]))
        if r is None:
            missing.append(pl["object"])
            continue
        worst = max(worst, max(abs(float(a_) - float(b_)) for a_, b_ in zip(r["loc"], pl["loc"])))
        per.append(dict(index=pl["index"], object=pl["object"], prototype=pl["prototype"],
                        loc=pl["loc"], rgb=r["rgb"], cov=r.get("cov"), mesh=pl["mesh"]))
    assert not missing, (f"trees_far/instance_irradiance.json has no row at the world location of "
                         f"{missing[:4]} ({len(missing)} of {len(want)}): the per-placement "
                         f"irradiance bake has not been run for these trees - re-run trees_far_set.py, the "
                         f"tfirr_* jobs and trees_far_compose.py")
    assert worst < 0.02, (f"trees_far/instance_irradiance.json row locations differ from trees_far.json by "
                          f"up to {worst:.4f} m - the two were built from different placements")
    return dict(
        present=True, source=ip.name, schema=irr["schema"], generated=irr.get("generated"),
        units=irr.get("units"), encoding=irr.get("encoding"), scale_applied="none (raw, see `ratio`)",
        range_global=irr.get("range_global"),
        mesh=dict(how="COLOR_0 (vertex AO, gamma2 - see `color0`) x placements[].rgb for that tree",
                  rows_are="EVERY tree_far tree, in tree_far index order; `mesh` says whether this tree "
                           "also has an instance row in the far-tree glbs (Phase 9 billboard-only rule). "
                           "The MESH consumer uses the `mesh: true` rows; the IMPOSTOR consumer "
                           "(farTreeIrradiance, joined by location) needs all of them.",
                  with_mesh=sum(1 for d in per if d["mesh"]),
                  billboard_only=sum(1 for d in per if not d["mesh"]),
                  placements=per),
        impostor=dict(
            # `how` is a formula, so every symbol in it has to be IN the manifest: a viewer that only reads
            # manifest.json cannot go and find strength/clamp/the zero-channel rule in the bake's own JSON
            # (review r2 finding 1). Copied verbatim, no defaults invented here - a missing key would mean
            # the bake changed its contract and should be noticed, not papered over.
            how=irr["ratio"]["use"], raw=irr["ratio"]["raw"],
            strength=irr["ratio"]["strength"], clamp=irr["ratio"]["clamp"],
            zero_channel_fallback=irr["ratio"]["zero_channel_fallback"],
            fallback=irr["ratio"]["fallback"],
            e_bake_body=irr["ratio"].get("e_bake_body"),
            prototypes={k: dict(E_bake=v["E_bake"], cov=v["cov"]) for k, v in sorted(irr["prototypes"].items())}),
        reduce=irr.get("reduce"), key=irr.get("key"), placement_key=irr.get("placement_key"),
        vertex_ao=irr.get("vertex_ao"))


def instance_block():
    """`lightmaps.instance_irradiance`: the 1 379 shrub/reed placements, IN env.glb's INSTANCE ROW ORDER.

    Two inputs, neither of them this writer's: `instance_irradiance.json` (bake engineer, one scene-linear
    RGB per placement with its world `loc`) and `instance_order.json` (export/gate4_instance_order.py, the
    glb row -> placement map joined on the instance TRANSLATION - `gltfpack -mi` strips node names and
    re-orders the rows, so a name is a label, never the key). Every number below comes from one of those two
    files. Without the order file the block still ships the bake's own summaries, with
    `order_recovered: false` and no arrays: an array in the wrong order would light 1 379 shrubs with each
    other's values.
    """
    ip = find("instance_irradiance.json")
    if ip is None:
        return dict(present=False,
                    note="out/gate3/instance_irradiance.json not synced yet (bake branch, Gate 4)")
    irr = json.loads(ip.read_text())
    # /2 is /1 plus a `prototypes` block carrying each impostor prototype's E_bake (the isolated bake's
    # environment irradiance), which the per-placement impostor modulation divides by - additive, so every
    # field this writer reads is unchanged. Accept both; anything else is a contract change, not a version.
    assert irr.get("schema") in IRR_SCHEMAS, \
        f"irr schema {irr.get('schema')!r}, expected one of {sorted(IRR_SCHEMAS)}"
    op = find("instance_order.json")
    order = json.loads(op.read_text()) if op is not None else None
    if order is not None:
        assert order.get("schema") == "pfa-phase6/gate4-instance-order/2", f"order schema {order.get('schema')!r}"
        assert order["placements"] == irr["placements"], \
            f"order {order['placements']} placements != irradiance {irr['placements']}"
        assert order["meshes_n"] == irr["meshes_n"], "order/irradiance mesh count mismatch"
        # The counts survive a re-bake unchanged, so they prove nothing about WHICH irradiance file the row
        # order was built from, nor which env.glb (review r5, 2). Pin both by identity.
        assert order.get("irradiance_generated") == irr.get("generated"), (
            f"instance_order.json was built against instance_irradiance.json generated "
            f"{order.get('irradiance_generated')}, but the file here is {irr.get('generated')}: re-run "
            f"export/gate4_instance_order.py before the manifest")
        # `generated` did not change when the bake added `loc` to the same file, so the real pin is the
        # hash: any re-bake, however stamped, forces the join to be re-run before the manifest.
        sha = hashlib.sha256(ip.read_bytes()).hexdigest()
        assert order.get("irradiance_sha256") in (None, sha), (
            f"instance_order.json was built against a different {ip.name} (sha256 "
            f"{order.get('irradiance_sha256')[:12]}... vs {sha[:12]}...): re-run "
            f"export/gate4_instance_order.py before the manifest")
        glb = next((q for q in (g3.GATE1_OUT / order["glb"],
                                g3.MAIN_ROOT / "export" / "out" / "gate1" / order["glb"]) if q.exists()), None)
        assert glb is not None, f"instance_order.json refers to {order['glb']}, which is in no out/gate1"
        assert glb.stat().st_size == order["glb_bytes"], (
            f"instance_order.json holds the row order of a {order['glb_bytes']} B {order['glb']}, but the "
            f"file on disk is {glb.stat().st_size} B: re-dump the rows and re-run the join")
    # A harness run (positions from env.gltf BY OBJECT NAME - the join the bake review ruled out) is never
    # shipped: the block keeps the bake's summaries and drops every array, exactly as if no order existed.
    harness = order is not None and not order.get("loc_in_json")
    if harness:
        print("[manifest_v4] WARNING: instance_order.json is a PFA_INSTANCE_ORDER_HARNESS run "
              "(loc_in_json: false) - no instance_irradiance rgb array is emitted. Re-run "
              "export/gate4_instance_order.py once the re-baked JSON carries per-placement `loc`.")

    rows_of = {} if harness else {m: e["objects"] for m, e in (order or {}).get("meshes", {}).items()}
    meshes = {}
    for mesh, m in sorted(irr["meshes"].items()):
        by_obj = {p["object"]: p for p in m["placements"]}
        e = dict(n=m["n"], min=m["min"], max=m["max"], mean=m["mean"], lum_min=m["lum_min"],
                 lum_mean=m["lum_mean"], lum_max=m["lum_max"], cov_mean=m["cov_mean"])
        if mesh in rows_of:
            names = rows_of[mesh]
            assert len(names) == m["n"], f"{mesh}: {len(names)} glb rows != {m['n']} placements"
            missing = [n for n in names if n not in by_obj]
            assert not missing, f"{mesh}: glb rows with no baked placement: {missing[:5]}"
            e["rgb"] = [c for n in names for c in by_obj[n]["rgb"]]
            e["cov"] = [by_obj[n]["cov"] for n in names]
            e["glb_nodes"] = sorted({nd["gltf_node"] for nd in order["nodes"]
                                     if any(s[0] == mesh for s in nd["segments"])})
        meshes[mesh] = e

    nodes = [] if harness else [
        dict(gltf_node=nd["gltf_node"], count=nd["count"], tris=nd["tris"], material=nd["material"],
             segments=nd["segments"]) for nd in (order or {}).get("nodes", [])]
    return dict(
        encode="none", dtype="float32", encoding=irr["encoding"], units=irr["units"],
        attribute="_IRRADIANCE", json=ip.name, placements=irr["placements"], meshes_n=irr["meshes_n"],
        range_global=irr["range_global"], lum_min=irr["lum_min"], lum_mean=irr["lum_mean"],
        lum_max=irr["lum_max"], reduce=irr["reduce"],
        in_glb=False,
        delivery=("this manifest, not the glb: env.glb is unchanged (no re-pack, no COLOR_0 on the cards). "
                  "`meshes[*].rgb` is a flat float32 RGB list in that mesh's glb row order; a node's "
                  "InstancedBufferAttribute is built from `nodes[*].segments` (see `nodes_note`), not by "
                  "assuming one mesh per node."),
        decode=("irradiance = rgb * lightmaps.scale (pi) - the same units as a DECODED lightmap texel. "
                "Multiply it into the card's diffuse term in place of the sky-only ambient, never as a tint. "
                "Nothing is quantised: `range_global` is informational."),
        order=("glb" if nodes else "none"),
        order_recovered=bool(nodes),
        order_source=(dict(file=op.name, schema=order["schema"], generator=order["generator"],
                           glb=order["glb"], glb_bytes=order["glb_bytes"], method=order["method"],
                           join="instance translation (the only key gltfpack -mi leaves in the glb)",
                           loc_source=order["loc_source"], loc_in_json=order["loc_in_json"],
                           irradiance_sha256=order.get("irradiance_sha256"),
                           axis_swap=order["axis_swap"], axis_swap_check=order["axis_swap_check"],
                           tol_m=order["tol_m"], margin=order["margin"],
                           rows_matched=order["rows_matched"],
                           worst_residual_m=order["worst_residual_m"],
                           worst_margin_ratio=order["worst_margin_ratio"],
                           name_crosscheck=order.get("name_crosscheck"))
                      if order is not None else
                      "instance_order.json not written yet: run `node web/tools/instance_rows.mjs "
                      "export/out/gate1/env.glb export/out/gate3/instance_rows.json && python3 "
                      "export/gate4_instance_order.py`. No rgb array ships until it is."),
        key=("INSTANCE TRANSLATION. The object name in instance_irradiance.json is a label: gltfpack -mi "
             "drops node names and re-orders the rows, so the arrays below are ordered by the positional "
             "join in `order_source`, verified row by row against env.glb's own matrices."),
        key_bake=irr["placement_key"],
        irradiance_generated=irr.get("generated"),
        nodes=nodes,
        nodes_note=(("the viewer binds per NODE, not per mesh: gltfpack merges meshes, so a node can draw "
                     "the placements of more than one of them. `segments` is that node's rows as an ordered "
                     "[mesh, count, offset] list, `offset` being the row index into THAT mesh's own rgb/cov "
                     "array (3*offset in the flat rgb) - a mesh may own several segments in a node, so read "
                     "them with a running cursor, never one slice per mesh. Merged here: " +
                     "; ".join(f"node {n['gltf_node']} = {n['count']} rows, " +
                               " + ".join(f"{c}x{m}@{o}" for m, c, o in n["segments"])
                               for n in nodes if len(n["segments"]) > 1) +
                     ". `gltf_node` is the index into env.glb's `nodes` array (three's GLTFLoader: "
                     "parser.associations).")
                    if nodes else
                    ("no usable order file: no node binding and no rgb array. " +
                     ("the one on disk is a PFA_INSTANCE_ORDER_HARNESS run (positions by object name), "
                      "which is not shippable - re-run export/gate4_instance_order.py against the "
                      "loc-carrying instance_irradiance.json." if harness else
                      "run export/gate4_instance_order.py."))),
        dark=irr["checks"]["dark"],
        meshes=meshes)


def instance_lod1_block(base):
    """`lightmaps.instance_irradiance.lod1`: the SAME per-placement irradiance, re-ordered for the shrub/reed
    LOD1 glb (`env_shrubs.glb`, Phase 6c item E).

    The values are not re-baked and not re-derived: they are `instance_irradiance.json`'s own RGB per
    placement, emitted a second time in **env_shrubs.glb's** row order, because that order is a different
    permutation of the same placements and `offset` indexes a mesh's own array. That is how both LODs share
    a placement's irradiance - swapping LOD must not change a shrub's lighting. Three of the 1 379 placements
    have no LOD1 (export/shrub_lod1.py `skipped_meshes`): they keep the env.glb card and are absent here.
    """
    ip, op = find("instance_irradiance.json"), find("instance_order_shrub_lod1.json")
    if ip is None or op is None:
        return None
    irr = json.loads(ip.read_text())
    order = json.loads(op.read_text())
    assert irr.get("schema") in IRR_SCHEMAS, \
        f"irr schema {irr.get('schema')!r}, expected one of {sorted(IRR_SCHEMAS)}"
    assert order.get("schema") == "pfa-phase6/gate4-instance-order/2", f"order schema {order.get('schema')!r}"
    assert order.get("set") == "shrub_lod1", f"{op.name} is the {order.get('set')!r} set"
    if not order.get("loc_in_json"):
        return dict(present=False, note="the LOD1 order file is a PFA_INSTANCE_ORDER_HARNESS run")
    sha = hashlib.sha256(ip.read_bytes()).hexdigest()
    assert order.get("irradiance_sha256") in (None, sha), (
        f"{op.name} was built against a different {ip.name}: re-run "
        f"PFA_ORDER_SET=shrub_lod1 python3 export/gate4_instance_order.py")
    glb = next((q for q in (g3.GATE1_OUT / order["glb"],
                            g3.MAIN_ROOT / "export" / "out" / "gate1" / order["glb"]) if q.exists()), None)
    assert glb is not None, f"{op.name} refers to {order['glb']}, which is in no out/gate1"
    assert glb.stat().st_size == order["glb_bytes"], (
        f"{op.name} holds the row order of a {order['glb_bytes']} B {order['glb']}, the file on disk is "
        f"{glb.stat().st_size} B: re-dump the rows and re-run the join")
    by_obj = {p["object"]: p for m in irr["meshes"].values() for p in m["placements"]}
    meshes = {}
    for mesh, e in sorted(order["meshes"].items()):
        names = e["objects"]
        missing = [n for n in names if n not in by_obj]
        assert not missing, f"{mesh}: LOD1 glb rows with no baked placement: {missing[:5]}"
        meshes[mesh] = dict(n=len(names),
                            rgb=[c for n in names for c in by_obj[n]["rgb"]],
                            cov=[by_obj[n]["cov"] for n in names],
                            glb_nodes=sorted({nd["gltf_node"] for nd in order["nodes"]
                                              if any(sg[0] == mesh for sg in nd["segments"])}))
    covered = sum(len(e["objects"]) for e in order["meshes"].values())
    return dict(
        glb=order["glb"], placements=covered, meshes_n=len(meshes),
        placements_in_lod2=base.get("placements"),
        not_in_lod1=(base.get("placements") or 0) - covered,
        encode=base.get("encode"), dtype=base.get("dtype"), decode=base.get("decode"),
        key=("INSTANCE TRANSLATION, the same join as the LOD2 set, run against env_shrubs.glb: "
             "`mesh` keys stay the LOD2 mesh names so the two LODs' arrays line up by mesh, while the "
             "row ORDER is this glb's own."),
        order_source=dict(file=op.name, glb_bytes=order["glb_bytes"], tol_m=order["tol_m"],
                          margin=order["margin"], rows_matched=order["rows_matched"],
                          worst_residual_m=order["worst_residual_m"],
                          worst_margin_ratio=order["worst_margin_ratio"],
                          axis_swap=order["axis_swap"], name_crosscheck=order.get("name_crosscheck")),
        nodes=[dict(gltf_node=nd["gltf_node"], count=nd["count"], tris=nd["tris"],
                    material=nd["material"], segments=nd["segments"]) for nd in order["nodes"]],
        nodes_note=("read exactly as the LOD2 `nodes`: an ordered [mesh, count, offset] list per node with a "
                    "running cursor, `gltf_node` indexing env_shrubs.glb's own nodes array."),
        meshes=meshes)


def main():
    man = json.loads((g3.GATE2_OUT / "manifest.json").read_text())
    # `glb.per_class` is carried through from Gate 2, which froze it when the Gate 2 chain last ran, so
    # it describes the glbs as they were THEN.  It is not decoration: export/verify_glb.py --gate5
    # checks the triangles the tier groups draw against `placed_tris` here, so a re-packed class fails
    # that check against a stale number (8a: the densified LOD2 shrubs took env from 679 779 to 781 931
    # drawn while this still said 679 779, and `bytes` had been stale since the QA-12-1 env re-pack -
    # 35 797 240 against a 38 119 568 B file on disk - without anything noticing).  The authority is the
    # Gate 1 manifest beside the glbs themselves, read local-then-MAIN like every other hand-off here.
    g1m = next((q for q in (g3.GATE1_OUT / "manifest.json",
                            g3.MAIN_ROOT / "export" / "out" / "gate1" / "manifest.json") if q.exists()),
               None)
    glb_refresh = []
    stale = []
    if g1m is not None:
        cur = json.loads(g1m.read_text()).get("glb", {}).get("per_class", {})
        for cls, now in cur.items():
            was = (man.get("glb", {}).get("per_class", {}) or {}).get(cls)
            if not isinstance(was, dict):
                # review r1 finding 4: a class Gate 1 knows about and Gate 2 does not is NOT refreshed
                # here, so say so rather than dropping it on the floor.
                stale.append(dict(cls=cls, side="gate1_only",
                                  why="in the Gate 1 manifest but not in Gate 2's glb.per_class, so "
                                      "nothing carries it into this manifest"))
                continue
            moved = {k: [was.get(k), now.get(k)] for k in ("bytes", "placed_tris", "objects", "meshes")
                     if k in now and was.get(k) != now.get(k)}
            if moved:
                glb_refresh.append(dict(cls=cls, **moved))
            was.update({k: v for k, v in now.items() if k != "path"})
        # review r1 finding 4, the case that fails SILENTLY and is the dangerous one: a class frozen into
        # Gate 2's per_class that the Gate 1 manifest beside the glbs no longer names keeps its Gate 2
        # numbers untouched and ships them, and verify_glb --gate5 then checks the tier groups against a
        # number nothing on disk backs. It is not an error here (a class can legitimately leave the export
        # set) but it must never be silent.
        for cls, was in sorted((man.get("glb", {}).get("per_class", {}) or {}).items()):
            if cls not in cur and isinstance(was, dict):
                stale.append(dict(cls=cls, side="gate2_only",
                                  bytes=was.get("bytes"), placed_tris=was.get("placed_tris"),
                                  why="carried unchanged from Gate 2: the Gate 1 manifest beside the glbs "
                                      "does not name this class, so nothing on disk backs these numbers"))
    if stale:
        man.setdefault("glb", {})["per_class_not_refreshed"] = stale
        for r in stale:
            print(f"[manifest_v4] WARN glb.per_class[{r['cls']}] not refreshed ({r['side']}): {r['why']}",
                  flush=True)
    if glb_refresh:
        man.setdefault("glb", {})["per_class_refreshed_from_gate1"] = dict(
            source=str(g1m), changed=glb_refresh,
            why="Gate 2 froze these when it last ran; verify_glb --gate5 checks the tier groups' drawn "
                "triangles against placed_tris, so they follow the glbs on disk.")
        print(f"[manifest_v4] glb.per_class refreshed from {g1m}: "
              + ", ".join(f"{r['cls']} " + " ".join(f"{k} {v[0]}->{v[1]}" for k, v in r.items()
                                                    if k != "cls") for r in glb_refresh), flush=True)
    setj = json.loads((g3.OUT / "gate3_set.json").read_text())
    comp = json.loads((g3.OUT / "compose.json").read_text()) if (g3.OUT / "compose.json").exists() else {}
    # export/gate3_encode.py is the authoritative encode (range = the map's own max, error in stops).
    enc = (json.loads((g3.OUT / "encode.json").read_text())["maps"]
           if (g3.OUT / "encode.json").exists() else {})
    jobs = {j["id"]: j for j in g3.read_jobs()["jobs"]}

    # The export engineer applies out/gate3/lightmap_uv2.npz to the glbs and writes uv2_relay_status.json
    # (`pfa-phase6/gate3-relay/1`, export/gate3_relay_check.py) beside it, in MAIN. This writer NEVER decides
    # a flag itself: `uv2_in_glb` and `vertex_irradiance.in_glb` are read from that file and from nowhere
    # else, and stay false while it is absent. Background (docs/decisions.md 2026-09-16): gltfpack had been
    # stripping TEXCOORD_1 from every glb since Gate 1, so Gate 1's own `uv2_in_glb: true` was never true.
    rp = next((q for q in (g3.OUT / "uv2_relay_status.json",
                           g3.MAIN_ROOT / "export" / "out" / "gate3" / "uv2_relay_status.json") if q.exists()),
              None)
    relay = json.loads(rp.read_text()) if rp is not None else None
    if relay is not None:
        assert relay.get("schema") == "pfa-phase6/gate3-relay/1", f"relay schema {relay.get('schema')!r}"
    relay_uv2 = (relay or {}).get("uv2", {})
    relay_all = (relay or {}).get("uv2_all_meshes", {})
    relay_vi = (relay or {}).get("vertex_irradiance") or {}

    def relay_entry(mesh, obj):
        """The relay row for an own-map asset, by MESH name first (its own key) then by asset name."""
        for d in (relay_uv2, relay_all):
            if mesh in d:
                return d[mesh]
        for d in (relay_uv2, relay_all):
            for e in d.values():
                if e.get("asset") == obj:
                    return e
        return None
    man["schema"] = SCHEMA
    man["gate"] = "gate3"
    man["generator"] = "export/manifest_v4.py"
    man["carried_from"] = "../gate2/manifest.json"
    man["textures"]["ktx2_dir"] = "../gate1/tex_ktx2"
    man["textures"]["gate2"]["ktx2_dir"] = "../gate2/tex_ktx2"
    if "etc1s_dir" in man["textures"]["gate2"]:
        man["textures"]["gate2"]["etc1s_dir"] = "../gate2/tex_ktx2_etc1s"

    ktx_dir = g3.KTX
    files, missing_ktx = {}, []

    def add_tex(key, w, h, kind, encode, mips, colorspace="linear", **extra):
        p = ktx_dir / f"{key}.ktx2"
        if not p.exists():
            missing_ktx.append(key)
            return None
        files[key] = dict(path=p.name, w=int(w), h=int(h), map=kind, colorspace=colorspace, encode=encode,
                          bytes=p.stat().st_size, mips=bool(mips),
                          resident_mb=g3.resident_mb(w, h, encode, mips), **extra)
        return key

    # ------------------------------------------------------------ lightmaps.assets
    own_rows = {r["object"]: r for r in setj["own_maps"]}
    assets = {}
    for jid, j in jobs.items():
        if j["kind"] not in ("own", "own_gate1uv2"):
            continue
        r = rec(jid)
        if r is None:
            continue
        row = own_rows[j["object"]]
        size = r["size"]
        base = r["key"]
        ka = add_tex(f"{base}_rgbm8", size, size, "lightmap", "rgbm8", True)
        kb = add_tex(f"{base}_gamma2", size, size, "lightmap", "gamma2", True)
        gate1_layout = j["kind"] == "own_gate1uv2"
        en = enc.get(base, {})
        in_glb = gate1_layout or not row["uv2_relaid"]
        ent = relay_entry(j.get("mesh", row.get("mesh", "")), j["object"])
        if ent is not None and isinstance(ent.get("uv2_in_glb"), bool):
            # For a gate3-relaid asset the flag IS the relay's. For the two `lmg1_*` diagnostics the sense is
            # inverted: they are baked on the FROZEN Gate 1 layout, so they are usable only while the glb has
            # NOT been re-laid.
            in_glb = (not ent["uv2_in_glb"]) if gate1_layout else bool(ent["uv2_in_glb"])
        e = dict(size=size, textures={"rgbm8": ka, "gamma2": kb}, default="gamma2",
                 range=en.get("range", r["map"]["range"]), uv2_in_glb=in_glb,
                 uv2_source="gate1" if (gate1_layout or not row["uv2_relaid"]) else "gate3_relaid",
                 uv2_coverage=row["coverage_gate1"] if gate1_layout else row["coverage"],
                 cm_per_texel=row["cm_per_texel_gate1"] if gate1_layout else row["cm_per_texel"],
                 area_m2=row["area_m2"], tris=row["tris"], bake_s=r["bake_s"],
                 exr=f"tex/{r['map']['exr']['path']}" if "exr" in r["map"] else None,
                 stats=en.get("stats", r["map"]["stats"]), signal_p99=en.get("signal_p99"),
                 roundtrip={"rgbm8": en.get("rgbm8", r["map"]["rgbm8"]["roundtrip"]),
                            "gamma2": en.get("gamma2", r["map"]["gamma2"]["roundtrip"])})
        if gate1_layout:
            e["note"] = ("diagnostic: the same asset baked on the FROZEN Gate 1 UV2. Usable only while the "
                         "glb still carries THAT layout - `uv2_in_glb` here is the inverse of the relay's "
                         "flag for the same mesh, and goes false the moment the re-laid UV2 is packed.")
            assets.setdefault("_gate1_layout", {})[j["object"]] = e
        else:
            assets[j["object"]] = e

    # ------------------------------------------------------------ lightmaps.slots
    atlases = {}
    for key, a in (comp.get("atlases") or {}).items():
        en = enc.get(key, {})
        ka = add_tex(f"{key}_rgbm8", g3.ATLAS_PX, g3.ATLAS_PX, "lightmap_atlas", "rgbm8", True)
        kb = add_tex(f"{key}_gamma2", g3.ATLAS_PX, g3.ATLAS_PX, "lightmap_atlas", "gamma2", True)
        atlases[key] = dict(pool=a["pool"], atlas=a["atlas"], atlas_px=a["atlas_px"], slot_px=a["slot_px"],
                            gutter_px=a["gutter_px"], usable_px=a["usable_px"], uv2_scale=a["uv2_scale"],
                            slots_expected=a["slots_expected"], slots_filled=a["slots_filled"],
                            slots_blank_n=a["slots_blank_n"],
                            textures={"rgbm8": ka, "gamma2": kb}, default="gamma2",
                            range=en.get("range", a["range"]),
                            stats=en.get("stats", a["stats"]), signal_p99=en.get("signal_p99"),
                            exr=f"tex/{a['exr']['path']}" if "exr" in a else None,
                            roundtrip={"rgbm8": en.get("rgbm8", a["rgbm8"]["roundtrip"]),
                                       "gamma2": en.get("gamma2", a["gamma2"]["roundtrip"])},
                            slot_check=a.get("slot_check"))

    # The 988 slots are addressed by the ORN / ARCH-instance meshes' own TEXCOORD_1: if orn.glb is packed
    # without `-kv` the atlases cannot be applied at all, so the relay's per-glb count is carried here too.
    by_glb = {}
    for e in relay_all.values():
        g = by_glb.setdefault(e.get("glb", "?"), {"meshes": 0, "with_uv2": 0})
        g["meshes"] += 1
        g["with_uv2"] += 1 if e.get("uv2_in_glb") else 0
    slot_meshes = [(k, e) for k, e in relay_all.items() if e.get("glb") == "orn.glb"]
    slots_uv2 = bool(slot_meshes) and all(e.get("uv2_in_glb") for _, e in slot_meshes)

    v = comp.get("vertex") or {}
    # The npz is the hand-off (float32, unencoded). What the glb actually carries is the export engineer's
    # per-mesh gamma-2 encode of it, reported back in the relay's `vertex_irradiance` block; the manifest
    # copies that range per mesh and says how to decode COLOR_0. Empty block -> in_glb stays false.
    vi_in_glb = bool(relay_vi) and all(isinstance(r, dict) for r in relay_vi.values())
    relay_vi_range = (relay or {}).get("vertex_irradiance_range_global")
    if relay_vi_range is None and relay_vi:
        rr = {r.get("range") for r in relay_vi.values() if isinstance(r, dict)}
        relay_vi_range = rr.pop() if len(rr) == 1 else None
    assert not vi_in_glb or relay_vi_range is not None, (
        "uv2_relay_status.json says COLOR_0 is in the glb but carries no single global range; the viewer "
        "cannot pick a per-mesh one (gltfpack -mi instances primitives across trees)")
    vertex = dict(encode=v.get("encode", "none"), dtype=v.get("dtype", "float32"),
                  shape=v.get("shape", "(n_verts, 3)"), units=v.get("units"),
                  attribute="COLOR_0", in_glb=vi_in_glb,
                  npz=v.get("npz"), bytes=v.get("bytes"), meshes_n=v.get("meshes"), verts=v.get("verts"),
                  npz_decode=("none: the npz holds the baked values themselves, scene-linear RGB, same units "
                              "as a DECODED lightmap texel. irradiance = value * lightmaps.scale (pi)."),
                  glb_encode="gamma2 at ONE GLOBAL range (code = sqrt(v / range)), FLOAT_COLOR, "
                             "env.glb -vc 16",
                  # ONE number for the whole block (lead's decision after viewer round 13b): gltfpack's -mi
                  # instances primitives across trees, so the 14 baked buffers arrive as 14 primitives over
                  # 26 placements and a PER-MESH range cannot be joined back to its mesh. The per-mesh rows
                  # below still carry `range` (the same value) plus their own mean and round-trip error.
                  range=relay_vi_range,
                  range_source=("uv2_relay_status.json vertex_irradiance_range_global = the max over all 14 "
                                "near-tree meshes in vertex_irradiance.npz"),
                  glb_decode=("v = COLOR_0 * COLOR_0 * lightmaps.vertex_irradiance.range, then "
                              "irradiance = v * lightmaps.scale (pi) - exactly as a gamma2 lightmap texel. "
                              "ONE global `range` for all 14 meshes; do not look for a per-mesh one. glTF "
                              "multiplies COLOR_0 into base colour by default, so these 14 meshes must "
                              "consume it as irradiance, not as a tint."),
                  meshes={r["mesh"]: dict(verts=r["verts"], min=r.get("min"), max=r["max"], mean=r["mean"],
                                          mean_nonzero=r.get("mean_nonzero"), p99=r.get("p99"),
                                          roundtrip=r["roundtrip"],
                                          **{k: relay_vi[r["mesh"]][k]
                                             for k in ("range", "encoding", "mean_linear",
                                                       "roundtrip_rel_p99")
                                             if isinstance(relay_vi.get(r["mesh"]), dict)
                                             and k in relay_vi[r["mesh"]]})
                          for r in v.get("rows", [])},
                  note=(("COLOR_0 is in env.glb; the single global `range` comes from "
                         "uv2_relay_status.json."
                         if vi_in_glb else
                         "`in_glb: false` until env.glb is re-exported with COLOR_0 and the relay reports a "
                         "global range; this writer re-runs on that hand-off. Until then the near trees "
                         "stay on the PMREM path and must take their irradiance from sky.diffuse, not "
                         "sky.glossy (QA-12b-1).")),
                  relay_note=(relay or {}).get("vertex_irradiance_skipped"))

    instance = instance_block()
    inst_lod1 = instance_lod1_block(instance)
    if inst_lod1 is not None:
        instance["lod1"] = inst_lod1

    man["lightmaps"] = dict(
        mode="baked", uv="TEXCOORD_1", scale=g3.LIGHTMAP_SCALE,
        bake=dict(engine="CYCLES", type="DIFFUSE", direct=True, indirect=True, color=False,
                  samples=g3.SAMPLES_LM, denoiser="OPENIMAGEDENOISE",
                  rig="light_presets.apply_final_cycles (Eevee-only rigs asserted off, per job)",
                  occluders=("the Gate 1 export set PLUS the 127 real far trees and the lagoon water restored "
                             "from master_delivery.blend; the 127 billboard quads are hidden from the rays")),
        decode=dict(rgbm8="rgb = t.rgb * t.a * range", gamma2="rgb = t.rgb * t.rgb * range",
                    then="irradiance = rgb * lightmaps.scale; colorSpace = NoColorSpace in both variants"),
        uv2_relay_threshold=g3.UV2_RELAY_THRESHOLD,
        uv2_relaid=setj.get("uv2_relaid", []),
        uv2_npz="lightmap_uv2.npz",
        uv2_relay_status=(dict(file="uv2_relay_status.json", schema=relay.get("schema"),
                               written_by=relay.get("written_by"),
                               meshes_with_uv2=sum(1 for e in relay_all.values() if e.get("uv2_in_glb")),
                               meshes_total=len(relay_all), by_glb=by_glb,
                               relaid_in_glb=sorted(e.get("asset", k) for k, e in relay_uv2.items()
                                                    if e.get("uv2_in_glb")),
                               gltfpack_flags=relay.get("gltfpack_flags"))
                          if relay is not None else
                          "not written yet: every re-laid asset stays uv2_in_glb=false"),
        assets=assets,
        slots=dict(atlases=atlases,
                   uv2_in_glb=slots_uv2 if relay is not None else False,
                   uv2_in_glb_source=("uv2_relay_status.json uv2_all_meshes, glb == orn.glb: "
                                      f"{sum(1 for _, e in slot_meshes if e.get('uv2_in_glb'))} of "
                                      f"{len(slot_meshes)} meshes carry TEXCOORD_1"
                                      if relay is not None else "relay not written yet"),
                   note=("the per-instance uv2_offset / uv2_scale are `orn_slots`, unchanged since v2 and derived "
                         "from export/gate1_common.slot_uv; this block only names the atlas texture per pool and "
                         "atlas index. Atlas rows are laid out for the glTF UV flip (v_gltf = 1 - v_blender): "
                         "see export/gate3_compose.py, and `slot_check` is that proof read back from the PNG.")),
        vertex_irradiance=vertex,
        instance_irradiance=instance)

    # ------------------------------------------------------------ impostors
    protos, imp_bytes = {}, 0
    for jid, j in jobs.items():
        if j["kind"] != "impostor":
            continue
        r = rec(jid)
        if r is None:
            continue
        p = j["prototype"]
        ka = add_tex(f"gate3_imp_{p}_albedo_{g3.IMP_SHIP_PX}", g3.IMP_SHIP_PX, g3.IMP_SHIP_PX,
                     "impostor_albedo", "gamma2", False)
        ka2 = add_tex(f"gate3_imp_{p}_albedo_{g3.IMP_ATLAS_PX}", g3.IMP_ATLAS_PX, g3.IMP_ATLAS_PX,
                      "impostor_albedo", "gamma2", False)
        # review finding 5: the normal+depth atlas is packed with `--encode uastc` (gate3_pack.sh:44), i.e.
        # ASTC 4x4, and was labelled `rgba8_unorm`. The residency was always counted right (1 B/texel); only
        # the label was wrong, and a wrong label is what a viewer writes its loader against.
        kn = add_tex(f"gate3_imp_{p}_normdepth_{g3.IMP_SHIP_PX}", g3.IMP_SHIP_PX, g3.IMP_SHIP_PX,
                     "impostor_normal_depth", "uastc_astc4x4", False)
        kn2 = add_tex(f"gate3_imp_{p}_normdepth_{g3.IMP_ATLAS_PX}", g3.IMP_ATLAS_PX, g3.IMP_ATLAS_PX,
                      "impostor_normal_depth", "uastc_astc4x4", False)
        # review finding 1: the prototype's own z = 0 is the placement datum, not the bbox bottom.
        # base_z_m comes from the job the bake was handed (gate3_set.json impostor_prototypes), or from the
        # record itself once it carries it; centre_z_m is the billboard centre above that datum.
        base_z = r["base_z_m"] if "base_z_m" in r else round(float(j["bbox_min"][2]), 4)
        top_z = r["base_z_m"] + r["bbox_m"][2] if "base_z_m" in r else round(float(j["bbox_max"][2]), 4)
        centre_z = r["centre_z_m"] if "centre_z_m" in r else round(float(r["centre"][2]), 4)
        h_above = r.get("height_above_base_m", round(top_z - max(base_z, 0.0), 4))
        assert abs((centre_z - base_z) - r["centre_above_base_m"]) < 2e-3, f"{p}: base/centre disagree"
        protos[p] = dict(albedo=ka, normal_depth=kn, albedo_2k=ka2, normal_depth_2k=kn2,
                         range=r["range"], radius_m=r["radius_m"], bbox_m=r["bbox_m"],
                         base_z_m=base_z, centre_z_m=centre_z, height_above_base_m=h_above,
                         depth_range_m=r["depth_range_m"],
                         views=r["views"], alpha_coverage=r["alpha_coverage"],
                         render_s=r["render_s"], s_per_view=r["s_per_view"],
                         bytes=sum(f["bytes"] for f in r["files"].values()),
                         roundtrip_albedo=r["files"]["albedo_1024"]["roundtrip"])
        imp_bytes += protos[p]["bytes"]
    ship = g3.IMP_SHIP_PX
    # 8d r2: the Gate 3 impostor set was built from the far list AS IT WAS, so a prototype that is new to
    # the far block (the 39 hall-belt trees brought three: cypress_column_s2 / _s31 and pine_s29, at
    # _LOD2) has no key in `impostor_prototype_map` and the viewer's join would fall through. Extend it
    # here with gate3_set.py's own rule - "an impostor is always the LOD1 prototype" - and assert the
    # target is one of the ALREADY BAKED prototypes, so nothing is re-baked. Recorded, never silent.
    proto_map_full = dict(setj["impostor_prototype_map"])
    proto_map_added = {}
    _far_list = json.loads((g3.GATE1_OUT / "export_set.json").read_text())["tree_far_list"]
    for _t in _far_list:
        _p = _t["prototype"]
        if _p in proto_map_full:
            continue
        _q = _p[:-5] + "_LOD1" if _p.endswith("_LOD2") else _p
        assert _q in protos, (f"far tree prototype {_p!r} maps to {_q!r}, which has no baked impostor "
                              f"atlas - that would need an atlas bake, which is not in scope")
        proto_map_full[_p] = _q
        proto_map_added[_p] = _q
    if proto_map_added:
        print(f"[manifest_v4] impostors.prototype_map extended with {len(proto_map_added)} key(s) new to "
              f"the far block: {proto_map_added}")

    scale = ship / float(g3.IMP_ATLAS_PX)
    man["impostors"] = dict(
        mapping="octahedral", grid=g3.IMP_GRID,
        atlas_px=ship, frame_px=int(g3.IMP_FRAME_PX * scale), gutter_px=int(g3.IMP_GUTTER_PX * scale),
        inner_px=int(g3.IMP_INNER_PX * scale),
        variant_2k=dict(atlas_px=g3.IMP_ATLAS_PX, frame_px=g3.IMP_FRAME_PX, gutter_px=g3.IMP_GUTTER_PX,
                        inner_px=g3.IMP_INNER_PX,
                        note=("on disk; the budget lever is which of the two is loaded"),
                        tier0_stand_in=(
                            "THE 1 K TWIN HAS NO TIER-0 STAND-IN OF ITS OWN, on purpose (review r1 "
                            "finding 2). There is exactly ONE half-resolution ETC1S copy per prototype, "
                            "and `tiers.lowres.files` may name it ONCE: web/src/manifest.js keys "
                            "`upgradeOf` by the stand-in url and `lowresFor` by the full url, so two "
                            "entries on one stand-in collide in the first map and not the second, and "
                            "web/test/tiers_test.mjs asserts the two are the same size. The stand-in is "
                            "therefore filed under whatever the viewer DRAWS BY DEFAULT - the band "
                            "atlas, else the 2 K - and the 1 K and 2 K octahedral albedos stay published "
                            "at tier 1 with no stand-in. Consequence: `?imp2k=0` / `?impband=0` are "
                            "TIER-1 reverts. They show the default's stand-in until tier 1 lands and "
                            "then swap to the 1 K file; they are A/B levers, not a first-frame path. "
                            "Re-adding a row for the 1 K key would break the 1:1 pairing tiers_test "
                            "checks, so it is not done."),),
        encode=dict(albedo=("gamma2 on RGB at the prototype's own `range` (rgb = t.rgb * t.rgb * range, "
                            "LINEAR oetf, NOT sRGB), straight (un-premultiplied) alpha in A"),
                    normal_depth=("rgb = world normal * 0.5 + 0.5 (Blender Z-up); A is depth about the "
                                  "BILLBOARD CENTRE, a = 0.5 there: depth_from_centre_m = "
                                  "(a - 0.5) * depth_range_m, positive away from the camera. The camera "
                                  "stand-off used at bake time is not exported and is not needed."),
                    normal_depth_note=("block compressed (UASTC -> ASTC 4x4) on purpose while `unlit` holds "
                                       "and nothing samples the normal or the depth. If the viewer ever "
                                       "shades or soft-depth-tests the impostor, repack this map lossless "
                                       "(toktx --zcmp, no --encode): +3.0 MB resident per prototype at 1K, "
                                       "+48.0 MB over the 16.")),
        lighting=("baked: Cycles Combined at the final rig, sun + sky + leaf translucency, film_transparent, "
                  f"{g3.SAMPLES_IMPOSTOR} spp + OIDN, with a camera-invisible lawn plane for the ground bounce"),
        unlit=("the atlas already holds lit radiance: draw it straight into the linear buffer before the LUT, "
               "with no lightmap, no sun and no environment term"),
        frame_lookup=("d = normalize(camera_pos - billboard_pos) in BLENDER Z-up (from a three.js dir with "
                      "(x, -z, y)); n = d / (|d.x|+|d.y|+|d.z|); if n.z >= 0 { u = n.x; v = n.y } else "
                      "{ u = (1-|n.y|)*sign(n.x); v = (1-|n.x|)*sign(n.y) }; uv01 = (u,v)*0.5+0.5; "
                      "col = round(uv01.x*(grid-1)); row = round(uv01.y*(grid-1)) counted from the BOTTOM"),
        frame_uv=("u = (col*frame_px + gutter_px + f.x*inner_px) / atlas_px; "
                  "v_from_bottom likewise with row; clamp f to [0,1] and inset by half a texel"),
        instance_rotation=("IGNORED on purpose: the lighting is baked in world space, so the frame is picked "
                           "from the world-space view direction. Two instances of one prototype differ by "
                           "scale, not silhouette."),
        placement=("s = tree_far[i].height_m / prototypes[p].height_above_base_m; the quad is a screen-facing "
                   "square of side 2*radius_m*s centred at trunk_base + (0,0, centre_z_m*s). Both heights are "
                   "measured from the prototype's OWN z = 0, the plane trunk_base maps to - NOT from the "
                   "bbox bottom: `base_z_m` is 0 for 14 of the 16 prototypes but -2.6748 m on "
                   "ENV_tree_willow_s37_LOD1 and -0.7183 m on ENV_tree_willow_s11_LOD1 (fronds that hang "
                   "below the trunk base and are buried in the Phase 5 scene). Dividing by bbox_m[2] there "
                   "made those two impostors 19 % / 6 % too small and lifted them off their trunks."),
        prototype_map=proto_map_full,
        prototype_map_added=proto_map_added,
        prototypes=protos,
        billboards="join on tree_far[i].prototype through prototype_map",
        note=("46 of the 127 far trees were exported against an LOD2 blob; every impostor is baked from the "
              "LOD1 mesh, which is why prototype_map exists and why there are 16 atlases, not 25."))

    # ------------------------------------------------------------ impostors.band (Phase 8b)
    # The band atlas: 12 azimuths x 3 elevations of 341 px frames on a 4096x1024 atlas per prototype,
    # replacing the ALBEDO LOOKUP ONLY (docs/briefs/phase8b_band_atlas.md).  Every constant here is
    # COPIED from the bake's own sidecar `out/gate3/band/band.json` and none of it is re-derived:
    # `azimuth0_deg` alone decides which way 127 cards face, and a value computed twice is a value
    # that can disagree with itself.  The block is written whole or not at all, which is also how
    # web/src/manifest.js reads it.
    bj = next((q for q in (g3.OUT / "band" / "band.json",
                           g3.MAIN_ROOT / "export" / "out" / "gate3" / "band" / "band.json")
               if q.exists()), None)
    if bj is not None:
        band = json.loads(bj.read_text())
        assert band.get("schema") == "pfa-phase8b/band-atlas/1", f"band.json schema {band.get('schema')!r}"
        bdir = bj.parent
        # The atlases live beside tex_ktx2, not in it, so their `path` is relative to
        # `textures.gate3.ktx2_dir` and the viewer's joinDir resolves the `..` as a URL.
        bprotos, band_bytes, band_missing = {}, 0, []
        for name, p in sorted((band.get("prototypes") or {}).items()):
            key, fn = p["albedo"], p["file"]
            f = bdir / fn
            if not f.exists():
                band_missing.append(key)
                continue
            files[key] = dict(path=f"../band/{fn}", w=int(band["atlas_px"][0]), h=int(band["atlas_px"][1]),
                              map="impostor_band", colorspace="linear", encode="gamma2",
                              bytes=f.stat().st_size, mips=False,
                              resident_mb=g3.resident_mb(band["atlas_px"][0], band["atlas_px"][1],
                                                         "gamma2", False))
            band_bytes += f.stat().st_size
            bprotos[name] = {k: p[k] for k in ("albedo", "file", "range", "range_same_as_octahedral",
                                               "crown_sphere_m", "radius_m", "centre_z_m", "ktx2_bytes")
                             if k in p}
            bprotos[name]["bytes"] = f.stat().st_size
        if band_missing:
            print(f"[manifest_v4] impostors.band: {len(band_missing)} atlas(es) named in band.json are not "
                  f"on disk: {band_missing[:3]}", flush=True)
        if bprotos:
            man["impostors"]["band"] = dict(
                dir="../gate3/band",
                columns=int(band["grid_az"]), rows=int(band["grid_el"]),
                # every one of these is band.json's own value, copied
                **{k: band[k] for k in ("mapping", "atlas_px", "frame_px", "gutter_px", "inner_px",
                                        "pad_px", "azimuth0_deg", "azimuth0_convention",
                                        "azimuth0_blender_dir", "azimuth0_octahedral_frame",
                                        "azimuth_step_deg", "azimuth_dir", "elevations_deg",
                                        "elevation_datum", "row_order", "cell_dirs_blender",
                                        "octahedral_nearest_frame", "frame_lookup", "frame_uv",
                                        "encode", "ktx2", "lighting", "unlit", "instance_rotation",
                                        "placement", "placement_note", "samples", "prototype_map")
                   if k in band},
                row_origin="bottom",
                range_source="octahedral",
                range_note=("`range` per prototype EQUALS impostors.prototypes[p].range, so one constant "
                            "decodes both atlases; band.json asserts it per prototype in "
                            "`range_same_as_octahedral`."),
                replaces=("the ALBEDO lookup only. normal_depth, the irradiance modulation, the darkening "
                          "floor and `placement` are the octahedral block's, unchanged - band.json's "
                          "`placement_note` records that the band frames the same bounding sphere at the "
                          "same ortho scale."),
                tier_note=("tier 1, with the prototype's 1 K OCTAHEDRAL half-resolution ETC1S copy as the "
                           "tier-0 stand-in: the first frame draws the 1 K octahedral and tier 1 upgrades "
                           "straight to the band. `?impband=0` falls back to the octahedral 2 K, which is "
                           "published at tier 1 with no stand-in of its own."),
                source=dict(sidecar=str(bj), schema=band.get("schema"),
                            generator=band.get("generator"), bytes=band_bytes),
                prototypes=bprotos, count=len(bprotos))
            print(f"[manifest_v4] impostors.band: {len(bprotos)} atlas(es), {band_bytes} B, "
                  f"{band['grid_az']}x{band['grid_el']} frames of {band['frame_px']} px on "
                  f"{band['atlas_px'][0]}x{band['atlas_px'][1]}, azimuth0 {band['azimuth0_deg']} deg",
                  flush=True)

    # ------------------------------------------------------------ probe + sky.diffuse
    pr = rec("probe_hero")
    if pr:
        man["probe"] = dict(kind="cube", faces=list(g3.PROBE_FACES), size_px=pr["ship_px"],
                            rendered_px=pr["rendered_px"], format="rgbe .hdr (32-bit EXR kept on disk)",
                            dir="probe", station=pr["station"],
                            position_blender=pr["position_blender"], position_gltf=pr["position_gltf"],
                            axes=("faces are rendered in Blender world axes and named for the three.js axes "
                                  "after the (x, z, -y) swap; face `px` looks along three.js +X, up -Y"),
                            samples=pr["samples"], world_branch=pr["world_branch"],
                            files={k: dict(hdr=v["hdr"], bytes=v["hdr_bytes"], mean=v["mean"], max=v["max"],
                                           hdr_rel_p99=v["hdr_rel_p99"]) for k, v in pr["faces"].items()},
                            use=("fallback environment for the water plane and anything the planar Reflector "
                                 "cannot reach; NOT the diffuse environment - see sky.diffuse"))
    sk = rec("sky_diffuse")
    if sk:
        man["sky"]["diffuse"] = dict(hdr=sk["hdr"], exr=sk["exr"], w=sk["w"], h=sk["h"], branch="diffuse",
                                     bytes_hdr=sk["hdr_bytes"], rotation_deg=90.0, u_offset=0.25,
                                     stats=sk["stats"], hdr_rel_p99=sk["hdr_rel_p99"],
                                     orientation_check=dict(upper_half_mean=sk["upper_mean"],
                                                            lower_half_mean=sk["lower_mean"]),
                                     use=("PMREM source for IRRADIANCE only (scene.environment / diffuse). "
                                          "sky.glossy stays the specular PMREM and sky.camera the background. "
                                          "Anything with a lightmap or a baked impostor takes no term from it."))

    # ------------------------------------------------------------ textures.gate3 + budget
    man["textures"]["gate3"] = dict(
        ktx2_dir="tex_ktx2", files=files, missing=missing_ktx,
        encoders=dict(rgbm8="toktx --t2 --zcmp 18 --genmipmap --assign_oetf linear (lossless, RGBA8 resident)",
                      gamma2="toktx --t2 --encode uastc --uastc_quality 2 --zcmp 18 --genmipmap --assign_oetf linear",
                      impostor=("toktx --t2 --encode uastc --uastc_quality 2 --zcmp 18 --assign_oetf linear "
                                "(no mips: an octahedral atlas mips across frame boundaries). Both impostor "
                                "maps, albedo and normal+depth, go through this one encoder.")),
        bytes=sum(f["bytes"] for f in files.values()),
        resident_rule=("ASTC 4x4 on the Apple GPU (`gamma2`, `uastc_astc4x4`) = 1 byte/texel, x4/3 for the "
                       "mip chain; an `rgbm8` / `rgba8` variant is uncompressed RGBA8 = 4 bytes/texel; a "
                       "texture without mips counts x1.0"))

    def res(pred):
        return round(sum(f["resident_mb"] for k, f in files.items() if pred(k, f)), 2)

    own_mb = res(lambda k, f: f["map"] == "lightmap" and f["encode"] == "gamma2" and "_lmg1_" not in k)
    atlas_mb = res(lambda k, f: f["map"] == "lightmap_atlas" and f["encode"] == "gamma2")
    imp_mb = round(sum(files[p["albedo"]]["resident_mb"] + files[p["normal_depth"]]["resident_mb"]
                       for p in protos.values() if p["albedo"] in files and p["normal_depth"] in files), 2)
    probe_mb = round(6 * g3.PROBE_SHIP_PX * g3.PROBE_SHIP_PX * 4 * 4 / 3 / (1024 * 1024), 2) if pr else 0.0
    sky_mb = round(g3.SKY_DIFFUSE_W * g3.SKY_DIFFUSE_H * 4 * 4 / 3 / (1024 * 1024), 2) if sk else 0.0
    b = man["budget"]
    carried = {k: v for k, v in b["resident_mb"].items()
               if k not in ("total", "lightmaps_own_map", "lightmap_slot_atlases", "tree_impostor_atlases")}
    band_mb = res(lambda k, f: f["map"] == "impostor_band")
    gate3 = dict(gate3_lightmaps_own=own_mb, gate3_lightmap_slot_atlases=atlas_mb,
                 gate3_tree_impostors=imp_mb, gate3_probe_cube=probe_mb, gate3_sky_diffuse=sky_mb)
    if band_mb:
        # 8b: the band atlases are a tier-1 ADDITION, not a replacement - the octahedral pair stays
        # published for `?impband=0` / `?imp2k=0`, so both sit in the reservation.
        gate3["gate3_tree_band_atlases"] = band_mb
    total = round(sum(carried.values()) + sum(gate3.values()), 2)
    b["resident_mb"] = dict(**carried, **gate3, total=total)
    b["gate3_reservation_mb"] = 459.0
    b["gate3_measured_mb"] = round(sum(gate3.values()), 2)
    b["gate3_vs_reservation_mb"] = round(sum(gate3.values()) - 459.0, 2)
    b["measured_viewer_baseline_mb"] = QA12B_VIEWER_TEXTURE_MB
    b["measured_total_mb"] = round(QA12B_VIEWER_TEXTURE_MB + sum(gate3.values()), 2)
    b["levers_not_applied"] = list(b.get("levers_not_applied", [])) + [
        f"impostor atlases at {g3.IMP_ATLAS_PX} px instead of {g3.IMP_SHIP_PX} "
        f"(+{round(imp_mb * 3, 2)} MB; the 2K files are on disk)",
        "lightmaps shipped as the lossless rgbm8 variant instead of gamma2 "
        f"(+{round((own_mb + atlas_mb) * 3, 2)} MB, exact instead of the measured gamma-2 error)"]
    b["note"] = ("two accountings, both reported: against this file's own carried rows the total is "
                 f"{total} MB; against the viewer's MEASURED texture residency at round 12b "
                 f"({QA12B_VIEWER_TEXTURE_MB} MB) it is {b['measured_total_mb']} MB. The budget line is "
                 f"{b['budget_mb']} MB.")

    # ------------------------------------------------------------ compositor.mist (lead, viewer round 13b)
    # The carried `compositor` block records COMP_golden_hour's `Mist` INPUT as 0.0, which is only what a
    # disconnected socket's stored default reports - the live value is the Mist PASS the Render Layers node
    # feeds it, and that pass is shaped entirely by scene.world.mist_settings. export/read_mist.py reads them
    # out of master_delivery.blend (read-only, no render) into out/gate3/mist_settings.json; this copies them
    # in so the viewer has the haze ramp's real start and depth instead of a zero.
    # Review r3 finding 2: export/out/ is gitignored, so a local-only lookup would silently drop
    # `compositor.mist` after the merge (the viewer would keep the 0.0 haze and nothing would say so).
    # Same local-then-MAIN resolution as the relay json above, and it says so when neither exists.
    mp = next((q for q in (g3.OUT / "mist_settings.json",
                           g3.MAIN_ROOT / "export" / "out" / "gate3" / "mist_settings.json") if q.exists()),
              None)
    if mp is None:
        print("[gate3] WARNING: no mist_settings.json in out/gate3 or MAIN's - compositor.mist is null and "
              "the viewer has no haze ramp. Run: scripts/blender_run.sh 600 -- --background "
              "master_delivery.blend --python export/read_mist.py", file=sys.stderr)
        cb = man.get("compositor")
        man["compositor"] = dict(cb if isinstance(cb, dict) else {}, mist=None,
                                 mist_missing="mist_settings.json not found in out/gate3 or MAIN's; run "
                                              "export/read_mist.py. COMP_golden_hour's own `Mist` group "
                                              "input is a disconnected socket's 0.0 default, not the value "
                                              "the render used.")
    else:
        mj = json.loads(mp.read_text())
        assert mj.get("schema") == "pfa-phase6/gate3-mist/1", f"mist schema {mj.get('schema')!r}"
        comp_block = man.get("compositor")
        if not isinstance(comp_block, dict):
            comp_block = {}
        comp_block["mist"] = dict(**(mj.get("mist") or {}),
                                  use_pass_mist=mj.get("use_pass_mist"),
                                  units="metres (1 BU = 1 m), measured along the view ray from the camera",
                                  source="master_delivery.blend scene.world.mist_settings, "
                                         "read by export/read_mist.py",
                                  file="mist_settings.json", read_at=mj.get("source"),
                                  formula=mj.get("note"),
                                  group_input_note=("COMP_golden_hour's own `Mist` group input reads 0.0 in "
                                                    "this block: that is a disconnected socket's stored "
                                                    "default, NOT the value the render used."))
        man["compositor"] = comp_block

    # ------------------------------------------------------------ Phase 6c item D: the foliage card maps
    # `materials.note` says a material that is not in `materials.sets` keeps what the glb gave it, and for the
    # eight leaf/shrub/reed cards what the glb gave them is the RAW 1 K texture - the Phase 5 material is
    # `image * tint`, and its Translucent branch is not in the glb at all. export/read_foliage.py reads both
    # out of master_delivery.blend and export/foliage_tex.py composes them; this block is how the viewer finds
    # them. These maps REPLACE the glb's baseColorTexture on exactly these materials.
    fo_p = next((q for q in (g3.OUT / "foliage" / "foliage_tex.json",
                             g3.MAIN_ROOT / "export" / "out" / "gate3" / "foliage" / "foliage_tex.json")
                 if q.exists()), None)
    if fo_p is not None:
        fo = json.loads(fo_p.read_text())
        assert fo.get("schema") == "pfa-phase6c/foliage-tex/1", f"foliage schema {fo.get('schema')!r}"
        mats_block = man.get("materials")
        if not isinstance(mats_block, dict):
            mats_block = {}
        def key(fname):
            return fname[:-4] if fname.endswith(".png") else fname
        entries = {}
        for m, v in sorted(fo["materials"].items()):
            f, st, tr = v["files"], v["stats"], v["translucency"]
            nrm = fo["normals"].get(f.get("normal"), {}) if f.get("normal") else {}
            entries[m] = dict(
                albedo={str(px): key(f[f"albedo_{px}"]) for px in fo["sizes"] if f"albedo_{px}" in f},
                translucency_map={str(px): key(f[f"translu_{px}"]) for px in fo["sizes"]
                                  if f"translu_{px}" in f},
                normal={str(px): key(n) for px, n in (nrm.get("files") or {}).items()},
                normal_scale=tr.get("normal_strength"),
                translucency=dict(colour_multiplier=tr.get("colour_multiplier"),
                                  constant=tr.get("constant"),
                                  factor_range=[tr.get("factor_min"), tr.get("factor_max")],
                                  factor_mean_in_leaf=tr.get("factor_mean_in_leaf"),
                                  how="mix = factor_map (linear grey, already includes the constant); "
                                      "0 = the Principled branch, 1 = a Translucent BSDF whose colour is "
                                      "albedo * colour_multiplier. With no map, apply `constant` uniformly."),
                alphaMode=v["alpha_mode"], alphaCutoff=v["alpha_cutoff"],
                double_sided=v["double_sided"], roughness=v["roughness"],
                specular=v["specular"], sheen=v["sheen"],
                source_texture=st["source"], source_px=st["source_px"], tint=st["tint"],
                hue_src_vs_material=[st["src_hsv"], st["tinted_hsv"]])
        mats_block["foliage"] = dict(
            dir="out/gate3/foliage/tex_ktx2", sizes=fo["sizes"],
            colorspace=dict(albedo="srgb", translucency_map="linear", normal="linear"),
            bytes=fo.get("ktx2_bytes"), files=len(fo.get("ktx2_files") or []),
            replaces=("the glb's baseColorTexture on these eight materials: the glb carries the untinted "
                      "source PNG, which is the same card for MAT_shrub / MAT_shrub_light / MAT_shrub_dry "
                      "and about 1.9x too dark on all three"),
            resolution_note=("1 K only. Every source is 1024x1024 (scripts/mat_leaf_textures.py), so the "
                             "2048 set round 1 also shipped was an upsample - 4x the memory, no new detail, "
                             "its only gain a smoother alpha edge at 3 m - and the lead dropped it "
                             "(decisions.md 2026-09-17, decision 2). A genuine 2 K would mean re-running the "
                             "generator, i.e. a Phase 5 material change, which needs the user's approval."),
            per_size_bytes={str(px): sum(os.path.getsize(os.path.join(str(fo_p.parent), "tex_ktx2", fn))
                                         for fn in (fo.get("ktx2_files") or [])
                                         if fn.endswith(f"_{px}.ktx2"))
                            for px in fo["sizes"]},
            materials=entries,
            source="export/read_foliage.py + export/foliage_tex.py + export/gltf_pack.sh --foliage")
        man["materials"] = mats_block

    # ------------------------------------------------------------ Phase 6c item E: the shrub/reed LOD1 set
    sl_p = next((q for q in (g3.GATE1_OUT / "shrub_lod1.json",
                             g3.MAIN_ROOT / "export" / "out" / "gate1" / "shrub_lod1.json") if q.exists()),
                None)
    if sl_p is not None:
        sl = json.loads(sl_p.read_text())
        assert sl.get("schema") == "pfa-phase6c/shrub-lod1/1", f"shrub_lod1 schema {sl.get('schema')!r}"
        sl_glb = next((q for q in (g3.GATE1_OUT / "env_shrubs.glb",
                                   g3.MAIN_ROOT / "export" / "out" / "gate1" / "env_shrubs.glb")
                       if q.exists()), None)
        man["shrubs"] = dict(lod1=dict(
            glb="env_shrubs.glb", bytes=(sl_glb.stat().st_size if sl_glb else None),
            load="lazy, beside env_trees.glb; until it is in, every shrub is the env.glb LOD2 card",
            textures="external, not embedded (gltfpack -tr): the same KTX2 in `textures.ktx2_dir` env.glb "
                     "carries. The tinted replacements are `materials.foliage`.",
            meshes=[dict(lod2_mesh=k, mesh=v["mesh"], source=v["lod1_mesh"], tris=v["tris"],
                         verts=v["verts"], lod2_tris=v["lod2_tris"], placements=v["placements"],
                         materials=v["materials"]) for k, v in sorted(sl["meshes"].items())],
            placements=len(sl["placements"]),
            placed_tris=sl["placed_tris"], placed_tris_lod2=sl["placed_tris_lod2"],
            unique_tris=sum(v["tris"] for v in sl["meshes"].values()),
            join=("lightmaps.instance_irradiance.lod1 - the SAME per-placement irradiance in this glb's own "
                  "row order, so swapping LOD does not change a shrub's lighting"),
            not_in_lod1=dict(placements=sl["placements_without_lod1"], meshes=sl["skipped_meshes"]),
            source="export/shrub_lod1.py + export/gltf_pack.sh --shrubs",
            note=("a separate glb rather than more meshes inside env.glb: putting them in env.glb means "
                  "re-running gate1_set.py, which rebuilds the UV1 atlases every Gate 2 PBR bake and every "
                  "Gate 3 lightmap is pinned to (export/shrub_lod1.py, export/README.md item 34).")))

    # ------------------------------------------------------------ Phase 6c item A: the far trees' meshes
    # export/trees_far.py + `gltf_pack.sh --trees` build `env_trees.glb`: the 16 impostor prototypes as real
    # LOD2 meshes, instanced at the same 127 `tree_far` placements the impostors use, in their own file so
    # the viewer can load it lazily and swap mesh <-> impostor at `treeMeshDist`. Same local-then-MAIN
    # resolution as every other hand-off, because export/out is gitignored.
    tf_p = next((q for q in (g3.GATE1_OUT / "trees_far.json",
                             g3.MAIN_ROOT / "export" / "out" / "gate1" / "trees_far.json") if q.exists()),
                None)
    if tf_p is not None:
        tf = json.loads(tf_p.read_text())
        assert tf.get("schema") == "pfa-phase6c/trees-far/1", f"trees_far schema {tf.get('schema')!r}"
        tf_glb = next((q for q in (g3.GATE1_OUT / "env_trees.glb",
                                   g3.MAIN_ROOT / "export" / "out" / "gate1" / "env_trees.glb")
                       if q.exists()), None)
        # review r5 finding 1/3: THE GUARD THAT WOULD HAVE CAUGHT THE BLOCKER. manifest_v4 ran before
        # trees_far.py was re-run for the belt, so the manifest advertised 127 placements against a
        # 166-instance glb and the viewer's join would have failed and dropped the whole far-tree layer.
        # The count and the billboard identity are now tied to the export set, and the glb may not be
        # older than the report that describes it.
        # PHASE 9 item 1: the far set may leave TAGGED rows without a mesh (export/belt_rule.py), so the
        # count that has to close is placements + billboard_only, and the billboard identity is checked
        # through each placement's own `index` instead of its position in the list.
        _tf_bo = tf.get("billboard_only", [])
        assert len(tf["placements"]) + len(_tf_bo) == len(man["tree_far"]), (
            f"trees_far.json has {len(tf['placements'])} placements + {len(_tf_bo)} billboard-only rows "
            f"and the export set {len(man['tree_far'])} far trees - re-run export/trees_far.py AND "
            f"PFA_TREES_SET=walkup export/trees_far.py BEFORE manifest_v4")
        _bad = [pl["index"] for pl in tf["placements"] + _tf_bo
                if pl["billboard"] != man["tree_far"][pl["index"]]["billboard"]]
        assert not _bad, (f"trees_far.json row {_bad[:4]} names a different billboard than the export "
                          f"set's tree_far row of the same index - the two were built from different lists")
        assert [pl["index"] for pl in tf["placements"]] == sorted(pl["index"] for pl in tf["placements"]), \
            "trees_far.json placements are not in tree_far index order - the cross-set subsequence check " \
            "and the positional join both depend on that order"
        if tf_glb is not None and tf_p.exists():
            assert tf_glb.stat().st_mtime >= tf_p.stat().st_mtime - 1, (
                f"{tf_glb.name} is older than {tf_p.name} - the glb was not re-packed after the last "
                f"trees_far.py run (export/gltf_pack.sh --trees)")
        man["trees"] = dict(far_mesh=dict(
            glb="env_trees.glb",
            bytes=(tf_glb.stat().st_size if tf_glb else None),
            load="lazy: nothing in the first frame depends on it; until it is in, the 127 far trees are the "
                 "impostors they always were",
            textures=("external, not embedded: the leaf and bark KTX2 in `textures.ktx2_dir` that env.glb "
                      "already carries (gltfpack -tr). Serve tex_ktx2 beside the glb or the trees load "
                      "untextured."),
            prototypes=[dict(name=k, mesh=v["mesh"], tris=v["tris"], verts=v["verts"],
                             materials=v["materials"],
                             height_above_base_m=v["height_above_base_m"],
                             src_tris=v["src_tris"], card_scale=v["reduction"]["card_scale"],
                             cards=[v["reduction"]["cards_kept"], v["reduction"]["cards_before"]])
                        for k, v in sorted(tf["prototypes"].items())],
            placements=[dict(index=pl["index"], prototype=pl["prototype"], mesh=pl["mesh"],
                             loc=pl["loc"], scale=pl["scale"], height_m=pl["height_m"],
                             source_tree=pl["source_tree"], billboard=pl["billboard"],
                             walk_dist_m=pl["walk_dist_m"])
                        for pl in tf["placements"]],
            placement=tf["placement_check"]["rule"],
            impostor_join="placements[i].billboard is tree_far[i].billboard and placements[i].prototype is "
                          "impostors.prototype_map[tree_far[i].prototype]: the mesh and the impostor are the "
                          "same tree at the same transform, which is what makes the crossfade legal",
            crown_top_deviation_m=tf["placement_check"]["worst_crown_top_deviation_m"],
            rows=("every tree is bark + leaf, so gltfpack -mi emits TWO instanced nodes per prototype (32 "
                  "meshes, 254 rows for 127 trees). Per-placement data is per TREE, not per row: a row's "
                  "placement is found the same way as `lightmaps.instance_irradiance`, by matching the "
                  "EXT_mesh_gpu_instancing TRANSLATION to `placements[].loc` in glTF space "
                  "(Blender (x, y, z) -> glTF (x, z, -y)), because gltfpack drops node names."),
            color0=(dict(tf["color0"], present=True) if tf.get("color0", {}).get("source")
                    else dict(present=False, note=tf["color0"].get("note"))),
            lighting=trees_lighting_block(tf, man),
            billboard_only=dict(
                count=len(_tf_bo),
                rule=(tf.get("billboard_only_rule") or {}).get("rule"),
                radius_m=(tf.get("billboard_only_rule") or {}).get("radius_m"),
                draw_within_m=(tf.get("billboard_only_rule") or {}).get("draw_within_m"),
                tag=(tf.get("billboard_only_rule") or {}).get("tag"),
                note=("these tree_far rows have NO instance row in this glb and are the impostor at EVERY "
                      "distance. Their impostors must still be MODULATED: `lighting.mesh.placements` "
                      "carries a row for them with `mesh: false`, and the viewer must set iIrr for them "
                      "while leaving iNear at 0."),
                rows=[dict(index=b["index"], billboard=b["billboard"], source_tree=b["source_tree"],
                           prototype=b["prototype"], loc=b["loc"], height_m=b["height_m"],
                           nearest_station=b.get("nearest_station"),
                           nearest_station_m=b.get("nearest_station_m")) for b in _tf_bo]),
            unique_tris=sum(v["tris"] for v in tf["prototypes"].values()),
            placed_tris=tf["gltf"]["placed_tris"],
            source="export/trees_far.py + export/gltf_pack.sh --trees",
            topology="out/gate3/trees_far/topology.json"))
        # -------------------------------------------------- Phase 6c round 3 item 2: the WALK-UP set
        # `PFA_TREES_SET=walkup export/trees_far.py` + `gltf_pack.sh --trees-lod1` build
        # `env_trees_lod1.glb`: the same 16 prototypes at 30 k instead of 8 k, at the SAME 127 placements
        # in the SAME row order, for the handful of trees a walker comes within ~15 m of. The viewer draws
        # it only inside `draw_within_m`; beyond that the 8 k far mesh, and beyond `treeMeshDist` the
        # impostor.
        tw_p = next((q for q in (g3.GATE1_OUT / "trees_far_lod1.json",
                                 g3.MAIN_ROOT / "export" / "out" / "gate1" / "trees_far_lod1.json")
                     if q.exists()), None)
        if tw_p is not None:
            tw = json.loads(tw_p.read_text())
            assert tw.get("schema") == "pfa-phase6c/trees-far/1", f"trees_far_lod1 schema {tw.get('schema')!r}"
            assert tw.get("set") == "walkup", f"trees_far_lod1.json is the {tw.get('set')!r} set"
            tw_glb = next((q for q in (g3.GATE1_OUT / "env_trees_lod1.glb",
                                       g3.MAIN_ROOT / "export" / "out" / "gate1" / "env_trees_lod1.glb")
                           if q.exists()), None)
            # PHASE 9 item 1. The two sets no longer hold the same rows: the billboard-only radius is
            # each set's OWN viewer draw distance, and the walk-up set is drawn at 15 m against the far
            # set's 45 m, so it keeps fewer tagged rows. Its rows are a SUBSET of the far set's, asserted
            # here by index and, on the geometry, twice more - pre-pack, node name and translation against
            # env_trees.gltf (trees_far.py `instance_order_check`), and post-pack, node-for-node row counts
            # and materials (verify_glb `trees_lod1_order_check`).
            # While the two sets DO hold the same rows the list is still stated by reference, exactly as
            # before, because a second copy could only ever disagree with the first; only when they differ
            # is the walk-up list written out, which is a shape `web/src/foliageLazy.js` already reads
            # (`Array.isArray( w.placements ) ? w.placements : ... same_as`).
            _tw_bo = tw.get("billboard_only", [])
            assert len(tw["placements"]) + len(_tw_bo) == len(man["tree_far"]), \
                (f"the walk-up set has {len(tw['placements'])} placements + {len(_tw_bo)} billboard-only "
                 f"rows against {len(man['tree_far'])} far trees")
            _tw_idx = [pl["index"] for pl in tw["placements"]]
            _tf_idx = [pl["index"] for pl in tf["placements"]]
            assert _tw_idx == sorted(_tw_idx), "the walk-up placements are not in tree_far index order"
            assert set(_tw_idx) <= set(_tf_idx), (
                f"the walk-up set places rows the far set does not: "
                f"{sorted(set(_tw_idx) - set(_tf_idx))[:4]} - the walk-up glb is drawn at the SHORTER "
                f"distance, so its rows must be a subset of the far set's")
            _same_rows = _tw_idx == _tf_idx
            man["trees"]["walkup_mesh"] = dict(
                glb="env_trees_lod1.glb",
                bytes=(tw_glb.stat().st_size if tw_glb else None),
                load="lazy, beside env_trees.glb; until it is in, every tree is the 8 k far mesh",
                draw_within_m=15.0,
                textures="external, exactly as far_mesh: the same leaf and bark KTX2 in textures.ktx2_dir",
                prototypes=[dict(name=k, mesh=v["mesh"], tris=v["tris"], verts=v["verts"],
                                 materials=v["materials"],
                                 height_above_base_m=v["height_above_base_m"],
                                 src_tris=v["src_tris"], card_scale=v["reduction"]["card_scale"],
                                 cards=[v["reduction"]["cards_kept"], v["reduction"]["cards_before"]])
                            for k, v in sorted(tw["prototypes"].items())],
                placements=(dict(
                    count=len(tw["placements"]),
                    same_as="trees.far_mesh.placements",
                    note="identical rows in identical order - read them from far_mesh; they are not "
                         "repeated here so the two can never disagree",
                    verified_pre_pack=tw["gltf"].get("instance_order_check"),
                    verified_post_pack="verify_glb.py trees_lod1_order_check") if _same_rows else
                    [dict(index=pl["index"], prototype=pl["prototype"], mesh=pl["mesh"],
                          loc=pl["loc"], scale=pl["scale"], height_m=pl["height_m"],
                          source_tree=pl["source_tree"], billboard=pl["billboard"],
                          walk_dist_m=pl["walk_dist_m"]) for pl in tw["placements"]]),
                placements_note=(None if _same_rows else
                                 "a SUBSET of trees.far_mesh.placements, in the same order: this set is "
                                 "drawn within draw_within_m (15 m) and the far set within 45 m, so the "
                                 "Phase 9 billboard-only rule leaves it fewer tagged rows. The rows that "
                                 "ARE here are byte-for-byte the far set's, and their per-placement "
                                 "irradiance is still read from trees.far_mesh.lighting by location."),
                billboard_only=dict(
                    count=len(_tw_bo),
                    rule=(tw.get("billboard_only_rule") or {}).get("rule"),
                    radius_m=(tw.get("billboard_only_rule") or {}).get("radius_m"),
                    draw_within_m=(tw.get("billboard_only_rule") or {}).get("draw_within_m"),
                    tag=(tw.get("billboard_only_rule") or {}).get("tag"),
                    note=("these tree_far rows have NO instance row in env_trees_lod1.glb. On desktop, "
                          "which loads this set, they are the impostor at every distance and their iIrr "
                          "must still come from trees.far_mesh.lighting (rows with `mesh: false`)."),
                    rows=[dict(index=b["index"], billboard=b["billboard"], source_tree=b["source_tree"],
                               prototype=b["prototype"], loc=b["loc"], height_m=b["height_m"],
                               nearest_station=b.get("nearest_station"),
                               nearest_station_m=b.get("nearest_station_m")) for b in _tw_bo]),
                join=("the same positional join as far_mesh, and the same result: 32 meshes and 254 rows "
                      "for 127 trees, node for node. A row's placement - and therefore its entry in "
                      "far_mesh.lighting's per-placement irradiance - is found by matching the "
                      "EXT_mesh_gpu_instancing TRANSLATION to trees.far_mesh.placements[].loc in glTF "
                      "space (Blender (x, y, z) -> glTF (x, z, -y)), because gltfpack drops node names."),
                color0=dict(present=False, note=tw["color0"].get("note")),
                lighting="reuse trees.far_mesh.lighting verbatim: same placements, same rows, same order. "
                         "This set carries no vertex AO by design (brief item 2) - the viewer's interior "
                         "term covers it.",
                crown_top_deviation_m=tw["placement_check"]["worst_crown_top_deviation_m"],
                unique_tris=sum(v["tris"] for v in tw["prototypes"].values()),
                placed_tris=tw["gltf"]["placed_tris"],
                tri_target=tw["tri_target"],
                source="PFA_TREES_SET=walkup export/trees_far.py + export/gltf_pack.sh --trees-lod1")
        else:
            print("[gate3] note: no out/gate1/trees_far_lod1.json - manifest has no `trees.walkup_mesh` "
                  "block (run PFA_TREES_SET=walkup export/trees_far.py, then "
                  "export/gltf_pack.sh --trees-lod1)", file=sys.stderr)
    else:
        print("[gate3] note: no out/gate1/trees_far.json - manifest has no `trees.far_mesh` block "
              "(run export/trees_far.py, then export/gltf_pack.sh --trees)", file=sys.stderr)

    man["gate3"] = dict(generated=time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                        jobs=len(jobs), records=len(list(g3.REC.glob("*.json"))))
    p = g3.OUT / "manifest.json"
    p.write_text(json.dumps(man, indent=1) + "\n")
    print(f"[gate3] manifest v4 -> {p} ({p.stat().st_size} B), textures.gate3 {len(files)} files, "
          f"missing {len(missing_ktx)}, resident {total} MB (measured basis {b['measured_total_mb']} MB)")
    return man


if __name__ == "__main__":
    main()
