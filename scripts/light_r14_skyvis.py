"""Round-14 item 3 (QA-06-7): is cam03's outer, lagoon-side colonnade row OCCLUDED from the sky, or reachable?

Round 12 answered the same question for the round-05 near-shaft box by ray-cast and the answer decided the round
(decisions.md 2026-09-09: "no owner tunes for the old box"). QA-06-7 names a NEW box -- 880 120 1200 600, the outer
row -- at 0.066 of the sunlit rotunda, and the fix is only worth attempting if that box can see the sky at all.

Method, per box: shoot a sub-sampled grid of CAMERA rays through the box, ray_cast the master to find what each one
hits, then from each hit point shoot a cosine-weighted hemisphere about the surface normal and count the rays that
escape (no hit within MAX_RAY). That is the box's own sky view factor, measured through the camera, so it is the
same pixels QA measures. The anti-sun half is counted separately, because the round-12 tint only reaches shaded
stone through it.

    scripts/blender_run.sh 1800 -- --background --python scripts/light_r14_skyvis.py -- --step 6 --rays 64
"""
import bpy, os, sys, math, time
from pathlib import Path
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
import light_build as lb
import light_r14_measure as m14

args = common.script_args()
MAX_RAY = 300.0
EPS = 0.01


def arg(name, default):
    return type(default)(args[args.index(name) + 1]) if name in args else default


STEP = arg("--step", 6)         # sample every STEP-th pixel in x and y inside the box
RAYS = arg("--rays", 64)
BLEND = args[args.index("--blend") + 1] if "--blend" in args else str(common.ROOT / "master.blend")
CAM = args[args.index("--cam") + 1] if "--cam" in args else "CAM_qa_03_colonnade_walk"
CAMID = args[args.index("--camid") + 1] if "--camid" in args else "03"


def hemi(n, k):
    """k cosine-weighted directions about the unit normal n (concentric-ish: a Fibonacci spiral in cos-space)."""
    up = Vector((0.0, 0.0, 1.0)) if abs(n.z) < 0.9 else Vector((1.0, 0.0, 0.0))
    t = n.cross(up).normalized()
    b = n.cross(t).normalized()
    ga = math.pi * (3.0 - math.sqrt(5.0))
    out = []
    for i in range(k):
        # cosine weighting: sin^2(theta) uniform in [0, 1)
        u = (i + 0.5) / k
        sin_t = math.sqrt(u)
        cos_t = math.sqrt(max(0.0, 1.0 - u))
        phi = i * ga
        out.append((t * (sin_t * math.cos(phi)) + b * (sin_t * math.sin(phi)) + n * cos_t).normalized())
    return out


bpy.ops.wm.open_mainfile(filepath=BLEND, load_ui=False)
scene = bpy.context.scene
common.set_lod(viewport=1, render=0)
bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get()
cam = bpy.data.objects[CAM]
scene.camera = cam
W, H = m14.BOXES[CAMID]["size"]
scene.render.resolution_x, scene.render.resolution_y = W, H

AZ, EL, _ = lb.solar_position("morning")
SUN = common.sun_direction(AZ, EL)
print(f"[skyvis] {Path(BLEND).name}: {len(scene.objects)} objects, cam {CAM}, {W}x{H}, "
      f"step {STEP}, {RAYS} hemisphere rays/point, sun az {AZ:.1f} el {EL:.1f}", flush=True)

mw = cam.matrix_world
origin = mw.translation
# camera frame in world space, at unit distance along -Z
frame = [mw @ v for v in cam.data.view_frame(scene=scene)]   # top-right, bottom-right, bottom-left, top-left
tr, br, bl, tl = frame


def ray_dir(px, py):
    u, v = (px + 0.5) / W, (py + 0.5) / H          # v = 0 at the TOP row (image coords)
    top = tl.lerp(tr, u)
    bot = bl.lerp(br, u)
    return (top.lerp(bot, v) - origin).normalized()


ROWS = {}
for name, (x0, y0, x1, y1) in m14.BOXES[CAMID]["boxes"].items():
    t0 = time.time()
    n_hit = n_miss = 0
    vis, vis_as, lam = [], [], []
    names = {}
    for py in range(y0, y1, STEP):
        for px in range(x0, x1, STEP):
            d = ray_dir(px, py)
            ok, loc, nor, idx, ob, _ = scene.ray_cast(dg, origin, d, distance=MAX_RAY)
            if not ok:
                n_miss += 1
                continue
            n_hit += 1
            names[ob.name.rsplit("_LOD", 1)[0]] = names.get(ob.name.rsplit("_LOD", 1)[0], 0) + 1
            if nor.dot(d) > 0:
                nor = -nor
            p = loc + nor * EPS
            free = free_as = 0
            wsum = was = 0.0
            for hd in hemi(nor, RAYS):
                hit, *_ = scene.ray_cast(dg, p, hd, distance=MAX_RAY)
                if not hit:
                    free += 1
                    if hd.dot(SUN) < 0.0:
                        free_as += 1
                if hd.dot(SUN) < 0.0:
                    was += 1
            vis.append(free / RAYS)
            vis_as.append(free_as / max(1, was))
    if not vis:
        print(f"  {name:16s} no geometry hit in the box ({n_miss} camera rays reached the sky)")
        continue
    top = sorted(names.items(), key=lambda kv: -kv[1])[:3]
    ROWS[name] = dict(vis=sum(vis) / len(vis), vis_as=sum(vis_as) / len(vis_as), n=len(vis),
                      sky_px=n_miss / max(1, n_hit + n_miss))
    print(f"  {name:16s} n {len(vis):5d}  sky view factor {ROWS[name]['vis']:.4f}  "
          f"anti-sun half {ROWS[name]['vis_as']:.4f}  camera rays that miss all geometry "
          f"{100*ROWS[name]['sky_px']:5.1f}%  ({time.time()-t0:.0f}s)  hits: "
          + ", ".join(f"{k}x{v}" for k, v in top), flush=True)

print("\n[skyvis] reading: a box whose sky view factor is a few 1e-3 cannot be lit by ANY sky knob; one at 1e-1 can.")
print("[skyvis] done", flush=True)
