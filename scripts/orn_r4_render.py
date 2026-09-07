"""ORN round-4 look-dev (QA-03-15 capitals, QA-03-8 rosettes, carried keystone depth).

Puts the rotunda capital, the coffer rosette and the arch keystone on their REAL ARCH socket frames with the REAL
lighting rig, and renders two things for each:
  * "close"  - a lookdev view at the angle the reference crop was shot from, 900 px;
  * "hero"   - a 1:1 border crop out of the real CAM_qa_01 frame (20 mm, 1920x1080), i.e. exactly the pixels QA
               judges in the crop pair. A rotunda capital is ~34 px tall there.

    blender --background --python scripts/orn_r4_render.py -- --tag before [--samples 40] [--eevee] [--blend X.blend]

Outputs renders/previews/ornament/r4_<tag>_<view>_<asset>.png and prints a luminance-tier report for the hero crops.
"""
import bpy, sys, os, math, time
from pathlib import Path
from mathutils import Vector, Matrix, Euler

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
import light_presets

args = common.script_args()


def arg(name, default=None, n=1):
    if name not in args:
        return default
    i = args.index(name) + 1
    v = args[i:i + n]
    return v[0] if n == 1 else v


TAG = arg("--tag", "t")
SAMPLES = int(arg("--samples", 40))
EEVEE = "--eevee" in args
BLEND = arg("--blend", str(common.ASSET_FILES["ORN"]))
ONLY = (arg("--only", "capital,rosette,keystone")).split(",")
OUT = common.RENDERS / "previews" / "ornament"

# ARCH socket frames, from architecture.blend (loc, outward +Y).  See docs/ornament_notes.md round 4.
SOCKETS = {
    "capital":  ((-10.11, 21.60, 24.80), (-0.139, 0.990, 0.0)),
    "capital2": ((3.76, 23.55, 24.80), (-0.139, 0.990, 0.0)),
    "keystone": ((-3.03, 21.59, 24.30), (-0.139, 0.990, 0.0)),
    "rosette":  ((-1.91, 13.60, 24.55), (-0.139, 0.990, 0.0)),
}
CAM01 = dict(loc=(-14.1, 100.0, 1.6), target=(0.0, 0.0, 1.6), lens=20.0, shift_y=0.06)
# the coffer rosettes are never in the cam01 frame; QA judges them at cam04 (straight up inside the rotunda)
CAM04 = dict(loc=(0.0, 3.0, 1.6), target=(0.0, 3.0, 40.0), lens=15.0, shift_y=0.0)
HERO_CAM = {"capital": "01", "keystone": "01", "rosette": "04"}
# close lookdev views: (asset key, distance, azimuth offset from the socket normal (deg), elevation (deg), lens)
CLOSE = {
    "capital": (11.0, 26.0, -11.0, 85.0),
    "rosette": (3.4, 22.0, 4.0, 85.0),
    "keystone": (3.2, 24.0, -14.0, 85.0),
}


def rz_for(n):
    return -math.atan2(n[0], n[1])


def socket_matrix(key):
    loc, n = SOCKETS[key]
    return Matrix.Translation(loc) @ Euler((0, 0, rz_for(n)), "XYZ").to_matrix().to_4x4()


def show(name, key, scene):
    o = bpy.data.objects.get(name)
    if o is None:
        print(f"[r4] MISSING {name}")
        return None
    o.hide_render = o.hide_viewport = False
    if o.name not in scene.collection.objects:
        try:
            scene.collection.objects.link(o)
        except RuntimeError:
            pass
    o.matrix_world = socket_matrix(key)
    return o


def slab(name, key, size, offset, mat, scene):
    """Stand-in piece of ARCH in the socket frame: size (w along x, depth along y, h along z), offset its centre."""
    me = bpy.data.meshes.new(name)
    bm_verts = []
    w, d, h = (s / 2 for s in size)
    for sx in (-1, 1):
        for sy in (-1, 1):
            for sz in (-1, 1):
                bm_verts.append((sx * w, sy * d, sz * h))
    faces = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    me.from_pydata(bm_verts, [], faces)
    me.update()
    ob = bpy.data.objects.new(name, me)
    scene.collection.objects.link(ob)
    ob.matrix_world = socket_matrix(key) @ Matrix.Translation(offset)
    common.assign_material(ob, mat)
    return ob


def cylinder(name, key, r, h, offset, mat, scene, seg=48):
    me = bpy.data.meshes.new(name)
    verts, faces = [], []
    for i in range(seg):
        a = 2 * math.pi * i / seg
        verts.append((r * math.cos(a), r * math.sin(a), 0.0))
        verts.append((r * math.cos(a), r * math.sin(a), h))
    for i in range(seg):
        j = (i + 1) % seg
        faces.append((2 * i, 2 * j, 2 * j + 1, 2 * i + 1))
    me.from_pydata(verts, [], faces)
    me.update()
    me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    ob = bpy.data.objects.new(name, me)
    scene.collection.objects.link(ob)
    ob.matrix_world = socket_matrix(key) @ Matrix.Translation(offset)
    common.assign_material(ob, mat)
    return ob


def make_cam(name, loc, target, lens, scene, shift_y=0.0):
    cd = bpy.data.cameras.new(name)
    cd.lens = lens
    cd.shift_y = shift_y
    ob = bpy.data.objects.new(name, cd)
    scene.collection.objects.link(ob)
    d = (Vector(target) - Vector(loc)).normalized()
    ob.matrix_world = Matrix.Translation(loc) @ (-d).to_track_quat("Z", "Y").to_matrix().to_4x4()
    return ob


def close_cam(key, obj, scene):
    dist, az_off, elev, lens = CLOSE[key]
    loc, n = SOCKETS[key]
    (x0, y0, z0), (x1, y1, z1) = ([min(v[i] for v in [obj.matrix_world @ Vector(c) for c in obj.bound_box])
                                   for i in range(3)],
                                  [max(v[i] for v in [obj.matrix_world @ Vector(c) for c in obj.bound_box])
                                   for i in range(3)])
    centre = Vector(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))
    a = math.atan2(n[1], n[0]) + math.radians(az_off)
    e = math.radians(elev)
    p = centre + Vector((math.cos(a) * math.cos(e), math.sin(a) * math.cos(e), math.sin(e))) * dist
    return make_cam(f"CAM_close_{key}", p, centre, lens, scene)


def border_for(scene, cam, obj, pad_px=26, res=(1920, 1080)):
    """Screen-space box of obj in cam, expanded by pad_px, as (min_x, max_x, min_y, max_y) in 0..1."""
    from bpy_extras.object_utils import world_to_camera_view
    pts = [world_to_camera_view(scene, cam, obj.matrix_world @ Vector(c)) for c in obj.bound_box]
    xs = [p.x for p in pts]
    ys = [p.y for p in pts]
    px, py = pad_px / res[0], pad_px / res[1]
    return (max(0.0, min(xs) - px), min(1.0, max(xs) + px), max(0.0, min(ys) - py), min(1.0, max(ys) + py))


def render(scene, path, res, border=None):
    scene.render.resolution_x, scene.render.resolution_y = res
    scene.render.resolution_percentage = 100
    if border:
        scene.render.use_border = True
        scene.render.use_crop_to_border = True
        (scene.render.border_min_x, scene.render.border_max_x,
         scene.render.border_min_y, scene.render.border_max_y) = border
    else:
        scene.render.use_border = False
    scene.render.filepath = str(path)
    scene.render.image_settings.file_format = "PNG"
    t = time.time()
    bpy.ops.render.render(write_still=True)
    print(f"[r4] {path.name} in {time.time() - t:.0f}s")


def main():
    bpy.ops.wm.open_mainfile(filepath=BLEND, load_ui=False)
    scene = bpy.context.scene
    for o in bpy.data.objects:
        o.hide_render = o.hide_viewport = True
    OUT.mkdir(parents=True, exist_ok=True)
    mat = common.load_material("MAT_concrete_ochre")

    def same_stone(o):
        """One stone for ornament and stand-in wall alike, so the sheet compares GEOMETRY, not two materials."""
        if o is not None:
            common.assign_material(o, mat)
        return o

    placed = {}
    if "capital" in ONLY:
        cap = same_stone(show("ORN_capital_rotunda_v1_LOD0", "capital", scene))
        same_stone(show("ORN_capital_rotunda_v2_LOD0", "capital2", scene))
        # shaft below, entablature block above, pier face behind
        for k in ("capital", "capital2"):
            cylinder(f"S_shaft_{k}", k, 1.06, 4.4, (0, 0, -4.4), mat, scene)
            slab(f"S_entab_{k}", k, (3.6, 3.6, 1.45), (0, -0.25, 2.6 + 0.725), mat, scene)
        slab("S_pier", "capital", (11.0, 2.4, 14.0), (7.0, -2.0, -6.0), mat, scene)
        placed["capital"] = cap
    if "keystone" in ONLY:
        ks = same_stone(show("ORN_keystone_v1_LOD0", "keystone", scene))
        slab("S_archivolt", "keystone", (5.0, 1.1, 1.30), (0, -0.55, 0.30), mat, scene)
        slab("S_spandrel", "keystone", (9.0, 1.9, 3.2), (0, -0.95, -2.2), mat, scene)
        placed["keystone"] = ks
    if "rosette" in ONLY:
        ro = same_stone(show("ORN_rosette_ceiling_v1_LOD0", "rosette", scene))
        # coffer box: a 1.05 m square recess 0.34 m deep in a wall face, with the rosette on its floor
        # ARCH deepened the saucer coffers to 0.55 m on 2026-09-07; the stand-in box matches
        for dx, dz in ((-0.70, 0.0), (0.70, 0.0), (0.0, 0.70), (0.0, -0.70)):
            slab(f"S_cofrib_{dx}_{dz}", "rosette", (0.35 if dx else 1.75, 0.55, 1.75 if dx else 0.35),
                 (dx, -0.275, dz + 0.30), mat, scene)
        slab("S_cofback", "rosette", (2.4, 0.30, 2.4), (0, -0.55 - 0.15, 0.30), mat, scene)
        placed["rosette"] = ro

    light_presets.apply_rig(scene, link=True)
    light_presets.apply_look(scene, link=True)
    if EEVEE:
        light_presets.apply_preview_eevee(scene, samples=32)
    else:
        light_presets.apply_final_cycles(scene, samples=SAMPLES)
    scene.cycles.use_denoising = True

    hero01 = make_cam("CAM_r4_hero01", CAM01["loc"], CAM01["target"], CAM01["lens"], scene, shift_y=CAM01["shift_y"])
    hero04 = make_cam("CAM_r4_hero04", CAM04["loc"], CAM04["target"], CAM04["lens"], scene)
    for key, obj in placed.items():
        hero = hero01 if HERO_CAM[key] == "01" else hero04
        scene.camera = hero
        bpy.context.view_layer.update()
        b = border_for(scene, hero, obj, pad_px=22)
        render(scene, OUT / f"r4_{TAG}_hero_{key}.png", (1920, 1080), border=b)
        scene.camera = close_cam(key, obj, scene)
        scene.render.use_border = False
        render(scene, OUT / f"r4_{TAG}_close_{key}.png", (900, 900))
        (x0, y0, z0), (x1, y1, z1) = ([min(v[i] for v in [obj.matrix_world @ Vector(c) for c in obj.bound_box])
                                       for i in range(3)],
                                      [max(v[i] for v in [obj.matrix_world @ Vector(c) for c in obj.bound_box])
                                       for i in range(3)])
        print(f"[r4] {key}: {obj.name} size {x1 - x0:.2f} x {y1 - y0:.2f} x {z1 - z0:.2f} m, "
              f"tris {len(obj.data.polygons)} faces")


main()
