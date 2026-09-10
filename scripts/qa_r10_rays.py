"""QA round 10 gate check: ray-cast opening test from the real camera stations (CLAUDE.md "Gate checks added 2026-09-10").

    scripts/blender_run.sh 600 -- --background master.blend --python scripts/qa_r10_rays.py

For each (camera, bay) pair the ray starts at the camera station (from scripts/qa_cameras.py, by name) and is aimed at
the point on the bay axis (lateral 0, apothem = mid-barrel) at z = 16..22.  Every hit along that ray is listed with the
distance, the apothem coordinate (ap) and the radius from the springing axis.  PASS for a z means the first hit is
either beyond the barrel band (the far side of the rotunda / sky seen through the opening) or the vault soffit itself,
i.e. its radius from the springing axis is within MAX_DEV of the local soffit radius.  A near-vault / rib-plate /
archivolt chord inside the opening is a FAIL: it sits well below the soffit radius.
"""
import bpy, math, os, sys
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
import qa_cameras
import arch_params as P

MAX_DEV = 0.45          # m below the local soffit radius (the rib plate is 0.38 proud)
R0, R1 = P.ARCH_SPAN / 2, P.INNER_ARCH_SPAN / 2
AP0, AP1 = P.INNER_APOTHEM, P.INNER_WALL_APOTHEM

PAIRS = [("CAM_qa_01_lagoon_hero", 0), ("CAM_qa_02_lagoon_ne_threequarter", 7)]


def bay_frame(k):
    d = P.az_dir(P.FACE_AZ0 + 45 * k)
    n = Vector((d[0], d[1], 0.0)).normalized()
    return n, Vector((-n.y, n.x, 0.0))


def soffit_r(ap):
    t = min(max((ap - AP0) / (AP1 - AP0), 0.0), 1.0)
    return R0 + (R1 - R0) * t


def station(name):
    spec = next(s for s in qa_cameras.CAMERAS if s["name"] == name)
    return Vector(spec["loc"])


def main():
    dg = bpy.context.evaluated_depsgraph_get()
    fails = []
    for cam_name, k in PAIRS:
        n, u = bay_frame(k)
        org = station(cam_name)
        print(f"\n=== {cam_name} -> bay {k:02d} (face az {P.FACE_AZ0 + 45 * k:.1f}); station "
              f"{tuple(round(v, 2) for v in org)}; barrel band ap {AP1:.2f}..{AP0:.2f}, soffit r {R1:.2f}..{R0:.2f}")
        for z in range(16, 23):
            tgt = n * ((AP0 + AP1) / 2) + Vector((0, 0, float(z)))
            d = (tgt - org).normalized()
            pos, hits, first_ok, guard = org.copy(), [], None, 0
            while guard < 40:
                guard += 1
                ok, loc, _nrm, _i, ob, _m = bpy.context.scene.ray_cast(dg, pos, d, distance=400.0)
                if not ok:
                    break
                ap = loc.x * n.x + loc.y * n.y
                r = math.hypot(loc.x * u.x + loc.y * u.y, loc.z - P.ARCH_SPRING_Z)
                inside = (AP1 - 0.3) <= ap <= (AP0 + 0.3)
                tag = ""
                if first_ok is None:
                    if not inside:
                        first_ok = ("PASS-through", ob.name)
                    elif soffit_r(ap) - r <= MAX_DEV:
                        first_ok = ("PASS-soffit", ob.name)
                    else:
                        first_ok = ("FAIL-blocker", ob.name)
                        tag = f" <== BLOCKER dev {soffit_r(ap) - r:+.2f} m below soffit"
                hits.append(f"{ob.name}@{(loc - org).length:.1f}m(ap {ap:+.1f}, r {r:.1f}){tag}")
                pos = loc + d * 0.02
                if len(hits) >= 6:
                    break
            verdict, obn = first_ok if first_ok else ("PASS-clear", "-")
            if verdict.startswith("FAIL"):
                fails.append((cam_name, z, obn))
            print(f"  z={z:>3} {verdict:12s} first={obn:34s} | " + (" | ".join(hits[:4]) if hits else "clear (sky)"))
    if fails:
        print(f"\n[qa_r10_rays] FAIL: {fails}")
        sys.exit(1)
    print("\n[qa_r10_rays] PASS: every ray's first hit is the far side of the opening or the soffit at its radius")


main()
