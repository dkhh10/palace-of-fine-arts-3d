#!/usr/bin/env python3
"""Gate 1 step 5d: prove the packed glbs still carry every placement, after gltfpack has folded the nodes.

    python3 export/verify_glb.py [export/out/gate1]

Per class it also asserts that every material name the export set uses survives into the glb, for any
class packed with -km (gltfpack merges materials with identical factors otherwise, and the ten identical
backdrop greys collapsed to one, orphaning nine Gate 2 texture sets). The other invariant is TRIANGLES DRAWN,
not node count: gltfpack legitimately merges single-use nodes that
share a material (564 ARCH objects become 442 nodes, the 4 ground objects one node), so a node count proves
nothing, while sum(primitive triangles x instance count) must equal export_set.json's placed triangles for that
class. Node and instance counts are reported alongside. The complementary check - nothing stacked at the world
origin, which is what QA-11c-1 shipped when 1379 shrub nodes were written with no transform - is made in
export/gltf_gate1.py on the UNCOMPRESSED .gltf, where the transforms are still readable; here only plain nodes
can be tested, because a meshopt-compressed instancing accessor cannot be decoded without the codec.
Exit 1 on any mismatch. No Blender, no GPU.
"""
import json
import os
import struct
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def glb_json(path):
    b = path.read_bytes()
    assert b[:4] == b"glTF", f"{path} is not a glb"
    ln = struct.unpack("<I", b[12:16])[0]
    return json.loads(b[20:20 + ln]), b


def accessor_count(doc, idx):
    return doc["accessors"][idx]["count"] if idx is not None else 0


def attr_tris(doc, attr):
    """Triangles in the file's MESHES (not placements) whose primitive carries `attr`. gltfpack merges
    primitives that share a material, so a primitive or vertex count proves nothing across the pack while the
    triangle total is preserved to within the degenerate-triangle tolerance."""
    t = 0
    for me in doc.get("meshes", []):
        for pr in me.get("primitives", []):
            if attr not in (pr.get("attributes") or {}):
                continue
            if "indices" in pr:
                t += accessor_count(doc, pr["indices"]) // 3
            else:
                t += accessor_count(doc, (pr.get("attributes") or {}).get("POSITION")) // 3
    return t


def mesh_centre(doc, mesh_idx):
    """Centre of a mesh's own bounding box, from the POSITION accessors' min/max (no codec needed)."""
    lo = [1e30] * 3
    hi = [-1e30] * 3
    seen = False
    for pr in doc["meshes"][mesh_idx].get("primitives", []):
        ai = (pr.get("attributes") or {}).get("POSITION")
        if ai is None:
            continue
        acc = doc["accessors"][ai]
        if "min" not in acc or "max" not in acc:
            continue
        seen = True
        for i in range(3):
            lo[i] = min(lo[i], acc["min"][i])
            hi[i] = max(hi[i], acc["max"][i])
    return [(lo[i] + hi[i]) / 2.0 for i in range(3)] if seen else None


def shrub_lod1_order_check(out, bad):
    """Phase 6c item E: `instance_order_shrub_lod1.json` against `env_shrubs.glb` itself.

    Both LODs bind the SAME per-placement irradiance, so the LOD1 row order has to be as hard-pinned as the
    LOD2 one: a stale order file does not look like an error in the viewer, it looks like the shrubs changing
    lighting when the walker crosses the LOD distance.
    """
    g3dir = out.parent / "gate3"
    alt = Path(os.environ.get("PFA_MAIN_ROOT",
                              "/Users/dk/Projects/3d render blender 3rd attempt building")) / "export/out/gate3"
    op = next((d / "instance_order_shrub_lod1.json" for d in (g3dir, alt)
               if (d / "instance_order_shrub_lod1.json").exists()), None)
    glb = out / "env_shrubs.glb"
    if op is None or not glb.exists():
        return None
    order = json.loads(op.read_text())
    if order.get("set") != "shrub_lod1":
        bad.append(f"{op.name} is the {order.get('set')!r} set, not shrub_lod1")
        return None
    if glb.stat().st_size != order.get("glb_bytes"):
        bad.append(f"{op.name} was written against a {order.get('glb_bytes')} B env_shrubs.glb, the file on "
                   f"disk is {glb.stat().st_size} B - re-dump the rows and re-run "
                   f"PFA_ORDER_SET=shrub_lod1 export/gate4_instance_order.py")
        return None
    if not order.get("loc_in_json"):
        bad.append(f"{op.name} is a PFA_INSTANCE_ORDER_HARNESS run: the LOD1 rows would be joined by name")
    doc, _ = glb_json(glb)
    per_mesh, rows_total = {}, 0
    for nd in order["nodes"]:
        i = nd["gltf_node"]
        gi = ((doc["nodes"][i].get("extensions") or {}).get("EXT_mesh_gpu_instancing")
              if isinstance(i, int) and 0 <= i < len(doc.get("nodes", [])) else None)
        if not gi:
            bad.append(f"env_shrubs.glb node {i} carries no EXT_mesh_gpu_instancing but the order file "
                       f"gives it {nd['count']} rows")
            continue
        n = accessor_count(doc, list((gi.get("attributes") or {}).values())[0])
        if n != nd["count"]:
            bad.append(f"env_shrubs.glb node {i} has {n} instance rows, the order file says {nd['count']}")
        rows_total += nd["count"]
        cursor = {}
        for mesh, count, off in nd["segments"]:
            if off != cursor.get(mesh, 0):
                bad.append(f"env_shrubs.glb node {i}: {mesh} segment starts at {off}, the running cursor is "
                           f"at {cursor.get(mesh, 0)}")
            cursor[mesh] = cursor.get(mesh, 0) + count
            per_mesh[mesh] = per_mesh.get(mesh, 0) + count
    for mesh, e in order["meshes"].items():
        if per_mesh.get(mesh) != e["n"]:
            bad.append(f"env_shrubs.glb gives {mesh} {per_mesh.get(mesh)} rows, the order file lists {e['n']}")
    return dict(glb="env_shrubs.glb", rows=rows_total, placements=order["placements"],
                meshes=len(order["meshes"]), nodes=len(order["nodes"]),
                worst_residual_m=order["worst_residual_m"],
                worst_margin_ratio=order["worst_margin_ratio"],
                counts_match=not any("env_shrubs" in b for b in bad),
                shares_irradiance_with="instance_order.json (the LOD2 set) - same instance_irradiance.json")


def trees_lod1_order_check(out, bad):
    """Phase 6c round 3 item 2: `env_trees_lod1.glb` (the walk-up set) against `env_trees.glb`.

    The brief's requirement is that the viewer reuses env_trees.glb's placement rows and its per-placement
    irradiance for the walk-up glb, so the two files have to present the SAME rows in the SAME order.
    `export/trees_far.py` asserts that before the pack, node name by node name and translation by
    translation, against the other set's glTF. What this adds is the only part gltfpack can still break: the
    pack groups placements into `EXT_mesh_gpu_instancing` buffers in its own order and drops the names, so a
    different mesh split or a different merge would re-segment the rows even though the glTF was identical.

    The row TRANSLATIONS themselves are not readable here - `gltfpack -cc` meshopt-encodes every buffer view,
    and decoding it needs the viewer's own loader (web/tools/instance_rows.mjs, which is how Gate 4 recovers
    env.glb's order). What IS readable from the JSON, and is what re-segmentation would move, is the
    structure: the same number of meshes, the same instanced nodes in the same sequence, the same row count
    in each, and the same material on each. All four are compared.
    """
    a_p, b_p = out / "env_trees.glb", out / "env_trees_lod1.glb"
    if not b_p.exists():
        return None                      # extra_glb_check already failed on the missing file
    if not a_p.exists():
        bad.append("env_trees_lod1: env_trees.glb is missing, so the walk-up set's row order cannot be "
                   "checked against the set it must match")
        return None
    ad, _ = glb_json(a_p)
    bd, _ = glb_json(b_p)

    def rows(doc):
        o = []
        for nd in doc.get("nodes", []):
            if "mesh" not in nd:
                continue
            gi = (nd.get("extensions") or {}).get("EXT_mesh_gpu_instancing")
            n = accessor_count(doc, list((gi.get("attributes") or {}).values())[0]) if gi else 1
            me = doc["meshes"][nd["mesh"]]
            mats = [doc["materials"][pr["material"]].get("name")
                    for pr in me.get("primitives", []) if "material" in pr]
            o.append((n, tuple(mats)))
        return o

    ra, rb = rows(ad), rows(bd)
    if len(ra) != len(rb):
        bad.append(f"env_trees_lod1.glb has {len(rb)} instanced nodes, env_trees.glb has {len(ra)} - "
                   f"gltfpack segmented the rows differently and the placement rows cannot be reused")
    else:
        for i, (x, y) in enumerate(zip(ra, rb)):
            if x[0] != y[0]:
                bad.append(f"env_trees_lod1.glb node {i} has {y[0]} instance rows, env_trees.glb has "
                           f"{x[0]} - the per-placement irradiance would land on the wrong tree")
                break
            if x[1] != y[1]:
                bad.append(f"env_trees_lod1.glb node {i} draws material {y[1]}, env_trees.glb draws "
                           f"{x[1]} - the two sets are not in the same mesh order")
                break
    return dict(glb="env_trees_lod1.glb", against="env_trees.glb",
                instanced_nodes=[len(ra), len(rb)],
                rows=[sum(n for n, _ in ra), sum(n for n, _ in rb)],
                meshes=[len(ad.get("meshes", [])), len(bd.get("meshes", []))],
                structure_matches=not any("env_trees_lod1.glb node" in x or
                                          "instanced nodes" in x for x in bad),
                translations="asserted pre-pack in export/trees_far.py `instance_order_check` (node name "
                             "and translation, row by row, against env_trees.gltf); the packed rows are "
                             "meshopt-encoded and only the viewer's loader can decode them")


def extra_glb_check(out, bad, name, report_name, maker):
    """Phase 6c: one of the side glbs - `env_trees` (item A, the far trees' LOD2 meshes) or `env_shrubs`
    (item E, the shrub/reed LOD1 set).

    Neither is one of the four export_set.json classes, so the class loop cannot see them. Each is checked
    against the report its builder wrote in the same Blender run that wrote the glTF: the source meshes and
    their triangle counts, and the placements. The three failures that matter and are invisible in a viewer
    are (1) a glb packed from a different glTF than the report describes, (2) instance rows lost or duplicated
    by `gltfpack -mi` - a tree or shrub in the wrong place or missing - and (3) a leaf material that lost its
    `alphaMode`, which draws every card as a solid rectangle (export/README.md items 29-30).
    """
    glb = out / f"{name}.glb"
    rep_p = out / report_name
    # A missing file is a FAILURE, not "nothing to check". Returning None here meant a deleted, never-built
    # or half-packed env_trees.glb / env_shrubs.glb made verify_glb print PASS - the manifest still names the
    # glb, and the viewer's lazy load is the first thing that finds out. Both are unconditional outputs of
    # this pipeline; if one is genuinely not wanted, remove it from the manifest, not from this check.
    if not glb.exists():
        bad.append(f"{name}: {glb.name} is missing - run its builder, then "
                   f"export/gltf_pack.sh {maker}")
        return None
    if not rep_p.exists():
        bad.append(f"{name}: {glb.name} exists but its report {report_name} does not, so nothing about it "
                   f"can be checked - re-run its builder, then export/gltf_pack.sh {maker}")
        return None
    rep = json.loads(rep_p.read_text())
    for src_name in (f"{name}.gltf", f"{name}_ktx2.gltf"):
        sp = out / src_name
        if sp.exists() and sp.stat().st_mtime > glb.stat().st_mtime + 1.0:
            bad.append(f"{name}: {src_name} is newer than {name}.glb - the glb was packed from a different "
                       f"glTF than this check reads. Re-run export/gltf_pack.sh {maker}.")
    doc, _ = glb_json(glb)
    mesh_tris = []
    for me in doc.get("meshes", []):
        t = 0
        for pr in me.get("primitives", []):
            if "indices" in pr:
                t += accessor_count(doc, pr["indices"]) // 3
            else:
                t += accessor_count(doc, (pr.get("attributes") or {}).get("POSITION")) // 3
        mesh_tris.append(t)
    rows_total, drawn_tris, inst_nodes, plain_nodes = 0, 0, 0, 0
    for nd in doc.get("nodes", []):
        if "mesh" not in nd:
            continue
        gi = (nd.get("extensions") or {}).get("EXT_mesh_gpu_instancing")
        if gi:
            n = accessor_count(doc, list((gi.get("attributes") or {}).values())[0])
            inst_nodes += 1
            rows_total += n
            drawn_tris += n * mesh_tris[nd["mesh"]]
        else:
            plain_nodes += 1
            rows_total += 1
            drawn_tris += mesh_tris[nd["mesh"]]
    # gltfpack splits a multi-primitive mesh into one mesh (and one instanced node) PER PRIMITIVE, and every
    # tree is bark + leaf, so the row count to expect is the pre-pack glTF's nodes weighted by their mesh's
    # primitive count - not the placement count. Read from env_trees.gltf, which the mtime pin above ties to
    # this glb.
    sgp = out / f"{name}.gltf"
    src = json.loads(sgp.read_text()) if sgp.exists() else None
    protos = rep.get("prototypes") or rep.get("meshes")
    want_rows = len(rep["placements"])
    want_meshes = len(protos)
    if src is not None:
        prims = [len(m.get("primitives", [])) for m in src.get("meshes", [])]
        want_rows = sum(prims[n["mesh"]] for n in src.get("nodes", []) if "mesh" in n)
        want_meshes = sum(prims)
    if rows_total != want_rows:
        bad.append(f"{name}.glb draws {rows_total} instances, {name}.gltf has {want_rows} "
                   f"(placements x primitives per mesh)")
    if len(doc.get("meshes", [])) != want_meshes:
        bad.append(f"{name}.glb has {len(doc.get('meshes', []))} meshes, {name}.gltf has "
                   f"{want_meshes} primitives over {len(protos)} source meshes")
    pkey = "prototype" if "prototypes" in rep else "lod2_mesh"
    want_tris = sum(protos[pl[pkey]]["tris"] for pl in rep["placements"])
    # gltfpack welds and re-triangulates, so the count moves a little; more than 1 % means geometry was lost.
    if want_tris and abs(drawn_tris - want_tris) > 0.01 * want_tris:
        bad.append(f"{name}.glb draws {drawn_tris} triangles, the export placed {want_tris} "
                   f"({100.0*(drawn_tris-want_tris)/want_tris:+.1f} %)")
    # the cut-out cards: the effective cutoff, because gltfpack drops `alphaCutoff` when it is the default 0.5
    want_alpha = rep.get("gltf", {}).get("alpha_mode_materials") or {}
    got = {m.get("name"): (m.get("alphaMode"), m.get("alphaCutoff", 0.5)) for m in doc.get("materials", [])}
    for mname, (mode, cut) in want_alpha.items():
        if mname not in got:
            bad.append(f"{name}.glb lost material {mname!r} (gltfpack merged or renamed it): the viewer "
                       f"picks the leaf materials out by name")
            continue
        g_mode, g_cut = got[mname]
        if g_mode != mode or abs(float(g_cut) - float(cut if cut is not None else 0.5)) > 1e-5:
            bad.append(f"{name}.glb {mname}: alphaMode {g_mode} cutoff {g_cut}, the glTF declared "
                       f"{mode} {cut} - a leaf card that ships OPAQUE is a solid rectangle")
    # COLOR_0 (item B's vertex AO), read out of the GLB, not echoed from the report. gltfpack drops vertex
    # colours unless it is given `-kv`, and the report is written by the Blender run BEFORE the pack, so a
    # missing `-kv` would leave the report saying COLOR_0 and the glb shipping none - trees with no occlusion
    # and nothing to see in a diff. Primitives, not meshes: gltfpack splits bark and leaf into separate meshes.
    prim_all = sum(len(m.get("primitives", [])) for m in doc.get("meshes", []))
    prim_c0 = sum(1 for m in doc.get("meshes", []) for pr in m.get("primitives", [])
                  if "COLOR_0" in (pr.get("attributes") or {}))
    want_c0 = bool(rep.get("gltf", {}).get("color0_meshes"))
    if want_c0 and prim_c0 == 0:
        bad.append(f"{name}: {report_name} names {len(rep['gltf']['color0_meshes'])} COLOR_0 meshes but "
                   f"{name}.glb carries COLOR_0 on 0 of {prim_all} primitives - gltfpack dropped the vertex "
                   f"colours. `-kv` is missing from the pack flags (export/gltf_pack.sh {maker}).")
    elif want_c0 and prim_c0 < prim_all:
        bad.append(f"{name}: COLOR_0 on {prim_c0} of {prim_all} primitives in {name}.glb - the vertex AO is "
                   f"attached per MESH, so every primitive of every mesh must carry it")
    elif not want_c0 and prim_c0:
        bad.append(f"{name}.glb carries COLOR_0 on {prim_c0} primitives that {report_name} does not declare")
    return dict(glb=f"{name}.glb", bytes=glb.stat().st_size, meshes=len(doc.get("meshes", [])),
                instanced_nodes=inst_nodes, plain_nodes=plain_nodes, rows=rows_total,
                placements=len(rep["placements"]), rows_expected=want_rows, drawn_tris=drawn_tris, export_tris=want_tris,
                unique_tris=sum(v["tris"] for v in protos.values()),
                alpha_materials={k: list(v) for k, v in sorted(got.items()) if v[0]},
                color0=want_c0, color0_primitives=f"{prim_c0}/{prim_all}",
                color0_range=(rep.get("color0") or {}).get("range"))


def instance_irradiance_check(out, bad):
    """Gate 4: the 1 379 shrub/reed placements' irradiance is addressed BY ROW, so the row count has to match.

    `out/gate3/instance_irradiance.json` (bake) holds one RGB per placement; `out/gate3/instance_order.json`
    (export/gate4_instance_order.py) says which env.glb instance row each one is, joined on the instance
    translation because `gltfpack -mi` drops node names. This asserts the two against env.glb ITSELF: every
    node the order file names is really instanced, its `EXT_mesh_gpu_instancing` accessor count equals the
    node's segment total, and each of the 28 meshes gets exactly as many glb rows as it has placements. An
    off-by-one here does not look like an error in the viewer - it looks like slightly wrong lighting on
    every shrub after the first mismatched row.
    """
    g3dir = out.parent / "gate3"
    alt = Path(os.environ.get("PFA_MAIN_ROOT",
                              "/Users/dk/Projects/3d render blender 3rd attempt building")) / "export/out/gate3"

    def find(name):
        for d in (g3dir, alt):
            if (d / name).exists():
                return d / name
        return None

    ip, op = find("instance_irradiance.json"), find("instance_order.json")
    if ip is None:
        return None                                   # the Gate 4 bake has not landed in this checkout
    irr = json.loads(ip.read_text())
    # The join keys on each placement's own world `loc`. Until the bake writes it the chain CANNOT be run
    # correctly, so a missing or harness order file is reported, not failed; once `loc` is there, both are
    # hard failures (review r5, 3).
    bakeable = all("loc" in p for m in irr.get("meshes", {}).values() for p in m.get("placements", []))
    if op is None:
        msg = ("instance_irradiance.json is present but instance_order.json is not: the per-placement "
               "irradiance has no glb row order (run export/gate4_instance_order.py) and the viewer would "
               "bind the values in the bake's own order, which gltfpack does not preserve")
        if bakeable:
            bad.append(msg)
        else:
            print(f"[verify_glb] note: {msg} - and it cannot be run yet: the placements carry no `loc`")
        return dict(placements=irr.get("placements"), meshes=irr.get("meshes_n"), order_recovered=False,
                    loc_in_irradiance=bakeable)
    order = json.loads(op.read_text())
    glb = out / f"{order.get('glb', 'env.glb')}"
    if not glb.exists():
        # Only the Gate 1 out dir holds env.glb; on any other (gate0) this check has nothing to say and a
        # `bad` would be a false failure of an unrelated pack (review r5, note 8).
        print(f"[verify_glb] note: {glb.name} is not in {out}, skipping the Gate 4 instance-row check")
        return None
    if not order.get("loc_in_json", False):
        msg = ("instance_order.json was produced by the PFA_INSTANCE_ORDER_HARNESS fallback "
               "(loc_in_json: false): the row order comes from env.gltf BY OBJECT NAME, the join the bake "
               "review ruled out. Re-run export/gate4_instance_order.py against an instance_irradiance.json "
               "that carries per-placement `loc`")
        if bakeable:
            bad.append(msg + " - which this one does, so nothing excuses the harness file any more")
        else:
            print(f"[verify_glb] note: {msg}; manifest_v4.py emits no rgb array from it")
    if glb.stat().st_size != order.get("glb_bytes"):
        bad.append(f"instance_order.json was written against a {order.get('glb_bytes')} B {glb.name}, but "
                   f"the file on disk is {glb.stat().st_size} B - re-run web/tools/instance_rows.mjs and "
                   f"export/gate4_instance_order.py, the row order is not the same glb's")
    doc, _ = glb_json(glb)
    per_mesh, rows_total = {}, 0
    for nd in order["nodes"]:
        i = nd["gltf_node"]
        gi = ((doc["nodes"][i].get("extensions") or {}).get("EXT_mesh_gpu_instancing")
              if isinstance(i, int) and 0 <= i < len(doc.get("nodes", [])) else None)
        if not gi:
            bad.append(f"{glb.name} node {i} carries no EXT_mesh_gpu_instancing, but instance_order.json "
                       f"maps {nd['count']} placement rows onto it")
            continue
        n_glb = accessor_count(doc, (gi.get("attributes") or {}).get("TRANSLATION"))
        seg_total = sum(s[1] for s in nd["segments"])
        rows_total += seg_total
        if n_glb != nd["count"] or seg_total != nd["count"]:
            bad.append(f"{glb.name} node {i}: {n_glb} instance rows in the glb, {nd['count']} in "
                       f"instance_order.json, {seg_total} in its segments")
        # [mesh, count, offset]: a mesh can own more than one segment in a node, and the offsets must
        # tile that mesh's array exactly once - a wrong offset silently shifts a run of shrubs.
        cursor = {}
        for m, c, o in nd["segments"]:
            if o != cursor.get(m, 0):
                bad.append(f"{glb.name} node {i}: segment offset {o} for {m} but the running cursor is at "
                           f"{cursor.get(m, 0)} - the per-mesh array would be read out of step")
            cursor[m] = o + c
            per_mesh[m] = per_mesh.get(m, 0) + c
    mism = {m: (c, irr["meshes"].get(m, {}).get("n")) for m, c in per_mesh.items()
            if irr["meshes"].get(m, {}).get("n") != c}
    if mism:
        bad.append(f"{len(mism)} of the {irr['meshes_n']} shrub/reed meshes have a different number of glb "
                   f"instance rows than baked placements (mesh: glb_rows, placements): "
                   f"{dict(list(mism.items())[:4])}")
    absent = sorted(set(irr["meshes"]) - set(per_mesh))
    if absent:
        bad.append(f"{len(absent)} baked shrub/reed meshes have no glb instance rows at all: {absent[:4]}")
    if rows_total != irr["placements"]:
        bad.append(f"{rows_total} glb instance rows mapped, {irr['placements']} placements baked")
    return dict(placements=irr["placements"], rows_in_glb=rows_total, meshes=irr["meshes_n"],
                meshes_matched=len(per_mesh), nodes=len(order["nodes"]),
                merged_nodes=[n["gltf_node"] for n in order["nodes"] if len(n["segments"]) > 1],
                counts_match=not (mism or absent) and rows_total == irr["placements"],
                join=order.get("method", "")[:80], loc_in_json=order.get("loc_in_json"),
                loc_in_irradiance=bakeable,
                worst_residual_m=order.get("worst_residual_m"),
                worst_margin_ratio=order.get("worst_margin_ratio"),
                order_recovered=True)


# --------------------------------------------------------------------------------- 6b Gate 5: the groups
def glb_placed_tris(doc):
    """Triangles DRAWN by a glb: sum(primitive triangles x instance count), the same invariant Gate 1
    checks.  gltfpack merges single-use nodes, so a node or primitive count proves nothing."""
    mesh_tris = []
    for me in doc.get("meshes", []):
        t = 0
        for pr in me.get("primitives", []):
            if "indices" in pr:
                t += accessor_count(doc, pr["indices"]) // 3
            else:
                t += accessor_count(doc, (pr.get("attributes") or {}).get("POSITION")) // 3
        mesh_tris.append(t)
    tris = nodes = placements = 0
    for nd in doc.get("nodes", []):
        if "mesh" not in nd:
            continue
        nodes += 1
        gi = (nd.get("extensions") or {}).get("EXT_mesh_gpu_instancing")
        if gi:
            n = accessor_count(doc, (gi.get("attributes") or {}).get("TRANSLATION"))
            if n == 0:
                n = max((accessor_count(doc, i) for i in (gi.get("attributes") or {}).values()),
                        default=0)
            tris += mesh_tris[nd["mesh"]] * n
            placements += n
        else:
            tris += mesh_tris[nd["mesh"]]
            placements += 1
    return dict(tris=tris, nodes=nodes, placements=placements, meshes=len(mesh_tris))


def _glb_json_chunk(b):
    ln = int.from_bytes(b[12:16], "little")
    return b[20:20 + ln]


def _pub(out, rel):
    """A published path resolves either in THIS worktree's out/gate5 (what it just wrote) or in MAIN's
    out/gate5 (where the other gates live and where sync_main.sh copies to). Both are tried, in that
    order, so the check works before and after the sync."""
    p = Path(out) / rel
    if p.exists():
        return p
    main = Path(os.environ.get("PFA_MAIN_ROOT",
                               "/Users/dk/Projects/3d render blender 3rd attempt building"))
    return main / "export/out/gate5" / rel


def verify_gate5(out_dir, variant="desktop"):
    """Item D: the per-tier groups carry the Gate 3 geometry, once each, under the per-file cap.

    Four assertions, none of which a wrong cut can pass:
      1. every Gate 1 asset appears EXACTLY ONCE across the non-placeholder groups and the whole-file
         classes (a tier-0 placeholder group is allowed to repeat its own assets and must be a SUBSET
         of the tier that replaces it);
      2. the triangles DRAWN per class, summed over its groups, equal `glb.per_class[cls].placed_tris`
         from manifest v4 - which is what "geometry is identical to Gate 3, so the six-station ray test
         is unaffected" means in a file that has been re-packed (the mobile variant is SIMPLIFIED on
         purpose, so there the ratio is reported and only bounded);
      3. every external texture URI a group carries resolves to a file that is published;
      4. no published file is over the per-file cap.
    """
    out = Path(out_dir)
    name = "manifest_mobile.json" if variant == "mobile" else "manifest.json"
    man = json.loads((out / name).read_text())
    # v5 carries every v4 block forward, so the Gate 3 truth is inside this same file: `assets` (the
    # export set's identity) and `glb.per_class_gate3` (what Gate 3 actually drew, per class).
    v4 = dict(assets=man["assets"], glb=dict(per_class=man["glb"]["per_class_gate3"]))
    bad, rep = [], {}
    cap = man["tiers"]["per_file_cap_bytes"]
    groups = man["glb"]["groups"]
    placeholders = [g for g in groups if g.get("placeholder")]
    real = [g for g in groups if not g.get("placeholder")]

    # 1. every asset exactly once
    seen = {}
    for g in real:
        for a in g["assets"]:
            seen.setdefault(a, []).append(g["id"])
    whole = [e for e in man["files"] if e["kind"] == "glb"]
    for e in whole:
        cls = os.path.basename(e["path"]).replace(".glb", "")
        for a, rec in v4["assets"].items():
            c = "ground" if rec.get("kind") == "ground" else \
                "arch" if rec["cls"] == "ARCH" else "orn" if rec["cls"] == "ORN" else "env"
            if c == cls:
                seen.setdefault(a, []).append(cls + ".glb")
    dup = {a: g for a, g in seen.items() if len(g) > 1}
    miss = sorted(set(v4["assets"]) - set(seen))
    if dup:
        bad.append(f"{len(dup)} assets appear in more than one published file, e.g. "
                   f"{list(dup.items())[:3]}")
    if miss:
        bad.append(f"{len(miss)} Gate 1 assets are in no published file, e.g. {miss[:5]}")
    rep["assets_covered"] = len(seen)
    rep["assets_expected"] = len(v4["assets"])

    # a placeholder must be a subset of the tier that replaces it, or it shows something tier 1 removes
    for g in placeholders:
        same_cls = {a for r in real if r["cls"] == g["cls"] for a in r["assets"]}
        extra = sorted(set(g["assets"]) - same_cls)
        if extra:
            bad.append(f"placeholder {g['id']} carries {len(extra)} assets no real group has, e.g. "
                       f"{extra[:3]}")

    # 2. triangles drawn per class
    per_cls = {}
    for g in groups:
        if g.get("placeholder"):
            continue
        doc, _ = glb_json(_pub(out, g["path"]))
        c = glb_placed_tris(doc)
        d = per_cls.setdefault(g["cls"], dict(tris=0, placements=0, groups=0))
        d["tris"] += c["tris"]
        d["placements"] += c["placements"]
        d["groups"] += 1
    for e in whole:
        cls = os.path.basename(e["path"]).replace(".glb", "")
        gp = _pub(out, e["path"])
        if gp.exists():
            doc, _ = glb_json(gp)
            c = glb_placed_tris(doc)
            d = per_cls.setdefault(cls, dict(tris=0, placements=0, groups=0))
            d["tris"] += c["tris"]
            d["placements"] += c["placements"]
            d["groups"] += 1
    for cls, d in sorted(per_cls.items()):
        want = (v4["glb"]["per_class"].get(cls) or {}).get("placed_tris")
        if not want:
            continue
        d["gate3_tris"] = want
        d["ratio"] = round(d["tris"] / want, 4)
        if variant == "mobile":
            lo, hi = (0.3, 0.75) if cls in ("arch", "orn") else (0.99, 1.01)
            if not lo <= d["ratio"] <= hi:
                bad.append(f"{cls}: mobile draws {d['tris']} triangles, ratio {d['ratio']} outside "
                           f"[{lo}, {hi}] of Gate 3's {want}")
        elif abs(d["tris"] - want) / want > 0.005:
            bad.append(f"{cls}: the groups draw {d['tris']} triangles against Gate 3's {want} "
                       f"({100 * (d['tris'] / want - 1):+.3f} %, tolerance 0.5 %)")
    rep["per_class"] = per_cls

    # 2b. the container itself: tiers.py rewrites the JSON chunk of every group after gltfpack, to point
    # the `-tr` URIs at the published layout, so the GLB header and chunk framing are checked byte by
    # byte here - a wrong length is invisible in a tier table and fatal in the browser.
    for g in groups:
        b = _pub(out, g["path"]).read_bytes()
        if b[:4] != b"glTF" or int.from_bytes(b[8:12], "little") != len(b):
            bad.append(f"{g['id']}: GLB header length {int.from_bytes(b[8:12], 'little')} against "
                       f"{len(b)} bytes on disk")
            continue
        off, kinds = 12, []
        while off < len(b):
            ln = int.from_bytes(b[off:off + 4], "little")
            kinds.append(b[off + 4:off + 8])
            if ln % 4 or off + 8 + ln > len(b):
                bad.append(f"{g['id']}: chunk at {off} has length {ln}, unaligned or past the end")
                break
            off += 8 + ln
        else:
            if kinds[:1] != [b"JSON"]:
                bad.append(f"{g['id']}: first chunk is {kinds[:1]}, not JSON")
            doc = json.loads(_glb_json_chunk(b))
            # No image may ride in a bufferView: an embedded texture reaches three.js as a blob with
            # no name, so no tier can pair it with its full-resolution twin and the half-resolution
            # copy would stay in place for ever (viewer measurement, 2026-09-18).
            emb = [i for i, im in enumerate(doc.get("images", []))
                   if im.get("bufferView") is not None or not im.get("uri")]
            if emb:
                bad.append(f"{g['id']}: {len(emb)} of {len(doc.get('images', []))} images are embedded "
                           f"(bufferView) or have no uri - `-tr` lost, nothing can upgrade them")

    # 3. every external texture a group refers to is published, and resolves
    published = {os.path.normpath(e["path"]) for e in man["files"]}
    missing_tex = []
    lo_dir = (man["tiers"].get("lowres") or {}).get("dir", "tex_lo")
    lo_of = {}
    for e in man["files"]:
        if e.get("key") and e["path"].startswith(lo_dir + "/"):
            lo_of[e["key"]] = e["path"]
    for g in groups:
        for t in g["textures"]:
            key = os.path.basename(t)[:-len(".ktx2")] if t.endswith(".ktx2") else None
            # published as itself, or as the half-resolution twin the viewer redirects to (the mobile
            # set publishes only the twin)
            if os.path.normpath(t) not in published and key not in lo_of:
                missing_tex.append((g["id"], t))
            elif os.path.normpath(t) in published and not _pub(out, t).exists():
                missing_tex.append((g["id"], t + " (not on disk)"))
    if missing_tex:
        bad.append(f"{len(missing_tex)} group textures are not published or not on disk, e.g. "
                   f"{missing_tex[:3]}")
    rep["group_textures"] = sum(len(g["textures"]) for g in groups)

    # 5. review r5 finding 3: THE FAR-TREE COUNTS MUST AGREE ACROSS THE THREE PLACES THAT STATE THEM.
    # `tree_rule.far_billboards` (the export set), `trees.far_mesh.placements` / `walkup_mesh.count` (what
    # the viewer joins against) and the per-placement lighting rows are written by different steps, and in
    # the 8d belt round manifest_v4 ran before trees_far.py, so the manifest advertised 127 against a
    # 166-instance glb - the viewer's join would have failed and dropped the whole far-tree mesh layer.
    # Every pair but that one was already checked; this closes the triangle.
    tr = (man.get("assets_meta") or {}).get("tree_rule") or man.get("tree_rule")
    want_far = (tr or {}).get("far_billboards")
    if want_far is None and man.get("tree_far") is not None:
        want_far = len(man["tree_far"])
    trees = man.get("trees") or {}
    def _n(v):
        # a placement block is either the list itself or `{count, same_as}` (the walk-up set states it
        # by reference so the two can never disagree)
        if isinstance(v, list):
            return len(v)
        if isinstance(v, dict):
            return v.get("count")
        return None
    far_mesh = trees.get("far_mesh") or {}
    counts = dict(tree_far_rows=(len(man["tree_far"]) if man.get("tree_far") is not None else None),
                  far_billboards=want_far,
                  far_mesh_placements=_n(far_mesh.get("placements")),
                  walkup_count=_n((trees.get("walkup_mesh") or {}).get("placements")),
                  lighting_rows=_n((((far_mesh.get("lighting") or {}).get("mesh")) or {}).get("placements")))
    rep["far_tree_counts"] = counts
    seen_counts = {k: v for k, v in counts.items() if v}
    if len(set(seen_counts.values())) > 1:
        bad.append(f"the far-tree counts disagree: {seen_counts} - trees_far.py (both sets) and "
                   f"manifest_v4 were not run against the same export set")

    # 4. the per-file cap
    over = [(e["path"], e["bytes"]) for e in man["files"] if (e["bytes"] or 0) > cap]
    if over:
        bad.append(f"{len(over)} published files over the {cap} B cap: {over[:3]}")
    rep["files"] = len(man["files"])
    rep["tier_bytes"] = man["tiers"]["bytes"]

    print(f"[verify5:{variant}] assets {rep['assets_covered']}/{rep['assets_expected']}, "
          f"{rep['files']} published files, tiers {rep['tier_bytes']}")
    for cls, d in sorted(per_cls.items()):
        print(f"[verify5:{variant}] {cls}: {d['groups']} file(s), {d['placements']} placements, "
              f"{d['tris']} tris" + (f" = {d['ratio']}x Gate 3" if "ratio" in d else ""))
    for b in bad:
        print(f"[verify5:{variant}] FAIL {b}")
    rep["fail"] = bad
    (out / f"verify_gate5_{variant}.json").write_text(json.dumps(rep, indent=1))
    print(f"[verify5:{variant}] {'PASS' if not bad else 'FAIL'} -> "
          f"{out / f'verify_gate5_{variant}.json'}")
    return 1 if bad else 0


def main(out_dir):
    out = Path(out_dir)
    setjson = json.loads((out / "export_set.json").read_text())
    per_cls = {}
    for name, a in setjson["assets"].items():
        cls = "ground" if a.get("kind") == "ground" else \
              "arch" if a["cls"] == "ARCH" else "orn" if a["cls"] == "ORN" else "env"
        per_cls.setdefault(cls, []).append(name)
    near_expected = {}
    for name, a in setjson["assets"].items():
        loc = a.get("location_blender")
        if loc and sum(v * v for v in loc) ** 0.5 < 1.0:
            cls = "ground" if a.get("kind") == "ground" else \
                  "arch" if a["cls"] == "ARCH" else "orn" if a["cls"] == "ORN" else "env"
            near_expected[cls] = near_expected.get(cls, 0) + 1

    want_tris = {}
    for name, a in setjson["assets"].items():
        cls = "ground" if a.get("kind") == "ground" else \
              "arch" if a["cls"] == "ARCH" else "orn" if a["cls"] == "ORN" else "env"
        want_tris[cls] = want_tris.get(cls, 0) + a["tris"]

    # how many of the 988 per-instance lightmap slots each class owns (manifest `orn_slots`, the bake's).
    # A slot is addressed by world centre, so it needs its own mesh or instance in the packed glb.
    slot_objects = {}
    man_p = out / "manifest.json"
    if man_p.exists():
        man = json.loads(man_p.read_text())
        cls_of_obj = {name: ("ground" if a.get("kind") == "ground" else
                             "arch" if a["cls"] == "ARCH" else "orn" if a["cls"] == "ORN" else "env")
                      for name, a in setjson["assets"].items()}
        for rows_ in (man.get("orn_slots") or {}).values():
            for s in rows_:
                c = cls_of_obj.get(s.get("object"))
                if c:
                    slot_objects[c] = slot_objects.get(c, 0) + 1

    gl = json.loads((out / "gltf_gate1.json").read_text()) if (out / "gltf_gate1.json").exists() else {}
    flags = {}
    fp = out / "gltfpack_flags.txt"
    if fp.exists():
        for line in fp.read_text().split("\n"):
            if line.strip():
                parts = line.split()
                flags[parts[0]] = " ".join(parts[1:])

    rows, bad = {}, []
    for cls in ("arch", "orn", "env", "ground"):
        p = out / f"{cls}.glb"
        if not p.exists():
            continue
        doc, _ = glb_json(p)
        # Review r3 finding 1: every value below is read out of `<cls>.gltf` and compared with `<cls>.glb`,
        # so a glb older than the glTF it is checked against makes the PASS describe a file that was never
        # packed. Counts and material NAME SETS can match across a real change (a re-laid UV2, a different
        # primitive -> material assignment, a re-copied material) because neither is compared value by value.
        # mtime is the cheap pin: the pack writes the glb after reading both glTFs, so a newer source means
        # the glb is stale. 1 s of slack for filesystem granularity.
        for src_name in (f"{cls}.gltf", f"{cls}_ktx2.gltf"):
            sp = out / src_name
            if sp.exists() and sp.stat().st_mtime > p.stat().st_mtime + 1.0:
                bad.append(f"{cls}: {src_name} is newer than {cls}.glb "
                           f"({time.strftime('%H:%M:%S', time.localtime(sp.stat().st_mtime))} vs "
                           f"{time.strftime('%H:%M:%S', time.localtime(p.stat().st_mtime))}) - the glb was "
                           f"packed from a different glTF than the one this check reads. Re-run "
                           f"export/gltf_pack.sh --gate1.")
        mesh_tris = []
        for me in doc.get("meshes", []):
            t = 0
            for pr in me.get("primitives", []):
                if "indices" in pr:
                    t += accessor_count(doc, pr["indices"]) // 3
                else:
                    t += accessor_count(doc, (pr.get("attributes") or {}).get("POSITION")) // 3
            mesh_tris.append(t)
        plain = inst = inst_nodes = origin_inst = 0
        tris = 0
        for nd in doc.get("nodes", []):
            if "mesh" not in nd:
                continue
            mt = mesh_tris[nd["mesh"]]
            gi = (nd.get("extensions") or {}).get("EXT_mesh_gpu_instancing")
            if gi:
                n = accessor_count(doc, (gi.get("attributes") or {}).get("TRANSLATION"))
                if n == 0:
                    n = max((accessor_count(doc, i) for i in (gi.get("attributes") or {}).values()), default=0)
                inst += n
                inst_nodes += 1
                tris += mt * n
            else:
                plain += 1
                tris += mt
                # A missing node translation does NOT mean the geometry is at the origin: with -vpf gltfpack
                # writes float positions and drops the translation entirely, and the merged backdrop / ground
                # groups carry their world position inside the vertices. Use the POSITION accessor's own
                # min/max (gltfpack always writes them) plus whatever transform the node has.
                t = nd.get("translation") or [0.0, 0.0, 0.0]
                if nd.get("matrix"):
                    t = nd["matrix"][12:15]
                ctr = mesh_centre(doc, nd["mesh"])
                if ctr is not None:
                    w = [t[i] + ctr[i] for i in range(3)]
                    if sum(v * v for v in w) ** 0.5 < 1.0:
                        origin_inst += 1
        # gltfpack merges materials whose factors match unless -km is given, and a merged-away name is a
        # Gate 2 texture set that matches nothing. Assert the names for any class packed with -km; for the
        # others report the loss without failing (they are frozen byte-identical this round).
        want_mats = set((gl.get("classes", {}).get(cls) or {}).get("materials_expected") or [])
        have_mats = {m.get("name") for m in doc.get("materials", []) if m.get("name")}
        missing = sorted(want_mats - have_mats)
        strict = "-km" in (flags.get(cls) or "")
        # the slot-merge guard (gltf_gate1.py) deliberately gives a colliding mesh its own copy of the
        # material under the SAME NAME, so a class can hold more materials than names. That is the only
        # legitimate source of a duplicate name, and it is checked against the split list below.
        split = (gl.get("classes", {}).get(cls) or {}).get("merge_split_meshes") or []
        dup_names = len(doc.get("materials", [])) - len(have_mats)
        rows[cls] = dict(gltfpack_flags=flags.get(cls), materials_expected=len(want_mats),
                         materials_in_glb=len(doc.get("materials", [])),
                         materials_named_in_glb=len(have_mats), materials_missing=len(missing),
                         materials_missing_names=missing[:12], material_names_enforced=strict,
                         merge_split_meshes=split, duplicate_material_names=dup_names,
                         tris_drawn=tris, tris_expected=want_tris.get(cls, 0),
                         placements_in_glb=plain + inst, objects_in_set=len(per_cls.get(cls, [])),
                         plain_nodes=plain, instanced_nodes=inst_nodes, instanced_placements=inst,
                         plain_nodes_with_geometry_at_origin=origin_inst, expected_at_origin=near_expected.get(cls, 0))
        # gltfpack drops degenerate triangles while it optimises, so the match is within a tolerance, not
        # exact: measured 0.19 % on arch and 0.16 % on orn, 0.00 % on env and ground. A DROPPED PLACEMENT is
        # orders of magnitude bigger than that (one stacked shrub group is 8.8 % of ENV).
        if missing and strict:
            bad.append(f"{cls}: {len(missing)} material names in the export set are absent from the packed "
                       f"glb although it was packed with -km: {missing[:8]}")
        elif missing:
            print(f"[verify_glb] note {cls}: {len(missing)} material names merged away by gltfpack "
                  f"(no -km on this class): {missing[:6]}")
        # Gate 3: the two hand-off attributes have to SURVIVE the pack. gltfpack strips every attribute no
        # material references, and neither UV2 nor the near-tree irradiance is referenced by a glb material -
        # the lightmap textures are separate KTX2 the viewer attaches from the manifest. Before Gate 3,
        # arch.gltf carried TEXCOORD_1 on all 29 meshes and arch.glb carried none of it.
        src_p = out / f"{cls}.gltf"
        keeps_attrs = "-kv" in (flags.get(cls) or "")
        if src_p.exists():
            src = json.loads(src_p.read_text())
            for attr in ("TEXCOORD_1", "COLOR_0"):
                want_a, have_a = attr_tris(src, attr), attr_tris(doc, attr)
                rows[cls][f"tris_with_{attr}"] = have_a
                rows[cls][f"tris_with_{attr}_in_gltf"] = want_a
                if not want_a:
                    continue
                if not keeps_attrs:
                    print(f"[verify_glb] note {cls}: {attr} on {want_a} triangles in {cls}.gltf, {have_a} in "
                          f"the glb (packed without -kv, so gltfpack strips what no material references)")
                elif abs(have_a - want_a) / want_a > 0.01:
                    bad.append(f"{cls}: {attr} reaches {have_a} triangles in the packed glb but {want_a} in "
                               f"{cls}.gltf - the pack dropped the attribute the Gate 3 hand-off needs")
        want = want_tris.get(cls, 0)
        rows[cls]["tris_delta"] = tris - want
        rows[cls]["tris_delta_pct"] = round(100.0 * (tris - want) / max(want, 1), 3)
        if want and abs(tris - want) / want > 0.01:
            bad.append(f"{cls}: {tris} triangles drawn by the glb, {want} placed in export_set.json "
                       f"({100.0 * (tris - want) / want:+.2f} %, tolerance 1 %)")
        if origin_inst > max(1, near_expected.get(cls, 0)):
            bad.append(f"{cls}: {origin_inst} un-instanced mesh nodes have their GEOMETRY within 1 m of "
                       f"the world origin ({near_expected.get(cls, 0)} expected)")
        if dup_names and not split:
            bad.append(f"{cls}: {dup_names} materials share a name but no mesh was split for the slot-merge "
                       f"guard - gltfpack merged names away or the export wrote a duplicate by accident")
        # Review finding 3: the guard has to hold in BOTH directions. The split only works because `-km`
        # (keep named materials, so equal-named materials are never merged) is on arch and env; orn and
        # ground are packed `-cc -mi -kv` with no `-km`, so a split on either would be silently undone and
        # the merged mesh would take one lightmap slot for two objects again. Neither is split today
        # (gltf_gate1.json merge_split: arch 2 meshes, orn/env/ground none), and this makes that a rule
        # rather than a coincidence: a split class must carry -km AND show its duplicate names in the glb.
        if split and not strict:
            bad.append(f"{cls}: {len(split)} mesh(es) were split for the slot-merge guard ({split[:4]}) but "
                       f"the class is packed without -km ({flags.get(cls)}) - gltfpack merges the same-named "
                       f"material copies back and the split does nothing")
        # A glTF material with no `alphaMode` is OPAQUE by spec, so a cut-out card draws as a solid
        # rectangle - which is exactly how every leaf card shipped at cam02 before gltf_gate1.py started
        # writing the mode. gltf_gate1.json records, per class, which materials carry an alpha-bearing
        # baseColorTexture and what mode they were given; assert the packed glb still says so. gltfpack does
        # not drop alphaMode, but it DOES merge materials without -km, and a merged-away card material is the
        # same defect wearing a different hat.
        want_alpha = (gl.get("classes", {}).get(cls) or {}).get("alpha_mask_materials") or {}
        have_mode = {m.get("name"): (m.get("alphaMode"), m.get("alphaCutoff"))
                     for m in doc.get("materials", []) if m.get("name")}
        # glTF's default alphaCutoff is 0.5, so gltfpack legitimately DROPS the field when it equals 0.5 -
        # the effective value is still 0.5. Compare the effective one, or a non-default cutoff silently
        # falling back to 0.5 would read as a pass.
        wrong = []
        for n, w in want_alpha.items():
            mode, cut = have_mode.get(n) or (None, None)
            eff = 0.5 if cut is None else float(cut)
            if mode not in ("MASK", "BLEND"):
                wrong.append((n, mode, "no alphaMode"))
            elif mode == "MASK" and abs(eff - float(w["cutoff"])) > 1e-6:
                wrong.append((n, mode, f"effective cutoff {eff}, wanted {w['cutoff']}"))
        rows[cls]["alpha_cutout_materials"] = len(want_alpha)
        rows[cls]["alpha_cutout_cutoffs"] = sorted({v["cutoff"] for v in want_alpha.values()})
        if wrong:
            bad.append(f"{cls}: {len(wrong)} material(s) with an alpha-carrying baseColorTexture do not "
                       f"cut out correctly in the packed glb - without a mode glTF makes them OPAQUE and "
                       f"every card draws as a solid rectangle: {wrong[:4]}")
        if split and dup_names < len(split):
            bad.append(f"{cls}: {len(split)} mesh(es) were split for the slot-merge guard but the glb holds "
                       f"only {dup_names} duplicate material name(s) - gltfpack merged the copies back")
        # Every per-instance lightmap slot needs a MESH OF ITS OWN in the glb, or the viewer cannot address
        # it: it matches a drawn mesh (or instance) by world centre against `orn_slots`. Viewer round 13
        # found 114 of the 988 slots unreachable because gltfpack had merged the colonnade colbase
        # plinth/torus pairs. The class's placements must therefore cover its share of the slot table.
        slots_here = slot_objects.get(cls, 0)
        rows[cls]["slot_objects_in_manifest"] = slots_here
        if slots_here and plain + inst < slots_here:
            bad.append(f"{cls}: {plain + inst} placements in the glb for {slots_here} per-instance lightmap "
                       f"slots in orn_slots - gltfpack merged {slots_here - (plain + inst)} slot mesh(es) "
                       f"away and the viewer cannot address them")
    # ------------------------------------------------------------ Gate 3 hand-off, per mesh
    # 1. the seven re-laid meshes: their TEXCOORD_1 is the Gate 3 layout, not the Gate 1 one, and the island
    #    area it packs is reported. The relay threshold is 0.15 of the square; three of the seven still land
    #    below it after the re-lay (the bake measured the same and baked against it), so that is REPORTED, not
    #    asserted - what is asserted is that the layer changed and that it packs more than Gate 1's.
    # 2. the near-tree meshes carry COLOR_0 (the vertex irradiance), in the class that owns them.
    g3 = dict(uv2=(gl.get("gate3_uv2") or {}).get("meshes") or {},
              color0=(gl.get("gate3_color0") or {}).get("meshes") or {})
    low = []
    for mn, v in g3["uv2"].items():
        if v.get("max_uv_delta", 0) <= 1e-5:
            bad.append(f"{mn}: TEXCOORD_1 is identical to the Gate 1 layer (max delta {v.get('max_uv_delta')})")
        if v.get("coverage_gate3", 0) <= v.get("coverage_gate1", 0):
            bad.append(f"{mn}: the re-laid UV2 packs {v.get('coverage_gate3')} against Gate 1's "
                       f"{v.get('coverage_gate1')}")
        if v.get("coverage_gate3", 0) < 0.15:
            low.append((mn, v.get("coverage_gate3")))
    # 3. the lead's 2026-09-16 decision on ORN: orn.glb carries TEXCOORD_1 for the slot-atlas lightmap on all
    #    33 prototype meshes and NO COLOR_0 - the `cavity` attribute is already inside the Gate 2 albedo bake,
    #    and standard glTF would multiply it into base colour a second time.
    for cls in ("arch", "orn", "env", "ground"):
        r = rows.get(cls)
        if r is None:
            continue
        n_uv2 = len((gl.get("classes", {}).get(cls) or {}).get("texcoord1_meshes") or [])
        if cls == "orn":
            if n_uv2 != 33:
                bad.append(f"orn.gltf carries TEXCOORD_1 on {n_uv2} meshes, not the 33 ORN prototypes")
            if not r.get("tris_with_TEXCOORD_1"):
                bad.append("orn.glb carries no TEXCOORD_1: the ORN slot-atlas lightmap has no UV set")
        extra_col = sorted(set((gl.get("classes", {}).get(cls) or {}).get("color0_meshes") or [])
                           - set((gl.get("gate3_color0") or {}).get("meshes") or {}))
        if extra_col:
            bad.append(f"{cls}: COLOR_0 was exported for {len(extra_col)} meshes that are not the near-tree "
                       f"irradiance ({extra_col[:4]}); three.js multiplies COLOR_0 into base colour and the "
                       f"Gate 2 albedo bake already contains those attributes")
    cls_of_col = {m: cls for cls, r in rows.items() for m in
                  ((gl.get("classes", {}).get(cls) or {}).get("color0_meshes") or [])}
    missing_col = sorted(m for m in g3["color0"] if m not in cls_of_col)
    if g3["color0"] and missing_col:
        bad.append(f"{len(missing_col)} near-tree meshes have the irradiance attribute but no glTF wrote "
                   f"their COLOR_0: {missing_col[:6]}")
    # ------------------------------------------------------------ Gate 4: the per-placement irradiance
    r4 = instance_irradiance_check(out, bad)
    if r4 is not None:
        rows["gate4_instance_irradiance"] = r4
    # ------------------------------------------------------------ Phase 6c: the far trees' LOD2 meshes
    rt = extra_glb_check(out, bad, "env_trees", "trees_far.json", "--trees")
    if rt is not None:
        rows["trees_far"] = rt
    rw = extra_glb_check(out, bad, "env_trees_lod1", "trees_far_lod1.json", "--trees-lod1")
    if rw:
        rows["trees_walkup"] = rw
    rwo = trees_lod1_order_check(out, bad)
    if rwo:
        rows["trees_walkup_order"] = rwo
    rs = extra_glb_check(out, bad, "env_shrubs", "shrub_lod1.json", "--shrubs")
    if rs is not None:
        rows["shrub_lod1"] = rs
    ro = shrub_lod1_order_check(out, bad)
    if ro is not None:
        rows["shrub_lod1_order"] = ro
    rows["gate3"] = dict(
        uv2_meshes=len(g3["uv2"]),
        uv2_coverage={m: [v.get("coverage_gate1"), v.get("coverage_gate3")] for m, v in g3["uv2"].items()},
        uv2_below_threshold=low, uv2_threshold=0.15,
        color0_meshes=len(g3["color0"]), color0_classes=sorted(set(cls_of_col.values())),
        color0_encoding={m: (v.get("encode"), v.get("range")) for m, v in list(g3["color0"].items())[:1]})
    if low:
        print(f"[verify_glb] note: {len(low)} of {len(g3['uv2'])} re-laid meshes still pack under the 0.15 "
              f"relay threshold (the bake measured the same and baked against this layout): {low}")
    print("[verify_glb] " + json.dumps(rows))
    (out / "verify_glb.json").write_text(json.dumps(dict(classes=rows, failures=bad), indent=1) + "\n")
    if bad:
        for b in bad:
            print("[verify_glb] FAIL " + b, file=sys.stderr)
        return 1
    print("[verify_glb] PASS: every placed triangle in export_set.json is drawn by the glb")
    return 0


if __name__ == "__main__":
    if "--gate5" in sys.argv:
        args = [a for a in sys.argv[1:] if not a.startswith("--")]
        d = args[0] if args else str(ROOT / "export" / "out" / "gate5")
        rc = 0
        for v in ("desktop", "mobile"):
            if Path(d, "manifest_mobile.json" if v == "mobile" else "manifest.json").exists():
                rc |= verify_gate5(d, v)
        sys.exit(rc)
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else ROOT / "export" / "out" / "gate1"))
