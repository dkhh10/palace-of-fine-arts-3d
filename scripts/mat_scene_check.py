"""Materials verification inside the FULL assembled scene (round 3, QA-02-2 / -3 / -6).

    blender -b --python scripts/mat_scene_check.py -- [--blend master.blend] [--samples 48] [--tag r3]

The lineup in materials.blend cannot answer "does the algae band read at the waterline in the master" or "is the
stone still blotchy at 100 m", because it has neither ARCH's geometry nor ENV's water. This opens the assembled
master, adds two materials-owned close cameras (never saved back), and renders them with the lighting agent's final
Cycles preset:

  CAM_mat_scene_waterline  - a 50 mm three-quarter close on the podium / rostra where the stone meets z = WATER_Z,
                             placed from the actual bounding box of the podium objects so it does not need hand-tuning.
  CAM_mat_scene_stone      - a long lens on the entablature / spandrel zone from the hero station, i.e. QA's
                             "1:1 crop" of the hero, rendered directly instead of upscaled.

Outputs renders/previews/materials/<tag>_scene_<name>.png. Nothing is written back to any .blend.
"""
import bpy, sys, os, time, math
from pathlib import Path
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common

args = common.script_args()


def arg(name, default=None):
    if name in args:
        i = args.index(name)
        return args[i + 1] if i + 1 < len(args) else True
    return default


BLEND = Path(arg("--blend", str(common.ROOT / "master.blend")))
SAMPLES = int(arg("--samples", 48))
TAG = str(arg("--tag", "r3"))
OUT = common.RENDERS / "previews" / "materials"
OUT.mkdir(parents=True, exist_ok=True)

t0 = time.time()
bpy.ops.wm.open_mainfile(filepath=str(BLEND), load_ui=False)
scene = bpy.context.scene
print(f"[mat_scene] opened {BLEND.name} in {time.time() - t0:.1f}s; {len(bpy.data.objects)} objects")


def visible_bbox(pred):
    lo = Vector((1e9, 1e9, 1e9))
    hi = Vector((-1e9, -1e9, -1e9))
    n = 0
    for o in scene.objects:
        if o.type != "MESH" or o.hide_render or not pred(o.name):
            continue
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c)
            lo = Vector((min(lo[i], w[i]) for i in range(3)))
            hi = Vector((max(hi[i], w[i]) for i in range(3)))
        n += 1
    return (lo, hi, n) if n else (None, None, 0)


def add_cam(name, loc, aim, lens=50.0):
    cam = bpy.data.cameras.new(name)
    cam.lens = lens
    cam.clip_start, cam.clip_end = 0.1, 2000.0
    ob = bpy.data.objects.new(name, cam)
    scene.collection.objects.link(ob)
    ob.location = Vector(loc)
    d = Vector(aim) - Vector(loc)
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    return ob


lo, hi, n = visible_bbox(lambda s: s.startswith("ARCH_site"))
if n:
    print(f"[mat_scene] ARCH_site bbox from {n} objects: {[round(v,1) for v in lo]} .. {[round(v,1) for v in hi]}")

# Both close cameras stand at the hero station and use long lenses, so they crop exactly what QA crops out of the
# hero at 1:1 rather than showing a view nobody scores. (A bbox-placed camera picked up the whole site and framed a
# lawn instead of the shoreline.)
hero = bpy.data.objects.get("CAM_qa_01_lagoon_hero")
hloc = hero.location.copy() if hero else Vector((-16.0, 113.9, 1.0))
# waterline: the shore / podium base in front of the rotunda, where stone, rip-rap and z = WATER_Z meet
add_cam("CAM_mat_scene_waterline", hloc, Vector((-6.0, 34.0, -1.0)), lens=200.0)
# stone: the entablature / spandrel band, QA's "clean CAD at 1:1" crop
add_cam("CAM_mat_scene_stone", hloc, Vector((-2.0, 6.0, 20.0)), lens=135.0)

import light_presets
light_presets.apply_final_cycles(scene, samples=SAMPLES)
common.setup_scene(scene)
scene.render.image_settings.color_depth = "8"

# The merged lighting.blend still carries round 2's exposure; the lighting agent is raising it by +0.9 EV this round
# (QA-02-4). Judge materials at the exposure they will ship at, so albedo does not silently compensate for it.
EV = float(arg("--ev", 0.9))
scene.view_settings.exposure += EV
print(f"[mat_scene] view exposure {scene.view_settings.exposure - EV:.4f} {EV:+.2f} EV -> {scene.view_settings.exposure:.4f}")

JOBS = [("waterline", "CAM_mat_scene_waterline", (1600, 900)),
        ("stone", "CAM_mat_scene_stone", (1600, 900)),
        ("hero", "CAM_qa_01_lagoon_hero", (1920, 1080))]
WANT = str(arg("--cams", "waterline,stone,hero")).split(",")

for short, name, res in JOBS:
    if short not in WANT:
        continue
    ob = bpy.data.objects.get(name)
    if ob is None:
        print(f"[mat_scene] camera {name} missing, skipped")
        continue
    scene.camera = ob
    scene.render.resolution_x, scene.render.resolution_y = res
    fp = OUT / f"{TAG}_scene_{short}.png"
    scene.render.filepath = str(fp)
    t = time.time()
    bpy.ops.render.render(write_still=True)
    print(f"[mat_scene] {short} {res[0]}x{res[1]} {SAMPLES} spp in {time.time() - t:.1f}s -> {fp.name}")

print(f"[mat_scene] done in {time.time() - t0:.1f}s")
