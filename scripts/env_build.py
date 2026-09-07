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
LAGOON_OSM = L.ensure_ccw(L.dedupe_poly(SITE["lagoon0"][0]))
LAGOON = L.jitter_polygon(LAGOON_OSM, step=2.0, amp=0.5, seed=3)     # irregular stone edge (refs 169, 022)
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
    bank_w = 3.0 + 2.0 * L.fnoise(x, y, 0.08, 7)             # 1-5 m wide bank
    bank = L.smoothstep(0.0, max(1.5, bank_w), d)
    shore_z = L.SHORE_Z + 0.12 * L.fnoise(x, y, 0.5, 8)       # +-12 cm irregular edge
    return shore_z + (base - shore_z) * bank


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
    for (x, y) in L.resample_polyline(L.offset_polygon(LAGOON, 3.5), 3.0, closed=True):
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
        elif L.point_in_poly(cx, cy, LAGOON) or LAGOON_FIELD.dist(cx, cy) < 1.4:
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
WATER_BED_CLEARANCE = 0.05     # the water bed sits this far above the terrain bed (no z-fighting)


def build_water():
    """Closed lagoon volume (QA-01-3): a dense surface at WATER_Z, a bed 0.3-1.5 m below it and vertical walls at the
    shore and around both islets, so Cycles' volume absorption in MAT_water_lagoon has something to be inside.
    The surface is triangulated at ~2 m so the material's ripple normals/displacement resolve at hero distance."""
    log("water (closed volume)")
    coll = SUB["ENV_water"]
    step = 4.0 if QUICK else 2.0
    pts = []
    xs = [p[0] for p in LAGOON]
    ys = [p[1] for p in LAGOON]
    x = min(xs)
    while x < max(xs):
        y = min(ys)
        while y < max(ys):
            if LAGOON_FIELD.signed(x, y) < -0.6 and not any(f.signed(x, y) < 0.6 for f in ISLET_FIELDS):
                pts.append((x + 0.35 * L.fnoise(x, y, 0.9, 21), y + 0.35 * L.fnoise(x, y, 0.9, 22)))
            y += step
        x += step
    # the boundary rings are resampled finely so the shoreline reads as a curve, not a chord
    top_ring = L.resample_polyline(LAGOON, 2.0, closed=True)
    islet_rings = [L.resample_polyline(p, 2.0, closed=True) for p in ISLETS]
    verts2d, tris = L.cdt_triangulate(pts, [top_ring] + islet_rings)
    keep = []
    for (a, b, c) in tris:
        cx = (verts2d[a][0] + verts2d[b][0] + verts2d[c][0]) / 3
        cy = (verts2d[a][1] + verts2d[b][1] + verts2d[c][1]) / 3
        if L.point_in_poly(cx, cy, LAGOON) and not any(L.point_in_poly(cx, cy, p) for p in ISLETS):
            keep.append((a, b, c))

    n = len(verts2d)
    top = [(vx, vy, L.WATER_Z) for (vx, vy) in verts2d]
    bed = [(vx, vy, min(L.WATER_Z - 0.12, terrain_height(vx, vy) + WATER_BED_CLEARANCE)) for (vx, vy) in verts2d]
    verts = top + bed
    faces = [list(t) for t in keep]                                   # surface, up
    faces += [[c + n, b + n, a + n] for (a, b, c) in keep]            # bed, down

    # walls: every boundary edge of the surface (used by exactly one triangle) gets a quad down to the bed
    edge_use = {}
    for (a, b, c) in keep:
        for (p0, p1) in ((a, b), (b, c), (c, a)):
            key = (min(p0, p1), max(p0, p1))
            edge_use[key] = edge_use.get(key, 0) + 1
    border = []
    for (a, b, c) in keep:
        for (p0, p1) in ((a, b), (b, c), (c, a)):
            if edge_use[(min(p0, p1), max(p0, p1))] == 1:
                border.append((p0, p1))
    for (p0, p1) in border:
        faces.append([p1, p0, p0 + n, p1 + n])

    obj = L.mesh_from_tris("ENV_lagoon_water", verts, faces, coll, [L.mat("MAT_water_lagoon")], smooth=False)
    me = obj.data
    # smooth only the surface; the walls and the bed stay flat
    for poly in me.polygons:
        poly.use_smooth = all(me.vertices[i].co.z > L.WATER_Z - 0.01 for i in poly.vertices)
    uv = me.uv_layers.new(name="UVMap")
    for loop in me.loops:
        v = me.vertices[loop.vertex_index].co
        uv.data[loop.index].uv = (v.x / 10.0, v.y / 10.0)
    # manifold check
    counts = {}
    for poly in me.polygons:
        vs = list(poly.vertices)
        for i in range(len(vs)):
            key = (min(vs[i], vs[(i + 1) % len(vs)]), max(vs[i], vs[(i + 1) % len(vs)]))
            counts[key] = counts.get(key, 0) + 1
    open_edges = sum(1 for v in counts.values() if v != 2)
    depths = [L.WATER_Z - b[2] for b in bed]
    log(f"water: {L.tri_count(obj)} tris, {len(keep)} surface tris, {len(border)} wall quads, "
        f"open edges {open_edges}, depth {min(depths):.2f}-{max(depths):.2f} m")
    obj["closed_volume"] = open_edges == 0
    obj["mean_surface_edge_m"] = step
    return obj


# ----------------------------------------------------------------------------- rip-rap
def build_riprap():
    """Irregular rows of 0.4-1.1 m boulders along the water line (refs 022, 063, 169, 187): a broken line at the
    waterline (some half submerged), a second row up the bank, extra clusters where the shore is a 'hard' edge."""
    log("rip-rap")
    coll = SUB["ENV_extras"]
    rocks = [L.make_rock_mesh(f"ENV_rock_src_{i}", radius=0.5, seed=100 + i, subdiv=1 if i < 4 else 2) for i in range(7)]
    m_rock = L.mat("MAT_rock_riprap")
    rnd = random.Random(11)
    step = 1.2 if QUICK else 0.7
    shore = L.resample_polyline(LAGOON, step, closed=True)
    sectors = {}
    n = len(shore)
    for i, (x, y) in enumerate(shore):
        p0 = Vector(shore[i - 1]); p1 = Vector(shore[(i + 1) % n])
        d = (p1 - p0)
        if d.length < 1e-6:
            continue
        d.normalize()
        outward = Vector((d.y, -d.x))
        density = 0.55 + 0.45 * L.fnoise(x, y, 0.06, 12)      # stretches of dense stone and stretches of bare bank
        r = math.hypot(x, y)
        if r < 50:
            density += 0.25                                      # the rotunda peninsula is fully armoured
        ang = int((math.degrees(math.atan2(y, x)) + 360) % 360) // 45
        # waterline row: big boulders, partly submerged, jittered across the line
        if rnd.random() < density:
            s0 = rnd.uniform(0.32, 0.80)
            off = rnd.uniform(-1.3, 0.5)
            px, py = x + outward.x * off + rnd.uniform(-0.3, 0.3) * d.x, y + outward.y * off + rnd.uniform(-0.3, 0.3) * d.y
            # centre straddles the water line: about a third of each boulder stands proud (refs 022, 063, 187)
            pz = L.WATER_Z + 0.02 + s0 * 0.22 + rnd.uniform(-0.22, 0.14) - max(0.0, -off) * 0.18
            sectors.setdefault(ang, []).append((rnd.randrange(len(rocks)), ((px, py, pz), rnd.uniform(0, 6.283),
                                                (s0 * rnd.uniform(0.8, 1.4), s0 * rnd.uniform(0.8, 1.2), s0 * rnd.uniform(0.55, 0.9)))))
        # bank row: smaller stones, sparser
        if rnd.random() < density * 0.7:
            s1 = rnd.uniform(0.30, 0.62)
            off = rnd.uniform(0.8, 1.9)
            px, py = x + outward.x * off, y + outward.y * off
            pz = terrain_height(px, py) - 0.12 + s1 * 0.25
            sectors.setdefault(ang, []).append((rnd.randrange(len(rocks)), ((px, py, pz), rnd.uniform(0, 6.283),
                                                (s1 * rnd.uniform(0.8, 1.3), s1, s1 * rnd.uniform(0.6, 0.9)))))
    for isl in ISLETS[:1]:
        for (x, y) in L.resample_polyline(isl, 1.0, closed=True):
            s0 = rnd.uniform(0.32, 0.72)
            sectors.setdefault(9, []).append((rnd.randrange(len(rocks)), ((x + rnd.uniform(-0.4, 0.4), y + rnd.uniform(-0.4, 0.4), L.WATER_Z + 0.05 + s0 * 0.25), rnd.uniform(0, 6.283), s0)))
    total = 0
    count = 0
    for ang, items in sorted(sectors.items()):
        for ri in range(len(rocks)):
            tr = [t for (k, t) in items if k == ri]
            if not tr:
                continue
            obj = L.join_instances(f"ENV_riprap_s{ang:02d}_r{ri}", rocks[ri], tr, coll, m_rock)
            total += L.tri_count(obj)
            count += len(tr)
    for me in rocks:
        bpy.data.meshes.remove(me)
    log(f"rip-rap: {count} boulders, {total} tris")


# ----------------------------------------------------------------------------- shrubs, grasses and reeds
# QA-01-2: the shore planting is mounded foliage built from small per-leaf cards, not extruded slabs. Every card is
# a 9-13 cm quad with a v = up UV so the library's alpha-cut MAT_shrub / MAT_reeds textures give the silhouette.
# Instances are separate objects sharing one mesh, so the library materials' per-object random (PFA_instance) gives
# each bush its own hue/value; joined meshes would make a whole belt one colour.
SHRUB_CARD = 0.085         # leaf card width (m); height is 1.25 x this
BLADE_W = 0.05             # grass / reed blade width (m)


def _uv_quads(me):
    uv = me.uv_layers.new(name="UVMap")
    for poly in me.polygons:
        n = len(poly.vertices)
        for k, li in enumerate(poly.loop_indices):
            uv.data[li].uv = ((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0))[k % 4] if n == 4 else \
                             ((0.0, 0.0), (1.0, 0.0), (0.5, 1.0))[k % 3]
    return uv


def _card(verts, faces, cx, cy, cz, w, h, angle, tilt):
    """One leaf card: bottom edge (v=0) at (cx,cy,cz), leaning by `tilt` from vertical."""
    dx, dy = math.cos(angle) * w / 2, math.sin(angle) * w / 2
    ux = -math.sin(angle) * math.sin(tilt) * h
    uy = math.cos(angle) * math.sin(tilt) * h
    uz = math.cos(tilt) * h
    b = len(verts)
    verts += [(cx - dx, cy - dy, cz), (cx + dx, cy + dy, cz),
              (cx + dx + ux, cy + dy + uy, cz + uz), (cx - dx + ux, cy - dy + uy, cz + uz)]
    faces.append([b, b + 1, b + 2, b + 3])


def make_shrub_mesh(name, seed, radius=0.8, height=0.9, card=SHRUB_CARD, form="mound", cover=1.5):
    """Mounded evergreen bush (pittosporum / mahonia): a dark inner blob wrapped in a shell of small leaf cards.
    `form='upright'` gives the coarser, more open mahonia habit (cards clustered on a few upright sprays)."""
    rnd = random.Random(seed)
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=2, radius=1.0)
    for v in bm.verts:
        nz = L.noise.noise(v.co * 2.4 + Vector((seed, seed, 0)))
        r = 1.0 + 0.26 * nz
        v.co = Vector((v.co.x * radius * 0.72 * r, v.co.y * radius * 0.72 * r,
                       max(-0.05, v.co.z) * height * 0.72 * r))
    verts = [v.co.copy() for v in bm.verts]
    faces = [[v.index for v in f.verts] for f in bm.faces]
    n_core = len(faces)
    bm.free()
    area = 2 * math.pi * radius * (0.6 * radius + 0.4 * height)
    n_cards = max(40, int(cover * area / (card * card * 1.25 * 0.53)))
    if form == "upright":
        n_stems = rnd.randint(5, 9)
        stems = []
        for _ in range(n_stems):
            a = rnd.uniform(0, 2 * math.pi)
            rr = radius * rnd.uniform(0.0, 0.6)
            lean = rnd.uniform(0.05, 0.35)
            stems.append((math.cos(a) * rr, math.sin(a) * rr, a, lean, height * rnd.uniform(0.7, 1.15)))
        for _ in range(n_cards):
            sx, sy, sa, lean, sh = stems[rnd.randrange(n_stems)]
            t = rnd.uniform(0.25, 1.0) ** 0.55
            cz = t * sh
            spread = radius * 0.38 * (0.3 + t)
            cx = sx + math.cos(sa) * lean * cz + rnd.uniform(-spread, spread)
            cy = sy + math.sin(sa) * lean * cz + rnd.uniform(-spread, spread)
            _card(verts, faces, cx, cy, cz, card * rnd.uniform(0.75, 1.25), card * 1.25 * rnd.uniform(0.8, 1.4),
                  rnd.uniform(0, math.pi), rnd.uniform(-1.1, 1.1))
    else:
        for _ in range(n_cards):
            u = rnd.uniform(0, 2 * math.pi)
            zt = rnd.uniform(0.02, 1.0) ** 0.55
            rr = math.sqrt(max(0.0, 1.0 - zt * zt)) * radius * rnd.uniform(0.80, 1.12)
            cx, cy = math.cos(u) * rr, math.sin(u) * rr
            cz = zt * height * rnd.uniform(0.80, 1.05)
            _card(verts, faces, cx, cy, cz, card * rnd.uniform(0.7, 1.2), card * 1.25 * rnd.uniform(0.85, 1.45),
                  rnd.uniform(0, math.pi), rnd.uniform(-1.2, 1.2))
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], faces)
    me.update()
    _uv_quads(me)
    for i, p in enumerate(me.polygons):
        p.use_smooth = i < n_core
    me["cards"] = n_cards
    me["card_m"] = card
    return me


def make_blade_clump(name, seed, height=1.1, blades=60, width=BLADE_W, arch=0.35, spread=0.28):
    """Strappy clump: agapanthus (short, wide arch) and dry reeds (tall, upright). Blades are three-segment strips
    (<= 6 cm wide) that bend over, so the silhouette is never a straight-edged slab."""
    rnd = random.Random(seed)
    verts, faces = [], []
    for _ in range(blades):
        a = rnd.uniform(0, math.pi)
        w = width * rnd.uniform(0.6, 1.15)
        h = height * rnd.uniform(0.5, 1.35)
        ox, oy = rnd.uniform(-spread, spread), rnd.uniform(-spread, spread)
        la = rnd.uniform(0, 2 * math.pi)
        lean = arch * rnd.uniform(0.4, 1.6)
        lx, ly = math.cos(la) * h * lean, math.sin(la) * h * lean
        dx, dy = math.cos(a) * w / 2, math.sin(a) * w / 2
        b = len(verts)
        verts += [(ox - dx, oy - dy, 0.0), (ox + dx, oy + dy, 0.0),
                  (ox + dx * 0.75 + lx * 0.30, oy + dy * 0.75 + ly * 0.30, h * 0.52),
                  (ox - dx * 0.75 + lx * 0.30, oy - dy * 0.75 + ly * 0.30, h * 0.52),
                  (ox + dx * 0.45 + lx * 0.72, oy + dy * 0.45 + ly * 0.72, h * 0.85),
                  (ox - dx * 0.45 + lx * 0.72, oy - dy * 0.45 + ly * 0.72, h * 0.85),
                  (ox + dx * 0.10 + lx, oy + dy * 0.10 + ly, h * 0.99),
                  (ox - dx * 0.10 + lx, oy - dy * 0.10 + ly, h * 0.99)]
        faces += [[b, b + 1, b + 2, b + 3], [b + 3, b + 2, b + 4, b + 5], [b + 5, b + 4, b + 6, b + 7]]
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    # v runs 0..1 up the blade so the reed texture's roots/tips land where they should
    uv = me.uv_layers.new(name="UVMap")
    vs = (0.0, 0.0, 0.34, 0.34, 0.62, 0.62, 1.0, 1.0)
    us = (0.0, 1.0, 1.0, 0.0)
    for pi, poly in enumerate(me.polygons):
        seg = pi % 3
        for k, li in enumerate(poly.loop_indices):
            vi = poly.vertices[k] % 8
            uv.data[li].uv = (us[k % 4], vs[vi])
    return me


def make_twig_shrub_mesh(name, seed, radius=0.7, height=1.2, twigs=70):
    """Leafless winter shrub (many along the shore in ref 169): thin brown strips fanning out of a base."""
    rnd = random.Random(seed)
    verts, faces = [], []
    for t in range(twigs):
        a = rnd.uniform(0, 2 * math.pi)
        lean = rnd.uniform(0.15, 0.75)
        h = height * rnd.uniform(0.5, 1.2)
        w = rnd.uniform(0.02, 0.045)
        ox, oy = rnd.uniform(-0.15, 0.15), rnd.uniform(-0.15, 0.15)
        tx, ty = math.cos(a) * radius * lean, math.sin(a) * radius * lean
        mx, my, mz = ox + tx * 0.4, oy + ty * 0.4, h * 0.55
        ex, ey, ez = ox + tx, oy + ty, h
        pa = rnd.uniform(0, math.pi)
        dx, dy = math.cos(pa) * w, math.sin(pa) * w
        b = len(verts)
        verts += [(ox - dx, oy - dy, 0.0), (ox + dx, oy + dy, 0.0), (mx + dx * 0.8, my + dy * 0.8, mz), (mx - dx * 0.8, my - dy * 0.8, mz),
                  (ex + dx * 0.3, ey + dy * 0.3, ez), (ex - dx * 0.3, ey - dy * 0.3, ez)]
        faces.append([b, b + 1, b + 2, b + 3])
        faces.append([b + 3, b + 2, b + 4, b + 5])
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    uv = me.uv_layers.new(name="UVMap")
    vs = (0.0, 0.0, 0.55, 0.55, 1.0, 1.0)
    us = (0.0, 1.0, 1.0, 0.0)
    for poly in me.polygons:
        for k, li in enumerate(poly.loop_indices):
            uv.data[li].uv = (us[k % 4], vs[poly.vertices[k] % 6])
    return me


def build_shrubs():
    """Shore planting per reference sheet s6: pittosporum mounds (dark), mahonia (upright, coarser), agapanthus
    clumps at the water, dry reeds and leafless twig shrubs. Clustered with gaps so rip-rap and lawn show through."""
    log("shrubs + grasses + reeds")
    coll = SUB["ENV_shrubs"]
    rnd = random.Random(23)
    # (key, material, mesh factory) - meshes are shared by every instance of that key
    src = {}
    for i, (r, h) in enumerate(((0.55, 0.55), (0.8, 0.8), (1.1, 1.0), (1.5, 1.25))):
        src[f"pitto{i}"] = ("MAT_shrub", make_shrub_mesh(f"ENV_src_pittosporum_{i}", 300 + i, radius=r, height=h,
                                                         form="mound", cover=1.6))
    for i, (r, h) in enumerate(((0.7, 1.15), (0.95, 1.55))):
        src[f"maho{i}"] = (("MAT_shrub_light", "MAT_shrub"), make_shrub_mesh(f"ENV_src_mahonia_{i}", 320 + i, radius=r, height=h,
                                                        card=0.105, form="upright", cover=1.1))
    for i in range(3):
        src[f"agap{i}"] = ("MAT_reeds", make_blade_clump(f"ENV_src_agapanthus_{i}", 340 + i, height=0.62 + 0.12 * i,
                                                         blades=70, width=0.050, arch=0.55, spread=0.30))
    for i in range(3):
        src[f"reed{i}"] = (("MAT_shrub_dry", "MAT_reeds"), make_blade_clump(f"ENV_src_reed_{i}", 400 + i, height=1.0 + 0.22 * i,
                                                         blades=54, width=0.045, arch=0.18, spread=0.26))
    for i in range(3):
        src[f"twig{i}"] = (("MAT_shrub_dry", "MAT_reeds"), make_twig_shrub_mesh(f"ENV_src_twig_{i}", 350 + i,
                                                             radius=0.5 + 0.2 * i, height=0.9 + 0.25 * i))
    mats = {k: (L.mat_or(*m) if isinstance(m, tuple) else L.mat(m)) for k, (m, _) in src.items()}
    for k, (mname, me) in src.items():
        me.materials.append(mats[k])

    placed = []            # (key, (x, y, z), rot, scale)

    def land_ok(x, y, min_shore=0.0, max_shore=1e9):
        d = LAGOON_FIELD.signed(x, y)
        if d < min_shore or d > max_shore:
            return False
        if math.hypot(x + 14.1, y - 100.0) < 34.0:      # hero camera foreground stays clean (user image, ref 169)
            return False
        if math.hypot(x, y) < APRON_R + 1.0:
            return False
        if any(L.point_in_poly(x, y, L.offset_polygon(p, 2.5)) for p in COLONNADE_ROOFS):
            return False
        if HALL_FIELD.signed(x, y) < 1.0:
            return False
        return True

    def put(key, x, y, dz=-0.06, s=(0.85, 1.15)):
        placed.append((key, (x, y, terrain_height(x, y) + dz), rnd.uniform(0, 6.283), rnd.uniform(*s)))

    def clump(cx, cy, n, spread, keys, min_shore=0.9, max_shore=7.0):
        for _ in range(n):
            x, y = cx + rnd.uniform(-spread, spread), cy + rnd.uniform(-spread, spread)
            if land_ok(x, y, min_shore, max_shore):
                put(rnd.choice(keys), x, y)

    MOUNDS = ("pitto0", "pitto1", "pitto2", "pitto3")
    LOWMOUNDS = ("pitto0", "pitto1", "pitto2")
    MAHONIA = ("maho0", "maho1")
    AGAP = ("agap0", "agap1", "agap2")
    REEDS = ("reed0", "reed1", "reed2")
    TWIGS = ("twig0", "twig1", "twig2")

    # 1. rotunda peninsula: dense on the north-east (user image, right of the rotunda), open on the south-east.
    #    ref 169's shore is a continuous mass of foliage down to the rip-rap, so the belt is closed, not dotted.
    for (x, y) in L.resample_polyline(L.offset_polygon(LAGOON, 2.4), 2.6, closed=True):
        r = math.hypot(x, y)
        if not (APRON_R + 1.0 < r < 49.0):
            continue
        az = math.degrees(math.atan2(y, -x)) % 360
        ne = L.smoothstep(150.0, 60.0, abs(az - 40.0)) if az < 180 else 0.0
        se = L.smoothstep(150.0, 60.0, abs(az - 140.0)) if az < 200 else 0.0
        p = 0.62 + 0.32 * ne - 0.20 * se
        if rnd.random() < p:
            keys = MOUNDS + MAHONIA if ne > 0.5 else LOWMOUNDS + MAHONIA
            clump(x, y, rnd.randint(2, 6), 2.4, keys, min_shore=0.5, max_shore=9.0)
        if rnd.random() < 0.55:
            clump(x, y, rnd.randint(1, 3), 1.6, AGAP, min_shore=0.25, max_shore=3.2)
        if rnd.random() < 0.30:
            clump(x, y, 1, 1.5, TWIGS, min_shore=0.6, max_shore=6.0)
    # 2. the rest of the shore: the same belt, a little sparser, with more dry reeds at the water
    for (x, y) in L.resample_polyline(L.offset_polygon(LAGOON, 2.0), 3.0, closed=True):
        if math.hypot(x, y) < 50 or not land_ok(x, y, 0.4, 9.0):
            continue
        if rnd.random() < 0.62:
            clump(x, y, rnd.randint(2, 5), 2.8, LOWMOUNDS + MAHONIA, min_shore=0.5, max_shore=9.0)
        if rnd.random() < 0.35:
            clump(x, y, 1, 1.5, TWIGS, min_shore=0.5, max_shore=6.0)
        if rnd.random() < 0.7:
            clump(x, y, rnd.randint(1, 3), 1.8, REEDS, min_shore=0.2, max_shore=3.4)
        if rnd.random() < 0.5:
            clump(x, y, rnd.randint(1, 3), 1.6, AGAP, min_shore=0.2, max_shore=3.0)
    # 2b. bank cover: low mounds sitting on the rip-rap bank itself, so the pale stone band is broken up
    #     (in ref 169 the bank is visible only in gaps between the bushes)
    for (x, y) in L.resample_polyline(L.offset_polygon(LAGOON, 1.2), 2.2, closed=True):
        if rnd.random() < 0.55:
            clump(x, y, rnd.randint(1, 3), 1.3, LOWMOUNDS, min_shore=0.15, max_shore=2.6)
    # 2c. peninsula planting band 9-18 m back from the water, between the shore belt and the podium (lead's call
    #     after the hero camera stayed put): ref 169 shows beds of mounded shrubs and low trees there, not bare lawn.
    #     Beds, not a carpet - the gaps keep the mown lawn reading.
    n_band = len(placed)
    keys_band = LOWMOUNDS + MAHONIA + AGAP
    for off in (8.5, 11.5, 14.5, 17.5):
        for (x, y) in L.resample_polyline(L.offset_polygon(LAGOON, off), 2.5, closed=True):
            r = math.hypot(x, y)
            if not (APRON_R - 1.0 < r < 58.0):       # the strip between the platform apron and the shore belt
                continue
            bed = L.fnoise(x, y, 0.10, 31)           # ~10 m beds with mown lawn between them
            if bed < -0.25:
                continue
            if rnd.random() < 0.75 + 0.25 * bed:
                clump(x, y, rnd.randint(3, 7), 2.8, keys_band, min_shore=6.5, max_shore=21.0)
    n_band = len(placed) - n_band

    # 3. foundation planting along the colonnade fronts
    for p in COLONNADE_ROOFS[:2]:
        for (x, y) in L.resample_polyline(L.offset_polygon(p, 4.5), 5.0, closed=True):
            if land_ok(x, y, 1.0) and rnd.random() < 0.5:
                clump(x, y, rnd.randint(1, 3), 2.0, LOWMOUNDS + MAHONIA, min_shore=1.0, max_shore=1e9)
    # 4. the wooded islet: dense dark mounds under the willows
    for _ in range(90):
        p = ISLETS[0]
        xs = [q[0] for q in p]
        ys = [q[1] for q in p]
        x, y = rnd.uniform(min(xs), max(xs)), rnd.uniform(min(ys), max(ys))
        if L.point_in_poly(x, y, p) and ISLET_FIELDS[0].signed(x, y) < -0.8:
            key = rnd.choice(MOUNDS + AGAP + REEDS)
            placed.append((key, (x, y, terrain_height(x, y) - 0.05), rnd.uniform(0, 6.283), rnd.uniform(0.8, 1.25)))

    counts = {}
    total = 0
    for i, (key, loc, rot, sc) in enumerate(placed):
        me = src[key][1]
        obj = bpy.data.objects.new(f"ENV_shrub_{key}_{i:04d}", me)
        obj.location = loc
        obj.rotation_euler = (0.0, 0.0, rot)
        obj.scale = (sc * rnd.uniform(0.92, 1.08), sc * rnd.uniform(0.92, 1.08), sc * rnd.uniform(0.9, 1.12))
        coll.objects.link(obj)
        counts[key] = counts.get(key, 0) + 1
        total += L.tri_count(obj)
    card_max = max(src[k][1].get("card_m", 0.0) * 1.45 for k in src if src[k][1].get("card_m"))
    log(f"shrubs: {len(placed)} instances ({n_band} in the peninsula band 7.5-19.5 m from the water) "
        f"of {len(src)} meshes, {total} tris, "
        f"largest leaf card {card_max * 100:.0f} cm; {counts}")


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
                                   colonnade_polys=COLONNADE_ROOFS, hall_poly=HALL, hall_field=HALL_FIELD)
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
        env_backdrop.build_all(SUB, terrain_height, SITE, HALL, HALL_FIELD)
    # viewport default LOD1 (instances only); source trees stay hidden everywhere
    L.set_object_lod_visibility(ENV, 1)
    for obj in SUB["ENV_trees"].objects:
        obj.hide_viewport = True
        obj.hide_render = True
    # common.load_material appends one material at a time, which leaves PFA_*.001 / TEX_*.001 copies of the
    # library's shared node groups and images behind; the materials agent's helper remaps them back.
    try:
        import mat_lib
        mat_lib.dedupe_node_groups()
    except Exception as e:
        log(f"mat_lib.dedupe_node_groups skipped: {e}")
    for lod in (0, 1, 2):
        log(f"ENV tri count at LOD{lod}: {L.collection_tri_count(ENV, lod=lod):,}")
    log(f"objects in ENV: {len(ENV.all_objects)}")
    common.save_blend(common.ASSET_FILES["ENV"])
    if "--preview" in ARGS:
        import env_preview
        env_preview.render(tag="build")


main()
