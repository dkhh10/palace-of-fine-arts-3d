"""Ray-cast validation of the Phase 5 flythrough path. NOTHING IS RENDERED (round 14 is a no-render round).

Opens **assets/lighting.blend** and LINKS ARCH + ENV into the same scene, or -- with **`--master`** -- opens
**master.blend READ-ONLY** (it is never saved) and gates against the ORNAMENT instances the film actually shows;
see the comment on `use_master` below for why the two differ. Casts rays from the flythrough camera. Two modes:

    scripts/blender_run.sh 900 -- --background --python scripts/light_flythrough_check.py -- --probe 70.5,25.6 40,90
        For each (x, y): the surface directly below (cast down from +12 m), its object and z, plus the nearest
        obstacle at eye height. Used to SITE the route on real ground instead of eyeballed z values.

    scripts/blender_run.sh 1800 -- --background --python scripts/light_flythrough_check.py --
        The acceptance table: the camera sampled every --step frames (12 by default), and for each sample the
        position, the surface below (agl), the nearest hit over a Fibonacci sphere of --rays directions, and the
        instantaneous speed (sampled at EVERY frame, not every 12th). Then the four gates of the round-14 brief:
          clearance   min nearest-hit distance >= CLEAR_MIN (1.5 m) at every sampled frame
          level       camera never below the walk (agl >= AGL_MIN) and never below WATER_Z + 0.5 over water
          speed       <= 6 m/s everywhere except the flagged water crossing (<= 10 m/s)
          holds       >= 3 s of near-stationary camera at the hero station and under the dome

Exit code 0 only when all four gates pass, so `blender_run.sh` reports a real failure.
"""
import bpy, sys, os, math, json, time
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
import light_flythrough as ft
import arch_params as A

CLEAR_MIN = 1.5        # m, brief: ">= 1.5 m clearance everywhere"
CLEAR_MIN_GALLERY = 1.35   # inside the colonnade: the 2.80 m clear gallery caps the centreline at 1.40 m to a
                           # shaft axis (1.42 measured, the flutes give it back 0.02); the tightest ENV object
                           # is ENV_shrub_pitto1_1107 overhanging the walk at theta -50.8, 1.45 m
FPS_FALLBACK = [24]
AGL_MIN = 1.5          # m, camera above whatever surface is directly below it
WATER_MIN_Z = common.WATER_Z + 0.5     # -0.8: never this low over the lagoon
SPEED_MAX = 6.0        # m/s
SPEED_MAX_WATER = 10.0
HOLD_S = 3.0
HOLD_SPEED = 0.20      # m/s: "stationary" for the purpose of the eased holds
MAX_RAY = 300.0

WATER_NAMES = ("ENV_lagoon_water",)


def link_site():
    """ARCH + ENV + ORN linked into this scene, at the viewport LOD the master ships (LOD1).

    ROUND 16 (flythrough plan finding 2): ORN was missing, and ORN is what hangs off the ARCH surfaces the route
    passes closest to -- the capitals and the frieze of the gallery the camera walks down at 1.42 m from a shaft
    axis, 0.02 m over that gallery's own geometric bound. A clearance table taken without it was not a clearance
    table."""
    for key, coll in (("ARCH", "ARCH"), ("ENV", "ENV"), ("ORN", "ORN")):
        c = common.link_collection(common.ASSET_FILES[key], coll, link=True)
        print(f"[check] linked {coll}: {'ok' if c else 'MISSING'}")
    common.set_lod(viewport=1, render=0)
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    dg.update()
    return dg


def fib_dirs(n):
    out, ga = [], math.pi * (3.0 - math.sqrt(5.0))
    for i in range(n):
        z = 1.0 - 2.0 * (i + 0.5) / n
        r = math.sqrt(max(0.0, 1.0 - z * z))
        t = ga * i
        out.append(Vector((r * math.cos(t), r * math.sin(t), z)))
    return out


def cast(scene, dg, origin, direction, dist=MAX_RAY):
    hit, loc, nrm, idx, ob, mw = scene.ray_cast(dg, origin, direction, distance=dist)
    if not hit:
        return None, None, None
    return (Vector(loc) - Vector(origin)).length, (ob.name if ob else "?"), Vector(loc)


def surface_below(scene, dg, x, y, from_z):
    """The first surface under (x, y, from_z). Returns (name, z, agl) or (None, None, inf)."""
    d, name, loc = cast(scene, dg, Vector((x, y, from_z)), Vector((0.0, 0.0, -1.0)), MAX_RAY)
    if d is None:
        return None, None, float("inf")
    return name, loc.z, d


def nearest_hit(scene, dg, pos, dirs):
    best_d, best_n = float("inf"), None
    for v in dirs:
        d, name, _ = cast(scene, dg, pos, v, MAX_RAY)
        if d is not None and d < best_d:
            best_d, best_n = d, name
    return best_d, best_n


def probe(scene, dg, points, eye=1.75, from_z=40.0):
    dirs = fib_dirs(64)
    print(f"\n[probe] cast down from z={from_z:.1f}, eye = surface + {eye:.2f}")
    print(f"[probe] {'x':>8s} {'y':>8s} | {'surface':28s} {'z':>7s} | eye_z {'nearest':>8s}  what")
    for (x, y) in points:
        name, z, _ = surface_below(scene, dg, x, y, from_z)
        if name is None:
            print(f"[probe] {x:8.1f} {y:8.1f} | {'(nothing below)':28s} {'-':>7s} |")
            continue
        ez = z + eye
        d, what = nearest_hit(scene, dg, Vector((x, y, ez)), dirs)
        print(f"[probe] {x:8.1f} {y:8.1f} | {name:28s} {z:7.2f} | {ez:5.2f} {d:8.2f}  {what}")


def columns(prefix, cx=A.COL_ARC_CENTER[0], cy=A.COL_ARC_CENTER[1], tlo=-70.0, thi=-15.0):
    """Every object whose name starts with `prefix`, in colonnade-arc polar coordinates about COL_ARC_CENTER.
    Used to place the gallery entry in a real bay instead of on top of a shaft."""
    rows = []
    for o in bpy.data.objects:
        if not o.name.startswith(prefix):
            continue
        p = o.matrix_world.translation
        r = math.hypot(p.x - cx, p.y - cy)
        th = math.degrees(math.atan2(p.y - cy, p.x - cx))
        if tlo <= th <= thi:
            rows.append((th, r, o.name, p.x, p.y))
    rows.sort()
    print(f"\n[cols] {len(rows)} objects matching {prefix!r} in theta {tlo}..{thi}")
    for th, r, n, x, y in rows:
        print(f"[cols] theta {th:7.2f}  r {r:7.2f}  ({x:7.2f}, {y:7.2f})  {n}")


# ----------------------------------------------------------------------------- the acceptance run
def per_frame_speed(scene, cam, frames):
    """Position at every frame, and the speed between consecutive frames (m/s)."""
    pos = []
    for f in range(1, frames + 1):
        scene.frame_set(f)
        pos.append(cam.matrix_world.translation.copy())
    spd = [0.0] * len(pos)
    for i in range(1, len(pos)):
        spd[i] = (pos[i] - pos[i - 1]).length * FPS_FALLBACK[0]
    spd[0] = spd[1] if len(spd) > 1 else 0.0
    return pos, spd


def longest_hold(spd, lo, hi, fps):
    """Longest run of frames in [lo, hi] (1-based, inclusive) whose speed stays under HOLD_SPEED, in seconds."""
    best = run = 0
    for f in range(lo, min(hi, len(spd)) + 1):
        run = run + 1 if spd[f - 1] <= HOLD_SPEED else 0
        best = max(best, run)
    return best / fps


def leg_at(sch, f):
    for lg in sch["legs"]:
        if lg["f0"] <= f <= lg["f1"]:
            return lg
    return sch["legs"][-1] if f > sch["legs"][-1]["f1"] else dict(name="hero_hold", water=False, cap=0.0)


def check(scene, dg, step=12, rays=96):
    cam = bpy.data.objects.get("CAM_flythrough")
    if cam is None:
        sys.exit("[check] no CAM_flythrough in this file; run light_flythrough.py first")
    sch = ft.load_schedule()
    if sch is None:
        sys.exit("[check] CAM_flythrough carries no 'schedule'; rebuild with light_flythrough.py")
    fps, frames = sch["fps"], sch["frames"]
    FPS_FALLBACK[0] = fps
    dirs = fib_dirs(rays)
    pos, spd = per_frame_speed(scene, cam, frames)
    samples = list(range(1, frames + 1, step))
    if samples[-1] != frames:
        samples.append(frames)

    rows, t0 = [], time.time()
    for f in samples:
        scene.frame_set(f)
        p = cam.matrix_world.translation.copy()
        dg.update()
        d, what = nearest_hit(scene, dg, p, dirs)
        sname, sz, agl = surface_below(scene, dg, p.x, p.y, p.z)
        lg = leg_at(sch, f)
        rows.append(dict(frame=f, t=round((f - 1) / fps, 2), pos=[round(v, 2) for v in p],
                         d=round(d, 2) if d < 1e29 else None, what=what,
                         surface=sname or "-", surface_z=round(sz, 2) if sz is not None else None,
                         agl=round(agl, 2) if agl < 1e29 else None,
                         over_water=bool(sname and sname in WATER_NAMES),
                         speed=round(spd[f - 1], 2), leg=lg["name"]))
    print(f"[check] {len(samples)} samples x {rays} rays in {time.time() - t0:.1f}s")

    print("\n  frame     t |      x      y     z | nearest  what                              |"
          "   agl surface                    | speed  leg")
    for r in rows:
        x, y, z = r["pos"]
        dd = f"{r['d']:7.2f}" if r["d"] is not None else "    inf"
        ag = f"{r['agl']:5.2f}" if r["agl"] is not None else "  inf"
        print(f"  {r['frame']:5d} {r['t']:5.1f} | {x:6.1f} {y:6.1f} {z:5.2f} | {dd}  {(r['what'] or '-'):32s} | "
              f"{ag} {r['surface']:26s} | {r['speed']:5.2f}  {r['leg']}")

    # ------------------------------------------------------------------ gates
    fails = []
    #  Gate 1, clearance.  The colonnade gallery cannot satisfy 1.5 m: the rows are COL_ROW_SPACING 4.5 m apart
    #  and the shafts are COLONNADE_D 1.7 m, so the gallery is 2.8 m of clear width and the largest possible
    #  clearance on its centreline is 1.40 m.  The gallery leg is therefore gated at CLEAR_MIN_GALLERY.
    bad = []
    for r in rows:
        lim = CLEAR_MIN_GALLERY if r["leg"] == "gallery" else CLEAR_MIN
        if r["d"] is not None and r["d"] < lim:
            bad.append(f"f{r['frame']} {r['d']:.2f} < {lim} ({r['what']})")
    dmin = min(r["d"] for r in rows if r["d"] is not None)
    dmin_ng = min([r["d"] for r in rows if r["d"] is not None and r["leg"] != "gallery"] or [float("inf")])
    dmin_g = min([r["d"] for r in rows if r["d"] is not None and r["leg"] == "gallery"] or [float("inf")])
    print(f"\n[gate] clearance : min {dmin:.2f} m overall | outside the gallery {dmin_ng:.2f} (>= {CLEAR_MIN}) | "
          f"gallery {dmin_g:.2f} (>= {CLEAR_MIN_GALLERY}, geometric max on the centreline 1.40) "
          f"{'PASS' if not bad else 'FAIL: ' + '; '.join(bad)}")
    if bad:
        fails.append("clearance")

    lvl = []
    for r in rows:
        if r["agl"] is not None and r["agl"] < AGL_MIN:
            lvl.append(f"f{r['frame']} agl {r['agl']:.2f}")
        if r["over_water"] and r["pos"][2] < WATER_MIN_Z:
            lvl.append(f"f{r['frame']} z {r['pos'][2]:.2f} over water")
    aglmin = min(r["agl"] for r in rows if r["agl"] is not None)
    zw = [r["pos"][2] for r in rows if r["over_water"]]
    if not zw:
        # The over-water gate keys on the literal name in WATER_NAMES; if ENV renames or LOD-suffixes the
        # lagoon surface the gate would otherwise pass with ZERO samples (prep review 8).
        lvl.append(f"0 samples over water: none of {WATER_NAMES} was hit -- the gate is vacuous, not passing")
    print(f"[gate] level     : min agl {aglmin:.2f} m (>= {AGL_MIN}); over water min z "
          f"{(min(zw) if zw else float('nan')):.2f} (>= {WATER_MIN_Z}, {len(zw)} samples over the lagoon) "
          f"{'PASS' if not lvl else 'FAIL: ' + '; '.join(lvl)}")
    if lvl:
        fails.append("level")

    over = []
    for f in range(1, frames + 1):
        lg = leg_at(sch, f)
        lim = SPEED_MAX_WATER if lg["water"] else SPEED_MAX
        if spd[f - 1] > lim + 1e-6:
            over.append((f, spd[f - 1], lim))
    wat = [f for f in range(1, frames + 1) if leg_at(sch, f)["water"]]
    vmax_land = max(spd[f - 1] for f in range(1, frames + 1) if f not in set(wat))
    vmax_water = max([spd[f - 1] for f in wat] or [0.0])
    fmax_land = max(range(1, frames + 1), key=lambda f: -1.0 if f in set(wat) else spd[f - 1])
    # ROUND 16 (flythrough plan finding 3): ONE window, printed from the schedule's own leg table over EVERY frame,
    # not from the sampled frames. The round-14 report read "water crossing frames 1-404" beside a leg table that
    # ended `water` at 397 and began `shore` at 409 only because the check sampled every 12th frame (397, then
    # 409); the legs themselves are contiguous by construction. The boundary frame is printed so the two numbers
    # can never be quoted as two different windows again.
    # r16 review carry 3 (cosmetic): the legs are contiguous, so leg n's f1 IS leg n+1's f0 and printing both
    # read as an overlap ("water 1-404  shore 404-571"). Every leg after the first now prints f0 + 1.
    print(f"[gate] legs      : " + "  ".join(
        f"{lg['name']} {lg['f0'] + (1 if i else 0)}-{lg['f1']}@{lg['cap']:g}" for i, lg in enumerate(sch["legs"])))
    print(f"[gate] speed     : land max {vmax_land:.2f} m/s at f{fmax_land} (<= {SPEED_MAX}); water crossing is the "
          f"ONE window frames {min(wat)}-{max(wat)} (boundary: first land frame {max(wat) + 1}), max "
          f"{vmax_water:.2f} m/s (<= {SPEED_MAX_WATER}) "
          f"{'PASS' if not over else 'FAIL at %d frames, worst %.2f' % (len(over), max(o[1] for o in over))}")
    if over:
        fails.append("speed")

    holds = [(n, longest_hold(spd, w[0], w[1], fps)) for n, w in sch["holds"].items()]
    ok = all(s >= HOLD_S - 1e-6 for _, s in holds)
    print("[gate] holds     : " + "  ".join(f"{n} {s:.2f}s" for n, s in holds) +
          f"  (each >= {HOLD_S}s) {'PASS' if ok else 'FAIL'}")
    if not ok:
        fails.append("holds")

    total = sch["path_length_m"]
    print(f"\n[check] path {total:.1f} m over {frames} frames @ {fps} fps = {frames / fps:.1f} s, "
          f"mean {total / (frames / fps):.2f} m/s")
    print(f"[check] RESULT: {'ALL GATES PASS' if not fails else 'FAIL (' + ', '.join(fails) + ')'}")
    return rows, fails


if __name__ == "__main__":
    args = common.script_args()
    # ROUND 16 (flythrough plan finding 2). `--master` opens master.blend READ-ONLY (never saved) instead of
    # assets/lighting.blend + link_site(). It is the only way to gate clearance against the ORNAMENT the film
    # actually shows: `build_master` INSTANCES the ORN assets onto the ARCH sockets and then EXCLUDES the whole
    # "ORN" source collection from the view layer (build_master.py, "sources out of the view layer"), so the ORN
    # collection this script can link holds nothing but the prototypes -- 138 ORN meshes whose object origin is
    # the world origin, all hide_render. Linking it, as round 16 first did, produced thirteen "failures" between
    # frames 1077 and 1113 against ORN_capital_rotunda / ORN_attic_panel prototypes parked at (0,0,0), i.e.
    # against geometry that is not in the film. On master the same frames are gated against the real instances.
    use_master = "--master" in args
    blend = (common.ROOT / "master.blend") if use_master else common.ASSET_FILES["LIGHT"]
    bpy.ops.wm.open_mainfile(filepath=str(blend))
    scene = bpy.context.scene
    if use_master:
        common.set_lod(viewport=1, render=0)
        bpy.context.view_layer.update()
        dg = bpy.context.evaluated_depsgraph_get()
        dg.update()
        # r16 review carry 3: print the ROUTE fingerprint in this mode too. `--master` gates the geometry of
        # master.blend against the schedule this script computes from `light_flythrough`, so a master built from
        # a STALE assets/lighting.blend would otherwise pass every gate silently while carrying a different
        # camera path. Length + station count + frame range are enough to tell the two apart at a glance.
        print(f"[check] gating on {blend} ({len(scene.objects)} objects; ORN instanced onto its sockets)")
        _sch = ft.load_schedule()
        if _sch is None:
            print("[check] route fingerprint: master.blend carries NO schedule on CAM_flythrough")
        else:
            print(f"[check] route fingerprint (read off THIS file's CAM_flythrough): "
                  f"{_sch['path_length_m']:.1f} m, {len(_sch.get('stations', ft.STATIONS))} stations, "
                  f"frames 1-{_sch['frames']} @ {_sch['fps']} fps, legs " +
                  " ".join(f"{lg['name']}:{lg['f0']}-{lg['f1']}" for lg in _sch["legs"]))
    else:
        dg = link_site()
    if "--columns" in args:
        pre = args[args.index("--columns") + 1]
        columns(pre)
        sys.exit(0)
    if "--probe" in args:
        pts = []
        for a in args[args.index("--probe") + 1:]:
            if a.startswith("--"):
                break
            xs, ys = a.split(",")[:2]
            pts.append((float(xs), float(ys)))
        fz = float(args[args.index("--fromz") + 1]) if "--fromz" in args else 40.0
        probe(scene, dg, pts, from_z=fz)
        sys.exit(0)
    step = int(args[args.index("--step") + 1]) if "--step" in args else 12
    rays = int(args[args.index("--rays") + 1]) if "--rays" in args else 96
    rows, fails = check(scene, dg, step=step, rays=rays)
    if "--json" in args:
        out = common.RENDERS / "logs" / "light_flythrough_check.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(rows, indent=1))
        print(f"[check] wrote {out}")
    sys.exit(1 if fails else 0)
