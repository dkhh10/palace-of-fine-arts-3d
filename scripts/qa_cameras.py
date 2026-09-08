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
    dict(name="CAM_qa_01_lagoon_hero", loc=(-14.1, 100.0, 1.6), target=(0.0, 0.0, 1.6), lens=20.0, shift_y=0.06,
         ref="canonical/cam_01_lagoon_hero.png",
         note="THE hero. On the lagoon-face normal (az 82 deg), east shore ~115 m, eye level; real-photo twin ref 169 (golden hour)."),
    dict(name="CAM_qa_02_lagoon_ne_threequarter", loc=(70.5, 25.6, 1.1), target=(0.0, 0.0, 21.1), lens=24.0,
         ref="canonical/cam_02_ne_shore_threequarter.jpg",
         note="Ref 062 twin, re-stationed by QA round 04 (scripts/qa_cam02_probe.py sweep, 30-90 m, 16-24 mm): SSE shore path "
              "ON LAND at az 160 / 75 m, eye 1.5 m, 12 deg off the SE face normal (photo 13 deg), 24 mm (photo ~26 mm). "
              "Letterboxed ref 062 targets: visible top 0.02 / apex 0.07 (dome peeks over the attic as in the photo) / podium "
              "base 0.86 (ref 0.85) / attic width 0.41 (ref 0.55); tree occlusion 7 %. Deviations: 75 m (brief said 30-70) "
              "and a strip of south-embayment water at the bottom - from every on-land station within 47 m (NE peninsula) "
              "the build's podium base falls >= 17 % below the frame at 16 mm because the near attic hides the dome inside "
              "~77 m and the apex-to-base span needs a 13 mm lens."),
    dict(name="CAM_qa_03_colonnade_walk", loc=(81.0, 12.04, 1.7), target=(0.0, 0.0, 9.2), lens=18.0,
         ref="canonical/cam_03_colonnade_walk.jpg",
         note="Ref 128: inside the south colonnade looking north-west at the rotunda between two fluted columns."),
    dict(name="CAM_qa_04_rotunda_ceiling", loc=(0.0, 3.0, 1.6), target=(0.0, 3.0, 40.0), lens=15.0,
         ref="canonical/cam_04_rotunda_ceiling.jpg",
         note="Ref 083: straight up; eight inner arches, eight winged figures, star coffering."),
    dict(name="CAM_qa_05_south_lawn", loc=(28.1, 111.8, 1.5), target=(0.0, 0.0, 21.5), lens=35.0,
         ref="canonical/cam_05_south_lawn.jpg",
         note="Ref 063: south-east, ground level across the water's edge; podium, urns, stair, pier groups."),
    dict(name="CAM_qa_06_aerial", loc=(-205.0, 143.0, 120.0), target=(0.0, 0.0, 15.0), lens=50.0,
         ref="canonical/cam_06_aerial.jpg",
         note="Ref 105 bearing (NNE over the lagoon) at a third of its distance: silhouette, dome, both wings, lagoon outline, islet."),
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
        cam_data.shift_y = spec.get("shift_y", 0.0)
        obj = bpy.data.objects.new(spec["name"], cam_data)
        obj.location = spec["loc"]
        if abs(spec["target"][0] - spec["loc"][0]) < 1e-6 and abs(spec["target"][1] - spec["loc"][1]) < 1e-6:
            obj.rotation_euler = (math.pi, 0.0, 0.0)   # straight up (camera looks along local -Z); frame top toward -Y (west)
        else:
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
