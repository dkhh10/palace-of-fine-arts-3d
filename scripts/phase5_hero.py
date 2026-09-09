"""Phase 5 delivery: render the Cycles hero (CAM_qa_01_lagoon_hero) from master.blend at a given resolution and
sample count, using the SAME final Cycles preset every prior QA / lighting final render has used
(light_presets.apply_final_cycles -- denoiser, light tree, the two engine-conditional switches for CYCLES). Used
twice by scripts/phase5_deliver.sh: once for the 128 spp / 4K timing probe (checklist step 4), once for the chosen
final sample count (checklist step 5). Nothing is saved back to master.blend.

    scripts/blender_run.sh 7200 -- --background --python scripts/phase5_hero.py -- --spp 128 --res 3840 2160 --adaptive off
    scripts/blender_run.sh 7200 -- --background --python scripts/phase5_hero.py -- --spp 768 --res 3840 2160 --adaptive off --denoise on
    ... --blend master_delivery.blend      # the cleaned delivery copy (phase5_deliver.sh step 1b); default master.blend

Writes renders/final/hero_cam01_<W>x<H>_<spp>spp.png and prints one machine-parseable summary line:
    [phase5_hero] wall_time_s=<render seconds> open_s=<open seconds> total_s=<...> peak_rss_mb=<...> spp=<...> ...
scripts/phase5_deliver.sh greps `wall_time_s=` out of the step-4 log to pick step 5's sample count / resolution.
"""
import bpy, sys, os, time, resource
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
import light_presets as lp
import qa_cameras

args = common.script_args()


def arg(name, default=None, n=1):
    if name not in args:
        return default
    i = args.index(name) + 1
    vals = args[i:i + n]
    return vals[0] if n == 1 else vals


SPP = int(arg("--spp", 128))
RES = [int(v) for v in arg("--res", ["3840", "2160"], n=2)]
ADAPTIVE = arg("--adaptive", "off").lower() == "on"
DENOISE = arg("--denoise", "on").lower() != "off"
TIME_LIMIT = float(arg("--time-limit", 0.0))   # 0 = none (checklist step 4: "time_limit 0")
# The file to render. Default master.blend; phase5_deliver.sh step 1b passes the cleaned master_delivery.blend.
BLEND = Path(arg("--blend", str(common.ROOT / "master.blend")))

t0 = time.time()
bpy.ops.wm.open_mainfile(filepath=str(BLEND), load_ui=False)
t_open = time.time() - t0
scene = bpy.context.scene
print(f"[phase5_hero] opened {BLEND.name} in {t_open:.1f}s")

# Same preset every Cycles final in this build has used. Do not hand-roll Cycles settings here (see docs/tech_notes.md
# "The two Eevee-only rigs" -- setting scene.render.engine = 'CYCLES' by hand and skipping this call renders the
# Eevee-only vault override / shade fill into the frame).
lp.apply_final_cycles(scene, samples=SPP, time_limit=TIME_LIMIT)
scene.cycles.use_adaptive_sampling = ADAPTIVE
scene.cycles.use_denoising = DENOISE
common.setup_scene(scene)

# QA/lighting owns the camera stations; never trust a station baked into a stale master.blend (qa_render_round.py
# does the same rebuild-in-memory before every round; nothing here is saved back to the file).
qa_cameras.ensure(scene)
cam = bpy.data.objects.get("CAM_qa_01_lagoon_hero")
if cam is None:
    sys.exit("[phase5_hero] CAM_qa_01_lagoon_hero not found even after qa_cameras.ensure()")
scene.camera = cam

scene.render.resolution_x, scene.render.resolution_y = RES
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"   # depth / mode stay as apply_final_cycles set them (16-bit; review fix 3)

OUT = common.RENDERS / "final"
OUT.mkdir(parents=True, exist_ok=True)
fp = OUT / f"hero_cam01_{RES[0]}x{RES[1]}_{SPP}spp.png"
scene.render.filepath = str(fp)

t_render0 = time.time()
bpy.ops.render.render(write_still=True)
t_render = time.time() - t_render0
t_total = time.time() - t0

# ru_maxrss is bytes on macOS, kilobytes on Linux (this build is macOS-only per CLAUDE.md, but don't lie on Linux).
raw = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
peak_mb = raw / (1024.0 * 1024.0) if sys.platform == "darwin" else raw / 1024.0

if fp.exists():
    print(f"[phase5_hero] wrote {fp} ({fp.stat().st_size / 1e6:.1f} MB)")
else:
    print(f"[phase5_hero] NO FILE WRITTEN: {fp}")

print(f"[phase5_hero] wall_time_s={t_render:.1f} open_s={t_open:.1f} total_s={t_total:.1f} "
      f"peak_rss_mb={peak_mb:.1f} spp={SPP} res={RES[0]}x{RES[1]} adaptive={'on' if ADAPTIVE else 'off'} "
      f"denoise={'on' if DENOISE else 'off'} out={fp}")
