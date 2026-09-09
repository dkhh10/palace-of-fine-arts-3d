"""Round-8 acceptance renders for QA-06-3 (water) and QA-06-8 (the coffered saucer).

    blender -b --python scripts/mat_r8_render.py -- --engine cycles      # hero 1920x1080/64, cam05 + cam06 720p/32
    blender -b --python scripts/mat_r8_render.py -- --engine eevee       # cam06 + cam04 720p

Three Cycles frames and one Eevee pass is the whole render budget of the round, so everything is rendered from one
open master in one session per engine.  Measure with `python3 scripts/mat_r8_measure.py`.
"""
import bpy, sys, os, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
import light_presets

args = common.script_args()
ENGINE = (args[args.index("--engine") + 1] if "--engine" in args else "cycles").lower()
OUT = common.RENDERS / "previews" / "materials"
OUT.mkdir(parents=True, exist_ok=True)

JOBS = {
    "cycles": [("CAM_qa_01_lagoon_hero", 1920, 1080, 64),
               ("CAM_qa_05_south_lawn", 1280, 720, 32),
               ("CAM_qa_06_aerial", 1280, 720, 32)],
    # the re-measure after the murk ramp moved from 14-24 m to 30-90 m: cam06's lagoon is past 90 m either way,
    # so its frame stands; only the hero and cam05 change.
    "cycles2": [("CAM_qa_01_lagoon_hero", 1920, 1080, 64),
                ("CAM_qa_05_south_lawn", 1280, 720, 32)],
    "cycles3": [("CAM_qa_01_lagoon_hero", 1920, 1080, 64)],
    "cam04":  [("CAM_qa_04_rotunda_ceiling", 1280, 720, 32, "eevee")],
    # everything left on the SHIPPED water, in one session: the two Cycles lagoon frames QA-06-3 scores at
    # distance, then the Eevee pass (cam06 for QA-02-6's "not black from above", cam04 for QA-06-8's coffers).
    "final": [("CAM_qa_05_south_lawn", 1280, 720, 32, "cycles"),
              ("CAM_qa_06_aerial", 1280, 720, 32, "cycles"),
              ("CAM_qa_06_aerial", 1280, 720, 32, "eevee"),
              ("CAM_qa_04_rotunda_ceiling", 1280, 720, 32, "eevee")],
    "eevee":  [("CAM_qa_06_aerial", 1280, 720, 32),
               ("CAM_qa_04_rotunda_ceiling", 1280, 720, 32)],
}[ENGINE]

t0 = time.time()
bpy.ops.wm.open_mainfile(filepath=str(common.ROOT / "master.blend"), load_ui=False)
scene = bpy.context.scene
bpy.context.view_layer.update()
print(f"[r8render] opened master in {time.time() - t0:.1f}s, {len(bpy.data.objects)} objects, engine {ENGINE}")

for job in JOBS:
    cam, rx, ry, spp = job[:4]
    eng = job[4] if len(job) > 4 else ("eevee" if ENGINE == "eevee" else "cycles")
    if eng == "cycles":
        light_presets.apply_final_cycles(scene, samples=spp)
        for k, v in (("use_guiding", False), ("use_auto_tile", True), ("tile_size", 256)):
            if hasattr(scene.cycles, k):
                setattr(scene.cycles, k, v)
    else:
        light_presets.apply_preview_eevee(scene, samples=spp)
    common.setup_scene(scene)
    scene.render.image_settings.color_depth = "8"
    scene.render.use_border = False
    scene.camera = bpy.data.objects[cam]
    scene.render.resolution_x, scene.render.resolution_y = rx, ry
    fp = OUT / f"r8_{eng}_{cam.replace('CAM_qa_', '')}.png"
    scene.render.filepath = str(fp)
    t = time.time()
    bpy.ops.render.render(write_still=True)
    print(f"[r8render] {eng} {cam} {rx}x{ry} {spp}spp {time.time() - t:.1f}s -> {fp.name}")

print(f"[r8render] done in {time.time() - t0:.1f}s")
