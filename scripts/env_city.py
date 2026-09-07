"""Far field for cam 06 (QA-03-11): the Marina / Cow Hollow street grid, a house field with per-building colour and
roof variation, the Presidio wooded mass with its Main Post / Lombard Gate building rows, Palace Drive and the
street tree lines, and ground-colour variation (lawn / yards / gravel / asphalt) from r = 178 m out to r = 720 m.

Round 03's cam 06 aerial showed a flat olive plane with about five grey boxes past 150 m and no paths - "a game
skybox".  Everything here is far-field, LOD2-class geometry: flat quads for the ground, 12-tri prisms plus a
6-tri roof per house, 40-tri blobs for canopies, all joined into a few dozen objects.

GEOMETRY SOURCES.  All measured from reference/plans/_osm.json (294 building footprints with heights and street
names).  The extract contains no highway ways, so the street grid is derived from the buildings themselves:

* Grid orientation.  Total footprint-edge length binned by edge angle mod 90 deg peaks hard at **8-9 deg**
  (9.6 km of edge at 9 deg, 4.4 km at 8 deg; the next peak is 1.3 km).  GRID_ANG = 8.5 deg.
* Block pitch.  Fitting a line through the centroids of each addr:street group and projecting onto the grid axes
  puts the N-S streets (Lyon / Baker / Broderick) 89 and 136 m apart across, and the E-W streets (Marina Blvd,
  Jefferson, Beach, North Point, Bay, Francisco) 83 / 95 / 103 / 103 / 84 m apart.  Blocks are therefore ~137 m
  across the N-S streets and ~95 m along them - the SF standard 412 x 275 ft block.
* Where buildings exist.  Binning the 294 footprints by azimuth (0 deg = world +X = south, 90 deg = +Y = east)
  gives 24-29 buildings per 15 deg bin between 15 and 165 deg out to r = 350 m (the Marina / Cow Hollow grid),
  0-6 per bin between 250 and 355 deg (the Presidio: scattered institutional buildings addressed on Thornburg,
  Edie, Birmingham, Gorgas, O'Reilly, Letterman and Mason), and nothing at all between 170 and 250 deg (Marina
  Green, Crissy Field, the bay).  RESIDENTIAL_AZ / PRESIDIO_AZ / OPEN_AZ below follow that census.

cam 06 (loc -205, 143, 120 -> origin, 50 mm) puts its horizon crop (rows 0-220 of 720) on the ground between
r = 115 m and r = 413 m at azimuth 275-357 deg plus a sliver at 0-15 deg - that is the Presidio and the southern
end of the grid, which is why the Presidio side gets as much work here as the house field.
"""
import bpy, bmesh, sys, os, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
import env_lib as L
from mathutils import Vector

# ----------------------------------------------------------------------------- the grid
GRID_ANG = math.radians(8.5)
U = Vector((math.cos(GRID_ANG), math.sin(GRID_ANG)))     # along the N-S streets, increasing = south
V = Vector((-math.sin(GRID_ANG), math.cos(GRID_ANG)))    # along the E-W streets, increasing = east

PITCH_U = 95.0        # E-W streets this far apart (across the block's short axis)
PITCH_V = 137.0       # N-S streets this far apart
PHASE_U = -119.0      # Jefferson Street, from the addr:street fit
PHASE_V = 145.0       # Baker Street, ditto

ROAD_W = 11.0         # asphalt carriageway
WALK_W = 3.6          # gravel sidewalk each side

BLOCK_R0 = 178.0      # inside this the Palace grounds terrain owns the ground
ROAD_R0 = 152.0
CITY_R1 = 720.0
FILL_R0 = 320.0       # the OSM extract runs out around here; synthesised houses start outside it
FILL_R1 = 620.0

RESIDENTIAL_AZ = (8.0, 168.0)     # azimuth band (deg, 0 = +X south, 90 = +Y east) of the Marina / Cow Hollow grid
PRESIDIO_AZ = (248.0, 357.0)      # the Presidio: forest with institutional clusters
OPEN_AZ = (168.0, 248.0)          # Marina Green / Crissy Field / the bay shore: lawn, no houses

FAR_GROUND_Z = -0.6


def uv(x, y):
    p = Vector((x, y))
    return p.dot(U), p.dot(V)


def xy(u, v):
    p = U * u + V * v
    return p.x, p.y


def azimuth(x, y):
    return math.degrees(math.atan2(y, x)) % 360.0


def in_az(a, band):
    a0, a1 = band
    return a0 <= a <= a1 if a0 <= a1 else (a >= a0 or a <= a1)


# ----------------------------------------------------------------------------- roads
def palace_drive():
    """The loop road around the Palace grounds - Palace Drive on the north and east, the Bay Street / Presidio
    edge on the south and west.  Used both as a road ribbon and as a tree line."""
    pts = []
    for k in range(48):
        a = 2 * math.pi * k / 48.0
        rx = 205.0 + 22.0 * math.cos(2 * a)
        ry = 178.0 + 16.0 * math.sin(a)
        pts.append((rx * math.cos(a), 24.0 + ry * math.sin(a)))
    return L.smooth_polyline(pts, 2, closed=True)


def road_lines():
    """(polyline, width, kind) for every far-field road.  kind: 'street' (grid) | 'boulevard' (Presidio) | 'drive'."""
    out = []
    ku = int(CITY_R1 / PITCH_U) + 2
    kv = int(CITY_R1 / PITCH_V) + 2
    span = CITY_R1 + 160
    for k in range(-ku, ku + 1):
        u = PHASE_U + k * PITCH_U
        out.append(([xy(u, v) for v in range(int(-span), int(span), 16)], ROAD_W, "street"))
    for k in range(-kv, kv + 1):
        v = PHASE_V + k * PITCH_V
        out.append(([xy(u, v) for u in range(int(-span), int(span), 16)], ROAD_W, "street"))
    # Presidio: Richardson Avenue / Lombard Street out to the south-west, Lincoln Boulevard curving west,
    # a Presidio Boulevard spur and the Main Post approach.  Broad and sparse - the Presidio never was on the grid.
    out.append(([(150.0, -55.0), (250.0, -140.0), (340.0, -235.0), (430.0, -340.0), (520.0, -455.0)], 16.0, "boulevard"))
    out.append(([(115.0, -145.0), (190.0, -250.0), (250.0, -370.0), (300.0, -500.0), (335.0, -640.0)], 12.0, "boulevard"))
    out.append(([(-40.0, -235.0), (60.0, -305.0), (170.0, -360.0), (300.0, -400.0), (430.0, -420.0), (560.0, -428.0)], 12.0, "boulevard"))
    out.append(([(300.0, -110.0), (330.0, -230.0), (350.0, -360.0), (355.0, -500.0)], 9.0, "boulevard"))
    out.append(([(-150.0, -300.0), (-40.0, -425.0), (90.0, -545.0), (230.0, -645.0)], 10.0, "boulevard"))
    out.append((list(palace_drive()) + [palace_drive()[0]], 9.0, "drive"))
    return out


ROADS = road_lines()
PALACE_DRIVE = ROADS[-1][0]


class RoadField:
    """20 m bucket grid of every road corridor, so 'is this spot on a road?' is O(1)."""

    def __init__(self, roads, cell=20.0):
        self.cell = cell
        self.cells = {}
        for pts, w, kind in roads:
            half = w / 2 + WALK_W
            for (x, y) in L.resample_polyline(pts, 6.0):
                for i in range(int((x - half) // cell), int((x + half) // cell) + 1):
                    for j in range(int((y - half) // cell), int((y + half) // cell) + 1):
                        self.cells[(i, j)] = max(self.cells.get((i, j), 0.0), half)

    def on_road(self, x, y, pad=6.0):
        i, j = int(x // self.cell), int(y // self.cell)
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                if (i + di, j + dj) in self.cells:
                    return True
        return False


# ----------------------------------------------------------------------------- ground
def build_ground(SUB, terrain_height, clear):
    """Ground colour variation out to 720 m: block yards (lawn / dry grass / soil), asphalt carriageways and
    gravel sidewalks on every street, the Presidio forest floor and the open Marina Green / Crissy lawn.
    One mesh, five materials."""
    coll = SUB["ENV_backdrop"]
    mats_lib = [L.mat("MAT_lawn"), L.mat("MAT_gravel_path"), L.mat("MAT_backdrop_asphalt"),
                L.mat("MAT_soil"), L.mat("MAT_backdrop_hill")]
    LAWN, GRAVEL, ASPHALT, SOIL, DRY = 0, 1, 2, 3, 4
    rnd = random.Random(1207)

    def zf(x, y, dz=0.0):
        r = math.hypot(x, y)
        if r < 340.0:
            z = terrain_height(x, y)
        elif r < 380.0:
            t = (r - 340.0) / 40.0
            z = terrain_height(x, y) * (1 - t) + FAR_GROUND_Z * t
        else:
            z = FAR_GROUND_Z
        return z + 0.05 + dz + 0.9 * L.smoothstep(300.0, 720.0, r) * L.fnoise(x, y, 0.0035, 61)

    verts, faces, face_mat = [], [], []

    def quad(p0, p1, p2, p3, mi, dz=0.0):
        n = len(verts)
        for (x, y) in (p0, p1, p2, p3):
            verts.append((x, y, zf(x, y, dz)))
        faces.append((n, n + 1, n + 2, n + 3))
        face_mat.append(mi)

    # --- residential blocks, one quad each, tone varied per block
    blocks = []
    ku, kv = int(CITY_R1 / PITCH_U) + 2, int(CITY_R1 / PITCH_V) + 2
    corridor = ROAD_W / 2 + WALK_W
    for i in range(-ku, ku + 1):
        for j in range(-kv, kv + 1):
            u0 = PHASE_U + i * PITCH_U + corridor
            u1 = PHASE_U + (i + 1) * PITCH_U - corridor
            v0 = PHASE_V + j * PITCH_V + corridor
            v1 = PHASE_V + (j + 1) * PITCH_V - corridor
            cx, cy = xy((u0 + u1) / 2, (v0 + v1) / 2)
            r = math.hypot(cx, cy)
            if not (BLOCK_R0 <= r <= CITY_R1) or not clear(cx, cy) or not in_az(azimuth(cx, cy), RESIDENTIAL_AZ):
                continue
            t = rnd.random()
            quad(xy(u0, v0), xy(u1, v0), xy(u1, v1), xy(u0, v1),
                 LAWN if t < 0.45 else (DRY if t < 0.72 else SOIL))
            blocks.append((u0, u1, v0, v1))
    # --- everything else: coarse annulus wedges (Presidio forest floor, Marina Green, Crissy Field)
    seg = 3.0
    rings = ((BLOCK_R0, 300.0), (300.0, 430.0), (430.0, 570.0), (570.0, CITY_R1))
    a = 0.0
    while a < 360.0:
        am = math.radians(a + seg / 2)
        for r0, r1 in rings:
            rm = (r0 + r1) / 2
            cx, cy = rm * math.cos(am), rm * math.sin(am)
            az = azimuth(cx, cy)
            if in_az(az, RESIDENTIAL_AZ) or not clear(cx, cy):
                continue
            if in_az(az, PRESIDIO_AZ):
                mi = DRY if rnd.random() < 0.30 else SOIL
            else:
                mi = DRY if rnd.random() < 0.25 else LAWN
            p = [(rr * math.cos(math.radians(aa)), rr * math.sin(math.radians(aa)))
                 for (rr, aa) in ((r0, a), (r1, a), (r1, a + seg), (r0, a + seg))]
            quad(p[0], p[1], p[2], p[3], mi)
        a += seg
    # --- roads: gravel sidewalk band with the asphalt carriageway laid 1 cm on top
    nroad = 0
    for pts, w, kind in ROADS:
        line = L.resample_polyline(pts, 14.0)
        for i in range(len(line) - 1):
            (ax, ay), (bx, by) = line[i], line[i + 1]
            mx, my = (ax + bx) / 2, (ay + by) / 2
            r = math.hypot(mx, my)
            if not (ROAD_R0 <= r <= CITY_R1) or not clear(mx, my):
                continue
            if kind == "street" and not in_az(azimuth(mx, my), RESIDENTIAL_AZ):
                continue
            d = Vector((bx - ax, by - ay))
            if d.length < 1e-6:
                continue
            d.normalize()
            n = Vector((d.y, -d.x))
            for half, mi, dz in ((w / 2 + WALK_W, GRAVEL, 0.01), (w / 2, ASPHALT, 0.03)):
                quad((ax + n.x * half, ay + n.y * half), (bx + n.x * half, by + n.y * half),
                     (bx - n.x * half, by - n.y * half), (ax - n.x * half, ay - n.y * half), mi, dz)
            nroad += 1
    L.mesh_from_tris("ENV_backdrop_city_ground", verts, faces, coll, mats_lib, face_mat, smooth=False)
    print(f"[env_city] ground: {len(blocks)} blocks, {nroad} road segments, {len(faces)} faces")
    return blocks


# ----------------------------------------------------------------------------- houses
def _box_prism(bm, cx, cy, z0, w, dpt, h, rot):
    c, s = math.cos(rot), math.sin(rot)

    def P(u, v, z):
        return bm.verts.new((cx + c * u - s * v, cy + s * u + c * v, z))
    hw, hd = w / 2, dpt / 2
    a = [P(-hw, -hd, z0), P(hw, -hd, z0), P(hw, hd, z0), P(-hw, hd, z0)]
    b = [P(-hw, -hd, z0 + h), P(hw, -hd, z0 + h), P(hw, hd, z0 + h), P(-hw, hd, z0 + h)]
    bm.faces.new(a[::-1])
    bm.faces.new(b)
    for i in range(4):
        bm.faces.new((a[i], a[(i + 1) % 4], b[(i + 1) % 4], b[i]))
    return z0 + h


def _roof(bm, cx, cy, ze, w, dpt, rot, pitch, hip):
    c, s = math.cos(rot), math.sin(rot)

    def P(u, v, z):
        return bm.verts.new((cx + c * u - s * v, cy + s * u + c * v, z))
    hw, hd = w / 2 + 0.35, dpt / 2 + 0.35
    ridge = hd * pitch
    e00, e01 = P(-hw, -hd, ze), P(hw, -hd, ze)
    e11, e10 = P(hw, hd, ze), P(-hw, hd, ze)
    r0, r1 = P(-hw + hip, 0.0, ze + ridge), P(hw - hip, 0.0, ze + ridge)
    bm.faces.new((e00, e01, r1, r0))
    bm.faces.new((r0, r1, e11, e10))
    if hip > 0.0:
        bm.faces.new((e10, e00, r0))
        bm.faces.new((e01, e11, r1))
    else:
        bm.faces.new((e00, e10, r0))
        bm.faces.new((e11, e01, r1))


def _emit(coll, name, bm, material, seed):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(material)
    o = bpy.data.objects.new(name, me)
    o["instance_seed"] = seed
    coll.objects.link(o)
    return o


def build_fill_houses(SUB, blocks, terrain_height, clear):
    """Synthesised Marina / Cow Hollow houses in the blocks the OSM extract does not reach (r > FILL_R0).

    Lots front the E-W streets, 7.5 m wide (the SF 25 ft lot), 15 m deep, two rows per block.  Adjacent lots are
    emitted in runs of four into one object, so the library material's per-object random gives runs of matching
    colour - which is what a row-house street actually looks like - while the field as a whole carries dozens of
    hues.  Height, roof pitch, hip vs gable, tile vs membrane and the occasional flat-roofed apartment block all
    vary per lot.
    """
    coll = SUB["ENV_backdrop"]
    m_wall = L.mat("MAT_backdrop_building")
    m_roof = L.mat_or("MAT_backdrop_roof", "MAT_backdrop_building")
    m_tile = L.mat("MAT_backdrop_roof_tile")
    rnd = random.Random(4211)
    LOT_W, LOT_D, RUN = 7.5, 15.0, 4
    rot0 = math.atan2(V.y, V.x)
    nh = nobj = 0
    for (u0, u1, v0, v1) in blocks:
        for u_edge, sgn in ((u0, +1), (u1, -1)):
            u_c = u_edge + sgn * LOT_D / 2
            v = v0 + 1.0
            run_w = run_r = run_t = None
            k = 0

            def flush():
                nonlocal run_w, run_r, run_t, nobj
                if run_w is not None:
                    _emit(coll, f"ENV_backdrop_fill_{nobj:03d}", run_w, m_wall, rnd.random())
                    _emit(coll, f"ENV_backdrop_fillroof_{nobj:03d}", run_r, run_t, rnd.random())
                    nobj += 1
                run_w = run_r = run_t = None

            while v + LOT_W < v1:
                cx, cy = xy(u_c, v + LOT_W / 2)
                r = math.hypot(cx, cy)
                if not (FILL_R0 < r < FILL_R1) or not clear(cx, cy):
                    v += LOT_W
                    continue
                if k % RUN == 0:
                    flush()
                    run_w, run_r = bmesh.new(), bmesh.new()
                    run_t = m_tile if rnd.random() < 0.28 else m_roof
                z0 = (terrain_height(cx, cy) if r < 340 else FAR_GROUND_Z) - 0.4
                h = rnd.choice((8.0, 9.5, 9.5, 11.0, 11.0, 12.5, 14.0)) * rnd.uniform(0.94, 1.06)
                rot = rot0 + rnd.uniform(-0.025, 0.025)
                ze = _box_prism(run_w, cx, cy, z0, LOT_W - 0.7, LOT_D, h, rot)
                if rnd.random() >= 0.22:                    # 22 % flat-roofed apartment blocks
                    _roof(run_r, cx, cy, ze, LOT_W - 0.7, LOT_D, rot, rnd.uniform(0.30, 0.58),
                          0.0 if rnd.random() < 0.6 else (LOT_W - 0.7) * 0.34)
                nh += 1
                k += 1
                v += LOT_W
            flush()
    print(f"[env_city] fill houses: {nh} lots in {nobj} run objects (r {FILL_R0:.0f}-{FILL_R1:.0f} m)")
    return nh


# ----------------------------------------------------------------------------- Presidio buildings
#  (name, centre azimuth deg, centre radius m, ranks, per rank, spacing m, (width, depth), height, roof)
PRESIDIO_CLUSTERS = [
    ("lombard_gate", 334.0, 375.0, 3, 8, 26.0, (13.0, 9.0), 8.5, "tile"),
    ("letterman", 350.0, 335.0, 2, 5, 46.0, (30.0, 20.0), 13.0, "roof"),
    ("mainpost_a", 302.0, 505.0, 3, 9, 30.0, (17.0, 10.0), 9.5, "tile"),
    ("mainpost_b", 286.0, 615.0, 2, 8, 32.0, (16.0, 10.0), 9.0, "tile"),
    ("cavalry", 317.0, 600.0, 2, 7, 34.0, (22.0, 11.0), 8.0, "tile"),
    ("crissy", 228.0, 435.0, 1, 6, 42.0, (24.0, 12.0), 7.0, "roof"),
]


def build_presidio_buildings(SUB, clear):
    """The Presidio's institutional rows: Lombard Gate housing, Letterman, the Main Post barracks, the cavalry
    stables and the Crissy Field hangars.  The OSM extract already carries 16 of these (Thornburg / Edie /
    Birmingham / Gorgas / O'Reilly / Letterman / Mason) out to r = 359 m; these continue the same pattern to
    700 m, which is the band cam 06's horizon crop actually looks at.  One object per building, so the library
    material's per-object random gives every one its own stucco tone."""
    coll = SUB["ENV_backdrop"]
    m_wall = L.mat("MAT_backdrop_building")
    m_roof = L.mat_or("MAT_backdrop_roof", "MAT_backdrop_building")
    m_tile = L.mat("MAT_backdrop_roof_tile")
    rnd = random.Random(77)
    n = 0
    for (name, az, rad, ranks, per, spacing, (w, dpt), h, roofkind) in PRESIDIO_CLUSTERS:
        a = math.radians(az)
        cx, cy = rad * math.cos(a), rad * math.sin(a)
        tang = Vector((-math.sin(a), math.cos(a)))
        radial = Vector((math.cos(a), math.sin(a)))
        rot = math.atan2(tang.y, tang.x)
        for ri in range(ranks):
            for j in range(per):
                off_t = (j - (per - 1) / 2) * spacing + rnd.uniform(-3.0, 3.0)
                off_r = (ri - (ranks - 1) / 2) * (dpt + 26.0) + rnd.uniform(-4.0, 4.0)
                x = cx + tang.x * off_t + radial.x * off_r
                y = cy + tang.y * off_t + radial.y * off_r
                if math.hypot(x, y) > CITY_R1 or not clear(x, y):
                    continue
                bw, bh = bmesh.new(), bmesh.new()
                ww = w * rnd.uniform(0.9, 1.1)
                ze = _box_prism(bw, x, y, FAR_GROUND_Z - 0.3, ww, dpt, h * rnd.uniform(0.9, 1.15),
                                rot + rnd.uniform(-0.04, 0.04))
                _roof(bh, x, y, ze, ww, dpt, rot, rnd.uniform(0.26, 0.42), dpt * 0.35)
                s = rnd.random()
                _emit(coll, f"ENV_backdrop_presidio_{name}_{ri}{j}", bw, m_wall, s)
                _emit(coll, f"ENV_backdrop_presidioroof_{name}_{ri}{j}", bh,
                      m_tile if roofkind == "tile" else m_roof, s)
                n += 1
    print(f"[env_city] Presidio buildings: {n} in {len(PRESIDIO_CLUSTERS)} clusters")
    return n


# ----------------------------------------------------------------------------- far canopy
def _canopy_mesh(name, seed=0):
    """~40-tri lumpy blob: one far-field tree crown."""
    bm = bmesh.new()
    try:
        bmesh.ops.create_icosphere(bm, subdivisions=1, radius=1.0)
    except TypeError:
        bmesh.ops.create_icosphere(bm, subdivisions=1, diameter=1.0)
    rnd = random.Random(seed)
    for v in bm.verts:
        v.co = v.co * rnd.uniform(0.70, 1.28)
        v.co.z *= 1.30
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    return me


def build_canopy(SUB, clear):
    """The Presidio woods (190-700 m, west / south-west), wind-shorn cypress on Marina Green and Crissy Field,
    and the Palace Drive / grid street tree lines.  Instanced blobs joined into four objects."""
    coll = SUB["ENV_backdrop"]
    m_forest = L.mat("MAT_backdrop_forest")
    rnd = random.Random(913)
    src = {k: _canopy_mesh(f"ENV_src_canopy_{k}", 40 + k) for k in range(4)}
    rf = RoadField(ROADS)
    groups = {k: [] for k in src}
    n = 0

    def add(x, y, h, slim):
        w = h * slim
        groups[rnd.randrange(4)].append(((x, y, FAR_GROUND_Z + h * 0.54), rnd.uniform(0, 6.283),
                                         (w, w, h * 0.54)))

    # 1. the woods
    a = PRESIDIO_AZ[0]
    while a < PRESIDIO_AZ[1]:
        r = 192.0
        while r < 700.0:
            x0, y0 = r * math.cos(math.radians(a)), r * math.sin(math.radians(a))
            dens = 0.30 + 0.55 * L.smoothstep(185.0, 280.0, r)
            dens *= 0.45 + 0.75 * (0.5 + 0.5 * L.fnoise(x0, y0, 0.010, 71))
            if rnd.random() < dens:
                aa = a + rnd.uniform(-1.7, 1.7)
                rr = r + rnd.uniform(-9.0, 9.0)
                x, y = rr * math.cos(math.radians(aa)), rr * math.sin(math.radians(aa))
                if clear(x, y) and not rf.on_road(x, y):
                    add(x, y, rnd.uniform(9.0, 23.0), rnd.uniform(0.28, 0.46))
                    n += 1
            r += 15.0
        a += 3.2
    # 2. Marina Green / Crissy Field: scattered, never a wood
    for _ in range(110):
        a = rnd.uniform(*OPEN_AZ)
        r = rnd.uniform(200.0, 640.0)
        x, y = r * math.cos(math.radians(a)), r * math.sin(math.radians(a))
        if clear(x, y) and not rf.on_road(x, y):
            add(x, y, rnd.uniform(7.0, 15.0), rnd.uniform(0.35, 0.62))
            n += 1
    # 3. street tree lines: Palace Drive, then every grid street and Presidio boulevard
    for pts, w, kind in ROADS:
        line = L.resample_polyline(pts, 16.0)
        for i in range(len(line) - 1):
            x, y = line[i]
            r = math.hypot(x, y)
            if not (ROAD_R0 - 24.0 < r < CITY_R1) or not clear(x, y):
                continue
            if kind == "street" and not in_az(azimuth(x, y), RESIDENTIAL_AZ):
                continue
            d = Vector((line[i + 1][0] - x, line[i + 1][1] - y))
            if d.length < 1e-6:
                continue
            d.normalize()
            nv = Vector((d.y, -d.x))
            off = w / 2 + WALK_W + 1.4
            for sgn in (-1, 1):
                if rnd.random() > (0.72 if kind == "drive" else 0.55):
                    continue
                ox, oy = x + sgn * nv.x * off, y + sgn * nv.y * off
                if not clear(ox, oy):
                    continue
                add(ox, oy, rnd.uniform(8.0, 15.0), rnd.uniform(0.30, 0.50))
                n += 1
    tris = 0
    nobj = 0
    for k, items in groups.items():
        if not items:
            continue
        o = L.join_instances(f"ENV_backdrop_canopy_{k}", src[k], items, coll, m_forest)
        tris += L.tri_count(o)
        nobj += 1
    for me in src.values():
        if me.users == 0:
            bpy.data.meshes.remove(me)
    print(f"[env_city] far canopy: {n} crowns in {nobj} objects, {tris:,} tris")
    return n


# ----------------------------------------------------------------------------- entry point
def build_all(SUB, terrain_height, lagoon_field, hall_field, colonnade_polys=()):
    """`clear(x, y)` keeps the far field off the lagoon, the hall, the colonnades and the Palace platform."""
    col_fields = [L.PolyField(L.offset_polygon(p, 14.0), cell=8.0) for p in colonnade_polys]

    def clear(x, y):
        if lagoon_field.signed(x, y) < 25.0 or hall_field.signed(x, y) < 22.0:
            return False
        if math.hypot(x, y) < 120.0:
            return False
        for f in col_fields:
            if f.signed(x, y) < 0.0:
                return False
        return True

    blocks = build_ground(SUB, terrain_height, clear)
    build_fill_houses(SUB, blocks, terrain_height, clear)
    build_presidio_buildings(SUB, clear)
    build_canopy(SUB, clear)
