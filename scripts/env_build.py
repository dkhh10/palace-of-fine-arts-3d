"""Environment builder (Environment specialist). Idempotent: rebuilds collection ENV and saves assets/environment.blend.

    blender --background --python scripts/env_build.py [-- --no-trees --no-backdrop --quick --preview]

Sub-collections: ENV_terrain, ENV_water, ENV_trees (source trees, hidden), ENV_tree_instances, ENV_shrubs,
ENV_backdrop, ENV_extras (rip-rap, birds, lamp posts). World: +Y east (lagoon), -X north, z=0 rotunda floor,
water at common.WATER_Z. All footprints come from reference/plans/site_local.json via common.load_site_local().
"""
import bpy, bmesh, sys, os, math, random, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
import env_lib as L
from mathutils import Vector

ARGS = common.script_args()
NO_TREES = "--no-trees" in ARGS
NO_BACKDROP = "--no-backdrop" in ARGS
QUICK = "--quick" in ARGS          # coarser terrain, fewer rocks (for fast iteration)

T0 = time.time()


def log(msg):
    print(f"[env_build {time.time() - T0:6.1f}s] {msg}")


# ----------------------------------------------------------------------------- scene / collections
bpy.ops.wm.read_homefile(use_empty=True)
common.wipe_scene()
scene = common.setup_scene()
ENV = common.rebuild_collection("ENV")
SUB = {}
for name in ("ENV_terrain", "ENV_water", "ENV_trees", "ENV_tree_instances", "ENV_shrubs", "ENV_backdrop", "ENV_extras"):
    SUB[name] = common.get_collection(name, parent=ENV)

SITE = common.load_site_local()
LAGOON = L.ensure_ccw(L.dedupe_poly(SITE["lagoon0"][0]))
ISLETS = [L.ensure_ccw(L.dedupe_poly(SITE["lagoon1"][0])), L.ensure_ccw(L.dedupe_poly(SITE["lagoon2"][0]))]
COLONNADE_ROOFS = [L.ensure_ccw(L.dedupe_poly(p)) for k in ("roof306 h20", "roof310 h19", "roof313 h21", "roof314 h21") for p in SITE[k]]
HALL = L.ensure_ccw(L.dedupe_poly(SITE["b302 h20m"][0]))

LAGOON_FIELD = L.PolyField(LAGOON, cell=8.0)
ISLET_FIELDS = [L.PolyField(p, cell=6.0) for p in ISLETS]
HALL_FIELD = L.PolyField(HALL, cell=10.0)

APRON_R = 31.0          # inside this radius the ARCH platform covers the ground
TERRAIN_HALF = 360.0    # terrain covers +-360 m (720 x 720)


# ----------------------------------------------------------------------------- height field
def terrain_height(x, y):
    """Ground height (m) at world (x, y). Shared by the terrain mesh and by everything scattered on it."""
    for f in ISLET_FIELDS:
        d = f.signed(x, y)
        if d < 0:
            return -0.78 + 0.5 * L.smoothstep(0.0, 9.0, -d) + 0.06 * L.fnoise(x, y, 0.3, 4)
    d = LAGOON_FIELD.signed(x, y)
    if d < 0:                                    # lagoon bed
        depth = min(1.5, 0.3 + 0.16 * (-d))
        return L.WATER_Z - depth + 0.07 * L.fnoise(x, y, 0.15, 3)
    r = math.hypot(x, y)
    base = -0.45 + 0.10 * L.fnoise(x, y, 0.012, 1) + 0.04 * L.fnoise(x, y, 0.06, 2)
    pen = L.smoothstep(62.0, 46.0, r)            # 1 on the peninsula (lawn a bit lower there)
    base = base * (1 - pen) + (-0.6 + 0.03 * L.fnoise(x, y, 0.08, 5)) * pen
    if HALL_FIELD.signed(x, y) < 0:              # the hall stands on a slab at lawn level
        base = -0.4
    bank = L.smoothstep(0.0, 4.5, d)
    return L.SHORE_Z + (base - L.SHORE_Z) * bank


def on_ground(x, y, dz=0.0):
    return (x, y, terrain_height(x, y) + dz)


# ----------------------------------------------------------------------------- paths
def build_path_network():
    """Polylines (world coords) of the main gravel/asphalt paths, from the satellite tile and the OSM shore."""
    paths = []
    # 1. shore loop: 7 m outside the water, skipping the rotunda peninsula and the colonnade fronts
    loop = L.offset_polygon(LAGOON, 7.0)
    loop = L.smooth_polyline(loop, 2, closed=True)
    keep = []
    for (x, y) in loop:
        r = math.hypot(x, y)
        near_col = any(L.point_in_poly(x, y, L.offset_polygon(p, 6.0)) for p in COLONNADE_ROOFS)
        keep.append(r > 52.0 and not near_col and y > -25.0)
    # split into runs
    n = len(loop)
    start = next((i for i in range(n) if not keep[i]), None)
    if start is None:
        paths.append(loop + [loop[0]])
    else:
        run = []
        for k in range(1, n + 1):
            i = (start + k) % n
            if keep[i]:
                run.append(loop[i])
            elif run:
                paths.append(run)
                run = []
        if run:
            paths.append(run)
    paths = [p for p in paths if len(p) >= 4]
    # 2. spurs from the colonnade ends (pylons) to the shore loop
    paths.append([(-104.0, 4.0), (-98.0, 14.0), (-90.0, 26.0)])
    paths.append([(100.0, 34.0), (104.0, 44.0), (106.0, 56.0)])
    # 3. path behind the colonnades (between colonnade and hall), one per wing
    for wing, sign in (("roof306 h20", 1), ("roof310 h19", -1)):
        pts = []
        for t in range(0, 11):
            a = math.radians(-160 + t * 7) if sign > 0 else math.radians(110 + t * 6)
            cx, cy, rr = 0.0, 52.0, 97.0
            pts.append((cx + rr * math.sin(a) * (1 if sign > 0 else 1), cy + rr * math.cos(a)))
        pts = [(p[0], p[1]) for p in pts if HALL_FIELD.signed(p[0], p[1]) > 2.0]
        if len(pts) >= 3:
            paths.append(pts)
    # 4. path from the rotunda west door to the hall and along the lawns on the east shore
    paths.append([(-2.0, -33.0), (-2.0, -46.0), (-6.0, -62.0)])
    paths.append([(-40.0, 112.0), (-30.0, 132.0), (-20.0, 150.0)])
    paths.append([(60.0, 116.0), (75.0, 130.0), (92.0, 150.0)])
    return [L.resample_polyline(L.smooth_polyline(p, 1, closed=False), 4.0) for p in paths]


# ----------------------------------------------------------------------------- terrain
def build_terrain():
    log("terrain: grid + constraints")
    coll = SUB["ENV_terrain"]
    paths = build_path_network()
    path_width = 3.0
    path_fields = [L.PolyField(p, cell=8.0, closed=False) for p in paths]
    ribbons = []
    for p in paths:
        ribbons += L.ribbon_polygons(p, path_width)
    # grid points, three resolutions
    pts = []
    step_in = 4.0 if QUICK else 2.5
    step_mid = 8.0 if QUICK else 6.0
    step_out = 20.0
    rnd = random.Random(7)

    def zone(x, y):
        r = math.hypot(x, y - 40.0)
        return 0 if r < 175 else (1 if r < 300 else 2)

    for zi, step in enumerate((step_in, step_mid, step_out)):
        n = int(TERRAIN_HALF / step)
        for i in range(-n, n + 1):
            for j in range(-n, n + 1):
                x, y = i * step, j * step
                if zone(x, y) != zi:
                    continue
                jit = 0.3 * step
                pts.append((x + rnd.uniform(-jit, jit), y + rnd.uniform(-jit, jit)))
    # extra points in the lagoon and along the bank for the bed slope
    for (x, y) in L.resample_polyline(L.offset_polygon(LAGOON, -1.2), 3.0, closed=True):
        pts.append((x, y))
    for (x, y) in L.resample_polyline(L.offset_polygon(LAGOON, -4.0), 5.0, closed=True):
        pts.append((x, y))
    for (x, y) in L.resample_polyline(L.offset_polygon(LAGOON, 1.5), 3.0, closed=True):
        pts.append((x, y))
    apron = [(APRON_R * math.cos(a), APRON_R * math.sin(a)) for a in [k * 2 * math.pi / 72 for k in range(72)]]
    constraints = [LAGOON] + ISLETS + [L.offset_polygon(p, 2.0) for p in COLONNADE_ROOFS] + [apron] + ribbons + [HALL]
    # keep points away from the constraint edges (CDT epsilon issues) - cheap filter near the lagoon only
    pts = [p for p in pts if abs(LAGOON_FIELD.dist(p[0], p[1])) > 0.6]
    log(f"terrain: {len(pts)} grid points, {len(constraints)} constraint polygons")
    verts2d, tris = L.cdt_triangulate(pts, constraints)
    log(f"terrain: CDT {len(verts2d)} verts {len(tris)} tris; heights")
    heights = [terrain_height(x, y) for (x, y) in verts2d]
    verts = [(x, y, z) for (x, y), z in zip(verts2d, heights)]
    # face materials
    m_lawn, m_soil, m_gravel = L.mat("MAT_lawn"), L.mat("MAT_soil"), L.mat("MAT_gravel_path")
    mats = [m_lawn, m_soil, m_gravel]
    col_exp = [L.offset_polygon(p, 2.0) for p in COLONNADE_ROOFS]
    face_mat = []
    for (a, b, c) in tris:
        cx = (verts2d[a][0] + verts2d[b][0] + verts2d[c][0]) / 3
        cy = (verts2d[a][1] + verts2d[b][1] + verts2d[c][1]) / 3
        if any(L.point_in_poly(cx, cy, p) for p in ISLETS):
            face_mat.append(0)
        elif L.point_in_poly(cx, cy, LAGOON):
            face_mat.append(1)
        elif math.hypot(cx, cy) < APRON_R + 0.5 or any(L.point_in_poly(cx, cy, p) for p in col_exp):
            face_mat.append(2)
        elif any(f.dist(cx, cy) < path_width / 2 + 0.05 for f in path_fields):
            face_mat.append(2)
        elif L.point_in_poly(cx, cy, HALL):
            face_mat.append(2)
        else:
            face_mat.append(0)
    obj = L.mesh_from_tris("ENV_terrain_ground", verts, tris, coll, mats, face_mat, smooth=True)
    # split the bed into its own object so the lead can hide it / the water shader can find it
    log(f"terrain: mesh {L.tri_count(obj)} tris")
    # soil beds on the peninsula and the islet: handled by shrub scatter (soil material patches under shrubs)
    return obj, paths


# ----------------------------------------------------------------------------- water
def build_water():
    log("water")
    coll = SUB["ENV_water"]
    pts = []
    # interior lattice so the surface has some density for shader displacement / reflections
    step = 8.0
    xs = [p[0] for p in LAGOON]
    ys = [p[1] for p in LAGOON]
    x = min(xs)
    while x < max(xs):
        y = min(ys)
        while y < max(ys):
            if LAGOON_FIELD.signed(x, y) < -1.0:
                pts.append((x, y))
            y += step
        x += step
    verts2d, tris = L.cdt_triangulate(pts, [LAGOON] + ISLETS)
    keep = []
    for (a, b, c) in tris:
        cx = (verts2d[a][0] + verts2d[b][0] + verts2d[c][0]) / 3
        cy = (verts2d[a][1] + verts2d[b][1] + verts2d[c][1]) / 3
        if L.point_in_poly(cx, cy, LAGOON) and not any(L.point_in_poly(cx, cy, p) for p in ISLETS):
            keep.append((a, b, c))
    verts = [(x, y, L.WATER_Z) for (x, y) in verts2d]
    obj = L.mesh_from_tris("ENV_lagoon_water", verts, keep, coll, [L.mat("MAT_water_lagoon")], smooth=True)
    # simple planar UVs (10 m tiles) for the water shader
    me = obj.data
    uv = me.uv_layers.new(name="UVMap")
    for loop in me.loops:
        v = me.vertices[loop.vertex_index].co
        uv.data[loop.index].uv = (v.x / 10.0, v.y / 10.0)
    log(f"water: {L.tri_count(obj)} tris")
    return obj


# ----------------------------------------------------------------------------- rip-rap
def build_riprap():
    log("rip-rap")
    coll = SUB["ENV_extras"]
    rocks = [L.make_rock_mesh(f"ENV_rock_src_{i}", radius=0.5, seed=100 + i, subdiv=1) for i in range(6)]
    m_rock = L.mat("MAT_rock_riprap")
    rnd = random.Random(11)
    step = 1.3 if QUICK else 0.8
    shore = L.resample_polyline(LAGOON, step, closed=True)
    sectors = {}
    for i, (x, y) in enumerate(shore):
        # local outward normal (approx) from the neighbouring points
        p0 = Vector(shore[i - 1])
        p1 = Vector(shore[(i + 1) % len(shore)])
        d = (p1 - p0)
        if d.length < 1e-6:
            continue
        d.normalize()
        outward = Vector((d.y, -d.x))     # CCW polygon: right-hand side is outside (land)
        for row, (off, zc, smin, smax) in enumerate(((-0.15, L.WATER_Z + 0.05, 0.35, 0.75), (0.7, L.SHORE_Z - 0.25, 0.3, 0.6))):
            if row == 1 and rnd.random() < 0.35:
                continue
            px = x + outward.x * (off + rnd.uniform(-0.25, 0.25)) + rnd.uniform(-0.2, 0.2) * d.x
            py = y + outward.y * (off + rnd.uniform(-0.25, 0.25)) + rnd.uniform(-0.2, 0.2) * d.y
            s = rnd.uniform(smin, smax)
            pz = zc + rnd.uniform(-0.12, 0.12) + s * 0.25
            ang = int((math.degrees(math.atan2(y, x)) + 360) % 360) // 45
            sectors.setdefault(ang, []).append((rnd.randrange(len(rocks)), ((px, py, pz), rnd.uniform(0, 6.283), (s * rnd.uniform(0.8, 1.3), s, s * rnd.uniform(0.6, 1.0)))))
    # islet shore too
    for isl in ISLETS[:1]:
        for (x, y) in L.resample_polyline(isl, 1.0, closed=True):
            s = rnd.uniform(0.3, 0.6)
            sectors.setdefault(9, []).append((rnd.randrange(len(rocks)), ((x + rnd.uniform(-0.3, 0.3), y + rnd.uniform(-0.3, 0.3), L.WATER_Z + 0.1 + s * 0.2), rnd.uniform(0, 6.283), s)))
    total = 0
    for ang, items in sorted(sectors.items()):
        for ri in range(len(rocks)):
            tr = [t for (k, t) in items if k == ri]
            if not tr:
                continue
            obj = L.join_instances(f"ENV_riprap_s{ang:02d}_r{ri}", rocks[ri], tr, coll, m_rock)
            total += L.tri_count(obj)
    for me in rocks:
        bpy.data.meshes.remove(me)
    log(f"rip-rap: {total} tris")


# ----------------------------------------------------------------------------- shrubs and reeds
def make_shrub_mesh(name, seed, radius=0.8, height=0.9, cards=14):
    """Low-poly shrub: a squashed noisy icosphere plus crossed leaf cards."""
    rnd = random.Random(seed)
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=2, radius=radius * 0.72)
    for v in bm.verts:
        n = L.noise.noise(v.co * 2.6 + Vector((seed, seed, 0)))
        v.co = v.co * (1.0 + 0.28 * n)
        v.co.z = v.co.z * (height / radius) * 0.55 + height * 0.45
    verts = [v.co.copy() for v in bm.verts]
    faces = [[v.index for v in f.verts] for f in bm.faces]
    bm.free()
    for c in range(cards):
        a = rnd.uniform(0, math.pi)
        r = radius * rnd.uniform(0.3, 1.0)
        cx, cy = math.cos(a * 2) * r * 0.5, math.sin(a * 2) * r * 0.5
        w, h = radius * rnd.uniform(0.7, 1.2), height * rnd.uniform(0.9, 1.4)
        dx, dy = math.cos(a) * w / 2, math.sin(a) * w / 2
        base = len(verts)
        verts += [Vector((cx - dx, cy - dy, 0.0)), Vector((cx + dx, cy + dy, 0.0)), Vector((cx + dx, cy + dy, h)), Vector((cx - dx, cy - dy, h))]
        faces.append([base, base + 1, base + 2, base + 3])
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], faces)
    me.update()
    uv = me.uv_layers.new(name="UVMap")
    for poly in me.polygons:
        for k, li in enumerate(poly.loop_indices):
            uv.data[li].uv = ((0, 0), (1, 0), (1, 1), (0, 1))[k % 4]
    for p in me.polygons:
        p.use_smooth = True
    return me


def make_reed_mesh(name, seed, height=1.1, blades=9):
    rnd = random.Random(seed)
    verts, faces = [], []
    for b in range(blades):
        a = rnd.uniform(0, math.pi)
        w = rnd.uniform(0.35, 0.7)
        h = height * rnd.uniform(0.7, 1.3)
        ox, oy = rnd.uniform(-0.25, 0.25), rnd.uniform(-0.25, 0.25)
        dx, dy = math.cos(a) * w / 2, math.sin(a) * w / 2
        base = len(verts)
        verts += [(ox - dx, oy - dy, 0.0), (ox + dx, oy + dy, 0.0), (ox + dx * 0.6, oy + dy * 0.6, h), (ox - dx * 0.6, oy - dy * 0.6, h)]
        faces.append([base, base + 1, base + 2, base + 3])
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    uv = me.uv_layers.new(name="UVMap")
    for poly in me.polygons:
        for k, li in enumerate(poly.loop_indices):
            uv.data[li].uv = ((0, 0), (1, 0), (1, 1), (0, 1))[k % 4]
    return me


def build_shrubs():
    log("shrubs + reeds")
    coll = SUB["ENV_shrubs"]
    rnd = random.Random(23)
    shrubs = [make_shrub_mesh(f"ENV_shrub_src_{i}", 300 + i, radius=rnd.uniform(0.6, 1.1), height=rnd.uniform(0.6, 1.3)) for i in range(5)]
    reeds = [make_reed_mesh(f"ENV_reed_src_{i}", 400 + i) for i in range(3)]
    m_shrub, m_reed = L.mat("MAT_shrub"), L.mat("MAT_reeds")
    placements = {"pen": [], "shore": [], "col": [], "islet": []}
    reed_pl = []

    def land_ok(x, y, min_shore=0.0, max_shore=1e9):
        d = LAGOON_FIELD.signed(x, y)
        if d < min_shore or d > max_shore:
            return False
        if math.hypot(x + 16.0, y - 113.9) < 24.0:      # hero camera foreground stays clean (user image, ref 169)
            return False
        if math.hypot(x, y) < APRON_R + 1.0:
            return False
        if any(L.point_in_poly(x, y, L.offset_polygon(p, 2.5)) for p in COLONNADE_ROOFS):
            return False
        if HALL_FIELD.signed(x, y) < 1.0:
            return False
        return True

    # peninsula: a shrub belt along the rotunda island shore (dense on the lagoon side)
    for _ in range(900):
        a = rnd.uniform(-math.pi, math.pi)
        r = rnd.uniform(APRON_R + 1.5, 47.0)
        x, y = r * math.cos(a), r * math.sin(a)
        if not land_ok(x, y, 0.9, 7.0):
            continue
        east = L.smoothstep(-0.4, 0.7, y / max(1e-6, r))
        if rnd.random() > 0.35 + 0.55 * east:
            continue
        placements["pen"].append(((x, y, terrain_height(x, y) - 0.05), rnd.uniform(0, 6.283), rnd.uniform(0.9, 1.9)))
    # shore belt around the rest of the lagoon (between water and path)
    for (x, y) in L.resample_polyline(L.offset_polygon(LAGOON, 2.2), 2.4, closed=True):
        if math.hypot(x, y) < 50 or not land_ok(x, y, 0.8, 6.0):
            continue
        if rnd.random() < 0.45:
            placements["shore"].append(((x + rnd.uniform(-1, 1), y + rnd.uniform(-1, 1), terrain_height(x, y) - 0.05), rnd.uniform(0, 6.283), rnd.uniform(0.7, 1.6)))
        if rnd.random() < 0.7 and math.hypot(x + 16.0, y - 113.9) > 24.0:   # not in front of the hero camera
            rx, ry = x + rnd.uniform(-1.2, 0.6), y + rnd.uniform(-1.2, 0.6)
            reed_pl.append(((rx, ry, terrain_height(rx, ry) - 0.05), rnd.uniform(0, 6.283), rnd.uniform(0.7, 1.4)))
    # foundation planting along the colonnade fronts and the islet
    for p in COLONNADE_ROOFS[:2]:
        for (x, y) in L.resample_polyline(L.offset_polygon(p, 4.5), 3.0, closed=True):
            if land_ok(x, y, 1.0) and rnd.random() < 0.5:
                placements["col"].append(((x, y, terrain_height(x, y) - 0.05), rnd.uniform(0, 6.283), rnd.uniform(0.8, 1.7)))
    for _ in range(120):
        p = ISLETS[0]
        xs = [q[0] for q in p]
        ys = [q[1] for q in p]
        x, y = rnd.uniform(min(xs), max(xs)), rnd.uniform(min(ys), max(ys))
        if L.point_in_poly(x, y, p) and ISLET_FIELDS[0].signed(x, y) < -1.0:
            placements["islet"].append(((x, y, terrain_height(x, y) - 0.05), rnd.uniform(0, 6.283), rnd.uniform(0.8, 1.8)))
    total = 0
    for key, items in placements.items():
        for si in range(len(shrubs)):
            tr = [t for i, t in enumerate(items) if (i % len(shrubs)) == si]
            if tr:
                total += L.tri_count(L.join_instances(f"ENV_shrubs_{key}_{si}", shrubs[si], tr, coll, m_shrub))
    for si in range(len(reeds)):
        tr = [t for i, t in enumerate(reed_pl) if (i % len(reeds)) == si]
        if tr:
            total += L.tri_count(L.join_instances(f"ENV_reeds_{si}", reeds[si], tr, coll, m_reed))
    for me in shrubs + reeds:
        bpy.data.meshes.remove(me)
    log(f"shrubs: {sum(len(v) for v in placements.values())} shrubs, {len(reed_pl)} reed tufts, {total} tris")


# ----------------------------------------------------------------------------- birds
def make_gull_mesh(name, wings_open=False):
    """Very low-poly western gull, ~0.55 m long, origin at the belly."""
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=1, radius=0.12)
    for v in bm.verts:
        v.co.x *= 2.2
        v.co.y *= 1.0
        v.co.z *= 0.9
        v.co.z += 0.11
    head = bmesh.ops.create_icosphere(bm, subdivisions=1, radius=0.06)
    for v in head["verts"]:
        v.co += Vector((0.26, 0.0, 0.2))
    # beak + tail as tiny pyramids
    b0 = bm.verts.new((0.31, 0.0, 0.2))
    b1 = bm.verts.new((0.30, 0.02, 0.18))
    b2 = bm.verts.new((0.30, -0.02, 0.18))
    b3 = bm.verts.new((0.38, 0.0, 0.185))
    for f in ((b0, b1, b3), (b1, b2, b3), (b2, b0, b3)):
        bm.faces.new(f)
    t0 = bm.verts.new((-0.24, 0.05, 0.14))
    t1 = bm.verts.new((-0.24, -0.05, 0.14))
    t2 = bm.verts.new((-0.38, 0.0, 0.17))
    bm.faces.new((t0, t1, t2))
    if wings_open:
        for s in (1, -1):
            w0 = bm.verts.new((0.05, s * 0.08, 0.2))
            w1 = bm.verts.new((-0.1, s * 0.08, 0.2))
            w2 = bm.verts.new((-0.15, s * 0.6, 0.32))
            w3 = bm.verts.new((0.1, s * 0.6, 0.32))
            bm.faces.new((w0, w1, w2, w3))
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    return me


def build_birds():
    log("birds")
    coll = SUB["ENV_extras"]
    rnd = random.Random(31)
    m = L.mat("MAT_bird_white")
    sitting = make_gull_mesh("ENV_gull_src_sit")
    flying = make_gull_mesh("ENV_gull_src_fly", wings_open=True)
    sit_tr, fly_tr = [], []
    # gulls on the peninsula shore rocks (hero view: along the waterline right and left of the rotunda)
    for (x, y) in L.resample_polyline(LAGOON, 1.0, closed=True):
        r = math.hypot(x, y)
        if 33 < r < 49 and y > -5 and rnd.random() < 0.28:
            sit_tr.append(((x + rnd.uniform(-0.4, 0.4), y + rnd.uniform(-0.4, 0.4), L.SHORE_Z + 0.02), rnd.uniform(0, 6.283), rnd.uniform(0.9, 1.1)))
    # floating gulls on the water in front of the rotunda
    for _ in range(20):
        x, y = rnd.uniform(-45, 45), rnd.uniform(50, 100)
        if LAGOON_FIELD.signed(x, y) < -3:
            sit_tr.append(((x, y, L.WATER_Z - 0.06), rnd.uniform(0, 6.283), rnd.uniform(0.9, 1.1)))
    for _ in range(6):
        x, y = rnd.uniform(-60, 60), rnd.uniform(20, 110)
        fly_tr.append(((x, y, rnd.uniform(6, 22)), rnd.uniform(0, 6.283), 1.0))
    L.join_instances("ENV_gulls_sitting", sitting, sit_tr, coll, m)
    L.join_instances("ENV_gulls_flying", flying, fly_tr, coll, m)
    bpy.data.meshes.remove(sitting)
    bpy.data.meshes.remove(flying)
    log(f"birds: {len(sit_tr)} sitting/floating, {len(fly_tr)} flying")


# ----------------------------------------------------------------------------- lamp posts (cheap, along the shore path)
def build_lamp_posts(paths):
    coll = SUB["ENV_extras"]
    m = L.mat("MAT_lamp_post")
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=8, radius1=0.09, radius2=0.06, depth=3.6)
    for v in bm.verts:
        v.co.z += 1.8
    lamp = bmesh.ops.create_icosphere(bm, subdivisions=1, radius=0.22)
    for v in lamp["verts"]:
        v.co.z += 3.8
    me = bpy.data.meshes.new("ENV_lamp_src")
    bm.to_mesh(me)
    bm.free()
    rnd = random.Random(41)
    tr = []
    for p in paths[:2]:
        for (x, y) in L.resample_polyline(p, 28.0):
            tr.append(((x + 2.0 * rnd.uniform(-0.2, 0.2), y, terrain_height(x, y)), 0.0, 1.0))
    if tr:
        L.join_instances("ENV_lamp_posts", me, tr, coll, m)
    bpy.data.meshes.remove(me)


# ----------------------------------------------------------------------------- main
def main():
    terrain, paths = build_terrain()
    build_water()
    build_riprap()
    build_shrubs()
    build_birds()
    build_lamp_posts(paths)
    if not NO_TREES:
        import env_trees
        plan = env_trees.build_all(SUB, terrain_height, LAGOON_FIELD, ISLET_FIELDS, quick=QUICK,
                                   colonnade_polys=COLONNADE_ROOFS, hall_poly=HALL)
        notes = common.DOCS / "environment_notes.md"
        if notes.exists():
            txt = notes.read_text()
            a, b = "<!-- PLAN_TABLE_START -->", "<!-- PLAN_TABLE_END -->"
            if a in txt and b in txt:
                head, rest = txt.split(a, 1)
                _, tail = rest.split(b, 1)
                txt = head + a + "\n" + env_trees.plan_markdown(plan) + "\n" + b + tail
                notes.write_text(txt)
                log("planting plan table written into docs/environment_notes.md")
    if not NO_BACKDROP:
        import env_backdrop
        env_backdrop.build_all(SUB, terrain_height, SITE, HALL)
    # viewport default LOD1, report
    L.set_object_lod_visibility(ENV, 1)
    for lod in (0, 1, 2):
        log(f"ENV tri count at LOD{lod}: {L.collection_tri_count(ENV, lod=lod):,}")
    log(f"objects in ENV: {len(ENV.all_objects)}")
    common.save_blend(common.ASSET_FILES["ENV"])
    if "--preview" in ARGS:
        import env_preview
        env_preview.render(tag="build")


main()
