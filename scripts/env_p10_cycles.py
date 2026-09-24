"""Phase 10 ENV: the one Cycles hero for the sheet (cam 01, 1920x1080, 32 spp, LOD0 render) on the worktree master.

    scripts/blender_run.sh 900 -- --background --python scripts/env_p10_cycles.py -- --tag after2 [--samples 32]
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


TAG = arg("--tag", "after")
SPP = int(arg("--samples", "32"))
OUT = common.RENDERS / "previews" / "environment"
OUT.mkdir(parents=True, exist_ok=True)

t0 = time.time()
bpy.ops.wm.open_mainfile(filepath=str(common.ROOT / "master.blend"), load_ui=False)
scene = bpy.context.scene
qa_cameras.ensure(scene)
common.set_lod(viewport=1, render=0)
import light_presets
light_presets.apply_final_cycles(scene, samples=SPP)
common.setup_scene(scene)
scene.render.image_settings.color_depth = "8"
scene.render.resolution_x, scene.render.resolution_y = 1920, 1080
scene.render.resolution_percentage = 100
scene.render.use_border = False
scene.camera = next(o for o in bpy.data.objects if o.name.startswith("CAM_qa_01_"))
fp = OUT / f"p10_cycles_{TAG}_cam01.png"
scene.render.filepath = str(fp)
bpy.ops.render.render(write_still=True)
print(f"[env_p10_cycles] {fp.name} {SPP} spp in {time.time() - t0:.1f}s")
