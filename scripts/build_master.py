"""Assemble master.blend from the specialist asset files by LINKING their collections.
    blender -b --python scripts/build_master.py [-- --append] [-- --preview] [-- --no-env]
Idempotent: starts from an empty file every time. Only the lead runs/edits this.
"""
import bpy, sys, os
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
import qa_cameras

args = common.script_args()
LINK = "--append" not in args
ROOT = common.ROOT

# fresh file
bpy.ops.wm.read_homefile(use_empty=True)
common.wipe_scene()
scene = common.setup_scene()
scene.name = "PalaceOfFineArts"

linked = {}
plan = [
    ("ARCH", common.ASSET_FILES["ARCH"], "ARCH"),
    ("ORN", common.ASSET_FILES["ORN"], "ORN"),
    ("ENV", common.ASSET_FILES["ENV"], "ENV"),
    ("LIGHT", common.ASSET_FILES["LIGHT"], "LIGHT"),
]
if "--no-env" in args:
    plan = [p for p in plan if p[0] != "ENV"]
for key, path, coll_name in plan:
    if not path.exists():
        # Phase 0/1 fallback: lead's placeholder blockout stands in for ARCH
        if key == "ARCH" and (common.ASSETS / "placeholder_blockout.blend").exists():
            coll = common.link_collection(common.ASSETS / "placeholder_blockout.blend", "PLACEHOLDER", link=LINK)
            linked[key] = coll
        continue
    coll = common.link_collection(path, coll_name, link=LINK)
    linked[key] = coll

# world from lighting.blend (if present), else a neutral sky
light_file = common.ASSET_FILES["LIGHT"]
world = None
if light_file.exists():
    with bpy.data.libraries.load(str(light_file), link=LINK) as (src, dst):
        if "WORLD_golden_hour" in src.worlds:
            dst.worlds = ["WORLD_golden_hour"]
    world = bpy.data.worlds.get("WORLD_golden_hour")
if world is None:
    world = bpy.data.worlds.new("WORLD_placeholder")
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs[0].default_value = (0.55, 0.65, 0.85, 1.0)
        bg.inputs[1].default_value = 1.0
scene.world = world

# placeholder sun if lighting not delivered yet
if "LIGHT" not in linked:
    coll = common.rebuild_collection("LIGHT_placeholder")
    sun = bpy.data.lights.new("LIGHT_sun_placeholder", "SUN")
    sun.energy = 4.0
    sun.angle = 0.0093
    sun.color = (1.0, 0.75, 0.5)
    so = bpy.data.objects.new("LIGHT_sun_placeholder", sun)
    coll.objects.link(so)
    common.aim_sun(so, azimuth_deg=118.0, elevation_deg=7.0)

# cameras + render settings + the lighting agent's look (exposure, AgX look, compositor)
qa_cameras.ensure(scene)
common.configure_eevee(scene, samples=32)
if "LIGHT" in linked:
    try:
        import light_presets
        light_presets.apply_look(scene)
    except Exception as e:
        print("[build_master] light_presets.apply_look failed:", e)
scene.render.resolution_x, scene.render.resolution_y = 1920, 1080
common.set_lod_visibility(1)

common.save_blend(ROOT / "master.blend")
print("[build_master] linked:", {k: (v.name if v else None) for k, v in linked.items()})

if "--preview" in args:
    common.render_previews("lead")
