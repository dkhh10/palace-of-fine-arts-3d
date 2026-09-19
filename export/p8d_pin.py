"""Phase 8d step 1: the PIN REPORT. Does the rebuilt Gate 1 set still stand on MAIN's bakes?

    python3 export/p8d_pin.py            # exit 1 if any pin fails; writes out/gate1/p8d_pin.json

The 8d ENV change (backdrop materials + a tree belt) and the 8a-3 shrub-card UV scale must not move
anything the Gate 2 PBR bakes, the Gate 3 lightmaps, the impostor atlases or the instance-row joins are
addressed by. What is pinned, from the brief and docs/decisions.md "8a export gate":

  * uv1 groups / atlas tiles / coverage and uv2 meshes and lightmap slots - identical (the bakes' UV space)
  * near trees 20 / far billboards 127, and the near and far LISTS identical in content AND order (the
    billboard index is the impostor atlas' key and the instance rows' order)
  * ARCH and ORN placed triangles identical; ENV placed = MAIN + 6 900 (the belt) and nothing else
  * the lawn group renamed lawn -> backdrop_lawn, with no `..._lawn` group left behind

CPU only: it reads two export_set.json files. The glb byte-identity check (arch/orn/ground) runs after the
pack, in p8d_pin.py --glbs.
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = Path(os.environ.get("PFA_MAIN_ROOT", "/Users/dk/Projects/3d render blender 3rd attempt building"))
# r2 (the hall-east belt): the ENV delta is a NET of two movements the belt report states - the four
# icosphere belt objects leave backdrop_forest (-6 900 placed tris) and 39 far-tree billboards arrive
# (+78, two triangles each). 901 874 -> 895 052.
EXPECT_ENV_DELTA = -6822
EXPECT_FAR = 166            # 127 + 39 belt trees
EXPECT_NEAR = 20            # unchanged, same order
EXPECT_TREES_TOTAL = 186    # 147 + 39
EXPECT_LOD2_BLOB = 85       # 46 + 39: the belt trees' LOD2 blobs are in the source set too
BELT_JSON = "docs/phase8d_belt_r2_trees.json"


def sha(p):
    import hashlib
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def pin(a, b, out):
    def eq(name, va, vb, expect=None):
        ok = (va == vb) if expect is None else (vb == expect)
        out["checks"].append(dict(name=name, ok=bool(ok), main=va, new=vb, expected=expect))
        return ok

    ok = True
    for k in ("uv1_groups", "uv1_atlas_tiles", "uv1_coverage", "uv1_coverage_min", "uv2_meshes",
              "lightmap_slots", "lightmap_assets", "uv_missing_counts", "meshes_not_single_material"):
        ok &= eq(k, a.get(k), b.get(k))
    ta, tb = a["tree_rule"], b["tree_rule"]
    # r2: these three MOVE by the belt, by an amount the belt report states; the rest still pin.
    for k, want in (("trees_total", EXPECT_TREES_TOTAL), ("far_billboards", EXPECT_FAR),
                    ("lod2_blob_objects", EXPECT_LOD2_BLOB), ("near_exported", EXPECT_NEAR)):
        ok &= eq(f"tree_rule.{k}", ta.get(k), tb.get(k), expect=want)
    for k in ("within_radius", "near_tris_used"):
        ok &= eq(f"tree_rule.{k}", ta.get(k), tb.get(k))
    # THE FAR LIST. r2 appends 39 rows, but `bpy.data.objects` is name-sorted, so the exporter's own
    # order INTERLEAVES them among the existing ones and every TREEFAR_### index after the first belt
    # name shifts. What must hold is therefore not "the first 127 rows are byte-identical" but: the SET
    # of existing rows is unchanged, their relative order is unchanged, and the new rows are exactly the
    # 39 the belt report names (docs/phase8d_belt_r2_trees.json). All three are checked.
    fa, fb = a["tree_far_list"], b["tree_far_list"]
    key = lambda r: r.get("source_tree") or r.get("billboard")
    belt = json.loads((MAIN / BELT_JSON).read_text())
    belt_names = {t["lod1_object"] for t in (belt if isinstance(belt, list) else belt["trees"])}
    old_rows = [r for r in fb if key(r) not in belt_names]
    new_rows = [r for r in fb if key(r) in belt_names]
    ok &= eq("far list: the 127 existing rows survive, in order, with their content",
             [{k: v for k, v in r.items() if k != "billboard"} for r in fa],
             [{k: v for k, v in r.items() if k != "billboard"} for r in old_rows])
    ok &= eq("far list: exactly the belt's 39 rows are new", len(belt_names), len(new_rows),
             expect=len(belt_names))
    ok &= eq("far list: every new row is a belt tree", sorted(belt_names),
             sorted(key(r) for r in new_rows), expect=sorted(belt_names))
    # the interleave itself, recorded rather than assumed: where the new rows landed
    out["far_interleave"] = dict(
        first_new_index=next((i for i, r in enumerate(fb) if key(r) in belt_names), None),
        billboard_reindexed=sum(1 for i, r in enumerate(fb)
                                if key(r) not in belt_names and i < len(fa) and
                                fa[i].get("billboard") != r.get("billboard")),
        note="bpy.data.objects is name-sorted, so the belt names interleave and every TREEFAR_### index "
             "after the first new name shifts; the impostor atlas and the instance rows are keyed by "
             "PROTOTYPE and by row POSITION within the re-dumped order, both regenerated in this chain, "
             "so the shift is safe - but any diagnostic that quoted a TREEFAR_### index must be re-read.")
    # every new tree must resolve to an already-baked impostor prototype (no atlas re-bake in scope)
    man = json.loads((MAIN / "export/out/gate3/manifest.json").read_text())
    pmap = man["impostors"]["prototype_map"]
    baked = set(man["impostors"]["prototypes"])
    # gate3_set.py's own rule, verbatim: an impostor is always the LOD1 prototype. The Gate 3 map was
    # built from the PREVIOUS far list, so a prototype that is new to the far block is simply absent from
    # it; what matters is that the rule lands on a prototype that is already BAKED (no atlas re-bake).
    rule = lambda p: p[:-5] + "_LOD1" if p.endswith("_LOD2") else p
    new_protos = sorted({r["prototype"] for r in new_rows})
    unresolved = sorted(p for p in new_protos if rule(p) not in baked)
    ok &= eq("every new far tree resolves to a BAKED impostor prototype", [], unresolved, expect=[])
    out["new_prototypes"] = dict(
        prototypes=new_protos,
        resolved={p: rule(p) for p in new_protos},
        missing_from_gate3_map=sorted(p for p in new_protos if p not in pmap),
        note="the Gate 3 manifest's prototype_map predates the belt, so the keys listed in "
             "missing_from_gate3_map are absent from it; manifest_v4 extends the map with gate3_set's own "
             "_LOD2 -> _LOD1 rule and asserts the target is one of the 16 baked prototypes, so no atlas "
             "and no impostor blend is re-baked.")
    ok &= eq("tree_near_list (order and content)", a["tree_near_list"], b["tree_near_list"])
    for cls in ("ARCH", "ORN"):
        ok &= eq(f"placed_tris.{cls}", a["totals"]["placed_tris"][cls], b["totals"]["placed_tris"][cls])
    da = b["totals"]["placed_tris"]["ENV"] - a["totals"]["placed_tris"]["ENV"]
    out["env_arithmetic"] = dict(
        main=a["totals"]["placed_tris"]["ENV"], new=b["totals"]["placed_tris"]["ENV"], delta=da,
        expected=EXPECT_ENV_DELTA,
        terms="backdrop_forest loses the four icosphere belt objects (-6 900) and 39 far-tree billboards "
              "arrive at 2 tris each (+78): -6 822 net, 901 874 -> 895 052")
    ok &= eq("placed_tris.ENV delta", da, da, expect=EXPECT_ENV_DELTA)
    # the lawn rename, seen through the derived export names
    def groups(doc, needle):
        return sorted({n for n in doc["assets"] if needle in n})
    ok &= eq("lawn groups gone (MAIN had them)", None, groups(b, "_lawn") and
             [n for n in groups(b, "_lawn") if "backdrop_lawn" not in n], expect=[])
    ok &= eq("backdrop_lawn group present", True, bool(groups(b, "backdrop_lawn")), expect=True)
    out["lawn"] = dict(main=groups(a, "_lawn"), new=groups(b, "_lawn"))
    out["env_placed"] = dict(main=a["totals"]["placed_tris"]["ENV"],
                             new=b["totals"]["placed_tris"]["ENV"], delta=da)
    return ok


def glbs():
    """After the pack: arch / orn / ground glbs byte-identical to MAIN, env / env_shrubs expected to move."""
    out = {}
    for name in ("arch.glb", "orn.glb", "ground.glb", "env.glb", "env_shrubs.glb", "env_trees.glb",
                 "env_trees_lod1.glb"):
        p, q = ROOT / "export/out/gate1" / name, MAIN / "export/out/gate1" / name
        if not p.exists() or not q.exists():
            out[name] = "missing"
            continue
        out[name] = dict(bytes_main=q.stat().st_size, bytes_new=p.stat().st_size,
                         identical=sha(p) == sha(q))
    pinned = ("arch.glb", "orn.glb", "ground.glb")
    ok = all(isinstance(out[n], dict) and out[n]["identical"] for n in pinned)
    print(json.dumps(out, indent=1))
    print(f"[p8d_pin] glbs {'PASS' if ok else 'FAIL'}: {', '.join(pinned)} must be byte-identical")
    return ok, out


def main():
    outp = ROOT / "export/out/gate1/p8d_pin.json"
    if "--glbs" in sys.argv:
        ok, out = glbs()
        rec = json.loads(outp.read_text()) if outp.exists() else {}
        rec["glbs"] = out
        rec["glbs_ok"] = ok
        outp.write_text(json.dumps(rec, indent=1))
        return 0 if ok else 1
    a = json.loads((MAIN / "export/out/gate1/export_set.json").read_text())
    b = json.loads((ROOT / "export/out/gate1/export_set.json").read_text())
    out = dict(main=str(MAIN / "export/out/gate1/export_set.json"), checks=[])
    ok = pin(a, b, out)
    out["ok"] = bool(ok)
    outp.write_text(json.dumps(out, indent=1))
    for c in out["checks"]:
        mark = "ok  " if c["ok"] else "FAIL"
        v = c["expected"] if c["expected"] is not None else c["new"]
        print(f"[pin] {mark} {c['name']}: {str(v)[:110]}")
    print(f"[p8d_pin] ENV placed {out['env_placed']['main']} -> {out['env_placed']['new']} "
          f"(+{out['env_placed']['delta']}), lawn groups {out['lawn']['main']} -> {out['lawn']['new']}")
    print(f"[p8d_pin] {'PASS' if ok else 'FAIL'} -> {outp}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
