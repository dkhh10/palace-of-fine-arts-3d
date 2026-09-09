"""Does the projection deliver what its map asks?  `Photo` 0 vs 1 on one open master (review finding 4).

    blender -b --python scripts/mat_r9_phtest.py -- [--hero] [--spp 64] [--tag r9c]

Round 9's authority for "the map delivers a third of its own correction" was `/tmp/phtest.py`, an uncommitted
throwaway (docs/reviews/mat_r9_review.md finding 4, the same class as the round-8 finding 2).  This is that test,
committed, and extended to score itself against the map's own metadata.

What it does, in ONE open master:
  --hero   (optional) the full 1920x1080 Cycles acceptance frame at the SHIPPED `Photo` weight.
  always   the same camera as a BORDER of rows 190-320 -- the rotunda's attic and entablature, 12 % of a frame --
           rendered twice, with `Photo` forced to 0.0 and to 1.0 on every band material's projector group.
Then, for each of QA's boxes inside those rows, it prints

    asked      the display change the ratio map wants there, from projection_meta.json `display_ask_pct`
    delivered  the display change measured between the two border frames
    ratio      delivered / asked -- 1.00 is the test passing

`Photo` is forced to 1.0 (not to the shipped 0.6) because the map's ask is quoted at full weight and because the
shader's mix is a lerp: at weight w the delivered change is not w x the full-weight change, it is the change due
to a multiplier lerp(1, S, w), which the meta quotes separately as `display_pct_w06`.
"""
import bpy, sys, os, time, json
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
import light_presets
import mat_lib as ML

args = common.script_args()
SPP = int(args[args.index("--spp") + 1]) if "--spp" in args else 64
TAG = args[args.index("--tag") + 1] if "--tag" in args else "r9c"
DO_HERO = "--hero" in args
CAM = "CAM_qa_01_lagoon_hero"
BORDER = (190, 320)                       # rows of 1080: the attic string course down to the architrave
OUT = common.RENDERS / "previews" / "materials"
# QA's boxes (scripts/mat_r7_measure.py BOXES) that lie inside BORDER
BOXES = dict(attic_sunlit=(900, 222, 1020, 256), attic_shaded=(1110, 225, 1150, 260),
             entablature=(900, 262, 1020, 296))

lum = lambda a: 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def photo_nodes():
    """Every `Photo` input of every material that carries the concrete group (the band materials)."""
    out = []
    for m in bpy.data.materials:
        if not m.node_tree:
            continue
        for n in m.node_tree.nodes:
            if n.type == "GROUP" and n.node_tree and "Photo" in n.inputs:
                out.append(n.inputs["Photo"])
    return out


def render(scene, path, border=None, spp=SPP):
    light_presets.apply_final_cycles(scene, samples=spp)
    for k, v in (("use_guiding", False), ("use_auto_tile", True), ("tile_size", 256)):
        if hasattr(scene.cycles, k):
            setattr(scene.cycles, k, v)
    common.setup_scene(scene)
    scene.render.image_settings.color_depth = "8"
    scene.render.resolution_x, scene.render.resolution_y = 1920, 1080
    if border:
        scene.render.use_border = True
        scene.render.use_crop_to_border = False
        scene.render.border_min_x, scene.render.border_max_x = 0.0, 1.0
        scene.render.border_min_y = 1.0 - border[1] / 1080.0
        scene.render.border_max_y = 1.0 - border[0] / 1080.0
    else:
        scene.render.use_border = False
    scene.render.filepath = str(path)
    t = time.time()
    bpy.ops.render.render(write_still=True)
    print(f"[ph] {path.name} border={border} {spp}spp {time.time() - t:.1f}s")
    return np.asarray(bpy.data.images.load(str(path)).pixels[:], dtype=np.float64
                      ).reshape(1080, 1920, 4)[::-1, :, :3] * 255.0


t0 = time.time()
bpy.ops.wm.open_mainfile(filepath=str(common.ROOT / "master.blend"), load_ui=False)
scene = bpy.context.scene
scene.camera = bpy.data.objects[CAM]
bpy.context.view_layer.update()
inputs = photo_nodes()
shipped = float(inputs[0].default_value) if inputs else 0.0
print(f"[ph] opened master in {time.time() - t0:.1f}s, {len(bpy.data.objects)} objects, "
      f"{len(inputs)} Photo inputs at the shipped weight {shipped}")

if DO_HERO:
    render(scene, OUT / f"{TAG}_cycles_01_lagoon_hero.png", None)

frames = {}
for w in (0.0, 1.0):
    for s in inputs:
        s.default_value = w
    frames[w] = render(scene, OUT / f"{TAG}_phtest_{w:.1f}.png", BORDER)
for s in inputs:
    s.default_value = shipped

meta_p = ML.TEX_DIR / "projection" / "projection_meta.json"
asks = json.loads(meta_p.read_text()).get("display_ask_pct", {}) if meta_p.exists() else {}
print(f"[ph] {'box':16s} {'Photo 0':>9s} {'Photo 1':>9s} {'delivered':>10s} {'asked':>8s} {'delivered/asked':>16s}")
for nm, (x0, y0, x1, y1) in BOXES.items():
    a = float(lum(frames[0.0][y0:y1, x0:x1]).mean())
    b = float(lum(frames[1.0][y0:y1, x0:x1]).mean())
    d = 100.0 * (b / a - 1.0)
    ask = asks.get(nm, {}).get("display_pct_w1")
    r = f"{d / ask:16.2f}" if ask not in (None, 0.0) else f"{'-':>16s}"
    print(f"[ph] {nm:16s} {a:9.1f} {b:9.1f} {d:+9.2f} % {ask if ask is None else f'{ask:+7.2f}'} % {r}")
print(f"[ph] done in {time.time() - t0:.1f}s")
