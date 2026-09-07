"""Flythrough camera for the Palace of Fine Arts (Lighting & Rendering specialist).

Creates, inside the LIGHT collection of assets/lighting.blend:
  CAM_flythrough_path    bezier curve: east-shore hero position -> glide south along the shore -> across the water to
                         the south colonnade's end pylons -> between the columns along the colonnade axis -> under the
                         rotunda looking up at the dome
  CAM_flythrough_target  empty (keyframed look-at target)
  CAM_flythrough         camera, Follow Path (fixed position, keyframed offset_factor with eased holds) + Track To target
720 frames at 24 fps (30 s). Route waypoints come from the OSM footprints (reference/plans/site_local.json) and the
reference sheet; the timing table is in docs/lighting_notes.md.

    blender -b --python scripts/light_flythrough.py                # rebuild the path in assets/lighting.blend
    blender -b --python scripts/light_flythrough.py -- --test      # + 6 evenly spaced 640x360 Eevee frames of the
                                                                   #   placeholder into renders/previews/lighting/
"""
import bpy, os, sys, math, time, json
from pathlib import Path
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
import light_presets as lp

FPS = 24
FRAMES = 720
OUT = common.RENDERS / "previews" / "lighting"

# (x, y, z) world metres. z is camera height; water at -1.3, colonnade columns 20 m tall, gallery ~6 m wide.
WAYPOINTS = [
    ("hero_start",      (-16.0, 113.9, 1.0)),    # = CAM_qa_01 position on the east shore
    ("shore_south",     (22.0, 116.5, 2.0)),     # glide south-east along the east shore
    ("shore_se",        (58.0, 112.0, 3.0)),
    ("water_cross",     (78.0, 84.0, 5.0)),      # bank across the water toward the colonnade end
    ("colonnade_end",   (79.0, 54.0, 6.0)),      # just east of the end pylons, over the water's edge
    ("colonnade_in",    (75.8, 34.0, 6.0)),      # enter the gallery on its axis
    ("colonnade_mid1",  (74.5, 19.0, 6.0)),
    ("colonnade_mid2",  (68.5, 7.5, 6.0)),
    ("colonnade_mid3",  (61.5, -2.5, 6.0)),
    ("colonnade_mid4",  (50.0, -13.0, 6.0)),
    ("colonnade_out",   (37.0, -22.5, 5.5)),     # leave the gallery at its rotunda end
    ("rotunda_approach",(20.0, -14.0, 4.0)),     # between the south pier columns
    ("rotunda_centre",  (0.0, 1.0, 2.5)),        # under the dome
]
# key frames at which the camera reaches a waypoint (index into WAYPOINTS); eased in between, holds at both ends
KEYS = [(1, 0), (49, 0), (240, 2), (400, 4), (600, 10), (700, 12), (FRAMES, 12)]
# look-at target keyframes: (frame, (x, y, z))
TARGET_KEYS = [
    (1,   (0.0, 0.0, 17.0)),     # rotunda, hero framing
    (240, (0.0, 0.0, 15.0)),     # still on the rotunda while gliding
    (330, (72.0, 40.0, 12.0)),   # swing toward the colonnade end pylons
    (400, (74.0, 22.0, 9.0)),    # look down the gallery
    (600, (12.0, -8.0, 12.0)),   # toward the rotunda from inside the colonnade
    (700, (0.0, 0.0, 30.0)),     # rise toward the dome
    (FRAMES, (0.0, 1.0, 46.0)),  # straight up at the dome apex (dome top at ~47.9 m)
]


def _clear_old(coll):
    for name in ("CAM_flythrough", "CAM_flythrough_target", "CAM_flythrough_path"):
        o = bpy.data.objects.get(name)
        if o:
            data = o.data
            bpy.data.objects.remove(o, do_unlink=True)
            if data and data.users == 0:
                if isinstance(data, bpy.types.Curve):
                    bpy.data.curves.remove(data)
                elif isinstance(data, bpy.types.Camera):
                    bpy.data.cameras.remove(data)
    for a in list(bpy.data.actions):
        if a.name.startswith("CAM_flythrough"):
            bpy.data.actions.remove(a)


def build_path(coll):
    cu = bpy.data.curves.new("CAM_flythrough_path", "CURVE")
    cu.dimensions = "3D"
    cu.resolution_u = 24
    cu.use_path = True
    cu.path_duration = FRAMES
    cu.twist_mode = "Z_UP"
    sp = cu.splines.new("BEZIER")
    sp.bezier_points.add(len(WAYPOINTS) - 1)
    for bp, (_, p) in zip(sp.bezier_points, WAYPOINTS):
        bp.co = p
        bp.handle_left_type = bp.handle_right_type = "AUTO"
    sp.use_endpoint_u = True
    obj = bpy.data.objects.new("CAM_flythrough_path", cu)
    coll.objects.link(obj)
    for i, (name, p) in enumerate(WAYPOINTS):
        obj[f"wp_{i:02d}_{name}"] = list(p)
    return obj


def arc_length_fractions(path_obj):
    """Arc-length fraction of each waypoint along the evaluated bezier (Follow Path offset_factor is arc-length based)."""
    dg = bpy.context.evaluated_depsgraph_get()
    ev = path_obj.evaluated_get(dg)
    me = ev.to_mesh()
    pts = [v.co.copy() for v in me.vertices]
    ev.to_mesh_clear()
    if len(pts) < 2:
        return [i / (len(WAYPOINTS) - 1) for i in range(len(WAYPOINTS))], 0.0
    cum = [0.0]
    for a, b in zip(pts, pts[1:]):
        cum.append(cum[-1] + (b - a).length)
    total = cum[-1]
    fr = []
    for _, p in WAYPOINTS:
        k = min(range(len(pts)), key=lambda i: (pts[i] - Vector(p)).length)
        fr.append(cum[k] / total)
    fr[0], fr[-1] = 0.0, 1.0
    return fr, total


def _all_fcurves(action):
    """F-curves of a legacy (4.x) or layered/slotted (5.x) action."""
    if hasattr(action, "fcurves"):
        return list(action.fcurves)
    out = []
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                out.extend(bag.fcurves)
    return out


def build_camera(coll, path_obj):
    tgt = bpy.data.objects.new("CAM_flythrough_target", None)
    tgt.empty_display_type = "SPHERE"; tgt.empty_display_size = 1.5
    coll.objects.link(tgt)
    for f, p in TARGET_KEYS:
        tgt.location = p
        tgt.keyframe_insert("location", frame=f)
    cam_data = bpy.data.cameras.new("CAM_flythrough")
    cam_data.lens = 24.0
    cam_data.sensor_width = 36.0
    cam_data.sensor_fit = "HORIZONTAL"
    cam_data.clip_start = 0.1
    cam_data.clip_end = 5000.0
    cam_data.dof.use_dof = False
    cam = bpy.data.objects.new("CAM_flythrough", cam_data)
    coll.objects.link(cam)
    fp = cam.constraints.new("FOLLOW_PATH")
    fp.target = path_obj
    fp.use_fixed_location = True
    fp.use_curve_follow = False          # orientation comes from Track To
    fp.forward_axis = "TRACK_NEGATIVE_Z"
    fp.up_axis = "UP_Y"
    fractions, total = arc_length_fractions(path_obj)
    for frame, wp in KEYS:
        fp.offset_factor = fractions[wp]
        fp.keyframe_insert("offset_factor", frame=frame)
    tt = cam.constraints.new("TRACK_TO")
    tt.target = tgt
    tt.track_axis = "TRACK_NEGATIVE_Z"
    tt.up_axis = "UP_Y"
    # gentle easing: smooth handles everywhere, ease in/out at the holds
    for ob in (cam, tgt):
        ad = ob.animation_data
        if ad and ad.action:
            for fc in _all_fcurves(ad.action):
                for kp in fc.keyframe_points:
                    kp.interpolation = "BEZIER"
                    kp.easing = "EASE_IN_OUT"
                    kp.handle_left_type = kp.handle_right_type = "AUTO_CLAMPED"
    cam["fps"] = FPS; cam["frames"] = FRAMES
    cam["path_length_m"] = total
    cam["timing_table"] = json.dumps([dict(frame=f, t_s=round((f - 1) / FPS, 2), waypoint=WAYPOINTS[w][0], arc_fraction=round(fractions[w], 4)) for f, w in KEYS])
    return cam, tgt, fractions, total


def build(scene):
    scene.render.fps = FPS
    scene.frame_start, scene.frame_end = 1, FRAMES
    coll = common.get_collection("LIGHT")
    _clear_old(coll)
    path_obj = build_path(coll)
    cam, tgt, fractions, total = build_camera(coll, path_obj)
    print(f"[light_flythrough] path {total:.1f} m, {FRAMES} frames @ {FPS} fps = {FRAMES / FPS:.0f} s, mean {total / (FRAMES / FPS):.1f} m/s")
    print("[light_flythrough] timing table:")
    for f, w in KEYS:
        print(f"   frame {f:4d}  t={((f - 1) / FPS):5.2f}s  {WAYPOINTS[w][0]:18s} arc {fractions[w]:.3f}  pos {WAYPOINTS[w][1]}")
    return cam, path_obj, tgt


def sample_positions(scene, cam, frames):
    rows = []
    for f in frames:
        scene.frame_set(f)
        m = cam.matrix_world
        pos = tuple(round(v, 1) for v in m.translation)
        fwd = m.to_quaternion() @ Vector((0.0, 0.0, -1.0))
        rows.append((f, pos, tuple(round(v, 2) for v in fwd)))
    return rows


def render_test(scene, cam, n=6):
    """n evenly spaced 640x360 Eevee frames of whatever is in the scene (placeholder in Phase 2)."""
    OUT.mkdir(parents=True, exist_ok=True)
    lp.apply_preview_eevee(scene, samples=16)
    scene.camera = cam
    scene.render.resolution_x, scene.render.resolution_y = 640, 360
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    frames = [1 + round(i * (FRAMES - 1) / (n - 1)) for i in range(n)]
    outs = []
    for f in frames:
        scene.frame_set(f)
        fp = OUT / f"flythrough_test_{f:04d}.png"
        scene.render.filepath = str(fp)
        t = time.time()
        bpy.ops.render.render(write_still=True)
        outs.append(fp)
        print(f"[light_flythrough] frame {f} -> {fp.name} ({time.time() - t:.1f}s) cam at {tuple(round(v, 1) for v in cam.matrix_world.translation)}")
    return outs


if __name__ == "__main__":
    args = common.script_args()
    blend = common.ASSET_FILES["LIGHT"]
    if not blend.exists():
        sys.exit("[light_flythrough] run light_build.py first")
    bpy.ops.wm.open_mainfile(filepath=str(blend))
    scene = bpy.context.scene
    cam, path_obj, tgt = build(scene)
    for f, pos, fwd in sample_positions(scene, cam, [1, 120, 240, 360, 480, 600, 720]):
        print(f"[light_flythrough] f{f:4d} cam {pos} fwd {fwd}")
    scene.frame_set(1)
    common.save_blend(blend)
    if "--test" in args:
        # temp scene: placeholder + this rig
        common.link_collection(common.ASSETS / "placeholder_blockout.blend", "PLACEHOLDER", link=True)
        pc = bpy.data.collections.get("PLACEHOLDER_LIGHT")
        if pc:
            pc.hide_render = True
        lp.apply_look(scene)
        render_test(scene, cam)
