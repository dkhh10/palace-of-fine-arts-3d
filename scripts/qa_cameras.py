"""Fixed QA camera set. Six canonical viewpoints matched to reference photos (docs/reference_sheet.md).
Run standalone to add them to a file:  blender -b file.blend --python scripts/qa_cameras.py -- --save
Or from code:  import qa_cameras; qa_cameras.ensure(scene)

World: origin = rotunda floor centre, +Y toward the lagoon (east), -X north, +X south, z=0 rotunda floor.
Only the lead edits this file. Positions are refined against the reference photos in Phase 1.
"""
import bpy, sys, os, math
from pathlib import Path
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common

COLLECTION = "QA_CAMERAS"

# name, location (x, y, z), look-at target, focal length mm (36 mm sensor), reference photo, note
CAMERAS = [
    dict(name="CAM_qa_01_lagoon_hero", loc=(6.0, 118.0, 0.6), target=(0.0, 0.0, 20.0), lens=32.0,
         ref="user/user_wide_midday.png", note="THE hero. East shore, ~118 m, eye level, rotunda centred, colonnade wings at frame edges."),
    dict(name="CAM_qa_02_lagoon_ne_threequarter", loc=(-70.0, 95.0, 1.2), target=(0.0, 0.0, 22.0), lens=40.0,
         ref="raw/(reference agent to assign)", note="North-east shore, 3/4 view showing the south colonnade sweep behind the rotunda."),
    dict(name="CAM_qa_03_colonnade_walk", loc=(58.0, -2.0, 1.7), target=(20.0, 4.0, 14.0), lens=24.0,
         ref="raw/(reference agent to assign)", note="Inside the south colonnade looking north along the columns toward the rotunda; maidens on boxes overhead."),
    dict(name="CAM_qa_04_rotunda_ceiling", loc=(2.0, 6.0, 1.7), target=(0.0, 0.0, 40.0), lens=20.0,
         ref="raw/(reference agent to assign)", note="Under the rotunda looking up: inner arches, coffered ceiling."),
    dict(name="CAM_qa_05_south_lawn", loc=(75.0, 40.0, 1.6), target=(10.0, 0.0, 22.0), lens=35.0,
         ref="raw/(reference agent to assign)", note="From the south lawn across the lagoon tip: rotunda with pier groups and rostra at ground level."),
    dict(name="CAM_qa_06_aerial", loc=(120.0, 150.0, 70.0), target=(0.0, -10.0, 15.0), lens=35.0,
         ref="raw/(reference agent to assign)", note="Drone-height 3/4 from the south-east: silhouette, dome, both colonnade arcs, lagoon outline."),
]


def ensure(scene=None):
    scene = scene or bpy.context.scene
    coll = common.rebuild_collection(COLLECTION)
    cams = []
    for spec in CAMERAS:
        cam_data = bpy.data.cameras.new(spec["name"])
        cam_data.lens = spec["lens"]
        cam_data.sensor_width = 36.0
        cam_data.sensor_fit = "HORIZONTAL"
        cam_data.clip_start = 0.1
        cam_data.clip_end = 5000.0
        cam_data.dof.use_dof = False
        obj = bpy.data.objects.new(spec["name"], cam_data)
        obj.location = spec["loc"]
        obj.rotation_euler = common.lookat_rotation(spec["loc"], spec["target"])
        obj["reference_photo"] = spec["ref"]
        obj["note"] = spec["note"]
        coll.objects.link(obj)
        cams.append(obj)
    if scene.camera is None or scene.camera.name not in [c.name for c in cams]:
        scene.camera = cams[0]
    return cams


if __name__ == "__main__":
    cams = ensure()
    print(f"[qa_cameras] created {len(cams)} cameras")
    if "--save" in common.script_args() and bpy.data.filepath:
        bpy.ops.wm.save_mainfile()
