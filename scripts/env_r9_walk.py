"""Round-9 no-render probe: is the colonnade gallery walk clear of ENV planting?

    blender --background --python scripts/env_r9_walk.py -- [--blend assets/environment.blend] [--step 2.0]

LIGHT r14's flythrough walks the gallery centreline (the arc `arch_params.COL_ARC_CENTER` / `COL_ARC_R`, the one
ARCH strikes both column rows about) at eye z = COLONNADE_GROUND_Z + 1.15.  The clear width between the shaft
faces is `COL_ROW_SPACING - COLONNADE_D` = 2.80 m, so nothing may stand within 1.40 m of the centreline; the
planting rule (`env_lib.GALLERY_KEEPOUT`) is stricter at 4.1 m, which also clears the outer column face.

Definitions, fixed here so BEFORE and AFTER are the same measurement:
  walk samples   `env_lib.colonnade_walk_points(step)`, s = 0 .. arc length of each wing, both wings.
  ENV objects    every object in the .blend EXCEPT (a) `ENV_terrain` and `ENV_water` (the ground and the lagoon
                 surface: the walk stands ON them, so their distance is 0 by construction and says nothing),
                 (b) the hidden `ENV_trees` source meshes (parked at -600, -600), and (c) the LOD0/LOD2 copies of
                 an instance, which sit at the same origin as its LOD1 (counting them three times says nothing).
  origin d       plan (x, y) distance from the sample to the object's origin.  This is the statistic LIGHT r14
                 reported (ENV_shrub_pitto1_1107 at 1.45 m).
  extent d       plan (x, y) distance to the nearest MESH VERTEX of that object, in world space, counting only
                 vertices inside the eye band z = walk floor - 0.5 .. + 2.5 m.  A bounding sphere is useless here
                 (a merged rip-rap run or a 15 m eucalyptus crown swallows the walk without a leaf near the
                 floor); the z window is what makes "clearance" mean what the flythrough camera sees.
Exit code 1 if any sample has origin d < GALLERY_KEEPOUT **or** extent d < HALF_CLEAR (1.40 m), so the run fails
loudly in a chain.  Round-9 review, carry 9: only the origin statistic was gated, and the origin is the weaker of
the two - a joined run (the rip-rap, the path verges, a merged shrub belt) has one origin far from the walk and
geometry all over it, so an eye-band intrusion could pass while the printed number showed it.
"""
import bpy, sys, os, math
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
import env_lib as L

ARGS = common.script_args()


def arg(name, default):
    return ARGS[ARGS.index(name) + 1] if name in ARGS else default


BLEND = arg("--blend", "assets/environment.blend")
STEP = float(arg("--step", "2.0"))
SKIP_COLL = ("ENV_terrain", "ENV_water", "ENV_trees")
HALF_CLEAR = 1.40                # half of COL_ROW_SPACING - COLONNADE_D = 2.80 m, the flythrough's clear width
NEAR = 12.0          # bbox pre-filter: only objects whose box comes within this of a walk sample are opened


def main():
    path = BLEND if os.path.isabs(BLEND) else str(common.ROOT / BLEND)
    bpy.ops.wm.open_mainfile(filepath=path)
    print(f"[env_r9_walk] {path}")

    walk = [w for w in L.colonnade_walk_points(step=STEP) if w[3] >= -1e-6]
    wings = L.colonnade_wings()
    for name, _c, R, _t, _s, arc in wings:
        print(f"[env_r9_walk] wing {name:6s} arc {arc:6.1f} m at R {R:.1f}")
    print(f"[env_r9_walk] {len(walk)} walk samples, step {STEP} m; keep-out {L.GALLERY_KEEPOUT} m "
          f"(clear width 2.80 m = +-1.40 m)")

    # candidate objects: near the arc, not ground, LOD1 (or LOD-less) only
    try:
        import arch_params as AP
        z_floor = AP.COLONNADE_GROUND_Z
    except Exception:                                    # noqa: BLE001
        z_floor = -0.6
    z_lo, z_hi = z_floor - 0.5, z_floor + 2.5            # the eye band the flythrough flies (eye at floor + 1.15)
    print(f"[env_r9_walk] eye band z {z_lo:.2f} .. {z_hi:.2f} (colonnade floor {z_floor:.2f})")
    cand = []
    for o in bpy.data.objects:
        if o.type != "MESH":
            continue
        if any(c.name in SKIP_COLL for c in o.users_collection):
            continue
        if "_LOD0" in o.name or "_LOD2" in o.name:
            continue
        cx, cy = o.matrix_world.translation.x, o.matrix_world.translation.y
        corners = [o.matrix_world @ Vector(c) for c in o.bound_box]
        bx0, bx1 = min(c.x for c in corners), max(c.x for c in corners)
        by0, by1 = min(c.y for c in corners), max(c.y for c in corners)
        bz0, bz1 = min(c.z for c in corners), max(c.z for c in corners)
        near_walk = any(bx0 - NEAR <= x <= bx1 + NEAR and by0 - NEAR <= y <= by1 + NEAR for (x, y, _w, _s) in walk)
        if L.gallery_offset(cx, cy, pad=40.0) is None and not near_walk:
            continue
        cand.append((o.name, cx, cy, o, (bx0, bx1, by0, by1, bz0, bz1), near_walk))
    print(f"[env_r9_walk] {len(cand)} candidate ENV objects beside the wings")

    # exact plan distance to the mesh vertices inside the eye band, for the objects whose bbox reaches the walk
    verts = []
    for (nm, _cx, _cy, o, bb, near_walk) in cand:
        if not near_walk or bb[5] < z_lo or bb[4] > z_hi:
            continue
        mw = o.matrix_world
        pts = [(p.x, p.y) for p in (mw @ v.co for v in o.data.vertices) if z_lo <= p.z <= z_hi]
        if pts:
            verts.append((nm, pts))
    print(f"[env_r9_walk] {len(verts)} of them put geometry in the eye band within {NEAR} m of the walk")

    rows = []
    for (x, y, wing, s) in walk:
        b_o = b_e = None
        for (nm, ox, oy, _o, _bb, _nw) in cand:
            d = math.hypot(ox - x, oy - y)
            if b_o is None or d < b_o[0]:
                b_o = (d, nm)
        for (nm, pts) in verts:
            e = min(math.hypot(px - x, py - y) for (px, py) in pts)
            if b_e is None or e < b_e[0]:
                b_e = (e, nm)
        rows.append((wing, s, x, y, b_o or (1e9, "-"), b_e or (1e9, "-")))

    rows_sorted = sorted(rows, key=lambda r: r[4][0])
    print("\n  wing     s      x       y     nearest origin        d_orig   nearest extent        d_ext")
    for (wing, s, x, y, bo, be) in rows_sorted[:12]:
        print(f"  {wing:6s} {s:5.0f} {x:7.1f} {y:7.1f}   {bo[1][:26]:26s} {bo[0]:6.2f}   "
              f"{be[1][:26]:26s} {be[0]:6.2f}")

    bad = [r for r in rows if r[4][0] < L.GALLERY_KEEPOUT]
    bad_ext = [r for r in rows if r[5][0] < HALF_CLEAR]           # carry 9: the eye band is gated too
    inside = [r for r in rows if r[4][0] < HALF_CLEAR]
    worst_o = min(r[4][0] for r in rows)
    worst_e = min(r[5][0] for r in rows)
    print(f"\n[env_r9_walk] SUMMARY  samples {len(rows)}  min origin distance {worst_o:.2f} m  "
          f"min extent distance {worst_e:.2f} m")
    print(f"[env_r9_walk] samples with an ENV object ORIGIN inside the 2.80 m clear width (< {HALF_CLEAR} m): "
          f"{len(inside)}")
    print(f"[env_r9_walk] samples with ENV GEOMETRY in the eye band inside the clear width "
          f"(< {HALF_CLEAR} m): {len(bad_ext)}")
    print(f"[env_r9_walk] samples inside the {L.GALLERY_KEEPOUT} m planting keep-out: {len(bad)}")
    for wing, _c, _R, _t, _s, _a in wings:
        w = [r for r in rows if r[0] == wing]
        if w:
            print(f"[env_r9_walk]   wing {wing:6s}: min origin {min(r[4][0] for r in w):6.2f} m, "
                  f"min extent {min(r[5][0] for r in w):6.2f} m over {len(w)} samples")
    ok = not bad and not bad_ext
    print(f"[env_r9_walk] gates: origin >= {L.GALLERY_KEEPOUT} m ({worst_o:.2f}, "
          f"{'PASS' if not bad else 'FAIL'}), eye-band extent >= {HALF_CLEAR} m ({worst_e:.2f}, "
          f"{'PASS' if not bad_ext else 'FAIL'})")
    print("[env_r9_walk] PASS" if ok else "[env_r9_walk] FAIL")
    if not ok:
        sys.exit(1)


main()
