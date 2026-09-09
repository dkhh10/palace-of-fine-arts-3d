"""QA-05-6 probe: where does the rotunda entablature land in cam01 pixels, and what does a crop of it look like?

    blender --background <blend> --python scripts/arch_entab_probe.py -- [--map] [--courses] [--sil]
                                        [--render OUT.png]
                                        [--cam CAM_qa_01_lagoon_hero] [--res 1920 1080] [--spp 48]
                                        [--border x0 y0 x1 y1]

--courses prints the course-row table (ARCH round 5 item 2): for each named course of the hero face, its z, its
        projection d measured OFF THE MESH at that z, and the cam01 pixel row it occupies. Pairs with QA round 6
        item 7 (the same rows read off ref 169) so the per-course stack offset can be stated in metres.
--sil   geometric cam01 silhouette signature (no render): apex row, attic width and the attic corner-top row,
        projected straight from the vertices of the render set. Comparable with the alpha-render silhouette
        measured in round 4 through crop 690 40 1235 520 (add the crop origin to those numbers).

--map   prints, for a grid of (d, z) points on the near (lagoon) face of the rotunda -- d = projection outward from
        the wall plane at apothem P.WALL_APOTHEM, z = world height -- the pixel row/column the camera puts them at.
        This is the only honest way to know which model surface owns which row of QA's box 900 262 1020 296:
        a projecting moulding is lifted up the frame by (d * tan(up-look angle)), so profile depth and height mix.
--render renders only the border box (Cycles, --spp samples, denoised) into a full-frame-sized PNG, so the QA box
        coordinates stay valid while the render costs a fraction of a hero frame.
"""
import bpy, sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
import arch_params as P
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector
from mathutils.bvhtree import BVHTree

args = common.script_args()


def opt(flag, n=1, cast=float, default=None):
    if flag not in args:
        return default
    vals = args[args.index(flag) + 1:args.index(flag) + 1 + n]
    return [cast(v) for v in vals] if n > 1 else cast(vals[0])


CAM = opt("--cam", 1, str, "CAM_qa_01_lagoon_hero")
RES = opt("--res", 2, int, [1920, 1080])
SPP = opt("--spp", 1, int, 48)
OUT = opt("--render", 1, str, None)
BORDER = opt("--border", 4, int, None)

scene = bpy.context.scene
cam = bpy.data.objects.get(CAM)
if cam is None:                       # asset file: bring the fixed QA set in (nothing is saved)
    import qa_cameras
    qa_cameras.ensure(scene := bpy.context.scene)
    bpy.context.view_layer.update()
    cam = bpy.data.objects.get(CAM)
if cam is None:
    raise SystemExit(f"camera {CAM} not found: {[o.name for o in bpy.data.objects if o.type == 'CAMERA']}")
scene.camera = cam
scene.render.resolution_x, scene.render.resolution_y = RES
scene.render.resolution_percentage = 100

# near (lagoon) face: outward normal at compass azimuth FACE_AZ0, wall plane at apothem WALL_APOTHEM
nx, ny = P.az_dir(P.FACE_AZ0)


def pix(d, z):
    """(projection d outward from the wall plane, world height z) on the near face centre -> (col, row)"""
    r = P.WALL_APOTHEM + d
    co = world_to_camera_view(scene, cam, Vector((nx * r, ny * r, z)))
    return co.x * RES[0], (1.0 - co.y) * RES[1]


def world_matrix(o):
    """matrix_world is stale (identity) for objects hidden in the view layer -- every _LOD0 in the saved asset."""
    return o.matrix_world if o.parent is not None else o.matrix_basis


def wverts(names):
    for n in names:
        o = bpy.data.objects.get(n)
        if o is None or o.type != "MESH":
            continue
        mw = world_matrix(o)
        for v in o.data.vertices:
            yield mw @ v.co


# the ressaut / corner block starts RESSAUT_ALONG in from the end of the face, so the flat part of face 00 runs
# +-(FACE_LENGTH/2 - RESSAUT_ALONG) = 5.70 m either side of its centre; stay well inside it or the corner blocks
# (which project to the chamfer plane at circumradius 25) are read as if they were courses of the face.
FACE_HALF = P.FACE_LENGTH / 2 - P.RESSAUT_ALONG - 1.7


_BVH = {}


def bvh_of(name):
    """World-space BVH of an object's own mesh. Object.ray_cast needs an EVALUATED mesh, which a hidden object
    (every _LOD0 in the saved asset) does not have; this works on the mesh data itself. Modifiers (the bevels,
    <= 2 cm) are not included."""
    if name not in _BVH:
        o = bpy.data.objects.get(name)
        if o is None or o.type != "MESH":
            _BVH[name] = None
        else:
            M = world_matrix(o)
            _BVH[name] = BVHTree.FromPolygons([M @ v.co for v in o.data.vertices],
                                              [list(p.vertices) for p in o.data.polygons])
    return _BVH[name]


def face_d(names, z, dz=0.0, samples=41, halfwidth=FACE_HALF):
    """Projection d of the built profile at height z on the flat part of face 00, MEASURED: horizontal rays fired
    inward at that height, max hit distance outward from the wall plane. A swept ring has vertices only at its plan
    corners, so the face centre must be sampled by ray, not by vertex. dz nudges the ray inside the course
    (+ for a course bottom, - for a course top) so a shared boundary is not read off the neighbour."""
    tx, ty = -ny, nx
    best = None
    for n in names:
        bvh = bvh_of(n)
        if bvh is None:
            continue
        for i in range(samples):
            t = -halfwidth + 2 * halfwidth * i / (samples - 1)
            org = Vector((nx * (P.WALL_APOTHEM + 8.0) + tx * t, ny * (P.WALL_APOTHEM + 8.0) + ty * t, z + dz))
            loc, nor, idx, dist = bvh.ray_cast(org, Vector((-nx, -ny, 0.0)), 14.0)
            if loc is not None:
                d = loc.x * nx + loc.y * ny - P.WALL_APOTHEM
                best = d if best is None else max(best, d)
    return best


if "--courses" in args:
    # z of each course: arch_params where the vertical stack defines it, the object's own bounding box where the
    # mesh does. d always measured by ray. Pairs with QA round 6 item 7 (the same courses read off ref 169).
    def bbz(name, hi=True):
        o = bpy.data.objects.get(name)
        bb = [world_matrix(o) @ Vector(c) for c in o.bound_box]
        return max(v.z for v in bb) if hi else min(v.z for v in bb)

    ENT = ["ARCH_rotunda_entablature"]
    # the corona soffit lip is the lowest z of the entablature's outermost course -- measured, not assumed
    scan = [(P.ENTABLATURE_Z0 + i * 0.01, face_d(ENT, P.ENTABLATURE_Z0 + i * 0.01)) for i in range(381)]
    dmax = max(d for _, d in scan if d is not None)
    soffit_z = min(z for z, d in scan if d is not None and d >= dmax - 0.05)
    # names=None means "d is the literal value in the 4th slot" (the sunk relief field is behind the wall plane, so
    # an inward ray measures the wall, not the field).
    COURSES = [
        ("attic top (cornice crown)", bbz("ARCH_rotunda_attic_cornice"), ["ARCH_rotunda_attic_cornice"], -0.02),
        ("attic cornice corona soffit", P.ATTIC_Z1 - P.ATTIC_TOP_CORNICE_H + P.ATTIC_CORNICE_SOFFIT_DZ,
         ["ARCH_rotunda_attic_cornice"], 0.02),
        ("attic relief field top", P.ATTIC_Z1 - P.ATTIC_TOP_CORNICE_H - P.ATTIC_PANEL_FRAME, None, -P.ATTIC_PANEL_DEPTH),
        ("attic panel frame top", bbz("ARCH_rotunda_attic_frame_00"), ["ARCH_rotunda_attic_frame_00"], -0.02),
        ("attic panel frame bottom", bbz("ARCH_rotunda_attic_frame_00", False), ["ARCH_rotunda_attic_frame_00"], 0.02),
        ("attic relief field bottom", P.ATTIC_Z0 + P.ATTIC_BASE_MOULDING_H + P.ATTIC_PANEL_FRAME, None,
         -P.ATTIC_PANEL_DEPTH),
        ("cornice corona top", P.ENTABLATURE_Z1, ENT, -0.02),
        ("cornice corona bottom (soffit lip)", soffit_z, ENT, 0.02),
        ("dentil bed (block bottom)", bbz("ARCH_rotunda_dentils_LOD0", False), ["ARCH_rotunda_dentils_LOD0"], 0.02),
        ("frieze top", P.ENTABLATURE_Z0 + P.ARCHITRAVE_H + P.FRIEZE_H, ENT, -0.02),
        ("frieze bottom", P.ENTABLATURE_Z0 + P.ARCHITRAVE_H, ENT, 0.02),
        ("architrave bottom", P.ENTABLATURE_Z0, ENT, 0.02),
    ]
    c0, r0 = pix(0.0, P.ENTABLATURE_Z0)
    c1, r1 = pix(0.0, P.ENTABLATURE_Z1)
    scale = (r0 - r1) / (P.ENTABLATURE_Z1 - P.ENTABLATURE_Z0)
    print(f"[courses] {CAM} {RES[0]}x{RES[1]}, wall plane {scale:.2f} px/m; d measured by ray on the flat part of "
          f"face 00 (+-{FACE_HALF:.2f} m of its centre)")
    print(f"{'course':38s} {'z m':>7s} {'d m':>7s} {'row':>8s} {'col':>8s}  {'drop from the course above':>28s}")
    prev = None
    for label, z, names, dz in COURSES:
        d = dz if names is None else face_d(names, z, dz)
        d = 0.0 if d is None else d
        col, row = pix(d, z)
        print(f"{label:38s} {z:7.2f} {d:7.2f} {row:8.1f} {col:8.1f}  "
              + (f"{row - prev:+28.1f}" if prev is not None else f"{'-':>28s}"))
        prev = row
    # the rotunda capitals stand on the piers, not on the face centre: report the one nearest the hero face
    socks = [o for o in bpy.data.objects if o.name.startswith("SOCKET_capital_rotunda")]
    if socks:
        def azof(o):
            p = world_matrix(o).translation
            return math.degrees(math.atan2(p.y, -p.x)) % 360.0
        s = min(socks, key=lambda o: abs((azof(o) - P.FACE_AZ0 + 180.0) % 360.0 - 180.0))
        p = world_matrix(s).translation      # r5 review finding 6: use the same accessor as everything else
        r = math.hypot(p.x, p.y)
        ztop = p.z + P.CAPITAL_H
        co = world_to_camera_view(scene, cam, Vector((p.x, p.y, ztop)))   # r5 review finding 6: p.x / r * r was a no-op
        print(f"{'capital top (pier, az ' + format(azof(s), '.1f') + ')':38s} {ztop:7.2f} {r - P.WALL_APOTHEM:7.2f} "
              f"{(1.0 - co.y) * RES[1]:8.1f} {co.x * RES[0]:8.1f}   socket {s.name}, abacus projection is ORN's")

if "--sil" in args:
    # Geometric cam01 silhouette, no render: the top profile is built by projecting the vertices of the render set
    # (LOD0 + unsuffixed) and keeping the topmost row per column, then qa_silhouette.measure's own arithmetic is
    # applied to it -- apex = min over the central 30 % of the building's width, corner_top = median over the outer
    # 12 %, W_a = width at corner_top + 6 % of the crop height. Directly comparable with the round-4 alpha-render
    # numbers (crop 690 40 1235 520: apex_y 88, corner_top_y 212, wa_px 544, rise/W_a 0.228), which qa_silhouette
    # reports in ABSOLUTE image rows.
    SILCROP = opt("--silcrop", 4, int, [690, 40, 1235, 520])
    x0, y0, x1, y1 = SILCROP
    ARCH = bpy.data.collections.get("ARCH")
    LOD = opt("--sillod", 1, int, 1)      # the SAVED asset renders LOD1 (arch_build: LOD0/LOD2 are hide_render)
    PH = "--silph" in args                # the PH_ placeholder urns / figures, which the alpha render of round 4 saw
    render_set = [o for o in ARCH.all_objects if o.type == "MESH" and (PH or not o.name.startswith("PH_"))
                  and ("_LOD" not in o.name or f"_LOD{LOD}" in o.name)]
    if PH:
        render_set += [o for o in bpy.data.objects if o.name.startswith("PH_") and o.type == "MESH"
                       and o.name not in {x.name for x in render_set}]
    prof = [-1] * (x1 - x0)
    owner = [None] * (x1 - x0)
    used = nverts = 0
    for o in render_set:
        M = world_matrix(o)
        bb = [world_to_camera_view(scene, cam, M @ Vector(c)) for c in o.bound_box]
        if (max(c.x for c in bb) * RES[0] < x0 or min(c.x for c in bb) * RES[0] > x1
                or max((1.0 - c.y) * RES[1] for c in bb) < y0 or min((1.0 - c.y) * RES[1] for c in bb) > y1
                or max(c.z for c in bb) <= 0.0):
            continue
        used += 1
        pv = []
        for v in o.data.vertices:
            co = world_to_camera_view(scene, cam, M @ v.co)
            nverts += 1
            pv.append((co.x * RES[0], (1.0 - co.y) * RES[1], co.z))
        # rasterise the projected EDGES, not the vertices: a swept ring has vertices only at its plan corners, so a
        # vertex-only profile leaves most columns empty and the median of the outer band reads the ring's lower edge.
        for poly in o.data.polygons:
            vi = list(poly.vertices)
            for k in range(len(vi)):
                a, b = pv[vi[k]], pv[vi[(k + 1) % len(vi)]]
                if a[2] <= 0.0 or b[2] <= 0.0:
                    continue
                ca, cb = a[0], b[0]
                if ca > cb:
                    a, b, ca, cb = b, a, cb, ca
                for c in range(max(int(math.ceil(ca)), x0), min(int(math.floor(cb)), x1 - 1) + 1):
                    r = a[1] if cb - ca < 1e-9 else a[1] + (b[1] - a[1]) * (c - ca) / (cb - ca)
                    i = c - x0
                    if y0 <= r <= y1 and (prof[i] < 0 or r < prof[i]):
                        prof[i] = r
                        owner[i] = o.name
    import statistics
    valid = [i for i, v in enumerate(prof) if v >= 0]
    lx, rx = valid[0], valid[-1]
    w = rx - lx
    cen = [prof[i] for i in range(lx + int(0.35 * w), lx + int(0.65 * w)) if prof[i] >= 0]
    apex = min(cen)
    edge = [prof[i] for i in list(range(lx, lx + int(0.12 * w))) + list(range(rx - int(0.12 * w), rx + 1))
            if prof[i] >= 0]
    corner_top = statistics.median(edge)
    row = min(y1 - 1, corner_top + max(4, int(0.06 * (y1 - y0))))
    cov = [i for i, v in enumerate(prof) if 0 <= v <= row]
    wa = cov[-1] - cov[0]
    print(f"[sil] LOD{LOD}{' +PH' if PH else ''} crop {SILCROP} objects {used}/{len(render_set)} verts {nverts}")
    print(f"[sil] apex_y {apex:.1f}  corner_top_y {corner_top:.1f}  wa_row {row:.0f}  "
          f"wa {x0 + cov[0]}..{x0 + cov[-1]} = {wa} px  rise {corner_top - apex:.1f} px  "
          f"rise/W_a {(corner_top - apex) / wa:.4f}")
    if "--silwho" in args:
        for a, b in ((lx, lx + int(0.12 * w)), (rx - int(0.12 * w), rx + 1)):
            seen = {}
            for i in range(a, b):
                if prof[i] >= 0:
                    seen.setdefault(owner[i], []).append(prof[i])
            print(f"[sil] cols {x0 + a}..{x0 + b}: " + "; ".join(
                f"{k} n={len(v)} rows {min(v):.0f}-{max(v):.0f}" for k, v in sorted(seen.items())))
    print(f"[sil] round-4 alpha render (arch_r4b, docs/arch_notes.md): apex_y 88  corner_top_y 212  wa 544  "
          f"rise/W_a 0.228")

if "--map" in args or (OUT is None and "--courses" not in args and "--sil" not in args):   # r5 review finding 7
    print(f"[probe] {CAM} loc {tuple(round(v, 2) for v in cam.location)} lens {cam.data.lens} "
          f"shift {cam.data.shift_x:.3f},{cam.data.shift_y:.3f} res {RES}")
    c0, r0 = pix(0.0, P.ENTABLATURE_Z0)
    c1, r1 = pix(0.0, P.ENTABLATURE_Z1)
    print(f"[probe] wall plane: entablature z {P.ENTABLATURE_Z0} -> row {r0:.1f}, z {P.ENTABLATURE_Z1} -> row {r1:.1f}; "
          f"scale {(r0 - r1) / (P.ENTABLATURE_Z1 - P.ENTABLATURE_Z0):.2f} px/m   col at d=0: {c0:.1f}")
    cd, rd = pix(1.0, P.ENTABLATURE_Z0)
    print(f"[probe] 1.00 m of outward projection lifts a point by {r0 - rd:.2f} px "
          f"(= {(r0 - rd) / ((r0 - r1) / (P.ENTABLATURE_Z1 - P.ENTABLATURE_Z0)):.3f} m of apparent height)")
    print(f"{'z':>7} {'d':>6} {'row':>8} {'col':>8}")
    for z in (P.ENTABLATURE_Z0, P.ENTABLATURE_Z0 + 1.4, P.ENTABLATURE_Z0 + 2.6, P.ENTABLATURE_Z0 + 3.2,
              P.ENTABLATURE_Z1, P.ATTIC_Z0 + P.ATTIC_BASE_MOULDING_H, P.ATTIC_Z1):
        for d in (0.0, 0.5, 1.0, 1.7):
            c, r = pix(d, z)
            print(f"{z:7.2f} {d:6.2f} {r:8.1f} {c:8.1f}")

if OUT:
    # exactly the preset QA renders the hero with, so the crop's absolute luminances are comparable with
    # renders/previews/qa/round05_01_lagoon_hero_cycles.png (the "before" of the QA-05-6 measurement)
    import light_presets
    light_presets.apply_final_cycles(scene, samples=SPP, time_limit=0.0)
    if BORDER:
        x0, y0, x1, y1 = BORDER
        scene.render.use_border = True
        scene.render.use_crop_to_border = False
        scene.render.border_min_x = x0 / RES[0]
        scene.render.border_max_x = x1 / RES[0]
        scene.render.border_min_y = 1.0 - y1 / RES[1]
        scene.render.border_max_y = 1.0 - y0 / RES[1]
        print(f"[probe] border {BORDER}")
    scene.render.filepath = OUT if os.path.isabs(OUT) else str(common.ROOT / OUT)
    scene.render.image_settings.file_format = "PNG"
    bpy.ops.render.render(write_still=True)
    print("[probe] wrote", scene.render.filepath)
