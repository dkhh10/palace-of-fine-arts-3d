"""Backdrop for the Palace of Fine Arts environment (ENV_backdrop): the exhibition hall massing from OSM `b302` with a
pilastered crescent wall and the big arched entrance facing the rotunda, Marina district houses within ~450 m from
reference/plans/_osm.json (heights from OSM tags), the wooded Presidio ridge to the west/north-west, distant hills,
a far ground plane and a bay-water plane to the north. Everything low poly with library materials by name.
"""
import bpy, bmesh, sys, os, math, random, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
import env_lib as L
from mathutils import Vector

FAR_GROUND_Z = -0.6


def _prism(name, poly, z0, z1, coll, material, smooth=False):
    bm = bmesh.new()
    verts = [bm.verts.new((x, y, z0)) for (x, y) in poly]
    try:
        f = bm.faces.new(verts)
    except ValueError:
        bm.free()
        return None
    bmesh.ops.triangulate(bm, faces=[f])
    geom = bmesh.ops.extrude_face_region(bm, geom=bm.faces[:])
    up = [v for v in geom["geom"] if isinstance(v, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, verts=up, vec=(0, 0, z1 - z0))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    obj = bpy.data.objects.new(name, me)
    coll.objects.link(obj)
    me.materials.append(material)
    return obj


def _box(bm, cx, cy, cz, sx, sy, sz, rot=0.0):
    r = bmesh.ops.create_cube(bm, size=1.0)
    verts = r["verts"]
    c, s = math.cos(rot), math.sin(rot)
    for v in verts:
        x, y, z = v.co.x * sx, v.co.y * sy, v.co.z * sz
        v.co = Vector((cx + c * x - s * y, cy + s * x + c * y, cz + z))
    return verts


# ----------------------------------------------------------------------------- exhibition hall
ARC_CENTRE = Vector((0.0, 52.0))     # DPR: hall and colonnade radii struck from a point on the east side of the lagoon
HALL_Z0, HALL_EAVE, HALL_RISE = -0.4, 15.5, 4.5     # eave 15.5 + curved roof rise 4.5 = 20 m (OSM height)


def _hall_roof_z(x, y, r_mid, hd):
    r = (Vector((x, y)) - ARC_CENTRE).length
    t = (r - r_mid) / max(1e-6, hd)
    return HALL_EAVE + HALL_RISE * max(0.0, 1.0 - t * t)


def build_hall(SUB, hall_poly, hall_field):
    """Exhibition hall from OSM b302: buff stucco walls to a 15.5 m eave with a parapet, a shallow curved roof
    (rise 4.5 m, darker), pilasters every 7 m on the concave east wall, and the east entrance pavilion with the
    tall green double door on the rotunda's west-arch axis (ref 169 through the main arch; ref 022)."""
    coll = SUB["ENV_backdrop"]
    m_wall, m_roof = L.mat("MAT_backdrop_building"), L.mat("MAT_backdrop_roof")
    m_sky, m_door = L.mat("MAT_backdrop_skylight"), L.mat("MAT_backdrop_door_green")
    poly = L.ensure_ccw(hall_poly)
    _prism("ENV_backdrop_hall", poly, HALL_Z0, HALL_EAVE - 0.05, coll, m_wall)
    # curved roof: CDT of the footprint with interior points, parabolic section across the crescent
    rs = [(Vector(p) - ARC_CENTRE).length for p in poly]
    r_min, r_max = min(rs), max(rs)
    r_mid, hd = (r_min + r_max) / 2, (r_max - r_min) / 2
    xs = [p[0] for p in poly]; ys = [p[1] for p in poly]
    pts = []
    step = 6.0
    x = min(xs)
    while x < max(xs):
        y = min(ys)
        while y < max(ys):
            if hall_field.signed(x, y) < -2.0:
                pts.append((x, y))
            y += step
        x += step
    v2, tris = L.cdt_triangulate(pts, [poly])
    keep = [t for t in tris if L.point_in_poly(sum(v2[i][0] for i in t) / 3, sum(v2[i][1] for i in t) / 3, poly)]
    verts = [(x, y, _hall_roof_z(x, y, r_mid, hd)) for (x, y) in v2]
    L.mesh_from_tris("ENV_backdrop_hall_roof", verts, keep, coll, [m_roof], smooth=True)
    # parapet band + pilasters on the concave (east) wall
    bm = bmesh.new()
    n = len(poly)
    count = 0
    win_pl = []
    for i in range(n):
        a, b = Vector(poly[i]), Vector(poly[(i + 1) % n])
        d = b - a
        seg = d.length
        if seg < 1.0:
            continue
        d.normalize()
        nrm = Vector((d.y, -d.x))
        rot = math.atan2(d.y, d.x)
        mid = (a + b) / 2
        _box(bm, mid.x + nrm.x * 0.2, mid.y + nrm.y * 0.2, HALL_EAVE + 0.5, seg + 0.4, 1.0, 1.4, rot)   # parapet
        _box(bm, mid.x + nrm.x * 0.35, mid.y + nrm.y * 0.35, HALL_EAVE - 0.9, seg + 0.3, 1.3, 1.1, rot)  # cornice
        _box(bm, mid.x + nrm.x * 0.25, mid.y + nrm.y * 0.25, 9.0, seg + 0.2, 1.0, 0.55, rot)             # string course
        _box(bm, mid.x + nrm.x * 0.30, mid.y + nrm.y * 0.30, HALL_Z0 + 0.55, seg + 0.2, 1.1, 1.1, rot)   # plinth
        to_origin = (Vector((0.0, 0.0)) - mid).normalized()
        if seg >= 3.0 and nrm.dot(to_origin) > 0.3 and mid.length < 135:
            k = max(1, int(seg / 7.0))
            for j in range(k):
                t = (j + 0.5) / k
                p = a + d * (seg * t) + nrm * 0.4
                _box(bm, p.x, p.y, (HALL_Z0 + HALL_EAVE) / 2, 1.2, 0.8, HALL_EAVE - HALL_Z0, rot)
                count += 1
            # glazed bays halfway between pilasters: they read as window recesses at hero distance
            ts = [0.15, 0.85] if k == 1 else [j / k for j in range(1, k)] + [0.07, 0.93]
            for t in ts:
                if seg < 4.0:
                    continue
                q = a + d * (seg * t) + nrm * 0.18
                win_pl.append(((q.x, q.y, 6.6), (min(3.4, seg / k * 0.55), 0.30, 4.6), rot))
                win_pl.append(((q.x, q.y, 12.0), (min(3.4, seg / k * 0.55), 0.30, 3.0), rot))
    me = bpy.data.meshes.new("ENV_backdrop_hall_detail")
    bm.to_mesh(me); bm.free()
    me.materials.append(m_wall)
    o = bpy.data.objects.new("ENV_backdrop_hall_detail", me)
    coll.objects.link(o)
    if win_pl:
        bmw = bmesh.new()
        for ((wx, wy, wz), (sx, sy, sz), wrot) in win_pl:
            _box(bmw, wx, wy, wz, sx, sy, sz, wrot)
        mew = bpy.data.meshes.new("ENV_backdrop_hall_windows")
        bmw.to_mesh(mew); bmw.free()
        mew.materials.append(m_sky)
        ow = bpy.data.objects.new("ENV_backdrop_hall_windows", mew)
        coll.objects.link(ow)
    # entrance pavilion on the west-arch axis (compass az 262): march from the origin until inside the hall
    az = math.radians(262.0)
    ray = Vector((-math.cos(az), math.sin(az)))
    hit = None
    for r in range(20, 200):
        q = ray * float(r)
        if hall_field.signed(q.x, q.y) < 0:
            hit = q; break
    if hit is None:
        print("[env_backdrop] hall: no axis hit, pavilion skipped")
        return
    # wall segment at the hit point
    best = None
    for i in range(n):
        a, b = Vector(poly[i]), Vector(poly[(i + 1) % n])
        dd = L.seg_dist(hit.x, hit.y, a.x, a.y, b.x, b.y)
        if best is None or dd < best[0]:
            best = (dd, a, b)
    _, a, b = best
    d = (b - a).normalized()
    nrm = Vector((d.y, -d.x))
    if nrm.dot(-hit.normalized()) < 0:
        nrm = -nrm
    rot = math.atan2(d.y, d.x)
    P = hit + nrm * 0.0
    bm = bmesh.new()
    z0, zc = HALL_Z0, 11.0
    # piers, lintel, cornice, parapet
    for sgn in (-1, 1):
        q = P + d * (sgn * 5.5) + nrm * 2.5
        _box(bm, q.x, q.y, (z0 + zc) / 2, 5.0, 5.0, zc - z0, rot)
    q = P + nrm * 2.5
    _box(bm, q.x, q.y, (8.2 + zc) / 2, 6.2, 5.0, zc - 8.2, rot)                 # lintel over the 6 m opening
    _box(bm, q.x, q.y, zc + 0.4, 17.0, 6.2, 0.8, rot)                            # cornice
    _box(bm, q.x - nrm.x * 0.6, q.y - nrm.y * 0.6, zc + 1.4, 16.0, 5.0, 1.2, rot)  # parapet block
    # Aperture seal (carried QA-01-8 / materials note): the 6 m opening between the piers must never be an
    # unfilled hole in the massing - through the rotunda's west arch the hero camera looks straight into it.
    # A full-height backing slab spans wider and taller than the opening, then the reveal (jambs + head + sill)
    # is built in front of it so the doorway still reads as a recess rather than a painted rectangle.
    q2 = P + nrm * 0.9
    _box(bm, q2.x, q2.y, (z0 + 11.4) / 2, 9.0, 0.7, 11.4 - z0, rot)            # backing slab, seals the aperture
    _box(bm, q2.x, q2.y, (z0 + 8.2) / 2, 6.6, 0.6, 8.2 - z0, rot)              # recess back wall (door surround)
    for sgn in (-1, 1):                                                         # jambs
        qj = P + d * (sgn * 2.75) + nrm * 1.7
        _box(bm, qj.x, qj.y, (z0 + 8.2) / 2, 0.9, 2.0, 8.2 - z0, rot)
    qh = P + nrm * 1.7
    _box(bm, qh.x, qh.y, 8.55, 6.6, 2.0, 0.9, rot)                              # head of the reveal
    _box(bm, qh.x, qh.y, z0 + 0.12, 6.6, 2.2, 0.26, rot)                        # threshold
    me = bpy.data.meshes.new("ENV_backdrop_hall_pavilion")
    bm.to_mesh(me); bm.free()
    me.materials.append(m_wall)
    o = bpy.data.objects.new("ENV_backdrop_hall_pavilion", me)
    coll.objects.link(o)
    # the green double door (ref 169): 4.6 x 7.6 m, in the recess
    bm = bmesh.new()
    q3 = P + nrm * 1.25
    _box(bm, q3.x, q3.y, (z0 + 7.6) / 2, 4.6, 0.12, 7.6 - z0, rot)
    me = bpy.data.meshes.new("ENV_backdrop_hall_door")
    bm.to_mesh(me); bm.free()
    me.materials.append(m_door)
    o = bpy.data.objects.new("ENV_backdrop_hall_door", me)
    coll.objects.link(o)
    # skylight strip on the roof behind the pavilion
    bm = bmesh.new()
    q4 = P - nrm * 7.0
    zr = _hall_roof_z(q4.x, q4.y, r_mid, hd)
    _box(bm, q4.x, q4.y, zr + 0.25, 14.0, 3.0, 0.5, rot)
    me = bpy.data.meshes.new("ENV_backdrop_hall_skylight")
    bm.to_mesh(me); bm.free()
    me.materials.append(m_sky)
    o = bpy.data.objects.new("ENV_backdrop_hall_skylight", me)
    coll.objects.link(o)
    print(f"[env_backdrop] hall: {count} pilasters, {len(win_pl)} glazed bays, cornice + string course + plinth, "
          f"curved roof (eave {HALL_EAVE} + rise {HALL_RISE}), pavilion + green door at ({P.x:.1f}, {P.y:.1f})")


# ----------------------------------------------------------------------------- Marina houses
def _oabb(poly):
    """(centre, axis unit vector, half-length along it, half-width across it) of a polygon's best rectangle."""
    best = None
    for i in range(len(poly)):
        ax, ay = poly[(i + 1) % len(poly)][0] - poly[i][0], poly[(i + 1) % len(poly)][1] - poly[i][1]
        n = math.hypot(ax, ay)
        if n < 1e-6:
            continue
        ax, ay = ax / n, ay / n
        us = [x * ax + y * ay for (x, y) in poly]
        vs = [-x * ay + y * ax for (x, y) in poly]
        area = (max(us) - min(us)) * (max(vs) - min(vs))
        if best is None or area < best[0]:
            u0, u1, v0, v1 = min(us), max(us), min(vs), max(vs)
            cu, cv = 0.5 * (u0 + u1), 0.5 * (v0 + v1)
            best = (area, (cu * ax - cv * ay, cu * ay + cv * ax), (ax, ay),
                    0.5 * (u1 - u0), 0.5 * (v1 - v0))
    return best[1:] if best else None


def build_houses(SUB, site):
    """Marina / Presidio backdrop buildings from the OSM extract.

    QA-02-15: round 02 joined every footprint into ONE flat-topped prism with ONE material, so the skyline in cam06
    read as "plain grey boxes". Now each building is its own object - which gives the library material's per-object
    random a per-building hue and value - and carries a pitched roof (gable along the footprint's long axis, hipped
    on the squarer ones) in MAT_backdrop_roof.
    """
    coll = SUB["ENV_backdrop"]
    m_wall = L.mat("MAT_backdrop_building")
    m_roof = L.mat_or("MAT_backdrop_roof", "MAT_backdrop_building")
    path = common.REFERENCE_DIR / "plans" / "_osm.json"
    if not path.exists():
        print("[env_backdrop] no _osm.json, skipping houses")
        return
    data = json.loads(path.read_text())
    LAT, LON = common.LAT, common.LON
    skip_ids = {288371295, 288371306, 288371310, 288371313, 288371314, 288371302, 1104852117}   # the palace itself
    rnd = random.Random(3)
    count = 0
    for w in data["elements"]:
        if w.get("type") != "way" or "building" not in w.get("tags", {}) or not w.get("geometry"):
            continue
        if w["id"] in skip_ids:
            continue
        tags = w["tags"]
        pts = []
        for p in w["geometry"]:
            xe = (p["lon"] - LON) * math.cos(math.radians(LAT)) * 111320.0
            yn = (p["lat"] - LAT) * 110574.0
            pts.append(common.osm_to_world(xe, yn)[:2])
        pts = L.dedupe_poly(pts)
        if len(pts) < 3:
            continue
        cx = sum(p[0] for p in pts) / len(pts)
        cy = sum(p[1] for p in pts) / len(pts)
        if math.hypot(cx, cy) > 460 or math.hypot(cx, cy) < 60:
            continue
        h = tags.get("height")
        try:
            h = float(str(h).replace("m", "").strip()) if h else None
        except ValueError:
            h = None
        if h is None:
            lv = tags.get("building:levels")
            h = float(lv) * 3.2 if lv else rnd.uniform(8.0, 12.0)
        poly = L.ensure_ccw(pts)
        bm = bmesh.new()
        verts = [bm.verts.new((x, y, FAR_GROUND_Z)) for (x, y) in poly]
        try:
            f = bm.faces.new(verts)
        except ValueError:
            bm.free()
            continue
        bmesh.ops.triangulate(bm, faces=[f])
        faces = [fc for fc in bm.faces if all(v in verts for v in fc.verts)]
        geom = bmesh.ops.extrude_face_region(bm, geom=faces)
        up = [v for v in geom["geom"] if isinstance(v, bmesh.types.BMVert)]
        eaves = FAR_GROUND_Z + h + 0.6
        bmesh.ops.translate(bm, verts=up, vec=(0, 0, h + 0.6))
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        me = bpy.data.meshes.new(f"ENV_backdrop_house_{count:03d}")
        bm.to_mesh(me)
        bm.free()
        me.materials.append(m_wall)
        obj = bpy.data.objects.new(me.name, me)
        obj["instance_seed"] = rnd.random()          # the library material's per-object random
        coll.objects.link(obj)
        # pitched roof over the footprint's oriented bounding box (QA-02-15)
        box = _oabb(poly)
        if box:
            (bx, by), (ax, ay), half_l, half_w = box
            if 1.0 < half_w < 26.0 and half_l < 40.0:
                pitch = rnd.uniform(0.32, 0.55)      # 18-29 deg, the Marina norm
                ridge = half_w * pitch
                px, py = -ay, ax                     # across the ridge
                hip = 0.0 if half_l > 1.8 * half_w else half_w * 0.75    # squarer plans get hipped ends
                rb = bmesh.new()
                def V(u, v, z):
                    return rb.verts.new((bx + ax * u + px * v, by + ay * u + py * v, z))
                e00, e01 = V(-half_l, -half_w, eaves), V(half_l, -half_w, eaves)
                e11, e10 = V(half_l, half_w, eaves), V(-half_l, half_w, eaves)
                r0, r1 = V(-half_l + hip, 0.0, eaves + ridge), V(half_l - hip, 0.0, eaves + ridge)
                rb.faces.new((e00, e01, r1, r0))
                rb.faces.new((r0, r1, e11, e10))
                if hip > 0.0:
                    rb.faces.new((e10, e00, r0))
                    rb.faces.new((e01, e11, r1))
                else:
                    rb.faces.new((e00, e10, r0))
                    rb.faces.new((e11, e01, r1))
                bmesh.ops.recalc_face_normals(rb, faces=rb.faces[:])
                rme = bpy.data.meshes.new(f"ENV_backdrop_roof_{count:03d}")
                rb.to_mesh(rme)
                rb.free()
                rme.materials.append(m_roof)
                ro = bpy.data.objects.new(rme.name, rme)
                ro["instance_seed"] = obj["instance_seed"]
                coll.objects.link(ro)
        count += 1
    print(f"[env_backdrop] houses: {count} buildings within 460 m, separate objects with pitched roofs")


# ----------------------------------------------------------------------------- Phase 8d: the hall's tree belt
# ref 169 at 100 % (renders/qa_comparisons/phase8d_hero_wall_viewer_over_ref169.jpg): behind the north colonnade
# the photograph has NO lit wall -- a dark tree belt and deep shade fill every intercolumniation, and the
# exhibition hall shows only as a roof line above it.  We drew a continuous sunlit olive field with 102 dark
# glazed bays across 21 204 hero pixels (docs/briefs/phase8d_analysis.md).  This plants the belt that is
# actually there, on the hall's concave east face, between the hall and the colonnade.
#
# BUDGET.  The backdrop groups sit inside `env_so_far` in export/gate1_set.py, so every triangle added here comes
# out of `tree_allow` and can re-cut the near/far tree split.  The slack is near_tris_budget 398 894 -
# near_tris_used 391 908 = 6 986 triangles; the cheapest tree that could be pulled into the near list costs
# 12 892.  Staying at or under 6 986 keeps near 20 / far 127 byte-identical with CLASS_BUDGET["ENV"] untouched at
# 902 000 and no impostor re-bake.  BELT_TRI_CAP is that number; the planter stops when it is reached.
BELT_TRI_CAP = 6986


def build_hall_belt(SUB, hall_poly, hall_field, terrain_height, colonnade_polys=()):
    """A canopy belt along the hall's concave east face: 80-tri lobed crowns (env_city's far-canopy mesh) in
    MAT_backdrop_forest, so it joins the existing backdrop_forest export group and adds no new group.

    Measured placement (docs/briefs/phase8d_analysis.md + the Gate 1 geometry): the hall's east face stands at
    r = 47.8-110.8 m from the rotunda and its nearest patch is x -17.5..34.2, y -54.6..-43.8, z -0.4..16.7.  The
    belt stands 5-11 m in front of that face -- against the hall, not out in the palace grounds -- with the offset
    alternating so the silhouette has depth, and every crown is tested against the hall footprint and the
    colonnade roof polygons before it is planted.  One pass, closest-packed: the screen has to be continuous or
    the wall shows between the crowns exactly as it shows between the columns today.  Each crown is placed by its
    own measured z extent: underside 0.25-0.90 m below the local ground (no floating crowns, no trunks to pay for)
    and top 11-16 m above it, hard-capped at the hall's 15.7 m cornice line in world z."""
    import env_city
    coll = SUB["ENV_backdrop"]
    m_forest = L.mat("MAT_backdrop_forest")
    rnd = random.Random(8004)
    src = {k: env_city._canopy_mesh(f"ENV_src_hallbelt_{k}", 80 + k, lobes=4 if k < 3 else 3) for k in range(4)}
    tris_of = {k: len(me.polygons) for k, me in src.items()}
    # measured, not assumed: each crown cluster's own local z extent, so a crown can be placed by its UNDERSIDE and
    # its TOP instead of by its centre (review r2 finding 4 -- the first version put the centre at
    # z0 + rz + 0.6..2.4, which left every crown floating 0.6-2.4 m over the ground with no trunk under it, and let
    # the tallest ones reach ~22 m, over the hall's own 20 m roof crest).  89 trunks are not affordable: the pin
    # leaves 86 triangles.  So the crowns are sunk instead -- a belt of foliage meeting the shrub line, which is
    # what ref 169 shows behind the colonnade, at zero extra triangles.
    zext = {k: (min(v.co.z for v in me.vertices), max(v.co.z for v in me.vertices)) for k, me in src.items()}
    # tops stay under the hall's cornice line in WORLD z, so undulating terrain cannot push one over the roof:
    # HALL_EAVE + 0.2 = 15.7, which is 4.3 m below the 20.0 m roof crest (HALL_EAVE + HALL_RISE) and 1.0 m below
    # the 16.7 m parapet top (HALL_EAVE + 0.5 + 0.7).  ref 169 shows exactly that: the hall roofline above the belt.
    top_limit_world = HALL_EAVE + 0.2
    poly = L.ensure_ccw(hall_poly)
    n = len(poly)

    def blocked(x, y):
        if hall_field.signed(x, y) < 3.0:
            return True                                  # inside the hall, or hard against its wall
        if math.hypot(x, y) < 34.0:
            return True                                  # the rotunda's own platform
        for cp in colonnade_polys:
            for (dx, dy) in ((0.0, 0.0), (3.0, 0.0), (-3.0, 0.0), (0.0, 3.0), (0.0, -3.0)):
                if L.point_in_poly(x + dx, y + dy, cp):
                    return True
        return False

    # even arc-length sampling across the east-facing edges, so the spacing does not jump at every OSM corner
    STEP = 2.8
    items = {k: [] for k in src}
    carry = 0.0
    placed = skipped = 0
    tris = 0
    for i in range(n):
        a, b = Vector(poly[i]), Vector(poly[(i + 1) % n])
        d = b - a
        seg = d.length
        if seg < 1.0:
            carry = 0.0
            continue
        d = d / seg
        nrm = Vector((d.y, -d.x))                        # outward on the concave east face (as build_hall uses it)
        mid = (a + b) / 2
        to_origin = (Vector((0.0, 0.0)) - mid).normalized()
        if nrm.dot(to_origin) <= 0.20 or mid.length > 175.0:
            carry = 0.0
            continue
        u = carry
        while u < seg:
            base = a + d * u
            idx = placed + skipped
            u += STEP
            if tris + max(tris_of.values()) > BELT_TRI_CAP:
                skipped += 1
                continue
            off = (5.4 if idx % 2 else 9.2) + rnd.uniform(-1.1, 1.1)
            p = base + nrm * off + d * rnd.uniform(-1.0, 1.0)
            if blocked(p.x, p.y):
                skipped += 1
                continue
            k = rnd.choice((0, 0, 1, 1, 2, 3))
            rx = rnd.uniform(3.6, 5.6) * (0.80 if k == 3 else 1.0)
            z0 = terrain_height(p.x, p.y)
            sink = rnd.uniform(0.25, 0.90)                       # underside this far BELOW the local ground
            top = min(rnd.uniform(11.0, 16.0), top_limit_world - z0)
            zmin, zmax = zext[k]
            rz = max(1.0, (top + sink) / (zmax - zmin))
            items[k].append(((p.x, p.y, z0 - sink - zmin * rz), rnd.uniform(0.0, math.tau),
                             (rx, rx * rnd.uniform(0.82, 1.18), rz)))
            tris += tris_of[k]
            placed += 1
        carry = u - seg
    nobj = 0
    for k, tr in items.items():
        if not tr:
            continue
        L.join_instances(f"ENV_backdrop_hall_belt_{k}", src[k], tr, coll, m_forest)
        nobj += 1
    for me in src.values():
        if me.users == 0:
            bpy.data.meshes.remove(me)
    print(f"[env_backdrop] hall tree belt: {placed} crowns in {nobj} objects, {tris:,} tris "
          f"(cap {BELT_TRI_CAP:,}, {skipped} sample points rejected)")
    return tris


# ----------------------------------------------------------------------------- Presidio ridge, hills, far ground, bay
def build_landscape(SUB, terrain_height):
    coll = SUB["ENV_backdrop"]
    m_forest = L.mat("MAT_backdrop_forest")
    m_hill = L.mat("MAT_backdrop_hill")
    # Phase 8d: the far field gets MAT_backdrop_lawn, not the palace's MAT_lawn -- see mat_build.build_backdrop_lawn
    m_lawn = L.mat("MAT_backdrop_lawn")
    m_water = L.mat("MAT_water_lagoon")
    # far ground: annulus from the terrain edge (+-360) out to 2.5 km, flat at lawn level
    verts, faces = [], []
    n = 64
    r0, r1 = 355.0, 2600.0
    for k in range(n):
        a = 2 * math.pi * k / n
        verts.append((r0 * math.cos(a) * 1.02, r0 * math.sin(a) * 1.02, FAR_GROUND_Z - 0.05))
    for k in range(n):
        a = 2 * math.pi * k / n
        verts.append((r1 * math.cos(a), r1 * math.sin(a), FAR_GROUND_Z - 0.05))
    for k in range(n):
        faces.append((k, (k + 1) % n, n + (k + 1) % n, n + k))
    # square patch under the terrain (in case the terrain edge is not a circle): the terrain is 720 x 720; a circle
    # of r 355 leaves the corners open, so add a big square below at -0.7
    L.mesh_from_tris("ENV_backdrop_far_ground", verts, faces, coll, [m_lawn], smooth=False)
    zq = FAR_GROUND_Z - 4.0    # well below the lagoon bed (-2.8 m)
    sq = [(-360, -360, zq), (360, -360, zq), (360, 360, zq), (-360, 360, zq)]
    L.mesh_from_tris("ENV_backdrop_under_ground", sq, [(0, 1, 2, 3)], coll, [m_lawn], smooth=False)
    # the bay to the north (-X beyond ~ -450 m: Marina Green then the water) as a flat plane
    bay = [(-2600, -2600, FAR_GROUND_Z + 0.02), (-480, -2600, FAR_GROUND_Z + 0.02), (-480, 2600, FAR_GROUND_Z + 0.02), (-2600, 2600, FAR_GROUND_Z + 0.02)]
    L.mesh_from_tris("ENV_backdrop_bay", bay, [(0, 1, 2, 3)], coll, [m_water], smooth=False)
    # Presidio wooded ridge: west / south-west, 500-1500 m out, 30-90 m high, canopy bumps
    rnd = random.Random(9)

    def ridge(name, az0, az1, r_in, r_out, h_max, bump, mat, seg=40, rings=6):
        vs, fs = [], []
        for j in range(rings + 1):
            t = j / rings
            r = r_in + (r_out - r_in) * t
            for i in range(seg + 1):
                u = i / seg
                az = math.radians(az0 + (az1 - az0) * u)
                x = -r * math.cos(az)
                y = r * math.sin(az)
                # height: bell across the ring (0 at inner and outer edge, h_max in the middle), tapered at the ends
                prof = math.sin(math.pi * t) ** 0.8 * (math.sin(math.pi * u) ** 0.5)
                h = h_max * prof
                h += bump * prof * (0.5 + 0.5 * L.fnoise(x, y, 0.012, 21)) + bump * 0.6 * prof * abs(L.fnoise(x, y, 0.05, 22))
                vs.append((x, y, FAR_GROUND_Z + h))
        for j in range(rings):
            for i in range(seg):
                a = j * (seg + 1) + i
                fs.append((a, a + 1, a + seg + 2, a + seg + 1))
        return L.mesh_from_tris(name, vs, fs, coll, [mat], smooth=True)

    ridge("ENV_backdrop_presidio_ridge", 200, 335, 690, 1600, 45.0, 18.0, m_forest, seg=60, rings=8)
    ridge("ENV_backdrop_presidio_hill_sw", 205, 262, 1200, 2600, 110.0, 25.0, m_forest, seg=40, rings=6)
    # distant hills: Pacific Heights / Russian Hill to the south and south-east, bare hill material
    ridge("ENV_backdrop_hills_south", 120, 200, 1200, 2600, 90.0, 10.0, m_hill, seg=40, rings=5)
    ridge("ENV_backdrop_hills_east", 60, 125, 1600, 2600, 60.0, 8.0, m_hill, seg=30, rings=4)
    # Marin headlands across the bay to the north-west (very far, low)
    ridge("ENV_backdrop_marin", 300, 360, 2000, 2600, 120.0, 20.0, m_hill, seg=30, rings=4)
    print("[env_backdrop] landscape: far ground, bay, presidio ridge, hills")


def build_all(SUB, terrain_height, site, hall_poly, lagoon_field, hall_field=None, colonnade_polys=()):
    """`lagoon_field` is REQUIRED: env_city's keep-out test is built from it, and without it the whole Marina /
    Presidio far field (QA-03-11) would silently not be built at all."""
    if hall_field is None:
        hall_field = L.PolyField(hall_poly, cell=10.0)
    build_hall(SUB, hall_poly, hall_field)
    build_hall_belt(SUB, hall_poly, hall_field, terrain_height, colonnade_polys)
    build_houses(SUB, site)
    build_landscape(SUB, terrain_height)
    import env_city
    env_city.build_all(SUB, terrain_height, lagoon_field, hall_field, colonnade_polys)
