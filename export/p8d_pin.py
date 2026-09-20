"""Phase 8d step 1: the PIN REPORT. Does the rebuilt Gate 1 set still stand on MAIN's bakes?

    python3 export/p8d_pin.py            # exit 1 if any pin fails; writes out/gate1/p8d_pin.json

The 8d ENV change (backdrop materials + a tree belt) and the 8a-3 shrub-card UV scale must not move
anything the Gate 2 PBR bakes, the Gate 3 lightmaps, the impostor atlases or the instance-row joins are
addressed by. What is pinned, from the brief and docs/decisions.md "8a export gate":

  * uv1 groups / atlas tiles / coverage and uv2 meshes and lightmap slots - identical (the bakes' UV space)
  * the tree counts AT THEIR CURRENT VALUES (r2, the hall-east belt): trees 186, far billboards 166,
    LOD2 blobs 85, near 20 - and the near list identical in content and order
  * the far list is NOT compared by position: `bpy.data.objects` is name-sorted, so the belt's 39 names
    interleave and re-point 87 of the 127 existing TREEFAR_### ids. What is checked is that the 127
    existing rows survive with their content and their relative order, that exactly the belt's 39 rows are
    new, and that every new tree resolves to an ALREADY BAKED impostor prototype
  * ARCH and ORN placed triangles identical; ENV placed = MAIN - 6 822 (-6 900 icospheres +78 billboards)
  * the lawn group renamed lawn -> backdrop_lawn, with no `..._lawn` group left behind

CPU only: it reads two export_set.json files. The glb byte-identity check (arch/orn/ground) runs after the
pack, in p8d_pin.py --glbs.
"""
import json
import os
import sys
import time
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
# PHASE 9 item 1. The EXPORT SET does not move: `tree_rule` still says 186 trees / 166 far billboards and
# ENV placed is still 895 052, because a billboard-only row keeps its billboard and its impostor and loses
# only its instance row in the far-tree MESH glbs. What moves is downstream of the export set, so it is
# pinned here rather than inferred: the two mesh sets' row counts, at the values export/belt_rule.py
# computes from the manifest's own stations. A change to a station, to the belt, or to either set's
# `draw_within_m` moves these and must be a decision, not a surprise.
EXPECT_MESH_ROWS = dict(far=149, walkup=131)          # of 166 tree_far rows
EXPECT_BILLBOARD_ONLY = dict(far=17, walkup=35)       # the HB rows beyond that set's radius
EXPECT_PLACED_TRIS = dict(far=1182338, walkup=3890782)  # was 1 317 097 / 4 937 933


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
        # r5 finding 5: compare each EXISTING tree's billboard id BY THE TREE, not by list position -
        # position is exactly what the interleave changes, so the old form compared a row with whatever
        # happened to sit at its index and counted 0. Measured this way: 87 of the 127.
        billboard_reindexed=sum(1 for r in old_rows
                                if next((q for q in fa if key(q) == key(r)), {}).get("billboard")
                                != r.get("billboard")),
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


def mesh_rows(out):
    """PHASE 9 item 1: the two far-tree MESH sets' row counts, pinned at the rule's own values.

    Read from the two `trees_far*.json` reports rather than recomputed, so this pins WHAT SHIPPED. The
    rule that produced them is `export/belt_rule.py`, which has its own CPU self-test; what this adds is
    that the numbers cannot drift silently between export rounds. Both reports are optional - the pin runs
    before the far-tree sets in the chain - and a missing one is reported, never silently passed."""
    def eq(name, va, vb, expect=None):
        ok = (va == vb) if expect is None else (vb == expect)
        out["checks"].append(dict(name=name, ok=bool(ok), main=va, new=vb, expected=expect))
        return ok

    ok, seen, idx = True, {}, {}
    for set_name, rel in (("far", "export/out/gate1/trees_far.json"),
                          ("walkup", "export/out/gate1/trees_far_lod1.json")):
        p = ROOT / rel
        if not p.exists():
            out["checks"].append(dict(name=f"trees_far[{set_name}] rows", ok=False, main=None,
                                      new=f"{rel} not written yet", expected=EXPECT_MESH_ROWS[set_name]))
            ok = False
            continue
        d = json.loads(p.read_text())
        n, nb = len(d["placements"]), len(d.get("billboard_only", []))
        seen[set_name] = dict(placements=n, billboard_only=nb,
                              placed_tris=d.get("gltf", {}).get("placed_tris"),
                              radius_m=(d.get("billboard_only_rule") or {}).get("radius_m"))
        idx[set_name] = (frozenset(pl["index"] for pl in d["placements"]),
                         frozenset(b["index"] for b in d.get("billboard_only", [])))
        ok &= eq(f"trees_far[{set_name}] indices are distinct and close on tree_far", EXPECT_FAR,
                 len(idx[set_name][0] | idx[set_name][1]), expect=EXPECT_FAR)
        ok &= eq(f"trees_far[{set_name}].placements", None, n, expect=EXPECT_MESH_ROWS[set_name])
        ok &= eq(f"trees_far[{set_name}].billboard_only", None, nb,
                 expect=EXPECT_BILLBOARD_ONLY[set_name])
        ok &= eq(f"trees_far[{set_name}].placed_tris", None, seen[set_name]["placed_tris"],
                 expect=EXPECT_PLACED_TRIS[set_name])
        ok &= eq(f"trees_far[{set_name}] rows close against tree_far", EXPECT_FAR, n + nb, expect=EXPECT_FAR)
    if "far" in seen and "walkup" in seen:
        # the real relation, by ROW INDEX and not by count: the set drawn at the SHORTER distance may
        # place fewer rows but never one the longer-reaching set dropped, which is what makes the
        # cross-set order check in verify_glb a subsequence rather than an equality.
        extra = sorted(idx["walkup"][0] - idx["far"][0])
        ok &= eq("the walk-up placed rows are a subset of the far set's, by index", [],
                 extra, expect=[])
        missing = sorted(idx["far"][1] - idx["walkup"][1])
        ok &= eq("every row the far set drops is dropped by the walk-up set too", [],
                 missing, expect=[])
        ok &= eq("the walk-up rows are a subset of the far set's, by count", True,
                 seen["walkup"]["placements"] <= seen["far"]["placements"], expect=True)
        seen["walkup"]["extra_rows_vs_far"] = extra
    out["mesh_rows"] = seen
    return ok


def glbs():
    """After the pack: arch / orn / ground glbs byte-identical to MAIN, env / env_shrubs expected to move.

    r5 finding 7: this comparison is only meaningful BEFORE `export/sync_main.sh` copies the worktree over
    MAIN - afterwards every row reads `identical: true` by construction. Each row therefore carries the
    mtime of both sides and whether MAIN was already in sync, so a stale record cannot be read as a pass.
    """
    out = {}
    for name in ("arch.glb", "orn.glb", "ground.glb", "env.glb", "env_shrubs.glb", "env_trees.glb",
                 "env_trees_lod1.glb"):
        p, q = ROOT / "export/out/gate1" / name, MAIN / "export/out/gate1" / name
        if not p.exists() or not q.exists():
            out[name] = "missing"
            continue
        out[name] = dict(bytes_main=q.stat().st_size, bytes_new=p.stat().st_size,
                         identical=sha(p) == sha(q),
                         mtime_main=int(q.stat().st_mtime), mtime_new=int(p.stat().st_mtime),
                         main_is_newer_or_equal=q.stat().st_mtime >= p.stat().st_mtime)
    pinned = ("arch.glb", "orn.glb", "ground.glb")
    ok = all(isinstance(out[n], dict) and out[n]["identical"] for n in pinned)
    synced = all(isinstance(v, dict) and v["identical"] for v in out.values())
    out["_note"] = ("every row identical: MAIN has already been synced from this worktree, so this run "
                    "proves nothing - re-read the record taken before the sync"
                    ) if synced else "taken against an un-synced MAIN: the comparison is meaningful"
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
        rec["glbs_generated"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        rec.pop("glbs_note", None)
        outp.write_text(json.dumps(rec, indent=1))
        return 0 if ok else 1
    a = json.loads((MAIN / "export/out/gate1/export_set.json").read_text())
    b = json.loads((ROOT / "export/out/gate1/export_set.json").read_text())
    out = dict(main=str(MAIN / "export/out/gate1/export_set.json"), checks=[],
               generated=time.strftime("%Y-%m-%dT%H:%M:%S"))
    ok = pin(a, b, out)
    ok &= mesh_rows(out)
    out["ok"] = bool(ok)
    # review r6 item 7: the `glbs` block belongs to a PACK, and this run is before one. Whatever a
    # previous round left in the file describes glbs that no longer exist, so it is dropped rather than
    # carried - `--glbs` writes a fresh one, stamped, after the pack.
    out["glbs"] = None
    out["glbs_ok"] = None
    out["glbs_note"] = ("not taken: `python3 export/p8d_pin.py --glbs` fills this in AFTER "
                        "export/gltf_pack.sh, and only a record written after that pack means anything")
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
