"""Round-17 item 2, step 1: WHY is the colonnade gallery black in CYCLES, and where would a fill have to sit?

No render. Opens master.blend read-only, and answers three questions with numbers:

 1. **Is it occlusion or is it the light?** Cosine-weighted sky visibility, measured by ray-casting the hemisphere
    of the surface normal at the point ARCH r8 named -- the camera-facing side of
    `ARCH_colonnade_south_column_028` -- and at the walk under it, against the same measurement on a surface the
    rig already lands (the hero's shaded north attic). A shaded surface that sees 30 % of the sky and reads 3 lum
    has a light problem; one that sees 2 % has a geometry problem and belongs to ARCH.
 2. **What is overhead?** A straight-up ray from the walk: the first hit names the roof (solid entablature soffit,
    pergola beam, or nothing at all).
 3. **Where does a gallery fill go?** Both colonnade wings are an arc (arch_params: centre COL_ARC_CENTER,
    radius COL_ARC_R, two rows COL_ROW_SPACING apart). The script fits the two row radii and the arc span from
    the actual column origins on the master, so the emitter ring is placed on the geometry that exists rather
    than on the parameters that were meant to build it.

    scripts/blender_run.sh 600 -- --background --python scripts/light_r17_gallery.py -- --blend master.blend
"""
import bpy, os, sys, math, random
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common

args = common.script_args()


def arg(name, default):
    return args[args.index(name) + 1] if name in args else default


BLEND = arg("--blend", str(common.ROOT / "master.blend"))
N_RAYS = int(arg("--rays", "512"))
bpy.ops.wm.open_mainfile(filepath=BLEND, load_ui=False)
scene = bpy.context.scene
# ARCH r8's gotcha: the saved master is at viewport LOD1, so every _LOD0 object carries a stale identity matrix
# until the render LOD is made visible and the depsgraph updated. Every world-space number below depends on it.
common.set_lod(viewport=0, render=0)
bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get()
print(f"[r17gal] {BLEND}: {len(scene.objects)} objects, LOD0 visible", flush=True)


def hemisphere(normal, n):
    """Cosine-weighted directions about `normal` (Malley), deterministic."""
    rng = random.Random(12345)
    nz = Vector(normal).normalized()
    a = Vector((0.0, 0.0, 1.0)) if abs(nz.z) < 0.9 else Vector((1.0, 0.0, 0.0))
    nx = nz.cross(a).normalized()
    ny = nz.cross(nx)
    out = []
    for _ in range(n):
        r, phi = math.sqrt(rng.random()), 2.0 * math.pi * rng.random()
        out.append((nx * (r * math.cos(phi)) + ny * (r * math.sin(phi)) + nz * math.sqrt(max(0.0, 1 - r * r))).normalized())
    return out


def sky_fraction(origin, normal, label, eps=0.02):
    o = Vector(origin) + Vector(normal).normalized() * eps
    hits, first = 0, {}
    for d in hemisphere(normal, N_RAYS):
        ok, loc, nrm, idx, obj, _ = scene.ray_cast(dg, o, d, distance=400.0)
        if ok:
            hits += 1
            k = obj.name.rsplit("_LOD", 1)[0]
            first[k] = first.get(k, 0) + 1
    frac = 1.0 - hits / float(N_RAYS)
    top = sorted(first.items(), key=lambda kv: -kv[1])[:4]
    print(f"[r17gal] {label:34s} cosine sky visibility {100*frac:5.1f} %   "
          f"blockers: {', '.join(f'{k} {100*v/N_RAYS:.0f}%' for k, v in top)}", flush=True)
    return frac


def straight_up(origin, label):
    ok, loc, nrm, idx, obj, _ = scene.ray_cast(dg, Vector(origin), Vector((0, 0, 1)), distance=200.0)
    if ok:
        print(f"[r17gal] {label:34s} straight up: {obj.name} at z {loc.z:.2f} "
              f"({loc.z - origin[2]:.2f} m above)", flush=True)
    else:
        print(f"[r17gal] {label:34s} straight up: OPEN SKY", flush=True)


# --------------------------------------------------------------------- 1 + 2: the near column and its walk
cam = bpy.data.objects["CAM_qa_03_colonnade_walk"]
col = bpy.data.objects.get("ARCH_colonnade_south_column_028") or bpy.data.objects.get("ARCH_colonnade_south_column_028_LOD0")
C = Vector(col.matrix_world.translation)
K = Vector(cam.matrix_world.translation)
print(f"[r17gal] cam03 at ({K.x:.2f}, {K.y:.2f}, {K.z:.2f}); column 028 at ({C.x:.2f}, {C.y:.2f}, {C.z:.2f})", flush=True)
to_cam = Vector((K.x - C.x, K.y - C.y, 0.0)).normalized()
R_SHAFT = 0.80
p_shaft = Vector((C.x + to_cam.x * R_SHAFT, C.y + to_cam.y * R_SHAFT, C.z + 5.0))
sky_fraction(p_shaft, to_cam, "column 028 camera-facing shaft")
p_walk = Vector(((C.x + K.x) / 2.0, (C.y + K.y) / 2.0, C.z + 0.05))
sky_fraction(p_walk, Vector((0, 0, 1)), "gallery walk between them (up)")
straight_up(p_walk, "gallery walk")
straight_up((C.x + to_cam.x * 1.2, C.y + to_cam.y * 1.2, C.z + 5.0), "1.2 m off the shaft")
# the control: the hero's shaded north attic, a surface the round-16 rig lands inside its window
sky_fraction((-14.0, 12.0, 27.0), Vector((-0.5, 0.86, 0.0)), "hero shaded attic (control)")

# --------------------------------------------------------------------- 3: where the gallery fill goes
CEN = Vector((-11.2, 84.7, 0.0))
for wing in ("south", "north"):
    cols = [o for o in scene.objects if o.name.startswith(f"ARCH_colonnade_{wing}_column_") and o.name.endswith("_LOD0")]
    if not cols:
        cols = [o for o in scene.objects if o.name.startswith(f"ARCH_colonnade_{wing}_column_")]
    rs, angs, zs = [], [], []
    for o in cols:
        p = o.matrix_world.translation
        v = Vector((p.x - CEN.x, p.y - CEN.y))
        rs.append(v.length)
        angs.append(math.degrees(math.atan2(v.y, v.x)))
        zs.append(p.z)
    if not rs:
        continue
    inner = [r for r in rs if r < (min(rs) + max(rs)) / 2.0]
    outer = [r for r in rs if r >= (min(rs) + max(rs)) / 2.0]
    print(f"[r17gal] {wing} wing: {len(cols)} columns, base z {min(zs):.2f}, "
          f"row radii {sum(inner)/max(1,len(inner)):.2f} ({len(inner)}) and {sum(outer)/max(1,len(outer)):.2f} "
          f"({len(outer)}), arc {min(angs):.1f}..{max(angs):.1f} deg "
          f"= {math.radians(max(angs)-min(angs))*sum(rs)/len(rs):.1f} m", flush=True)

print("[r17gal] done", flush=True)
