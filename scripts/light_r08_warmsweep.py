"""Round-08b sweep for the sunlit-stone chroma problem (materials' hand-off after QA-02-4).

Materials measured that at +0.9 EV albedo has no authority left over chroma: a 44 % cut of albedo blue moved display
blue by 3 %. Hue is now right (attic 33.8 vs ref 33.9) but the sunlit attic's R-B spread is 81 against ref 169's 127 -
the stone reads pale and clean rather than golden. The excess is in BLUE (render 129 vs ref 93 at matching R), and on
a sunlit face the blue comes from the sky fill, so the levers are the sun:sky ratio, the sun's own colour, and the
exposure that decides how far up the AgX shoulder the stone sits.

    blender -b --python scripts/light_r08_warmsweep.py -- [--res 960 540] [--samples 32] [--cases ...]

Each case is `sky_strength,camera_boost,sun_blue_mult,exposure_delta`. camera_boost is varied INVERSELY to
sky_strength so that what the camera sees of the sky is unchanged (visible sky = strength x boost) while the diffuse
LIGHTING contribution changes - that separation is exactly what light_calibrate.make_sky_world's node graph is for.
Nothing is saved back; the file is opened read-only and the process exits when the script ends.
"""
import bpy, os, sys, time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
import light_presets as lp

args = common.script_args()


def arg(name, default, n=0):
    if name not in args:
        return default
    out = []
    for v in args[args.index(name) + 1:]:
        if v.startswith("--"):
            break
        out.append(v)
        if n and len(out) >= n:
            break
    return out or default


# strength, camera_boost, sun blue multiplier, exposure delta [, AgX look]. The look is the one lever round 05
# rejected ("Punchy crushes the sky-lit shade") under conditions that no longer hold: at +0.9 EV the shade is 25 %
# BRIGHTER than ref 169, so crushing it is now the correction rather than the damage.
CASES = arg("--cases", ["2.0,1.50,1.00,0.00", "1.0,3.00,1.00,0.00", "1.0,3.00,1.00,-0.35",
                        "0.6,5.00,1.00,0.00", "1.0,3.00,0.70,0.00"])
RES = [int(v) for v in arg("--res", ["960", "540"], n=2)]
SAMPLES = int(arg("--samples", ["32"], n=1)[0])
OUT = Path(arg("--out", [str(common.RENDERS / "previews" / "lighting")], n=1)[0])
OUT.mkdir(parents=True, exist_ok=True)

bpy.ops.wm.open_mainfile(filepath=str(common.ROOT / "master.blend"), load_ui=False)
scene = bpy.context.scene
lp.apply_final_cycles(scene, samples=SAMPLES)
common.setup_scene(scene)
scene.render.image_settings.color_depth = "8"
scene.render.resolution_x, scene.render.resolution_y = RES
scene.render.resolution_percentage = 100
scene.camera = bpy.data.objects.get("CAM_qa_01_lagoon_hero")

world = scene.world
nt = world.node_tree
n_strength = nt.nodes.get("strength")        # MULTIPLY: inputs[1] = sky strength (lighting AND visible)
n_boost = nt.nodes.get("camera_boost")       # MULTIPLY_ADD: inputs[1] = boost - 1 (camera + glossy only)
sun = bpy.data.objects.get("LIGHT_sun")
base_exp = scene.view_settings.exposure
base_col = tuple(sun.data.color)
print(f"[warmsweep] world '{world.name}' strength node {n_strength is not None}, boost node {n_boost is not None}")
print(f"[warmsweep] base exposure {base_exp:.4f}, sun colour {tuple(round(c,3) for c in base_col)}")

for case in CASES:
    parts = case.split(",")
    s, b, bm, de = (float(x) for x in parts[:4])
    look = parts[4] if len(parts) > 4 else None
    if look:
        try:
            scene.view_settings.look = look
        except Exception as e:
            print(f"[warmsweep] look {look!r} rejected: {e}")
            continue
    else:
        scene.view_settings.look = "AgX - Base Contrast"
    if n_strength:
        n_strength.inputs[1].default_value = s
    if n_boost:
        n_boost.inputs[1].default_value = b - 1.0
    sun.data.color = (base_col[0], base_col[1], base_col[2] * bm)
    scene.view_settings.exposure = base_exp + de
    tag = f"s{s:.2f}_b{b:.2f}_bm{bm:.2f}_e{de:+.2f}" + (("_" + look.replace("AgX - ", "").replace(" ", "")) if look else "")
    fp = OUT / f"r08warm_{tag}.png"
    scene.render.filepath = str(fp)
    t = time.time()
    bpy.ops.render.render(write_still=True)
    print(f"[warmsweep] {tag}: sky lighting x{s}, visible sky x{s*b:.2f}, sun blue x{bm}, exposure "
          f"{base_exp + de:.3f} -> {fp.name} ({time.time() - t:.1f}s)")

print("[warmsweep] done")
