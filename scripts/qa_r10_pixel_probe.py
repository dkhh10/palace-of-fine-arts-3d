"""QA round 10: name the object under a list of hero pixels (owner attribution for the tile defect list).

    scripts/blender_run.sh 300 -- --background master.blend --python scripts/qa_r10_pixel_probe.py -- [--cam 01] [--res 1920 1080]

Casts a ray from the camera through each pixel of PIXELS and prints the first hit's object name, collection, type,
distance and the dimensions of the hit object (so a "plain cylinder / low-poly blob" defect can name its object).
"""
import bpy, os, sys
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
import qa_cameras

ARGS = common.script_args()
RES = (1920, 1080)

# (x, y, label) in render pixels, y from the TOP (image convention)
PIXELS = [
    (1075, 1030, "near white waterfowl, foreground"),
    (1475, 725, "white post in the lagoon, mid"),
    (1770, 825, "blue-grey blob on the water"),
    (735, 800, "white post left of centre"),
    (950, 105, "dome cap"),
    (770, 415, "left side-bay lunette"),
    (1150, 415, "right side-bay lunette"),
    (865, 450, "left paired column shaft"),
    (1500, 600, "south colonnade shaft (speckle)"),
    (100, 590, "north colonnade back wall (violet panel)"),
    (960, 500, "main arch: coffered barrel"),
    (960, 1000, "water, foreground"),
]


# cam02 (Eevee 1280x720) — the mid-ground boxes and the gold/indigo soffit of the round-10 tile review
CAM2_RES = (1280, 720)
CAM2_PIXELS = [
    (1000, 500, "mid-ground flat ochre box, upper step"),
    (1050, 560, "mid-ground flat ochre box, lower step"),
    (860, 560, "mid-ground box, left"),
    (790, 690, "arch soffit coffer field (indigo)"),
    (770, 660, "arch soffit rim (chrome yellow)"),
    (300, 700, "shaded column shaft (violet)"),
]


def probe(scene, cam_name, res, pixels):
    cam = bpy.data.objects[cam_name]
    scene.camera = cam
    scene.render.resolution_x, scene.render.resolution_y = res
    dg = bpy.context.evaluated_depsgraph_get()
    mw = cam.matrix_world
    org = mw.translation
    tr, br, bl, tl = [mw @ v for v in cam.data.view_frame(scene=scene)]
    print(f"\n=== {cam_name} at {res[0]}x{res[1]}")
    for px, py, label in pixels:
        u = (px + 0.5) / res[0]
        v = (py + 0.5) / res[1]
        top = tl + (tr - tl) * u
        bot = bl + (br - bl) * u
        p = top + (bot - top) * v
        d = (p - org).normalized()
        ok, loc, _n, _i, ob, _m = scene.ray_cast(dg, org, d, distance=2000.0)
        if not ok:
            print(f"({px:4d},{py:4d}) {label:38s} -> SKY")
            continue
        coll = ob.users_collection[0].name if ob.users_collection else "-"
        me = ob.evaluated_get(dg).data
        nf = len(me.polygons) if hasattr(me, "polygons") else -1
        mat = ob.active_material.name if ob.active_material else "-"
        print(f"({px:4d},{py:4d}) {label:38s} -> {ob.name:42s} [{coll:16s}] {(loc - org).length:7.1f} m "
              f"dim {tuple(round(x, 2) for x in ob.dimensions)} faces {nf} mat {mat}")


def main():
    scene = bpy.context.scene
    qa_cameras.ensure(scene)
    probe(scene, "CAM_qa_02_lagoon_ne_threequarter", CAM2_RES, CAM2_PIXELS)
    cam = bpy.data.objects["CAM_qa_01_lagoon_hero"]
    scene.camera = cam
    scene.render.resolution_x, scene.render.resolution_y = RES
    dg = bpy.context.evaluated_depsgraph_get()
    from bpy_extras.object_utils import world_to_camera_view  # noqa: F401  (kept for reference)
    mw = cam.matrix_world
    org = mw.translation
    # frame corners in camera space at distance 1
    frame = [mw @ v for v in cam.data.view_frame(scene=scene)]  # tr, br, bl, tl
    tr, br, bl, tl = frame
    for px, py, label in PIXELS:
        u = (px + 0.5) / RES[0]
        v = (py + 0.5) / RES[1]           # 0 at top
        top = tl + (tr - tl) * u
        bot = bl + (br - bl) * u
        p = top + (bot - top) * v
        d = (p - org).normalized()
        ok, loc, _n, _i, ob, _m = scene.ray_cast(dg, org, d, distance=2000.0)
        if not ok:
            print(f"({px:4d},{py:4d}) {label:38s} -> SKY")
            continue
        coll = ob.users_collection[0].name if ob.users_collection else "-"
        dim = tuple(round(x, 2) for x in ob.dimensions)
        me = ob.evaluated_get(dg).data
        nf = len(me.polygons) if hasattr(me, "polygons") else -1
        mat = ob.active_material.name if ob.active_material else "-"
        print(f"({px:4d},{py:4d}) {label:38s} -> {ob.name:42s} [{coll:16s}] {(loc - org).length:7.1f} m "
              f"dim {dim} faces {nf} mat {mat}")


main()
