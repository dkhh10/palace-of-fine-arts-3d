"""Phase 5 flythrough camera for the Palace of Fine Arts (Lighting & Rendering specialist).

ROUND 14 REWRITE. The round-02 route predated architecture rounds 4-5, environment rounds 5-8 and the QA
re-stationing of cam01/cam02, and it flew the colonnade at z = 6.0 m -- head height is z = 1.15 on a walk whose
paving `env_build.build_colonnade_paving` puts at -0.6 to -0.75. Every station below is now a MEASURED point on the
current site (`scripts/light_flythrough_check.py --probe`, logs renders/logs/light_r14_probe*.log), and the timing
is no longer a hand-written frame list: `speed_profile()` builds a trapezoidal velocity profile under a per-leg
speed cap with a 2.5 m/s^2 accel limit, and offset_factor is keyed at EVERY frame with LINEAR interpolation, so the
speed the constraint produces is the speed that was designed. Validation (ray-cast, no render) is the check script.

Objects, all inside the LIGHT collection of assets/lighting.blend:
  CAM_flythrough_path    bezier curve through the stations
  CAM_flythrough_target  empty, keyframed look-at target
  CAM_flythrough         camera, Follow Path (fixed location, keyed offset_factor) + Track To the target
  cam["schedule"]        JSON: fps, frames, path length, leg frame ranges + speed caps, hold windows, station table

    scripts/blender_run.sh 600 -- --background --python scripts/light_flythrough.py       # rebuild + save
    scripts/blender_run.sh 900 -- --background --python scripts/light_flythrough_check.py --   # validate
"""
import bpy, os, sys, math, json, time
from pathlib import Path
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
import light_presets as lp
import arch_params as A
import qa_cameras

FPS = 24
ACCEL = 2.5              # m/s^2 tangential; 0 -> 9.2 m/s in 3.7 s / 17 m
HOLD_HERO_S = 3.5        # brief: >= 3 s
HOLD_DOME_S = 3.5
V_WATER = 9.2            # brief cap 10 m/s on the water crossing (8 % headroom for the constraint's own resampling)
V_LAND = 5.6             # brief cap 6 m/s everywhere else
V_GALLERY = 4.6          # a walk, not a drive, between the colonnade columns
LENS = 24.0
OUT = common.RENDERS / "previews" / "lighting"

# ---------------------------------------------------------------------------------------------- the route
# Colonnade geometry, from arch_params + the built file (scripts/light_flythrough_check.py --columns, log
# renders/logs/light_r14_cols.log): the two column rows of each wing sit at r 115.15 and 119.65 about
# COL_ARC_CENTER, so the gallery centreline is r 117.40 and the gallery is COL_ROW_SPACING - COLONNADE_D =
# 4.50 - 1.70 = 2.80 m of clear width.  ITS CENTRELINE THEREFORE CANNOT BE MORE THAN 1.40 m FROM A SHAFT --
# the brief's 1.5 m is unreachable inside the colonnade and the check gates that leg at 1.35 m instead
# (`light_flythrough_check.CLEAR_MIN_GALLERY`).
CX, CY = A.COL_ARC_CENTER
R_WALK = A.COL_ARC_R                                   # 117.40 gallery centreline
R_INNER = R_WALK - A.COL_ROW_SPACING / 2               # 115.15 inner column row
Z_WALK = A.COLONNADE_GROUND_Z + 1.75                   # 1.15 eye height over the walk (paving measured at -0.62..-0.75)
# The entry crosses the inner row RADIALLY through the centre of the 4.5 m bay between the columns at theta
# -44.94 and -42.75, and reaches the centreline exactly at the next column's theta, so the diagonal is 2.25 m
# out per 2.25 m along and the clearance never drops below the gallery's own 1.40 m bound.
GAP_THETA, TURN_THETA = -43.85, -44.94
GAL_THETA_0, GAL_THETA_1, GAL_STEP = -47.14, -67.14, 2.2   # then the open end past the last columns (-66.90)
GAL_EXIT_THETA = -69.30



def qa_xy(cam_name):
    """The (x, y) of a QA camera, read from `qa_cameras.CAMERAS` by name so a re-stationing there cannot
    silently desync the flythrough (prep review 1; §23.1.2 records this desyncing once already).
    z is NOT taken from qa_cameras: the flythrough's eye heights are probed against the surface below."""
    for spec in qa_cameras.CAMERAS:
        if spec["name"] == cam_name:
            return tuple(round(c, 2) for c in spec["loc"][:2])
    raise KeyError(f"{cam_name} is not in qa_cameras.CAMERAS")


def arc_xy(theta_deg, r):
    a = math.radians(theta_deg)
    return (CX + r * math.cos(a), CY + r * math.sin(a))


def _arc(name, theta, r, z, cap, leg, note, tangent=True):
    """A station placed in colonnade-arc polar coordinates. `tangent` marks the ones that lie ON the centreline
    and therefore get arc-tangent bezier handles; the two radial entry stations do not."""
    x, y = arc_xy(theta, r)
    return (name, (round(x, 2), round(y, 2), z), cap, leg, (theta if tangent else None), note)


# (name, (x, y, z), speed cap of the leg ARRIVING here, leg label, arc theta or None, note)
# Every z is eye height over the MEASURED surface below (probe logs renders/logs/light_r14_probe*.log):
#   lagoon water -1.30 | shore terrain -0.48..-0.79 | colonnade walk paving -0.62..-0.75 | ARCH_site_platform 0.00
STATIONS = [
    ("hero",       qa_xy("CAM_qa_01_lagoon_hero") + (1.60,), V_WATER, "hero_hold", None,
                                                "CAM_qa_01 station; water below, agl 2.90"),
    ("lagoon_a",   (  6.00,  99.00, 2.20), V_WATER, "water", None, "over the lagoon and the low east islet (agl 2.4+)"),
    ("lagoon_b",   ( 24.00,  93.00, 2.80), V_WATER, "water", None, "water -1.30"),
    ("lagoon_c",   ( 40.00,  84.00, 3.20), V_WATER, "water", None, "water -1.30, apex of the crossing"),
    ("lagoon_d",   ( 54.00,  68.00, 3.20), V_WATER, "water", None, "water -1.30"),
    ("lagoon_e",   ( 62.00,  56.00, 4.00), V_WATER, "water", None, "water -1.30; climbing for the shore thicket"),
    ("shore_over", ( 68.00,  49.00, 6.20), V_WATER, "water", None, "over the ENV_shrub_big1_1047/1051 shore thicket "
                                                                   "(crowns to ~2.6 m); end of the water crossing"),
    ("landfall",   ( 72.50,  43.50, 3.60), V_LAND,  "shore", None, "colonnade-walk apron -0.71, the first clear ground"),
    ("walk_a",     ( 73.50,  38.00, 1.90), V_LAND,  "shore", None, "apron -0.69"),
    ("walk_b",     ( 73.00,  33.00, 1.25), V_LAND,  "shore", None, "apron -0.71"),
    ("walk_c",     ( 72.00,  29.00, 1.10), V_LAND,  "shore", None, "terrain -0.74"),
    # ROUND 16 (QA-08-13). This station used to be read from qa_cameras by name, on prep review 1's rule that a
    # re-stationing there must not silently desync the route. It desynced the route the other way instead: in
    # round 08 the lead moved CAM_qa_02 from the SSE shore path (70.5, 25.6) to the NNE fit of ref 062 at
    # (-79.8, 24.4), i.e. to the FAR SIDE of the building from every other station on this leg. The bezier then ran
    # the camera across the courtyard and back, the route went 250 m -> ~530 m and the saved frame range 1-1224 ->
    # 1-2616 (109 s at 24 fps) with nothing in any brief asking for it. The lead's round-16 decision is that the
    # flythrough stays ~50 s, so the station is PINNED at the east-shore point the route was designed around and
    # the QA camera is no longer on the route. Kept because it is a good station in its own right (the
    # three-quarter over the courtyard) -- it is simply not CAM_qa_02 any more, and the name says so.
    ("ne_apron",   ( 70.50,  25.60, 1.06), V_LAND,  "shore", None,
                                                "east shore apron, the round-07 CAM_qa_02 station; walk -0.69, agl 1.75"),
    ("apron_a",    ( 70.20,  19.00, 1.15), V_LAND,  "shore", None, "courtyard apron, terrain -0.58"),
    ("apron_b",    ( 68.60,  13.50, 1.12), V_LAND,  "shore", None, "courtyard apron, terrain -0.63"),
    _arc("bay_line",  GAP_THETA,  108.00, 1.08, V_GALLERY, "gallery", "on the bay's radial line, 7 m short of the row", tangent=False),
    _arc("gap_in",    GAP_THETA,  R_INNER, 1.05, V_GALLERY, "gallery", "through the centre of the 4.5 m bay (inner row)", tangent=False),
    _arc("gap_out",   GAP_THETA,  R_WALK, Z_WALK, V_GALLERY, "gallery", "still on the bay's radial line, now on the "
         "centreline: the turn happens INSIDE the bay, not across the next column", tangent=False),
    _arc("gal_turn",  TURN_THETA, R_WALK, Z_WALK, V_GALLERY, "gallery", "on the centreline at the next column's theta"),
]
STATIONS += [_arc(f"gal_{i:02d}", th, R_WALK, Z_WALK, V_GALLERY, "gallery", "gallery centreline")
             for i, th in enumerate([GAL_THETA_0 - GAL_STEP * k
                                     for k in range(int(round((GAL_THETA_0 - GAL_THETA_1) / GAL_STEP)) + 1)])]
STATIONS += [
    _arc("gal_out", GAL_EXIT_THETA, R_WALK, 1.10, V_GALLERY, "gallery",
         "past the last columns (theta -66.90): the wing's open rotunda end"),
    # The approach swings SOUTH of the ENV_shrub_pitto7_1159 / big2_0920 group at (27..29, -19..-22), which the
    # first two round-14 routes clipped at 0.60 and 1.39 m; every station below probes >= 1.77 m clear.
    ("app_a",      ( 28.00, -24.00, 1.09), V_LAND, "approach", None, "terrain -0.66, clear 1.79"),
    ("app_b",      ( 26.50, -22.50, 1.14), V_LAND, "approach", None, "terrain -0.61, clear 1.77"),
    ("app_c",      ( 25.00, -21.00, 1.15), V_LAND, "approach", None, "terrain -0.60, clear 1.78"),
    ("app_d",      ( 24.00, -19.50, 1.15), V_LAND, "approach", None, "terrain -0.60, clear 1.78"),
    ("app_e",      ( 22.50, -17.80, 1.25), V_LAND, "approach", None, "terrain -0.60, on the az-218 face axis between "
                                                                     "the piers at az 194.5 and 239.5"),
    ("app_f",      ( 20.50, -16.00, 1.55), V_LAND, "approach", None, "ARCH_site_step_1 at -0.20"),
    ("app_g",      ( 17.30, -13.60, 1.75), V_LAND, "approach", None, "ARCH_site_platform 0.00; through the arch on the "
                                                                    "az-217 face (offset 0.45 m of a 12.5 m clear span)"),
    ("app_h",      ( 11.00,  -8.60, 1.75), V_LAND, "approach", None, "platform, inside the inner ring"),
    ("app_i",      (  6.30,  -4.90, 1.75), V_LAND, "approach", None, "platform"),
    ("dome",       qa_xy("CAM_qa_04_rotunda_ceiling") + (1.75,), V_LAND, "approach", None,
                                                "CAM_qa_04 station; the ceiling look-up"),
]
WATER_LEGS = {"water"}

# look-at target: (station name, "start"|"end"|0.0, (x, y, z)). "start"/"end" pin to the ends of that station's hold.
TARGET_KEYS = [
    ("hero",       "start", (0.0, 0.0, 14.0)),   # hero framing: 24 mm at 101 m holds the waterline and the apex
    ("hero",       "end",   (0.0, 0.0, 14.0)),
    ("lagoon_c",   0.0,     (0.0, 0.0, 12.0)),
    ("shore_over", 0.0,     (14.0, 2.0, 16.0)),  # swing off the rotunda toward the south wing over the landfall
    ("ne_apron",   0.0,     (0.0, 0.0, 21.1)),   # the round-07 CAM_qa_02 target: the rotunda over the courtyard
    ("gap_in",     0.0,     (0.0, 0.0, 12.0)),   # through the bay, still on the rotunda
    ("gal_04",     0.0,     (0.0, 0.0, 9.2)),    # CAM_qa_03's target: the rotunda seen through the columns
    ("gal_out",    0.0,     (0.0, 0.0, 12.0)),
    ("app_d",      0.0,     (0.0, 0.0, 18.0)),
    ("dome",       "start", (0.0, 2.0, 26.0)),   # arriving under the dome, up the drum
    ("dome",       "end",   (0.0, 4.5, 45.0)),   # the ceiling look-up, held; 2 deg off vertical keeps the roll stable
]


# ---------------------------------------------------------------------------------------------- curve + arc length
def _clear_old():
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


def build_path(coll, resolution_u=32):
    cu = bpy.data.curves.new("CAM_flythrough_path", "CURVE")
    cu.dimensions = "3D"
    cu.resolution_u = resolution_u
    cu.use_path = True
    cu.twist_mode = "Z_UP"
    sp = cu.splines.new("BEZIER")
    sp.bezier_points.add(len(STATIONS) - 1)
    for bp, st in zip(sp.bezier_points, STATIONS):
        bp.co = st[1]
        bp.handle_left_type = bp.handle_right_type = "AUTO"
    # Stations that lie on the colonnade arc get FREE handles on the arc TANGENT, with the exact cubic length for a
    # circular arc of the local step, h = (4/3) R tan(dtheta/4).  AUTO handles cut the corner at the gallery entry
    # and bulged the centreline out toward the outer row (round-14 check 1: 0.89 m from column_001).
    for i, st in enumerate(STATIONS):
        th = st[4]
        if th is None:
            continue
        steps = [abs(th - STATIONS[j][4]) for j in (i - 1, i + 1)
                 if 0 <= j < len(STATIONS) and STATIONS[j][4] is not None]
        if not steps:
            continue
        a = math.radians(th)
        fwd = Vector((math.sin(a), -math.cos(a), 0.0))       # direction of travel: theta DECREASING
        co = Vector(sp.bezier_points[i].co)
        sp.bezier_points[i].handle_left_type = sp.bezier_points[i].handle_right_type = "FREE"
        hl = (4.0 / 3.0) * R_WALK * math.tan(math.radians(steps[0]) / 4.0)
        hr = (4.0 / 3.0) * R_WALK * math.tan(math.radians(steps[-1]) / 4.0)
        sp.bezier_points[i].handle_left = co - fwd * hl
        sp.bezier_points[i].handle_right = co + fwd * hr
    obj = bpy.data.objects.new("CAM_flythrough_path", cu)
    coll.objects.link(obj)
    bpy.context.view_layer.update()
    return obj


def polyline(path_obj):
    """The evaluated polyline of the bezier, sampled exactly as Blender's path is (resolution_u per segment),
    so the arc-length fractions below are the ones Follow Path's offset_factor uses."""
    sp = path_obj.data.splines[0]
    res = path_obj.data.resolution_u
    bp = sp.bezier_points
    pts = []
    for i in range(len(bp) - 1):
        p0, p1 = Vector(bp[i].co), Vector(bp[i].handle_right)
        p2, p3 = Vector(bp[i + 1].handle_left), Vector(bp[i + 1].co)
        n = res if i < len(bp) - 2 else res + 1
        for k in range(n):
            u = k / res
            m = 1.0 - u
            pts.append(m * m * m * p0 + 3 * m * m * u * p1 + 3 * m * u * u * p2 + u * u * u * p3)
    cum = [0.0]
    for a, b in zip(pts, pts[1:]):
        cum.append(cum[-1] + (b - a).length)
    return pts, cum


def station_arclengths(path_obj):
    """Arc length of each station along that polyline (the stations ARE the bezier knots, so this is exact)."""
    _, cum = polyline(path_obj)
    res = path_obj.data.resolution_u
    return [cum[min(i * res, len(cum) - 1)] for i in range(len(STATIONS))], cum[-1]


# ---------------------------------------------------------------------------------------------- speed profile
def speed_profile(s_wp, caps, accel=ACCEL, ds=0.20):
    """Trapezoidal velocity profile: v <= the leg cap, |dv/dt| <= accel, v = 0 at both ends.
    Returns (grid_s, v, t) with t[i] the time to reach grid_s[i]."""
    S = s_wp[-1]
    n = max(2, int(S / ds) + 1)
    step = S / (n - 1)
    grid = [i * step for i in range(n)]
    v = []
    for s in grid:
        k = 1
        while k < len(s_wp) - 1 and s > s_wp[k] + 1e-9:
            k += 1
        v.append(caps[k])
    v[0] = v[-1] = 0.0
    for i in range(1, n):
        v[i] = min(v[i], math.sqrt(v[i - 1] ** 2 + 2 * accel * step))
    for i in range(n - 2, -1, -1):
        v[i] = min(v[i], math.sqrt(v[i + 1] ** 2 + 2 * accel * step))
    t = [0.0]
    for i in range(1, n):
        t.append(t[-1] + step / max(0.5 * (v[i - 1] + v[i]), 1e-6))
    return grid, v, t


def invert(t_grid, s_grid, tt, v_grid=None):
    """s at time tt from the monotone t -> s table.

    ROUND 16 (flythrough plan finding 1). With `v_grid` this integrates the profile EXACTLY inside the grid
    interval instead of interpolating s linearly across it. `speed_profile` grids arc length at ds = 0.20 m, so
    the first interval out of a hold spans v 0 -> 0.5 m/s, i.e. ~0.8 s of wall time; interpolating s linearly
    across it renders that whole interval at a constant 0.5 m/s and then steps, which sampled as 0.00 -> 0.50 m/s
    in one frame at the hero boundary (frame 85) and 2.10 -> 0.50 -> 0.00 settling under the dome (frames
    1105-1129): an effective 3.2 m/s^2 against the designed ACCEL 2.5, a visible jerk out of shot 1 and a snap
    into shot 6. The profile is piecewise-constant-acceleration by construction (v[i+1]^2 = v[i]^2 + 2 a ds), so
    s(tau) = s_i + v_i tau + a tau^2 / 2 is not an approximation: it is the curve the profile already describes,
    and it makes the rendered speed continuous at both hold boundaries."""
    if tt <= 0:
        return s_grid[0]
    if tt >= t_grid[-1]:
        return s_grid[-1]
    lo, hi = 0, len(t_grid) - 1
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if t_grid[mid] <= tt:
            lo = mid
        else:
            hi = mid
    ds = s_grid[hi] - s_grid[lo]
    if v_grid is not None and ds > 1e-12:
        v0, v1 = v_grid[lo], v_grid[hi]
        a = (v1 * v1 - v0 * v0) / (2.0 * ds)
        tau = tt - t_grid[lo]
        return min(s_grid[hi], s_grid[lo] + v0 * tau + 0.5 * a * tau * tau)
    f = (tt - t_grid[lo]) / max(t_grid[hi] - t_grid[lo], 1e-12)
    return s_grid[lo] + f * ds


def schedule(path_obj):
    """Frame -> arc length, plus the leg/hold frame ranges. Frame count is DERIVED from the route and the caps."""
    s_wp, total = station_arclengths(path_obj)
    caps = [st[2] for st in STATIONS]
    grid, v, t = speed_profile(s_wp, caps)
    t_move = t[-1]
    h1 = int(round(HOLD_HERO_S * FPS))
    move = int(math.ceil(t_move * FPS))
    frames = h1 + move + int(round(HOLD_DOME_S * FPS))
    frames = int(math.ceil(frames / 24.0) * 24)          # whole seconds
    s_of_frame = []
    for f in range(1, frames + 1):
        if f <= h1:
            s_of_frame.append(0.0)
        elif f <= h1 + move:
            s_of_frame.append(invert(t, grid, (f - h1) / FPS, v))
        else:
            s_of_frame.append(total)
    # station arrival frames
    arrive = {}
    for i, st in enumerate(STATIONS):
        target_s = s_wp[i]
        f = next((k + 1 for k, s in enumerate(s_of_frame) if s >= target_s - 1e-6), frames)
        arrive[st[0]] = max(1, f)
    arrive[STATIONS[0][0]] = 1
    legs, cur = [], None
    for i, st in enumerate(STATIONS[1:], start=1):
        label = st[3]
        f0 = arrive[STATIONS[i - 1][0]]
        f1 = arrive[st[0]]
        if cur and cur["name"] == label:
            cur["f1"] = f1
        else:
            cur = dict(name=label, f0=f0, f1=f1, cap=st[2], water=label in WATER_LEGS)
            legs.append(cur)
    holds = dict(hero=[1, h1], dome=[h1 + move, frames])
    return dict(fps=FPS, frames=frames, hold_hero_frames=h1, move_frames=move,
                path_length_m=round(total, 2), t_move_s=round(t_move, 2), legs=legs, holds=holds,
                arrive={k: int(v_) for k, v_ in arrive.items()},
                stations=[dict(name=st[0], pos=list(st[1]), cap=st[2], leg=st[3], note=st[5]) for st in STATIONS],
                s_station=[round(s, 2) for s in s_wp]), s_of_frame, total, s_wp, grid, v, t


# ---------------------------------------------------------------------------------------------- camera
def _all_fcurves(action):
    if hasattr(action, "fcurves") and len(action.fcurves):
        return list(action.fcurves)
    out = []
    for layer in getattr(action, "layers", []):
        for strip in layer.strips:
            for bag in strip.channelbags:
                out.extend(bag.fcurves)
    return out


def build_camera(coll, path_obj, sch, s_of_frame, total):
    tgt = bpy.data.objects.new("CAM_flythrough_target", None)
    tgt.empty_display_type = "SPHERE"
    tgt.empty_display_size = 1.5
    coll.objects.link(tgt)
    for name, when, p in TARGET_KEYS:
        if when == "start":
            f = sch["holds"]["hero"][0] if name == "hero" else sch["holds"]["dome"][0]
        elif when == "end":
            f = sch["holds"]["hero"][1] if name == "hero" else sch["holds"]["dome"][1]
        else:
            f = sch["arrive"][name]
        tgt.location = p
        tgt.keyframe_insert("location", frame=f)

    cam_data = bpy.data.cameras.new("CAM_flythrough")
    cam_data.lens = LENS
    cam_data.sensor_width = 36.0
    cam_data.sensor_fit = "HORIZONTAL"
    cam_data.clip_start = 0.1
    cam_data.clip_end = 5000.0
    cam_data.dof.use_dof = False
    cam = bpy.data.objects.new("CAM_flythrough", cam_data)
    cam.location = (0.0, 0.0, 0.0)
    coll.objects.link(cam)

    fp = cam.constraints.new("FOLLOW_PATH")
    fp.target = path_obj
    fp.use_fixed_location = True
    fp.use_curve_follow = False          # orientation comes from Track To
    fp.forward_axis = "TRACK_NEGATIVE_Z"
    fp.up_axis = "UP_Y"
    for f in range(1, sch["frames"] + 1):
        fp.offset_factor = min(1.0, max(0.0, s_of_frame[f - 1] / total))
        fp.keyframe_insert("offset_factor", frame=f)
    tt = cam.constraints.new("TRACK_TO")
    tt.target = tgt
    tt.track_axis = "TRACK_NEGATIVE_Z"
    tt.up_axis = "UP_Y"

    for fc in _all_fcurves(cam.animation_data.action):     # exact speed: no bezier overshoot on offset_factor
        for kp in fc.keyframe_points:
            kp.interpolation = "LINEAR"
    for fc in _all_fcurves(tgt.animation_data.action):     # the look-at may ease
        for kp in fc.keyframe_points:
            kp.interpolation = "BEZIER"
            kp.easing = "EASE_IN_OUT"
            kp.handle_left_type = kp.handle_right_type = "AUTO_CLAMPED"

    cam["fps"] = FPS
    cam["frames"] = sch["frames"]
    cam["path_length_m"] = total
    cam["schedule"] = json.dumps(sch)
    path_obj["path_length_m"] = total
    path_obj.data.path_duration = sch["frames"]
    return cam, tgt


def load_schedule():
    """The schedule as built, read back from the camera (so the check script needs no rebuild)."""
    cam = bpy.data.objects.get("CAM_flythrough")
    if cam is None or "schedule" not in cam.keys():
        return None
    return json.loads(cam["schedule"])


def build(scene):
    coll = common.get_collection("LIGHT")
    _clear_old()
    path_obj = build_path(coll)
    sch, s_of_frame, total, s_wp, grid, v, t = schedule(path_obj)
    cam, tgt = build_camera(coll, path_obj, sch, s_of_frame, total)
    scene.render.fps = FPS
    scene.frame_start, scene.frame_end = 1, sch["frames"]
    scene.frame_set(1)

    print(f"\n[light_flythrough] path {total:.1f} m; {sch['frames']} frames @ {FPS} fps = {sch['frames'] / FPS:.1f} s "
          f"(hero hold {sch['hold_hero_frames'] / FPS:.2f}s + move {sch['t_move_s']:.2f}s + dome hold "
          f"{(sch['frames'] - sch['hold_hero_frames'] - sch['move_frames']) / FPS:.2f}s), mean "
          f"{total / (sch['frames'] / FPS):.2f} m/s")
    print(f"[light_flythrough] legs:")
    for lg in sch["legs"]:
        print(f"    {lg['name']:10s} frames {lg['f0']:5d}-{lg['f1']:5d}  cap {lg['cap']:.1f} m/s"
              f"{'  (WATER CROSSING)' if lg['water'] else ''}")
    print(f"[light_flythrough] stations:")
    for i, st in enumerate(STATIONS):
        print(f"    {st[0]:11s} f{sch['arrive'][st[0]]:5d}  t={(sch['arrive'][st[0]] - 1) / FPS:6.2f}s  "
              f"s={s_wp[i]:7.1f} m  pos {st[1]}   {st[5]}")
    print(f"[light_flythrough] designed speed: max {max(v):.2f} m/s (water cap {V_WATER}, land {V_LAND}, "
          f"gallery {V_GALLERY})")
    return cam, path_obj, tgt, sch


def render_test(scene, cam, n=6, res=(640, 360)):
    """Phase 5 low-res Eevee test animation helper. NOT run in round 14 (no-render round)."""
    OUT.mkdir(parents=True, exist_ok=True)
    lp.apply_preview_eevee(scene, samples=16)
    scene.camera = cam
    scene.render.resolution_x, scene.render.resolution_y = res
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    sch = load_schedule() or dict(frames=scene.frame_end)
    frames = [1 + round(i * (sch["frames"] - 1) / (n - 1)) for i in range(n)]
    for f in frames:
        scene.frame_set(f)
        scene.render.filepath = str(OUT / f"flythrough_test_{f:04d}.png")
        t = time.time()
        bpy.ops.render.render(write_still=True)
        print(f"[light_flythrough] frame {f} ({time.time() - t:.1f}s) cam at "
              f"{tuple(round(x, 1) for x in cam.matrix_world.translation)}")


if __name__ == "__main__":
    args = common.script_args()
    blend = common.ASSET_FILES["LIGHT"]
    if not blend.exists():
        sys.exit("[light_flythrough] run light_build.py first")
    bpy.ops.wm.open_mainfile(filepath=str(blend))
    scene = bpy.context.scene
    cam, path_obj, tgt, sch = build(scene)
    for f in range(1, sch["frames"] + 1, max(1, sch["frames"] // 12)):
        scene.frame_set(f)
        m = cam.matrix_world
        p = tuple(round(x, 1) for x in m.translation)
        d = tuple(round(x, 2) for x in (m.to_quaternion() @ Vector((0.0, 0.0, -1.0))))
        print(f"[light_flythrough] f{f:5d} cam {p} fwd {d}")
    scene.frame_set(1)
    common.save_blend(blend)
