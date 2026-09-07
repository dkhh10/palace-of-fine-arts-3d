"""ORN look-dev for QA-02-9/10: render the attic band (panel + corner figure + corner scroll) from the REAL cam05
station with the REAL lighting rig, against a stand-in attic wall, so the relief can be iterated in ~1 min instead
of rebuilding master.blend.

    blender --background --python scripts/orn_relief_render.py -- [--samples 48] [--tag t1] [--res 1920 1080]
                                                                 [--panel 1] [--eevee]

The panel, corner figure and corner scroll are placed on the ARCH socket frames measured from architecture.blend
(SOCKET_attic_panel_001 / attic_figure_001 / finial_001 - the SE-facing set cam05 looks at, where the morning sun
hits the face nearly head-on, s.n = 0.98). Output: renders/previews/ornament/relief_<tag>.png
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


SAMPLES = int(arg("--samples", 48))
TAG = arg("--tag", "t1")
RES = [int(v) for v in arg("--res", ["1920", "1080"], n=2)]
PANEL_V = int(arg("--panel", 1))
FIG_V = int(arg("--figure", 1))

# ARCH socket frames (measured with scripts/orn_relief_check.py --sockets)
SOCKETS = {
    "panel":  ((12.79, 16.97, 32.55), (0.602, 0.799, 0.0)),
    "figure": ((6.27, 24.25, 31.22), (0.250, 0.968, 0.0)),
    "scroll": ((6.11, 23.62, 38.30), (0.250, 0.968, 0.0)),
    # the neighbouring corner, so the frame has a second figure in it
    "figure2": ((21.58, 12.71, 31.22), (0.862, 0.508, 0.0)),
    "scroll2": ((21.02, 12.38, 38.30), (0.862, 0.508, 0.0)),
    "panel2": ((21.04, 2.96, 32.55), (0.990, 0.139, 0.0)),
}
CAM05 = ((28.1, 111.8, 1.5), (0.0, 0.0, 20.0), 40.0)


def rz_for(n):
    return -math.atan2(n[0], n[1])


def place(obj, key):
    loc, n = SOCKETS[key]
    obj.matrix_world = Matrix.Translation(loc) @ Euler((0, 0, rz_for(n)), "XYZ").to_matrix().to_4x4()


def wall(name, key, w, h, z0, thick=1.4, y0=-0.02):
    """A stand-in slice of the attic wall behind an ornament socket (so occlusion and bounce are realistic)."""
    loc, n = SOCKETS[key]
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    ob = bpy.context.object
    ob.name = name
    ob.scale = (w / 2, thick / 2, h / 2)
    ob.matrix_world = (Matrix.Translation(loc) @ Euler((0, 0, rz_for(n)), "XYZ").to_matrix().to_4x4()
                       @ Matrix.Translation((0, y0 - thick / 2, z0 + h / 2)) @ Matrix.Diagonal((w, thick, h, 1.0)))
    return ob


def main():
    bpy.ops.wm.open_mainfile(filepath=str(common.ASSET_FILES["ORN"]), load_ui=False)
    scene = bpy.context.scene
    # everything hidden except what we place
    for o in bpy.data.objects:
        o.hide_render = True
        o.hide_viewport = True

    def show(name, key):
        o = bpy.data.objects.get(name)
        if o is None:
            print(f"[relief] MISSING {name}")
            return None
        o.hide_render = False
        o.hide_viewport = False
        if o.name not in scene.collection.objects:
            try:
                scene.collection.objects.link(o)
            except RuntimeError:
                pass
        place(o, key)
        return o

    show(f"ORN_attic_panel_v{PANEL_V}_LOD0", "panel")
    show(f"ORN_attic_figure_v{FIG_V}_LOD0", "figure")
    show(f"ORN_corner_scroll_v1_LOD0", "scroll")
    p2 = bpy.data.objects.get(f"ORN_attic_panel_v{(PANEL_V % 3) + 1}_LOD0")
    if p2:
        p2.hide_render = p2.hide_viewport = False
        if p2.name not in scene.collection.objects:
            try:
                scene.collection.objects.link(p2)
            except RuntimeError:
                pass
        place(p2, "panel2")

    mat = common.load_material("MAT_concrete_ochre")
    # stand-in attic wall behind the panel, plus the corner block and the cornice that overhangs it
    walls = [wall("W_panel", "panel", 12.6, 5.6, -0.55),
             wall("W_panel2", "panel2", 12.6, 5.6, -0.55),
             wall("W_corner", "figure", 5.9, 7.3, -0.30, thick=2.6, y0=0.30),
             wall("W_corner2", "figure2", 5.9, 7.3, -0.30, thick=2.6, y0=0.30),
             wall("W_cap", "scroll", 6.2, 0.34, -0.34, thick=3.2, y0=0.60),
             wall("W_cap2", "scroll2", 6.2, 0.34, -0.34, thick=3.2, y0=0.60),
             wall("W_cornice", "panel", 12.6, 0.9, 4.55, thick=1.9, y0=0.55),
             wall("W_cornice2", "panel2", 12.6, 0.9, 4.55, thick=1.9, y0=0.55),
             wall("W_base", "panel", 12.6, 1.4, -1.95, thick=1.9, y0=0.45),
             wall("W_base2", "panel2", 12.6, 1.4, -1.95, thick=1.9, y0=0.45)]
    for w in walls:
        common.assign_material(w, mat)

    cam_loc, target, lens = CAM05
    cam_data = bpy.data.cameras.new("CAM_relief")
    cam_data.lens = lens
    cam = bpy.data.objects.new("CAM_relief", cam_data)
    scene.collection.objects.link(cam)
    d = (Vector(target) - Vector(cam_loc)).normalized()
    cam.matrix_world = Matrix.Translation(cam_loc) @ (-d).to_track_quat("Z", "Y").to_matrix().to_4x4()
    scene.camera = cam

    light_presets.apply_rig(scene, link=True)
    light_presets.apply_look(scene, link=True)
    if "--exposure" in args:
        scene.view_settings.exposure = float(arg("--exposure"))
    if "--eevee" in args:
        light_presets.apply_preview_eevee(scene, samples=32)
    else:
        light_presets.apply_final_cycles(scene, samples=SAMPLES)
    scene.render.resolution_x, scene.render.resolution_y = RES
    scene.render.resolution_percentage = 100
    out = common.RENDERS / "previews" / "ornament" / f"relief_{TAG}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    scene.render.filepath = str(out)
    scene.render.image_settings.file_format = "PNG"
    print(f"[relief] exposure {scene.view_settings.exposure:.4f} look {scene.view_settings.look}")
    t = time.time()
    bpy.ops.render.render(write_still=True)
    print(f"[relief] wrote {out} in {time.time() - t:.0f}s")


main()
