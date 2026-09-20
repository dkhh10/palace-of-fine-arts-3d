"""PHASE 9 item 1 — the billboard-only rule for the TAGGED far trees, and its CPU self-test.

    python3 export/belt_rule.py            # the table for both sets; exit 1 if an invariant breaks

Why this is its own module. `export/trees_far.py` runs only inside Blender (it imports bpy at the top), so
the rule that decides WHICH far-tree rows get a mesh could not otherwise be exercised, measured or
regression-tested without a Blender run. Everything here is pure data - the Gate 3 manifest's `tree_far`
rows and `stations`, plus the 8d belt report - so the same code answers "which rows does this set place"
for the export and for the analysis, and the two can never drift apart.

THE RULE. A row tagged `HB` (the hall-east belt, 8d r2) keeps its mesh only if its trunk base is within
`draw_within_m + FADE_BAND_M` of a QA station eye, where `draw_within_m` is the distance the VIEWER draws
THAT SET at (walk-up 15 m on desktop, far 45 m on mobile). Beyond that the fragment dissolve discards every
fragment of the mesh, so no station can ever see it and the row ships as its impostor alone. Untagged rows
are never excluded.

WHAT IT DOES NOT DECIDE. The row stays in `tree_far`, keeps its billboard, its impostor atlas frame and its
per-placement irradiance row; only the instance row in this set's glb goes away. See the BILLBOARD-ONLY
ROWS note in export/trees_far.py for the viewer hand-off that goes with it.
"""
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gate0_common as g0  # noqa: E402

BELT_JSON = "docs/phase8d_belt_r2_trees.json"   # the 8d r2 belt report: the HB tag's own record
BELT_TAG = "HB"                                 # the tag this rule acts on
FADE_BAND_M = 5.0        # `pfaFadeBand` default (web/src/foliage.js); beyond draw_within_m + this the
                         # fragment dissolve discards every fragment, so no station can see the mesh
STATION_PREFIX = "CAM_qa_"   # the six QA stations in manifest `stations`; CAM_flythrough is not a station
# the two sets' viewer draw distances, kept here so the analysis and the export read ONE number each.
# far  = what MOBILE loads (device.js `walkupMesh: '0'`, `farTreeMesh: 45`)
# walkup = what DESKTOP loads (`trees.walkup_mesh.draw_within_m`, `WALKUP_DIST_M` in foliageLazy.js)
DRAW_WITHIN_M = dict(far=45.0, walkup=15.0)


def pick(rel):
    """A repo-relative path, this worktree first, then MAIN (export/out and the docs are both read that way)."""
    return next((q for q in (g0.ROOT / rel, g0.MAIN_ROOT / rel) if q.exists()), None)


def read_manifest():
    p = pick("export/out/gate3/manifest.json")
    assert p is not None, "export/out/gate3/manifest.json not found in this worktree or in MAIN"
    return json.loads(p.read_text()), p


def belt_indices(man):
    """The `tree_far` row indices carrying the HB tag, from the belt report itself.

    The tag lives in the 8d r2 build record, not in the manifest: the export set's `tree_far` rows have no
    tag field and inventing one here would be a second list to keep in step. The join is by `source_tree`
    == the belt row's `lod1_object`, and it is asserted TOTAL - a belt tree that no longer reaches the far
    list means the belt or the export set moved and this rule's numbers are stale."""
    p = pick(BELT_JSON)
    assert p is not None, f"{BELT_JSON} not found in this worktree or in MAIN - the HB tag has no source"
    doc = json.loads(p.read_text())
    names = {t["lod1_object"] for t in doc["trees"]}
    assert len(names) == int(doc["count"]), \
        f"{p.name}: {len(names)} distinct lod1_object names for a declared count of {doc['count']}"
    idx = {i for i, r in enumerate(man["tree_far"]) if r["source_tree"] in names}
    assert len(idx) == len(names), (
        f"{p.name} names {len(names)} belt trees but only {len(idx)} of them are `tree_far` rows - the belt "
        f"and the export set were built from different scenes, so the billboard-only rule cannot know "
        f"which rows it is allowed to drop")
    return idx, p, doc


def station_eyes(man):
    """The six QA station EYE positions, from the manifest's own `stations` block (Blender world).

    Read from the manifest rather than from scripts/qa_cameras.py so the rule measures against the stations
    that were actually exported; `CAM_flythrough` is excluded because it is a path and its stored location
    is the identity."""
    st = {k: [float(v) for v in d["location"]]
          for k, d in (man.get("stations") or {}).items() if k.startswith(STATION_PREFIX)}
    assert len(st) >= 6, \
        f"manifest `stations` has {len(st)} {STATION_PREFIX}* cameras, expected the six QA stations"
    return st


def nearest_station(eyes, loc):
    d = {k: math.dist([float(v) for v in loc], e) for k, e in eyes.items()}
    k = min(d, key=d.get)
    return k, d[k]


def select(man, belt, eyes, draw_within_m):
    """-> (keep_radius_m, {index: (station, distance)} for the EXCLUDED rows).

    Excluded = tagged AND farther from every station eye than draw_within_m + FADE_BAND_M."""
    r = float(draw_within_m) + FADE_BAND_M
    out = {}
    for i in sorted(belt):
        k, d = nearest_station(eyes, man["tree_far"][i]["trunk_base"])
        if d > r:
            out[i] = (k, d)
    return r, out


def _main():
    man, man_p = read_manifest()
    belt, belt_p, _doc = belt_indices(man)
    eyes = station_eyes(man)
    far = man["tree_far"]
    proto_map = man["impostors"]["prototype_map"]
    tris = {}
    for set_name, rel in (("far", "export/out/gate1/trees_far.json"),
                          ("walkup", "export/out/gate1/trees_far_lod1.json")):
        q = pick(rel)
        if q is not None:
            d = json.loads(q.read_text())
            tris[set_name] = ({k: v["tris"] for k, v in d["prototypes"].items()},
                              d.get("gltf", {}).get("placed_tris"))
    print(f"[belt_rule] {man_p}\n[belt_rule] tag {BELT_TAG} from {belt_p}: {len(belt)} of {len(far)} far rows")
    ok = True
    prev_excluded = None
    for set_name in ("far", "walkup"):
        r, excl = select(man, belt, eyes, DRAW_WITHIN_M[set_name])
        kept = sorted(belt - set(excl))
        line = (f"[belt_rule] {set_name:6} draw_within {DRAW_WITHIN_M[set_name]:4.0f} m + fade "
                f"{FADE_BAND_M:.0f} = {r:4.0f} m: {len(kept):2} tagged rows placed, "
                f"{len(excl):2} billboard-only")
        if set_name in tris:
            per, placed = tris[set_name]
            saved = sum(per[proto_map[far[i]["prototype"]]] for i in excl)
            line += (f"   placed tris {placed} -> {placed - saved} (-{saved}, "
                     f"-{100.0 * saved / placed:.1f} %), rows {len(far)} -> {len(far) - len(excl)}")
        print(line)
        for i in kept:
            k, d = nearest_station(eyes, far[i]["trunk_base"])
            print(f"           keeps {far[i]['source_tree']:34} {d:6.1f} m from {k}")
        # INVARIANT 1: a tagged row a station can see as a mesh is never excluded
        for i in excl:
            _k, d = nearest_station(eyes, far[i]["trunk_base"])
            if d <= r:
                print(f"[belt_rule] FAIL row {i} excluded at {d:.1f} m, inside the {r:.0f} m radius"); ok = False
        # INVARIANT 2: the sets nest - a set drawn at a SHORTER distance never keeps a row the longer one drops
        if prev_excluded is not None and not prev_excluded.keys() <= set(excl):
            print(f"[belt_rule] FAIL the {set_name} set keeps a row the longer-reaching set dropped"); ok = False
        prev_excluded = excl
    # INVARIANT 3: nothing untagged is ever touched
    for set_name in ("far", "walkup"):
        _r, excl = select(man, belt, eyes, DRAW_WITHIN_M[set_name])
        if not set(excl) <= belt:
            print(f"[belt_rule] FAIL the {set_name} set excluded an untagged row"); ok = False
    print(f"[belt_rule] {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(_main())
