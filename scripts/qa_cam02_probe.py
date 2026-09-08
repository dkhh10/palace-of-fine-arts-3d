"""QA probe for the CAM_qa_02 re-station (QA / Critic owned; round 04). Reads master.blend, never saves it.

Sweeps a polar grid of stations around the rotunda, keeps the ON-LAND ones (downward ray hits terrain, not water),
solves the camera pitch per lens so the dome apex sits APEX_ROW from the top of a 16:9 frame (ref 062 letterboxed),
records where the podium base row lands, the attic width, and — by ray casting from the station to ~150 points on
the rotunda's visible faces — the fraction of the rotunda silhouette hidden by trees / by a colonnade. Then renders
the best candidates in Eevee at low cost so the eye can confirm the numbers.

    blender -b --python scripts/qa_cam02_probe.py -- [--out DIR] [--rmin 30 --rmax 70 --rstep 5 --azstep 10]
                                                     [--lenses 16,18,20,22,24] [--render-top 6] [--res 640 360] [--samples 8]
                                                     [--cams "name:x,y,z:tx,ty,tz:lens" ...]   # explicit stations only
Targets (ref 062 letterboxed into 16:9): apex 0.01-0.03 of the height from the top, podium base row 0.85 +- 0.03,
attic width 0.55 of the frame width, no water in the foreground, tree occlusion <= 10 % of the silhouette samples.
"""
import bpy, sys, os, math, time, json
from pathlib import Path
from mathutils import Vector, Matrix
from bpy_extras.object_utils import world_to_camera_view

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common

args = common.script_args()


def arg(name, default=None, n=1):
    if name not in args:
        return default
    i = args.index(name) + 1
    vals = []
    for v in args[i:]:
        if v.startswith("--"):
            break
        vals.append(v)
        if n and len(vals) >= n:
            break
    return vals[0] if n == 1 else vals


OUT = Path(arg("--out", "/tmp/qa_cam02"))
OUT.mkdir(parents=True, exist_ok=True)
RMIN, RMAX, RSTEP = float(arg("--rmin", 30)), float(arg("--rmax", 70)), float(arg("--rstep", 5))
AZSTEP = float(arg("--azstep", 10))
LENSES = [float(v) for v in arg("--lenses", "16,18,20,22,24").split(",")]
RENDER_TOP = int(arg("--render-top", 6))
RES = [int(v) for v in arg("--res", ["640", "360"], n=2)]
SAMPLES = int(arg("--samples", 8))
EYE = 1.5
APEX_ROW = 0.02          # ref 062: the dome cap touches the top edge; letterboxed target "within 3 % of the top"
BASE_ROW = 0.85          # ref 062 podium base row (letterboxed)
ATTIC_W = 0.554          # ref 062 attic 1350/1920 of a 1.40:1 photo, letterboxed into 16:9
FACE_AZ0 = 82.0          # hero face normal (az, deg clockwise from north); faces every 45 deg

bpy.ops.wm.open_mainfile(filepath=str(common.ROOT / "master.blend"), load_ui=False)
scene = bpy.context.scene
common.set_lod(viewport=1, render=1)
scene.render.resolution_x, scene.render.resolution_y = 1280, 720
scene.render.resolution_percentage = 100
bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get()


def az_to_xy(az, r):
    """az clockwise from north; -X north, +Y east."""
    a = math.radians(az)
    return (-r * math.cos(a), r * math.sin(a))


def cast(origin, direction, dist=1000.0):
    ok, loc, nrm, idx, ob, mat = scene.ray_cast(dg, Vector(origin), Vector(direction).normalized(), distance=dist)
    return (ob.name if ok and ob else None), (loc if ok else None)


def classify(name):
    if name is None:
        return "none"
    if name.startswith("ARCH_rotunda") or name.startswith("ORN_") or name.startswith("SOCKET_") \
            or name.startswith("ARCH_site_rostra") or name.startswith("ARCH_site_stair") \
            or (name.startswith("INST_") and "colonnade" not in name.lower()):
        return "rotunda"   # the rostra / podium walls and stairs are the rotunda's base in ref 062
    if name.startswith("ARCH_colonnade") or name.startswith("ARCH_pylon") or name.startswith("ARCH_hall") or name.startswith("ARCH_planter"):
        return "colonnade"
    if name.startswith("ENV_tree") or name.startswith("ENV_shrub"):
        return "tree"
    if "water" in name.lower() or "lagoon" in name.lower():
        return "water"
    if name.startswith("ENV_terrain") or name.startswith("ENV_riprap") or name.startswith("ARCH_site") \
            or "ground" in name.lower() or "lawn" in name.lower() or "path" in name.lower():
        return "ground"
    return "other"


t0 = time.time()
# apex from the geometry (march down through anything that is not the rotunda), podium face by a horizontal march
p = Vector((0, 0, 80))
APEX_Z = 49.4
for _ in range(8):
    name, loc = cast(p, (0, 0, -1), 120.0)
    print(f"[probe] apex march hit {name} at z {loc.z if loc else None}")
    if loc is None:
        break
    if classify(name) == "rotunda":   # INST_finial_008 is the 0.6 m apex cap on SOCKET_finial dome_apex (arch_params: apex 52.8 + 0.6)
        APEX_Z = loc.z
        break
    p = loc + Vector((0, 0, -0.05))
print(f"[probe] APEX_Z {APEX_Z:.2f} (bvh build {time.time()-t0:.1f}s)")
OTHER_NAMES = {}


def podium_base_point(az):
    """First rotunda surface met by a horizontal ray at z = 1.5 (inside the podium wall's 0-4.3 m band), then the
    ground row just outside that face: the visible bottom of the podium wall."""
    p = Vector(az_to_xy(az, 45.0) + (1.5,))
    d = (Vector((0, 0, 1.5)) - p).normalized()
    face = None
    for _ in range(12):
        name, loc = cast(p, d, 60.0)
        if name is None:
            return None
        if classify(name) == "rotunda":
            face = loc
            break
        p = loc + d * 0.05
    if face is None:
        return None
    out = face - d * 0.4
    gname, gloc = cast((out.x, out.y, 6.0), (0, 0, -1), 20.0)
    gz = gloc.z if gloc is not None else -0.6
    return Vector((face.x, face.y, min(gz, 0.0)))


# silhouette sample points on the visible outer faces (wall / attic / drum / dome)
SAMPLES_PTS = []
for az in range(0, 360, 10):
    for z in (2.0, 9.0, 16.0, 23.0, 30.0, 36.0):
        x, y = az_to_xy(az, 23.0)
        SAMPLES_PTS.append((Vector((x, y, z)), az))
    for r, z in ((11.0, 44.0), (5.0, 48.0)):
        x, y = az_to_xy(az, r)
        SAMPLES_PTS.append((Vector((x, y, z)), az))
SAMPLES_PTS.append((Vector((0, 0, APEX_Z - 0.3)), None))
# top surface of the rotunda solid (vertical rays over the plan): the visible top silhouette from a low station is
# usually the NEAR attic corner / figure, not the dome apex (from eye level the apex clears the near attic only
# beyond ~77 m: 52.6 / D > 37.5 / (D - 22)), so the framing solve uses the highest projected top point.
TOP_PTS = []
for r in [0.0] + [2.0 * k for k in range(1, 15)]:
    for az in (range(0, 360, 15) if r > 0 else [0]):
        x, y = az_to_xy(az, r)
        name, loc = cast((x, y, 80.0), (0, 0, -1), 100.0)
        if loc is not None and classify(name) == "rotunda" and loc.z > 20.0:
            TOP_PTS.append(Vector(loc))
print(f"[probe] {len(TOP_PTS)} top-surface points; max z {max(p.z for p in TOP_PTS):.2f}, "
      f"attic-ring (r 20-26) max z {max([p.z for p in TOP_PTS if 20 <= math.hypot(p.x, p.y) <= 26] or [0]):.2f}")
ATTIC_CORNERS = [Vector(az_to_xy(FACE_AZ0 + 22.5 + 45 * k, 24.4) + (35.0,)) for k in range(8)]

cam_data = bpy.data.cameras.new("PROBE_cam02")
cam_data.sensor_width, cam_data.sensor_fit = 36.0, "HORIZONTAL"
cam_data.clip_start, cam_data.clip_end = 0.1, 5000.0
cam_obj = bpy.data.objects.new("PROBE_cam02", cam_data)
scene.collection.objects.link(cam_obj)
scene.camera = cam_obj


def place(loc, target):
    rot = common.lookat_rotation(loc, target)
    cam_obj.matrix_world = Matrix.Translation(Vector(loc)) @ rot.to_matrix().to_4x4()


def row_of(pt):
    v = world_to_camera_view(scene, cam_obj, pt)
    return 1.0 - v.y, v.x


def solve_pitch(loc, lens):
    """target z so that the apex sits APEX_ROW from the top; returns (zt, base_row, attic_w)."""
    cam_data.lens = lens
    lo, hi = -60.0, 120.0
    for _ in range(40):
        zt = 0.5 * (lo + hi)
        place(loc, (0.0, 0.0, zt))
        r = min(row_of(p)[0] for p in TOP_PTS)     # visible top silhouette (near attic figure or the apex)
        if r > APEX_ROW:      # top too low in the frame -> tilt the camera DOWN (lower target)
            hi = zt
        else:
            lo = zt
    zt = 0.5 * (lo + hi)
    place(loc, (0.0, 0.0, zt))
    xs = [row_of(c)[1] for c in ATTIC_CORNERS]
    return zt, max(xs) - min(xs)


def occlusion(loc):
    cam = Vector(loc)
    vis = tree = col = other = 0
    for pt, az in SAMPLES_PTS:
        if az is not None:
            nx, ny = az_to_xy(az, 1.0)
            to_cam = (cam - pt)
            to_cam.z = 0
            if to_cam.length < 1e-6 or (Vector((nx, ny, 0)).dot(to_cam.normalized()) < math.cos(math.radians(75))):
                continue
        d = pt - cam
        name, _ = cast(cam, d, d.length + 3.0)
        c = classify(name)
        if c == "rotunda":
            vis += 1
        elif c == "tree":
            tree += 1
        elif c == "colonnade":
            col += 1
        elif c != "none":
            other += 1
            OTHER_NAMES[name] = OTHER_NAMES.get(name, 0) + 1
    n = max(1, vis + tree + col + other)
    return vis, tree / n, col / n, other / n


results = []
explicit = arg("--cams", [], n=0) or []
stations = []
if explicit:
    for s in explicit:
        name, loc, tgt, lens = s.split(":")
        loc = tuple(float(v) for v in loc.split(","))
        stations.append(dict(name=name, loc=loc, lens=float(lens), tgt=tuple(float(v) for v in tgt.split(","))))
else:
    az = 0.0
    while az < 360.0:
        r = RMIN
        while r <= RMAX + 1e-6:
            x, y = az_to_xy(az, r)
            gname, gloc = cast((x, y, 60.0), (0, 0, -1), 200.0)
            gc = classify(gname)
            if gc in ("ground", "other") and gloc is not None and gloc.z < 3.0:
                stations.append(dict(name=f"az{int(az):03d}_r{int(r):02d}", loc=(x, y, gloc.z + EYE), ground=gname))
            else:
                results.append(dict(name=f"az{int(az):03d}_r{int(r):02d}", az=az, r=r, skip=gc or "none", ground=gname))
            r += RSTEP
        az += AZSTEP
print(f"[probe] {len(stations)} on-land stations of {len(stations) + len(results)} ({time.time()-t0:.1f}s)")

for st in stations:
    loc = st["loc"]
    az = (math.degrees(math.atan2(loc[1], -loc[0])) + 360.0) % 360.0
    r = math.hypot(loc[0], loc[1])
    face_off = min(abs((az - FACE_AZ0 - 45 * k + 180) % 360 - 180) for k in range(8))
    vis, occ_t, occ_c, occ_o = occlusion(loc)
    base_pt = podium_base_point(az)
    best = None
    for lens in ([st["lens"]] if "lens" in st else LENSES):
        zt, attic_w = solve_pitch(loc, lens)
        if "tgt" in st:
            cam_data.lens = lens
            place(loc, st["tgt"])
            zt = st["tgt"][2]
        apex_row, _ = row_of(Vector((0, 0, APEX_Z)))      # > APEX_ROW means the dome is hidden behind the near attic
        top_row = min(row_of(p)[0] for p in TOP_PTS)
        base_row = row_of(base_pt)[0] if base_pt else float("nan")
        score = 3.0 * abs(base_row - BASE_ROW) + 1.0 * abs(attic_w - ATTIC_W) + 1.0 * occ_t + 2.0 * occ_c \
            + 0.01 * max(0.0, face_off - 15.0)
        rec = dict(name=st["name"], az=round(az, 1), r=round(r, 1), loc=[round(v, 2) for v in loc], lens=lens,
                   target_z=round(zt, 2), apex_row=round(apex_row, 3), top_row=round(top_row, 3), base_row=round(base_row, 3),
                   attic_w=round(attic_w, 3), occ_tree=round(occ_t, 3), occ_col=round(occ_c, 3), occ_other=round(occ_o, 3),
                   vis=vis, face_off=round(face_off, 1), score=round(score, 4), ground=st.get("ground"))
        if best is None or score < best["score"]:
            best = rec
        if explicit:
            results.append(rec)
    if not explicit:
        results.append(best)

cands = [r for r in results if "score" in r]
cands.sort(key=lambda r: r["score"])
ok = [r for r in cands if r["occ_tree"] <= 0.10 and r["occ_col"] <= 0.05]
print(f"[probe] {len(cands)} scored, {len(ok)} pass occlusion (tree <= 10 %, colonnade <= 5 %); sweep {time.time()-t0:.1f}s")
print("name        az     r   lens  tgt_z  top   apex  base   atticW  occT  occC  occO  vis  faceOff  score  ground")
for rec in (ok[:25] + [r for r in cands if r not in ok][:10]):
    print(f"{rec['name']:11s} {rec['az']:5.0f} {rec['r']:5.1f}  {rec['lens']:4.0f}  {rec['target_z']:6.2f} "
          f"{rec['top_row']:.3f} {rec['apex_row']:.3f} {rec['base_row']:.3f}  {rec['attic_w']:.3f}  {rec['occ_tree']:.2f}  {rec['occ_col']:.2f}  "
          f"{rec['occ_other']:.2f}  {rec['vis']:3d}  {rec['face_off']:5.1f}  {rec['score']:.3f}  {rec['ground']}")
print("[probe] 'other' occluder names:", sorted(OTHER_NAMES.items(), key=lambda kv: -kv[1])[:20])
(OUT / "cam02_probe.json").write_text(json.dumps(dict(apex_z=APEX_Z, results=results), indent=1))

to_render = (cands if explicit else ok)[:RENDER_TOP]
if to_render:
    import light_presets
    light_presets.apply_preview_eevee(scene, samples=SAMPLES)
    scene.render.resolution_x, scene.render.resolution_y = RES
    scene.render.resolution_percentage = 100
    for rec in to_render:
        cam_data.lens = rec["lens"]
        place(rec["loc"], (0.0, 0.0, rec["target_z"]))
        fp = OUT / f"cam02_{rec['name']}_l{int(rec['lens'])}.png"
        scene.render.filepath = str(fp)
        t = time.time()
        bpy.ops.render.render(write_still=True)
        print(f"[probe] rendered {rec['name']} lens {rec['lens']} loc {rec['loc']} target_z {rec['target_z']} -> {fp} ({time.time()-t:.1f}s)")
print(f"[probe] done in {time.time()-t0:.1f}s")
