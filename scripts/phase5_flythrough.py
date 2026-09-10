"""Phase 5 delivery: low-res Eevee test animation of the flythrough, rendered from master.blend. CAM_flythrough /
CAM_flythrough_path / CAM_flythrough_target are built into assets/lighting.blend by scripts/light_flythrough.py
(round 14 rewrite: 1224 frames @ 24 fps, docs/lighting_notes.md sec 23 "The flythrough path, rebuilt on the site
that actually exists, and validated by ray-cast"). This script only renders frames; scripts/phase5_deliver.sh step 6
encodes them with ffmpeg afterwards. Nothing is saved back to master.blend.

    scripts/blender_run.sh 7200 -- --background --python scripts/phase5_flythrough.py -- --res 640 360 --samples 16 --frame-step 2
    ... --blend master_delivery.blend      # the cleaned delivery copy (phase5_deliver.sh step 1b); default master.blend

Writes renders/anim/flythrough_test/frame_####.png (directory is cleared first: idempotent, no stale frames from a
previous partial run) and prints one machine-parseable summary line:
    [phase5_flythrough] wall_time_s=<...> frames_written=<...> fps=<...> frame_step=<...> ...
scripts/phase5_deliver.sh greps `fps=` / `frame_step=` to compute the ffmpeg output frame rate (fps / frame_step, so
skipping every 2nd frame does not double the apparent speed -- see docs/tech_notes.md "Opening and rendering
master.blend").
"""
import bpy, sys, os, time, shutil
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
import light_presets as lp
import light_flythrough as ft

args = common.script_args()


def arg(name, default=None, n=1):
    if name not in args:
        return default
    i = args.index(name) + 1
    vals = args[i:i + n]
    return vals[0] if n == 1 else vals


RES = [int(v) for v in arg("--res", ["640", "360"], n=2)]
SAMPLES = int(arg("--samples", 16))
FRAME_STEP = int(arg("--frame-step", 2))
OUT_DIR = common.RENDERS / "anim" / "flythrough_test"
# The file to render. Default master.blend; phase5_deliver.sh step 1b passes the cleaned master_delivery.blend.
BLEND = Path(arg("--blend", str(common.ROOT / "master.blend")))

t0 = time.time()
bpy.ops.wm.open_mainfile(filepath=str(BLEND), load_ui=False)
print(f"[phase5_flythrough] opened {BLEND.name} in {time.time() - t0:.1f}s")
scene = bpy.context.scene

cam = bpy.data.objects.get("CAM_flythrough")
if cam is None:
    sys.exit(f"[phase5_flythrough] CAM_flythrough not found in {BLEND.name} -- run scripts/light_flythrough.py first")
scene.camera = cam

sch = ft.load_schedule()
frames = sch["frames"] if sch else scene.frame_end
fps = sch["fps"] if sch else 24
scene.render.fps = fps
FRAME_START = int(arg("--frame-start", 1))      # lead, Phase 5: resume a run the watchdog cut (keeps the step-2 grid)
scene.frame_start, scene.frame_end = FRAME_START, frames
scene.frame_step = FRAME_STEP
n_expected = len(range(FRAME_START, frames + 1, FRAME_STEP))
print(f"[phase5_flythrough] {frames} frames @ {fps} fps, step {FRAME_STEP} -> {n_expected} frames to render")

lp.apply_preview_eevee(scene, samples=SAMPLES)   # 16 TAA per docs/tech_notes.md's flythrough test-animation recipe
common.setup_scene(scene)
scene.render.resolution_x, scene.render.resolution_y = RES
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_depth = "8"
scene.render.image_settings.color_mode = "RGB"

if OUT_DIR.exists() and FRAME_START == 1:       # a resumed run (--frame-start > 1) keeps the frames already rendered
    shutil.rmtree(OUT_DIR)
OUT_DIR.mkdir(parents=True, exist_ok=True)
scene.render.filepath = str(OUT_DIR / "frame_####")

t_render0 = time.time()
bpy.ops.render.render(animation=True)
t_render = time.time() - t_render0
n_written = len(list(OUT_DIR.glob("frame_*.png")))

print(f"[phase5_flythrough] wall_time_s={t_render:.1f} frames_written={n_written} expected={n_expected} "
      f"res={RES[0]}x{RES[1]} samples={SAMPLES} fps={fps} frame_step={FRAME_STEP} out_dir={OUT_DIR}")
