"""Phase 10 r1, steps 2 and 5 -- per-camera world-position / normal passes from the registered photo cameras.

    scripts/blender_run.sh 1800 -- --background <file.blend> --python scripts/mat_p10_depth.py -- \
        --out <dir> [--cams 10,31,67] [--scale 0.5] [--arch-only] [--clip 12] [--hide ENV_backdrop,ENV_terrain]   (clip: skip the terrain / ENV
        within 12 m of a registered camera that sits a few decimetres under ENV's ground)

Reads assets/textures/projection2/cameras.json (world K, R, t per image). For every camera: a Blender pinhole camera
(COLMAP SIMPLE_RADIAL radial term is NOT rendered; the numpy side applies k1 when it maps render pixels to photo
pixels), Cycles CPU, 1 spp, pixel filter 0.01 (each pixel = the ray through its centre), multilayer EXR with the
Position and Normal passes (world space) at the registered size x --scale. Background = +inf (position 0, alpha 0).
No save. With --arch-only every non-ARCH object is hidden from render (the step-2 edge check on architecture.blend).
LOD: render LOD0 (common.set_lod), as master's render setting.
"""
import bpy, sys, os, json, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
from mathutils import Matrix

args = common.script_args()
def arg(k, d=None):
    return args[args.index(k) + 1] if k in args else d
OUT = common.ROOT / arg("--out", "assets/textures/projection2/work/depth")
OUT.mkdir(parents=True, exist_ok=True)
SCALE = float(arg("--scale", "1.0"))
cams = json.loads((common.ASSETS / "textures" / "projection2" / "cameras.json").read_text())["cameras"]
sel = arg("--cams")
if sel:
    keep = {int(x) for x in sel.split(",")}
    todo = [(k, c) for k, c in enumerate(cams) if k in keep]
else:
    todo = list(enumerate(cams))

common.set_lod(viewport=1, render=0)
scene = bpy.context.scene
if "--arch-only" in args:
    arch = {o.name for o in bpy.data.collections["ARCH"].all_objects}
    for o in scene.objects:
        if o.name not in arch:
            o.hide_render = True
HIDE = [h for h in arg("--hide", "").split(",") if h]
for o in scene.objects:                       # e.g. ENV_backdrop,ENV_terrain: several registered cameras stand inside
    if any(o.name.startswith(h) for h in HIDE):   # ENV's backdrop houses / canopy on the east shore (ray probe)
        o.hide_render = True
for o in scene.objects:                       # water / glass / volumes must not stop the position ray
    if o.type == "MESH" and ("water" in o.name.lower() or "lagoon" in o.name.lower()) and not o.name.startswith("ARCH"):
        o.hide_render = True
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = 1
scene.cycles.use_adaptive_sampling = False
scene.cycles.use_denoising = False
scene.cycles.max_bounces = 0
scene.cycles.filter_width = 0.01
scene.render.film_transparent = True
scene.render.resolution_percentage = 100
scene.render.use_persistent_data = True
vl = scene.view_layers[0]
vl.use_pass_position = True
vl.use_pass_normal = True
vl.use_pass_z = True
scene.world = scene.world or bpy.data.worlds.new("W")
st = scene.render.image_settings
st.media_type = "MULTI_LAYER_IMAGE"
st.file_format = "OPEN_EXR_MULTILAYER"
st.color_depth = "32"
st.exr_codec = "ZIP"

cd = bpy.data.cameras.new("P10CAM")
co = bpy.data.objects.new("P10CAM", cd)
scene.collection.objects.link(co)
scene.camera = co
flip = Matrix(((1, 0, 0), (0, -1, 0), (0, 0, -1)))
for k, c in todo:
    W, H = c["size"]
    w, h = max(1, round(W * SCALE)), max(1, round(H * SCALE))
    K = c["K"]; f, cx, cy = K[0][0] * w / W, K[0][2] * w / W, K[1][2] * h / H
    scene.render.resolution_x, scene.render.resolution_y = w, h
    cd.sensor_fit = "HORIZONTAL" if w >= h else "VERTICAL"
    sw = 36.0
    cd.sensor_width = cd.sensor_height = sw
    big = max(w, h)
    cd.lens = f * sw / big
    cd.shift_x = -(cx - w / 2) / big
    cd.shift_y = (cy - h / 2) / big
    cd.clip_start, cd.clip_end = float(arg("--clip", "0.5")), 5000.0
    R = Matrix(c["R"])
    Rc2w = R.transposed() @ flip
    M = Rc2w.to_4x4(); M.translation = c["centre"]
    co.matrix_world = M
    scene.render.filepath = str(OUT / f"cam_{k:02d}.exr")
    bpy.ops.render.render(write_still=True)
    print(f"[p10depth] cam {k:02d} {c['file'][:40]} {w}x{h} lens {cd.lens:.2f}", flush=True)
(OUT / "meta.json").write_text(json.dumps(dict(scale=SCALE, cams=[k for k, _ in todo])))
print("[p10depth] done")
