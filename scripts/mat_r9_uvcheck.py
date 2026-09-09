"""Does the shader's world-space projection equal architecture's baked `UVProj`?  (no render)

    blender -b --background --python scripts/mat_r9_uvcheck.py

Round 9's projection is computed in the shader from the world position (mat_build.build_group_photo) rather than
read from the `UVProj` layer, because `UVProj` exists on the 33 ARCH meshes only and QA's attic box is covered by
ORN's attic-panel assets -- a UVProj-only projection would stop at every ornament edge, which is a seam generator.
This script proves the two are the same projection by evaluating BOTH on every vertex that carries the layer:

  a) `bpy_extras.object_utils.world_to_camera_view` on a reconstruction of the bake camera  (Blender's own maths)
  b) the closed form the shader implements                                                   (mat_build)
  c) the baked `UVProj` layer                                                                (architecture.blend)

It prints the worst |a-b| and |b-c| in PIXELS of the 1920x1080 projector frame.
"""
import bpy, sys, os, math
from mathutils import Vector, Euler
from bpy_extras.object_utils import world_to_camera_view

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common

LOC, TARGET = (-14.1, 100.0, 1.6), (0.0, 0.0, 1.6)
LENS, SENSOR, SHIFT_Y, RES = 20.0, 36.0, 0.06, (1920, 1080)
UV_NAME = "UVProj"


def closed_form(p, basis):
    right, up, fwd, us, uo, vs, vo = basis
    d = p - Vector(LOC)
    depth = max(d.dot(fwd), 1.0)
    return (d.dot(right) / depth) * us + uo, (d.dot(up) / depth) * vs + vo


def basis():
    rot = common.lookat_rotation(LOC, TARGET)
    M = Euler(rot).to_matrix()
    hx = SENSOR / (2.0 * LENS)
    hy = hx * RES[1] / RES[0]
    dy = SHIFT_Y * SENSOR / LENS
    return (M.col[0], M.col[1], -M.col[2], 1.0 / (2.0 * hx), 0.5, 1.0 / (2.0 * hy), (hy - dy) / (2.0 * hy))


bpy.ops.wm.open_mainfile(filepath=str(common.ROOT / "assets" / "architecture.blend"), load_ui=False)
scene = bpy.context.scene
cd = bpy.data.cameras.new("PROJ_CHECK")
cd.lens, cd.sensor_width, cd.sensor_fit, cd.shift_y = LENS, SENSOR, "HORIZONTAL", SHIFT_Y
cam = bpy.data.objects.new("PROJ_CHECK", cd)
cam.location = LOC
cam.rotation_euler = common.lookat_rotation(LOC, TARGET)
scene.collection.objects.link(cam)
scene.camera = cam
scene.render.resolution_x, scene.render.resolution_y = RES
scene.render.resolution_percentage = 100
bpy.context.view_layer.update()

B = basis()
worst_ab = worst_bc = 0.0
worst_bc_name = ""
n_obj = n_v = 0
for o in bpy.data.objects:
    if o.type != "MESH" or UV_NAME not in (l.name for l in o.data.uv_layers):
        continue
    n_obj += 1
    # matrix_world is stale (identity) for objects hidden in the view layer; matrix_basis is always current.
    mw = o.matrix_basis if o.parent is None else o.matrix_world
    uvl = o.data.uv_layers[UV_NAME].data
    step = max(1, len(o.data.loops) // 400)
    for li in range(0, len(o.data.loops), step):
        vi = o.data.loops[li].vertex_index
        p = mw @ o.data.vertices[vi].co
        co = world_to_camera_view(scene, cam, p)
        if co.z <= 1.0:
            continue
        ua, va = co.x, co.y
        ub, vb = closed_form(p, B)
        uc, vc = uvl[li].uv
        worst_ab = max(worst_ab, math.hypot((ua - ub) * RES[0], (va - vb) * RES[1]))
        d = math.hypot((ub - uc) * RES[0], (vb - vc) * RES[1])
        if d > worst_bc:
            worst_bc, worst_bc_name = d, o.name
        n_v += 1

print(f"[uvcheck] {n_obj} meshes carry {UV_NAME}, {n_v} sampled loops")
print(f"[uvcheck] worst |world_to_camera_view - shader closed form| = {worst_ab:.4f} px")
print(f"[uvcheck] worst |shader closed form - baked UVProj|        = {worst_bc:.4f} px  ({worst_bc_name})")
