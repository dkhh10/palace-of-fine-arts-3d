"""Phase 10 r1, step 9 -- the measurement renders on the rebuilt master (one Blender, frames in sequence).

    scripts/blender_run.sh 2400 -- --background master.blend --python scripts/mat_p10_render.py -- --tag after \
        [--jobs hero,cam02,cam03,eevee] [--spp 64]

hero  = CAM_qa_01_lagoon_hero 1920x1080 Cycles;  cam02 / cam03 = 1280x720 Cycles;  eevee = the hero in Eevee (parity).
Written to renders/previews/materials/p10_<tag>_<job>.png.  Settings as scripts/mat_r10_render.py (the final Cycles
preset of light_presets at --spp, guiding off, 8-bit PNG).
"""
import bpy, sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
import light_presets

args = common.script_args()
JOBS = (args[args.index("--jobs") + 1] if "--jobs" in args else "hero,cam02,cam03,eevee").split(",")
SPP = int(args[args.index("--spp") + 1]) if "--spp" in args else 64
TAG = args[args.index("--tag") + 1] if "--tag" in args else "x"
OUT = common.RENDERS / "previews" / "materials"
OUT.mkdir(parents=True, exist_ok=True)
scene = bpy.context.scene
SETS = {"hero": ("CAM_qa_01_lagoon_hero", 1920, 1080, "CYCLES"),
        "cam02": ("CAM_qa_02_lagoon_ne_threequarter", 1280, 720, "CYCLES"),
        "cam03": ("CAM_qa_03_colonnade_walk", 1280, 720, "CYCLES"),
        "eevee": ("CAM_qa_01_lagoon_hero", 1920, 1080, "BLENDER_EEVEE")}
t0 = time.time()
for job in JOBS:
    cam, rx, ry, eng = SETS[job]
    if eng == "CYCLES":
        light_presets.apply_final_cycles(scene, samples=SPP)
        for k, v in (("use_guiding", False), ("use_auto_tile", True), ("tile_size", 256)):
            if hasattr(scene.cycles, k):
                setattr(scene.cycles, k, v)
    else:
        scene.render.engine = "BLENDER_EEVEE"
        if hasattr(scene.eevee, "taa_render_samples"):
            scene.eevee.taa_render_samples = 32
    common.setup_scene(scene)
    scene.render.engine = eng
    scene.render.image_settings.color_depth = "8"
    scene.camera = bpy.data.objects[cam]
    scene.render.resolution_x, scene.render.resolution_y = rx, ry
    scene.render.resolution_percentage = 100
    scene.render.use_border = False
    fp = OUT / f"p10_{TAG}_{job}.png"
    scene.render.filepath = str(fp)
    t = time.time()
    bpy.ops.render.render(write_still=True)
    print(f"[p10render] {job} {cam} {rx}x{ry} {eng} {time.time() - t:.1f}s -> {fp.name}", flush=True)
print(f"[p10render] done in {time.time() - t0:.1f}s")
