"""Round-9 renders: the hero acceptance frame and the projector frame the ratio map is built from.

    blender -b --python scripts/mat_r9_render.py -- --jobs before
    blender -b --python scripts/mat_r9_render.py -- --jobs after
    blender -b --python scripts/mat_r9_render.py -- --jobs eevee
    blender -b --python scripts/mat_r9_render.py -- --jobs cam04

`before` renders TWO frames from one open master:

  hero      CAM_qa_01_lagoon_hero as the round-08 stations define it (loc z 1.3 = 2.6 m over the water), full
            1920x1080 Cycles -- the BEFORE column of the acceptance table, measured on QA's boxes.
  projector a camera reconstructed at the station `scripts/arch_uvproj.py` baked `UVProj` from, i.e. cam01 as it
            stood BEFORE the round-08 move: loc (-14.1, 100.0, 1.6), target (0, 0, 1.6), 20 mm, shift_y 0.06
            (renders/logs/arch_r7_build.log:49).  `UVProj` is a per-vertex bake of that camera's frame
            coordinates and architecture.blend has not been rebuilt since the station moved, so a ratio map built
            in the CURRENT hero frame would land 3-4 px low on the wall.  Building it in the projector's own frame
            costs nothing (ref 169's alignment `arch_params.REF169_XF` was fitted against that same station) and
            makes the projection exact instead of approximately registered.
            Rendered as a BORDER (rows 40-400 of 1080) because the band mask only ever reads the drum, the attic
            and the entablature: ~1/3 of a frame, not a whole one, against the round's Cycles budget.
"""
import bpy, sys, os, time, math

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
import light_presets

args = common.script_args()
JOBS = (args[args.index("--jobs") + 1] if "--jobs" in args else "before").lower()
SPP = int(args[args.index("--spp") + 1]) if "--spp" in args else 64
TAG = args[args.index("--tag") + 1] if "--tag" in args else ""
OUT = common.RENDERS / "previews" / "materials"
OUT.mkdir(parents=True, exist_ok=True)

# the station arch_uvproj.py baked UVProj from (qa_cameras.py before commit 65ef92c)
PROJ = dict(loc=(-14.1, 100.0, 1.6), target=(0.0, 0.0, 1.6), lens=20.0, shift_y=0.06)
PROJ_BORDER = (40, 400)          # rows of 1080 the ratio map is built from


def projector_camera():
    """Rebuild the UVProj bake camera as PROJ_CAM_r9 (never saved into anyone's asset)."""
    name = "PROJ_CAM_r9"
    old = bpy.data.objects.get(name)
    if old:
        bpy.data.objects.remove(old, do_unlink=True)
    cd = bpy.data.cameras.new(name)
    cd.lens, cd.sensor_width, cd.sensor_fit = PROJ["lens"], 36.0, "HORIZONTAL"
    cd.clip_start, cd.clip_end, cd.shift_y = 0.1, 5000.0, PROJ["shift_y"]
    cd.dof.use_dof = False
    o = bpy.data.objects.new(name, cd)
    o.location = PROJ["loc"]
    o.rotation_euler = common.lookat_rotation(PROJ["loc"], PROJ["target"])
    bpy.context.scene.collection.objects.link(o)
    bpy.context.view_layer.update()
    return o


t0 = time.time()
bpy.ops.wm.open_mainfile(filepath=str(common.ROOT / "master.blend"), load_ui=False)
scene = bpy.context.scene
bpy.context.view_layer.update()
print(f"[r9render] opened master in {time.time() - t0:.1f}s, {len(bpy.data.objects)} objects, jobs {JOBS}")

# (camera, rx, ry, spp, engine, border rows or None)
SETS = {
    "before": [("CAM_qa_01_lagoon_hero", 1920, 1080, SPP, "cycles", None),
               ("PROJ_CAM_r9", 1920, 1080, SPP, "cycles", PROJ_BORDER)],
    # the acceptance pass: one full hero frame, one cam04 for the coffers (r8 review carry 7), and cam05's water
    # band as a BORDER (rows 600-720 of 720 = the band mat_r8_measure scores) so the hold item "cam05 band lum
    # 70-117, sat >= 0.24" is verified in Cycles for 1/6 of a frame instead of being estimated from the hero flank.
    "after":  [("CAM_qa_01_lagoon_hero", 1920, 1080, SPP, "cycles", None),
               ("CAM_qa_04_rotunda_ceiling", 1280, 720, 32, "cycles", None),
               ("CAM_qa_05_south_lawn", 1280, 720, 32, "cycles", (600, 720))],
    # the shipped state: the last Cycles hero frame plus the Eevee five-camera pass in ONE open master.
    "final":  [("CAM_qa_01_lagoon_hero", 1920, 1080, SPP, "cycles", None),
               ("CAM_qa_01_lagoon_hero", 1920, 1080, 32, "eevee", None),
               ("CAM_qa_02_lagoon_ne_threequarter", 1280, 720, 32, "eevee", None),
               ("CAM_qa_04_rotunda_ceiling", 1280, 720, 32, "eevee", None),
               ("CAM_qa_05_south_lawn", 1280, 720, 32, "eevee", None),
               ("CAM_qa_06_aerial", 1280, 720, 32, "eevee", None)],
    "proj":   [("PROJ_CAM_r9", 1920, 1080, SPP, "cycles", PROJ_BORDER)],
    "cam04":  [("CAM_qa_04_rotunda_ceiling", 1280, 720, 32, "cycles", None)],
    "eevee":  [("CAM_qa_01_lagoon_hero", 1920, 1080, 32, "eevee", None),
               ("CAM_qa_02_lagoon_ne_threequarter", 1280, 720, 32, "eevee", None),
               ("CAM_qa_04_rotunda_ceiling", 1280, 720, 32, "eevee", None),
               ("CAM_qa_05_south_lawn", 1280, 720, 32, "eevee", None),
               ("CAM_qa_06_aerial", 1280, 720, 32, "eevee", None)],
}[JOBS]

for cam, rx, ry, spp, eng, border in SETS:
    obj = bpy.data.objects.get(cam) or (projector_camera() if cam == "PROJ_CAM_r9" else None)
    if obj is None:
        raise SystemExit(f"[r9render] camera {cam} not in master.blend")
    if eng == "cycles":
        light_presets.apply_final_cycles(scene, samples=spp)
        for k, v in (("use_guiding", False), ("use_auto_tile", True), ("tile_size", 256)):
            if hasattr(scene.cycles, k):
                setattr(scene.cycles, k, v)
    else:
        light_presets.apply_preview_eevee(scene, samples=spp)
    common.setup_scene(scene)
    scene.render.image_settings.color_depth = "8"
    scene.camera = obj
    scene.render.resolution_x, scene.render.resolution_y = rx, ry
    if border:
        # Blender's border is in 0..1 from the BOTTOM; rows count from the top.
        scene.render.use_border = True
        scene.render.use_crop_to_border = False
        scene.render.border_min_x, scene.render.border_max_x = 0.0, 1.0
        scene.render.border_min_y = 1.0 - border[1] / ry
        scene.render.border_max_y = 1.0 - border[0] / ry
    else:
        scene.render.use_border = False
    fp = OUT / f"r9{TAG}_{eng}_{cam.replace('CAM_qa_', '').replace('PROJ_CAM_r9', 'projector')}.png"
    scene.render.filepath = str(fp)
    t = time.time()
    bpy.ops.render.render(write_still=True)
    print(f"[r9render] {eng} {cam} {rx}x{ry} {spp}spp border={border} {time.time() - t:.1f}s -> {fp.name}")

print(f"[r9render] done in {time.time() - t0:.1f}s")
