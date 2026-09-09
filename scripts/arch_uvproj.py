"""Second UV layer `UVProj` on the hero-facing ARCH meshes: the vertex's position in the CAM_qa_01_lagoon_hero frame.

    blender -b assets/architecture.blend --background --python scripts/arch_uvproj.py -- [--dry] [--save]

Why (docs/briefs/materials_r8_projection.md): the photo-projection pass needs a camera-space UV. Every ARCH mesh
carries exactly one UV layer, `UVMap`, written by `arch_lib.cube_project_uv` -- a triplanar box projection in world
metres, overlapping and not in 0..1 (docs/arch_notes.md round 4 item 3). It is the right input for the tiling
concrete material and the wrong one for a camera projection, and it must not be overwritten. So this script adds a
SECOND layer, leaving `UVMap` first, active and active_render.

`UVProj` convention: u = x of `bpy_extras.object_utils.world_to_camera_view` at 1920x1080, v = its y, i.e. u,v in
0..1 over the frame with v = 0 at the BOTTOM (Blender's image convention). Pixel column = u * 1920, pixel row from
the top = (1 - v) * 1080. Vertices behind the camera (w2cv z <= 0) or outside 0..1 are CLAMPED into 0..1 and flagged
in the POINT float attribute `UVProj_valid` (1.0 = inside the frame and in front of the camera, 0.0 = clamped): a
projection shader must multiply its weight by that attribute or the frame edge smears across the far side.

Objects: the hero-facing bands of docs/arch_notes.md round 4 item 3 -- attic sweeps + the per-face 00/07/01 panels,
frames, niches and pilasters, the entablature and its dentil / modillion / egg courses (both LOD objects share ONE
mesh, so the layer is written once on the mesh and both objects get it), and the drum / band / cornice.

Geometry only: nothing renders, no master.blend is touched.
"""
import bpy, sys, os, math, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
import arch_params as P
import arch_lib as L
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

args = common.script_args()
DRY = "--dry" in args
SAVE = "--save" in args
CAM_NAME = "CAM_qa_01_lagoon_hero"
RES = (1920, 1080)
UV_NAME = "UVProj"
FLAG = "UVProj_valid"

# ----------------------------------------------------------------------------- the object list (round 4 item 3)
HERO_FACES = (0, 7, 1)          # 00 = the lagoon face (az 82); 07 (az 37) and 01 (az 127) are obliquely visible
NAMES = ["ARCH_rotunda_attic_base", "ARCH_rotunda_attic_cornice", "ARCH_rotunda_attic_roof",
         "ARCH_rotunda_entablature",
         "ARCH_rotunda_dentils_LOD0", "ARCH_rotunda_dentils_LOD1",
         "ARCH_rotunda_modillions_LOD0", "ARCH_rotunda_modillions_LOD1",
         "ARCH_rotunda_eggs_LOD0",
         "ARCH_rotunda_drum", "ARCH_rotunda_drum_band", "ARCH_rotunda_drum_cornice"]
for k in HERO_FACES:
    NAMES += [f"ARCH_rotunda_attic_panel_{k:02d}", f"ARCH_rotunda_attic_frame_{k:02d}",
              f"ARCH_rotunda_attic_niche_{k:02d}",
              f"ARCH_rotunda_attic_pilaster_{k:02d}_a", f"ARCH_rotunda_attic_pilaster_{k:02d}_b",
              f"ARCH_rotunda_attic_corner_{k:02d}", f"ARCH_rotunda_attic_corner_cap_{k:02d}"]

# ----------------------------------------------------------------------------- camera
scene = bpy.context.scene
cam = bpy.data.objects.get(CAM_NAME)
if cam is None:                                   # asset file: bring in the fixed QA set (never saved with it)
    import qa_cameras
    qa_cameras.ensure(scene)
    cam = bpy.data.objects.get(CAM_NAME)
if cam is None:
    raise SystemExit(f"camera {CAM_NAME} not found")
scene.camera = cam
scene.render.resolution_x, scene.render.resolution_y = RES
scene.render.resolution_percentage = 100
scene.render.pixel_aspect_x = scene.render.pixel_aspect_y = 1.0
bpy.context.view_layer.update()
print(f"[uvproj] {CAM_NAME} loc {tuple(round(v, 2) for v in cam.location)} lens {cam.data.lens} "
      f"shift {cam.data.shift_x:.3f},{cam.data.shift_y:.3f} res {RES[0]}x{RES[1]}")


def frame_px(world):
    """world Vector -> (col, row) in 1920x1080 pixels, plus w2cv depth."""
    co = world_to_camera_view(scene, cam, Vector(world))
    return co.x * RES[0], (1.0 - co.y) * RES[1], co.z


def world_matrix(o):
    """matrix_world is STALE for objects hidden in the view layer (LOD0 is hide_viewport in the saved file), so it
    reports identity for them. matrix_basis is derived from loc/rot/scale on access and is always current.

    r5 review finding 3: matrix_basis is only the world matrix for an UNPARENTED object with no delta transform.
    A parented hidden object has a stale matrix_world too, so there is no correct answer here -- refuse instead of
    silently baking a wrong projection. Nothing in arch_build/arch_lib parents an ARCH object today."""
    if o.parent is not None or tuple(o.delta_location) != (0.0, 0.0, 0.0) or tuple(o.delta_scale) != (1.0, 1.0, 1.0):
        raise SystemExit(f"[uvproj] {o.name} is parented or has a delta transform: matrix_world may be stale for a "
                         f"hidden object and matrix_basis is not its world matrix. Walk the parent chain first.")
    return o.matrix_basis


def ray_px(az_deg, r, z):
    """A point r metres out along compass azimuth az at height z -> (col, row). Same math as arch_entab_probe.pix."""
    nx, ny = P.az_dir(az_deg)
    return frame_px((nx * r, ny * r, z))


# ----------------------------------------------------------------------------- resolve the objects, group by mesh
objs, missing = [], []
for n in NAMES:
    o = bpy.data.objects.get(n)
    (objs if (o is not None and o.type == "MESH") else missing).append(o if o is not None else n)
by_mesh = {}
for o in objs:
    by_mesh.setdefault(o.data.name, []).append(o)
print(f"[uvproj] {len(objs)} objects / {len(by_mesh)} meshes; missing: {missing if missing else 'none'}")
pre_fails = 0        # r5 review finding 4: the shared-mesh agreement is now ENFORCED, not just printed
for mname, group in sorted(by_mesh.items()):
    if len(group) > 1:      # LOD siblings sharing a mesh: one camera UV can only be right if their transforms agree
        m0 = world_matrix(group[0])
        for o in group[1:]:
            d = max(abs(a - b) for ra, rb in zip(m0, world_matrix(o)) for a, b in zip(ra, rb))
            bad = d > 1e-6
            pre_fails += bad
            print(f"[uvproj] shared mesh {mname}: {group[0].name} / {o.name} matrix_world max delta {d:.2e} "
                  f"{'FAIL (one mesh cannot carry two camera UVs)' if bad else 'OK'}")

if DRY:
    for o in sorted(objs, key=lambda o: o.name):
        bb = [world_matrix(o) @ Vector(c) for c in o.bound_box]
        print(f"[uvproj]   {o.name:44s} verts {len(o.data.vertices):6d} polys {len(o.data.polygons):6d} "
              f"uv {[u.name for u in o.data.uv_layers]} loc {tuple(round(v, 2) for v in o.location)} "
              f"z {min(v.z for v in bb):.2f}..{max(v.z for v in bb):.2f}")
    raise SystemExit(0)

# ----------------------------------------------------------------------------- write the layer
tot_v = tot_clamped = 0
worst = 0.0
for mname, group in sorted(by_mesh.items()):
    me = group[0].data
    mw = world_matrix(group[0])
    uv = me.uv_layers.get(UV_NAME) or me.uv_layers.new(name=UV_NAME, do_init=False)
    if FLAG in me.attributes:
        me.attributes.remove(me.attributes[FLAG])
    flag = me.attributes.new(name=FLAG, type="FLOAT", domain="POINT")
    uv = me.uv_layers[UV_NAME]   # r5 review finding 5: CustomData may reallocate on the attribute remove/add
    vuv, vflag = [], []
    for v in me.vertices:
        co = world_to_camera_view(scene, cam, mw @ v.co)
        ok = co.z > 0.0 and 0.0 <= co.x <= 1.0 and 0.0 <= co.y <= 1.0
        vuv.append((min(1.0, max(0.0, co.x)), min(1.0, max(0.0, co.y))))
        vflag.append(1.0 if ok else 0.0)
    data = uv.data
    for li, lp in enumerate(me.loops):
        data[li].uv = vuv[lp.vertex_index]
    flag.data.foreach_set("value", vflag)
    # UVMap stays layer 0, active and active_render
    idx = me.uv_layers.find("UVMap")
    if idx >= 0:
        me.uv_layers.active_index = idx
        me.uv_layers["UVMap"].active_render = True
    n_clamp = int(len(vflag) - sum(vflag))
    tot_v += len(vflag)
    tot_clamped += n_clamp
    # round-trip: read the layer back and check every LOOP against the camera projection of its own vertex
    err = 0.0
    for li, lp in enumerate(me.loops):
        if vflag[lp.vertex_index] < 0.5:
            continue
        u, w = data[li].uv
        c, r, _ = frame_px(mw @ me.vertices[lp.vertex_index].co)
        err = max(err, abs(u * RES[0] - c), abs((1.0 - w) * RES[1] - r))
    worst = max(worst, err)
    print(f"[uvproj] {mname:40s} objs {len(group)} verts {len(vflag):6d} clamped {n_clamp:6d} "
          f"({100.0 * n_clamp / max(1, len(vflag)):5.1f} %) layers {[u.name for u in me.uv_layers]} "
          f"active {me.uv_layers.active.name} active_render "
          f"{[u.name for u in me.uv_layers if u.active_render]} round-trip {err:.2e} px")
print(f"[uvproj] TOTAL verts {tot_v} clamped {tot_clamped} ({100.0 * tot_clamped / max(1, tot_v):.1f} %) "
      f"worst round-trip {worst:.2e} px")

# ----------------------------------------------------------------------------- named-point checks (brief item 1)
# Three points whose frame position is predicted from arch_params ALONE (no mesh), then compared with the UV the
# layer actually carries at that point on the surface. Tolerance: 2 px.
# The point is looked up with `closest_point_on_mesh` and the UV interpolated across the triangle that owns it,
# because a swept ring has vertices only at its plan corners: the centre of face 00 is 4.6 m from the nearest
# vertex, so a nearest-vertex read would measure the sweep's vertex spacing, not the UV.
from mathutils.geometry import barycentric_transform, intersect_point_tri


def uv_at(o, world_pt):
    """(col, row) that the UVProj layer gives at the surface point nearest `world_pt`, and how far that point is."""
    me = o.data
    mw = world_matrix(o)
    ok, loc, nrm, fidx = o.closest_point_on_mesh(mw.inverted() @ Vector(world_pt))
    if not ok:
        return None, None, None
    me.calc_loop_triangles()
    uvl = me.uv_layers[UV_NAME].data
    tris = [t for t in me.loop_triangles if t.polygon_index == fidx]
    pick = None
    for t in tris:
        a, b, c = (me.vertices[i].co for i in t.vertices)
        if intersect_point_tri(loc, a, b, c) is not None:
            pick = t
            break
    t = pick or tris[0]
    a, b, c = (me.vertices[i].co for i in t.vertices)
    ua, ub, uc = (Vector((*uvl[li].uv, 0.0)) for li in t.loops)
    uvw = barycentric_transform(loc, a, b, c, ua, ub, uc)
    return uvw.x * RES[0], (1.0 - uvw.y) * RES[1], (mw @ loc - Vector(world_pt)).length
# The three offsets used to be hand-entered (0.74 / 1.66 / 3.48 / -0.15). Round 6 takes the first three from
# arch_params, so the checks follow the profile instead of being re-fitted to it (r5 review finding 2).
CHECKS = [
    ("attic corner   (attic cornice crown, ressaut az 59.5)", "ARCH_rotunda_attic_cornice",
     P.VERTEX_AZ0, P.CHAMFER_CIRCUMRADIUS + P.ATTIC_CORNICE_D, P.ATTIC_Z1 - 0.06),
    ("cornice corona (face 00 centre, soffit lip)", "ARCH_rotunda_entablature",
     P.FACE_AZ0, P.WALL_APOTHEM + P.CORNICE_CORONA_D, P.ENTABLATURE_Z0 + P.CORNICE_CORONA_SOFFIT_DZ),
    ("drum ring      (cornice ring rim, near side)", "ARCH_rotunda_drum_cornice",
     P.FACE_AZ0, P.DRUM_CORNICE_R, P.DRUM_Z1 - 0.15),
]
print(f"{'check':52s} {'pred col,row':>17s} {'uv col,row':>17s} {'d px':>7s} {'surf dist m':>11s}")
fails = pre_fails
for label, oname, az, r, z in CHECKS:
    o = bpy.data.objects.get(oname)
    if o is None:
        print(f"{label:52s}  MISSING {oname}")
        fails += 1
        continue
    pc, pr, _ = ray_px(az, r, z)
    nx, ny = P.az_dir(az)
    target = Vector((nx * r, ny * r, z))
    uc, ur, sd = uv_at(o, target)
    if uc is None:
        print(f"{label:52s}  closest_point_on_mesh failed on {oname}")
        fails += 1
        continue
    dpx = math.hypot(uc - pc, ur - pr)
    fails += dpx > 2.0
    print(f"{label:52s} {pc:8.1f},{pr:7.1f} {uc:8.1f},{ur:7.1f} {dpx:7.2f} {sd:11.3f}  "
          f"{oname}  {'OK' if dpx <= 2.0 else 'FAIL'}")

# ----------------------------------------------------------------------------- tri counts (must be unchanged)
ARCH = bpy.data.collections.get("ARCH")
stats = {}
for lod in (0, 1, 2):
    sel = [o for o in ARCH.all_objects if o.type == "MESH" and (f"_LOD{lod}" in o.name or "_LOD" not in o.name)
           and not o.name.startswith("PH_")]
    stats[f"tris_LOD{lod}"] = L.tri_count(sel)
stats["objects"] = len(ARCH.all_objects)
old = json.loads((common.DOCS / "arch_stats.json").read_text())
for k, v in stats.items():
    print(f"[uvproj] {k}: {v} (arch_stats.json {old.get(k)}) {'SAME' if old.get(k) == v else 'CHANGED'}")
    fails += old.get(k) != v

if SAVE and not fails:
    common.save_blend(common.ASSETS / "architecture.blend")
    print("[uvproj] saved assets/architecture.blend")
elif SAVE:
    print(f"[uvproj] NOT SAVED: {fails} check(s) failed")
print(f"[uvproj] done, {fails} failure(s)")
