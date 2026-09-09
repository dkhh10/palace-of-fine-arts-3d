"""Render the hero (CAM_qa_01_lagoon_hero) from a built master, for env_measure's band boxes.

QA-03-10 is stated as a *luminance* ratio against ref 169, and luminance in an ENV preview is set by
env_preview's placeholder sun, not by the shipped light rig - so the band can only be measured on a master
that carries LIGHT.  This opens a master .blend read-only, points the scene at the hero camera at
1920x1080 and renders it; nothing is saved back.

    blender -b --python scripts/env_r5_hero.py -- --out renders/previews/environment/r5_master_hero.png
    blender -b --python scripts/env_r5_hero.py -- --blend /path/to/master.blend --samples 96
    blender -b --python scripts/env_r5_hero.py -- --cam CAM_qa_03_colonnade_walk --engine BLENDER_EEVEE --res 1280x720 --lod 1
"""
import bpy, sys, os
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common

ARGV = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def opt(name, default=None):
    return ARGV[ARGV.index(name) + 1] if name in ARGV else default


# BUG, found in the round-7 review follow-up: this defaulted to `<main checkout>/master.blend`, so every round-7
# render read the MAIN master (ENV r6, 5954 objects) while the numbers were reported against the master this
# worktree had just built (6484 objects).  The default is now THIS checkout's master; pass --blend for any other.
blend = Path(opt("--blend", str(common.ROOT / "master.blend")))
out = Path(opt("--out", str(common.ROOT / "renders/previews/environment/r5_master_hero.png")))
samples = int(opt("--samples", "96"))
engine = opt("--engine", "CYCLES").upper()
cam_name = opt("--cam", "CAM_qa_01_lagoon_hero")
res = opt("--res")
RES = tuple(int(v) for v in res.split("x")) if res else (1920, 1080)

print(f"[env_r5_hero] opening {blend}")
bpy.ops.wm.open_mainfile(filepath=str(blend))
scene = bpy.context.scene
cam = bpy.data.objects.get(cam_name)
if cam is None:
    cands = [o.name for o in bpy.data.objects if o.type == "CAMERA"]
    sys.exit(f"[env_r5_hero] no camera {cam_name}; have {cands}")
scene.camera = cam
lod = opt("--lod")
if lod is not None:                       # match QA's Eevee pass, which renders LOD1 for both viewport and render
    common.set_lod(viewport=int(lod), render=int(lod))
scene.render.resolution_x, scene.render.resolution_y = RES
scene.render.resolution_percentage = 100
scene.render.engine = engine
if engine == "CYCLES":
    scene.cycles.samples = samples
    scene.cycles.use_adaptive_sampling = True
    scene.cycles.use_denoising = True
    scene.cycles.denoiser = "OPENIMAGEDENOISE"
    scene.cycles.device = "GPU"
    prefs = bpy.context.preferences.addons["cycles"].preferences
    try:
        prefs.compute_device_type = "METAL"
        prefs.get_devices()
        for d in prefs.devices:
            d.use = True
    except Exception as e:                                    # noqa: BLE001 - CPU fallback is fine
        print(f"[env_r5_hero] GPU setup skipped: {e}")
if "--nocomp" in ARGV:      # diagnostic: strip lighting's COMP_golden_hour mist to isolate the geometry's own contrast
    scene.render.use_compositing = False
    print("[env_r5_hero] compositing OFF (COMP_golden_hour mist bypassed)")
scene.render.image_settings.file_format = "PNG"
scene.render.filepath = str(out)
out.parent.mkdir(parents=True, exist_ok=True)
print(f"[env_r5_hero] {engine} {samples} spp {RES[0]}x{RES[1]} -> {out}")
bpy.ops.render.render(write_still=True)
print("[env_r5_hero] done")
