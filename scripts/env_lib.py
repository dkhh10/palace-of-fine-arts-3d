"""Environment helpers (owned by the Environment specialist). Import from env_build.py / env_trees.py / env_preview.py.

Geometry conventions as in common.py: metric, +Y = east (lagoon), -X = north, z = 0 rotunda floor, WATER_Z lagoon.
Everything here is pure bpy/bmesh/mathutils + numpy (no scipy).
"""
import bpy, bmesh, math, random, sys, os
from pathlib import Path
from mathutils import Vector, noise
from mathutils.geometry import delaunay_2d_cdt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common

WATER_Z = common.WATER_Z          # -1.3
GROUND_Z = common.GROUND_Z        # -0.4
SHORE_Z = WATER_Z + 0.55          # top of the rip-rap bank
PENINSULA_Z = -0.6

# Placeholder colours for library materials that do not exist yet (materials.blend is another agent's file).
# These only colour the fallback placeholder; common.load_material swaps in the real material when it exists.
ENV_PLACEHOLDER_COLORS = {
    "MAT_lawn": ((0.09, 0.16, 0.045, 1.0), 0.85),
    "MAT_soil": ((0.14, 0.10, 0.06, 1.0), 0.9),
    "MAT_gravel_path": ((0.38, 0.35, 0.30, 1.0), 0.9),
    "MAT_rock_riprap": ((0.32, 0.30, 0.26, 1.0), 0.85),
    "MAT_bark_cypress": ((0.20, 0.14, 0.10, 1.0), 0.9),
    "MAT_bark_eucalyptus": ((0.55, 0.48, 0.40, 1.0), 0.8),
    "MAT_leaf_cypress": ((0.018, 0.038, 0.012, 1.0), 0.8),
    "MAT_leaf_pine": ((0.015, 0.032, 0.011, 1.0), 0.8),
    "MAT_leaf_eucalyptus": ((0.075, 0.115, 0.05, 1.0), 0.7),
    "MAT_leaf_broadleaf": ((0.05, 0.11, 0.028, 1.0), 0.7),
    "MAT_shrub": ((0.045, 0.10, 0.03, 1.0), 0.8),
    "MAT_shrub_light": ((0.13, 0.19, 0.055, 1.0), 0.8),
    "MAT_shrub_dry": ((0.26, 0.15, 0.07, 1.0), 0.9),
    "MAT_reeds": ((0.32, 0.24, 0.10, 1.0), 0.85),
    "MAT_water_lagoon": ((0.04, 0.09, 0.08, 1.0), 0.08),
    # QA-04-8: the near field reads blue (hue 209) instead of teal (190-192).  Lighting showed the sky hue is
    # exact, so the missing green is the lagoon's own upwelling - the bed under the shallow shelf, which was on
    # MAT_soil (brown).  ENV names MAT_lagoon_bed; until the library ships it this placeholder is the algae /
    # silt olive the bed reads as through 0.3-0.9 m of water (refs 022, 169, 063).
    "MAT_lagoon_bed": ((0.055, 0.085, 0.048, 1.0), 0.92),
    "MAT_backdrop_building": ((0.40, 0.31, 0.19, 1.0), 0.85),
    "MAT_backdrop_roof": ((0.17, 0.16, 0.145, 1.0), 0.85),
    # far-field only (QA-03-11): asphalt carriageways and the Presidio's red clay tile roofs. Not in the library
    # yet - see docs/environment_notes.md "open issues".
    "MAT_backdrop_asphalt": ((0.052, 0.050, 0.049, 1.0), 0.72),
    "MAT_backdrop_roof_tile": ((0.185, 0.072, 0.042, 1.0), 0.80),
    "MAT_backdrop_skylight": ((0.045, 0.055, 0.065, 1.0), 0.18),
    "MAT_backdrop_door_green": ((0.03, 0.11, 0.05, 1.0), 0.5),
    "MAT_backdrop_forest": ((0.05, 0.09, 0.04, 1.0), 0.9),
    "MAT_backdrop_hill": ((0.25, 0.28, 0.20, 1.0), 0.9),
    "MAT_bird_white": ((0.85, 0.85, 0.82, 1.0), 0.6),
    "MAT_lamp_post": ((0.08, 0.08, 0.08, 1.0), 0.5),
}


FOLIAGE_MATS = ("MAT_leaf_cypress", "MAT_leaf_pine", "MAT_leaf_eucalyptus", "MAT_leaf_broadleaf", "MAT_shrub",
                "MAT_shrub_light", "MAT_shrub_dry", "MAT_reeds")


def _foliage_placeholder_tree(m, col, rough, translucency=0.35, tint_attr="Col"):
    """Placeholder foliage shader: Principled + Translucent mix, base colour multiplied by the per-instance vertex
    colour tint (attribute `Col`, white when absent). The library material replaces all of this."""
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    mix = nt.nodes.new("ShaderNodeMixShader")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    trans = nt.nodes.new("ShaderNodeBsdfTranslucent")
    attr = nt.nodes.new("ShaderNodeAttribute")
    attr.attribute_name = tint_attr
    mul = nt.nodes.new("ShaderNodeMix")
    mul.data_type = "RGBA"
    mul.blend_type = "MULTIPLY"
    mul.inputs["Factor"].default_value = 1.0
    mul.inputs[6].default_value = col          # A
    nt.links.new(attr.outputs["Color"], mul.inputs[7])   # B
    # attribute is black when the mesh has no `Col`: guard with a max against white*0 -> use a mix toward white
    guard = nt.nodes.new("ShaderNodeMix")
    guard.data_type = "RGBA"
    guard.blend_type = "MIX"
    guard.inputs["Factor"].default_value = 1.0
    guard.inputs[6].default_value = col
    nt.links.new(attr.outputs["Alpha"], guard.inputs["Factor"])   # alpha 0 (no attribute) -> plain colour
    nt.links.new(mul.outputs[2], guard.inputs[7])
    nt.links.new(guard.outputs[2], bsdf.inputs["Base Color"])
    nt.links.new(guard.outputs[2], trans.inputs["Color"])
    bsdf.inputs["Roughness"].default_value = rough
    try:
        bsdf.inputs["Specular IOR Level"].default_value = 0.25
    except Exception:
        pass
    mix.inputs[0].default_value = translucency
    nt.links.new(bsdf.outputs[0], mix.inputs[1])
    nt.links.new(trans.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    out.location = (600, 0); mix.location = (400, 0); bsdf.location = (150, 100); trans.location = (150, -250)
    guard.location = (-100, 0); mul.location = (-300, 0); attr.location = (-550, 0)


def mat(name):
    """Library material by name (placeholder recoloured to something plausible if the library lacks it)."""
    m = common.load_material(name)
    if m.get("placeholder") and name in ENV_PLACEHOLDER_COLORS:
        col, rough = ENV_PLACEHOLDER_COLORS[name]
        if name in FOLIAGE_MATS and m.node_tree and not m.get("env_foliage_tree"):
            _foliage_placeholder_tree(m, col, rough, translucency=0.3 if name != "MAT_shrub_dry" else 0.1)
            m["env_foliage_tree"] = True
        else:
            bsdf = m.node_tree.nodes.get("Principled BSDF") if m.node_tree else None
            if bsdf:
                bsdf.inputs["Base Color"].default_value = col
                bsdf.inputs["Roughness"].default_value = rough
        m.diffuse_color = col
    if name in FOLIAGE_MATS:
        m.use_backface_culling = False
    return m


def qa_camera(key, fallback_loc, fallback_lens=None):
    """`(location, lens)` of the QA camera whose name contains `key`, read from `scripts/qa_cameras.py`.

    The sight-line caps (`env_build.band_sightline_cap`, `env_trees.screen_height_cap`) are only correct if they
    use the stations the QA renders actually use, and those move: the lead re-stationed cam 02 in QA round 04.
    A hand-copied snapshot would keep capping against the old station without saying so.  Returns **None** if
    qa_cameras is importable but has no such camera (the caller drops that eye); returns the literal fallback
    only if qa_cameras cannot be imported at all, so an ENV build outside the repo still runs.
    """
    try:
        import qa_cameras
    except Exception:                                    # noqa: BLE001 - running without the repo on sys.path
        return (tuple(fallback_loc), fallback_lens)
    spec = next((c for c in qa_cameras.CAMERAS if key in c["name"]), None)
    if spec is None:
        return None
    return (tuple(spec["loc"]), spec.get("lens", fallback_lens))


def mat_or(preferred, fallback):
    """Library material `preferred` if it exists, otherwise `fallback`. Lets ENV name materials the materials agent
    is still building (MAT_leaf_pine, MAT_shrub_light, MAT_shrub_dry): the moment the name lands in the library the
    remap takes effect with no code change. The unused placeholder datablock is discarded."""
    m = common.load_material(preferred)
    if not m.get("placeholder"):
        if preferred in FOLIAGE_MATS or "leaf" in preferred or "shrub" in preferred or "reed" in preferred:
            m.use_backface_culling = False
        return m
    if m.users == 0:
        try:
            m.use_fake_user = False
            bpy.data.materials.remove(m)
        except Exception:
            pass
    return mat(fallback)


def jitter_polygon(poly, step=2.0, amp=0.45, seed=3):
    """Resample a closed polygon at `step` and push the points along the local normal by noise (+-amp):
    turns the smooth OSM shore trace into an irregular stone edge. Returns a CCW polygon."""
    pts = resample_polyline(ensure_ccw(poly), step, closed=True)
    n = len(pts)
    out = []
    for i in range(n):
        p0, p1, p2 = Vector(pts[i - 1]), Vector(pts[i]), Vector(pts[(i + 1) % n])
        d = (p2 - p0)
        if d.length < 1e-6:
            out.append(tuple(p1)); continue
        d.normalize()
        nrm = Vector((d.y, -d.x))
        off = amp * (0.6 * fnoise(p1.x, p1.y, 0.35, seed) + 0.4 * fnoise(p1.x, p1.y, 1.1, seed + 1))
        out.append((p1.x + nrm.x * off, p1.y + nrm.y * off))
    return dedupe_poly(out, eps=0.2)


# ----------------------------------------------------------------------------- 2D polygon utilities
def poly_area(poly):
    a = 0.0
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        a += x1 * y2 - x2 * y1
    return 0.5 * a


def ensure_ccw(poly):
    return list(poly) if poly_area(poly) > 0 else list(reversed(poly))


def dedupe_poly(poly, eps=0.05):
    out = []
    for p in poly:
        if not out or (abs(p[0] - out[-1][0]) > eps or abs(p[1] - out[-1][1]) > eps):
            out.append((float(p[0]), float(p[1])))
    if len(out) > 1 and abs(out[0][0] - out[-1][0]) < eps and abs(out[0][1] - out[-1][1]) < eps:
        out.pop()
    return out


def point_in_poly(x, y, poly):
    inside = False
    n = len(poly)
    j = n - 1
    for i in range(n):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if (yi > y) != (yj > y):
            xint = (xj - xi) * (y - yi) / (yj - yi + 1e-12) + xi
            if x < xint:
                inside = not inside
        j = i
    return inside


def seg_dist(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    l2 = dx * dx + dy * dy
    if l2 < 1e-12:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / l2))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


class PolyField:
    """Fast-ish signed distance to a polygon using a coarse bucket grid over its segments."""

    def __init__(self, poly, cell=10.0, closed=True):
        self.poly = poly
        self.cell = cell
        self.closed = closed
        xs = [p[0] for p in poly]
        ys = [p[1] for p in poly]
        self.x0, self.y0 = min(xs) - cell, min(ys) - cell
        self.nx = int((max(xs) - self.x0) / cell) + 3
        self.ny = int((max(ys) - self.y0) / cell) + 3
        self.buckets = {}
        n = len(poly)
        for i in range(n if closed else n - 1):
            a, b = poly[i], poly[(i + 1) % n]
            i0, i1 = sorted((int((a[0] - self.x0) / cell), int((b[0] - self.x0) / cell)))
            j0, j1 = sorted((int((a[1] - self.y0) / cell), int((b[1] - self.y0) / cell)))
            for ci in range(i0 - 1, i1 + 2):
                for cj in range(j0 - 1, j1 + 2):
                    self.buckets.setdefault((ci, cj), []).append((a[0], a[1], b[0], b[1]))

    def dist(self, x, y):
        ci, cj = int((x - self.x0) / self.cell), int((y - self.y0) / self.cell)
        best = 1e9
        r = 0
        while r < 6:
            found = False
            for i in range(ci - r, ci + r + 1):
                for j in range(cj - r, cj + r + 1):
                    if r > 0 and abs(i - ci) != r and abs(j - cj) != r:
                        continue
                    for (ax, ay, bx, by) in self.buckets.get((i, j), ()):
                        found = True
                        d = seg_dist(x, y, ax, ay, bx, by)
                        if d < best:
                            best = d
            if found and best < (r + 0.5) * self.cell:
                break
            r += 1
        if best > 1e8:   # nothing nearby: brute force
            p = self.poly
            n = len(p)
            best = min(seg_dist(x, y, p[i][0], p[i][1], p[(i + 1) % n][0], p[(i + 1) % n][1]) for i in range(n if self.closed else n - 1))
        return best

    def signed(self, x, y):
        """negative inside (closed polygons only)."""
        d = self.dist(x, y)
        return -d if (self.closed and point_in_poly(x, y, self.poly)) else d


def water_polygons(site):
    """`(lagoon_osm, lagoon, islets, lagoon_field, islet_fields)` for a `site_local` dict.

    One definition of "where the water is", so a probe cannot drift from the build (r9 review: the same class of
    mistake as ENV's colonnade exclusion, which tested a copy of the arc instead of the arc).  `env_build` calls
    this at import time; `env_r9_replan --land` calls it to test PLAN coordinates against the same fields.
    """
    lagoon_osm = ensure_ccw(dedupe_poly(site["lagoon0"][0]))
    lagoon = jitter_polygon(lagoon_osm, step=2.0, amp=0.5, seed=3)      # irregular stone edge (refs 169, 022)
    islets = [ensure_ccw(dedupe_poly(site["lagoon1"][0])), ensure_ccw(dedupe_poly(site["lagoon2"][0]))]
    return (lagoon_osm, lagoon, islets,
            PolyField(lagoon, cell=8.0), [PolyField(p, cell=6.0) for p in islets])


def offset_polygon(poly, dist):
    """Simple vertex-normal offset (positive = outward for a CCW polygon). Good enough for smooth shorelines."""
    poly = ensure_ccw(poly)
    n = len(poly)
    out = []
    for i in range(n):
        p0, p1, p2 = poly[i - 1], poly[i], poly[(i + 1) % n]
        d1 = Vector((p1[0] - p0[0], p1[1] - p0[1])).normalized()
        d2 = Vector((p2[0] - p1[0], p2[1] - p1[1])).normalized()
        n1 = Vector((d1.y, -d1.x))
        n2 = Vector((d2.y, -d2.x))
        nn = (n1 + n2)
        if nn.length < 1e-6:
            nn = n1
        nn.normalize()
        cosang = max(0.35, nn.dot(n1))
        out.append((p1[0] + nn.x * dist / cosang, p1[1] + nn.y * dist / cosang))
    return out


def resample_polyline(pts, step, closed=False):
    """Points at roughly even spacing along a polyline."""
    if closed:
        pts = list(pts) + [pts[0]]
    out = [pts[0]]
    carry = 0.0
    for i in range(len(pts) - 1):
        a, b = Vector(pts[i]), Vector(pts[i + 1])
        seg = (b - a).length
        if seg < 1e-9:
            continue
        t = step - carry
        while t < seg:
            out.append(tuple(a + (b - a) * (t / seg)))
            t += step
        carry = seg - (t - step)
    return out


def smooth_polyline(pts, iterations=2, closed=True):
    pts = [Vector(p) for p in pts]
    n = len(pts)
    for _ in range(iterations):
        new = []
        for i in range(n):
            if not closed and (i == 0 or i == n - 1):
                new.append(pts[i])
                continue
            new.append((pts[i - 1] + 2 * pts[i] + pts[(i + 1) % n]) / 4)
        pts = new
    return [tuple(p) for p in pts]


def ribbon_polygons(polyline, width, closed=False):
    """Turn a polyline into quad strips (list of 4-point polygons) of the given width."""
    pts = [Vector(p) for p in polyline]
    if closed:
        pts.append(pts[0])
    quads = []
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        d = (b - a)
        if d.length < 1e-6:
            continue
        d.normalize()
        nrm = Vector((-d.y, d.x)) * (width / 2)
        quads.append([tuple(a + nrm), tuple(a - nrm), tuple(b - nrm), tuple(b + nrm)])
    return quads


def smoothstep(e0, e1, x):
    t = max(0.0, min(1.0, (x - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


def fnoise(x, y, scale, seed=0.0):
    return noise.noise(Vector((x * scale + seed * 13.1, y * scale + seed * 7.7, seed)))


# ----------------------------------------------------------------------------- mesh building
def mesh_from_tris(name, verts, faces, coll, materials=(), face_mat=None, smooth=True):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], [tuple(f) for f in faces])
    me.update(calc_edges=True)
    for m in materials:
        me.materials.append(m)
    if face_mat is not None:
        me.polygons.foreach_set("material_index", face_mat)
    if smooth:
        me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    obj = bpy.data.objects.new(name, me)
    coll.objects.link(obj)
    return obj


def cdt_triangulate(points, constraint_polys, epsilon=0.01):
    """Constrained Delaunay of points + closed constraint polygons. Returns (verts2d, tris)."""
    verts = [Vector((p[0], p[1])) for p in points]
    edges = []
    for poly in constraint_polys:
        base = len(verts)
        for p in poly:
            verts.append(Vector((p[0], p[1])))
        n = len(poly)
        for i in range(n):
            edges.append((base + i, base + (i + 1) % n))
    vo, eo, fo, ov, oe, of_ = delaunay_2d_cdt(verts, edges, [], 0, epsilon)
    tris = []
    for f in fo:
        if len(f) == 3:
            tris.append(tuple(f))
        else:   # fan-triangulate the rare n-gon
            for k in range(1, len(f) - 1):
                tris.append((f[0], f[k], f[k + 1]))
    return [(v.x, v.y) for v in vo], tris


def displace_mesh_random(me, amount, seed=0):
    rnd = random.Random(seed)
    for v in me.vertices:
        n = v.normal
        v.co += n * rnd.uniform(-amount, amount)


def make_rock_mesh(name, radius=0.5, seed=0, subdiv=1):
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=radius)
    rnd = random.Random(seed)
    sx, sy, sz = rnd.uniform(0.8, 1.4), rnd.uniform(0.7, 1.2), rnd.uniform(0.5, 0.8)
    for v in bm.verts:
        n = noise.noise(v.co * rnd.uniform(1.5, 3.0) + Vector((seed, 0, 0)))
        v.co = v.co * (1.0 + 0.35 * n)
        v.co.x *= sx
        v.co.y *= sy
        v.co.z *= sz
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = False
    return me


def join_instances(name, mesh, transforms, coll, material=None, tints=None):
    """Bake many copies of `mesh` (list of (loc, rot_z, scale)) into one mesh object. `tints` (one RGB per
    transform) is written to a point colour attribute `Col` for per-instance colour variation."""
    bm = bmesh.new()
    src = bmesh.new()
    src.from_mesh(mesh)
    src.verts.ensure_lookup_table()
    verts_src = [v.co.copy() for v in src.verts]
    faces_src = [[v.index for v in f.verts] for f in src.faces]
    src.free()
    all_verts = []
    all_faces = []
    for (loc, rz, sc) in transforms:
        base = len(all_verts)
        c, s = math.cos(rz), math.sin(rz)
        if isinstance(sc, (int, float)):
            sx = sy = sz = sc
        else:
            sx, sy, sz = sc
        for v in verts_src:
            x, y, z = v.x * sx, v.y * sy, v.z * sz
            all_verts.append((loc[0] + c * x - s * y, loc[1] + s * x + c * y, loc[2] + z))
        for f in faces_src:
            all_faces.append([base + i for i in f])
    me = bpy.data.meshes.new(name)
    me.from_pydata(all_verts, [], all_faces)
    me.update()
    if material:
        me.materials.append(material)
    if tints is not None and len(all_verts):
        nv = len(verts_src)
        ca = me.color_attributes.new(name="Col", type="FLOAT_COLOR", domain="POINT")
        flat = []
        for t in tints:
            flat.extend([t[0], t[1], t[2], 1.0] * nv)
        ca.data.foreach_set("color", flat)
    # keep the source mesh's UVs (all instances share them)
    if mesh.uv_layers:
        src_uv = mesh.uv_layers[0].data
        uv = me.uv_layers.new(name="UVMap")
        n_loop = len(src_uv)
        flat = [0.0] * (len(me.loops) * 2)
        base = 0
        per = [src_uv[i].uv for i in range(n_loop)]
        for k in range(len(transforms)):
            for i in range(n_loop):
                flat[(base + i) * 2] = per[i][0]
                flat[(base + i) * 2 + 1] = per[i][1]
            base += n_loop
        if base == len(me.loops):
            uv.data.foreach_set("uv", flat)
    obj = bpy.data.objects.new(name, me)
    coll.objects.link(obj)
    bm.free()
    return obj


def tri_count(obj):
    me = obj.data
    if me is None or not hasattr(me, "polygons"):
        return 0
    return sum(max(0, len(p.vertices) - 2) for p in me.polygons)


def collection_tri_count(coll, lod=None, visible_only=False):
    total = 0
    for obj in coll.all_objects:
        if obj.type != "MESH":
            continue
        if lod is not None and "_LOD" in obj.name and not obj.name.endswith(f"_LOD{lod}"):
            continue
        if visible_only and obj.hide_render:
            continue
        total += tri_count(obj)
    return total


def set_object_lod_visibility(coll, level=1):
    for obj in coll.all_objects:
        if "_LOD" in obj.name:
            lod = obj.name.rsplit("_LOD", 1)[1][:1]
            obj.hide_viewport = lod != str(level)


# ----------------------------------------------------------------------------- sun geometry (QA-02-7)
# The golden-hour sun agreed with lighting. At el 7.4 deg a 30 m crown throws a 230 m shadow, so any tall tree
# up-sun of a colonnade wing puts it in shade: this is the geometry behind QA-02-7, and env_trees.shadow_relief
# uses it to keep the wing faces lit.
SUN_AZ, SUN_EL = 118.5, 7.4
CROWN_R = {"cypress_column": 0.20, "redwood": 0.22, "cypress": 0.34, "pine": 0.36, "eucalyptus": 0.34,
           "willow": 0.45, "broadleaf": 0.42}
ARC_CENTRE = (0.0, 52.0)          # the wings are arcs struck from here (env_backdrop.ARC_CENTRE)


def sun_vector(az=SUN_AZ, el=SUN_EL):
    """Unit vector pointing FROM the scene TOWARD the sun. Azimuth is degrees clockwise from north; in this
    project's world north is -X and east is +Y (CLAUDE.md)."""
    a, e = math.radians(az), math.radians(el)
    return (-math.cos(a) * math.cos(e), math.sin(a) * math.cos(e), math.sin(e))


def crown_ellipsoid(species, x, y, h, base_z=-0.5):
    """(centre, radii) of the crown blob used for sun-occlusion tests. Crowns run 0.35 H .. 1.02 H."""
    r = CROWN_R.get(species, 0.35) * h
    z0, z1 = base_z + 0.35 * h, base_z + 1.02 * h
    return (x, y, 0.5 * (z0 + z1)), (r, r, 0.5 * (z1 - z0))


def ray_hits_ellipsoid(origin, d, centre, radii, tmin=0.5):
    """Distance along d at which the ray enters the ellipsoid, or None."""
    ox = (origin[0] - centre[0]) / radii[0]
    oy = (origin[1] - centre[1]) / radii[1]
    oz = (origin[2] - centre[2]) / radii[2]
    dx, dy, dz = d[0] / radii[0], d[1] / radii[1], d[2] / radii[2]
    a = dx * dx + dy * dy + dz * dz
    b = 2.0 * (ox * dx + oy * dy + oz * dz)
    c = ox * ox + oy * oy + oz * oz - 1.0
    disc = b * b - 4 * a * c
    if disc < 0 or a < 1e-12:
        return None
    s = math.sqrt(disc)
    for t in sorted(((-b - s) / (2 * a), (-b + s) / (2 * a))):
        if t > tmin:
            return t
    return None


def wing_samples(colonnade_polys, heights=(6.0, 12.0, 17.0), step=4.0):
    """Sample points on the lagoon-facing (inner) face of each colonnade wing: [(wing_index, x, y, z), ...].

    The wings are arcs about ARC_CENTRE; the face that carries the composition in ref 169 is the one turned
    toward that centre, so ring points inside the ring's median radius are kept.
    """
    cx, cy = ARC_CENTRE
    out = []
    for wi, poly in enumerate(colonnade_polys[:2]):
        ring = resample_polyline(ensure_ccw(poly), step, closed=True)
        rads = sorted(math.hypot(x - cx, y - cy) for (x, y) in ring)
        med = rads[len(rads) // 2]
        for (x, y) in ring:
            if math.hypot(x - cx, y - cy) <= med:
                for z in heights:
                    out.append((wi, x, y, z))
    return out


def shadowed_fraction(samples, trees, az=SUN_AZ, el=SUN_EL, base_z=-0.5):
    """(per (wing, z) counts, {tree index: samples it shadows}) for trees given as (species, x, y, h, note)."""
    s = sun_vector(az, el)
    blobs = [crown_ellipsoid(t[0], t[1], t[2], max(0.5, t[3]), base_z) for t in trees]
    alive = [t[3] > 0.1 for t in trees]
    per, blockers = {}, {}
    for (wi, x, y, z) in samples:
        o = (x, y, z)
        hit = None
        for i, (c, r) in enumerate(blobs):
            if not alive[i]:
                continue
            if (trees[i][1] - x) * s[0] + (trees[i][2] - y) * s[1] < -2.0:
                continue                                     # caster must be up-sun of the sample
            if ray_hits_ellipsoid(o, s, c, r) is not None:
                hit = i
                break
        tot, sh = per.get((wi, z), (0, 0))
        per[(wi, z)] = (tot + 1, sh + (1 if hit is not None else 0))
        if hit is not None:
            blockers[hit] = blockers.get(hit, 0) + 1
    return per, blockers


# ----------------------------------------------------------------------------- the colonnade gallery walk
# LIGHT r14's flythrough walks the colonnade on the arc ARCH strikes its two column rows about
# (`arch_params.COL_ARC_CENTER` / `COL_ARC_R`), at eye z = COLONNADE_GROUND_Z + 1.15.  Geometry, all of it from
# arch_params so it cannot drift:
#     rows            R +- COL_ROW_SPACING / 2          (117.4 +- 2.25)
#     shaft diameter  COLONNADE_D                       (1.7 at the base)
#     clear width     COL_ROW_SPACING - COLONNADE_D     = 2.80 m, i.e. +-1.40 m about the centreline
#     structure       |r - R| <= (COL_ROW_SPACING + COLONNADE_D) / 2 = 3.10 m
# GALLERY_KEEPOUT is the radial band no ENV object may be planted in: the structure plus 1.0 m, so a crown of any
# size still leaves the outer column face clear and the walk's 2.80 m is never entered.  Until round 9 the
# colonnade exclusion was the OSM roof polygon (`COLONNADE_ROOFS`), which is NOT the modelled arc: over the middle
# of the south wing the polygon's outer edge falls INSIDE R, so "plant 2.8 m outside the footprint" put shrubs on
# the gallery floor (LIGHT r14: ENV_shrub_pitto1_1107 at 1.45 m from the centreline).
GALLERY_KEEPOUT = 4.1        # m from the gallery centreline; = 3.10 structure + 1.0 margin (rounded)


def colonnade_wings():
    """`[(name, (cx, cy), R, th0, sgn, arc_length_m)]` - `arch_build.Wing`'s own arithmetic, re-derived here from
    `arch_params` (never a copy of the angles: ARCH moves the pylons and the wing spans move with them)."""
    try:
        import arch_params as AP
    except Exception:                                    # noqa: BLE001
        return []
    cx, cy = AP.COL_ARC_CENTER
    R = AP.COL_ARC_R
    out = []
    for name, spec in AP.WINGS.items():
        s0, s1 = spec["start"], spec["pylon"]
        th0 = math.atan2(s0[1] - cy, s0[0] - cx)
        th1 = math.atan2(s1[1] - cy, s1[0] - cx)
        d = th1 - th0
        while d > math.pi:
            d -= 2 * math.pi
        while d < -math.pi:
            d += 2 * math.pi
        out.append((name, (cx, cy), R, th0, 1 if d > 0 else -1, abs(d) * R))
    return out


def colonnade_walk_points(step=2.0, pad=0.0):
    """Points on the gallery centreline every `step` m: `(x, y, wing_name, s)`.  `pad` extends the span past both
    ends of the wing (the pylon cluster sits at s = L + COL_CLUSTER_PAIR / 2)."""
    out = []
    for name, (cx, cy), R, th0, sgn, arc in colonnade_wings():
        s = -pad
        while s <= arc + pad + 1e-6:
            th = th0 + sgn * s / R
            out.append((cx + R * math.cos(th), cy + R * math.sin(th), name, s))
            s += step
    return out


def gallery_offset(x, y, pad=6.0):
    """Radial distance |r - R| of (x, y) from the gallery centreline of the nearest wing it stands beside, or
    `None` when the point is past either end of both wings (+- `pad` m of arc)."""
    best = None
    for _name, (cx, cy), R, th0, sgn, arc in colonnade_wings():
        r = math.hypot(x - cx, y - cy)
        if r < 1e-6:
            continue
        d = (math.atan2(y - cy, x - cx) - th0) * sgn
        while d > math.pi:
            d -= 2 * math.pi
        while d < -math.pi:
            d += 2 * math.pi
        s = d * R
        if -pad <= s <= arc + pad:
            off = abs(r - R)
            best = off if best is None else min(best, off)
    return best


def gallery_clear(x, y, keep=GALLERY_KEEPOUT, pad=6.0):
    """True when (x, y) may be planted: it is not inside `keep` m of a colonnade gallery centreline."""
    off = gallery_offset(x, y, pad=pad)
    return off is None or off >= keep
