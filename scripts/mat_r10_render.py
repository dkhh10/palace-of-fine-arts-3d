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
    ("a", {"Panel Tone": 0.22, "Ridge Dark": 0.30, "Streaks": 0.75}),
    ("b", {"Panel Tone": 0.34, "Ridge Dark": 0.42, "Streaks": 0.85}),
    ("c", {"Panel Tone": 0.14, "Ridge Dark": 0.20, "Streaks": 0.60}),
    ("d", {"Panel Tone": 0.45, "Ridge Dark": 0.52, "Streaks": 0.95}),
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


def set_border(scene, win, rx, ry):
    scene.render.use_border = True
    scene.render.use_crop_to_border = False
    scene.render.border_min_x, scene.render.border_max_x = win[0] / rx, win[2] / rx
    scene.render.border_min_y, scene.render.border_max_y = 1.0 - win[3] / ry, 1.0 - win[1] / ry


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
else:
    SETS = {
        "cam04": [("CAM_qa_04_rotunda_ceiling", 1280, 720, SPP, None)],
        "hero":  [("CAM_qa_01_lagoon_hero", 1920, 1080, SPP, None)],
        "dome":  [("CAM_qa_01_lagoon_hero", 1920, 1080, SPP, DOME_WINDOW)],
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
