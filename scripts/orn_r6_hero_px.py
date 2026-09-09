"""ORN round 6: how tall does a rotunda capital stand in the hero frame, in pixels? (no render)

    scripts/blender_run.sh 300 -- --background --python scripts/orn_r6_hero_px.py

QA-06-6 measures the capital at 24 px on cam01 against 37 px in the photograph (three capitals cropped out of
ref 169 measure 38-44 px). That number is a projection, not a look, so it can be computed exactly from the socket
positions in assets/architecture.blend and the CAM_qa_01 spec in scripts/qa_cameras.py -- no GPU, no shading.

For every SOCKET_capital_rotunda_* it prints the distance to the camera and the height in pixels of a vertical
segment of the OLD course (2.6 m) and the NEW one (3.0 m) at that distance, for the capitals that are actually in
frame (the eight on the lagoon side).
"""
import bpy, sys, os, math, re
from pathlib import Path
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
import qa_cameras

# r6 review finding 7: this used to hard-code RES_X = 1920 and SENSOR = 36.0. Both are read now - the sensor off
# the camera qa_cameras actually builds, the resolution off qa_render_round.py's own `--res` default - so a change
# in either file shows up here instead of silently invalidating the pixel numbers below.
SPEC = next(s for s in qa_cameras.CAMERAS if s["name"] == "CAM_qa_01_lagoon_hero")
qa_cameras.ensure(bpy.context.scene)
CAM = bpy.data.objects[SPEC["name"]]
SENSOR = CAM.data.sensor_width
LENS = CAM.data.lens


def qa_default_res_x():
    """The width QA renders at: the default of `--res` in scripts/qa_render_round.py, read from its source."""
    src = (Path(__file__).resolve().parent / "qa_render_round.py").read_text()
    m = re.search(r'arg\("--res",\s*\[\s*"(\d+)"\s*,\s*"(\d+)"\s*\]', src)
    if not m:
        raise SystemExit("[orn] FAIL cannot read the --res default out of qa_render_round.py")
    return int(m.group(1)), int(m.group(2))


RES_X, RES_Y = qa_default_res_x()
if "--res-x" in common.script_args():
    RES_X = int(common.script_args()[common.script_args().index("--res-x") + 1])
eye = Vector(SPEC["loc"])
fwd = (Vector(SPEC["target"]) - eye).normalized()
px_per_rad_x = RES_X * LENS / SENSOR      # px = size / axial depth * lens / sensor * RES_X (exact, not small-angle)

bpy.ops.wm.open_mainfile(filepath=str(common.ASSET_FILES["ARCH"]), load_ui=False)
rows = []
for o in bpy.data.objects:
    if o.get("orn_type") == "capital_rotunda":
        p = o.matrix_world.translation.copy()
        p.z += 1.5                       # mid-height of the course
        d = (p - eye).length
        depth = (p - eye).dot(fwd)       # distance along the view axis: what the perspective divide uses
        rows.append((o.name, d, depth, o.get("capital_height")))
rows.sort(key=lambda r: r[2])
print(f"cam {SPEC['name']}: eye {tuple(SPEC['loc'])}, lens {LENS} mm on a {SENSOR} mm sensor, "
      f"{RES_X} x {RES_Y} px (from qa_cameras.ensure + qa_render_round's --res default)")
print(f"{'socket':28s} {'range':>8s} {'depth':>8s} {'2.6 m':>8s} {'3.0 m':>8s} {'stamped':>8s}")
for name, d, depth, caph in rows:
    if depth <= 0:
        continue
    print(f"{name:28s} {d:8.1f} {depth:8.1f} {2.6 / depth * px_per_rad_x:8.1f} "
          f"{3.0 / depth * px_per_rad_x:8.1f} {(caph or 0.0):8.2f}")
front = [r for r in rows if r[2] > 0][:8]
if front:
    ds = [r[2] for r in front]
    print(f"\nthe eight capitals nearest the hero camera: depth {min(ds):.1f}-{max(ds):.1f} m -> "
          f"a 2.6 m course is {2.6 / max(ds) * px_per_rad_x:.1f}-{2.6 / min(ds) * px_per_rad_x:.1f} px, "
          f"a 3.0 m course {3.0 / max(ds) * px_per_rad_x:.1f}-{3.0 / min(ds) * px_per_rad_x:.1f} px "
          f"(ref 169: 38-44 px, QA-06-6 target 37)")
