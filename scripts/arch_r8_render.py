"""ARCH round 8 proof renders: one full frame from one QA camera, Cycles.

    blender --background master.blend --python scripts/arch_r8_render.py -- --cam 1 [--res 1920x1080] [--samples 64]
        [--out renders/previews/arch/r8_cam01.png]

Full frame (no border): the r8 defect is the arch opening itself, so the whole frame is inspected in 100 % tiles.
"""
import bpy, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common

args = common.script_args()


def opt(flag, cast, default):
    return cast(args[args.index(flag) + 1]) if flag in args and args.index(flag) + 1 < len(args) else default


CAMS = {1: "CAM_qa_01_lagoon_hero", 2: "CAM_qa_02_lagoon_ne_threequarter", 3: "CAM_qa_03_colonnade_walk"}
CAM_N = opt("--cam", int, 1)
SAMPLES = opt("--samples", int, 64)
RX, RY = (int(v) for v in opt("--res", str, "1920x1080").split("x"))
OUT = opt("--out", str, str(common.RENDERS / "previews" / "arch" / f"r8_cam{CAM_N:02d}.png"))
os.makedirs(os.path.dirname(OUT), exist_ok=True)

scene = bpy.context.scene
common.setup_scene(scene)
cam = bpy.data.objects.get(CAMS[CAM_N])
if cam is None:
    import qa_cameras
    qa_cameras.ensure(scene)
    cam = bpy.data.objects[CAMS[CAM_N]]
scene.camera = cam
common.set_lod(viewport=1, render=0)
common.configure_cycles(scene, samples=SAMPLES)
scene.render.use_border = False
scene.render.resolution_x, scene.render.resolution_y = RX, RY
scene.render.resolution_percentage = 100
scene.render.filepath = OUT
print(f"[arch_r8_render] {CAMS[CAM_N]} cycles {SAMPLES} spp {RX}x{RY} -> {OUT}")
t = time.time()
bpy.ops.render.render(write_still=True)
print(f"[arch_r8_render] done in {time.time() - t:.1f}s")
