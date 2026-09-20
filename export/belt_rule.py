"""PHASE 9 item 1 — the billboard-only rule for the TAGGED far trees, and its CPU self-test.

    python3 export/belt_rule.py            # the table for both sets; exit 1 if an invariant breaks
    python3 export/belt_rule.py --frustum  # the cam03 analysis the choice rests on (same exit rule)

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


# ---------------------------------------------------------------------------------------------------
# The cam03 frustum analysis (`--frustum`). The rule above is a SPHERE about each eye, on purpose; this
# is the measurement that says why a sphere is not enough to justify option (a), and it is here rather
# than in prose so that a moved station, a re-cut belt or a new lens re-computes it instead of ageing.
# ---------------------------------------------------------------------------------------------------
FRUSTUM_STATION = "CAM_qa_03_colonnade_walk"
FRUSTUM_WITHIN_M = 15.0      # the walk-up set's draw distance: the rows that can be drawn as meshes at all
FRUSTUM_SCREEN_PX = 1920     # the delivery width the magnification is quoted at


def _cam_basis(st):
    """(eye, right, up, forward) in Blender world from a manifest `stations` entry.

    Blender's XYZ euler is R = Rz @ Ry @ Rx, and a camera looks down its own -Z with +X right, +Y up."""
    assert st.get("rotation_mode", "XYZ") == "XYZ", f"station rotation_mode {st.get('rotation_mode')}"
    rx, ry, rz = (float(v) for v in st["rotation_euler_xyz"])
    cx, sx, cy, sy, cz, sz = (math.cos(rx), math.sin(rx), math.cos(ry),
                              math.sin(ry), math.cos(rz), math.sin(rz))
    m = ((cz * cy, cz * sy * sx - sz * cx, cz * sy * cx + sz * sx),
         (sz * cy, sz * sy * sx + cz * cx, sz * sy * cx - cz * sx),
         (-sy,     cy * sx,                cy * cx))
    col = lambda j: [m[i][j] for i in range(3)]      # noqa: E731
    return ([float(v) for v in st["location"]], col(0), col(1), [-v for v in col(2)])


def frustum_rows(man, belt, station=FRUSTUM_STATION, within_m=FRUSTUM_WITHIN_M):
    """Every belt row whose TRUNK BASE is within `within_m` of that station's eye, projected into it.

    Per row: the trunk-base and crown-centre distances (the crown centre is what a card is quoted at),
    the ndc box of the row's world bounding box (width_m x width_m x height_m about the trunk base, the
    same box the billboard stands in), whether any of it is in frame, and how big ONE inner impostor
    texel would be on screen there - `inner_px` of the atlas spread across the crown's angular width at
    the crown-centre distance, at `FRUSTUM_SCREEN_PX`. `inner_px` is read from the manifest, never typed."""
    st = man["stations"][station]
    eye, right, up, fwd = _cam_basis(st)
    tan_x = (float(st["sensor_width_mm"]) / 2.0) / float(st["lens_mm"])
    assert st.get("sensor_fit", "HORIZONTAL") == "HORIZONTAL", "vertical sensor fit is not handled"
    tan_y = tan_x * 9.0 / 16.0
    near = float(st.get("clip_start") or 0.1)
    inner_px = float(man["impostors"]["inner_px"])
    dot = lambda a, b: sum(p * q for p, q in zip(a, b))          # noqa: E731
    out = []
    for i in sorted(belt):
        t = man["tree_far"][i]
        tb = [float(v) for v in t["trunk_base"]]
        d_base = math.dist(tb, eye)
        if d_base > within_m:
            continue
        w, h = float(t["width_m"]), float(t["height_m"])
        centre = [tb[0], tb[1], tb[2] + h / 2.0]
        d_crown = math.dist(centre, eye)
        xs, ys, zs = [], [], []
        for dx in (-w / 2, w / 2):
            for dy in (-w / 2, w / 2):
                for dz in (0.0, h):
                    v = [tb[0] + dx - eye[0], tb[1] + dy - eye[1], tb[2] + dz - eye[2]]
                    z = dot(v, fwd)
                    zs.append(z)
                    if z > near:
                        xs.append(dot(v, right) / z / tan_x)
                        ys.append(dot(v, up) / z / tan_y)
        # In frame = some corner is in front of the near plane AND the ndc box of the corners that are
        # overlaps [-1, 1]^2. The crown centre's depth is reported too but is NOT the test: at 6.5 m a
        # 13 m crown straddles the eye plane, so its centre can sit behind the camera while the near half
        # of it fills the left of the frame (cypress_33). A corner that merely grazes the plane projects
        # far outside the box and is rejected by the ndc test on its own (redwood_26 at ndc x -27.8).
        z_c = dot([centre[k] - eye[k] for k in range(3)], fwd)
        inside = bool(xs) and min(xs) <= 1 and max(xs) >= -1 and min(ys) <= 1 and max(ys) >= -1
        crown_px = w / (2.0 * tan_x * d_crown) * FRUSTUM_SCREEN_PX
        out.append(dict(index=i, tree=t["source_tree"], d_base_m=d_base, d_crown_m=d_crown,
                        xy_m=math.dist(tb[:2], eye[:2]), w_m=w, h_m=h, z_crown_m=z_c, z_max_m=max(zs),
                        in_frustum=inside,
                        ndc_x=(min(xs), max(xs)) if xs else None,
                        ndc_y=(min(ys), max(ys)) if ys else None,
                        crown_px=crown_px, texel_px=crown_px / inner_px))
    return out, station, inner_px


def _frustum_main():
    man, man_p = read_manifest()
    belt, belt_p, _doc = belt_indices(man)
    eyes = station_eyes(man)
    rows, station, inner_px = frustum_rows(man, belt)
    print(f"[belt_rule] {man_p}\n[belt_rule] tag {BELT_TAG} from {belt_p}: {len(belt)} of "
          f"{len(man['tree_far'])} far rows")
    print(f"[belt_rule] {station} at {FRUSTUM_WITHIN_M:.0f} m, {man['stations'][station]['lens_mm']:.0f} mm "
          f"on {man['stations'][station]['sensor_width_mm']:.0f} mm, 16:9, {FRUSTUM_SCREEN_PX} px wide; "
          f"impostor inner_px {inner_px:.0f}")
    print(f"{'row':>4} {'tree':32} {'d_crown':>7} {'d_base':>6} {'xy':>6} {'in':>4} "
          f"{'ndc x':>15} {'ndc y':>15} {'crown m':>12} {'crown px':>8} {'px/texel':>8}")
    for r in rows:
        nx = f"{r['ndc_x'][0]:6.2f}..{r['ndc_x'][1]:6.2f}" if r["ndc_x"] else "  (behind)"
        ny = f"{r['ndc_y'][0]:6.2f}..{r['ndc_y'][1]:6.2f}" if r["ndc_y"] else "  (behind)"
        print(f"{r['index']:4} {r['tree']:32} {r['d_crown_m']:7.1f} {r['d_base_m']:6.1f} {r['xy_m']:6.1f} "
              f"{'YES' if r['in_frustum'] else 'no':>4} {nx:>15} {ny:>15} "
              f"{r['w_m']:5.1f} x {r['h_m']:4.1f} {r['crown_px']:8.0f} {r['texel_px']:8.1f}")
        if not r["in_frustum"]:
            print(f"     -> out of frame: the crown centre is {r['z_crown_m']:+.1f} m along the view axis "
                  f"and the deepest corner reaches only {r['z_max_m']:+.1f} m, so the box that does clear "
                  f"the near plane projects outside [-1, 1]")
        elif r["z_crown_m"] <= 0:
            print(f"     -> in frame although the crown CENTRE is {abs(r['z_crown_m']):.1f} m behind the "
                  f"eye plane: the near half of the crown (corners to {r['z_max_m']:+.1f} m) is what draws")
    # INVARIANT: no row this camera can see is ever billboard-only, in EITHER set. If a station moves or
    # a draw distance changes so that an in-frame row falls outside the sphere, this fails loudly.
    ok = True
    for set_name in ("far", "walkup"):
        r_m, excl = select(man, belt, eyes, DRAW_WITHIN_M[set_name])
        for r in rows:
            if r["in_frustum"] and r["index"] in excl:
                print(f"[belt_rule] FAIL {set_name}: row {r['index']} {r['tree']} is IN {station}'s frame "
                      f"and the rule would ship it billboard-only ({excl[r['index']][1]:.1f} m > {r_m:.0f} m)")
                ok = False
    n_in = sum(1 for r in rows if r["in_frustum"])
    print(f"[belt_rule] {n_in} of {len(rows)} belt rows within {FRUSTUM_WITHIN_M:.0f} m are in frame; "
          f"every one of them keeps its mesh in both sets" if ok else "[belt_rule] frustum invariant broken")
    print(f"[belt_rule] {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


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
    sys.exit(_frustum_main() if "--frustum" in sys.argv else _main())
