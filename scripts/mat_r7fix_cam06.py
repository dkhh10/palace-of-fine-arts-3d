"""QA-02-6 regression check for the shipped water: is the lagoon still not black FROM ABOVE?

    blender -b --python scripts/mat_r7fix_cam06.py -- [--gains 0.15,1.00] [--engines eevee,cycles] [--samples 32]

Round 7 shipped `MAT_water_lagoon` with WATER_MURK_GAIN 0.15 behind a Fresnel weight (0.15 + 0.85 (1-F)^2), i.e.
~0.054 of the round-6 murk on the hero's grazing water and ~0.114 at cam06's ~30 deg.  The round-7 review found
that the "leaves the aerial lagoon alone" argument had been computed for a 0.55 gain and that no cam06 render was
made at the shipped 0.15, so QA-02-6 ("the lagoon reads as a black mirror from above", round 2) was untested.

This renders CAM_qa_06_aerial at QA's own 1280x720 at the shipped gain and at the round-6 gain 1.00, in both
engines, on ONE open master, and prints the lagoon boxes.  Two engines because MAT_water_lagoon is a split shader:
the Cycles branch is the Fresnel-weighted murk under a Principled, the Eevee branch is a separate Diffuse+Glossy
pair fed by WATER_MURK_EEVEE which the gain does not touch at all -- so the Eevee pair is expected to be identical
and is the control that proves QA's Eevee preview pass cannot see this change.
"""
import bpy, sys, os, time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
import light_presets

args = common.script_args()


def arg(name, default=None):
    if name in args:
        i = args.index(name)
        return args[i + 1] if i + 1 < len(args) else True
    return default


GAINS = [float(v) for v in str(arg("--gains", "0.15,1.00")).split(",")]
ENGINES = str(arg("--engines", "eevee,cycles")).split(",")
SAMPLES = int(arg("--samples", 32))
RES = (1280, 720)
OUT = common.RENDERS / "previews" / "materials"
OUT.mkdir(parents=True, exist_ok=True)

t0 = time.time()
bpy.ops.wm.open_mainfile(filepath=str(common.ROOT / "master.blend"), load_ui=False)
scene = bpy.context.scene
bpy.context.view_layer.update()
print(f"[cam06] opened master in {time.time() - t0:.1f}s, {len(bpy.data.objects)} objects")

mat = bpy.data.materials["MAT_water_lagoon"]
gain = {n.name: n for n in mat.node_tree.nodes}["WATER_MURK_GAIN"]
print(f"[cam06] shipped WATER_MURK_GAIN = {gain.outputs[0].default_value:.3f}")

cam = bpy.data.objects["CAM_qa_06_aerial"]
scene.camera = cam
scene.render.resolution_x, scene.render.resolution_y = RES
scene.render.image_settings.color_depth = "8"

for eng in ENGINES:
    if eng.startswith("ee"):
        light_presets.apply_preview_eevee(scene, samples=max(16, SAMPLES))
    else:
        light_presets.apply_final_cycles(scene, samples=SAMPLES)
    common.setup_scene(scene)
    for k, v in (("use_guiding", False), ("use_auto_tile", True), ("tile_size", 256)):
        if hasattr(scene.cycles, k):
            setattr(scene.cycles, k, v)
    for g in GAINS:
        gain.outputs[0].default_value = g
        fp = OUT / f"r7fix_cam06_{eng}_g{g:.2f}.png"
        scene.render.filepath = str(fp)
        t = time.time()
        bpy.ops.render.render(write_still=True)
        print(f"[cam06] {eng} gain {g:.2f} {RES[0]}x{RES[1]} {SAMPLES} spp in {time.time() - t:.1f}s -> {fp.name}")

print(f"[cam06] done in {time.time() - t0:.1f}s")
