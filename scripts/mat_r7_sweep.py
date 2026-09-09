"""Round-7 water sweep: several settings of MAT_water_lagoon on ONE master, in ONE Blender session.

    blender -b --python scripts/mat_r7_sweep.py -- [--cases ctl,w1,w2] [--samples 64] [--full ctl]

Why a sweep and not a library rebuild per variant: QA-05-4 / lighting r12's hand-off 1 are three coupled numbers
(near-water saturation, near-water hue, the building's reflection) and round 6 already showed that every knob that
reaches one reaches the others.  Opening the 154 MB master costs ~40 s and a full hero 40 % of the render, so the
water cases are rendered as a BORDER crop of the hero (x 780-1560, y 700-1080) at the hero's own resolution: every
box QA-05-4 measures is inside it, the pixels are identical to a full render's, and one case costs ~70 s instead of
~240 s.  `--full <case>` renders that one case as a whole frame (the stone boxes need the rest of the image).

Cases set node values only, so nothing is written to any .blend: `WATER_MURK_GAIN` (a scalar on the murk albedo),
the Principled's Transmission Weight and Sheen Weight, `WATER_VOLUME` Density and `WATER_CHOP` (ripple amplitude).
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


# gain = scalar on the murk albedo; trans = Transmission Weight; vol = volume density; chop = ripple amplitude
CASES = {
    "ctl": dict(gain=1.00, trans=0.40, vol=0.70, chop=1.00, sheen=0.00),
    "w1":  dict(gain=1.00, trans=0.18, vol=0.70, chop=1.00, sheen=0.00),
    "w2":  dict(gain=1.00, trans=0.40, vol=0.12, chop=1.00, sheen=0.00),
    "w3":  dict(gain=0.70, trans=0.18, vol=0.12, chop=1.00, sheen=0.00),
    "w4":  dict(gain=0.70, trans=0.18, vol=0.12, chop=1.60, sheen=0.00),
    "w5":  dict(gain=0.45, trans=0.18, vol=0.12, chop=1.60, sheen=0.00),
    "w6":  dict(gain=0.70, trans=0.18, vol=0.12, chop=1.60, sheen=0.35),
    # the decisive one: murk albedo zero = a pure Fresnel mirror.  If the near-water hue / saturation barely move,
    # the water shader has no authority over them at QA's grazing crop and the numbers are the reflected sky's.
    "w7":  dict(gain=0.00, trans=0.18, vol=0.12, chop=1.00, sheen=0.00),
    "w8":  dict(gain=1.00, trans=0.40, vol=0.70, chop=2.60, sheen=0.00),
    "w9":  dict(gain=2.20, trans=0.18, vol=0.12, chop=1.60, sheen=0.00),
}
BORDER = (780 / 1920.0, 1560 / 1920.0, 1.0 - 1080 / 1080.0, 1.0 - 700 / 1080.0)   # min_x, max_x, min_y, max_y

SAMPLES = int(arg("--samples", 64))
WANT = str(arg("--cases", "ctl,w1,w2,w3,w4")).split(",")
FULL = str(arg("--full", "ctl")).split(",")
OUT = common.RENDERS / "previews" / "materials"
OUT.mkdir(parents=True, exist_ok=True)

t0 = time.time()
bpy.ops.wm.open_mainfile(filepath=str(common.ROOT / "master.blend"), load_ui=False)
scene = bpy.context.scene
bpy.context.view_layer.update()
print(f"[sweep] opened master in {time.time() - t0:.1f}s, {len(bpy.data.objects)} objects")

mat = bpy.data.materials.get("MAT_water_lagoon")
if mat is None:
    raise SystemExit("[sweep] MAT_water_lagoon missing")
nt = mat.node_tree
nodes = {n.name: n for n in nt.nodes}
prin = next(n for n in nt.nodes if n.bl_idname == "ShaderNodeBsdfPrincipled")
vol = next((n for n in nt.nodes if n.bl_idname == "ShaderNodeVolumePrincipled"), None)
gain = nodes.get("WATER_MURK_GAIN")
chop = nodes.get("WATER_CHOP")
print(f"[sweep] water nodes: principled={prin.name} volume={vol and vol.name} gain={gain and gain.name} chop={chop and chop.name}")

light_presets.apply_final_cycles(scene, samples=SAMPLES)
common.setup_scene(scene)
scene.render.image_settings.color_depth = "8"
for k, v in (("use_guiding", False), ("use_auto_tile", True), ("tile_size", 256)):
    if hasattr(scene.cycles, k):
        setattr(scene.cycles, k, v)
scene.camera = bpy.data.objects["CAM_qa_01_lagoon_hero"]
scene.render.resolution_x, scene.render.resolution_y = 1920, 1080

for name in WANT:
    c = CASES[name]
    if gain:
        gain.outputs[0].default_value = c["gain"]
    if chop:
        chop.outputs[0].default_value = c["chop"]
    prin.inputs["Transmission Weight"].default_value = c["trans"]
    prin.inputs["Sheen Weight"].default_value = c["sheen"]
    if vol:
        vol.inputs["Density"].default_value = c["vol"]
    full = name in FULL
    scene.render.use_border = not full
    scene.render.use_crop_to_border = False
    if not full:
        scene.render.border_min_x, scene.render.border_max_x = BORDER[0], BORDER[1]
        scene.render.border_min_y, scene.render.border_max_y = BORDER[2], BORDER[3]
    fp = OUT / f"r7w_{name}_hero.png"
    scene.render.filepath = str(fp)
    t = time.time()
    bpy.ops.render.render(write_still=True)
    print(f"[sweep] {name} {c} {'FULL' if full else 'border'} {time.time() - t:.1f}s -> {fp.name}")

print(f"[sweep] done in {time.time() - t0:.1f}s")
