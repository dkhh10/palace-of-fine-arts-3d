"""Round-8 water blocker: what does the hero's water MIRROR actually see, as a function of ripple slope?

    blender -b --python scripts/mat_r8_probe.py -- [--boxes water_refl,near_water]

Render-free.  QA-06-3's blocker is the reflection column box 900 760 1020 840: R-B +2.5 against ref 169's +69.0.
Lighting r14 (docs/lighting_notes.md 24.3) isolated the box into two terms by switching the glossy sky off --
building+murk 52.1 lum at R-B +51.6, plus reflected sky 51.7 lum at R-B -49.5 -- and handed materials the
arithmetic: the BUILDING half has to come up 2.3x with the sky half held.  That can happen in only two ways:
the mirror rays that currently reach the sky are re-aimed onto the stone, or the stone they already reach is
returned more efficiently.  Which one is available is a geometry question, and geometry can be raycast instead
of rendered.

Per box this casts the camera ray to the water, then the mirror ray for a fan of ripple facet slopes (pitch =
tilt in the camera's view plane, roll = across it), and reports where each mirror ray lands: SKY, an ARCH_*
surface (and at what height above the water), or the environment.  Each stone hit is additionally tested against
the sun direction for occlusion, so the report separates "hits the building" from "hits the SUNLIT building" --
the sunlit share is what carries R-B +69.  It also follows the transmitted ray downward to show whether the
lagoon bed is under the box or whether that 18 % of the surface escapes to the world.
"""
import bpy, sys, os, math
from collections import Counter
from mathutils import Vector, Matrix

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common

args = common.script_args()


def arg(name, default=None):
    if name in args:
        i = args.index(name)
        return args[i + 1] if i + 1 < len(args) else True
    return default


BOXES = {
    "water_refl": (900, 760, 1020, 840),
    "near_water": (1150, 1000, 1450, 1050),
    "ripples":    (1100, 960, 1500, 1060),
}
WANT = str(arg("--boxes", "water_refl,near_water")).split(",")
RES = (1920, 1080)
PITCHES = [-12, -8, -5, -3, -1.5, 0, 1.5, 3, 5, 8, 12]
ROLLS = [0, 3, 8]

bpy.ops.wm.open_mainfile(filepath=str(common.ROOT / "master.blend"), load_ui=False)
scene = bpy.context.scene
cam = bpy.data.objects["CAM_qa_01_lagoon_hero"]
scene.camera = cam
scene.render.resolution_x, scene.render.resolution_y = RES
bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get()
print(f"[probe] master: {len(bpy.data.objects)} objects; cam at {tuple(round(v,2) for v in cam.matrix_world.translation)}")

sun = bpy.data.objects.get("LIGHT_sun")
sun_dir = None
if sun is not None:
    sun_dir = -(sun.matrix_world.to_3x3() @ Vector((0.0, 0.0, -1.0))).normalized()  # toward the sun
    el = math.degrees(math.asin(max(-1.0, min(1.0, sun_dir.z))))
    print(f"[probe] sun toward {tuple(round(v,3) for v in sun_dir)} (elevation {el:.1f} deg)")

frame = cam.data.view_frame(scene=scene)
tl, bl, br, tr = frame[3], frame[2], frame[1], frame[0]
M = cam.matrix_world
origin = M.translation


def ray(px, py):
    u, v = (px + 0.5) / RES[0], (py + 0.5) / RES[1]
    p = tl.lerp(tr, u).lerp(bl.lerp(br, u), v)
    return (M @ p - origin).normalized()


def cast(o, d, far=4000.0):
    hit, loc, nrm, idx, obj, mat = scene.ray_cast(dg, o + d * 1e-3, d, distance=far)
    return hit, loc, obj


def label(obj):
    if obj is None:
        return "SKY"
    n = obj.name
    for pre in ("ARCH_", "ORN_", "ENV_", "LIGHT_"):
        if n.startswith(pre):
            return pre[:-1]
    return "other"


for name in WANT:
    x0, y0, x1, y1 = BOXES[name]
    pts, dirs = [], []
    for py in range(y0, y1, max(1, (y1 - y0) // 5)):
        for px in range(x0, x1, max(1, (x1 - x0) // 8)):
            d = ray(px, py)
            hit, loc, obj = cast(origin, d)
            if hit and obj is not None and obj.active_material and obj.active_material.name.startswith("MAT_water"):
                pts.append(loc)
                dirs.append(d)
    if not pts:
        print(f"[probe] {name}: no water pixels")
        continue
    dist = sum((p - origin).length for p in pts) / len(pts)
    inc = sum(math.degrees(math.acos(min(1.0, abs(d.z)))) for d in dirs) / len(dirs)
    print(f"\n[probe] === {name} {BOXES[name]} : {len(pts)} water samples, mean {dist:.1f} m, "
          f"mean incidence {inc:.1f} deg from normal ===")
    print(f"[probe] {'pitch':>6} {'roll':>5} {'SKY%':>6} {'ARCH%':>6} {'ORN%':>6} {'ENV%':>6} "
          f"{'sunlit%':>8} {'meanZ':>7} {'rayEl':>6}")
    for roll in ROLLS:
        for pitch in PITCHES:
            c, names = Counter(), Counter()
            zs, sunlit, stone, els = [], 0, 0, []
            for p, d in zip(pts, dirs):
                # facet normal: pitch tilts in the vertical plane containing the view ray, roll across it
                fwd = Vector((d.x, d.y, 0.0)).normalized()
                side = fwd.cross(Vector((0, 0, 1.0))).normalized()
                n = Matrix.Rotation(math.radians(roll), 3, fwd) @ (
                    Matrix.Rotation(math.radians(pitch), 3, side) @ Vector((0, 0, 1.0)))
                n.normalize()
                r = (d - 2.0 * d.dot(n) * n).normalized()
                els.append(math.degrees(math.asin(max(-1.0, min(1.0, r.z)))))
                hit, loc, obj = cast(p, r)
                lb = label(obj)
                c[lb] += 1
                names[obj.name if obj is not None else "SKY"] += 1
                if hit and lb in ("ARCH", "ORN"):
                    stone += 1
                    zs.append(loc.z)
                    if sun_dir is not None:
                        sh, _, _ = cast(loc, sun_dir)
                        if not sh:
                            sunlit += 1
            n_t = len(pts)
            mz = (sum(zs) / len(zs)) if zs else float("nan")
            if roll == 0 and pitch in (0.0, 3.0, 5.0, 8.0):
                print(f"[probe]   names p{pitch:+.0f}: " + ", ".join(f"{k}={v}" for k, v in names.most_common(6)))
            print(f"[probe] {pitch:6.1f} {roll:5.1f} {100*c['SKY']/n_t:6.1f} {100*c['ARCH']/n_t:6.1f} "
                  f"{100*c['ORN']/n_t:6.1f} {100*c['ENV']/n_t:6.1f} {100*sunlit/n_t:8.1f} {mz:7.2f} "
                  f"{sum(els)/len(els):6.1f}")
    # transmitted ray: does anything catch it, or does it escape to the world?
    c = Counter()
    for p, d in zip(pts, dirs):
        n = Vector((0, 0, 1.0))
        cosi = -d.dot(n)
        eta = 1.0 / 1.333
        k = 1.0 - eta * eta * (1.0 - cosi * cosi)
        if k < 0:
            c["TIR"] += 1
            continue
        r = (eta * d + (eta * cosi - math.sqrt(k)) * n).normalized()
        hit, loc, obj = cast(p, r)
        c[label(obj) if hit else "SKY"] += 1
    print(f"[probe] transmitted ray (IOR 1.333): {dict(c)}")

print("[probe] done")
