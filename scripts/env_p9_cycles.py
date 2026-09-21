"""Phase 9 ENV / 8d R3: the Cycles control.  The phase closes with a 4K Cycles hero, so the tile has to be
visible to Cycles and not only to Eevee.  Proof without a second master build: master.blend reads the tile PNGs
from disk at open (`//assets/textures/backdrop/*.png`), so the same master renders with the tile and with a flat
0.505 grey stand-in of the same size, and the pair is a true before / after for the Cycles path.

    scripts/blender_run.sh 900 -- --background --python scripts/env_p9_cycles.py -- --tag cyc_after --cam 06
"""
import os
import sys
import time

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
import qa_cameras

args = common.script_args()


def arg(name, default=None):
    if name not in args:
        return default
    i = args.index(name) + 1
    return args[i] if i < len(args) and not args[i].startswith("--") else default


TAG = arg("--tag", "cyc_after")
CAM = arg("--cam", "06")
SPP = int(arg("--samples", "24"))
OUT = common.RENDERS / "previews" / "environment"
OUT.mkdir(parents=True, exist_ok=True)

t0 = time.time()
bpy.ops.wm.open_mainfile(filepath=str(common.ROOT / "master.blend"), load_ui=False)
scene = bpy.context.scene
qa_cameras.ensure(scene)
common.set_lod(viewport=1, render=1)
import light_presets
light_presets.apply_final_cycles(scene, samples=SPP)
common.setup_scene(scene)
scene.render.image_settings.color_depth = "8"
scene.render.resolution_x, scene.render.resolution_y = 1920, 1080
# render only the cam06 city band (x 300-940, y 0-200 of the 1920x1080 frame): a control, not a hero, and a
# border keeps it a ~1 minute job instead of a ten minute one.  use_crop_to_border keeps the pixel grid, so the
# two frames of the pair are directly subtractable.
scene.render.use_border = True
scene.render.use_crop_to_border = True
scene.render.border_min_x, scene.render.border_max_x = 300 / 1920, 940 / 1920
scene.render.border_min_y, scene.render.border_max_y = 1.0 - 200 / 1080, 1.0
scene.camera = next(o for o in bpy.data.objects if o.name.startswith(f"CAM_qa_{CAM}_"))
fp = OUT / f"p9r3_{TAG}_cam{CAM}.png"
scene.render.filepath = str(fp)
bpy.ops.render.render(write_still=True)
print(f"[env_p9_cycles] {fp.name} {SPP} spp in {time.time() - t0:.1f}s")
