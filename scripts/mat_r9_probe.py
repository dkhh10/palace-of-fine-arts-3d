"""What is inside a hero box, and what projection weight does it get?  (raycast, no render)

    blender -b --python scripts/mat_r9_probe.py -- [--box 1110,225,1150,260] [--n 12]

Fires camera rays through a grid inside a 1920x1080 hero box, and for every hit reports the object, the material,
and every factor of `PFA_photo`'s weight evaluated by hand: the facing angle to the projector, the world z and
radius gates, and the mask pack sampled at the hit's own projector UV.  Written because round 9's shaded-attic box
did not move when the facing plateau was widened, and a render cannot say which gate is the binding one.
"""
import bpy, sys, os, math
from mathutils import Vector, Euler
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common

args = common.script_args()
BOX = [int(v) for v in (args[args.index("--box") + 1] if "--box" in args else "1110,225,1150,260").split(",")]
N = int(args[args.index("--n") + 1]) if "--n" in args else 12
RES = (1920, 1080)
PLOC, PTARGET = Vector((-14.1, 100.0, 1.6)), (0.0, 0.0, 1.6)
LENS, SENSOR, SHIFT_Y = 20.0, 36.0, 0.06
FACE_LO, FACE_HI = math.cos(math.radians(80.0)), math.cos(math.radians(58.0))
PZ = (24.0, 26.0, 45.5, 47.5)
PR = 34.0

bpy.ops.wm.open_mainfile(filepath=str(common.ROOT / "master.blend"), load_ui=False)
scene = bpy.context.scene
cam = bpy.data.objects["CAM_qa_01_lagoon_hero"]
scene.camera = cam
scene.render.resolution_x, scene.render.resolution_y = RES
bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get()

M = Euler(common.lookat_rotation(tuple(PLOC), PTARGET)).to_matrix()
right, up, fwd = M.col[0], M.col[1], -M.col[2]
hx = SENSOR / (2.0 * LENS)
hy = hx * RES[1] / RES[0]
dyv = SHIFT_Y * SENSOR / LENS
mask_path = common.ROOT / "assets" / "textures" / "projection" / "PFA_photo_mask.png"
# Blender's bundled python has no PIL; the mask is read through bpy.data.images (bottom-up RGBA float).
_mi = bpy.data.images.load(str(mask_path))
mask = np.array(_mi.pixels[:], dtype=np.float64).reshape(_mi.size[1], _mi.size[0], 4)[::-1, :, :3]

cw = cam.matrix_world
cd = cam.data
chx = cd.sensor_width / (2.0 * cd.lens)
chy = chx * RES[1] / RES[0]
cdy = cd.shift_y * cd.sensor_width / cd.lens


def ramp(x, lo, hi):
    return max(0.0, min(1.0, (x - lo) / (hi - lo)))


def smoothstep(x):
    return x * x * (3 - 2 * x)


rows = {}
for iy in range(N):
    for ix in range(N):
        px = BOX[0] + (BOX[2] - BOX[0]) * (ix + 0.5) / N
        py = BOX[1] + (BOX[3] - BOX[1]) * (iy + 0.5) / N
        X = (px / RES[0] - 0.5) * 2 * chx
        Y = (0.5 - py / RES[1]) * 2 * chy + cdy
        d = (cw.to_3x3() @ Vector((X, Y, -1.0))).normalized()
        hit, loc, nrm, idx, obj, _ = scene.ray_cast(dg, cw.translation, d)
        if not hit:
            rows.setdefault(("MISS", ""), []).append(None)
            continue
        mats = obj.data.materials if obj.type == "MESH" else []
        mname = mats[min(idx if idx < len(mats) else 0, len(mats) - 1)].name if mats else "-"
        to_cam = (PLOC - loc).normalized()
        ndot = nrm.normalized().dot(to_cam)
        facing = smoothstep(ramp(ndot, FACE_LO, FACE_HI))
        z, rad = loc.z, math.hypot(loc.x, loc.y)
        zg = ramp(z, PZ[0], PZ[1]) * (1.0 - ramp(z, PZ[2], PZ[3]))
        rg = 1.0 - ramp(rad, PR, PR + 3.0)
        dvec = loc - PLOC
        depth = max(dvec.dot(fwd), 1.0)
        u = (dvec.dot(right) / depth) / (2 * hx) + 0.5
        v = (dvec.dot(up) / depth) / (2 * hy) + (hy - dyv) / (2 * hy)
        if 0.0 <= u < 1.0 and 0.0 <= v < 1.0:
            mr = mask[int((1 - v) * mask.shape[0]), int(u * mask.shape[1])]
            mw = float(mr[0] * mr[1] * mr[2])
        else:
            mw = 0.0
        key = (obj.name.split(".")[0], mname)
        rows.setdefault(key, []).append((math.degrees(math.acos(max(-1, min(1, ndot)))), facing, z, rad, zg, rg, mw))

print(f"[probe] box {BOX} {N * N} rays, facing ramp {math.degrees(math.acos(FACE_HI)):.0f}-"
      f"{math.degrees(math.acos(FACE_LO)):.0f} deg")
for (o, mname), v in sorted(rows.items(), key=lambda kv: -len(kv[1])):
    good = [x for x in v if x]
    if not good:
        print(f"  {o:44s} {mname:26s} {len(v):4d} rays  (no hit)")
        continue
    a = np.array(good)
    print(f"  {o:44s} {mname:26s} {len(v):4d} rays  angle {a[:, 0].mean():5.1f} deg  facing {a[:, 1].mean():.3f}  "
          f"z {a[:, 2].mean():5.1f}  rad {a[:, 3].mean():5.1f}  zgate {a[:, 4].mean():.3f}  rgate {a[:, 5].mean():.3f}  "
          f"mask {a[:, 6].mean():.3f}  -> weight {(a[:, 1] * a[:, 4] * a[:, 5] * a[:, 6]).mean():.3f}")
