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
    if not glb.exists() or not rep_p.exists():
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
    return dict(glb=f"{name}.glb", bytes=glb.stat().st_size, meshes=len(doc.get("meshes", [])),
                instanced_nodes=inst_nodes, plain_nodes=plain_nodes, rows=rows_total,
                placements=len(rep["placements"]), rows_expected=want_rows, drawn_tris=drawn_tris, export_tris=want_tris,
                unique_tris=sum(v["tris"] for v in protos.values()),
                alpha_materials={k: list(v) for k, v in sorted(got.items()) if v[0]},
                color0=bool(rep.get("gltf", {}).get("color0_meshes")))


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
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else ROOT / "export" / "out" / "gate1"))
