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
def build_hall(SUB, hall_poly):
    """b302 massing (20 m per OSM; DPR: 45 ft truss + parapet) + pilasters + arched entrance bay facing the rotunda."""
    coll = SUB["ENV_backdrop"]
    m = L.mat("MAT_backdrop_building")
    z0, z1 = -0.4, 19.6
    obj = _prism("ENV_backdrop_hall", hall_poly, z0, z1, coll, m)
    # the hall's east (concave) wall faces the rotunda: pilasters every ~7 m on the segments whose outward normal
    # points toward the rotunda (dot(normal, to_origin) > 0.3)
    bm = bmesh.new()
    poly = L.ensure_ccw(hall_poly)
    n = len(poly)
    count = 0
    arch_done = False
    for i in range(n):
        a, b = Vector(poly[i]), Vector(poly[(i + 1) % n])
        d = b - a
        seg = d.length
        if seg < 3.0:
            continue
        d.normalize()
        nrm = Vector((d.y, -d.x))         # outward for CCW
        mid = (a + b) / 2
        to_origin = (Vector((0.0, 0.0)) - mid).normalized()
        if nrm.dot(to_origin) < 0.3 or mid.length > 130:
            continue
        rot = math.atan2(d.y, d.x)
        k = max(1, int(seg / 7.0))
        for j in range(k):
            t = (j + 0.5) / k
            p = a + d * (seg * t) + nrm * 0.45
            _box(bm, p.x, p.y, (z0 + z1) / 2 + 1.0, 1.4, 0.9, z1 - z0 - 2.0, rot)
            count += 1
        # the big arched entrance bay: on the segment closest to the west axis of the rotunda (y < 0, |x| small)
        if not arch_done and abs(mid.x) < 12 and mid.y < 0:
            arch_done = True
            p = mid + nrm * 1.2
            _box(bm, p.x, p.y, (z0 + 24.0) / 2, 16.0, 2.4, 24.4, rot)        # tall entrance bay with a parapet
            for s in (-1, 1):
                q = mid + d * (s * 9.0) + nrm * 1.8
                _box(bm, q.x, q.y, (z0 + 25.0) / 2, 3.0, 3.6, 25.4, rot)   # flanking piers
    # parapet / cornice band
    for i in range(n):
        a, b = Vector(poly[i]), Vector(poly[(i + 1) % n])
        d = b - a
        seg = d.length
        if seg < 1.0:
            continue
        d.normalize()
        nrm = Vector((d.y, -d.x))
        rot = math.atan2(d.y, d.x)
        mid = (a + b) / 2 + nrm * 0.3
        _box(bm, mid.x, mid.y, z1 + 0.4, seg, 1.2, 1.4, rot)
    me = bpy.data.meshes.new("ENV_backdrop_hall_detail")
    bm.to_mesh(me)
    bm.free()
    me.materials.append(m)
    o = bpy.data.objects.new("ENV_backdrop_hall_detail", me)
    coll.objects.link(o)
    print(f"[env_backdrop] hall: {count} pilasters, arch bay {'placed' if arch_done else 'NOT placed'}")
    return obj


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


def build_all(SUB, terrain_height, site, hall_poly):
    build_hall(SUB, hall_poly)
    build_houses(SUB, site)
    build_landscape(SUB, terrain_height)
