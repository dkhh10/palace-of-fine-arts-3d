"""Phase 10 r1, step 3 -- a third UV layer `UVBake` on the hero-facing rotunda meshes: a non-overlapping atlas layout
for the registered multi-view photo projection (docs/briefs/phase10_projection.md step 3).  ARCH-routed by the lead.

    scripts/blender_run.sh 900 -- --background assets/architecture.blend --python scripts/arch_uvbake.py -- [--dry] [--save]

Adds exactly ONE UV layer, `UVBake`, to the meshes listed below and changes nothing else: `UVMap` stays first, active
and active_render; `UVProj` and `UVProj_valid` are untouched (hashed before and after); vertex / face counts are
checked unchanged.  Objects that share a mesh (the LOD0/LOD1 courses, the 16 rotunda columns, the 16 column bases)
get the layer once, on the shared mesh -- so the 16 columns share ONE atlas region: the projection fills it with the
median over every registered view of every visible column (docs/materials_notes.md, Phase 10 r1).

Atlas groups: 0 attic, 1 entablature, 2 drum + columns, 3 the lagoon arch, each packed into one 2048 QUADRANT
(g % 2, g // 2) of a single shared 4096 atlas (so one image node serves every material), inset 1 %.
Layout: see the comment block above `unwrap_ring` (sector x facing-class planar charts in metres for the rings,
per-component front projection for the ornament courses, Smart UV Project rescaled to metres for the shared column /
base meshes and the arch; every island scaled by its visibility weight; one CARDINAL-rotation CONCAVE pack per group).
Measured 2026-09-24 (quadrant layout, 7cdede75): hero-front (faces 07/00/01, columns) 43 / 50 / 64 / 136 texels per
metre in the 2048 quadrants, fill 41 / 29 / 44 / 13 % (the checkpoint's Smart-UV layout: 27 / 19 / 36 / 295 in a whole
4096 each).  The lead accepted the density (the registered photos resolve 16-40 px/m).  200 texels/m is out of reach for the attic group in one
4096 atlas: its 741 m2 of weight-1 faces alone need 29.6 M texels at 200/m, the atlas has 16.8 M.

Checks that fail the run (and block --save): texel overlap (rasterised pixel-centre coverage > 1 at 2048 per group,
tolerance 0.05 % of covered texels for float ties on shared edges), UV outside 0..1, layer order / active / render
flags, UVProj hash, vertex / face counts.  Prints texels per metre per group (target >= 200 on the lagoon side).
Writes assets/textures/projection2/uvbake_groups.json (group -> object names, for mat_p10_meshdump.py, plus `sha1`:
mesh -> SHA-1 of its UVBake layer; a differing layout fails the run unless --write-hashes).  Exit code 1 on any
failure (review part 1, finding 6).  `--dry` only resolves the objects and exits before every check.
"""
import bpy, bmesh, sys, os, math, json, hashlib
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common

args = common.script_args()
DRY = "--dry" in args
SAVE = "--save" in args
UV = "UVBake"
ATLAS = 4096
BACK_SCALE = 0.25
QUAD_INSET = 0.01
MARGIN = 0.0012          # of a group's own 0..1 layout before the quadrant remap: ~2.5 px at 2048 per quadrant
SHAPE = args[args.index("--shape") + 1] if "--shape" in args else "CONCAVE"
ROTM = args[args.index("--rot") + 1] if "--rot" in args else "CARDINAL"
ANGLE = {1: 80.0}        # the entablature's egg / dentil / modillion courses: fewer, larger islands
FACE_AZ0 = 82.0
HERO_FACES = (0, 7, 1)
OUT = common.ASSETS / "textures" / "projection2"
(OUT / "work").mkdir(parents=True, exist_ok=True)

attic = ["ARCH_rotunda_attic_base", "ARCH_rotunda_attic_cornice", "ARCH_rotunda_attic_roof"]
for k in HERO_FACES:
    attic += [f"ARCH_rotunda_attic_panel_{k:02d}", f"ARCH_rotunda_attic_frame_{k:02d}",
              f"ARCH_rotunda_attic_niche_{k:02d}",
              f"ARCH_rotunda_attic_pilaster_{k:02d}_a", f"ARCH_rotunda_attic_pilaster_{k:02d}_b",
              f"ARCH_rotunda_attic_corner_{k:02d}", f"ARCH_rotunda_attic_corner_cap_{k:02d}"]
entab = ["ARCH_rotunda_entablature", "ARCH_rotunda_dentils_LOD0", "ARCH_rotunda_dentils_LOD1",
         "ARCH_rotunda_modillions_LOD0", "ARCH_rotunda_modillions_LOD1", "ARCH_rotunda_eggs_LOD0"]
drum = ["ARCH_rotunda_drum", "ARCH_rotunda_drum_band", "ARCH_rotunda_drum_cornice"]
drum += [f"ARCH_rotunda_column_{i:02d}_LOD0" for i in range(16)]
drum += ["ARCH_rotunda_colbase_00_plinth", "ARCH_rotunda_colbase_00_torus"]
drum += [f"ARCH_rotunda_colbase_{i:02d}_{j}" for i in range(1, 16) for j in (0, 1)]
arch = ["ARCH_rotunda_archivolt_00", "ARCH_rotunda_impost_00_a", "ARCH_rotunda_impost_00_b"]
GROUPS = {0: attic, 1: entab, 2: drum, 3: arch}


def world_matrix(o):
    if o.parent is not None or tuple(o.delta_location) != (0.0, 0.0, 0.0) or tuple(o.delta_scale) != (1.0, 1.0, 1.0):
        raise SystemExit(f"[uvbake] {o.name} is parented or has a delta transform")
    return o.matrix_basis


def uv_hash(me, name):
    if name not in me.uv_layers:
        return None
    a = np.zeros(len(me.loops) * 2, np.float32)
    me.uv_layers[name].data.foreach_get("uv", a)
    return hashlib.sha1(a.tobytes()).hexdigest()


def attr_hash(me, name):
    if name not in me.attributes:
        return None
    at = me.attributes[name]
    a = np.zeros(len(at.data), np.float32)
    at.data.foreach_get("value", a)
    return hashlib.sha1(a.tobytes()).hexdigest()


# ----------------------------------------------------------------------------- resolve
fails = 0
reps = {}          # group -> list of representative objects (one per mesh)
names_out = {}
for g, names in GROUPS.items():
    seen, rl, found = set(), [], []
    for n in names:
        o = bpy.data.objects.get(n)
        if o is None or o.type != "MESH":
            print(f"[uvbake] MISSING {n}")
            fails += 1
            continue
        found.append(n)
        if o.data.name in seen:
            continue
        seen.add(o.data.name)
        rl.append(o)
    reps[g] = rl
    names_out[g] = found
    print(f"[uvbake] group {g}: {len(found)} objects, {len(rl)} meshes")
before = {}
for g, rl in reps.items():
    for o in rl:
        me = o.data
        before[me.name] = dict(v=len(me.vertices), f=len(me.polygons), uvmap=uv_hash(me, "UVMap"),
                               uvproj=uv_hash(me, "UVProj"), flag=attr_hash(me, "UVProj_valid"),
                               layers=[u.name for u in me.uv_layers if u.name != UV])
if DRY:
    raise SystemExit(0)

# ----------------------------------------------------------------------------- unwrap + pack per group
for o in bpy.context.view_layer.objects:
    o.select_set(False)


STATIONS = [np.array([-math.cos(math.radians(a)) * 130.0, math.sin(math.radians(a)) * 130.0, 1.0])
            for a in (FACE_AZ0 - 30.0, FACE_AZ0, FACE_AZ0 + 30.0)]     # the registered cameras' spread (probe)


def face_weight(c, n):
    """1 where a face (world centre c, world normal n) faces at least one lagoon station and lies on the lagoon
    half; BACK_SCALE elsewhere (roofs, tops, the far side, inward faces: no registered photo can see them)."""
    az = np.degrees(np.arctan2(c[:, 1], -c[:, 0])) % 360.0
    d = np.abs((az - FACE_AZ0 + 180.0) % 360.0 - 180.0)
    vis = np.zeros(len(c), bool)
    for S in STATIONS:
        v = S - c
        v /= np.linalg.norm(v, axis=1, keepdims=True)
        vis |= (n * v).sum(1) > 0.10
    return np.where(vis & (d <= 80.0), 1.0, BACK_SCALE)


def to_world(o, pc, pn):
    mw = np.array(world_matrix(o))
    c = pc @ mw[:3, :3].T + mw[:3, 3]
    n = pn @ np.linalg.inv(mw[:3, :3])
    n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
    return c, n


# Layout (round-1 fix of the checkpoint's density finding: Smart UV Project joined every octagon ring into one
# 110 m strip, so the pack could not scale past 19-36 texels/m):
#   ring meshes     -> charts = (octagon sector of the face centre) x (facing class); each chart is a planar
#                      projection in METRES in the sector frame (front: tangent x z; soffit/top: tangent x radial;
#                      side: radial x z; back: -tangent x z); islands = connected faces of one chart.
#   ornament meshes -> (dentils / modillions / eggs) per connected component: every face that does not look away
#                      from the component's own front direction is projected on the component's front plane (sides,
#                      tops and soffits collapse to slivers: a 0.1-0.2 m course is one texel column deep at the
#                      photo's resolution); the faces looking away go to a small separate island.
#   shared / arch   -> (the 16 columns, the bases, the archivolt and imposts) Smart UV Project, rescaled to metres.
#   Every island is then scaled by its WEIGHT = sector weight (faces 07/00/01 1.0, 06/02 0.35, rest 0.12) x class
#   weight (front 1, soffit / side 0.6, top 0.25, back 0.12), so the atlas spends its texels where the registered
#   photos (azimuth 59-107 deg, eye height) can see; one pack per group preserves the relative scale.
SECTOR_W = {0: 1.0, 1: 1.0, 7: 1.0, 2: 0.35, 6: 0.35}
SECTOR_W_REST = 0.1
CLASS_W = dict(F=1.0, D=0.5, S=0.5, U=0.1, B=0.08)
AXIS_R = 6.0          # faces centred within 6 m of the axis (drum / attic caps under the dome) are never seen: 0.05
ORN_KEYS = ("dentils", "modillions", "eggs")


def compass_az(c):
    return np.degrees(np.arctan2(c[..., 1], -c[..., 0])) % 360.0


def az_vec(az):
    a = np.radians(az)
    return np.stack([-np.cos(a), np.sin(a), np.zeros_like(a)], -1)


def sector_of(c):
    return np.round(((compass_az(c) - FACE_AZ0) % 360.0) / 45.0).astype(int) % 8


def mesh_arrays(o):
    me = o.data
    mw = np.array(world_matrix(o))
    co = np.zeros(len(me.vertices) * 3, np.float64); me.vertices.foreach_get("co", co)
    wco = co.reshape(-1, 3) @ mw[:3, :3].T + mw[:3, 3]
    nf = len(me.polygons)
    fc = np.zeros(nf * 3); me.polygons.foreach_get("center", fc)
    fn = np.zeros(nf * 3); me.polygons.foreach_get("normal", fn)
    fc = fc.reshape(-1, 3) @ mw[:3, :3].T + mw[:3, 3]
    fn = fn.reshape(-1, 3) @ np.linalg.inv(mw[:3, :3])
    fn /= np.maximum(np.linalg.norm(fn, axis=1, keepdims=True), 1e-12)
    ls = np.zeros(nf, np.int32); me.polygons.foreach_get("loop_start", ls)
    lt = np.zeros(nf, np.int32); me.polygons.foreach_get("loop_total", lt)
    lv = np.zeros(len(me.loops), np.int32); me.loops.foreach_get("vertex_index", lv)
    lface = np.repeat(np.arange(nf), lt)
    return wco, fc, fn, lv, lface


def components(me, label):
    """Connected components of faces across edges, restricted to faces with the same label."""
    nf = len(me.polygons)
    parent = np.arange(nf)
    def find(i):
        r = i
        while parent[r] != r:
            r = parent[r]
        while parent[i] != r:
            parent[i], i = r, parent[i]
        return r
    ek = {}
    for p in me.polygons:
        for ek_ in p.edge_keys:
            ek.setdefault(ek_, []).append(p.index)
    for fs in ek.values():
        for a, b in zip(fs[:-1], fs[1:]):
            if label[a] == label[b]:
                ra, rb = find(a), find(b)
                if ra != rb:
                    parent[ra] = rb
    return np.array([find(i) for i in range(nf)])


def unwrap_ring(o):
    """Returns per-loop UV (metres x weight, charts offset apart), per-face weight."""
    me = o.data
    wco, fc, fn, lv, lface = mesh_arrays(o)
    sec = sector_of(fc)
    d = az_vec(FACE_AZ0 + 45.0 * sec)
    z = np.array([0, 0, 1.0])
    t = np.cross(z, d)
    nd, nz, nt = (fn * d).sum(1), fn[:, 2], (fn * t).sum(1)
    cls = np.where(nz >= 0.6, "U", np.where(nz <= -0.6, "D", np.where(nd >= 0.35, "F",
                   np.where(nd <= -0.35, "B", "S"))))
    code = sec * 8 + np.searchsorted(np.array(sorted("BDFSU")), cls)
    comp = components(me, code)
    w = np.array([SECTOR_W.get(int(s), SECTOR_W_REST) for s in sec]) * np.array([CLASS_W[c] for c in cls])
    w = np.where(np.hypot(fc[:, 0], fc[:, 1]) < AXIS_R, 0.05, w)
    P = wco[lv]
    f = lface
    dl, tl = d[f], t[f]
    pz, pd, pt = P[:, 2], (P * dl).sum(1), (P * tl).sum(1)
    c = cls[f]
    u = np.select([c == "F", c == "B", c == "U", c == "D", c == "S"],
                  [pt, -pt, pt, pt, pd * np.sign(nt[f] + 1e-9)])
    v = np.select([c == "F", c == "B", c == "U", c == "D", c == "S"], [pz, pz, pd, -pd, pz])
    return np.stack([u, v], 1) * w[f][:, None], comp[f], w, cls


def unwrap_orn(o):
    me = o.data
    wco, fc, fn, lv, lface = mesh_arrays(o)
    comp0 = components(me, np.zeros(len(me.polygons), int))
    area = np.zeros(len(me.polygons)); me.polygons.foreach_get("area", area)
    fdir = np.zeros((len(me.polygons), 3))
    for r in np.unique(comp0):
        m = comp0 == r
        rad = az_vec(compass_az(fc[m].mean(0)))
        nn = fn[m] * area[m, None]
        nn = nn[(fn[m] @ rad) > 0.2].sum(0)
        nn[2] = 0.0
        dd = nn / np.linalg.norm(nn) if np.linalg.norm(nn) > 1e-9 else rad
        fdir[m] = dd
    away = (fn * fdir).sum(1) < -0.05
    comp = components(me, comp0 * 2 + away)
    sec = sector_of(fc)
    w = np.array([SECTOR_W.get(int(s), SECTOR_W_REST) for s in sec]) * np.where(away, CLASS_W["B"], 1.0)
    z = np.array([0, 0, 1.0])
    t = np.cross(z, fdir)
    P = wco[lv]; f = lface
    u = (P * t[f]).sum(1) * np.where(away[f], -1.0, 1.0)
    v = P[:, 2]
    cls = np.where(away, "B", "F")
    return np.stack([u, v], 1) * w[f][:, None], comp[f], w, cls


def rescale_smart(o, weight=1.0):
    """Smart-projected UVs -> metres (per mesh: sqrt(3D area / UV area)) x weight."""
    me = o.data
    uvl = me.uv_layers[UV]
    uv = np.zeros(len(me.loops) * 2); uvl.data.foreach_get("uv", uv); uv = uv.reshape(-1, 2)
    me.calc_loop_triangles()
    n = len(me.loop_triangles)
    li = np.zeros(n * 3, np.int32); me.loop_triangles.foreach_get("loops", li)
    vi = np.zeros(n * 3, np.int32); me.loop_triangles.foreach_get("vertices", vi)
    wco, *_ = mesh_arrays(o)
    P = wco[vi].reshape(n, 3, 3); U = uv[li].reshape(n, 3, 2)
    a3 = 0.5 * np.linalg.norm(np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0]), axis=1).sum()
    e = U[:, 1:] - U[:, :1]
    a2 = 0.5 * np.abs(e[:, 0, 0] * e[:, 1, 1] - e[:, 0, 1] * e[:, 1, 0]).sum()
    uvl.data.foreach_set("uv", (uv * math.sqrt(a3 / max(a2, 1e-12)) * weight).ravel())


def is_smart(o, g):
    return g == 3 or "column" in o.data.name or "colbase" in o.data.name


FACE_W = {}           # mesh name -> per-face weight (the report's hero-front density uses weight == 1)
vis_state = {}
for g, rl in reps.items():
    for o in rl:
        vis_state[o.name] = (o.hide_viewport, o.hide_get(), o.hide_render)
for g, rl in reps.items():
    for o in rl:
        me = o.data
        if UV in me.uv_layers:
            me.uv_layers.remove(me.uv_layers[UV])
        me.uv_layers.new(name=UV, do_init=False)
        me.uv_layers.active = me.uv_layers[UV]
        o.hide_set(False); o.hide_viewport = False
    smart = [o for o in rl if is_smart(o, g)]
    if smart:
        for o in smart:
            o.select_set(True)
        bpy.context.view_layer.objects.active = smart[0]
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.uv.smart_project(angle_limit=math.radians(60.0), island_margin=0.0, area_weight=0.0,
                                 correct_aspect=True, scale_to_bounds=False)
        bpy.ops.object.mode_set(mode="OBJECT")
        for o in smart:
            o.select_set(False)
            rescale_smart(o)
            FACE_W[o.data.name] = np.ones(len(o.data.polygons))
            print(f"[uvbake]   {o.data.name:40s} smart project, metres, weight 1")
    off = 0.0
    for o in rl:
        if is_smart(o, g):
            continue
        orn = any(k in o.data.name for k in ORN_KEYS)
        uv, comp_l, w, cls = (unwrap_orn if orn else unwrap_ring)(o)
        # separate every island in UV space before the pack (Blender finds islands by UV connectivity):
        # island k gets its own 0.0 origin shifted by a unique offset along u
        ids, inv = np.unique(comp_l, return_inverse=True)
        mn = np.full((len(ids), 2), np.inf)
        np.minimum.at(mn, inv, uv)
        mx = np.full((len(ids), 2), -np.inf)
        np.maximum.at(mx, inv, uv)
        wid = mx[:, 0] - mn[:, 0] + 1.0
        start = off + np.concatenate([[0.0], np.cumsum(wid)[:-1]])
        off = start[-1] + wid[-1]
        uv = uv - mn[inv] + np.stack([start[inv], np.zeros(len(inv))], 1)
        o.data.uv_layers[UV].data.foreach_set("uv", uv.ravel())
        FACE_W[o.data.name] = w
        print(f"[uvbake]   {o.data.name:40s} {'ornament' if orn else 'ring':8s} islands {len(ids):5d} "
              f"faces weight-1 {int((w >= 1).sum())}/{len(w)} classes "
              f"{ {c: int((cls == c).sum()) for c in 'FDSUB' if (cls == c).any()} }")
    for o in rl:
        o.select_set(True)
    bpy.context.view_layer.objects.active = rl[0]
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.select_all(action="SELECT")
    bpy.ops.uv.pack_islands(rotate=True, scale=True, margin_method="FRACTION", margin=MARGIN, shape_method=SHAPE, rotate_method=ROTM)
    bpy.ops.object.mode_set(mode="OBJECT")
    # one shared 4096 atlas image: group g -> quadrant (g % 2, g // 2), inset by QUAD_INSET so the atlas corner
    # (0, 0) -- where a mesh WITHOUT UVBake samples -- is empty (confidence 0 there, procedural fallback).
    qx, qy = g % 2, g // 2
    for o in rl:
        uvl = o.data.uv_layers[UV]
        a = np.zeros(len(o.data.loops) * 2); uvl.data.foreach_get("uv", a); a = a.reshape(-1, 2)
        a = (np.array([qx, qy]) + QUAD_INSET + (1.0 - 2 * QUAD_INSET) * a) / 2.0
        uvl.data.foreach_set("uv", a.ravel())
    for o in rl:
        o.select_set(False)
        me = o.data
        idx = me.uv_layers.find("UVMap")
        me.uv_layers.active_index = idx
        me.uv_layers["UVMap"].active_render = True
for n, (hv, hg, hr) in vis_state.items():          # the saved visibility flags are ARCH's, not ours
    o = bpy.data.objects[n]
    o.hide_viewport = hv; o.hide_set(hg); o.hide_render = hr

# ----------------------------------------------------------------------------- checks
RES_CHK = 2048


def raster_count(tris_uv, res):
    cnt = np.zeros((res, res), np.int32)
    T = tris_uv * res - 0.5                       # pixel-centre coordinates
    for t in T:
        x0, y0 = np.floor(t.min(0)).astype(int); x1, y1 = np.ceil(t.max(0)).astype(int)
        x0, y0 = max(x0, 0), max(y0, 0); x1, y1 = min(x1, res - 1), min(y1, res - 1)
        if x1 < x0 or y1 < y0:
            continue
        xs, ys = np.meshgrid(np.arange(x0, x1 + 1), np.arange(y0, y1 + 1))
        (ax, ay), (bx, by), (cx, cy) = t
        den = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if abs(den) < 1e-14:
            continue
        l1 = ((by - cy) * (xs - cx) + (cx - bx) * (ys - cy)) / den
        l2 = ((cy - ay) * (xs - cx) + (ax - cx) * (ys - cy)) / den
        inside = (l1 > 0) & (l2 > 0) & (1 - l1 - l2 > 0)
        cnt[ys[inside], xs[inside]] += 1
    return cnt


report = {}
for g, rl in reps.items():
    TU, A3, A2, W = [], 0.0, 0.0, []
    dens = []
    for o in rl:
        me = o.data
        after_layers = [u.name for u in me.uv_layers]
        b = before[me.name]
        ok = (after_layers == b["layers"] + [UV] and me.uv_layers.active.name == "UVMap"
              and me.uv_layers[0].name == "UVMap" and [u.name for u in me.uv_layers if u.active_render] == ["UVMap"]
              and uv_hash(me, "UVMap") == b["uvmap"] and uv_hash(me, "UVProj") == b["uvproj"]
              and attr_hash(me, "UVProj_valid") == b["flag"]
              and len(me.vertices) == b["v"] and len(me.polygons) == b["f"])
        if not ok:
            fails += 1
            print(f"[uvbake] LAYER/GEOMETRY CHECK FAIL {me.name}: layers {after_layers} "
                  f"active {me.uv_layers.active.name} render {[u.name for u in me.uv_layers if u.active_render]}")
        me.calc_loop_triangles()
        n = len(me.loop_triangles)
        li = np.zeros(n * 3, np.int32); me.loop_triangles.foreach_get("loops", li)
        vi = np.zeros(n * 3, np.int32); me.loop_triangles.foreach_get("vertices", vi)
        uv = np.zeros(len(me.loops) * 2, np.float32); me.uv_layers[UV].data.foreach_get("uv", uv)
        uvt = uv.reshape(-1, 2)[li].reshape(n, 3, 2).astype(np.float64)
        co = np.zeros(len(me.vertices) * 3, np.float32); me.vertices.foreach_get("co", co)
        mw = np.array(world_matrix(o))
        wco = co.reshape(-1, 3) @ mw[:3, :3].T + mw[:3, 3]
        P = wco[vi].reshape(n, 3, 3)
        a3 = 0.5 * np.linalg.norm(np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0]), axis=1)
        e = uvt[:, 1:] - uvt[:, :1]
        a2 = 0.5 * np.abs(e[:, 0, 0] * e[:, 1, 1] - e[:, 0, 1] * e[:, 1, 0])
        pc = P.mean(1)
        tp = np.zeros(n, np.int32); me.loop_triangles.foreach_get("polygon_index", tp)
        w = FACE_W[me.name][tp]
        front = (w >= 1.0) & (a3 > 1e-6)
        if front.any():
            dens.append((float(a3[front].sum()), float(a2[front].sum())))
        if (uvt < -1e-6).any() or (uvt > 1 + 1e-6).any():
            fails += 1
            print(f"[uvbake] UV OUTSIDE 0..1 on {me.name}")
        TU.append(uvt)
    TU = np.concatenate(TU)
    qx, qy = g % 2, g // 2
    TU = TU * 2.0 - np.array([qx, qy])                      # the group's quadrant back to 0..1
    if (TU < -1e-6).any() or (TU > 1 + 1e-6).any():
        fails += 1
        print(f"[uvbake] group {g} leaves its quadrant")
    cnt = raster_count(TU, RES_CHK)
    np.save(OUT / "work" / f"uvcov_{g}.npy", np.packbits(cnt > 0))
    cov = (cnt > 0).sum(); ovl = (cnt > 1).sum()
    a3f = sum(d[0] for d in dens); a2f = sum(d[1] for d in dens)
    tpm = math.sqrt(a2f * ATLAS * ATLAS / a3f)       # shared 4096 atlas units = the 2048 quadrant if a3f > 0 else 0.0
    bad = ovl > 0.0005 * cov
    fails += bad
    report[g] = dict(objects=names_out[g], meshes=[o.data.name for o in rl], triangles=int(len(TU)),
                     coverage=float(cov / RES_CHK ** 2), overlap_texels=int(ovl), overlap_frac=float(ovl / max(cov, 1)),
                     texels_per_m_front=tpm, front_area_m2=a3f)
    print(f"[uvbake] group {g}: tris {len(TU)} atlas fill {100 * cov / RES_CHK ** 2:.1f} % overlap texels {ovl} "
          f"({100 * ovl / max(cov, 1):.3f} %) {'FAIL' if bad else 'OK'}; weight-1 (faces 07/00/01 front, columns) {a3f:.0f} m2 at "
          f"{tpm:.0f} texels/m (2048 quadrant of the {ATLAS} atlas)")

# per-mesh SHA-1 of the UVBake layer: the committed atlases (PFA_p10_*.png) are only valid for this exact layout.
# A run whose layout differs from the committed hashes is a FAILURE unless --write-hashes (then the projection must
# be re-run).  arch_build.py's hook (lead) reads `fails` from the exec namespace and refuses to save when it is > 0.
gpath = OUT / "uvbake_groups.json"
committed = json.loads(gpath.read_text()).get("sha1", {}) if gpath.exists() else {}
sha = {}
for g, rl in reps.items():
    for o in rl:
        sha[o.data.name] = uv_hash(o.data, UV)
changed = sorted(k for k in sha if committed and committed.get(k) != sha[k])
_run_directly = "--python" in sys.argv and sys.argv[sys.argv.index("--python") + 1].endswith("arch_uvbake.py")
stale_atlases = bool(changed) and "--write-hashes" not in args
if stale_atlases:
    # Strict when run directly (protects a projected atlas); advisory inside the arch_build.py hook: a fresh build
    # lays out 4 ornament courses differently from the saved file (lead, 2026-09-24, renders/logs/p10_arch_hook_check.log),
    # and the atlases ship at weight 0 (decisions.md), so a rebuild must not be blocked by a stale-atlas warning.
    fails += 1 if _run_directly else 0
    print(f"[uvbake] UVBake LAYOUT DIFFERS from the committed hashes on {len(changed)} mesh(es) {changed[:5]}: the "
          f"projected atlases are stale (re-run the projection and pass --write-hashes)"
          + ("" if _run_directly else " -- WARNING only inside arch_build.py"))
gout = {str(g): v["objects"] for g, v in report.items()}
gout["sha1"] = sha if (not committed or "--write-hashes" in args) else committed
json.dump(gout, open(gpath, "w"), indent=1)
json.dump(report, open(OUT / "work" / "uvbake_report.json", "w"), indent=1)
if SAVE and not fails:
    common.save_blend(common.ASSETS / "architecture.blend")
    print("[uvbake] saved assets/architecture.blend")
elif SAVE:
    print(f"[uvbake] NOT SAVED: {fails} check(s) failed")
print(f"[uvbake] done, {fails} failure(s)")
if fails and _run_directly:                     # exec'd by arch_build.py: the hook reads `fails` instead
    raise SystemExit(1)
