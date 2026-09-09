"""Ornament & sculpture helpers (ORN agent). Import from scripts/orn_build.py / orn_preview.py.

Everything here builds meshes headless with bmesh / evaluated depsgraphs (no operators that need a 3D view).
Frame convention for every asset (docs/sockets.md): origin at the bottom-centre of the footprint, +Z up, +Y outward
(toward the viewer), metres, scale applied.

Main entry points
    orn_collection(sub)              -> sub-collection ORN/ORN_<sub> (created)
    rebuild_type(sub)                -> wiped sub-collection
    revolve / surface / tube_fn / loft_rings / box / skin_figure / acanthus_leaf / volute
    union_blob(objs, ...)            -> voxel-remeshed, smoothed single mesh (sculpture look)
    decimate / displace_noise / apply_all / join / shade_smooth / origin_bottom_centre
    finalize_asset(hi, type, variant, budgets, bake)  -> LOD0/1/2 objects + baked maps + props + material
"""
import bpy, bmesh, math, random, os, sys, time
from pathlib import Path
from mathutils import Vector, Matrix, Euler, noise

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common

ORN_ROOT = "ORN"
TEX_DIR = common.ASSETS / "textures" / "orn"
MAT_NAME = "MAT_ornament_concrete"
TAU = math.tau

# LOD triangle budgets per type (docs/sockets.md): (LOD0, LOD1, LOD2)
BUDGETS = {
    "default": (80000, 18000, 1800),
    # round 4: rotunda 100k -> 64k (16 instances, -0.6 M tris in the master); inner/colonnade 80k -> 48k, matching
    # the in-place trim the round-3 pass applied to capital_colonnade (114 instances).
    "capital_rotunda": (64000, 16000, 2000),
    "capital_inner": (48000, 12000, 1500),
    "capital_colonnade": (48000, 12000, 1500),
    "maiden": (100000, 20000, 2000),
    "attic_figure": (120000, 20000, 2000),
    "winged_figure": (100000, 20000, 2000),
    "attic_panel": (150000, 24000, 2400),
    "urn": (60000, 12000, 1200),
    "keystone": (50000, 8000, 800),
    "finial": (20000, 4000, 400),
    "rosette_ceiling": (26000, 5000, 500),   # round 4: modelled petals instead of a lathe wobble
    "moulding": (30000, 6000, 600),
    "corner_scroll": (40000, 8000, 800),
    # round 5: full-run rinceau panels for the 24 rotunda ressaut frieze faces. 1523 tris/m at LOD1 (the greek_key
    # moulding runs 6000 tris/m, but that band is at eye level on the rostra; this one is 12.5 px tall on the hero).
    "frieze_rinceau": (48000, 9000, 900),
    "frieze_rinceau_return": (24000, 4500, 450),
}


# ----------------------------------------------------------------------------- collections
def orn_collection(sub=None):
    root = bpy.data.collections.get(ORN_ROOT)
    if root is None:
        root = bpy.data.collections.new(ORN_ROOT)
    if root.name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(root)
    if sub is None:
        return root
    name = f"ORN_{sub}"
    c = bpy.data.collections.get(name)
    if c is None:
        c = bpy.data.collections.new(name)
    if c.name not in root.children:
        root.children.link(c)
    return c


def rebuild_type(sub):
    """Idempotent: wipe ORN_<sub> (objects + orphan data) and return it fresh."""
    root = orn_collection()
    name = f"ORN_{sub}"
    common.clear_collection(name, remove_collection=True)
    c = bpy.data.collections.new(name)
    root.children.link(c)
    return c


def work_collection():
    """Scratch collection for intermediate geometry; wiped by the builder at the end."""
    c = bpy.data.collections.get("ORN_work")
    if c is None:
        c = bpy.data.collections.new("ORN_work")
        bpy.context.scene.collection.children.link(c)
    return c


def remove_object(obj):
    data = obj.data
    bpy.data.objects.remove(obj, do_unlink=True)
    if data is not None and data.users == 0:
        try:
            bpy.data.meshes.remove(data)
        except Exception:
            pass


# ----------------------------------------------------------------------------- basic mesh creation
def mesh_object(name, verts, faces, coll=None, edges=(), smooth=True):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], list(edges), [tuple(f) for f in faces])
    me.validate(verbose=False)
    me.update()
    if smooth:
        me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    obj = bpy.data.objects.new(name, me)
    (coll or work_collection()).objects.link(obj)
    return obj


def surface(name, fn, nu, nv, coll=None, wrap_u=False, wrap_v=False, smooth=True, cap_v0=False, cap_v1=False):
    """Parametric quad surface. fn(u, v) -> (x, y, z) with u, v in [0, 1]. nu x nv quads."""
    verts = []
    cu = nu if wrap_u else nu + 1
    cv = nv if wrap_v else nv + 1
    for j in range(cv):
        v = j / nv
        for i in range(cu):
            u = i / nu
            verts.append(fn(u, v))
    faces = []
    def idx(i, j):
        return (j % cv) * cu + (i % cu)
    for j in range(nv if not wrap_v else nv):
        if not wrap_v and j >= nv:
            break
        for i in range(nu):
            a, b, c, d = idx(i, j), idx(i + 1, j), idx(i + 1, j + 1), idx(i, j + 1)
            if len({a, b, c, d}) == 4:
                faces.append((a, b, c, d))
    if cap_v0:
        faces.append(tuple(idx(i, 0) for i in range(cu))[::-1] if wrap_u else tuple(idx(i, 0) for i in range(cu))[::-1])
    if cap_v1:
        faces.append(tuple(idx(i, cv - 1) for i in range(cu)))
    return mesh_object(name, verts, faces, coll, smooth=smooth)


def revolve(name, profile, segments=48, coll=None, scale_fn=None, cap_bottom=True, cap_top=True, smooth=True, z_offset=0.0):
    """Lathe a (r, z) profile around +Z. profile: list of (r, z) from bottom to top.
    scale_fn(theta, t) -> radial multiplier (t = 0..1 along the profile) for gadroons / fluting / squarish plans."""
    n = len(profile)
    def fn(u, v):
        th = u * TAU
        k = v * (n - 1)
        i = min(int(k), n - 2)
        f = k - i
        r = profile[i][0] * (1 - f) + profile[i + 1][0] * f
        z = profile[i][1] * (1 - f) + profile[i + 1][1] * f
        if scale_fn:
            r *= scale_fn(th, v)
        return (r * math.cos(th), r * math.sin(th), z + z_offset)
    obj = surface(name, fn, segments, (n - 1) * 1, coll, wrap_u=True, smooth=smooth)
    # merge degenerate pole rings and cap
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    if cap_bottom or cap_top:
        bm.edges.ensure_lookup_table()
        boundary = [e for e in bm.edges if e.is_boundary]
        if boundary:
            bmesh.ops.holes_fill(bm, edges=boundary, sides=0)
            if not cap_bottom or not cap_top:
                # remove unwanted cap by z
                zs = sorted(v.co.z for v in bm.verts)
                zmin, zmax = zs[0], zs[-1]
                for f in list(bm.faces):
                    c = f.calc_center_median()
                    if len(f.verts) > 4:
                        if (not cap_bottom and abs(c.z - zmin) < 1e-4) or (not cap_top and abs(c.z - zmax) < 1e-4):
                            bm.faces.remove(f)
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    if smooth:
        obj.data.polygons.foreach_set("use_smooth", [True] * len(obj.data.polygons))
    return obj


def resample_profile(profile, n):
    """Resample an (r, z) polyline to n evenly spaced points (by arc length) so revolve() rings are even."""
    pts = [Vector((r, z)) for r, z in profile]
    seg = [(pts[i + 1] - pts[i]).length for i in range(len(pts) - 1)]
    total = sum(seg)
    out = []
    for k in range(n):
        d = total * k / (n - 1)
        acc = 0.0
        for i, s in enumerate(seg):
            if acc + s >= d or i == len(seg) - 1:
                f = 0.0 if s == 0 else (d - acc) / s
                p = pts[i].lerp(pts[i + 1], min(max(f, 0.0), 1.0))
                out.append((p.x, p.y))
                break
            acc += s
    return out


def smooth_profile(profile, iterations=2, keep_ends=True):
    p = [Vector(x) for x in profile]
    for _ in range(iterations):
        q = list(p)
        for i in range(1, len(p) - 1):
            q[i] = (p[i - 1] + p[i] * 2 + p[i + 1]) / 4.0
        p = q
    return [(v.x, v.y) for v in p]


def loft_rings(name, rings, coll=None, cap_bottom=True, cap_top=True, smooth=True):
    """rings: list of lists of Vector (same count each), bottom to top. Quads between consecutive rings."""
    n = len(rings[0])
    verts = [tuple(v) for ring in rings for v in ring]
    faces = []
    for j in range(len(rings) - 1):
        for i in range(n):
            a = j * n + i
            b = j * n + (i + 1) % n
            c = (j + 1) * n + (i + 1) % n
            d = (j + 1) * n + i
            faces.append((a, b, c, d))
    if cap_bottom:
        faces.append(tuple(range(n))[::-1])
    if cap_top:
        base = (len(rings) - 1) * n
        faces.append(tuple(base + i for i in range(n)))
    return mesh_object(name, verts, faces, coll, smooth=smooth)


def box(name, size, coll=None, location=(0, 0, 0), bevel=0.0, segments=2):
    sx, sy, sz = size
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=(sx, sy, sz), verts=bm.verts)
    bmesh.ops.translate(bm, vec=location, verts=bm.verts)
    if bevel > 0:
        bmesh.ops.bevel(bm, geom=bm.verts[:] + bm.edges[:], offset=bevel, segments=segments, profile=0.7, affect="EDGES")
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(name, me)
    (coll or work_collection()).objects.link(obj)
    if bevel > 0:
        me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    return obj


def sphere(name, radius, coll=None, location=(0, 0, 0), scale=(1, 1, 1), segments=24, rings=16):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=segments, v_segments=rings, radius=radius)
    bmesh.ops.scale(bm, vec=scale, verts=bm.verts)
    bmesh.ops.translate(bm, vec=location, verts=bm.verts)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    obj = bpy.data.objects.new(name, me)
    (coll or work_collection()).objects.link(obj)
    return obj


# ----------------------------------------------------------------------------- sweeps
def frames_along(path):
    """Parallel-transport frames along a polyline. Returns list of (point, tangent, normal, binormal)."""
    pts = [Vector(p) for p in path]
    n = len(pts)
    tangents = []
    for i in range(n):
        if i == 0:
            t = pts[1] - pts[0]
        elif i == n - 1:
            t = pts[-1] - pts[-2]
        else:
            t = pts[i + 1] - pts[i - 1]
        tangents.append(t.normalized() if t.length > 1e-9 else Vector((0, 0, 1)))
    # initial normal: something perpendicular to t0
    t0 = tangents[0]
    ref = Vector((0, 0, 1)) if abs(t0.z) < 0.9 else Vector((1, 0, 0))
    nrm = (ref - t0 * ref.dot(t0)).normalized()
    out = []
    for i in range(n):
        t = tangents[i]
        if i > 0:
            # transport previous normal
            nrm = (nrm - t * nrm.dot(t))
            if nrm.length < 1e-6:
                ref = Vector((0, 0, 1)) if abs(t.z) < 0.9 else Vector((1, 0, 0))
                nrm = (ref - t * ref.dot(t))
            nrm.normalize()
        b = t.cross(nrm).normalized()
        out.append((pts[i], t, nrm.copy(), b))
    return out


def tube(name, path, radius_fn, coll=None, segments=12, section_fn=None, cap=True, smooth=True):
    """Sweep a section along a polyline. radius_fn(t)->(a, b) ellipse semi-axes (or float);
    section_fn(theta, t)->(x, y) in the frame (overrides the ellipse)."""
    frames = frames_along(path)
    nv = len(frames) - 1
    def fn(u, v):
        k = v * nv
        i = min(int(round(k)), nv)
        p, t, n, b = frames[i]
        th = u * TAU
        if section_fn:
            x, y = section_fn(th, v)
        else:
            r = radius_fn(v)
            a, bb = (r, r) if not isinstance(r, (tuple, list)) else r
            x, y = a * math.cos(th), bb * math.sin(th)
        return tuple(p + n * x + b * y)
    obj = surface(name, fn, segments, nv, coll, wrap_u=True, smooth=smooth, cap_v0=cap, cap_v1=cap)
    return obj


def bezier(p0, p1, p2, p3, n):
    p0, p1, p2, p3 = (Vector(p) for p in (p0, p1, p2, p3))
    out = []
    for i in range(n + 1):
        t = i / n
        a = (1 - t) ** 3
        b = 3 * (1 - t) ** 2 * t
        c = 3 * (1 - t) * t * t
        d = t ** 3
        out.append(p0 * a + p1 * b + p2 * c + p3 * d)
    return out


# ----------------------------------------------------------------------------- ornament primitives
def acanthus_leaf(name, length=1.0, width=0.6, curl=0.55, droop=0.35, ribs=7, rib_amp=0.03, bulge=0.06,
                  thickness=0.035, lobes=4, lobe_depth=0.10, nu=16, nv=24, coll=None, seed=0, base_width=0.35,
                  spine=None, mid_dip=0.0):
    """One 'shell' acanthus leaf as at the Palace: broad fan with radial ribs, the tip curling outward and down.
    Local frame: base at origin, grows along +Z, bends outward toward +Y (outward = away from the bell).
    `spine`: optional explicit centreline as a list of (y, z) or (x, y, z); overrides curl/droop and sets nv.
      Use it to make the leaf hug a flared bell and then curl its tip outward and DOWN (round 4, QA-03-15) - the
      down-turned tip is what gives a sky-lit-only undercut and therefore a dark recess in raking sun.
    `mid_dip`: extra cupping (metres) subtracted from the leaf centre at mid height, so the two halves of the leaf
      read as separate lit lobes with a shadowed spine between them.
    Returns a solidified, subdivided mesh object."""
    rng = random.Random(seed)
    if spine is not None:
        centre = [Vector((0.0, p[0], p[1])) if len(p) == 2 else Vector(p) for p in spine]
        nv = len(centre) - 1
    else:
        # centreline: cubic bezier in the (y outward, z up) plane
        p0 = (0.0, 0.0, 0.0)
        p1 = (0.0, 0.04 * length, 0.50 * length)
        p2 = (0.0, curl * 0.55 * length, 0.98 * length)
        p3 = (0.0, curl * length, (1.0 - droop) * length)
        centre = bezier(p0, p1, p2, p3, nv)
    frames = frames_along(centre)
    jit = [(rng.uniform(-1, 1)) for _ in range(ribs + 2)]

    def fn(u, v):
        s = (u - 0.5) * 2.0   # -1..1 across
        k = v * nv
        i = min(int(round(k)), nv)
        p, t, n, b = frames[i]
        # width profile: narrow base, widest at ~0.72, rounded tip; scalloped edge near the tip
        wv = base_width + (1.0 - base_width) * math.sin(math.pi * min(v, 1.0) ** 0.9) ** 0.8
        if v > 0.55:
            wv *= 1.0 - lobe_depth * abs(math.sin(lobes * math.pi * u)) * ((v - 0.55) / 0.45)
        half = 0.5 * width * wv
        # cross-section: convex outward with radial ribs
        rib = rib_amp * math.cos(s * math.pi * ribs * 0.5 + 0.15 * jit[int((u * ribs)) % len(jit)]) * (0.3 + 0.7 * v)
        conv = bulge * (1.0 - s * s) * (0.4 + 0.6 * v)
        if mid_dip:
            # cup the leaf: pull the centre back, keep the two edges forward (a shadowed spine down the leaf)
            conv -= mid_dip * math.exp(-(s / 0.42) ** 2) * math.sin(math.pi * min(v, 1.0) ** 0.8)
        # frame: n ~ outward, b ~ across.  Use across = world x, outward from frame normal
        across = Vector((1.0, 0.0, 0.0))
        outward = Vector((0.0, t.z, -t.y)).normalized()   # outer face normal, continuous along the curl
        pos = p + across * (half * s) + outward * (rib + conv)
        return tuple(pos)

    obj = surface(name, fn, nu, nv, coll, smooth=True)
    sol = obj.modifiers.new("Solidify", "SOLIDIFY")
    sol.thickness = thickness
    sol.offset = -1.0
    sol.use_even_offset = False
    sol.thickness_clamp = 0.5
    sub = obj.modifiers.new("Subsurf", "SUBSURF")
    sub.levels = 1
    apply_all(obj)
    return obj


def band_sweep(name, pts, axis, width_fn, thick_fn, coll=None, segments=10, power=2.6):
    """Sweep a flat band (superellipse section) along a polyline. axis = constant Vector along which the band is
    wide; the thin direction is tangent x axis. width_fn(t), thick_fn(t) are full sizes."""
    pts = [Vector(p) for p in pts]
    axis = Vector(axis).normalized()
    n = len(pts)
    tangents = []
    for i in range(n):
        if i == 0:
            t = pts[1] - pts[0]
        elif i == n - 1:
            t = pts[-1] - pts[-2]
        else:
            t = pts[i + 1] - pts[i - 1]
        tangents.append(t.normalized() if t.length > 1e-9 else Vector((0, 0, 1)))
    def se(c, k):
        return math.copysign(abs(c) ** (2.0 / k), c)
    def fn(u, v):
        i = min(int(round(v * (n - 1))), n - 1)
        p, t = pts[i], tangents[i]
        perp = t.cross(axis)
        if perp.length < 1e-6:
            perp = Vector((0, 0, 1))
        perp.normalize()
        th = u * TAU
        a = 0.5 * width_fn(v)
        b = 0.5 * thick_fn(v)
        return tuple(p + axis * (a * se(math.cos(th), power)) + perp * (b * se(math.sin(th), power)))
    return surface(name, fn, segments, n - 1, coll, wrap_u=True, smooth=True, cap_v0=True, cap_v1=True)


def volute(name, eye=(0.0, 0.0, 0.0), radius=0.35, turns=2.0, band=(0.16, 0.06), stem_base=None, stem_ctrl=None,
           coll=None, segments=10, steps=56, taper=0.45, direction=1.0):
    """Corinthian corner scroll. Spiral in the local YZ plane around `eye` (axis = +X). It starts at the bottom of
    the outer coil, rolls outward (+Y * direction), over the top, and curls inward into the eye. If stem_base is given
    a caulis (bezier from stem_base via stem_ctrl to the coil start) is prefixed. band = (width along X, thickness)."""
    eye = Vector(eye)
    pts = []
    th_max = turns * TAU
    for k in range(steps + 1):
        f = k / steps
        th = math.pi + f * th_max
        r = radius * (1.0 - f) ** 1.1 + radius * 0.07
        pts.append(eye + Vector((0.0, -direction * r * math.sin(th), r * math.cos(th))))
    n_stem = 0
    if stem_base is not None:
        sb = Vector(stem_base)
        sc = Vector(stem_ctrl) if stem_ctrl is not None else (sb + pts[0]) * 0.5
        stem = bezier(sb, sc, sc, pts[0], 12)[:-1]
        n_stem = len(stem)
        pts = stem + pts
    total = len(pts) - 1
    def width_fn(v):
        i = v * total
        f = max(0.0, (i - n_stem) / max(1, total - n_stem))
        return band[0] * (1.0 - taper * f)
    def thick_fn(v):
        i = v * total
        f = max(0.0, (i - n_stem) / max(1, total - n_stem))
        return band[1] * (1.0 - 0.3 * f)
    return band_sweep(name, pts, (1.0, 0.0, 0.0), width_fn, thick_fn, coll, segments=segments)


def skin_figure(name, joints, bones, coll=None, subdiv=2, smooth_iters=0):
    """Stick-figure body proxy. joints: {name: (Vector pos, (rx, ry))}; bones: [(a, b), ...].
    Returns a mesh object (skin + subsurf applied)."""
    names = list(joints.keys())
    index = {n: i for i, n in enumerate(names)}
    verts = [tuple(joints[n][0]) for n in names]
    edges = [(index[a], index[b]) for a, b in bones]
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, edges, [])
    me.update()
    obj = bpy.data.objects.new(name, me)
    (coll or work_collection()).objects.link(obj)
    sk = obj.modifiers.new("Skin", "SKIN")
    sk.use_smooth_shade = True
    sk.branch_smoothing = 0.5
    for i, n in enumerate(names):
        r = joints[n][1]
        if not isinstance(r, (tuple, list)):
            r = (r, r)
        obj.data.skin_vertices[0].data[i].radius = (r[0], r[1])
    obj.data.skin_vertices[0].data[0].use_root = True
    sub = obj.modifiers.new("Subsurf", "SUBSURF")
    sub.levels = subdiv
    apply_all(obj)
    if smooth_iters:
        smooth_verts(obj, smooth_iters)
    return obj


# ----------------------------------------------------------------------------- modifiers & mesh ops
def apply_all(obj):
    """Replace obj.data with the evaluated mesh (all modifiers applied). Objects hidden in the viewport are not
    evaluated by the depsgraph (modifiers would be silently skipped), so visibility is forced on for the evaluation."""
    hv, hr = obj.hide_viewport, obj.hide_render
    obj.hide_viewport = False
    obj.hide_render = False
    try:
        obj.hide_set(False)
    except Exception:
        pass
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(dg)
    me = bpy.data.meshes.new_from_object(ev, preserve_all_data_layers=True, depsgraph=dg)
    obj.hide_viewport, obj.hide_render = hv, hr
    old = obj.data
    obj.modifiers.clear()
    obj.data = me
    me.name = old.name + "_a"
    if old.users == 0:
        bpy.data.meshes.remove(old)
    return obj


def tri_count(obj):
    return sum(len(p.vertices) - 2 for p in obj.data.polygons)


def decimate(obj, target=None, ratio=None, planar=False):
    n = tri_count(obj)
    if ratio is None:
        if target is None or n <= target:
            return obj
        ratio = target / n
    m = obj.modifiers.new("Decimate", "DECIMATE")
    m.decimate_type = "COLLAPSE"
    m.ratio = max(0.001, min(1.0, ratio))
    m.use_collapse_triangulate = True
    apply_all(obj)
    fix_normals(obj)
    return obj


def fix_normals(obj):
    """Consistent outward face normals + drop degenerate faces (collapse decimation can flip slivers)."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.dissolve_degenerate(bm, dist=1e-5, edges=bm.edges)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    return obj


def remesh_voxel(obj, voxel=0.03, adaptivity=0.0, smooth_normals=True):
    m = obj.modifiers.new("Remesh", "REMESH")
    m.mode = "VOXEL"
    m.voxel_size = voxel
    m.adaptivity = adaptivity
    m.use_smooth_shade = smooth_normals
    apply_all(obj)
    return obj


def smooth_verts(obj, iterations=5, factor=0.5, keep_volume=False):
    if keep_volume:
        m = obj.modifiers.new("CSmooth", "CORRECTIVE_SMOOTH")
        m.iterations = iterations
        m.factor = factor
        m.use_only_smooth = True
    else:
        m = obj.modifiers.new("Smooth", "SMOOTH")
        m.iterations = iterations
        m.factor = factor
    apply_all(obj)
    return obj


def subdivide(obj, levels=1, simple=False):
    m = obj.modifiers.new("Subsurf", "SUBSURF")
    m.levels = levels
    m.subdivision_type = "SIMPLE" if simple else "CATMULL_CLARK"
    apply_all(obj)
    return obj


def solidify(obj, thickness, offset=-1.0):
    m = obj.modifiers.new("Solidify", "SOLIDIFY")
    m.thickness = thickness
    m.offset = offset
    m.use_even_offset = False
    m.thickness_clamp = 0.5
    apply_all(obj)
    return obj


def displace_noise(obj, strength=0.01, size=0.25, seed=0, direction="NORMAL", basis="BLENDER_ORIGINAL", depth=2,
                   texture_type="CLOUDS", mid=0.5):
    """Weathering / fold detail: Displace modifier with a procedural texture, applied."""
    tex = bpy.data.textures.new(f"tex_{obj.name}_{seed}", texture_type)
    if texture_type == "CLOUDS":
        tex.noise_scale = size
        tex.noise_depth = depth
        tex.noise_basis = basis
    elif texture_type == "STUCCI":
        tex.noise_scale = size
        tex.turbulence = 5.0
    elif texture_type == "VORONOI":
        tex.noise_scale = size
    m = obj.modifiers.new("Displace", "DISPLACE")
    m.texture = tex
    m.strength = strength
    m.mid_level = mid
    m.direction = direction
    m.texture_coords = "OBJECT"
    # random offset via an empty so seeds differ
    e = bpy.data.objects.new(f"disp_empty_{seed}", None)
    work_collection().objects.link(e)
    rng = random.Random(seed)
    e.location = (rng.uniform(-50, 50), rng.uniform(-50, 50), rng.uniform(-50, 50))
    m.texture_coords_object = e
    apply_all(obj)
    bpy.data.objects.remove(e)
    bpy.data.textures.remove(tex)
    return obj


def join(objs, name, coll=None):
    """Join meshes (world transforms applied) into a new object; originals removed."""
    bm = bmesh.new()
    for o in objs:
        if o.type != "MESH":
            continue
        me = o.data.copy()
        me.transform(o.matrix_world)
        bm.from_mesh(me)
        bpy.data.meshes.remove(me)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    obj = bpy.data.objects.new(name, me)
    (coll or (objs[0].users_collection[0] if objs and objs[0].users_collection else work_collection())).objects.link(obj)
    for o in objs:
        remove_object(o)
    return obj


def union_blob(objs, name, voxel=0.03, smooth=6, smooth_factor=0.5, coll=None, keep_volume=False, adaptivity=0.0):
    """Merge overlapping parts into ONE smooth watertight surface (sculpture look)."""
    j = join(objs, name + "_join", coll)
    remesh_voxel(j, voxel=voxel, adaptivity=adaptivity)
    if smooth:
        smooth_verts(j, smooth, smooth_factor, keep_volume=keep_volume)
    j.name = name
    j.data.name = name
    return j


def transform(obj, location=(0, 0, 0), rotation=(0, 0, 0), scale=(1, 1, 1), apply=True):
    """Set a transform and (optionally) bake it into the mesh."""
    obj.location = location
    obj.rotation_euler = Euler([math.radians(a) for a in rotation], "XYZ")
    obj.scale = scale
    if apply:
        bake_transform(obj)
    return obj


def bake_transform(obj):
    obj.data.transform(obj.matrix_world)
    obj.matrix_world = Matrix.Identity(4)
    return obj


def duplicate(obj, name, coll=None):
    new = obj.copy()
    new.data = obj.data.copy()
    new.name = name
    new.data.name = name
    (coll or obj.users_collection[0]).objects.link(new)
    return new


def shade_smooth(obj, sharp_angle_deg=None):
    me = obj.data
    me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    if sharp_angle_deg is not None:
        bm = bmesh.new()
        bm.from_mesh(me)
        lim = math.radians(sharp_angle_deg)
        for e in bm.edges:
            if len(e.link_faces) == 2:
                e.smooth = e.calc_face_angle(0.0) < lim
        bm.to_mesh(me)
        bm.free()
    me.update()


def bbox(obj):
    xs = [v.co.x for v in obj.data.vertices]
    ys = [v.co.y for v in obj.data.vertices]
    zs = [v.co.z for v in obj.data.vertices]
    return (min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs))


def origin_bottom_centre(obj, y_mode="centre"):
    """Move the mesh so the footprint bottom-centre is at the object origin. y_mode: 'centre' (bbox centre),
    'back' (min y at 0; the asset projects toward +Y, e.g. relief panels, keystones), 'keep' (XY as built: figures
    whose feet are already at the origin)."""
    (x0, y0, z0), (x1, y1, z1) = bbox(obj)
    if y_mode == "asis":          # mesh already in its socket frame (e.g. maidens hanging from the box rim)
        obj.matrix_world = Matrix.Identity(4)
        return obj
    if y_mode == "keep":
        cx, cy = 0.0, 0.0
    else:
        cx = 0.5 * (x0 + x1)
        cy = 0.5 * (y0 + y1) if y_mode == "centre" else y0
    obj.data.transform(Matrix.Translation((-cx, -cy, -z0)))
    obj.matrix_world = Matrix.Identity(4)
    return obj


def recentre_xy_only(obj):
    (x0, y0, z0), (x1, y1, z1) = bbox(obj)
    obj.data.transform(Matrix.Translation((-0.5 * (x0 + x1), -0.5 * (y0 + y1), 0.0)))
    return obj


def vertex_cavity(obj, name="cavity", rays=10, dist=None, bias=None, gamma=1.0):
    """Bake a per-vertex ambient-occlusion / cavity value into a FLOAT_COLOR attribute on the POINT domain.

    LOD0 is the RENDER LOD and carries no UVs, so a vertex attribute is the only channel the materials shader has
    for darkening the ornament recesses on the geometry that actually gets rendered (QA-03-15 / QA-02-3).
    1.0 = fully open, 0.0 = fully enclosed. Read it in a shader with an Attribute node, name "cavity".
    `dist` (default: 6 % of the object's diagonal) is the radius that counts as a recess."""
    me = obj.data
    me.calc_loop_triangles()
    bb = [Vector(c) for c in obj.bound_box]
    diag = (bb[6] - bb[0]).length
    dist = dist if dist is not None else 0.06 * diag
    bias = bias if bias is not None else max(1e-4, 0.004 * diag)
    from mathutils.bvhtree import BVHTree
    bvh = BVHTree.FromPolygons([v.co for v in me.vertices], [tuple(p.vertices) for p in me.polygons],
                               all_triangles=False, epsilon=0.0)
    # fixed cosine-ish hemisphere set (deterministic, so rebuilds are reproducible)
    dirs = []
    ga = math.pi * (3.0 - math.sqrt(5.0))
    for i in range(rays):
        z = (i + 0.5) / rays              # 0..1 -> cos(theta) from the normal
        r = math.sqrt(max(0.0, 1.0 - z * z))
        a = i * ga
        dirs.append((r * math.cos(a), r * math.sin(a), z))
    attr = me.color_attributes.get(name)
    if attr is not None:
        me.color_attributes.remove(attr)
    attr = me.color_attributes.new(name=name, type="FLOAT_COLOR", domain="POINT")
    up = Vector((0.0, 0.0, 1.0))
    vals = []
    for v in me.vertices:
        n = Vector(v.normal)
        if n.length < 1e-6:
            vals.append(1.0)
            continue
        n.normalize()
        t = n.cross(up if abs(n.z) < 0.9 else Vector((1.0, 0.0, 0.0)))
        t.normalize()
        b = n.cross(t)
        o = v.co + n * bias
        hits = 0
        for dx, dy, dz in dirs:
            d = (t * dx + b * dy + n * dz)
            hit = bvh.ray_cast(o, d, dist)
            if hit[0] is not None:
                hits += 1
        vals.append((1.0 - hits / rays) ** gamma)
    data = []
    for a in vals:
        data += [a, a, a, 1.0]
    attr.data.foreach_set("color", data)
    me.update()
    lo = min(vals) if vals else 1.0
    print(f"[orn] cavity attribute on {obj.name}: {len(vals)} verts, dist {dist:.3f} m, min {lo:.2f}, "
          f"mean {sum(vals) / max(1, len(vals)):.2f}")
    return attr


# ----------------------------------------------------------------------------- UV + baking
def ensure_uv(obj, angle_limit=66.0, margin=0.01):
    if obj.data.uv_layers:
        return
    prev_active = bpy.context.view_layer.objects.active
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    obj.hide_viewport = False
    obj.hide_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(angle_limit), island_margin=margin, correct_aspect=True)
    bpy.ops.object.mode_set(mode="OBJECT")
    obj.select_set(False)
    if prev_active:
        bpy.context.view_layer.objects.active = prev_active


def bake_maps(hi, lo, name, size=2048, ao=False, ao_samples=16, cage=None, ray=None):
    """Bake tangent-space normal (+ optional AO) from hi onto lo. Saves PNGs under assets/textures/orn/.
    Returns dict of relative paths ('//textures/orn/<file>')."""
    TEX_DIR.mkdir(parents=True, exist_ok=True)
    ensure_uv(lo)
    (x0, y0, z0), (x1, y1, z1) = bbox(lo)
    diag = (Vector((x1, y1, z1)) - Vector((x0, y0, z0))).length
    # Verified 2026-09-07 on the rotunda capital: a tiny cage (0.5 % of the diagonal) with an unlimited ray gives a
    # clean map; larger cages make rays hit neighbouring leaves first (black patches on LOD1).
    cage = cage if cage is not None else max(0.006, diag * 0.005)
    ray = ray if ray is not None else 0.0
    scene = bpy.context.scene
    prev_engine = scene.render.engine
    common.configure_cycles(scene, samples=ao_samples, denoise=False, device="GPU")
    scene.cycles.use_adaptive_sampling = False
    scene.render.bake.use_selected_to_active = True
    scene.render.bake.cage_extrusion = cage
    scene.render.bake.max_ray_distance = ray
    scene.render.bake.margin = 8
    scene.render.bake.use_clear = True
    # temp bake material with an active image node
    bmat = bpy.data.materials.new(f"ORN_bake_{name}")
    bmat.use_nodes = True
    node = bmat.node_tree.nodes.new("ShaderNodeTexImage")
    bmat.node_tree.nodes.active = node
    saved_mats = [m for m in lo.data.materials]
    lo.data.materials.clear()
    lo.data.materials.append(bmat)
    out = {}
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    hi_hidden = (hi.hide_render, hi.hide_viewport)
    hi.hide_render = False
    hi.hide_viewport = False
    hi.hide_set(False)
    lo.hide_viewport = False
    lo.hide_set(False)
    hi.select_set(True)
    lo.select_set(True)
    bpy.context.view_layer.objects.active = lo
    jobs = [("NORMAL", "nrm", True)]
    if ao:
        jobs.append(("AO", "ao", False))
    for btype, suffix, is_data in jobs:
        img = bpy.data.images.new(f"{name}_{suffix}", size, size, alpha=False, float_buffer=False)
        img.colorspace_settings.name = "Non-Color" if is_data else "sRGB"
        node.image = img
        t = time.time()
        kwargs = dict(type=btype, use_selected_to_active=True, cage_extrusion=cage, max_ray_distance=ray, margin=8)
        if btype == "NORMAL":
            kwargs["normal_space"] = "TANGENT"
        bpy.ops.object.bake(**kwargs)
        fname = f"{name}_{suffix}.png"
        fpath = TEX_DIR / fname
        img.filepath_raw = str(fpath)
        img.file_format = "PNG"
        img.save()
        img.filepath = str(fpath)
        img.source = "FILE"
        img.reload()
        out[suffix] = f"//textures/orn/{fname}"
        print(f"[orn] baked {btype} {size}px for {name} in {time.time() - t:.1f}s -> {fname}")
    lo.data.materials.clear()
    for m in saved_mats:
        lo.data.materials.append(m)
    bpy.data.materials.remove(bmat)
    hi.hide_render, hi.hide_viewport = hi_hidden
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    scene.render.engine = prev_engine
    return out


# ----------------------------------------------------------------------------- assets: LODs, material, props
def asset_name(typ, variant=None, lod=None):
    n = f"ORN_{typ}"
    if variant is not None:
        n += f"_v{variant}"
    if lod is not None:
        n += f"_LOD{lod}"
    return n


def enforce_lod2_budget(lod2, src, budget, voxel=None):
    """LOD2 wrapper around enforce_tri_budget; see there. Kept as a name because scripts/orn_r5_lod2fix.py calls it.
    `voxel` now defaults to the adaptive size (longest dimension / 240) rather than a flat 0.10 m: on the r6 attic
    panel a 0.10 m weld rounded 48-51 mm off the top and bottom of the 5.27 m field, i.e. LOD2 no longer filled the
    course it is placed in. 0.10 m is still what orn_r5_lod2fix.py passes explicitly."""
    return enforce_tri_budget(lod2, src, budget, voxel=voxel, tier=2)


def enforce_tri_budget(obj, src, budget, voxel=None, tier=2):
    """Make a LOD reach its tier budget even when collapse decimation stalls.

    Collapse decimation cannot go below ~4 faces per shell, so a LOD2 built from thousands of DISJOINT shells (the
    attic-panel relief after the field clamp: v1 stalled at 15343 tris against a 2400 budget) never reaches budget.
    A voxel remesh welds the shells into one surface first; the collapse then gets there. Silhouette only -- LOD2 is
    used beyond ~200 m. Only lod2's MESH DATA is replaced, so the object name, material slots, custom properties and
    viewport state survive and build_master.py sees no change.

    Folded in from the round-5 one-off scripts/orn_r5_lod2fix.py (ORN r5 review finding 5) so that a rebuild of an
    asset cannot silently restore an over-budget LOD2. Round 6: it applies to **LOD1** too. The r6 attic panel
    (figures scaled x1.1711 onto the 5.27 m field) made design 1 a denser shell soup and its LOD1 stalled at 34652
    tris against the 24000 budget -- the same stall, one tier up, and LOD1 is the tier the viewport and every Eevee
    preview use. `voxel` defaults to the object's longest dimension / 240 (0.044 m on a 10.5 m panel), fine enough
    that the weld only closes the gaps between shells.
    """
    before = tri_count(obj)
    if before <= budget:
        return obj
    if voxel is None:
        voxel = max(0.008, max(obj.dimensions) / 240.0)
    coll = obj.users_collection[0] if obj.users_collection else bpy.context.scene.collection
    tmp = duplicate(src, f"{obj.name}__weld", coll)
    remesh_voxel(tmp, voxel=voxel)
    mid = tri_count(tmp)
    decimate(tmp, target=budget)
    shade_smooth(tmp)
    old = obj.data
    obj.data = tmp.data
    obj.data.name = obj.name
    bpy.data.objects.remove(tmp, do_unlink=True)
    if old.users == 0:
        bpy.data.meshes.remove(old)
    after = tri_count(obj)
    obj[f"lod{tier}_note"] = f"voxel-welded at {voxel:.3f} m then collapsed: {before} -> {after} tris (budget {budget})"
    print(f"[orn] LOD{tier} budget: {obj.name} {before} -> remesh {mid} -> {after} tris (budget {budget})")
    return obj


def finalize_asset(hi, typ, variant=1, coll=None, budgets=None, bake=True, bake_size=2048, ao=False,
                   lod2_obj=None, y_mode="centre", size_note="", extra_props=None, sharp_angle=None, cavity=False):
    """Turn a hi-res work mesh into ORN_<typ>_v<n>_LOD0/1/2 in ORN_<typ>: origin, material, decimation, bakes, props.
    Returns (lod0, lod1, lod2)."""
    coll = coll or orn_collection(typ)
    budgets = budgets or BUDGETS.get(typ, BUDGETS["default"])
    mat = common.load_material(MAT_NAME)
    origin_bottom_centre(hi, y_mode=y_mode)
    shade_smooth(hi, sharp_angle)
    lod0 = hi
    lod0.name = asset_name(typ, variant, 0)
    lod0.data.name = lod0.name
    common.link_object(lod0, coll)
    decimate(lod0, target=budgets[0])
    lod1 = duplicate(lod0, asset_name(typ, variant, 1), coll)
    decimate(lod1, target=budgets[1])
    shade_smooth(lod1)
    # collapse stalls at ~4 faces per shell on shell-soup reliefs at LOD1 as well as LOD2 (r6 attic panel v1)
    enforce_tri_budget(lod1, lod0, budgets[1], tier=1)
    if lod2_obj is not None:
        lod2 = lod2_obj
        lod2.name = asset_name(typ, variant, 2)
        lod2.data.name = lod2.name
        common.link_object(lod2, coll)
        shade_smooth(lod2)
        enforce_lod2_budget(lod2, lod2, budgets[2])
    else:
        lod2 = duplicate(lod1, asset_name(typ, variant, 2), coll)
        decimate(lod2, target=budgets[2])
        shade_smooth(lod2)
        # collapse stalls at ~4 faces per shell on shell-soup reliefs; weld and re-collapse if still over budget
        enforce_lod2_budget(lod2, lod1, budgets[2])
    for o in (lod0, lod1, lod2):
        common.assign_material(o, mat)
        o["orn_type"] = typ
        o["variant"] = variant
        o["tris"] = tri_count(o)
        (x0, y0, z0), (x1, y1, z1) = bbox(o)
        o["size"] = f"{x1 - x0:.2f} x {y1 - y0:.2f} x {z1 - z0:.2f} m (x y z)"
        if size_note:
            o["size_note"] = size_note
        if extra_props:
            for k, v in extra_props.items():
                o[k] = v
    if cavity:
        t0 = time.time()
        for o in (lod0, lod1):
            vertex_cavity(o)
            o["cavity_attr"] = "cavity"
        print(f"[orn] cavity attributes for {asset_name(typ, variant)} in {time.time() - t0:.1f}s")
    if bake:
        try:
            maps = bake_maps(lod0, lod1, asset_name(typ, variant), size=bake_size, ao=ao)
            lod1["normal_map"] = maps.get("nrm", "")
            lod1["ao_map"] = maps.get("ao", "")
        except Exception as e:
            print(f"[orn] WARNING bake failed for {lod1.name}: {e}")
            lod1["normal_map"] = ""
            lod1["ao_map"] = ""
    else:
        lod1["normal_map"] = ""
        lod1["ao_map"] = ""
    # viewport default: LOD1 only
    lod0.hide_viewport = True
    lod2.hide_viewport = True
    print(f"[orn] {asset_name(typ, variant)}: LOD0 {tri_count(lod0)} / LOD1 {tri_count(lod1)} / LOD2 {tri_count(lod2)} tris")
    return lod0, lod1, lod2


def clear_work():
    common.clear_collection("ORN_work", remove_collection=True)
    for t in list(bpy.data.textures):
        if t.name.startswith("tex_"):
            bpy.data.textures.remove(t)
    for m in list(bpy.data.meshes):
        if m.users == 0:
            bpy.data.meshes.remove(m)


def report(typ=None):
    lines = []
    for o in sorted(bpy.data.objects, key=lambda o: o.name):
        if o.name.startswith("ORN_") and o.type == "MESH" and "_LOD" in o.name:
            if typ and o.get("orn_type") != typ:
                continue
            lines.append(f"{o.name}: {tri_count(o)} tris, {o.get('size', '')}, nrm={o.get('normal_map', '-')}")
    return "\n".join(lines)


# ----------------------------------------------------------------------------- frieze runs (QA-01-11)
def unit_length_of(unit_obj):
    """Documented repeat length of a linear moulding unit, in metres. Every ORN moulding LOD carries the custom
    property `unit_length`; fall back to the X size of its bounding box."""
    ul = unit_obj.get("unit_length")
    if ul:
        return float(ul)
    (x0, _, _), (x1, _, _) = bbox(unit_obj)
    return max(1e-6, x1 - x0)


def _run_geometry(socket, unit_length):
    """Resolve a `frieze_run` socket into a list of (matrix_world, x_scale) placements for consecutive units.

    Straight run  : custom prop `run_length` (or `size_hint`); the socket sits at the START of the run, local +X =
                    run direction, +Y = outward, +Z = up (docs/sockets.md).
    Curved run    : additionally `arc_center` (3 floats, world), `arc_radius`, and optionally `arc_start` / `arc_end`
                    (radians, measured in the world XY plane from +X). Without the angles they are derived from the
                    socket's position (start angle) and its local +X (sweep direction) plus `run_length`.
    Units are laid end to end and scaled along X by <= a few % so the run ends flush; curved units are chords.
    """
    M = socket.matrix_world
    origin = M.translation.copy()
    ax_x = (M.to_3x3() @ Vector((1, 0, 0))).normalized()
    ax_z = (M.to_3x3() @ Vector((0, 0, 1))).normalized()
    run = float(socket.get("run_length", socket.get("size_hint", 0.0)) or 0.0)
    centre = socket.get("arc_center")
    radius = float(socket.get("arc_radius", 0.0) or 0.0)
    out = []
    if centre is not None and radius > 1e-6:
        c = Vector((float(centre[0]), float(centre[1]), origin.z))
        a0 = socket.get("arc_start")
        a1 = socket.get("arc_end")
        if a0 is None:
            a0 = math.atan2(origin.y - c.y, origin.x - c.x)
        a0 = float(a0)
        if a1 is None:
            perp = Vector((-math.sin(a0), math.cos(a0), 0.0))       # CCW tangent at a0
            sign = 1.0 if ax_x.dot(perp) >= 0.0 else -1.0
            if run <= 0.0:
                run = radius * TAU
            a1 = a0 + sign * (run / radius)
        a1 = float(a1)
        sweep = a1 - a0
        n = max(1, int(round(abs(sweep) * radius / unit_length)))
        dt = sweep / n
        for i in range(n):
            pa = c + Vector((radius * math.cos(a0 + i * dt), radius * math.sin(a0 + i * dt), 0.0))
            pb = c + Vector((radius * math.cos(a0 + (i + 1) * dt), radius * math.sin(a0 + (i + 1) * dt), 0.0))
            chord = pb - pa
            clen = chord.length
            x = chord.normalized()
            z = ax_z
            y = z.cross(x).normalized()                              # matches the socket's own frame at i = 0
            z = x.cross(y).normalized()
            rot = Matrix((( x.x, y.x, z.x), ( x.y, y.y, z.y), ( x.z, y.z, z.z))).to_4x4()
            out.append((Matrix.Translation((pa + pb) * 0.5) @ rot, clen / unit_length))
        return out, n, abs(sweep) * radius
    # straight
    if run <= 0.0:
        run = unit_length
    n = max(1, int(round(run / unit_length)))
    sx = run / (n * unit_length)
    for i in range(n):
        out.append((M @ Matrix.Translation(((i + 0.5) * unit_length * sx, 0.0, 0.0)), sx))
    return out, n, run


def array_unit_along_run(unit_obj, socket_empty, collection=None, name_prefix=None, instances=True,
                         seed_base=None, extra_props=None, fit="auto", tol=0.06, alternatives=None):
    """Lay copies of a linear moulding unit end to end along a `frieze_run` socket. Returns the new objects.

    `unit_obj`     an `ORN_<kind>_v<n>_LOD<k>` mesh whose origin is the bottom-centre of its BACK face, that runs
                   along +X for `unit_obj["unit_length"]` metres and projects toward +Y (docs/sockets.md).
    `socket_empty` a `SOCKET_frieze_run_###` empty (straight: `run_length`; curved: `arc_center` / `arc_radius` and
                   optionally `arc_start` / `arc_end`).
    `instances`    True -> every copy shares `unit_obj.data` (linked duplicates, one mesh in memory).
    `fit`          "scale" (or True) -> the leftover is absorbed by scaling every unit along X so the run ends flush;
                   "centre" -> floor(run / unit) unscaled units centred on the run, leaving equal plain margins at
                   both ends (what a real frieze does on a short run); "auto" (default) -> scale when that costs less
                   than `tol` (6 %), otherwise centre; False/"none" -> exact-length units laid from the start.
    `alternatives` optional list of other unit objects; the one whose scale fit is closest to 1 is used, so the lead
                   can hand the helper e.g. [ORN_rosette_band, ORN_greek_key] and let each run pick.
    Each copy carries `orn_type`, `unit_index`, `run_socket` and a decorrelated `instance_seed` so that
    MAT_ornament_concrete's Object-Info-Random / instance_seed variation differs per unit.
    """
    if alternatives:
        best, best_err = unit_obj, None
        for cand in [unit_obj] + list(alternatives):
            pl, _, _ = _run_geometry(socket_empty, unit_length_of(cand))
            err = abs(pl[0][1] - 1.0)
            if best_err is None or err < best_err:
                best, best_err = cand, err
        unit_obj = best
    kind = unit_obj.get("orn_type") or unit_obj.name
    ul = unit_length_of(unit_obj)
    places, n, run = _run_geometry(socket_empty, ul)
    mode = {True: "scale", False: "none", None: "none"}.get(fit, fit)
    if mode == "auto":
        mode = "scale" if abs(places[0][1] - 1.0) <= tol else "centre"
    if mode == "centre" and len(places) > 1 and socket_empty.get("arc_center") is None:
        # unscaled units, centred on the run: n' = floor(run / unit), plain margins at both ends
        M = socket_empty.matrix_world
        n = max(1, int(run // ul))
        margin = 0.5 * (run - n * ul)
        places = [(M @ Matrix.Translation((margin + (i + 0.5) * ul, 0.0, 0.0)), 1.0) for i in range(n)]
    elif mode == "centre":
        places = [(m, 1.0) for m, _ in places]
    elif mode == "none":
        places = [(m, 1.0) for m, _ in places]
    if collection is None:
        collection = unit_obj.users_collection[0] if unit_obj.users_collection else bpy.context.scene.collection
    prefix = name_prefix or f"INST_{kind}"
    sidx = socket_empty.name.rsplit("_", 1)[-1]
    if seed_base is None:
        seed_base = abs(hash(socket_empty.name)) % 100000
    made = []
    for i, (mat, sx) in enumerate(places):
        ob = bpy.data.objects.new(f"{prefix}_{sidx}_{i:03d}", unit_obj.data if instances else unit_obj.data.copy())
        collection.objects.link(ob)
        ob.matrix_world = mat @ Matrix.Diagonal((sx, 1.0, 1.0, 1.0))
        ob["orn_type"] = kind
        ob["unit_index"] = i
        ob["run_socket"] = socket_empty.name
        ob["instance_seed"] = (seed_base + i * 7919) % 100000
        if extra_props:
            for k, v in extra_props.items():
                ob[k] = v
        made.append(ob)
    sx0 = places[0][1]
    warn = "  *** x-fit off by more than %.0f %%; consider a shorter unit ***" % (tol * 100) if abs(sx0 - 1.0) > tol else ""
    print(f"[orn] array_unit_along_run: {unit_obj.name} x{len(places)} ({ul:.3f} m unit) along {socket_empty.name} "
          f"({run:.2f} m{', curved' if socket_empty.get('arc_center') is not None else ''}), {mode}, x-fit {sx0:.4f}{warn}")
    return made
