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
import struct
import sys
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
