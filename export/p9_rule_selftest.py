"""PHASE 9 item 1 — the billboard-only rule, end to end, on CPU.

    python3 export/p9_rule_selftest.py        # exit 0 = every case behaved

`export/trees_far.py` runs only inside Blender, so the rule it applies and the manifest it feeds could
otherwise be exercised only by a full export. This builds the two `trees_far*.json` reports the rule WOULD
write - the real reports with the excluded rows removed and a `billboard_only` list added, exactly as
trees_far.py assembles them - and pushes them through the two readers that consume them:

  * `manifest_v4.trees_lighting_block`, which must return ONE ROW PER FAR TREE (not per mesh placement),
    because the impostor of a billboard-only row still needs its E_placement / E_bake;
  * `verify_glb.far_tree_counts`, which must accept the new shape and REJECT every way of getting it wrong.

The Gate 4 order check has the same kind of negative suite (`export/gate4_order_selftest.py`); this is that
pattern for the far-tree counts. CPU only: no Blender, no GPU, nothing written.
"""
import copy
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import belt_rule as br       # noqa: E402
import manifest_v4 as m4     # noqa: E402
import verify_glb as vg      # noqa: E402

FAILS = []
TOTAL = 0


def ok(cond, what):
    global TOTAL
    TOTAL += 1
    print(f"  {'ok  ' if cond else 'FAIL'} {what}")
    if not cond:
        FAILS.append(what)


def synth(man, belt, eyes, set_name, real):
    """the report trees_far.py would write for `set_name`, from the real one plus the rule."""
    r, excl = br.select(man, belt, eyes, br.DRAW_WITHIN_M[set_name])
    keep = [pl for pl in real["placements"] if pl["index"] not in excl]
    pmap = man["impostors"]["prototype_map"]
    bo = [dict(index=i, tag=br.BELT_TAG, billboard=man["tree_far"][i]["billboard"],
               source_tree=man["tree_far"][i]["source_tree"],
               prototype=pmap[man["tree_far"][i]["prototype"]],
               source_prototype=man["tree_far"][i]["prototype"],
               loc=[round(float(v), 4) for v in man["tree_far"][i]["trunk_base"]],
               height_m=man["tree_far"][i]["height_m"],
               walk_dist_m=man["tree_far"][i]["walk_dist_m"],
               nearest_station=excl[i][0], nearest_station_m=round(excl[i][1], 2))
          for i in sorted(excl)]
    # trees_far.py re-states `gltf.placed_tris` after the rule, so the synthetic report must too or the
    # pin would be fed the PRE-rule triangle count and could not be exercised against its own expectation.
    per = {k: v["tris"] for k, v in (real.get("prototypes") or {}).items()}
    g = dict(real.get("gltf") or {})
    if per and g.get("placed_tris") is not None:
        g["placed_tris"] = g["placed_tris"] - sum(per[pmap[man["tree_far"][i]["prototype"]]] for i in excl)
    d = dict(real, placements=keep, billboard_only=bo, gltf=g,
             billboard_only_rule=dict(tag=br.BELT_TAG, radius_m=r,
                                      draw_within_m=br.DRAW_WITHIN_M[set_name], rule="(selftest)"))
    return d


def run_pin(reports, root):
    """`p8d_pin.mesh_rows` against reports written under `root` -> (overall ok, {check name: ok})."""
    import p8d_pin as pin
    g1 = Path(root) / "export/out/gate1"
    g1.mkdir(parents=True, exist_ok=True)
    for set_name, rel in (("far", "trees_far.json"), ("walkup", "trees_far_lod1.json")):
        if set_name in reports:
            (g1 / rel).write_text(json.dumps(reports[set_name]))
        elif (g1 / rel).exists():
            (g1 / rel).unlink()
    was, pin.ROOT = pin.ROOT, Path(root)
    try:
        out = dict(checks=[])
        good = pin.mesh_rows(out)
    finally:
        pin.ROOT = was
    return good, {c["name"]: c["ok"] for c in out["checks"]}


def main():
    man, man_p = br.read_manifest()
    belt, _bp, _doc = br.belt_indices(man)
    eyes = br.station_eyes(man)
    reports = {}
    for set_name, rel in (("far", "export/out/gate1/trees_far.json"),
                          ("walkup", "export/out/gate1/trees_far_lod1.json")):
        p = br.pick(rel)
        if p is None:
            print(f"[p9_selftest] {rel} not found - run the export first", file=sys.stderr)
            return 2
        reports[set_name] = synth(man, belt, eyes, set_name, json.loads(p.read_text()))
    tf, tw = reports["far"], reports["walkup"]
    n = len(man["tree_far"])
    print(f"[p9_selftest] {man_p}\n[p9_selftest] far {len(tf['placements'])} + "
          f"{len(tf['billboard_only'])}, walk-up {len(tw['placements'])} + {len(tw['billboard_only'])}, "
          f"of {n} far trees")

    print("the lighting block")
    blk = m4.trees_lighting_block(tf, man)
    per = blk["mesh"]["placements"]
    ok(len(per) == n, f"one row per FAR TREE, not per mesh placement ({len(per)} of {n})")
    ok(blk["mesh"]["with_mesh"] == len(tf["placements"])
       and blk["mesh"]["billboard_only"] == len(tf["billboard_only"]),
       f"the two populations are counted ({blk['mesh']['with_mesh']} + {blk['mesh']['billboard_only']})")
    ok(sorted(d["index"] for d in per) == list(range(n)), "every tree_far index is covered exactly once")
    ok([d["index"] for d in per] == sorted(d["index"] for d in per), "the rows are in tree_far order")
    bo_idx = {b["index"] for b in tf["billboard_only"]}
    ok(all(d["mesh"] is (d["index"] not in bo_idx) for d in per), "`mesh` is true exactly for the placed rows")
    ok(all(isinstance(d.get("rgb"), list) and len(d["rgb"]) == 3 for d in per),
       "every row - billboard-only included - carries an rgb, which is the whole point")

    print("the set relations")
    fi = [p["index"] for p in tf["placements"]]
    wi = [p["index"] for p in tw["placements"]]
    ok(set(wi) <= set(fi), f"the walk-up rows are a subset of the far set's ({len(wi)} <= {len(fi)})")
    ok(wi == sorted(wi) and fi == sorted(fi), "both lists are in tree_far index order")
    ok(bo_idx <= belt and {b['index'] for b in tw['billboard_only']} <= belt,
       "only TAGGED rows are ever excluded")

    print("the irradiance topology (review r1 finding 1)")
    # `topology.json` is what export/trees_far_set.py builds the per-placement irradiance blend from, and
    # that bake covers EVERY far row - a billboard-only row's impostor is modulated by it like any other.
    # The rule's first cut wrote only the mesh rows here, which made the next bake die on its own
    # `len(placed) == len(tree_far)` assert. `belt_rule.topology_problems` is the one contract the writer,
    # the reader and this test all call; the synthetic file below is the shape trees_far.py now writes.
    def topo_row(i, has_mesh):
        t = man["tree_far"][i]
        p = man["impostors"]["prototype_map"][t["prototype"]]
        s = float(t["height_m"]) / float(man["impostors"]["prototypes"][p]["height_above_base_m"])
        loc = [round(float(v), 4) for v in t["trunk_base"]]
        return dict(index=i, object=f"TREEFAR_{i:03d}", prototype=p, mesh=f"MESH_{p}", scale=round(s, 6),
                    has_mesh=has_mesh, loc=loc, height_m=t["height_m"], walk_dist_m=t["walk_dist_m"],
                    source_tree=t["source_tree"],
                    placed_bbox_min=[loc[0] - 1.0, loc[1] - 1.0, loc[2]],
                    placed_bbox_max=[loc[0] + 1.0, loc[1] + 1.0, loc[2] + float(t["height_m"])])
    fbo = {b["index"] for b in tf["billboard_only"]}
    good_topo = dict(placements=[topo_row(i, i not in fbo) for i in range(n)])
    ok(not br.topology_problems(good_topo["placements"], n, len(tf["placements"])),
       f"the shape trees_far.py writes passes ({n} rows, {n - len(fbo)} with a mesh) - "
       f"{br.topology_problems(good_topo['placements'], n, len(tf['placements']))}")
    ok(br.check_topology(good_topo, n) is good_topo["placements"], "check_topology returns the rows")

    def tcase(name, mutate, needle, n_mesh=None):
        rows = copy.deepcopy(good_topo["placements"])
        mutate(rows)
        b = br.topology_problems(rows, n, n_mesh)
        ok(any(needle in x for x in b), f"{name}: reported {(b[0][:95] if b else 'NOTHING')}")

    # THE REGRESSION ITSELF: the file carries the mesh rows alone, as the first cut of the rule wrote it
    tcase("only the mesh rows are written (the r1 blocker)",
          lambda r: r.__setitem__(slice(None), [x for x in r if x["has_mesh"]]),
          "irradiance bake places EVERY far row")
    tcase("a billboard-only row carries no `scale`",
          lambda r: next(x for x in r if not x["has_mesh"]).pop("scale"), "no `scale`")
    tcase("a billboard-only row carries no `object`",
          lambda r: next(x for x in r if not x["has_mesh"]).pop("object"), "no `object`")
    tcase("a row carries no placed bbox",
          lambda r: r[0].pop("placed_bbox_max"), "no `placed_bbox_max`")
    tcase("a row is not flagged either way",
          lambda r: r[0].pop("has_mesh"), "no `has_mesh`")
    tcase("the rows are written in a different order",
          lambda r: r.reverse(), "index order")
    tcase("one far row is written twice and another dropped",
          lambda r: r.__setitem__(5, dict(r[6])), "share an `index`")
    tcase("the mesh count disagrees with the set's own placement list",
          lambda r: r, "flagged `has_mesh`", n_mesh=len(tf["placements"]) + 1)
    # and the contract is not vacuous: it fails with a different tree_far length
    ok(br.topology_problems(good_topo["placements"], n + 1),
       "a topology written against a different far list FAILs")

    print("verify_glb.far_tree_counts - the good shape, then every way of breaking it")
    good = dict(tree_far=man["tree_far"], tree_rule=dict(far_billboards=n), trees=dict(
        far_mesh=dict(placements=[dict(index=i) for i in fi],
                      billboard_only=dict(count=len(tf["billboard_only"])),
                      lighting=dict(mesh=dict(placements=[dict(index=i) for i in range(n)]))),
        walkup_mesh=dict(placements=[dict(index=i) for i in wi],
                         billboard_only=dict(count=len(tw["billboard_only"])))))
    counts, bad = vg.far_tree_counts(good)
    ok(not bad, f"the shipped shape passes ({counts['far_mesh_placements']} + "
                f"{counts['far_mesh_billboard_only']} = {counts['tree_far_rows']}) - {bad}")

    cases = []

    def case(name, mutate, needle):
        m = copy.deepcopy(good)
        mutate(m)
        _c, b = vg.far_tree_counts(m)
        hit = any(needle in x for x in b)
        cases.append((name, hit, b))
        ok(hit, f"{name}: reported {(b[0][:95] if b else 'NOTHING')}")

    case("a mesh row vanishes with no billboard-only row to match",
         lambda m: m["trees"]["far_mesh"]["placements"].pop(), "mesh placements +")
    case("the billboard-only count is inflated",
         lambda m: m["trees"]["far_mesh"].__setitem__("billboard_only", dict(count=99)), "mesh placements +")
    case("the lighting list is cut down to the mesh placements",
         lambda m: m["trees"]["far_mesh"]["lighting"]["mesh"].__setitem__(
             "placements", [dict(index=i) for i in fi]), "per-placement irradiance row")
    case("the walk-up set places a row the far set does not",
         lambda m: (m["trees"]["walkup_mesh"]["placements"].extend(
             [dict(index=-1)] * (len(fi) - len(wi) + 1)),
             m["trees"]["walkup_mesh"].__setitem__("billboard_only", dict(count=0))), "subset of the far")
    case("the export set and the manifest disagree about the far list",
         lambda m: m.__setitem__("tree_rule", dict(far_billboards=n - 1)), "disagree")
    # and the shape that shipped BEFORE this rule must still pass unchanged
    m = copy.deepcopy(good)
    m["trees"]["far_mesh"]["placements"] = [dict(index=i) for i in range(n)]
    m["trees"]["far_mesh"].pop("billboard_only")
    m["trees"]["walkup_mesh"]["placements"] = dict(count=n, same_as="trees.far_mesh.placements")
    m["trees"]["walkup_mesh"].pop("billboard_only")
    _c, b = vg.far_tree_counts(m)
    ok(not b, f"the pre-rule shape (166 / 166 / same_as, no billboard_only) still passes - {b}")

    print("export/p8d_pin.mesh_rows - the shipped numbers, then the drifts it has to catch")
    with tempfile.TemporaryDirectory() as td:
        good_pin, names = run_pin(reports, td)
        ok(good_pin, f"the rule's own two reports pass every pin ({len(names)} checks)")
        ok(any("subset of the far set's, by index" in k for k in names),
           "the pin really compares row INDICES across the sets, not just their counts")

        def neg(what, mutate, check_substr):
            r = copy.deepcopy(reports)
            mutate(r)
            g, ns = run_pin(r, td)
            hit = any(check_substr in k and not v for k, v in ns.items())
            ok(not g and hit, f"{what}: the pin FAILs, and on `...{check_substr}`")

        neg("a walk-up row goes missing", lambda r: r["walkup"]["placements"].pop(),
            "walkup].placements")
        neg("the walk-up set places a row the far set dropped",
            lambda r: (r["walkup"]["placements"].append(dict(r["far"]["billboard_only"][0])),
                       r["walkup"]["billboard_only"].__delitem__(
                           next(j for j, b in enumerate(r["walkup"]["billboard_only"])
                                if b["index"] == r["far"]["billboard_only"][0]["index"]))),
            "subset of the far set's, by index")
        neg("the far set drops a row the walk-up set still places",
            lambda r: (r["far"]["billboard_only"].append(dict(r["far"]["placements"].pop(0))),),
            "subset of the far set's, by index")
        neg("the placed triangles drift while the row counts hold",
            lambda r: r["far"]["gltf"].__setitem__("placed_tris",
                                                   r["far"]["gltf"]["placed_tris"] - 1),
            "far].placed_tris")
        g, ns = run_pin({k: v for k, v in reports.items() if k != "walkup"}, td)
        ok(not g and not ns.get("trees_far[walkup] rows", True),
           "a report that has not been written yet is REPORTED, never silently passed")

    print(f"[p9_selftest] {TOTAL - len(FAILS)}/{TOTAL} checks behaved"
          + (f" - {len(FAILS)} FAILURE(S)" if FAILS else ""))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
