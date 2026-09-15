"""Round-10 renders: the dome-cap sweep (QA-10-8) and the acceptance pass.

    blender -b --python scripts/mat_r10_render.py -- --jobs sweep      # 4 dome variants, one small border each
    blender -b --python scripts/mat_r10_render.py -- --jobs cam04      # one 1280x720 Cycles cam04
    blender -b --python scripts/mat_r10_render.py -- --jobs hero       # one 1920x1080 Cycles hero

`sweep` opens master ONCE and renders the dome-cap window (cols 890-1030, rows 80-135 of 1920x1080 = 0.37 % of a
frame) for each variant, so four data points cost about one twentieth of a hero frame.  The variants are applied
by overriding the group-node inputs on a LOCAL copy of `MAT_dome_membrane` -- master links the materials, so the
material is copied (which localises the node tree that carries the group node's input values; the `PFA_dome`
group itself is untouched and stays exactly as `scripts/mat_build.py` built it).
"""
import bpy, sys, os, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
import light_presets

args = common.script_args()
JOBS = (args[args.index("--jobs") + 1] if "--jobs" in args else "sweep").lower()
SPP = int(args[args.index("--spp") + 1]) if "--spp" in args else 64
TAG = args[args.index("--tag") + 1] if "--tag" in args else ""
OUT = common.RENDERS / "previews" / "materials"
OUT.mkdir(parents=True, exist_ok=True)

DOME_WINDOW = (890, 80, 1030, 135)          # x0, y0, x1, y1 in the 1920x1080 hero frame

# the sweep: structure strength, bracketing the column-sd the QA box asks for (>= 8, ref 169's own box 6.61)
VARIANTS = [
    # sweep 8: the bump.  Every albedo route to more structure costs mean level, and the box has ~2 lum of slack
    # over its 205 floor.  A lap seam is a real raised ridge, so letting it SHADE itself buys variance at
    # roughly no mean cost: the lit side gains what the shaded side loses.
    ("a", {"Panel Tone": 0.35, "Ridge Dark": 0.45, "Streaks": 0.35, "Seed": 5.0, "Bump": 0.35}),
    ("b", {"Panel Tone": 0.35, "Ridge Dark": 0.45, "Streaks": 0.35, "Seed": 5.0, "Bump": 1.20}),
    ("c", {"Panel Tone": 0.35, "Ridge Dark": 0.45, "Streaks": 0.35, "Seed": 5.0, "Bump": 2.40}),
    ("d", {"Panel Tone": 0.35, "Ridge Dark": 0.35, "Ridge Width": 0.42, "Streaks": 0.35, "Seed": 5.0, "Bump": 2.40}),
]


def dome_group_node():
    """The PFA_dome group node inside MAT_dome_membrane, on a local copy of the material."""
    objs = [o for o in bpy.data.objects
            for s in o.material_slots if s.material and s.material.name.split(".")[0] == "MAT_dome_membrane"]
    if not objs:
        raise SystemExit("[r10render] no object carries MAT_dome_membrane")
    mat = next(s.material for s in objs[0].material_slots
               if s.material and s.material.name.split(".")[0] == "MAT_dome_membrane")
    if mat.library is not None:
        local = mat.copy()                   # copying a linked material gives a local material + local node tree
        for o in objs:
            for s in o.material_slots:
                if s.material is mat:
                    s.material = local
        mat = local
    node = next(n for n in mat.node_tree.nodes
                if n.bl_idname == "ShaderNodeGroup" and n.node_tree and n.node_tree.name.split(".")[0] == "PFA_dome")
    print(f"[r10render] dome material {mat.name} (library={mat.library}) on {len(objs)} object(s)")
    return node


def set_border(scene, win, rx, ry, crop=False):
    scene.render.use_border = True
    scene.render.use_crop_to_border = crop
    scene.render.border_min_x, scene.render.border_max_x = win[0] / rx, win[2] / rx
    scene.render.border_min_y, scene.render.border_max_y = 1.0 - win[3] / ry, 1.0 - win[1] / ry


def object_pixel_box(scene, cam, name, rx, ry, margin):
    """Pixel bounding box of an object's world bound_box in the hero frame, padded by `margin` px."""
    from bpy_extras.object_utils import world_to_camera_view
    from mathutils import Vector
    o = bpy.data.objects[name]
    xs, ys = [], []
    for c in o.bound_box:
        co = world_to_camera_view(scene, cam, o.matrix_world @ Vector(c))
        xs.append(co.x * rx)
        ys.append((1.0 - co.y) * ry)
    win = (max(0, int(min(xs)) - margin), max(0, int(min(ys)) - margin),
           min(rx, int(max(xs)) + margin), min(ry, int(max(ys)) + margin))
    print(f"[r10render] {name} projects to pixels x {win[0]}-{win[2]}, y {win[1]}-{win[3]} "
          f"({win[2] - win[0]}x{win[3] - win[1]} px)")
    return win


t0 = time.time()
bpy.ops.wm.open_mainfile(filepath=str(common.ROOT / "master.blend"), load_ui=False)
scene = bpy.context.scene
bpy.context.view_layer.update()
print(f"[r10render] opened master in {time.time() - t0:.1f}s, {len(bpy.data.objects)} objects, jobs {JOBS}")

if JOBS == "sweep":
    node = dome_group_node()
    cam = bpy.data.objects["CAM_qa_01_lagoon_hero"]
    light_presets.apply_final_cycles(scene, samples=SPP)
    for k, v in (("use_guiding", False), ("use_auto_tile", True), ("tile_size", 256)):
        if hasattr(scene.cycles, k):
            setattr(scene.cycles, k, v)
    common.setup_scene(scene)
    scene.render.image_settings.color_depth = "8"
    scene.camera = cam
    scene.render.resolution_x, scene.render.resolution_y = 1920, 1080
    set_border(scene, DOME_WINDOW, 1920, 1080)
    for tag, params in VARIANTS:
        for k, v in params.items():
            node.inputs[k].default_value = v
        fp = OUT / f"r10_dome_{tag}.png"
        scene.render.filepath = str(fp)
        t = time.time()
        bpy.ops.render.render(write_still=True)
        print(f"[r10render] variant {tag} {params} {time.time() - t:.1f}s -> {fp.name}")
elif JOBS == "apex":
    # mat_r10_review.md finding 1: verify the ridge guard on ARCH_rotunda_dome_apex_cap.  One bordered, CROPPED
    # Cycles frame at hero resolution, so the finial is measured at the pixels the hero actually delivers while
    # the output image stays a few hundred pixels.  No new hero.
    # Which camera actually SEES it?  Projecting the bound box is not enough: from the hero station the finial
    # is beyond the dome's own limb (the camera is 50 m below the crown and 100 m out, so the silhouette top is
    # the tangent point on the near flank and the apex is behind it).  Ray-cast the projected centre and take
    # the first camera whose first hit is the cap itself.
    from mathutils import Vector
    scene.render.resolution_x, scene.render.resolution_y = 1920, 1080
    target = bpy.data.objects["ARCH_rotunda_dome_apex_cap"]
    cam = None
    for c in [o for o in bpy.data.objects if o.type == "CAMERA" and o.name.startswith("CAM_qa_")]:
        scene.camera = c
        bpy.context.view_layer.update()
        w = object_pixel_box(scene, c, target.name, 1920, 1080, 0)
        if w[2] <= w[0] or w[3] <= w[1]:
            continue
        dg = bpy.context.evaluated_depsgraph_get()
        o = c.matrix_world.translation
        hit, loc, nrm, idx, obj, mx = scene.ray_cast(
            dg, o, (target.matrix_world.translation - o).normalized(), distance=5000.0)
        print(f"[r10render]   {c.name}: first hit {obj.name if hit else '<none>'}")
        if hit and obj.name == target.name:
            cam = c
            break
    if cam is None:
        raise SystemExit("[r10render] no QA camera has line of sight to ARCH_rotunda_dome_apex_cap")
    light_presets.apply_final_cycles(scene, samples=SPP)
    for k, v in (("use_guiding", False), ("use_auto_tile", True), ("tile_size", 256)):
        if hasattr(scene.cycles, k):
            setattr(scene.cycles, k, v)
    common.setup_scene(scene)
    scene.render.image_settings.color_depth = "8"
    scene.camera = cam
    scene.render.resolution_x, scene.render.resolution_y = 1920, 1080
    win = object_pixel_box(scene, cam, target.name, 1920, 1080, 22)
    print(f"[r10render] APEX_CAM {cam.name}")
    node = dome_group_node()
    set_border(scene, win, 1920, 1080, crop=True)
    # one job, the pair: the guard off (a limit so large that min() always picks `Ridge Width`, which is the
    # shipped-at-e1a4964 behaviour) and the guard on at its default.
    for tag, limit in (("off", 1000.0), ("on", 0.11)):
        node.inputs["Ridge Arc Limit"].default_value = limit
        fp = OUT / f"r10{TAG}_apexcap_{tag}.png"
        scene.render.filepath = str(fp)
        t = time.time()
        bpy.ops.render.render(write_still=True)
        print(f"[r10render] apex cap guard {tag} (limit {limit}) {win} {SPP}spp {time.time() - t:.1f}s -> {fp.name}")
    print(f"[r10render] APEX_WIN {win[0]} {win[1]} {win[2]} {win[3]}")
else:
    SETS = {
        "cam04": [("CAM_qa_04_rotunda_ceiling", 1280, 720, SPP, None)],
        "hero":  [("CAM_qa_01_lagoon_hero", 1920, 1080, SPP, None)],
        "dome":  [("CAM_qa_01_lagoon_hero", 1920, 1080, SPP, DOME_WINDOW)],
        # the acceptance pass: both frames from one open master, so the 160 MB load is paid once
        "both":  [("CAM_qa_01_lagoon_hero", 1920, 1080, SPP, None),
                  ("CAM_qa_04_rotunda_ceiling", 1280, 720, SPP, None)],
    }[JOBS]
    for cam, rx, ry, spp, win in SETS:
        obj = bpy.data.objects[cam]
        light_presets.apply_final_cycles(scene, samples=spp)
        for k, v in (("use_guiding", False), ("use_auto_tile", True), ("tile_size", 256)):
            if hasattr(scene.cycles, k):
                setattr(scene.cycles, k, v)
        common.setup_scene(scene)
        scene.render.image_settings.color_depth = "8"
        scene.camera = obj
        scene.render.resolution_x, scene.render.resolution_y = rx, ry
        if win:
            set_border(scene, win, rx, ry)
        else:
            scene.render.use_border = False
        fp = OUT / f"r10{TAG}_cycles_{cam.replace('CAM_qa_', '')}.png"
        scene.render.filepath = str(fp)
        t = time.time()
        bpy.ops.render.render(write_still=True)
        print(f"[r10render] {cam} {rx}x{ry} {spp}spp border={win} {time.time() - t:.1f}s -> {fp.name}")

print(f"[r10render] done in {time.time() - t0:.1f}s")
