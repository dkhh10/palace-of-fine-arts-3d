"""ARCH r8 item 3: what does cam03 actually see of its nearest colonnade column?

    blender --background master.blend --python scripts/arch_r8_cam03.py -- [--res 1280x720]

Reports, for the columns nearest CAM_qa_03_colonnade_walk: distance, which LOD is render-visible, the shaft mesh's
flute signature (min/max radius round the shaft at mid height -> flute depth in mm and in px at that distance), the
projected pixel width of the shaft, and whether the capital socket for that column carries a live ORN instance.
"""
import bpy, math, os, sys
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common

ARGS = common.script_args()
RES = ARGS[ARGS.index("--res") + 1] if "--res" in ARGS else "1280x720"
RX, RY = (int(v) for v in RES.split("x"))

# NOTE: hidden objects keep a STALE matrix_world in a background file (the saved master has viewport=LOD1, so every
# LOD0 object reads matrix_world = identity until the view layer is updated with them visible). Show the render LOD
# in the viewport too and force the update, or every LOD0 column looks like it sits at the world origin.
common.set_lod(viewport=0, render=0)
bpy.context.view_layer.update()
scene = bpy.context.scene
cam = bpy.data.objects["CAM_qa_03_colonnade_walk"]
scene.camera = cam
scene.render.resolution_x, scene.render.resolution_y = RX, RY
print(f"cam03 at {tuple(round(v, 2) for v in cam.location)} lens {cam.data.lens} mm, {RX}x{RY}")


def visible(ob):
    return not ob.hide_render and all(not c.hide_render for c in ob.users_collection)


def shaft_stats(ob):
    """(z_mid radius min, max, n_ring_samples) of the shaft mesh at mid height -> the flute signature."""
    me = ob.data
    if not me.vertices:
        return None
    zs = [v.co.z for v in me.vertices]
    zmid = (min(zs) + max(zs)) / 2
    band = [v.co for v in me.vertices if abs(v.co.z - zmid) < 0.35]
    if len(band) < 8:
        return None
    rr = [math.hypot(c.x, c.y) for c in band]
    return min(rr), max(rr), len(band)


def px_width(ob, dist):
    """Screen width in px of the object's bounding box as seen by cam03."""
    xs, ys = [], []
    for corner in ob.bound_box:
        w = ob.matrix_world @ Vector(corner)
        p = world_to_camera_view(scene, cam, w)
        if p.z <= 0:
            continue
        xs.append(p.x * RX)
        ys.append(p.y * RY)
    if not xs:
        return None
    return (max(xs) - min(xs), max(ys) - min(ys), min(xs), max(xs))


cands = []
for ob in bpy.data.objects:
    if "_column_" in ob.name and ob.name.startswith("ARCH_colonnade"):
        d = (ob.matrix_world.translation - cam.location).length
        if ob.name.endswith("_LOD1") or ob.name.endswith("_LOD2"):
            continue
        cands.append((d, ob))
cands.sort(key=lambda t: t[0])
print("\ndist  | object                                        | vis | verts |  r_min  r_max  flute mm | px w x h | px x-range")
seen_axes = []
for d, ob in cands[:12]:
    st = shaft_stats(ob)
    pw = px_width(ob, d)
    fl = ""
    if st:
        fl = f"{st[0]:6.3f} {st[1]:6.3f} {1000 * (st[1] - st[0]):8.0f}"
    pws = f"{pw[0]:5.0f} x {pw[1]:5.0f} | {pw[2]:7.0f}..{pw[3]:.0f}" if pw else "  (behind camera)"
    print(f"{d:5.2f} | {ob.name:<45} | {'Y' if visible(ob) else '.'}   | {len(ob.data.vertices):5d} | {fl} | {pws}")

# the nearest render-visible shaft: capital socket / ORN instance at its top
near = next((ob for d, ob in cands if visible(ob)), None)
if near:
    top = near.matrix_world.translation.copy()
    zs = [(near.matrix_world @ v.co).z for v in near.data.vertices]
    top.z = max(zs)
    print(f"\nnearest render-visible shaft: {near.name} at {tuple(round(v, 2) for v in near.matrix_world.translation)}, "
          f"shaft top z {top.z:.2f}, mesh '{near.data.name}' ({len(near.data.polygons)} faces)")
    print("objects within 3.0 m of that shaft top (capital / astragal / ORN instance):")
    for ob in bpy.data.objects:
        if ob.type not in {"MESH", "EMPTY"}:
            continue
        p = ob.matrix_world.translation
        if (p - top).length < 3.0:
            print(f"   {(p - top).length:5.2f} m  {ob.name:<48} type {ob.type:<6} "
                  f"render={'Y' if visible(ob) else '.'} coll {[c.name for c in ob.users_collection]}")
