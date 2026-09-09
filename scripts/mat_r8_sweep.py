"""Round-8 water sweep: WATER_BUMP_DIST (the ripple SLOPE) on ONE master, in ONE Blender session.

    blender -b --python scripts/mat_r8_sweep.py -- [--cases w0,w1,w2,w3] [--samples 64]

QA-06-3 is a blocker with three coupled numbers on the hero (reflection R-B / lum, near-water hue / saturation,
the ripples' R-B).  Rounds 4-7 swept the murk, the transmission, the volume, the sheen and `WATER_CHOP` and none
of them moved the reflection's colour, because none of them is the term that decides it.  `mat_r8_probe.py` shows
what does: the mirror ray out of the reflection box leaves at +7.3 deg on flat water and lands on a shore willow,
on the backdrop hall seen through the rotunda arch, or on sky, while the SUNLIT stone sits at +17 to +23 deg of
ray elevation, i.e. behind a ripple facet pitched +5 to +8 deg.  The knob that reaches those facets is the Bump
node's DISTANCE (its Strength only blends toward the bumped normal and the shipped chop already sits at ~0.94 of
the way there, which is why chop sweeps saturated).

Each case is a border crop of the hero (x 780-1560, y 700-1080) at the hero's own resolution -- water_refl,
near_water_sky and ripples are all inside it -- so a case costs ~70 s instead of ~240 s and its pixels are
identical to a full render's.  Measure the PNGs with `python3 scripts/mat_r8_measure.py <png>...`.
"""
import bpy, sys, os, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
import light_presets

args = common.script_args()


def arg(name, default=None):
    if name in args:
        i = args.index(name)
        return args[i + 1] if i + 1 < len(args) else True
    return default


CASES = {                          # dist = WATER_BUMP_DIST (m of bump height -> ripple slope)
    "w0": dict(dist=0.030),        # round-7 shipped water: the control
    "w1": dict(dist=0.070),
    "w2": dict(dist=0.130),
    "w3": dict(dist=0.220),
}
BORDER = (780 / 1920.0, 1560 / 1920.0, 0.0, 1.0 - 700 / 1080.0)   # min_x, max_x, min_y, max_y

SAMPLES = int(arg("--samples", 64))
WANT = str(arg("--cases", "w0,w1,w2,w3")).split(",")
OUT = common.RENDERS / "previews" / "materials"
OUT.mkdir(parents=True, exist_ok=True)

t0 = time.time()
bpy.ops.wm.open_mainfile(filepath=str(common.ROOT / "master.blend"), load_ui=False)
scene = bpy.context.scene
bpy.context.view_layer.update()
print(f"[r8sweep] opened master in {time.time() - t0:.1f}s, {len(bpy.data.objects)} objects")

mat = bpy.data.materials["MAT_water_lagoon"]
dist = {n.name: n for n in mat.node_tree.nodes}.get("WATER_BUMP_DIST")
if dist is None:
    raise SystemExit("[r8sweep] WATER_BUMP_DIST missing -- rebuild assets/materials.blend and master.blend")

light_presets.apply_final_cycles(scene, samples=SAMPLES)
common.setup_scene(scene)
scene.render.image_settings.color_depth = "8"
for k, v in (("use_guiding", False), ("use_auto_tile", True), ("tile_size", 256)):
    if hasattr(scene.cycles, k):
        setattr(scene.cycles, k, v)
scene.camera = bpy.data.objects["CAM_qa_01_lagoon_hero"]
scene.render.resolution_x, scene.render.resolution_y = 1920, 1080
scene.render.use_border, scene.render.use_crop_to_border = True, False
scene.render.border_min_x, scene.render.border_max_x = BORDER[0], BORDER[1]
scene.render.border_min_y, scene.render.border_max_y = BORDER[2], BORDER[3]

for name in WANT:
    c = CASES[name]
    dist.outputs[0].default_value = c["dist"]
    fp = OUT / f"r8w_{name}_hero.png"
    scene.render.filepath = str(fp)
    t = time.time()
    bpy.ops.render.render(write_still=True)
    print(f"[r8sweep] {name} dist={c['dist']} {time.time() - t:.1f}s -> {fp.name}")

print(f"[r8sweep] done in {time.time() - t0:.1f}s")
