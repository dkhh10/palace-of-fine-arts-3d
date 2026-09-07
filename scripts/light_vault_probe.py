"""QA-02-12 diagnostic: does LIGHT_rotunda_vault_bounce actually SEE the barrel-vault soffits? (no render)

A render sweep answers "how much light" only after minutes of GPU. This answers "any light at all" in seconds:
sample points on the vault soffit surface, raycast from each toward each vault light and toward the central disk,
and report which fraction of the light is occluded and at what cosine. If a soffit patch cannot see the emitter,
no amount of energy will fix it and the emitter has to move.

    blender -b --python scripts/light_vault_probe.py -- [--blend master.blend]

Geometry from arch_params (rotunda, 8 faces at azimuth 82 + 45k): the barrel-vault soffit is the annulus between the
inner ring wall (apothem 15.38) and the arch wall's inner face (19.5), springing z 17.5, crown z 23.75.
"""
import bpy, os, sys, math
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common

args = common.script_args()
blend = args[args.index("--blend") + 1] if "--blend" in args else "master.blend"
bpy.ops.wm.open_mainfile(filepath=str(common.ROOT / blend), load_ui=False)
scene = bpy.context.scene
dg = bpy.context.evaluated_depsgraph_get()

FACE_AZ0, N_FACES = 82.0, 8
R_IN, R_OUT = 15.6, 19.3          # radial band of the soffit, just inside the two wall faces
Z_SPRING, Z_CROWN = 17.5, 23.75


def az_dir(az_deg):
    a = math.radians(az_deg)
    return Vector((-math.cos(a), math.sin(a), 0.0))


def cast(origin, target):
    """True if the segment origin->target is clear."""
    d = target - origin
    dist = d.length
    hit, loc, nrm, idx, obj, mat = scene.ray_cast(dg, origin + d.normalized() * 0.05, d.normalized(), distance=dist - 0.05)
    return (not hit), (obj.name if hit else None), ((loc - origin).length if hit else dist)


lights = sorted([o for o in bpy.data.objects if o.name.startswith("LIGHT_rotunda_vault_bounce")], key=lambda o: o.name)
disk = bpy.data.objects.get("LIGHT_rotunda_bounce")
print(f"[vault_probe] {len(lights)} vault lights, central disk: {disk.name if disk else None}")
for o in lights[:2]:
    print(f"[vault_probe]   {o.name} at {tuple(round(v,1) for v in o.location)} size {o.data.size}x{o.data.size_y} "
          f"energy {o.data.energy} spread {math.degrees(getattr(o.data,'spread',0)):.0f} deg")

# sample the soffit of bay 0 and bay 2 (a lagoon-facing bay and a side bay) on a small grid
for k in (0, 2):
    n = az_dir(FACE_AZ0 + 45.0 * k)
    t = Vector((-n.y, n.x, 0.0))
    print(f"\n[vault_probe] --- bay {k} (azimuth {FACE_AZ0 + 45.0*k:.0f}), normal {tuple(round(v,2) for v in n)}")
    for r in (R_IN + 0.6, (R_IN + R_OUT) / 2, R_OUT - 0.6):
        for lat in (-3.0, 0.0, 3.0):
            # the vault is a barrel: at tangential offset `lat` from the bay axis the soffit hangs lower
            half = 12.5 / 2
            z = Z_SPRING + math.sqrt(max(0.0, half ** 2 - lat ** 2)) if abs(lat) < half else Z_SPRING
            p = n * r + t * lat + Vector((0, 0, z))
            # find the real soffit just above/below p by casting straight up from 1 m below
            hit, loc, nrm, idx, obj, mat = scene.ray_cast(dg, p - Vector((0, 0, 4.0)), Vector((0, 0, 1.0)), distance=12.0)
            if not hit:
                print(f"   r {r:5.1f} lat {lat:+4.1f}: no surface overhead (bay is open to the sky here)")
                continue
            surf, nz = loc, nrm
            best = None
            for o in lights:
                clear, blocker, d = cast(surf, o.location)
                cosang = max(0.0, (o.location - surf).normalized().dot(nz))
                if clear and (best is None or cosang > best[1]):
                    best = (o.name, cosang, d)
            dclear, dblock, dd = cast(surf, disk.location) if disk else (False, "n/a", 0)
            dcos = max(0.0, (disk.location - surf).normalized().dot(nz)) if disk else 0.0
            vis = f"{best[0][-2:]} cos {best[1]:.2f} d {best[2]:.1f} m" if best else "NONE VISIBLE"
            print(f"   r {r:5.1f} lat {lat:+4.1f} -> soffit z {surf.z:5.1f} n {tuple(round(v,2) for v in nz)} | "
                  f"vault: {vis} | disk: {'clear' if dclear else 'BLOCKED by ' + str(dblock)} cos {dcos:.2f} d {dd:.1f} m")

print("\n[vault_probe] done")
