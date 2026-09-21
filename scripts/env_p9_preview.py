"""Phase 9 ENV / 8d R3 preview pass: Eevee, 1920x1080, from the rebuilt master.

1920x1080 is not a choice: the 8d backdrop boxes (`scripts/qa_r22_probe.BACKDROP`) are stated in 1920x1080 frame
pixels and `hf` (mean |laplacian|) is resolution-dependent, so measuring a 1280x720 preview upscaled to 1920
would read several times low.  Rendering native keeps the before / after and the photo columns comparable.

    scripts/blender_run.sh 900 -- --background --python scripts/env_p9_preview.py -- --tag before --cams 01 05 06

Writes renders/previews/environment/p9r3_<tag>_cam<NN>.png.
"""
import os
import sys
import time

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
import qa_cameras

args = common.script_args()


def arg(name, default=None, n=1):
    if name not in args:
        return default
    i = args.index(name) + 1
    vals = [v for v in args[i:i + n] if not v.startswith("--")]
    return (vals[0] if vals else default) if n == 1 else vals


TAG = arg("--tag", "after")
CAMS = arg("--cams", ["01", "05", "06"], n=6)
SAMPLES = int(arg("--samples", 32))
BLEND = arg("--blend", str(common.ROOT / "master.blend"))
OUT = common.RENDERS / "previews" / "environment"
OUT.mkdir(parents=True, exist_ok=True)

t0 = time.time()
bpy.ops.wm.open_mainfile(filepath=BLEND, load_ui=False)
scene = bpy.context.scene
qa_cameras.ensure(scene)
common.set_lod(viewport=1, render=1)
import light_presets
light_presets.apply_preview_eevee(scene, samples=SAMPLES)
common.setup_scene(scene)
scene.render.image_settings.color_depth = "8"
scene.render.resolution_x, scene.render.resolution_y = 1920, 1080
print(f"[env_p9_preview] opened {BLEND} in {time.time() - t0:.1f}s, tag={TAG}, cams={CAMS}")

for c in CAMS:
    cam = next((o for o in bpy.data.objects if o.name.startswith(f"CAM_qa_{c}_")), None)
    if cam is None:
        print(f"[env_p9_preview] no camera for {c}")
        continue
    scene.camera = cam
    fp = OUT / f"p9r3_{TAG}_cam{c}.png"
    scene.render.filepath = str(fp)
    t = time.time()
    bpy.ops.render.render(write_still=True)
    print(f"[env_p9_preview] {fp.name} in {time.time() - t:.1f}s")
print(f"[env_p9_preview] done in {time.time() - t0:.1f}s")
