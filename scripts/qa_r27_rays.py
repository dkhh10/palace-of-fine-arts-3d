"""QA round 27 gate check: ray-cast opening test on the Phase 10 master (CLAUDE.md "Gate checks added 2026-09-10").

    scripts/blender_run.sh 600 -- --background master.blend --python scripts/qa_r27_rays.py

Same classification as scripts/qa_r10_rays.py (first hit beyond the barrel band = PASS-through, on the soffit within MAX_DEV
= PASS-soffit, anything inside the band below the soffit = FAIL-blocker), extended to the stations the brief names:
hero bay 0 (+ cam02 bay 7, whose frame gained the Phase 10 cypresses), cam03 bay 2 (the rotunda face it looks at between
two columns), cam04 all eight inner-ring bays. Plus the cam03 colonnade opening: a fan of rays from the station to the
rotunda through the intercolumniation, listing the first hits (a hit on a non-column colonnade face nearer than the
rotunda = FAIL). CPU only, no render.
"""
import bpy, math, os, sys
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import qa_cameras
import arch_params as P

MAX_DEV = 0.45
R0, R1 = P.ARCH_SPAN / 2, P.INNER_ARCH_SPAN / 2
AP0, AP1 = P.INNER_APOTHEM, P.INNER_WALL_APOTHEM
PAIRS = [("CAM_qa_01_lagoon_hero", 0), ("CAM_qa_02_lagoon_ne_threequarter", 7), ("CAM_qa_03_colonnade_walk", 2)] + \
        [("CAM_qa_04_rotunda_ceiling", k) for k in range(8)]


def bay_frame(k):
    d = P.az_dir(P.FACE_AZ0 + 45 * k)
    n = Vector((d[0], d[1], 0.0)).normalized()
    return n, Vector((-n.y, n.x, 0.0))


def soffit_r(ap):
    t = min(max((ap - AP0) / (AP1 - AP0), 0.0), 1.0)
    return R0 + (R1 - R0) * t


def station(name):
    return Vector(next(s for s in qa_cameras.CAMERAS if s["name"] == name)["loc"])


def march(dg, org, d, n=6):
    pos, hits = org.copy(), []
    while len(hits) < n:
        ok, loc, _nrm, _i, ob, _m = bpy.context.scene.ray_cast(dg, pos, d, distance=400.0)
        if not ok:
            break
        hits.append((ob.name, loc.copy(), (loc - org).length))
        pos = loc + d * 0.02
    return hits


def main():
    dg = bpy.context.evaluated_depsgraph_get()
    fails, n_rays = [], 0
    for cam_name, k in PAIRS:
        n, u = bay_frame(k)
        org = station(cam_name)
        print(f"\n=== {cam_name} -> bay {k} (face az {P.FACE_AZ0 + 45 * k:.1f})")
        for z in range(16, 23):
            tgt = n * ((AP0 + AP1) / 2) + Vector((0, 0, float(z)))
            d = (tgt - org).normalized()
            first, row = None, []
            for obn, loc, dist in march(dg, org, d):
                ap = loc.x * n.x + loc.y * n.y
                r = math.hypot(loc.x * u.x + loc.y * u.y, loc.z - P.ARCH_SPRING_Z)
                inside = (AP1 - 0.3) <= ap <= (AP0 + 0.3)
                if first is None:
                    first = ("PASS-through", obn) if not inside else \
                        (("PASS-soffit", obn) if soffit_r(ap) - r <= MAX_DEV else ("FAIL-blocker", obn))
                row.append(f"{obn}@{dist:.1f}m(ap {ap:+.1f}, r {r:.1f})")
            n_rays += 1
            v, obn = first or ("PASS-clear", "-")
            if v.startswith("FAIL"):
                fails.append((cam_name, k, z, obn))
            print(f"  z={z:>3} {v:12s} first={obn:40s} | " + (" | ".join(row[:3]) if row else "clear (sky)"))
    # cam03 colonnade opening: fan from the station to the rotunda face through the intercolumniation
    spec = next(s for s in qa_cameras.CAMERAS if s["name"] == "CAM_qa_03_colonnade_walk")
    org, tgt0 = Vector(spec["loc"]), Vector(spec["target"])
    rot_dist = org.to_2d().length - P.WALL_CIRCUMRADIUS
    print(f"\n=== cam03 colonnade opening fan (rotunda outer wall ~{rot_dist:.1f} m from the station)")
    for dz in (-6, -3, 0, 3, 6, 10):
        for dl in (-2.0, 0.0, 2.0):
            side = (tgt0 - org).cross(Vector((0, 0, 1))).normalized()
            tgt = tgt0 + Vector((0, 0, dz)) + side * dl
            d = (tgt - org).normalized()
            hits = march(dg, org, d, 3)
            n_rays += 1
            if not hits:
                print(f"  dz={dz:+3d} dl={dl:+.0f}  clear (sky)"); continue
            obn, loc, dist = hits[0]
            bad = dist < rot_dist - 1.0 and obn.startswith("ARCH_") and "column" not in obn and "col_" not in obn
            if bad:
                fails.append(("cam03-fan", dz, dl, obn))
            print(f"  dz={dz:+3d} dl={dl:+.0f}  {'FAIL-near' if bad else 'ok':9s} " +
                  " | ".join(f"{h[0]}@{h[2]:.1f}m z{h[1].z:.1f}" for h in hits))
    print(f"\n[qa_r27_rays] {n_rays} rays, {len(fails)} fails")
    if fails:
        print(f"[qa_r27_rays] FAIL: {fails}")
        sys.exit(1)
    print("[qa_r27_rays] PASS")


main()
