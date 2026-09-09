"""Architecture round 6 proof render: a Cycles cam01 crop of the hero-facing stack, nothing else.

    blender --background master.blend --python scripts/arch_r6_render.py -- [--samples 64] [--out <png>]

Only the band the round-6 course work touches is rendered (render border, NOT crop, so the output is a full
1920x1080 frame and its rows are the same rows QA's aligned overlay and `arch_entab_probe --courses` quote).
Everything outside the border stays black; the sheet script crops it.
"""
import bpy, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common

args = common.script_args()


def opt(flag, cast, default):
    return cast(args[args.index(flag) + 1]) if flag in args and args.index(flag) + 1 < len(args) else default


SAMPLES = opt("--samples", int, 64)
OUT = opt("--out", str, str(common.RENDERS / "previews" / "architecture" / "arch_r6_cam01_stack.png"))
ROWS = (opt("--row0", int, 100), opt("--row1", int, 380))
COLS = (opt("--col0", int, 660), opt("--col1", int, 1270))
RES = (1920, 1080)

scene = bpy.context.scene
common.setup_scene(scene)
cam = bpy.data.objects.get("CAM_qa_01_lagoon_hero")
if cam is None:
    import qa_cameras
    qa_cameras.ensure(scene)
    cam = bpy.data.objects["CAM_qa_01_lagoon_hero"]
scene.camera = cam
common.configure_cycles(scene, samples=SAMPLES)
scene.render.resolution_x, scene.render.resolution_y = RES
scene.render.resolution_percentage = 100
scene.render.use_border = True
scene.render.use_crop_to_border = False
scene.render.border_min_x = COLS[0] / RES[0]
scene.render.border_max_x = COLS[1] / RES[0]
scene.render.border_min_y = 1.0 - ROWS[1] / RES[1]
scene.render.border_max_y = 1.0 - ROWS[0] / RES[1]
scene.render.filepath = OUT
print(f"[arch_r6_render] cycles {SAMPLES} spp, {RES[0]}x{RES[1]}, border cols {COLS} rows {ROWS} -> {OUT}")
t = time.time()
bpy.ops.render.render(write_still=True)
print(f"[arch_r6_render] done in {time.time() - t:.1f}s")
