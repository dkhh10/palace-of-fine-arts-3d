"""QA round 09: the cam06 gate needs a PAIR of frames (composited / un-composited), so QA renders the
un-composited twin of round09_06_aerial.png from the same master. Read-only: nothing is saved back.

    blender -b --python scripts/qa_r08_c06.py -- [--blend master.blend]

Writes renders/previews/qa/round09_06_aerial_nocomp.png (Eevee 1280x720, 32 TAA, LOD1 -- the same rig as the
round's Eevee pass, with scene.render.use_compositing off). The ratio itself is computed outside Blender by
`env_r7_measure.py --c06ratio <comp> <nocomp>` (environment's definition, docs/environment_notes.md).
"""
import bpy, sys, os, time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
import qa_cameras

args = common.script_args()
blend = Path(args[args.index("--blend") + 1]) if "--blend" in args else common.ROOT / "master.blend"

bpy.ops.wm.open_mainfile(filepath=str(blend), load_ui=False)
scene = bpy.context.scene
qa_cameras.ensure(scene)
common.set_lod(viewport=1, render=1)
try:
    import light_presets
    light_presets.apply_preview_eevee(scene, samples=32)
except Exception as e:
    print("[qa_c06] apply_preview_eevee failed:", e)

scene.render.use_compositing = False
scene.render.use_sequencer = False
scene.camera = bpy.data.objects["CAM_qa_06_aerial"]
scene.render.resolution_x, scene.render.resolution_y = 1280, 720
scene.render.resolution_percentage = 100
out = common.RENDERS / "previews" / "qa" / "round09_06_aerial_nocomp.png"
scene.render.filepath = str(out)
scene.render.image_settings.file_format = "PNG"
t0 = time.time()
bpy.ops.render.render(write_still=True)
print(f"[qa_c06] wrote {out} in {time.time() - t0:.1f}s (use_compositing off)")
