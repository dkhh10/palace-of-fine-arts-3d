"""QA exposure response sweep (QA / Critic owned). Renders the hero camera from an EXISTING master.blend at several
values of scene.view_settings.exposure and reports the display-referred luminance of the QA measurement regions, so the
"how many EV under the photograph" question can be answered with a measured response curve instead of a gamma guess
(AgX compresses highlights, so display ratio != scene ratio).

    blender -b --python scripts/qa_exposure_sweep.py -- [--evs 0 0.5 1.0] [--res 960 540] [--out DIR]

Nothing is saved back to master.blend; the file is opened read-only and the process exits when the script ends.
"""
import bpy, sys, os, time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common

args = common.script_args()


def arg(name, default=None, n=1):
    if name not in args:
        return default
    i = args.index(name) + 1
    vals = []
    for v in args[i:]:
        if v.startswith("--"):
            break
        vals.append(v)
        if n and len(vals) >= n:
            break
    return vals[0] if n == 1 else vals


EVS = [float(v) for v in (arg("--evs", ["0", "0.5", "1.0"], n=0) or ["0", "0.5", "1.0"])]
RES = [int(v) for v in arg("--res", ["960", "540"], n=2)]
OUT = Path(arg("--out", "/tmp/qa_exposure"))
OUT.mkdir(parents=True, exist_ok=True)

bpy.ops.wm.open_mainfile(filepath=str(common.ROOT / "master.blend"), load_ui=False)
scene = bpy.context.scene
import light_presets
light_presets.apply_preview_eevee(scene, samples=32)
scene.render.resolution_x, scene.render.resolution_y = RES
scene.render.resolution_percentage = 100
cam = bpy.data.objects.get("CAM_qa_01_lagoon_hero")
scene.camera = cam
base = scene.view_settings.exposure
print(f"[qa_exposure] base view_settings.exposure = {base}")

for ev in EVS:
    scene.view_settings.exposure = base + ev
    fp = OUT / f"hero_ev{ev:+.2f}.png"
    scene.render.filepath = str(fp)
    t = time.time()
    bpy.ops.render.render(write_still=True)
    print(f"[qa_exposure] ev {ev:+.2f} -> {fp} in {time.time() - t:.1f}s")

print("[qa_exposure] done")
