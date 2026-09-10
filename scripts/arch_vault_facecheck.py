"""ARCH r8 acceptance check: every barrel-vault face must follow the soffit, and the bay axis must be clear.

    blender --background <file.blend> --python scripts/arch_vault_facecheck.py -- [--rays] [--quiet]

Background (ARCH r8 brief): build_vault_coffers builds the rib network as a FLAT plate (outline 17.6 x 4.1 m with the
coffer holes) and then maps the VERTICES onto the barrel.  The plate's cap triangles are produced by
mathutils.geometry.tessellate_polygon, which happily emits triangles spanning the whole plate; once the vertices are
bent onto the arc such a triangle becomes a CHORD cutting straight through the space under the vault.  In the v1 hero
the upper half of the main arch was one flat plate 2 m behind the arch face.  The fix is to subdivide the plate along
the arc (arch_lib.bisect_grid) before the mapping, so no face spans more than one small step in s.

Checks, per bay k = 0..7, on ARCH_rotunda_vault_coffers_kk and ARCH_rotunda_vault_kk:
  * radial deviation: for each face centre, t = (apothem - INNER_APOTHEM) / (INNER_WALL_APOTHEM - INNER_APOTHEM) gives
    the local soffit radius r(t) = r0 + (r1 - r0) t; the face's own radius from the springing axis is
    sqrt(x_along^2 + (z - ARCH_SPRING_Z)^2).  r(t) - r_face is how far the face sits BELOW the soffit (into the
    opening).  The rib plate is VAULT_COFFER_DEPTH = 0.38 proud, so the legal maximum is 0.45.
  * face area: no face over 1.0 m2.
Exit 1 if any bay fails either.  --rays adds the cam01 (bay 00) / cam02 (bay 07) axis rays at z 16..22.
"""
import bpy, math, os, sys
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
import arch_params as P

ARGS = common.script_args()
QUIET = "--quiet" in ARGS

MAX_DEV = 0.45          # m below the local soffit radius (the rib plate itself is 0.38 proud)
MAX_AREA = 1.0          # m2

R0, R1 = P.ARCH_SPAN / 2, P.INNER_ARCH_SPAN / 2
AP0, AP1 = P.INNER_APOTHEM, P.INNER_WALL_APOTHEM


def face_dir(k):
    return P.az_dir(P.FACE_AZ0 + 45 * k)


def bay_frame(k):
    n = Vector((face_dir(k)[0], face_dir(k)[1], 0.0)).normalized()
    u = Vector((-n.y, n.x, 0.0))
    return n, u


def check_object(ob, k, dg):
    """(nfaces, worst_dev, n_dev_fail, worst_area, n_area_fail) for one vault object of bay k."""
    n, u = bay_frame(k)
    me = ob.evaluated_get(dg).data
    mw = ob.matrix_world
    worst_dev, worst_area, ndev, nar = -9.9, 0.0, 0, 0
    worst_c = None
    for p in me.polygons:
        c = mw @ p.center
        ap = c.x * n.x + c.y * n.y
        t = (ap - AP0) / (AP1 - AP0)
        if not (-0.05 <= t <= 1.05):
            continue                       # outside the barrel band (nothing should be, but do not judge it here)
        t = min(max(t, 0.0), 1.0)
        r_soffit = R0 + (R1 - R0) * t
        xl = c.x * u.x + c.y * u.y
        dz = c.z - P.ARCH_SPRING_Z
        if dz < -0.6:
            continue                       # below the springing: jamb geometry, not the barrel
        r_face = math.hypot(xl, dz)
        dev = r_soffit - r_face
        if dev > worst_dev:
            worst_dev, worst_c = dev, tuple(round(v, 1) for v in c)
        if dev > MAX_DEV:
            ndev += 1
        a = p.area
        worst_area = max(worst_area, a)
        if a > MAX_AREA:
            nar += 1
    return len(me.polygons), worst_dev, ndev, worst_area, nar, worst_c


def rays(k, label, z_list=range(16, 23)):
    """Cast inward along bay k's axis; list every hit out to the far side of the rotunda."""
    n, _ = bay_frame(k)
    dg = bpy.context.evaluated_depsgraph_get()
    print(f"--- axis rays, bay {k:02d} ({label}) : start at apothem 30 m, direction -n")
    for z in z_list:
        origin = Vector((n.x * 30.0, n.y * 30.0, float(z)))
        d = Vector((-n.x, -n.y, 0.0))
        pos, hits, guard = origin.copy(), [], 0
        while guard < 40:
            guard += 1
            ok, loc, _nrm, _i, ob, _m = bpy.context.scene.ray_cast(dg, pos, d, distance=70.0)
            if not ok:
                break
            trav = (loc - origin).length
            ap = loc.x * n.x + loc.y * n.y
            hits.append(f"{ob.name}@{trav:.1f}m(ap {ap:+.1f})")
            pos = loc + d * 0.02
        print(f"  z={z:>4}: " + (" | ".join(hits[:8]) if hits else "clear"))


def main():
    dg = bpy.context.evaluated_depsgraph_get()
    fails = []
    print("bay | object                     | faces |  worst dev |  n>0.45 | worst area | n>1.0 | worst centre")
    for k in range(8):
        for base in ("vault_coffers", "vault"):
            name = f"ARCH_rotunda_{base}_{k:02d}"
            ob = bpy.data.objects.get(name)
            if ob is None:
                print(f" {k:02d} | {name:<26} | MISSING")
                fails.append(name)
                continue
            nf, dev, ndev, area, nar, wc = check_object(ob, k, dg)
            bad = "FAIL" if (ndev or nar) else "ok"
            print(f" {k:02d} | {name:<26} | {nf:5d} | {dev:10.3f} | {ndev:7d} | {area:10.3f} | {nar:5d} | {wc} {bad}")
            if ndev or nar:
                fails.append(name)
    # report-only: the ceiling rib plate is built the same way (flat plate, vertices pushed onto the sphere)
    ob = bpy.data.objects.get("ARCH_rotunda_ceiling_ribs")
    if ob:
        me = ob.evaluated_get(dg).data
        big = sorted((p.area for p in me.polygons), reverse=True)[:5]
        # the saucer sphere the rib plate is mapped onto (build_ceiling): rib room face hangs COFFER_DEPTH below it
        apo = P.INNER_WALL_APOTHEM - P.INNER_WALL_THICKNESS
        R = (apo ** 2 + P.CEILING_RISE ** 2) / (2 * P.CEILING_RISE)
        cz = P.CEILING_RING_Z + P.CEILING_RISE - R
        drop = 0.0
        for p in me.polygons:
            c = ob.matrix_world @ p.center
            zs = cz + math.sqrt(max(R * R - c.x * c.x - c.y * c.y, 0.0))
            drop = max(drop, zs - c.z)
        print(f"    ceiling_ribs: {len(me.polygons)} faces, largest areas {[round(a, 2) for a in big]}, "
              f"max face-centre drop below the saucer sphere {drop:.3f} m (legal <= COFFER_DEPTH "
              f"{P.COFFER_DEPTH:.2f} + tessellation)")
    if "--rays" in ARGS:
        rays(0, "cam01 hero, lagoon face")
        rays(7, "cam02 three-quarter")
    if fails:
        print(f"FACECHECK FAILED: {sorted(set(fails))}")
        sys.exit(1)
    print("FACECHECK PASSED: all 8 bays within %.2f m of the soffit, no face over %.1f m2" % (MAX_DEV, MAX_AREA))


main()
