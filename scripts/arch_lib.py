"""Geometry helpers for the architecture builder (bmesh based, no live booleans).

Every builder returns a Blender object linked into the given collection, with:
  - origin at `origin` (world coords), scale (1,1,1), rotation 0 unless stated,
  - cube-projection UVs in metres (world space),
  - smooth shading with sharp edges marked by angle, an optional bevel modifier,
  - `part_type` custom property and a library material assigned by name.
"""
import bpy, bmesh, math, os, sys
from mathutils import Vector, Matrix
from mathutils.geometry import tessellate_polygon

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
import arch_params as P

SINK = 0.03          # stacked solids are sunk this much into the solid below (never coplanar faces)
SHARP_ANGLE = math.radians(32.0)


# ============================================================================= 2D helpers
def signed_area(poly):
    a = 0.0
    for i in range(len(poly)):
        x0, y0 = poly[i][:2]
        x1, y1 = poly[(i + 1) % len(poly)][:2]
        a += x0 * y1 - x1 * y0
    return a / 2.0


def ensure_ccw(poly):
    return list(poly) if signed_area(poly) > 0 else list(reversed(poly))


def rot2(v, deg):
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    return (v[0] * c - v[1] * s, v[0] * s + v[1] * c)


def add2(a, b):
    return (a[0] + b[0], a[1] + b[1])


def mul2(a, k):
    return (a[0] * k, a[1] * k)


def norm2(a):
    l = math.hypot(a[0], a[1]) or 1.0
    return (a[0] / l, a[1] / l)


def dot2(a, b):
    return a[0] * b[0] + a[1] * b[1]


def regular_polygon(r, n, phase_deg=0.0):
    return [(r * math.cos(math.radians(phase_deg) + 2 * math.pi * i / n),
             r * math.sin(math.radians(phase_deg) + 2 * math.pi * i / n)) for i in range(n)]


def octagon_world(apothem):
    """Rotunda octagon outline (world XY) with vertices at VERTEX_AZ0 + 45k, CCW."""
    rc = apothem / math.cos(math.radians(22.5))
    return ensure_ccw([P.az_to_xy(P.VERTEX_AZ0 + 45 * k, rc) for k in range(8)])


def rect(cx, cy, w, h):
    return [(cx - w / 2, cy - h / 2), (cx + w / 2, cy - h / 2), (cx + w / 2, cy + h / 2), (cx - w / 2, cy + h / 2)]


def offset_polygon(poly, d):
    """Offset a CCW polygon outward by d (mitred)."""
    n = len(poly)
    out = []
    for i in range(n):
        p0, p1, p2 = poly[i - 1], poly[i], poly[(i + 1) % n]
        e0 = norm2((p1[0] - p0[0], p1[1] - p0[1]))
        e1 = norm2((p2[0] - p1[0], p2[1] - p1[1]))
        n0 = (e0[1], -e0[0])
        n1 = (e1[1], -e1[0])
        den = 1.0 + dot2(n0, n1)
        if den < 0.05:
            m = n1
        else:
            m = ((n0[0] + n1[0]) / den, (n0[1] + n1[1]) / den)
        out.append((p1[0] + d * m[0], p1[1] + d * m[1]))
    return out


# ============================================================================= mesh finishing
def _finish(name, bm, coll, mat=None, part_type=None, origin=(0.0, 0.0, 0.0), smooth=True, bevel=True,
            bevel_width=None, uv=True, props=None):
    bm.normal_update()
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    if smooth:
        for f in bm.faces:
            f.smooth = True
        for e in bm.edges:
            if e.is_boundary:
                e.smooth = False
                continue
            try:
                ang = e.calc_face_angle()
            except ValueError:
                ang = 0.0
            e.smooth = ang < SHARP_ANGLE
    if origin != (0.0, 0.0, 0.0):
        bmesh.ops.translate(bm, verts=bm.verts, vec=(-origin[0], -origin[1], -origin[2]))
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.update()
    obj = bpy.data.objects.new(name, me)
    obj.location = origin
    coll.objects.link(obj)
    if uv:
        cube_project_uv(obj)
    if bevel:
        add_bevel(obj, bevel_width or P.BEVEL_WIDTH)
    if mat:
        common.assign_material(obj, common.load_material(mat))
    if part_type:
        obj["part_type"] = part_type
    obj["instance_seed"] = sum(ord(c) for c in name) % 997   # per-object variation seed for the materials agent
    if props:
        for k, v in props.items():
            obj[k] = v
    return obj


def add_bevel(obj, width=None, segments=None):
    b = obj.modifiers.new("bevel", "BEVEL")
    b.width = width or P.BEVEL_WIDTH
    b.segments = segments or P.BEVEL_SEGMENTS
    b.limit_method = "ANGLE"
    b.angle_limit = math.radians(40.0)
    b.miter_outer = "MITER_ARC"
    b.harden_normals = False
    # Phase 4 perf (2026-09-07): the bevelled objects carry no LOD suffix, so they sit in both the viewport (LOD1)
    # and the render (LOD0) set. Render-only keeps every arris the QA-02-3 edge-wear mask reads from while taking
    # 261 k triangles out of the viewport. Measured cost of the bevels in an Eevee render of architecture.blend:
    # cam01 6.0 s -> 6.8 s, cam05 7.1 s -> 9.0 s (1280x720, 16 TAA, warm) -- keep them in the render.
    b.show_viewport = False
    b.show_render = True
    return b


def cube_project_uv(obj, scale=1.0):
    """Box projection in world metres: each face is mapped by its dominant normal axis."""
    me = obj.data
    if not me.polygons:
        return
    uv = me.uv_layers.get("UVMap") or me.uv_layers.new(name="UVMap")
    mw = obj.matrix_world
    verts = [mw @ v.co for v in me.vertices]
    data = uv.data
    for poly in me.polygons:
        n = poly.normal
        ax, ay, az = abs(n.x), abs(n.y), abs(n.z)
        for li in poly.loop_indices:
            v = verts[me.loops[li].vertex_index]
            if az >= ax and az >= ay:
                u, w = v.x, v.y
            elif ax >= ay:
                u, w = v.y, v.z
            else:
                u, w = v.x, v.z
            data[li].uv = (u * scale, w * scale)


def instance(name, src_obj, location, rot_z=0.0, coll=None, part_type=None, props=None):
    """New object sharing src_obj's mesh (and materials), placed at location with a Z rotation (radians)."""
    o = bpy.data.objects.new(name, src_obj.data)
    o.location = location
    o.rotation_euler = (0.0, 0.0, rot_z)
    (coll or src_obj.users_collection[0]).objects.link(o)
    for m in src_obj.modifiers:
        mm = o.modifiers.new(m.name, m.type)
        for attr in ("width", "segments", "limit_method", "angle_limit", "miter_outer", "harden_normals"):
            if hasattr(m, attr):
                setattr(mm, attr, getattr(m, attr))
    for k in src_obj.keys():
        if not k.startswith("_"):
            o[k] = src_obj[k]
    o["instance_seed"] = sum(ord(c) for c in name) % 997
    if part_type:
        o["part_type"] = part_type
    if props:
        for k, v in props.items():
            o[k] = v
    return o


def tri_count(objs):
    total = 0
    for o in objs:
        if o.type != "MESH":
            continue
        for p in o.data.polygons:
            total += max(len(p.vertices) - 2, 1)
    return total


# ============================================================================= primitives
def prism(name, poly, z0, z1, coll, mat=None, part_type=None, origin=None, ngon=True, **kw):
    """Extrude a simple (hole-free) polygon from z0 to z1. Caps are n-gons (or tessellated if ngon=False)."""
    poly = ensure_ccw(poly)
    bm = bmesh.new()
    bot = [bm.verts.new((x, y, z0)) for x, y in poly]
    top = [bm.verts.new((x, y, z1)) for x, y in poly]
    n = len(poly)
    for i in range(n):
        bm.faces.new((bot[i], bot[(i + 1) % n], top[(i + 1) % n], top[i]))
    if ngon:
        bm.faces.new(list(reversed(bot)))
        bm.faces.new(top)
    else:
        tris = tessellate_polygon([[(x, y, 0.0) for x, y in poly]])
        for a, b, c in tris:
            bm.faces.new((bot[c], bot[b], bot[a]))
            bm.faces.new((top[a], top[b], top[c]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    if origin == "first":
        origin = (poly[0][0], poly[0][1], z0)
    elif origin is None:
        origin = (0.0, 0.0, z0)
    return _finish(name, bm, coll, mat, part_type, origin=origin, **kw)


def loft(name, rings, coll, mat=None, part_type=None, origin=(0.0, 0.0, 0.0), flip=False, closed=False, **kw):
    """Quad surface through a list of 3D point rows (open rows unless closed=True). flip inverts normals."""
    bm = bmesh.new()
    rows = [[bm.verts.new(tuple(p)) for p in ring] for ring in rings]
    n = len(rows[0])
    for a, b in zip(rows[:-1], rows[1:]):
        rng = range(n) if closed else range(n - 1)
        for i in rng:
            j = (i + 1) % n
            bm.faces.new((a[i], a[j], b[j], b[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    if flip:
        bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
    return _finish(name, bm, coll, mat, part_type, origin=origin, bevel=False, **kw)


def box(name, center, size, z0, z1, coll, rot_deg=0.0, mat=None, part_type=None, **kw):
    """Axis-aligned box (rotated by rot_deg about Z) centred at center (x,y), footprint size=(w,d)."""
    w, d = size
    corners = [(-w / 2, -d / 2), (w / 2, -d / 2), (w / 2, d / 2), (-w / 2, d / 2)]
    poly = [add2(center, rot2(c, rot_deg)) for c in corners]
    return prism(name, poly, z0, z1, coll, mat, part_type, origin=(center[0], center[1], z0), **kw)


def ring_prism(name, outer, inner, z0, z1, coll, mat=None, part_type=None, **kw):
    """Prism between two concentric polygons with the same vertex count (all quads)."""
    outer, inner = ensure_ccw(outer), ensure_ccw(inner)
    assert len(outer) == len(inner)
    n = len(outer)
    bm = bmesh.new()
    ob = [bm.verts.new((x, y, z0)) for x, y in outer]
    ot = [bm.verts.new((x, y, z1)) for x, y in outer]
    ib = [bm.verts.new((x, y, z0)) for x, y in inner]
    it = [bm.verts.new((x, y, z1)) for x, y in inner]
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((ob[i], ob[j], ot[j], ot[i]))
        bm.faces.new((ib[j], ib[i], it[i], it[j]))
        bm.faces.new((ot[i], ot[j], it[j], it[i]))
        bm.faces.new((ob[j], ob[i], ib[i], ib[j]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return _finish(name, bm, coll, mat, part_type, origin=(0.0, 0.0, z0), **kw)


def plate(name, outline, holes, thickness, origin3d, xaxis, yaxis, coll, mat=None, part_type=None,
          step=0.0, step_depth=0.0, **kw):
    """A slab built in a local 2D frame: outline/holes are 2D polygons in (xaxis, yaxis) coordinates;
    the plate's front face is at the frame origin plane, the back face `thickness` behind (along -normal,
    normal = xaxis x yaxis). Holes go right through. Caps are tessellated, sides are quads.

    `step` > 0 gives every hole a two-register reveal (QA-03-8): the last `step_depth` of the thickness, at the
    BACK face, is widened by `step` all round, so a coffer shows a wide shallow outer register stepping in to the
    deep box. That break is what catches a grazing light and puts a shadow line round every coffer; a single
    straight reveal seen nearly face-on shows nothing."""
    X, Y = Vector(xaxis).normalized(), Vector(yaxis).normalized()
    N = X.cross(Y).normalized()
    O = Vector(origin3d)
    outline = ensure_ccw(outline)
    holes_ccw = [ensure_ccw(h) for h in holes]
    stepped = step > 1e-6 and 0.0 < step_depth < thickness
    holes_back = [offset_polygon(h, step) for h in holes_ccw] if stepped else holes_ccw
    holes = [list(reversed(h)) for h in holes_ccw]
    holes_b = [list(reversed(h)) for h in holes_back]
    bm = bmesh.new()
    front, back = [], []

    def ring(loop, depth):
        return [bm.verts.new(O + X * x + Y * y - N * depth) for x, y in loop]

    # outline walls (never stepped)
    f = ring(outline, 0.0)
    b = ring(outline, thickness)
    front.append(f)
    back.append(b)
    for i in range(len(outline)):
        j = (i + 1) % len(outline)
        bm.faces.new((f[i], f[j], b[j], b[i]))
    # hole walls
    for hn, hb in zip(holes, holes_b):
        n = len(hn)
        f = ring(hn, 0.0)
        front.append(f)
        if stepped:
            m0 = ring(hn, thickness - step_depth)
            m1 = ring(hb, thickness - step_depth)
            b = ring(hb, thickness)
            for i in range(n):
                j = (i + 1) % n
                bm.faces.new((f[i], f[j], m0[j], m0[i]))       # deep box wall
                bm.faces.new((m0[i], m0[j], m1[j], m1[i]))     # the ledge
                bm.faces.new((m1[i], m1[j], b[j], b[i]))       # outer register wall
        else:
            b = ring(hn, thickness)
            for i in range(n):
                j = (i + 1) % n
                bm.faces.new((f[i], f[j], b[j], b[i]))
        back.append(b)
    for loops, verts in ((( [outline] + holes ), front), (([outline] + holes_b), back)):
        flat = [[(x, y, 0.0) for x, y in loop] for loop in loops]
        allv = [v for lp in verts for v in lp]
        for a, b_, c in tessellate_polygon(flat):
            try:
                bm.faces.new((allv[a], allv[b_], allv[c]) if verts is front else (allv[c], allv[b_], allv[a]))
            except ValueError:
                pass
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return _finish(name, bm, coll, mat, part_type, origin=tuple(O), **kw)


def grid_frame(name, xs, ys, thickness, coll, mat=None, part_type=None, hole=None, **kw):
    """All-quad rib network: a flat slab in the XY plane (front at z=0, back at z=-thickness) divided by the breakpoints
    xs/ys into cells; cell (i, j) is a through-hole when hole(i, j) is True (default: odd i and odd j)."""
    hole = hole or (lambda i, j: i % 2 == 1 and j % 2 == 1)
    nx, ny = len(xs) - 1, len(ys) - 1
    bm = bmesh.new()
    front = [[bm.verts.new((x, y, 0.0)) for y in ys] for x in xs]
    back = [[bm.verts.new((x, y, -thickness)) for y in ys] for x in xs]
    for i in range(nx):
        for j in range(ny):
            if hole(i, j):
                # side walls of the hole (inward facing)
                bm.faces.new((front[i][j], front[i + 1][j], back[i + 1][j], back[i][j]))
                bm.faces.new((front[i + 1][j], front[i + 1][j + 1], back[i + 1][j + 1], back[i + 1][j]))
                bm.faces.new((front[i + 1][j + 1], front[i][j + 1], back[i][j + 1], back[i + 1][j + 1]))
                bm.faces.new((front[i][j + 1], front[i][j], back[i][j], back[i][j + 1]))
            else:
                bm.faces.new((front[i][j], front[i + 1][j], front[i + 1][j + 1], front[i][j + 1]))
                bm.faces.new((back[i][j + 1], back[i + 1][j + 1], back[i + 1][j], back[i][j]))
    # outer side walls
    for i in range(nx):
        bm.faces.new((front[i + 1][0], front[i][0], back[i][0], back[i + 1][0]))
        bm.faces.new((front[i][ny], front[i + 1][ny], back[i + 1][ny], back[i][ny]))
    for j in range(ny):
        bm.faces.new((front[0][j], front[0][j + 1], back[0][j + 1], back[0][j]))
        bm.faces.new((front[nx][j + 1], front[nx][j], back[nx][j], back[nx][j + 1]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return _finish(name, bm, coll, mat, part_type, origin=(0.0, 0.0, 0.0), **kw)


def lathe(name, profile, coll, segments=64, mat=None, part_type=None, origin=(0.0, 0.0, 0.0), center=(0.0, 0.0),
          close_top=False, close_bottom=False, phase_deg=0.0, flip=False, **kw):
    """Revolve a (r, z) polyline about the vertical axis through `center`. Points with r=0 become poles.
    flip=True inverts the normals (for surfaces seen from inside, e.g. the ceiling)."""
    bm = bmesh.new()
    rings = []
    for r, z in profile:
        if r < 1e-6:
            rings.append(bm.verts.new((center[0], center[1], z)))
        else:
            rings.append([bm.verts.new((center[0] + r * math.cos(math.radians(phase_deg) + 2 * math.pi * i / segments),
                                        center[1] + r * math.sin(math.radians(phase_deg) + 2 * math.pi * i / segments), z))
                          for i in range(segments)])
    for a, b in zip(rings[:-1], rings[1:]):
        for i in range(segments):
            j = (i + 1) % segments
            if isinstance(a, list) and isinstance(b, list):
                bm.faces.new((a[i], a[j], b[j], b[i]))
            elif isinstance(a, list):
                bm.faces.new((a[i], a[j], b))
            elif isinstance(b, list):
                bm.faces.new((a, b[j], b[i]))
    if close_bottom and isinstance(rings[0], list):
        bm.faces.new(list(reversed(rings[0])))
    if close_top and isinstance(rings[-1], list):
        bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    if flip:
        bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
    return _finish(name, bm, coll, mat, part_type, origin=origin, **kw)


def sweep_closed(name, path, profile, coll, mat=None, part_type=None, origin=(0.0, 0.0, 0.0), z0=0.0, **kw):
    """Sweep a 2D profile [(d, z)] (d = outward offset from the path line, z relative to z0) along a closed
    CCW plan polygon with mitred corners. The profile polyline is open: its first and last points normally lie
    on the path (d=0) so the band closes against a wall; pass a closed profile (first == last) for a free beam."""
    path = ensure_ccw(path)
    n = len(path)
    mit = []
    for i in range(n):
        p0, p1, p2 = path[i - 1], path[i], path[(i + 1) % n]
        e0 = norm2((p1[0] - p0[0], p1[1] - p0[1]))
        e1 = norm2((p2[0] - p1[0], p2[1] - p1[1]))
        n0 = (e0[1], -e0[0])
        n1 = (e1[1], -e1[0])
        den = 1.0 + dot2(n0, n1)
        if den < 0.02:
            m = n1
        else:
            m = ((n0[0] + n1[0]) / den, (n0[1] + n1[1]) / den)
        mit.append(m)
    bm = bmesh.new()
    rows = []
    for i in range(n):
        px, py = path[i]
        mx, my = mit[i]
        rows.append([bm.verts.new((px + d * mx, py + d * my, z0 + z)) for d, z in profile])
    m = len(profile)
    for i in range(n):
        j = (i + 1) % n
        for k in range(m - 1):
            bm.faces.new((rows[i][k], rows[j][k], rows[j][k + 1], rows[i][k + 1]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return _finish(name, bm, coll, mat, part_type, origin=origin, **kw)


def sweep_open(name, path3d, normals, binormals, profile, coll, mat=None, part_type=None, origin=(0.0, 0.0, 0.0),
               cap=True, **kw):
    """General open sweep: point = path[i] + a*normals[i] + b*binormals[i] for each (a, b) in profile.
    normals/binormals are per-path-point unit vectors (already mitred if needed). Caps are n-gons."""
    bm = bmesh.new()
    rows = []
    for p, nrm, bnr in zip(path3d, normals, binormals):
        p, nrm, bnr = Vector(p), Vector(nrm), Vector(bnr)
        rows.append([bm.verts.new(p + nrm * a + bnr * b) for a, b in profile])
    m = len(profile)
    closed_profile = (abs(profile[0][0] - profile[-1][0]) < 1e-9 and abs(profile[0][1] - profile[-1][1]) < 1e-9)
    for i in range(len(rows) - 1):
        for k in range(m - 1):
            bm.faces.new((rows[i][k], rows[i + 1][k], rows[i + 1][k + 1], rows[i][k + 1]))
    if cap:
        first = rows[0][:-1] if closed_profile else rows[0]
        last = rows[-1][:-1] if closed_profile else rows[-1]
        if len(first) >= 3:
            try:
                bm.faces.new(first)
                bm.faces.new(list(reversed(last)))
            except ValueError:
                pass
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return _finish(name, bm, coll, mat, part_type, origin=origin, **kw)


def arc_path(center, radius, a0_deg, a1_deg, n):
    pts = []
    for i in range(n + 1):
        a = math.radians(a0_deg + (a1_deg - a0_deg) * i / n)
        pts.append((center[0] + radius * math.cos(a), center[1] + radius * math.sin(a)))
    return pts


def plan_path_to_3d(path2d, z, outward_sign=1.0):
    """For sweep_open along a plan polyline: returns (path3d, normals (horizontal, mitred), binormals (+Z))."""
    n = len(path2d)
    pts3, nrms, bins = [], [], []
    for i in range(n):
        p = path2d[i]
        if i == 0:
            e = norm2((path2d[1][0] - p[0], path2d[1][1] - p[1]))
            m = (e[1], -e[0])
        elif i == n - 1:
            e = norm2((p[0] - path2d[i - 1][0], p[1] - path2d[i - 1][1]))
            m = (e[1], -e[0])
        else:
            e0 = norm2((p[0] - path2d[i - 1][0], p[1] - path2d[i - 1][1]))
            e1 = norm2((path2d[i + 1][0] - p[0], path2d[i + 1][1] - p[1]))
            n0, n1 = (e0[1], -e0[0]), (e1[1], -e1[0])
            den = 1.0 + dot2(n0, n1)
            m = n1 if den < 0.02 else ((n0[0] + n1[0]) / den, (n0[1] + n1[1]) / den)
        pts3.append((p[0], p[1], z))
        nrms.append((m[0] * outward_sign, m[1] * outward_sign, 0.0))
        bins.append((0.0, 0.0, 1.0))
    return pts3, nrms, bins


# ============================================================================= columns
def entasis_radius(t, r_b, r_t):
    """Shaft radius at parameter t (0 bottom .. 1 top): straight for the lower third, then a smooth taper."""
    if t <= 1 / 3:
        return r_b
    s = (t - 1 / 3) / (2 / 3)
    return r_b - (r_b - r_t) * (s ** 1.6)


def flute_section(flutes=None, k_arc=2, fillet_fraction=None, arc_half_deg=None):
    """Cross-section of a fluted shaft as [(angle, depth_factor)] for one full turn, plus the radial depth
    fraction that turns depth_factor into a radius scale.

    The hollow is a true segmental circular arc of half-angle `arc_half_deg`, sampled at EQUAL ARC ANGLES, so the
    samples crowd towards the arris and the flute wall is steep where it meets the fillet. depth_factor is 0 on the
    fillet and 1 at the bottom of the hollow; the caller uses r * (1 - depth * factor)."""
    flutes = flutes or P.FLUTES
    ff = P.FILLET_FRACTION if fillet_fraction is None else fillet_fraction
    th = math.radians(P.FLUTE_ARC_HALF_DEG if arc_half_deg is None else arc_half_deg)
    pitch = 2 * math.pi / flutes
    fillet_w = pitch * ff / (1 + ff)
    flute_w = pitch - fillet_w
    sec = []
    for f in range(flutes):
        a0 = f * pitch
        sec.append((a0, 0.0))
        sec.append((a0 + fillet_w, 0.0))
        for k in range(1, k_arc + 1):
            phi = -th + 2 * th * k / (k_arc + 1)
            u = (math.sin(phi) + math.sin(th)) / (2 * math.sin(th))
            sec.append((a0 + fillet_w + u * flute_w, (math.cos(phi) - math.cos(th)) / (1 - math.cos(th))))
    # depth as a fraction of the radius: (arc depth / arc width) * flute width in radians
    depth = (1 - math.cos(th)) / (2 * math.sin(th)) * flute_w
    return sec, depth


def shaft_rings(height, lod, apophyge, fade):
    """Ring heights up a shaft, graded so the flute run-outs at both ends get rings and the plain middle does not."""
    if lod == 2:
        return [i * height / 6 for i in range(7)]
    foot = apophyge + fade
    if lod == 0:
        zs = [0.0, 0.05, 0.11, 0.18, 0.27, 0.38, foot]
        top = [height - 0.34, height - 0.24, height - 0.16, height - 0.09, height - 0.04, height]
        n_mid = 18
    else:
        zs = [0.0, apophyge, foot]
        top = [height - 0.06, height]
        n_mid = 6
    z0, z1 = foot, top[0]
    zs += [z0 + (z1 - z0) * i / n_mid for i in range(1, n_mid)]
    zs += top
    return sorted(set(round(z, 4) for z in zs if 0.0 <= z <= height))


def column_shaft(name, r_b, r_t, height, coll, lod=1, flutes=P.FLUTES, mat=None, part_type="column",
                 origin=(0.0, 0.0, 0.0), fade=0.35, apophyge=0.18, **kw):
    """Fluted (LOD0/1) or plain (LOD2) shaft with entasis, origin at the bottom centre. The flutes fade out
    (rounded ends) over `fade` metres at both ends; the bottom `apophyge` flares to the base."""
    k_arc = {0: 8, 1: 4}.get(lod, 0)
    if k_arc == 0:
        section, depth = [(2 * math.pi * i / 32, 0.0) for i in range(32)], 0.0
    else:
        section, depth = flute_section(flutes, k_arc)
    zs = shaft_rings(height, lod, apophyge, fade)
    bm = bmesh.new()
    rings = []
    for z in zs:
        t = z / height
        r = entasis_radius(t, r_b, r_t)
        if z < apophyge:
            r += 0.06 * (1 - z / apophyge) ** 2 * r_b
        m = 1.0
        if depth > 0:
            e0 = min(1.0, max(0.0, (z - apophyge) / fade))
            e1 = min(1.0, max(0.0, (height - z - 0.05) / fade))
            m = (e0 * e0 * (3 - 2 * e0)) * (e1 * e1 * (3 - 2 * e1))
        ring = []
        for ang, fac in section:
            rr = r * (1 - depth * fac * m)
            ring.append(bm.verts.new((origin[0] + rr * math.cos(ang), origin[1] + rr * math.sin(ang), origin[2] + z)))
        rings.append(ring)
    n = len(section)
    for a, b in zip(rings[:-1], rings[1:]):
        for i in range(n):
            j = (i + 1) % n
            bm.faces.new((a[i], a[j], b[j], b[i]))
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return _finish(name, bm, coll, mat, part_type, origin=origin, bevel=False, **kw)


def attic_base_profile(r, h=1.0, plinth=None, seg=6):
    """(r, z) polyline of a real Attic base above a square plinth, for a shaft of radius `r`; z 0 = bottom of
    the plinth, z h = the shaft springing.

    QA-03-9: the old profile was one smooth flare with a 6 cm scotia and an upper torus that overshot `h` (so the
    lathe folded on itself) and it read as a smooth bell. This one lays the classical courses out from
    P.BASE_COURSES -- lower torus, fillet, scotia, fillet, upper torus, apophyge -- with sharp fillets between
    them, and caps the tori so nothing overhangs the square plinth."""
    plinth_h = P.BASE_PLINTH_FRACTION * h
    H = h - plinth_h
    r_cap = (plinth / 2 - 0.05) if plinth else r * P.BASE_LOWER_TORUS_R
    R_lt = min(r * P.BASE_LOWER_TORUS_R, r_cap)          # lower torus, widest element
    R_ut = r + P.BASE_UPPER_TORUS_F * (R_lt - r)         # upper torus, 80 % of that projection
    R_sc = r * P.BASE_SCOTIA_R                           # scotia throat, just inside the shaft
    _, f_lt = P.BASE_COURSES[0]
    _, f_f1 = P.BASE_COURSES[1]
    _, f_sc = P.BASE_COURSES[2]
    _, f_f2 = P.BASE_COURSES[3]
    _, f_ut = P.BASE_COURSES[4]
    _, f_ap = P.BASE_COURSES[5]
    pts = []
    z = plinth_h

    def torus(R, dz):
        nonlocal z
        tr, base = dz / 2, R - dz / 2
        for i in range(seg + 1):
            a = -math.pi / 2 + math.pi * i / seg
            pts.append((base + tr * math.cos(a), z + tr * (1 + math.sin(a))))
        z += dz

    def fillet(R, dz):
        nonlocal z
        pts.append((R, z))
        pts.append((R, z + dz))
        z += dz

    R_f1 = R_sc + 0.30 * (R_lt - R_sc)
    R_f2 = R_sc + 0.30 * (R_ut - R_sc)
    pts.append((R_lt - f_lt * H / 2, plinth_h))          # the torus sits on the plinth top
    torus(R_lt, f_lt * H)
    fillet(R_f1, f_f1 * H)
    dz = f_sc * H                                        # scotia: concave arc dipping to the throat
    for i in range(1, seg + 1):
        u = i / seg
        edge = R_f1 + (R_f2 - R_f1) * u
        pts.append((edge - (edge - R_sc) * math.sin(math.pi * u) ** 0.7, z + dz * u))
    z += dz
    fillet(R_f2, f_f2 * H)
    torus(R_ut, f_ut * H)
    dz = f_ap * H                                        # apophyge: flare in to the shaft
    for i in range(1, seg + 1):
        u = i / seg
        pts.append((R_ut - f_ut * H / 2 - (R_ut - f_ut * H / 2 - r) * (u ** 0.55), z + dz * u))
    return pts


def column_base(name, r, coll, height=1.0, plinth=None, segments=48, mat=None, origin=(0.0, 0.0, 0.0), **kw):
    """Square plinth + Attic base torus set, origin at the plinth bottom centre."""
    plinth = plinth or 2.3 * r
    plinth_h = P.BASE_PLINTH_FRACTION * height
    objs = []
    objs.append(box(name + "_plinth", (origin[0], origin[1]), (plinth, plinth), origin[2], origin[2] + plinth_h, coll,
                    mat=mat, part_type="column", **kw))
    prof = attic_base_profile(r, height, plinth)
    prof = [(rr, origin[2] + z) for rr, z in prof]
    prof.insert(0, (0.0, origin[2] + plinth_h - SINK))
    objs.append(lathe(name + "_torus", prof, coll, segments=segments, mat=mat, part_type="column", origin=origin,
                      center=(origin[0], origin[1]), close_top=True, bevel=False, **kw))
    return objs


def placeholder_capital(name, r_top, height, coll, mat=None, origin=(0.0, 0.0, 0.0), segments=32, **kw):
    """Crude Corinthian massing for previews only (bell + abacus). Lives in ARCH_placeholders."""
    bell = [(0.0, origin[2] - SINK), (r_top * 0.98, origin[2] - SINK), (r_top * 1.05, origin[2] + 0.12 * height),
            (r_top * 1.02, origin[2] + 0.25 * height), (r_top * 1.15, origin[2] + 0.45 * height),
            (r_top * 1.30, origin[2] + 0.62 * height), (r_top * 1.42, origin[2] + 0.78 * height),
            (r_top * 1.36, origin[2] + 0.80 * height), (0.0, origin[2] + 0.80 * height)]
    o1 = lathe(name + "_bell", bell, coll, segments=segments, mat=mat, part_type="capital", origin=origin,
               center=(origin[0], origin[1]), bevel=False, **kw)
    ab = 2 * r_top * 1.45
    o2 = box(name + "_abacus", (origin[0], origin[1]), (ab, ab), origin[2] + 0.78 * height, origin[2] + height, coll,
             mat=mat, part_type="capital", **kw)
    return [o1, o2]


# ============================================================================= sockets
def add_socket(name, location, outward, coll, orn_type, size_hint, variant_seed=0, extra=None, size=0.6):
    """Empty with local +Z up and local +Y = outward (horizontal direction)."""
    dx, dy = norm2((outward[0], outward[1]))
    yaw = math.atan2(-dx, dy)
    e = bpy.data.objects.new(name, None)
    e.empty_display_type = "ARROWS"
    e.empty_display_size = size
    e.location = location
    e.rotation_euler = (0.0, 0.0, yaw)
    e["orn_type"] = orn_type
    e["size_hint"] = float(size_hint)
    e["variant_seed"] = int(variant_seed)
    if extra:
        for k, v in extra.items():
            e[k] = v
    coll.objects.link(e)
    return e


class SocketCounter:
    def __init__(self, coll):
        self.coll = coll
        self.counts = {}

    def add(self, orn_type, location, outward, size_hint, extra=None, size=0.6):
        i = self.counts.get(orn_type, 0)
        self.counts[orn_type] = i + 1
        return add_socket(f"SOCKET_{orn_type}_{i:03d}", location, outward, self.coll, orn_type, size_hint,
                          variant_seed=i * 7919 % 1000, extra=extra, size=size)
