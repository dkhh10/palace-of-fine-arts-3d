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
        to_origin = (Vector((0.0, 0.0)) - mid).normalized()
        if seg >= 3.0 and nrm.dot(to_origin) > 0.3 and mid.length < 135:
            k = max(1, int(seg / 7.0))
            for j in range(k):
                t = (j + 0.5) / k
                p = a + d * (seg * t) + nrm * 0.4
                _box(bm, p.x, p.y, (HALL_Z0 + HALL_EAVE) / 2, 1.2, 0.8, HALL_EAVE - HALL_Z0, rot)
                count += 1
    me = bpy.data.meshes.new("ENV_backdrop_hall_detail")
    bm.to_mesh(me); bm.free()
    me.materials.append(m_wall)
    o = bpy.data.objects.new("ENV_backdrop_hall_detail", me)
    coll.objects.link(o)
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
    q2 = P + nrm * 0.9
    _box(bm, q2.x, q2.y, (z0 + 8.2) / 2, 6.6, 0.6, 8.2 - z0, rot)              # recess back wall (door surround)
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
    print(f"[env_backdrop] hall: {count} pilasters, curved roof, pavilion + door at ({P.x:.1f}, {P.y:.1f})")


# ----------------------------------------------------------------------------- Marina houses
def build_houses(SUB, site):
    coll = SUB["ENV_backdrop"]
    m = L.mat("MAT_backdrop_building")
    path = common.REFERENCE_DIR / "plans" / "_osm.json"
    if not path.exists():
        print("[env_backdrop] no _osm.json, skipping houses")
        return
    data = json.loads(path.read_text())
    LAT, LON = common.LAT, common.LON
    skip_ids = {288371295, 288371306, 288371310, 288371313, 288371314, 288371302, 1104852117}   # the palace itself
    rnd = random.Random(3)
    bm = bmesh.new()
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
        verts = [bm.verts.new((x, y, FAR_GROUND_Z)) for (x, y) in poly]
        try:
            f = bm.faces.new(verts)
        except ValueError:
            continue
        bmesh.ops.triangulate(bm, faces=[f])
        # extrude this face region
        faces = [fc for fc in bm.faces if all(v in verts for v in fc.verts)]
        geom = bmesh.ops.extrude_face_region(bm, geom=faces)
        up = [v for v in geom["geom"] if isinstance(v, bmesh.types.BMVert)]
        bmesh.ops.translate(bm, verts=up, vec=(0, 0, h + 0.6))
        count += 1
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new("ENV_backdrop_houses")
    bm.to_mesh(me)
    bm.free()
    me.materials.append(m)
    o = bpy.data.objects.new("ENV_backdrop_houses", me)
    coll.objects.link(o)
    print(f"[env_backdrop] houses: {count} buildings within 460 m")


# ----------------------------------------------------------------------------- Presidio ridge, hills, far ground, bay
def build_landscape(SUB, terrain_height):
    coll = SUB["ENV_backdrop"]
    m_forest = L.mat("MAT_backdrop_forest")
    m_hill = L.mat("MAT_backdrop_hill")
    m_lawn = L.mat("MAT_lawn")
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

    ridge("ENV_backdrop_presidio_ridge", 200, 335, 700, 1600, 45.0, 18.0, m_forest, seg=60, rings=8)
    ridge("ENV_backdrop_presidio_hill_sw", 205, 262, 1200, 2600, 110.0, 25.0, m_forest, seg=40, rings=6)
    # distant hills: Pacific Heights / Russian Hill to the south and south-east, bare hill material
    ridge("ENV_backdrop_hills_south", 120, 200, 1200, 2600, 90.0, 10.0, m_hill, seg=40, rings=5)
    ridge("ENV_backdrop_hills_east", 60, 125, 1600, 2600, 60.0, 8.0, m_hill, seg=30, rings=4)
    # Marin headlands across the bay to the north-west (very far, low)
    ridge("ENV_backdrop_marin", 300, 360, 2000, 2600, 120.0, 20.0, m_hill, seg=30, rings=4)
    print("[env_backdrop] landscape: far ground, bay, presidio ridge, hills")


def build_all(SUB, terrain_height, site, hall_poly, hall_field=None):
    if hall_field is None:
        hall_field = L.PolyField(hall_poly, cell=10.0)
    build_hall(SUB, hall_poly, hall_field)
    build_houses(SUB, site)
    build_landscape(SUB, terrain_height)
