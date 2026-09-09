"""Seam test: what does the projection do to cam02 and cam05?  (Eevee, two frames)

    blender -b --python scripts/mat_r9_seam.py -- [--cams 02,05]

Constraint 2 of docs/briefs/materials_r8_projection.md: "no visible seam at the mask edges from cam02 / cam05
(state the seam test)".  A seam is a STEP in the shipped image where the projection weight steps, so the test
renders each camera twice from one open master -- once with `Photo` forced to 0 on every band material and once at
the shipped 0.6 -- and reports, on the difference image: the peak change, the fraction of pixels changed by more
than 1 lum, and the largest single-pixel step of that difference (the seam metric; a hard mask edge shows up here
and nowhere else).  Rendering the SAME frame twice removes sampling noise from the comparison except for Eevee's
TAA, which is deterministic at a fixed sample count.
"""
import bpy, sys, os, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
import light_presets

args = common.script_args()
CAMS = (args[args.index("--cams") + 1] if "--cams" in args else "02,05").split(",")
NAMES = {"01": "CAM_qa_01_lagoon_hero", "02": "CAM_qa_02_lagoon_ne_threequarter",
         "05": "CAM_qa_05_south_lawn", "06": "CAM_qa_06_aerial"}
BAND = ("MAT_concrete_ochre", "MAT_ornament_concrete", "MAT_drum_band")
OUT = common.RENDERS / "previews" / "materials"

bpy.ops.wm.open_mainfile(filepath=str(common.ROOT / "master.blend"), load_ui=False)
scene = bpy.context.scene
targets = [m for m in bpy.data.materials if any(m.name.startswith(b) for b in BAND)]
nodes = [n for m in targets for n in m.node_tree.nodes
         if n.type == "GROUP" and n.node_tree and n.node_tree.name.startswith("PFA_concrete") and "Photo" in n.inputs]
shipped = nodes[0].inputs["Photo"].default_value if nodes else 0.0
print(f"[seam] {len(targets)} band materials, {len(nodes)} concrete group nodes, shipped Photo = {shipped}")

light_presets.apply_preview_eevee(scene, samples=32)
common.setup_scene(scene)
scene.render.image_settings.color_depth = "8"
scene.render.use_border = False
scene.render.resolution_x, scene.render.resolution_y = 1280, 720
for c in CAMS:
    scene.camera = bpy.data.objects[NAMES[c]]
    for tag, v in (("off", 0.0), ("on", shipped)):
        for n in nodes:
            n.inputs["Photo"].default_value = v
        scene.render.filepath = str(OUT / f"r9_seam_{c}_{tag}.png")
        t = time.time()
        bpy.ops.render.render(write_still=True)
        print(f"[seam] cam{c} Photo={v} {time.time() - t:.1f}s")
