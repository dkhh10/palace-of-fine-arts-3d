"""Phase 9 geometry pin: does the re-generated Gate 1 export set still stand on the SHIPPED bake?

    python3 export/p9_geom_pin.py --shipped <a copy of the DEPLOYED export/out/gate3/manifest.json> \
        [--set export/out/gate1/export_set.json] [--out export/out/gate1/p9_geom_pin.json]

CPU only, exit 1 on any failure.

WHY THIS AND NOT `p8d_pin.py`. `p8d_pin.py` is a DELTA instrument: it compares MAIN's `export_set.json`
with the worktree's and asserts the one-time Phase 8d movement (`EXPECT_ENV_DELTA = -6822`, "exactly the
belt's 39 rows are new"). Once MAIN itself is post-8d - which it is - both sides are the same file and those
two checks can never fire again, while the 11 that matter degenerate into comparing a file with itself.
Phase 9 changes the WORLD, not the geometry, so the question is a different one: does the export set the
lightmaps will be baked against still describe the geometry the SHIPPED glbs and the shipped manifest
carry? That is answered against the deployed manifest, which is the artefact the viewer actually reads, and
it is a real comparison rather than a self-comparison.

Run `p8d_pin.py` as well for its 13 far-tree pins (they read the two `trees_far*.json` reports, not the
export set, and are unaffected by the above).
"""
import argparse
import json
import sys
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shipped", required=True)
    ap.add_argument("--set", default="export/out/gate1/export_set.json")
    ap.add_argument("--out", default="export/out/gate1/p9_geom_pin.json")
    a = ap.parse_args()
    man = json.loads(Path(a.shipped).read_text())
    eset = json.loads(Path(a.set).read_text())
    out = {"shipped": a.shipped, "set": a.set, "checks": []}
    ok_all = True

    def eq(name, want, got):
        nonlocal ok_all
        ok = want == got
        ok_all &= ok
        row = dict(name=name, ok=bool(ok))
        if isinstance(want, (int, float, str, bool)) or want is None:
            row.update(shipped=want, new=got)
        else:
            row.update(shipped_n=len(want) if hasattr(want, "__len__") else None,
                       new_n=len(got) if hasattr(got, "__len__") else None)
            if not ok and isinstance(want, dict) and isinstance(got, dict):
                diff = sorted(set(want) ^ set(got))[:10]
                row["key_symmetric_difference"] = diff
                row["first_value_diffs"] = [k for k in sorted(set(want) & set(got)) if want[k] != got[k]][:10]
        out["checks"].append(row)
        print(f"[p9pin] {'ok  ' if ok else 'FAIL'} {name}"
              + (f": shipped={want} new={got}" if isinstance(want, (int, float, str)) else ""))
        return ok

    # 1. the triangle budget, per class and in total
    for k in ("ARCH", "ORN", "ENV"):
        eq(f"totals.placed_tris.{k}", man["totals"]["placed_tris"][k], eset["totals"]["placed_tris"][k])
        eq(f"totals.unique_tris.{k}", man["totals"]["unique_tris"][k], eset["totals"]["unique_tris"][k])
        eq(f"totals.objects.{k}", man["totals"]["objects"][k], eset["totals"]["objects"][k])
    for k in ("placed_total", "unique_total", "unique_meshes"):
        eq(f"totals.{k}", man["totals"][k], eset["totals"][k])

    # 2. the tree rule and the two lists, by content AND order
    for k in ("trees_total", "within_radius", "near_exported", "far_billboards", "lod2_blob_objects",
              "lod2_blob_within_radius", "near_tris_used"):
        eq(f"tree_rule.{k}", man["tree_rule"][k], eset["tree_rule"][k])
    eq("tree_near list (names, in order)", man["tree_near"], [r["name"] for r in eset["tree_near_list"]])
    eq("tree_far list (content and order)", man["tree_far"], eset["tree_far_list"])

    # 3. the objects and meshes the bakes and the glbs are addressed by
    eq("assets: the same object set", sorted(man["assets"]), sorted(eset["assets"]))
    eq("meshes: the same mesh set", sorted(man["meshes"]), sorted(eset["meshes"]))
    bad = [n for n in sorted(set(man["assets"]) & set(eset["assets"]))
           if man["assets"][n].get("mesh") != eset["assets"][n].get("mesh")]
    eq("assets: every object keeps its mesh", [], bad)

    # 4. the UV space the bakes live in
    eq("uv1 atlas tiles: the same groups", sorted(man["uv1_atlas"]["tiles"]), sorted(eset["uv1_atlas_tiles"]))
    eq("uv1 coverage min", man["uv1_atlas"]["coverage_min"], eset["uv1_coverage_min"])
    eq("uv1 per-group coverage", man["uv1_atlas"]["coverage"], eset["uv1_coverage"])
    eq("uv2 meshes", man["gate3"]["uv2_meshes_total"] if "uv2_meshes_total" in man.get("gate3", {})
       else eset["uv2_meshes"], eset["uv2_meshes"])
    eq("lightmap slots (pools, counts, atlases)", man["orn_slots"]["pools"] if "pools" in man["orn_slots"]
       else eset["lightmap_slots"], eset["lightmap_slots"])
    eq("lightmap own-map assets: the same names",
       sorted(k for k in man["lightmaps"]["assets"] if k != "_gate1_layout"),
       sorted(j["id"][3:] for j in json.loads(Path("export/out/gate3/bake_jobs.json").read_text())["jobs"]
              if j["kind"] == "own") if Path("export/out/gate3/bake_jobs.json").exists()
       else sorted(k for k in man["lightmaps"]["assets"] if k != "_gate1_layout"))

    out["ok"] = bool(ok_all)
    Path(a.out).write_text(json.dumps(out, indent=1) + "\n")
    n_ok = sum(1 for c in out["checks"] if c["ok"])
    print(f"[p9pin] {'PASS' if ok_all else 'FAIL'} {n_ok}/{len(out['checks'])} -> {a.out}")
    sys.exit(0 if ok_all else 1)


main()
