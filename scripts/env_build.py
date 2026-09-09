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
import arch_params as AP        # read-only: ARCH owns these constants, ENV must track them, never copy them
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
COL_FIELDS = [L.PolyField(p, cell=8.0) for p in COLONNADE_ROOFS[:2]]      # QA-05-11: the walk is a level
# ... with a bounding box in front of it: `terrain_height` is called ~10^5 times and PolyField.dist falls back to
# a brute-force scan of all 95 segments (plus a point-in-poly) for any point outside its bucket grid's reach.
COL_BOXES = [(min(q[0] for q in p) - 7.0, min(q[1] for q in p) - 7.0,
              max(q[0] for q in p) + 7.0, max(q[1] for q in p) + 7.0) for p in COLONNADE_ROOFS[:2]]
COLONNADE_WALK_Z = AP.COLONNADE_GROUND_Z   # the level the column bases are modelled on (-0.60 today).  Imported,
                                           # not copied: a hand-copy matches today and drifts silently tomorrow.

APRON_R = 31.0          # inside this radius the ARCH platform covers the ground
TERRAIN_HALF = 360.0    # terrain covers +-360 m (720 x 720)


# ------------------------------------------------------- QA-04-4 / QA-03-13: the shore cap is a SIGHT LINE
# QA-03-13 asked for the podium's Greek-key course to stay legible from cam 05; round 03 answered with a radius
# rule - every shrub inside r 54 m clamped to <= 1.2 m - and QA-04-4 then measured the result as "a bare pale
# quay with 0.5-1 m dot shrubs at ~40 px spacing and an exposed podium base", against ref 169's 2-4 m mounds.
# The two requirements only conflict while the cap is a radius.  What the references actually show (169 from the
# east, 063 from the south-east) is a continuous mass of mounded shrubs 2-3.5 m high whose tops stop just under
# the band: the podium wall is 4.3 m and the meander course is its top 0.5 m, so a 3.2 m mound on the shore
# buries the base and leaves the band clear.  The cap below is exactly that - the height of the ray from each
# camera's eye to the bottom of the band where it passes over the shrub.
PODIUM_BAND_Z0 = 3.8         # bottom of the Greek-key / rosette course (sheet: podium wall 0 -> 4.3, band h 0.5)
PODIUM_BAND_R = 27.3         # arch_params.PODIUM_LOBE_R - the innermost (hardest to keep clear) band stone
BAND_MARGIN = 0.30           # crown tops stop this far under the sight line
# `band_sightline_cap` returns None where no camera's ray to the band passes over the point - there is nothing to
# keep clear there, and it is not the sight line's business to say how tall a shrub may be.  The blanket ceiling
# that applies to EVERY shrub in the build, sight line or not, is SHRUB_H_CEILING, applied in `put`.
SHRUB_H_CEILING = 4.00       # QA-04-4's acceptance window tops out at 4 m; nothing scattered is ever taller
SHORE_H_MIN = 0.55           # ... and the cap never shrinks a shrub below this, however low the sight line runs
# Eye points that must keep the band: cam 01 (hero), cam 05 (QA-03-13's own camera), cam 02 (the SSE station the
# lead re-stationed in QA round 04).  Read from scripts/qa_cameras.py by name, never copied: a snapshot would keep
# capping the shore against a station the QA renders no longer use.  A camera that is not in the set drops out.
CAM01 = L.qa_camera("_qa_01_", (-14.1, 100.0, 1.6), 20.0)
CAM02 = L.qa_camera("_qa_02_", (70.5, 25.6, 1.1), 24.0)
CAM05 = L.qa_camera("_qa_05_", (28.1, 111.8, 1.5), 35.0)
BAND_EYES = tuple(c[0] for c in (CAM01, CAM05, CAM02) if c is not None)
CAM02_XY = CAM02[0][:2] if CAM02 is not None else (70.5, 25.6)


def _ray_circle_t(ox, oy, dx, dy, radius):
    """Distance along the unit ray (ox, oy) + t (dx, dy) to the first crossing of the circle r = radius about the
    world origin, or None if it misses."""
    b = ox * dx + oy * dy
    c = ox * ox + oy * oy - radius * radius
    disc = b * b - c
    if disc <= 0.0:
        return None
    root = math.sqrt(disc)
    t = -b - root
    return t if t > 0.0 else None


def band_sightline_cap(x, y, z_ground):
    """Tallest shrub at (x, y) that still leaves the podium's Greek-key band visible from every hero camera.

    Returns None when no camera's ray to the band passes over this point - beside or behind the podium there is
    no band stone to hide, so the sight line imposes nothing.  `put` applies SHRUB_H_CEILING either way.
    """
    cap = None
    for (ex, ey, ez) in BAND_EYES:
        dx, dy = x - ex, y - ey
        d = math.hypot(dx, dy)
        if d < 1e-6:
            continue
        D = _ray_circle_t(ex, ey, dx / d, dy / d, PODIUM_BAND_R)
        if D is None or d > D - 1.0:
            continue                       # beside or behind the podium: this shrub hides no band stone
        z_line = ez + (PODIUM_BAND_Z0 - ez) * d / D
        c = z_line - BAND_MARGIN - z_ground
        cap = c if cap is None else min(cap, c)
    return None if cap is None else max(SHORE_H_MIN, cap)


# ----------------------------------------------------------------------------- height field
def terrain_height(x, y):
    """Ground height (m) at world (x, y). Shared by the terrain mesh and by everything scattered on it."""
    for f in ISLET_FIELDS:
        d = f.signed(x, y)
        if d < 0:
            return -0.78 + 0.5 * L.smoothstep(0.0, 9.0, -d) + 0.06 * L.fnoise(x, y, 0.3, 4)
    d = LAGOON_FIELD.signed(x, y)
    if d < 0:                                    # lagoon bed
        # QA-02-6: the round-02 bed dropped to its full 1.5 m within 7.5 m of the shore, so the water the hero
        # camera sees at 6-12 m already had the longest possible absorption path through MAT_water_lagoon's murk -
        # it read as a near-black cyan. The real lagoon has a wide shallow shelf (refs 022, 169: the rip-rap and
        # bed pebbles are visible several metres out). Shelf 0.25-0.85 m to 14 m out, then down to 1.5 m by 30 m.
        # QA-04-8 (round 6): the shelf is a little shallower and a little wider again.  The hero's near-field box
        # (1150 1000 1450 1050) looks at water 8-9 m in front of the lens, ~5 m off the bank; every centimetre of
        # absorption path there is a centimetre of the bed's green that does not come back up.
        e = -d
        depth = 0.22 + 0.52 * L.smoothstep(0.0, 16.0, e) + 0.72 * L.smoothstep(16.0, 32.0, e)
        return L.WATER_Z - depth + 0.07 * L.fnoise(x, y, 0.15, 3)
    r = math.hypot(x, y)
    base = -0.45 + 0.10 * L.fnoise(x, y, 0.012, 1) + 0.04 * L.fnoise(x, y, 0.06, 2)
    pen = L.smoothstep(62.0, 46.0, r)            # 1 on the peninsula (lawn a bit lower there)
    base = base * (1 - pen) + (-0.6 + 0.03 * L.fnoise(x, y, 0.08, 5)) * pen
    # QA-05-11 (round 7): the colonnade walk is a defined level, not lawn.  `arch_params.COLONNADE_GROUND_Z` is
    # -0.60 and ENV's lawn ran at -0.45 through the wings, so every column base stood 15 cm buried - visible at
    # cam 03, which looks straight down the walk, and the new paving would have added 3.5 cm more.  The walk is
    # pulled to -0.60 inside the wing footprint and blends back to lawn between the terrain's own two constraint
    # rings (offset 2.0 and 5.5), so the slope change lands on a mesh edge instead of being sampled.
    for bb, f in zip(COL_BOXES, COL_FIELDS):
        if not (bb[0] <= x <= bb[2] and bb[1] <= y <= bb[3]):
            continue
        d = f.signed(x, y)
        if d < 5.5:
            t = L.smoothstep(5.5, 2.0, d)
            base = base * (1 - t) + (COLONNADE_WALK_Z + 0.02 * L.fnoise(x, y, 0.25, 6)) * t
            break
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
    verges = []
    for p in paths:
        ribbons += L.ribbon_polygons(p, path_width)
        verges += L.ribbon_polygons(p, path_width + 3.0)      # QA-03-9: soil verge each side of every walk
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
    # QA-03-9: cam 03 stood on "a flat olive plane".  The ground now carries real bands: the gravel walk inside
    # the colonnade, a soil planting bed 2-5.5 m outside it (where the foundation shrubs stand), lawn, and a soil
    # verge along every path.  All four are CDT constraints so the edges are clean rather than sampled.
    col_bed = [L.offset_polygon(p, 5.5) for p in COLONNADE_ROOFS]
    constraints = ([LAGOON] + ISLETS + [L.offset_polygon(p, 2.0) for p in COLONNADE_ROOFS] + col_bed
                   + [apron] + verges + ribbons + [HALL])
    # keep points away from the constraint edges (CDT epsilon issues) - cheap filter near the lagoon only
    pts = [p for p in pts if abs(LAGOON_FIELD.dist(p[0], p[1])) > 0.6]
    log(f"terrain: {len(pts)} grid points, {len(constraints)} constraint polygons")
    verts2d, tris = L.cdt_triangulate(pts, constraints)
    log(f"terrain: CDT {len(verts2d)} verts {len(tris)} tris; heights")
    heights = [terrain_height(x, y) for (x, y) in verts2d]
    verts = [(x, y, z) for (x, y), z in zip(verts2d, heights)]
    # face materials
    m_lawn, m_soil, m_gravel = L.mat("MAT_lawn"), L.mat("MAT_soil"), L.mat("MAT_gravel_path")
    m_bed = L.mat("MAT_lagoon_bed")            # QA-04-8: the bed is not brown soil, see below
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
        elif any(L.point_in_poly(cx, cy, p) for p in col_bed):
            face_mat.append(1)                                          # colonnade planting bed (QA-03-9)
        elif any(f.dist(cx, cy) < path_width / 2 + 1.5 for f in path_fields):
            face_mat.append(1)                                          # soil verge (QA-03-9)
        elif L.point_in_poly(cx, cy, HALL):
            face_mat.append(2)
        else:
            face_mat.append(0)
    # QA-04-8: the lagoon bed is now its own object with its own material.  The near field read hue 208.7 (blue)
    # against ref 169's 190-192 (teal); lighting measured the sky's hue as exact, so the missing green is the
    # lagoon's upwelling - and the bed under the shallow 0.25-0.85 m shelf was carrying MAT_soil, a brown.  Split
    # out as ENV_lagoon_bed so materials can address it (and the lead can hide it) without touching the lawn.
    bed_tris, land_tris, land_mat = [], [], []
    for (t, mi) in zip(tris, face_mat):
        cx = (verts2d[t[0]][0] + verts2d[t[1]][0] + verts2d[t[2]][0]) / 3
        cy = (verts2d[t[0]][1] + verts2d[t[1]][1] + verts2d[t[2]][1]) / 3
        if L.point_in_poly(cx, cy, LAGOON) and not any(L.point_in_poly(cx, cy, p) for p in ISLETS):
            bed_tris.append(t)
        else:
            land_tris.append(t)
            land_mat.append(mi)
    def compact(tri_list):
        """Renumber a triangle list onto only the vertices it uses - otherwise each half of the split carries the
        whole terrain's vertex array (ENV_lagoon_bed came out with ~100 k loose verts and a 720 m bounding box,
        which breaks any bound-box test and every viewport frame-selected)."""
        remap, tris_out = {}, []
        for t in tri_list:
            tris_out.append(tuple(remap.setdefault(i, len(remap)) for i in t))
        vs = [None] * len(remap)
        for old_i, new_i in remap.items():
            vs[new_i] = verts[old_i]
        return vs, tris_out

    land_v, land_t = compact(land_tris)
    bed_v, bed_t = compact(bed_tris)
    obj = L.mesh_from_tris("ENV_terrain_ground", land_v, land_t, coll, mats, land_mat, smooth=True)
    bed = L.mesh_from_tris("ENV_lagoon_bed", bed_v, bed_t, coll, [m_bed], [0] * len(bed_t), smooth=True)
    log(f"terrain: mesh {L.tri_count(obj)} tris + ENV_lagoon_bed {L.tri_count(bed)} tris "
        f"({m_bed.name}{' PLACEHOLDER' if m_bed.get('placeholder') else ''})")
    # soil beds on the peninsula and the islet: handled by shrub scatter (soil material patches under shrubs)
    return obj, paths


# ----------------------------------------------------------------------------- paving (QA-05-11)
# cam 03 stands inside the south colonnade and its ground came back "bare": ground/sunlit 0.197, std 15.7, where
# ref 128 shows a paved walk with joints and a planting edge.  ARCH does not model a colonnade floor
# (`arch_params.COLONNADE_GROUND_Z = -0.6` is a level, not a slab), so the walk is ENV's terrain triangle soup -
# one flat gravel material with nothing on it.
#
# The walk is a curved colonnade, so its paving is radial: courses struck from the same centre as the wings
# (arch_params COL_ARC_CENTER, the centre env_trees.COLONNADE_ARC uses), alternate courses set half a slab out of
# phase (running bond).  Each slab is one quad lifted PAVE_LIFT over the terrain with a PAVE_JOINT gap all round,
# so the joints are real geometry that self-shadows at a 7.4 deg sun, and each slab's four corners carry an
# independent few-millimetre jitter so no two slabs return the sun identically.  ~2 tris per slab.
PAVE_CENTRE = tuple(AP.COL_ARC_CENTER)     # imported, not copied (see COLONNADE_WALK_Z)
PAVE_SLAB = 1.55              # course depth and nominal slab width (m)
PAVE_JOINT = 0.055            # joint width (m)
PAVE_LIFT = 0.035             # slab top over the terrain (m) - the joint gap is this deep
PAVE_INSET = 1.6              # the paved area is the wing footprint offset outward by this (the gravel band
                              # the terrain already lays down at +2.0 stays as a border)


def build_paving():
    """Radial paving slabs on both colonnade walks: `ENV_ground_colonnade_walk` (QA-05-11)."""
    log("paving: colonnade walk")
    coll = SUB["ENV_terrain"]
    cx, cy = PAVE_CENTRE
    rnd = random.Random(4021)
    verts, faces, fmat = [], [], []
    m_main = L.mat_or("MAT_paving_stone", "MAT_gravel_path")
    m_worn = L.mat_or("MAT_paving_stone_worn", "MAT_soil")
    n_slabs = 0
    for wing in COLONNADE_ROOFS[:2]:
        poly = L.offset_polygon(L.ensure_ccw(wing), PAVE_INSET)
        ring = L.resample_polyline(poly, 2.0, closed=True)
        # polar extent about the arc centre, unwrapped around the wing's own mean bearing
        mx = sum(math.cos(math.atan2(y - cy, x - cx)) for (x, y) in ring) / len(ring)
        my = sum(math.sin(math.atan2(y - cy, x - cx)) for (x, y) in ring) / len(ring)
        a_mid = math.atan2(my, mx)
        rs, das = [], []
        for (x, y) in ring:
            rs.append(math.hypot(x - cx, y - cy))
            das.append((math.atan2(y - cy, x - cx) - a_mid + math.pi) % (2 * math.pi) - math.pi)
        r0, r1 = min(rs) - 0.4, max(rs) + 0.4
        a0, a1 = min(das) - 0.002, max(das) + 0.002
        course = 0
        rb = r0
        while rb < r1:
            rm = rb + PAVE_SLAB / 2
            astep = PAVE_SLAB / max(1.0, rm)
            phase = (0.5 * astep) if course % 2 else 0.0
            ab = a0 - phase
            while ab < a1:
                am = ab + astep / 2
                px = cx + rm * math.cos(a_mid + am)
                py = cy + rm * math.sin(a_mid + am)
                if not L.point_in_poly(px, py, poly):
                    ab += astep
                    continue
                ja = PAVE_JOINT / max(1.0, rm) / 2
                ri, ro = rb + PAVE_JOINT / 2, rb + PAVE_SLAB - PAVE_JOINT / 2
                dz = PAVE_LIFT + rnd.uniform(-0.008, 0.008)
                b = len(verts)
                for (rr, aa) in ((ri, ab + ja), (ro, ab + ja), (ro, ab + astep - ja), (ri, ab + astep - ja)):
                    vx = cx + rr * math.cos(a_mid + aa)
                    vy = cy + rr * math.sin(a_mid + aa)
                    verts.append((vx, vy, terrain_height(vx, vy) + dz + rnd.uniform(-0.006, 0.006)))
                faces.append((b, b + 1, b + 2, b + 3))
                # worn / repaired slabs in patches, not salt-and-pepper: a noise field picks the patches
                fmat.append(1 if L.fnoise(px, py, 0.09, 44) + 0.5 * L.fnoise(px, py, 0.5, 45) > 0.42 else 0)
                n_slabs += 1
                ab += astep
            rb += PAVE_SLAB
            course += 1
    if not faces:
        log("paving: no slabs (no colonnade polygons?)")
        return None
    obj = L.mesh_from_tris("ENV_ground_colonnade_walk", verts, faces, coll, [m_main, m_worn], fmat, smooth=False)
    log(f"paving: {n_slabs} slabs, {L.tri_count(obj):,} tris, "
        f"{100.0 * sum(fmat) / max(1, len(fmat)):.0f} % worn ({m_main.name} / {m_worn.name})")
    return obj


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
        # QA-04-14: cam 02's foreground strip is the south embayment.  Its bank is 7.4 m from the lens, just under
        # the frame edge, so what has to read is the stone standing OUT in the shallows 9-26 m away: denser, and
        # scaled up (`big_stone`) so a 0.5 m cobble does not vanish at 24 mm.
        d_cam02 = math.hypot(x - CAM02_XY[0], y - CAM02_XY[1])
        big_stone = 1.0
        if d_cam02 < 40.0:
            density += 0.30
            big_stone = 1.55 - 0.35 * (d_cam02 / 40.0)
        ang = int((math.degrees(math.atan2(y, x)) + 360) % 360) // 45
        # waterline row: big boulders, partly submerged, jittered across the line
        if rnd.random() < density:
            s0 = rnd.uniform(0.32, 0.80) * big_stone
            off = rnd.uniform(-1.3, 0.5) - (rnd.uniform(0.0, 2.4) if big_stone > 1.0 else 0.0)
            px, py = x + outward.x * off + rnd.uniform(-0.3, 0.3) * d.x, y + outward.y * off + rnd.uniform(-0.3, 0.3) * d.y
            # centre straddles the water line: about a third of each boulder stands proud (refs 022, 063, 187)
            pz = L.WATER_Z + 0.02 + s0 * 0.22 + rnd.uniform(-0.22, 0.14) - max(0.0, -off) * 0.18
            sectors.setdefault(ang, []).append((rnd.randrange(len(rocks)), ((px, py, pz), rnd.uniform(0, 6.283),
                                                (s0 * rnd.uniform(0.8, 1.4), s0 * rnd.uniform(0.8, 1.2), s0 * rnd.uniform(0.55, 0.9)))))
        # bank row: smaller stones, sparser
        if rnd.random() < density * 0.7:
            s1 = rnd.uniform(0.30, 0.62) * big_stone
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

# Shrub LOD ladder (QA round 02 performance item). The round-02 master carried 1761 LOD-less shrubs at ~1870 tris
# each = 3.3 M tris in EVERY LOD and in every render. A bush is 0.8 m across; at the hero camera's 60-115 m it is
# 8-15 px, so 1300 leaf cards buy nothing. Leaf COVERAGE (n_cards * card^2) is what makes the silhouette read, so
# each step keeps the coverage and multiplies the card size instead: cards get k x wider and k^2 x fewer.
#   LOD0 full, LOD1 ~2.2 x cards (~21 % of the tris), LOD2 ~4.5 x cards (~5 %) on a coarser core.
SHRUB_LOD = {0: dict(card=1.00, cover=1.00, blade=1.00, sub=2),
             1: dict(card=2.20, cover=0.95, blade=0.33, sub=2),
             2: dict(card=4.50, cover=0.85, blade=0.12, sub=1)}
# a shrub farther than this from every QA camera renders its LOD1 mesh even at LOD0 (LOD2 beyond 2 x)
SHRUB_FAR = 80.0


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


def make_shrub_mesh(name, seed, radius=0.8, height=0.9, card=SHRUB_CARD, form="mound", cover=1.5, lod=0):
    """Mounded evergreen bush (pittosporum / mahonia): a dark inner blob wrapped in a shell of small leaf cards.
    `form='upright'` gives the coarser, more open mahonia habit (cards clustered on a few upright sprays)."""
    step = SHRUB_LOD[lod]
    card = card * step["card"]
    cover = cover * step["cover"]
    rnd = random.Random(seed)
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=step["sub"], radius=1.0)
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
    me["lod"] = lod
    me["shrub_height_m"] = height
    return me


def make_blade_clump(name, seed, height=1.1, blades=60, width=BLADE_W, arch=0.35, spread=0.28, lod=0):
    """Strappy clump: agapanthus (short, wide arch) and dry reeds (tall, upright). Blades are three-segment strips
    (<= 6 cm wide) that bend over, so the silhouette is never a straight-edged slab."""
    step = SHRUB_LOD[lod]
    blades = max(6, int(round(blades * step["blade"])))
    width = width / max(0.2, step["blade"]) ** 0.5 if lod else width
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
    me["lod"] = lod
    me["shrub_height_m"] = height
    return me


def make_twig_shrub_mesh(name, seed, radius=0.7, height=1.2, twigs=70, lod=0):
    """Leafless winter shrub (many along the shore in ref 169): thin brown strips fanning out of a base."""
    twigs = max(8, int(round(twigs * SHRUB_LOD[lod]["blade"])))
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
    me["lod"] = lod
    me["shrub_height_m"] = height
    return me


def build_shrubs():
    """Shore planting per reference sheet s6: pittosporum mounds (dark), mahonia (upright, coarser), agapanthus
    clumps at the water, dry reeds and leafless twig shrubs. Clustered with gaps so rip-rap and lawn show through.

    Round 02 fixes:
      * QA-02-18 "a regular row of near-identical dark pom-poms": 9 mound seeds instead of 4, three material
        families across them (MAT_shrub / MAT_shrub_light / MAT_shrub_dry) so the belt carries a hue spread, a
        2.4:1 instance size spread, no two neighbours drawn from the same source mesh, and dry reeds / twigs
        seeded into the peninsula belt (they were only used past r = 50 m) for the warm dry fraction.
      * QA-02-13 "the shrub band hides the podium and its Greek-key band": every shrub inside r = 54 m of the
        rotunda is clamped to 1.2 m tall.
      * performance: every source mesh is built at three LODs and each placement becomes three objects, like the
        trees, so ENV_LOD1 no longer carries the full-density cards; shrubs past SHRUB_FAR from every QA camera
        render their LOD1 mesh even at LOD0.
    """
    log("shrubs + grasses + reeds")
    coll = SUB["ENV_shrubs"]
    rnd = random.Random(23)
    # QA-04-4 (round 6): the radius clamp is gone.  ROSTRA_R 54 m / ROSTRA_H_RANGE 0.42-1.20 m was round 03's
    # answer to QA-03-13 and it is what made the hero shoreline "a bare pale quay with 0.5-1 m dot shrubs and an
    # exposed podium base".  The cap is now `band_sightline_cap` (see the top of this file): per instance, the
    # height of the ray from each hero camera's eye to the bottom of the podium's Greek-key course.  On the hero
    # shoreline it comes out at 3.2-3.7 m, which is ref 169's own mound height, and it still guarantees the band.

    # (key, material(s), {lod: mesh}, nominal height) - meshes are shared by every instance of that key
    src = {}

    def add(key, mats, factory, nom_h, **kw):
        src[key] = (mats, {lod: factory(f"ENV_src_{key}_LOD{lod}", lod=lod, **kw) for lod in (0, 1, 2)}, nom_h)

    # nine mound seeds over three material families: the belt can no longer repeat a silhouette or a hue
    MOUND_SPEC = [(0.50, 0.50, "MAT_shrub"), (0.68, 0.62, "MAT_shrub_light"), (0.80, 0.80, "MAT_shrub"),
                  (0.95, 0.72, "MAT_shrub_dry"), (1.10, 1.00, "MAT_shrub"), (1.25, 0.88, "MAT_shrub_light"),
                  (1.50, 1.25, "MAT_shrub"), (1.05, 1.35, "MAT_shrub_light"), (0.72, 1.05, "MAT_shrub_dry")]
    for i, (r, h, m) in enumerate(MOUND_SPEC):
        add(f"pitto{i}", (m, "MAT_shrub"), make_shrub_mesh, h, seed=300 + i, radius=r, height=h,
            form="mound", cover=1.6)
    # QA-04-4: ref 169's shoreline mounds are 2-4 m, not 1 m.  Four large sources, three silhouettes deep, so the
    # hero belt can reach the sight-line cap without scaling one small mound to four times its design size.
    BIG_SPEC = [(1.70, 2.10, "MAT_shrub_light"), (2.15, 2.60, "MAT_shrub_light"),
                (2.60, 3.10, "MAT_shrub"), (1.55, 3.40, "MAT_shrub_light")]
    for i, (r, h, m) in enumerate(BIG_SPEC):
        add(f"big{i}", (m, "MAT_shrub"), make_shrub_mesh, h, seed=360 + i, radius=r, height=h,
            card=0.135, form="mound" if i != 3 else "upright", cover=1.75)
    for i, (r, h) in enumerate(((0.62, 1.05), (0.78, 1.35), (0.95, 1.60))):
        add(f"maho{i}", ("MAT_shrub_light", "MAT_shrub"), make_shrub_mesh, h, seed=320 + i, radius=r, height=h,
            card=0.105, form="upright", cover=1.1)
    for i in range(3):
        add(f"agap{i}", ("MAT_reeds", "MAT_reeds"), make_blade_clump, 0.62 + 0.12 * i, seed=340 + i,
            height=0.62 + 0.12 * i, blades=70, width=0.050, arch=0.55, spread=0.30)
    for i in range(3):
        add(f"reed{i}", ("MAT_shrub_dry", "MAT_reeds"), make_blade_clump, 1.0 + 0.22 * i, seed=400 + i,
            height=1.0 + 0.22 * i, blades=54, width=0.045, arch=0.18, spread=0.26)
    for i in range(3):
        add(f"twig{i}", ("MAT_shrub_dry", "MAT_reeds"), make_twig_shrub_mesh, 0.9 + 0.25 * i, seed=350 + i,
            radius=0.5 + 0.2 * i, height=0.9 + 0.25 * i, twigs=70)

    # the clamp below has to work on the mesh's real z extent, not on the nominal height the factory was asked
    # for: round 03's "1.2 m" shrubs measured 1.87 m in the file because the mound meshes overshoot their nominal
    # height and the instancing step then adds its own +-15 % z jitter.
    REAL_H = {}
    for k, (_, lods, _) in src.items():
        hh = []
        for me in lods.values():                # LOD1/LOD2 use wider cards, so they are the taller meshes
            zs = [v.co.z for v in me.vertices]
            if zs:
                hh.append(max(zs) - min(zs))
        REAL_H[k] = max(hh) if hh else src[k][2]
    Z_JITTER_MAX = 1.15

    mats = {k: L.mat_or(*m) for k, (m, _, _) in src.items()}
    for k, (_, lods, _) in src.items():
        for me in lods.values():
            me.materials.append(mats[k])

    placed = []            # (key, (x, y, z), rot, scale)
    walk_dropped = [0]     # round 9: candidates refused by the colonnade-gallery keep-out

    def land_ok(x, y, min_shore=0.0, max_shore=1e9):
        d = LAGOON_FIELD.signed(x, y)
        if d < min_shore or d > max_shore:
            return False
        if math.hypot(x + 14.1, y - 100.0) < 34.0:      # hero camera foreground stays clean (user image, ref 169)
            return False
        if math.hypot(x - 81.0, y - 12.04) < 17.0:     # QA-03-9: cam 03's own foreground - a 0.9 m bush 3 m from an
            return False                               # 18 mm lens is nothing but black leaf cards in the shade
        if math.hypot(x, y) < APRON_R + 1.0:
            return False
        if any(L.point_in_poly(x, y, L.offset_polygon(p, 2.5)) for p in COLONNADE_ROOFS):
            return False
        if not L.gallery_clear(x, y):                  # round 9, see GALLERY_KEEPOUT in env_lib
            return False
        if HALL_FIELD.signed(x, y) < 1.0:
            return False
        return True

    def put(key, x, y, dz=-0.06, s=(0.58, 1.80)):
        # Round 9 (LIGHT r14's flythrough clearance): the OSM roof polygon above is NOT the modelled colonnade -
        # over the middle of both wings its outer edge falls INSIDE the arc ARCH strikes the column rows about, so
        # "plant 2.8 / 4.5 m outside the footprint" put shrubs on the gallery floor (the walk probe measured a
        # nearest origin of 0.26 m against a 2.80 m clear width).  The keep-out is the arc, read from arch_params.
        # It is enforced HERE, not only in `land_ok`, because the embayment fringe and the islet call `put` direct.
        if not L.gallery_clear(x, y):
            walk_dropped[0] += 1
            return
        sc = rnd.uniform(*s) * rnd.uniform(0.85, 1.18)        # QA-03-14: 3.1:1 nominal size spread
        h = REAL_H[key] * sc * Z_JITTER_MAX
        zg = terrain_height(x, y)
        cap = band_sightline_cap(x, y, zg)                    # QA-04-4 / QA-03-13, see the top of this file
        cap = SHRUB_H_CEILING if cap is None else min(cap, SHRUB_H_CEILING)
        if h > cap:
            sc *= cap / h
        placed.append((key, (x, y, zg + dz), rnd.uniform(0, 6.283), sc))

    def clump(cx, cy, n, spread, keys, min_shore=0.9, max_shore=7.0, s=(0.58, 1.80), dz=-0.06):
        last = None
        for _ in range(n):
            x, y = cx + rnd.uniform(-spread, spread), cy + rnd.uniform(-spread, spread)
            if not land_ok(x, y, min_shore, max_shore):
                continue
            # QA-02-18: never two neighbours off the same source mesh
            choices = [k for k in keys if k != last] or list(keys)
            key = rnd.choice(choices)
            last = key
            put(key, x, y, dz=dz, s=s)

    MOUNDS = tuple(f"pitto{i}" for i in range(len(MOUND_SPEC)))
    BIG = tuple(f"big{i}" for i in range(len(BIG_SPEC)))
    LOWMOUNDS = ("pitto0", "pitto1", "pitto2", "pitto3", "pitto5", "pitto8")
    MAHONIA = ("maho0", "maho1", "maho2")
    AGAP = ("agap0", "agap1", "agap2")
    REEDS = ("reed0", "reed1", "reed2")
    TWIGS = ("twig0", "twig1", "twig2")
    DRY = REEDS + TWIGS

    # 1. rotunda peninsula: dense on the north-east (user image, right of the rotunda), open on the south-east.
    #    ref 169's shore is a continuous mass of foliage down to the rip-rap, so the belt is closed, not dotted.
    for (x, y) in L.resample_polyline(L.offset_polygon(LAGOON, 2.4), 2.9, closed=True):
        r = math.hypot(x, y)
        if not (APRON_R + 1.0 < r < 49.0):
            continue
        az = math.degrees(math.atan2(y, -x)) % 360
        ne = L.smoothstep(150.0, 60.0, abs(az - 40.0)) if az < 180 else 0.0
        se = L.smoothstep(150.0, 60.0, abs(az - 140.0)) if az < 200 else 0.0
        # QA-03-14: a ~11 m gate opens and closes the belt, so the gaps between clumps are metres long and the
        # spacing standard deviation is a real fraction of the mean instead of Poisson noise.
        gate = L.fnoise(x, y, 0.095, 91) + 0.55 * L.fnoise(x, y, 0.031, 92)
        if gate < -0.16:
            continue
        p = (0.68 + 0.26 * ne - 0.18 * se) * L.smoothstep(-0.16, 0.25, gate)
        if rnd.random() < p:
            # QA-04-4: the hero shoreline gets the big mounds.  A second noise field decides which clumps are the
            # 2-3.5 m ones, so the belt reads as a run of tall mounds with lower stuff between them rather than a
            # uniformly raised hedge - ref 169's shore is exactly that.
            tall = L.fnoise(x, y, 0.055, 94) + 0.4 * L.fnoise(x, y, 0.14, 95)
            if tall > -0.05:
                keys = BIG + MOUNDS + MAHONIA if ne > 0.35 else BIG[:3] + LOWMOUNDS + MAHONIA
                clump(x, y, rnd.randint(2, 5), 3.0, keys, min_shore=0.5, max_shore=10.0, s=(0.80, 1.85))
            else:
                keys = MOUNDS + MAHONIA if ne > 0.5 else LOWMOUNDS + MAHONIA
                clump(x, y, rnd.randint(2, 5), 2.6, keys, min_shore=0.5, max_shore=9.0)
        if rnd.random() < 0.50:
            clump(x, y, rnd.randint(1, 3), 1.6, AGAP, min_shore=0.25, max_shore=3.2)
        # QA-02-18 wanted warm dry material in the hero's own shore band; round 6 measured the result at
        # saturation 0.73 against ref 169's 0.64 over the same crop, with the rust-coloured twig clumps reading
        # as the loudest thing on the shore.  In the photo they are a handful of bare shrubs at frame-left, not
        # a third of the belt, so the probability comes back from 0.52 to 0.30.
        if rnd.random() < 0.30:
            clump(x, y, rnd.randint(1, 3), 2.0, DRY, min_shore=0.4, max_shore=6.5)
    # 2. the rest of the shore: the same belt, a little sparser, with more dry reeds at the water
    for (x, y) in L.resample_polyline(L.offset_polygon(LAGOON, 2.0), 3.4, closed=True):
        if math.hypot(x, y) < 50 or not land_ok(x, y, 0.4, 9.0):
            continue
        if L.fnoise(x, y, 0.085, 93) < -0.20:                 # QA-03-14: same gate on the outer shore
            continue
        if rnd.random() < 0.58:
            clump(x, y, rnd.randint(2, 4), 2.8, LOWMOUNDS + MAHONIA, min_shore=0.5, max_shore=9.0)
        if rnd.random() < 0.35:
            clump(x, y, 1, 1.5, TWIGS, min_shore=0.5, max_shore=6.0)
        if rnd.random() < 0.62:
            clump(x, y, rnd.randint(1, 3), 1.8, REEDS, min_shore=0.2, max_shore=3.4)
        if rnd.random() < 0.45:
            clump(x, y, rnd.randint(1, 3), 1.6, AGAP, min_shore=0.2, max_shore=3.0)
    # 2b. bank cover: low mounds sitting on the rip-rap bank itself, so the pale stone band is broken up
    #     (in ref 169 the bank is visible only in gaps between the bushes)
    for (x, y) in L.resample_polyline(L.offset_polygon(LAGOON, 1.2), 2.6, closed=True):
        if rnd.random() < 0.50:
            clump(x, y, rnd.randint(1, 3), 1.3, LOWMOUNDS + TWIGS, min_shore=0.15, max_shore=2.6)
    # 2c. peninsula planting band 9-18 m back from the water, between the shore belt and the podium (lead's call
    #     after the hero camera stayed put): ref 169 shows beds of mounded shrubs and low trees there, not bare lawn.
    #     Beds, not a carpet - the gaps keep the mown lawn reading.
    n_band = len(placed)
    keys_band = LOWMOUNDS + MAHONIA + AGAP + REEDS
    for off in (8.5, 11.5, 14.5, 17.5):
        for (x, y) in L.resample_polyline(L.offset_polygon(LAGOON, off), 2.9, closed=True):
            r = math.hypot(x, y)
            if not (APRON_R - 1.0 < r < 58.0):       # the strip between the platform apron and the shore belt
                continue
            bed = L.fnoise(x, y, 0.10, 31)           # ~10 m beds with mown lawn between them
            if bed < -0.20:
                continue
            if rnd.random() < 0.70 + 0.25 * bed:
                # QA-04-4: the bed between the shore belt and the podium carries the big mounds too - in ref 169
                # the foliage in front of the podium is continuous from the water up to the rostra.  The sight-line
                # cap (band_sightline_cap) is what keeps the Greek-key course clear, not a height rule here.
                kb = keys_band + (BIG if bed > 0.05 else BIG[:2])
                clump(x, y, rnd.randint(2, 6), 2.8, kb, min_shore=6.5, max_shore=21.0, s=(0.70, 1.85))
    n_band = len(placed) - n_band

    # 2d. QA-04-14: the south embayment in front of cam 02 (70.5, 25.6, 1.1).  The bottom 12 % of that frame
    #     (rows 634-720 of 720) lands on the water 9-26 m out - world x 40-64, y -1..31 - and the near bank sits
    #     7.4 m from the lens, just under the frame edge, so the foreground was a flat sheet of water with no edge
    #     at all.  A reed / agapanthus fringe standing IN the shallows (signed distance negative = in the water)
    #     plus the heavier rip-rap added in build_riprap gives that strip a readable shore.
    n_emb = len(placed)
    for (x, y) in L.resample_polyline(L.offset_polygon(LAGOON, 0.4), 1.6, closed=True):
        d_cam = math.hypot(x - CAM02_XY[0], y - CAM02_XY[1])
        if not (4.0 < d_cam < 42.0):
            continue
        gate = L.fnoise(x, y, 0.13, 96)
        if gate < -0.30:                       # reed beds are patchy: bare stone between the stands
            continue
        # emergent stands: 0.2-3.2 m OUT into the water, tall enough to break the horizon of the strip
        for _ in range(rnd.randint(1, 3)):
            ox, oy = x + rnd.uniform(-1.4, 1.4), y + rnd.uniform(-1.4, 1.4)
            off = LAGOON_FIELD.signed(ox, oy)
            if not (-3.2 < off < 1.4):
                continue
            key = rnd.choice(REEDS + AGAP if off < 0.2 else REEDS + TWIGS + AGAP)
            put(key, ox, oy, dz=-0.10 if off < 0 else -0.06, s=(0.85, 1.75))
        # bank mounds behind them, so the strip has a silhouette above the reeds
        if rnd.random() < 0.55:
            clump(x, y, rnd.randint(1, 3), 2.2, LOWMOUNDS + MAHONIA + BIG[:2],
                  min_shore=0.6, max_shore=7.0, s=(0.70, 1.70))
    log(f"shrubs: south-embayment cam02 fringe {len(placed) - n_emb} clumps")

    # 3. foundation planting along the colonnade fronts
    # QA-03-9: everything along the colonnade fronts sits in the wing's own shade, where MAT_shrub's dark cards
    # read as black holes at cam 03.  Use the pale / dry families and mahonia there instead.
    PALE = ("pitto1", "pitto5", "pitto7", "maho0", "maho1", "maho2")
    n_walk = len(placed)
    for p in COLONNADE_ROOFS[:2]:
        # QA-05-11: a planting EDGE against the new paving (build_paving pave to offset 1.6, the terrain lays
        # gravel to 2.0 and soil from there to 5.5).  Ref 128 has a low continuous edge - agapanthus and clipped
        # low mounds - right where the slabs stop, then the deeper bed behind it.  Low and pale, because
        # everything here stands in the wing's own shade (the QA-03-9 finding).
        for (x, y) in L.resample_polyline(L.offset_polygon(p, 2.8), 3.0, closed=True):
            if land_ok(x, y, 1.0) and rnd.random() < 0.60:
                clump(x, y, rnd.randint(1, 2), 1.0, AGAP + ("pitto0", "pitto1", "maho0"),
                      min_shore=1.0, max_shore=1e9, s=(0.55, 1.05))
        for (x, y) in L.resample_polyline(L.offset_polygon(p, 4.5), 4.2, closed=True):
            if land_ok(x, y, 1.0) and rnd.random() < 0.58:
                clump(x, y, rnd.randint(1, 3), 2.0, PALE + TWIGS, min_shore=1.0, max_shore=1e9)
    log(f"shrubs: colonnade walk edge + bed {len(placed) - n_walk} instances, "
        f"{walk_dropped[0]} candidates refused by the {L.GALLERY_KEEPOUT} m gallery keep-out")
    # 4. the wooded islet: dense dark mounds under the willows
    for _ in range(80):
        p = ISLETS[0]
        xs = [q[0] for q in p]
        ys = [q[1] for q in p]
        x, y = rnd.uniform(min(xs), max(xs)), rnd.uniform(min(ys), max(ys))
        if L.point_in_poly(x, y, p) and ISLET_FIELDS[0].signed(x, y) < -0.8:
            put(rnd.choice(MOUNDS + AGAP + REEDS), x, y, dz=-0.05)

    # ---- instancing: three objects per placement, mesh chosen by distance to the nearest QA camera
    try:
        import qa_cameras
        CAM_XY = [(c["loc"][0], c["loc"][1]) for c in qa_cameras.CAMERAS]
    except Exception:
        CAM_XY = [(-14.1, 100.0)]
    lod_colls = {lod: common.get_collection(f"ENV_shrubs_LOD{lod}", parent=coll) for lod in (0, 1, 2)}
    counts, tris = {}, {0: 0, 1: 0, 2: 0}
    dry_keys = set(DRY)
    n_dry = 0
    for i, (key, loc, rot, sc) in enumerate(placed):
        cam_d = min(math.hypot(loc[0] - cx, loc[1] - cy) for (cx, cy) in CAM_XY)
        shift = 0 if cam_d <= SHRUB_FAR else (1 if cam_d <= 2.0 * SHRUB_FAR else 2)
        sxy = sc * rnd.uniform(0.88, 1.14)
        for lod in (0, 1, 2):
            me = src[key][1][min(2, lod + shift)]
            obj = bpy.data.objects.new(f"ENV_shrub_{key}_{i:04d}_LOD{lod}", me)
            obj.location = loc
            obj.rotation_euler = (0.0, 0.0, rot)
            obj.scale = (sxy, sc * rnd.uniform(0.88, 1.14), sc * rnd.uniform(0.9, 1.15))
            obj.hide_render = lod != 0
            obj.hide_viewport = lod != 1
            lod_colls[lod].objects.link(obj)
            tris[lod] += L.tri_count(obj)
        counts[key] = counts.get(key, 0) + 1
        n_dry += key in dry_keys
    card_max = max(src[k][1][0].get("card_m", 0.0) * 1.45 for k in src if src[k][1][0].get("card_m"))
    log(f"shrubs: {len(placed)} instances ({n_band} in the peninsula band, {100.0 * n_dry / max(1, len(placed)):.0f} % "
        f"warm dry) of {len(src)} sources x 3 LODs; tris LOD0 {tris[0]:,} LOD1 {tris[1]:,} LOD2 {tris[2]:,}; "
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
            if not L.gallery_clear(x, y):        # round 9: never a lamp post on the colonnade walk
                continue
            tr.append(((x + 2.0 * rnd.uniform(-0.2, 0.2), y, terrain_height(x, y)), 0.0, 1.0))
    if tr:
        L.join_instances("ENV_lamp_posts", me, tr, coll, m)
    bpy.data.meshes.remove(me)


# ----------------------------------------------------------------------------- main
def main():
    terrain, paths = build_terrain()
    build_paving()
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
        env_backdrop.build_all(SUB, terrain_height, SITE, HALL, LAGOON_FIELD,
                               hall_field=HALL_FIELD, colonnade_polys=COLONNADE_ROOFS)
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
