"""Round 9: where every hand-placed PLAN tree stands relative to cam 01 and to the colonnade gallery.

    blender -b --python scripts/env_r9_replan.py -- [--solve 0.684 0.704 ...] [--roff 13.0] [--land] [--verify]

No Blender data is touched (it runs headless only because `qa_cameras` imports bpy/mathutils).  For each PLAN
entry it prints the closed-form cam-01 frame x of the trunk, the crown's frame-x span, the distance along the
view axis and `env_lib.gallery_offset` - the radial distance from the colonnade gallery centreline, which is the
number round 9 found four A-group entries failing.  `--solve` re-derives a world position for a target frame x at
`--roff` metres outside the arc (that is `env_r8_fit.solve`, the round-8 tool, so the A group can be re-placed the
way A2 was instead of being swept there by `shadow_relief`).

`--land` tests every PLAN coordinate against the three hard gates a hand-placed tree has to satisfy on its own,
now that no build pass will move it (r9 review, finding 1): dry land (`env_lib.water_polygons`, the very fields
`env_build` passes to `env_trees`), the 4.1 m gallery keep-out, and QA-02-13's 37 m podium ring measured with the
PLAN height.  For a failing entry it spiral-searches the nearest coordinate that passes ALL THREE, so the plan can
be corrected by hand instead of by a snap that runs after the gates.

`--verify` re-runs the two solvers whose output is frozen in PLAN - `env_r8_fit.solve` for the A and A2 conifers,
and the QA-02-13 radial push for the podium-ring bake - and fails if any baked coordinate has drifted more than
0.2 m from what the code now computes (r9 review, carry 7: PLAN was a literal snapshot with nothing asserting it,
so a change to COL_ARC_CENTER / COL_ARC_R, the cam-01 station or the lens would silently make all of it stale).
"""
import sys, os, math

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
import env_lib as L
import env_trees
import env_r8_fit as FIT
import qa_cameras

ARGS = common.script_args()
ROFF = float(ARGS[ARGS.index("--roff") + 1]) if "--roff" in ARGS else 13.0

SPEC = next(c for c in qa_cameras.CAMERAS if "_qa_01_" in c["name"])
LX, LY = SPEC["loc"][0], SPEC["loc"][1]
_fx, _fy = SPEC["target"][0] - LX, SPEC["target"][1] - LY
_n = math.hypot(_fx, _fy)
FWD = (_fx / _n, _fy / _n)
RGT = (FWD[1], -FWD[0])
KTAN = 0.5 * 36.0 / SPEC["lens"]


def frame_x(x, y):
    dx, dy = x - LX, y - LY
    z = dx * FWD[0] + dy * FWD[1]
    return 0.5 + 0.5 * ((dx * RGT[0] + dy * RGT[1]) / z) / KTAN


def axis_dist(x, y):
    return (x - LX) * FWD[0] + (y - LY) * FWD[1]


def span(sp, x, y, h):
    """Crown frame-x span: the trunk +- the crown radius (env_lib.CROWN_R x height) across the view axis."""
    rad = L.CROWN_R.get(sp, 0.35) * h
    z = max(1e-3, axis_dist(x, y))
    half = 0.5 * (rad / z) / KTAN
    c = frame_x(x, y)
    return c - half, c + half


PODIUM_R, CLEAR = 31.0, 6.0            # QA-02-13, as in env_trees.shadow_relief


def gates(sp, x, y, h, lagoon_field, islet_fields):
    """`(dry, gallery_ok, podium_ok)` for one candidate coordinate - the three gates a hand-placed PLAN entry has
    to satisfy by itself.  Same predicates as `env_trees.land_snap`, `env_lib.gallery_clear` and the podium loop
    in `env_trees.shadow_relief`."""
    dry = not (lagoon_field.signed(x, y) < 1.0 and not any(f.signed(x, y) < 0 for f in islet_fields))
    g = L.gallery_offset(x, y)
    rad = L.CROWN_R.get(sp, 0.35) * h
    d = math.hypot(x, y)
    return dry, (g is None or g >= L.GALLERY_KEEPOUT), (d - rad >= PODIUM_R + CLEAR)


def land_report():
    site = common.load_site_local()
    _osm, _lag, _isl, lagoon_field, islet_fields = L.water_polygons(site)
    print(f"\n[env_r9_replan] PLAN vs the three hard gates: dry land, {L.GALLERY_KEEPOUT} m gallery keep-out, "
          f"{PODIUM_R + CLEAR:.0f} m podium ring (PLAN height)")
    bad = 0
    for (sp, x, y, h, note) in env_trees.PLAN:
        dry, gok, pok = gates(sp, x, y, h, lagoon_field, islet_fields)
        if dry and gok and pok:
            continue
        bad += 1
        why = " ".join(w for w, ok in (("IN-WATER", dry), ("GALLERY", gok), ("PODIUM", pok)) if not ok)
        d = math.hypot(x, y)
        rad = L.CROWN_R.get(sp, 0.35) * h
        print(f"  {str(note).split(' ')[0]:5s} {sp:14s} ({x:6.1f},{y:6.1f}) h{h:4.0f}  {why:22s} "
              f"lagoon {lagoon_field.signed(x, y):6.2f}  r-crown {d - rad:5.1f}  frame x {frame_x(x, y):.3f}")
        # nearest coordinate that passes all three: 0.5 m spiral steps, 32 bearings, out to 20 m
        best = None
        for i in range(1, 41):
            r = 0.5 * i
            for k in range(32):
                a = 2 * math.pi * k / 32
                xx, yy = x + r * math.cos(a), y + r * math.sin(a)
                if all(gates(sp, xx, yy, h, lagoon_field, islet_fields)):
                    best = (xx, yy, r)
                    break
            if best:
                break
        if best:
            print(f"        nearest coordinate passing all three: ({best[0]:6.2f},{best[1]:6.2f})  {best[2]:.1f} m "
                  f"away  frame x {frame_x(x, y):.3f} -> {frame_x(best[0], best[1]):.3f}  "
                  f"d_axis {axis_dist(best[0], best[1]):6.1f}")
        else:
            print("        NO coordinate within 20 m passes all three")
    print(f"[env_r9_replan] {bad} of {len(env_trees.PLAN)} PLAN entries fail a gate")
    return bad


# --- carry 7: the coordinates in PLAN that are a formula's output, and the formula that produced them ----------
# `--verify` recomputes each and fails if PLAN has drifted more than TOL metres from it.
TOL = 0.2
SOLVED = [   # (frame-x target, radial offset outside the arc, PLAN coordinate, label)
    (0.672, 13.0, (-37.2, -43.1), "A cluster core"),
    (0.684, 13.0, (-40.0, -42.5), "A cluster depth"),
    (0.704, 13.0, (-44.5, -41.4), "A dark mass right of the dome"),
    (0.713, 13.0, (-46.5, -40.8), "A cluster second crown"),
    (0.723, 13.0, (-48.6, -40.2), "A cluster depth"),
    (0.790, 8.0, (-60.5, -30.6), "A2 strip pine"),
    (0.820, 8.0, (-65.7, -28.2), "A2 second column"),
    (0.890, 8.0, (-76.6, -22.3), "A2 first box"),
]


def verify():
    print(f"\n[env_r9_replan] --verify: PLAN vs the solvers, tolerance {TOL} m")
    fails = 0
    for (t, roff, (px, py), label) in SOLVED:
        X, Y = FIT.solve(t, roff)
        d = math.hypot(X - px, Y - py)
        ok = d <= TOL
        fails += 0 if ok else 1
        print(f"  {'ok  ' if ok else 'FAIL'} solve({t:.3f}, {roff:+.1f}) -> ({X:7.2f},{Y:7.2f})  PLAN "
              f"({px:7.2f},{py:7.2f})  d {d:5.2f} m   {label}")
    for (sp, x, y, h, note) in env_trees.PLAN:
        d = math.hypot(x, y)
        rad = L.CROWN_R.get(sp, 0.35) * h
        if d - rad >= PODIUM_R + CLEAR or d < 1e-3:
            continue
        fails += 1
        print(f"  FAIL {sp:14s} ({x:6.1f},{y:6.1f}) h{h:4.0f} crown {rad:4.1f} reaches r {d - rad:5.1f} - inside "
              f"the {PODIUM_R + CLEAR:.0f} m podium ring   [{str(note)[:40]}]")
    # Phase 10: the appended NE-mass columns carry a crown-width factor, so their ring radius is the larger of
    # CROWN_R and the measured Sapling radius x that factor (env_trees.P10_REAL_R).
    for (sp, x, y, h, note, w) in getattr(env_trees, "P10_ADD", []):
        d = math.hypot(x, y)
        rad = max(L.CROWN_R.get(sp, 0.35), env_trees.P10_REAL_R.get(sp, 0.35) * w) * h
        ok = d - rad >= PODIUM_R + CLEAR and L.gallery_clear(x, y)
        fails += 0 if ok else 1
        print(f"  {'ok  ' if ok else 'FAIL'} P10 {sp:14s} ({x:6.1f},{y:6.1f}) h{h:4.0f} w{w:.1f} crown {rad:4.1f} "
              f"reaches r {d - rad:5.1f} (ring {PODIUM_R + CLEAR:.0f})   [{str(note)[:40]}]")
    print(f"[env_r9_replan] --verify: {fails} failure(s)")
    if fails:
        sys.exit(1)


def shipped_report(blend="assets/environment.blend"):
    """Every hand-placed PLAN entry, PLAN coordinate vs the coordinate that is IN THE BLEND.

    The round's headline claim - "PLAN holds the shipped coordinate" - is only worth what a reader can check, and
    r8 and r9 both shipped it untrue (env r9 review, finding 1).  This opens the built .blend and matches each
    instance back to its plan entry by species + note, so the table can be pasted into the notes.  Non-zero exit
    if any hand-placed tree stands more than 0.01 m from its PLAN coordinate.
    """
    import bpy
    path = blend if os.path.isabs(blend) else str(common.ROOT / blend)
    bpy.ops.wm.open_mainfile(filepath=path)
    built = {}
    for o in bpy.data.objects:
        if not o.name.startswith("ENV_tree_") or not o.name.endswith("_LOD1"):
            continue
        key = (o.get("species"), str(o.get("note", "")))
        built.setdefault(key, []).append((o.location.x, o.location.y, o.name))
    print(f"\n[env_r9_replan] --shipped {path}")
    print("  group species        PLAN (   X,     Y)   shipped (   X,     Y)   d      object")
    worst, n, dropped = 0.0, 0, 0
    for (sp, x, y, h, note) in env_trees.PLAN:
        if str(note).split(" ")[0] not in env_trees.PIN_HAND_PLACED:
            continue
        n += 1
        cands = built.get((sp, str(note)), [])
        if not cands:
            # `shadow_relief` may DROP an F/H backdrop tree behind the hero camera (env_trees.relief_policy
            # returns droppable there); that is not a move and does not fail this check.  Anything else missing is.
            droppable = env_trees.relief_policy(note, x, y)[1]
            print(f"  {str(note).split(' ')[0]:5s} {sp:14s} ({x:6.1f},{y:6.1f})   not built "
                  f"({'dropped by shadow_relief, droppable here' if droppable else 'UNEXPECTED'})")
            dropped += 1
            worst = max(worst, 0.0 if droppable else 1e9)
            continue
        # several entries can share a note ("F east shore row"), so a matched instance is consumed
        bx, by, nm = min(cands, key=lambda c: math.hypot(c[0] - x, c[1] - y))
        cands.remove((bx, by, nm))
        d = math.hypot(bx - x, by - y)
        worst = max(worst, d)
        print(f"  {str(note).split(' ')[0]:5s} {sp:14s} ({x:6.1f},{y:6.1f})   ({bx:6.1f},{by:6.1f})   "
              f"{d:5.3f}  {nm}")
    print(f"[env_r9_replan] --shipped: {n} hand-placed entries, {n - dropped} built, {dropped} dropped as "
          f"droppable, worst PLAN-to-shipped distance {min(worst, 999.999):.3f} m")
    if worst > 0.01:
        sys.exit(1)


def main():
    print(f"[env_r9_replan] cam 01 {SPEC['loc']} lens {SPEC['lens']} mm; gallery keep-out {L.GALLERY_KEEPOUT} m")
    print("  group species     (   X,     Y)   h   frame x span     centre   d_axis  gallery_off")
    for (sp, x, y, h, note) in env_trees.PLAN:
        g = L.gallery_offset(x, y)
        gs = "   -  " if g is None else f"{g:6.2f}"
        flag = "  <-- INSIDE THE GALLERY" if (g is not None and g < L.GALLERY_KEEPOUT) else ""
        a, b = span(sp, x, y, h)
        print(f"  {str(note).split(' ')[0]:5s} {sp:12s} ({x:6.1f},{y:6.1f}) {h:4.0f}   "
              f"{a:.3f}-{b:.3f}    {frame_x(x, y):.3f}   {axis_dist(x, y):6.1f}   {gs}{flag}")
    if "--podium" in ARGS:
        # QA-02-13 (env_trees.shadow_relief): no crown within 6 m of the 31 m podium.  Round 9 stops that pass
        # relocating hand-placed trees, so the correction has to live in PLAN.  These are the coordinates the
        # radial push produced, computed with the PLAN height (the tallest the tree can be, so the clearance
        # holds however far the relief later lowers it).
        PODIUM_R, CLEAR = 31.0, 6.0
        print(f"\n[env_r9_replan] QA-02-13 podium ring {PODIUM_R + CLEAR:.0f} m, PLAN heights")
        for (sp, x, y, h, note) in env_trees.PLAN:
            d = math.hypot(x, y)
            rad = L.CROWN_R.get(sp, 0.35) * h
            if d - rad >= PODIUM_R + CLEAR or d < 1e-3:
                continue
            k = (PODIUM_R + CLEAR + rad) / d
            nx, ny = x * k, y * k
            print(f"    {sp:14s} ({x:6.1f},{y:6.1f}) h{h:4.0f} crown {rad:4.1f} reaches r {d - rad:5.1f}"
                  f"  ->  ({nx:6.2f},{ny:6.2f})  frame x {frame_x(x, y):.3f} -> {frame_x(nx, ny):.3f}"
                  f"   [{str(note)[:34]}]")
    if "--shipped" in ARGS:
        shipped_report()
    if "--land" in ARGS:
        land_report()
    if "--verify" in ARGS:
        verify()
    if "--solve" in ARGS:
        i = ARGS.index("--solve")
        targets = []
        for v in ARGS[i + 1:]:
            try:
                targets.append(float(v))
            except ValueError:
                break
        print(f"\n[env_r9_replan] solving for frame x {targets} at {ROFF:+.1f} m outside the arc")
        for t in targets:
            X, Y = FIT.solve(t, ROFF)
            g = L.gallery_offset(X, Y)
            print(f"    -> ({X:7.2f}, {Y:7.2f})  frame x {frame_x(X, Y):.3f}  d_axis {axis_dist(X, Y):6.1f}  "
                  f"gallery_off {('-' if g is None else f'{g:.2f}')}")


main()
