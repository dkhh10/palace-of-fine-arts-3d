"""QA-03-16 isolating test (QA / Critic owned; round 04). Renders the hero at 3840x2160, 16 spp, Cycles GPU + OIDN,
once with the compositor OFF and once ON, and prints the two wall times. Reads master.blend, never saves it.

    blender -b --python scripts/qa_4k_probe.py -- [--out DIR] [--samples 16] [--modes off,on] [--time-limit 1200]

`--time-limit` is Cycles' own sampling cap (seconds) so a wedged frame still ends; the compositor / denoise tail is
not covered by it, which is exactly the phase under suspicion, so run this under an outer `timeout` as well.
"""
import bpy, sys, os, time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common, light_presets

args = common.script_args()


def arg(name, default=None):
    if name not in args:
        return default
    return args[args.index(name) + 1]


OUT = Path(arg("--out", "/tmp/qa_4k"))
OUT.mkdir(parents=True, exist_ok=True)
SAMPLES = int(arg("--samples", 16))
MODES = arg("--modes", "off,on").split(",")
TIME_LIMIT = float(arg("--time-limit", 1200))

t0 = time.time()
bpy.ops.wm.open_mainfile(filepath=str(common.ROOT / "master.blend"), load_ui=False)
scene = bpy.context.scene
print(f"[4k] opened master in {time.time() - t0:.1f}s")
light_presets.apply_final_cycles(scene, samples=SAMPLES, time_limit=TIME_LIMIT)
common.setup_scene(scene)
scene.render.image_settings.color_depth = "8"
scene.render.resolution_x, scene.render.resolution_y = 3840, 2160
scene.render.resolution_percentage = 100
cam = bpy.data.objects.get("CAM_qa_01_lagoon_hero")
if cam:
    scene.camera = cam
# Blender 5.x: the compositor tree is scene.compositing_node_group (scene.node_tree / use_nodes are gone)
ng = getattr(scene, "compositing_node_group", None) or getattr(scene, "node_tree", None)
print(f"[4k] compositor: use_compositing={scene.render.use_compositing} tree={ng.name if ng else None} "
      f"nodes={len(ng.nodes) if ng else 0}; device {scene.cycles.device}; samples {scene.cycles.samples}; "
      f"denoise {scene.cycles.use_denoising}")

for mode in MODES:
    on = mode.strip().lower() == "on"
    scene.render.use_compositing = on
    if hasattr(scene, "use_nodes"):
        scene.use_nodes = on and ng is not None
    fp = OUT / f"hero_4k_{SAMPLES}spp_comp_{mode.strip()}.png"
    scene.render.filepath = str(fp)
    t = time.time()
    bpy.ops.render.render(write_still=True)
    dt = time.time() - t
    print(f"[4k] compositor {mode.strip():3s}: {dt:.1f}s wall for 3840x2160 @ {SAMPLES} spp -> {fp} "
          f"({fp.stat().st_size / 1e6:.1f} MB)" if fp.exists() else f"[4k] compositor {mode}: {dt:.1f}s, NO FILE WRITTEN")
    sys.stdout.flush()
print(f"[4k] done in {time.time() - t0:.1f}s")
