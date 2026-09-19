"""8a gate check: the shrub prototypes' UNIQUE triangle counts in master_delivery.blend.

The 8a decision (docs/decisions.md 2026-09-19) puts the clumping + densification on LOD2: unique
LOD2 3 920 -> 6 948 and unique LOD1 17 094 -> 31 268.  The ENV re-export must not start unless the
rebuilt master_delivery.blend actually carries those meshes.  CPU only, read-only, no render:

    scripts/blender_run.sh 600 -- --background master_delivery.blend \
        --python export/p8a_shrub_check.py -- --json <out.json>

Unique = distinct mesh datablocks, one count per datablock, exactly as gate1_set.py budgets them
(`shrub_by_mesh` keyed on `ob.data.name`, the LOD2 sibling looked up by name).
"""
import json
import os
import sys

import bpy

EXPECT = {"LOD1": 31268, "LOD2": 6948}


def tris(me):
    return sum(len(p.vertices) - 2 for p in me.polygons)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out_path = argv[argv.index("--json") + 1] if "--json" in argv else None

    # Counted by the MESH datablock's own LOD suffix, not the object's.  Three `_LOD1` shrub objects
    # carry a `_LOD2` mesh (maho2, pitto5, reed1 - the same 3 of 1 379 placements export/shrub_lod1.py
    # already skips, "25 of the 28 meshes"), so keying on the object's name counts those LOD2 meshes
    # a second time in the LOD1 total and makes it read 736 triangles high.
    per_lod = {}
    for ob in bpy.data.objects:
        if ob.type != "MESH" or not ob.name.startswith("ENV_shrub"):
            continue
        for lod in ("LOD0", "LOD1", "LOD2"):
            if ob.data.name.endswith("_" + lod):
                per_lod.setdefault(lod, {}).setdefault(ob.data.name, tris(ob.data))
            if ob.name.endswith("_" + lod):
                per_lod[lod + "_objects"] = per_lod.get(lod + "_objects", 0) + 1

    rep = {"source": bpy.data.filepath, "expect": EXPECT, "lods": {}}
    for lod in ("LOD0", "LOD1", "LOD2"):
        meshes = per_lod.get(lod, {})
        rep["lods"][lod] = dict(unique_meshes=len(meshes), unique_tris=sum(meshes.values()),
                                objects=per_lod.get(lod + "_objects", 0))
    ok = True
    for lod, want in EXPECT.items():
        got = rep["lods"][lod]["unique_tris"]
        hit = got == want
        ok &= hit
        rep["lods"][lod]["expected"] = want
        rep["lods"][lod]["match"] = hit
        print(f"[p8a-check] {lod}: {rep['lods'][lod]['unique_meshes']} unique mesh(es), "
              f"{got} unique tris over {rep['lods'][lod]['objects']} object(s) "
              f"- expected {want} -> {'OK' if hit else 'MISMATCH'}", flush=True)
    print(f"[p8a-check] LOD0: {rep['lods']['LOD0']['unique_meshes']} unique mesh(es), "
          f"{rep['lods']['LOD0']['unique_tris']} unique tris (no expectation)", flush=True)
    # The ENV builder's own table (renders/logs/p8a_stats_lod2.log) totals "25 sources", not the 28
    # LOD1 mesh datablocks in the file, so the two numbers can differ without either being wrong.
    # Pair every LOD1 mesh with the LOD2 mesh its OBJECT's sibling uses, and print the per-prototype
    # table so a mismatch on the total can be attributed to a named prototype.
    pairs = {}
    for ob in bpy.data.objects:
        if ob.type != "MESH" or not ob.name.endswith("_LOD1") or not ob.name.startswith("ENV_shrub"):
            continue
        sib = bpy.data.objects.get(ob.name.replace("_LOD1", "_LOD2"))
        key = ob.data.name
        if key in pairs:
            continue
        pairs[key] = dict(lod1_tris=tris(ob.data),
                          lod2_mesh=sib.data.name if sib else None,
                          lod2_tris=tris(sib.data) if sib else None,
                          example_object=ob.name)
    rep["lod1_by_mesh"] = pairs
    by_lod2 = {}
    for k, v in pairs.items():
        by_lod2.setdefault(v["lod2_mesh"], []).append(k)
    rep["distinct_lod2_meshes_under_lod1"] = len(by_lod2)
    print(f"[p8a-check] {len(pairs)} LOD1 mesh datablocks over "
          f"{len(by_lod2)} distinct LOD2 meshes", flush=True)
    for k in sorted(pairs):
        v = pairs[k]
        print(f"[p8a-check]   {k:44s} LOD1 {v['lod1_tris']:7d}  "
              f"LOD2 {str(v['lod2_tris']):>7s}  ({v['lod2_mesh']})", flush=True)
    rep["pass"] = bool(ok)
    print(f"[p8a-check] {'PASS' if ok else 'FAIL'}", flush=True)
    if out_path:
        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
        with open(out_path, "w") as f:
            json.dump(rep, f, indent=1)
        print(f"[p8a-check] wrote {out_path}", flush=True)


main()
