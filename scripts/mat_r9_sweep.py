"""Round-9 water sweep: how much of the grazing mirror is tinted (`WATER_GLOSS_MIX`).

    blender -b --python scripts/mat_r9_sweep.py -- [--cases 0,0.45,0.75,1.0] [--spp 64]

Renders the hero from master.blend as a BORDER on rows 740-1080 only -- every water box QA scores
(water_refl 900 760 1020 840, ripples 1100 960 1500 1060, near_water_sky 1150 1000 1450 1050, lagoon_flank
100 900 400 960) lives there, and 31 % of a frame is what a four-case sweep is allowed to cost in a round whose
budget is three hero frames.  Prints the table with `mat_r9_measure`'s windows.

`WATER_GLOSS_MIX` = 0 is bit-identical to the round-8 water, so case 0 is the BEFORE column and the sweep is
self-contained on one master.
"""
import bpy, sys, os, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
import light_presets

args = common.script_args()
CASES = [float(v) for v in (args[args.index("--cases") + 1] if "--cases" in args else "0,0.45,0.75,1.0").split(",")]
SPP = int(args[args.index("--spp") + 1]) if "--spp" in args else 64
BORDER = (740, 1080)
OUT = common.RENDERS / "previews" / "materials"
OUT.mkdir(parents=True, exist_ok=True)


def require_value_node(node, name):
    """docs/reviews/mat_r8_review.md finding 1: writing outputs[0].default_value on anything but a Value node is a
    silent no-op (a Map Range ignores it), which produces identical frames and a table that looks reproduced."""
    if node is None:
        raise SystemExit(f"[r9sweep] node {name} not found in MAT_water_lagoon")
    if node.type != "VALUE":
        raise SystemExit(f"[r9sweep] {name} is a {node.type} node, not VALUE: driving outputs[0].default_value "
                         f"would be a silent no-op. Drive its input instead.")


t0 = time.time()
bpy.ops.wm.open_mainfile(filepath=str(common.ROOT / "master.blend"), load_ui=False)
scene = bpy.context.scene
mat = bpy.data.materials.get("MAT_water_lagoon")
if mat is None:
    raise SystemExit("[r9sweep] MAT_water_lagoon not in master.blend")
node = mat.node_tree.nodes.get("WATER_GLOSS_MIX")
require_value_node(node, "WATER_GLOSS_MIX")
print(f"[r9sweep] opened master in {time.time() - t0:.1f}s, {len(bpy.data.objects)} objects; "
      f"WATER_GLOSS_MIX shipped at {node.outputs[0].default_value}")

light_presets.apply_final_cycles(scene, samples=SPP)
for k, v in (("use_guiding", False), ("use_auto_tile", True), ("tile_size", 256)):
    if hasattr(scene.cycles, k):
        setattr(scene.cycles, k, v)
common.setup_scene(scene)
scene.render.image_settings.color_depth = "8"
scene.camera = bpy.data.objects["CAM_qa_01_lagoon_hero"]
scene.render.resolution_x, scene.render.resolution_y = 1920, 1080
scene.render.use_border = True
scene.render.use_crop_to_border = False
scene.render.border_min_x, scene.render.border_max_x = 0.0, 1.0
scene.render.border_min_y = 1.0 - BORDER[1] / 1080.0
scene.render.border_max_y = 1.0 - BORDER[0] / 1080.0

for c in CASES:
    node.outputs[0].default_value = c
    fp = OUT / f"r9_water_g{str(c).replace('.', 'p')}.png"
    scene.render.filepath = str(fp)
    t = time.time()
    bpy.ops.render.render(write_still=True)
    print(f"[r9sweep] WATER_GLOSS_MIX {c:.2f} {time.time() - t:.1f}s -> {fp.name}")

print(f"[r9sweep] done in {time.time() - t0:.1f}s")
