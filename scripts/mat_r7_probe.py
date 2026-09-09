"""Which material is actually under each QA box?  Ray-cast the hero camera through the box's pixels.

    blender -b --python scripts/mat_r7_probe.py -- [--boxes attic_sunlit,entablature]

Round 7 needed this because two library changes aimed at QA's attic box (a 1.7x run-off amplitude, then a 3.6x
run-off tile on the ornament material) moved the box's column-mean spread by -0.3 and -0.4 lum.  A shader change
that measures as nothing is either compressed by the view transform or landing on a surface that is not there;
this separates the two.  Prints, per box, the share of rays that hit each material and the mean hit distance.
"""
import bpy, sys, os
from collections import Counter
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common

args = common.script_args()
BOXES = {
    "attic_sunlit":   (900, 222, 1020, 256),
    "attic_string":   (880, 214, 1040, 222),
    "entablature":    (900, 262, 1020, 296),
    "attic_shaded":   (1110, 225, 1150, 260),
    "shore_band":     (700, 600, 1200, 740),
    "water_refl":     (900, 760, 1020, 840),
    "columns":        (680, 280, 1240, 470),
}
WANT = [b for b in (args[args.index("--boxes") + 1].split(",") if "--boxes" in args else BOXES)]
RES = (1920, 1080)

bpy.ops.wm.open_mainfile(filepath=str(common.ROOT / "master.blend"), load_ui=False)
scene = bpy.context.scene
dg = bpy.context.evaluated_depsgraph_get()
cam = bpy.data.objects["CAM_qa_01_lagoon_hero"]
scene.camera = cam
scene.render.resolution_x, scene.render.resolution_y = RES
bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get()

# camera ray for a pixel: view frame in camera space, then to world
frame = cam.data.view_frame(scene=scene)
tl, bl, br, tr = frame[3], frame[2], frame[1], frame[0]
M = cam.matrix_world
origin = M.translation


def ray(px, py):
    u = (px + 0.5) / RES[0]
    v = (py + 0.5) / RES[1]
    top = tl.lerp(tr, u)
    bot = bl.lerp(br, u)
    p = top.lerp(bot, v)
    return (M @ p - origin).normalized()


for name in WANT:
    x0, y0, x1, y1 = BOXES[name]
    hits, dists, miss = Counter(), [], 0
    nx = max(1, (x1 - x0) // 6)
    ny = max(1, (y1 - y0) // 4)
    n = 0
    for i in range(nx):
        for j in range(ny):
            px = x0 + (i + 0.5) * (x1 - x0) / nx
            py = y0 + (j + 0.5) * (y1 - y0) / ny
            ok, loc, nrm, idx, ob, _ = scene.ray_cast(dg, origin, ray(px, py))
            n += 1
            if not ok:
                miss += 1
                continue
            m = None
            try:
                me = ob.evaluated_get(dg).data
                if me.polygons and idx < len(me.polygons):
                    si = me.polygons[idx].material_index
                    if si < len(ob.material_slots) and ob.material_slots[si].material:
                        m = ob.material_slots[si].material.name
            except Exception:
                pass
            if m is None and ob.material_slots and ob.material_slots[0].material:
                m = ob.material_slots[0].material.name
            hits[m or "<none>"] += 1
            dists.append((loc - origin).length)
    print(f"\n[probe] {name} {BOXES[name]}  {n} rays, {miss} miss, mean distance "
          f"{(sum(dists) / len(dists) if dists else 0):.1f} m")
    for k, v in hits.most_common(8):
        print(f"[probe]   {v * 100.0 / max(1, n):5.1f} %  {k}")
