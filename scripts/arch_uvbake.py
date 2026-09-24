"""Phase 10 r1, step 3 -- a third UV layer `UVBake` on the hero-facing rotunda meshes: a non-overlapping atlas layout
for the registered multi-view photo projection (docs/briefs/phase10_projection.md step 3).  ARCH-routed by the lead.

    scripts/blender_run.sh 900 -- --background assets/architecture.blend --python scripts/arch_uvbake.py -- [--dry] [--save]

Adds exactly ONE UV layer, `UVBake`, to the meshes listed below and changes nothing else: `UVMap` stays first, active
and active_render; `UVProj` and `UVProj_valid` are untouched (hashed before and after); vertex / face counts are
checked unchanged.  Objects that share a mesh (the LOD0/LOD1 courses, the 16 rotunda columns, the 16 column bases)
get the layer once, on the shared mesh -- so the 16 columns share ONE atlas region: the projection fills it with the
median over every registered view of every visible column (docs/materials_notes.md, Phase 10 r1).

Atlas groups (one 4096 atlas each, UV 0..1):  0 attic, 1 entablature, 2 drum + columns, 3 the lagoon arch.
Layout: Smart UV Project (60 deg) per group over all its meshes at once (multi-object edit, so texel density is
uniform across the group), then every island whose faces all look away from the lagoon (face-centre azimuth more
than 80 deg from face 00's 82 deg) is shrunk to BACK_SCALE, then one pack with rotation.  The registered photos
span ~57 deg of azimuth around face 00, so the back half carries no photo data and only needs a valid layout.

Checks that fail the run (and block --save): texel overlap (rasterised pixel-centre coverage > 1 at 2048 per group,
tolerance 0.05 % of covered texels for float ties on shared edges), UV outside 0..1, layer order / active / render
flags, UVProj hash, vertex / face counts.  Prints texels per metre per group (target >= 200 on the lagoon side).
Writes assets/textures/projection2/uvbake_groups.json (group -> object names) for mat_p10_meshdump.py.
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
MARGIN = 0.0012          # 5 px at 4096: the bleed the projection dilates into
ANGLE = {1: 80.0}        # the entablature's egg / dentil / modillion courses: fewer, larger islands
FACE_AZ0 = 82.0
HERO_FACES = (0, 7, 1)
OUT = common.ASSETS / "textures" / "projection2"
OUT.mkdir(parents=True, exist_ok=True)

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
        o.select_set(True)
    bpy.context.view_layer.objects.active = rl[0]
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(ANGLE.get(g, 60.0)), island_margin=0.0, area_weight=0.0,
                             correct_aspect=True, scale_to_bounds=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    # shrink back-facing islands (shared meshes -- columns, bases -- are seen at every azimuth: kept at 1)
    for o in rl:
        me = o.data
        shared = "column" in me.name or "colbase" in me.name
        bm = bmesh.new(); bm.from_mesh(me)
        uvl = bm.loops.layers.uv[UV]
        bm.faces.ensure_lookup_table()
        pc = np.array([f.calc_center_median() for f in bm.faces])
        pn = np.array([f.normal for f in bm.faces])
        w = np.ones(len(bm.faces)) if shared else face_weight(*to_world(o, pc, pn))
        # islands: union faces across edges whose two sides carry the same UVs
        parent = list(range(len(bm.faces)))

        def find(i):
            while parent[i] != i:
                parent[i] = parent[parent[i]]
                i = parent[i]
            return i
        for e in bm.edges:
            lf = e.link_loops
            if len(lf) != 2:
                continue
            l1, l2 = lf
            a1, b1 = l1[uvl].uv, l1.link_loop_next[uvl].uv
            a2, b2 = l2.link_loop_next[uvl].uv, l2[uvl].uv
            if (a1 - a2).length < 1e-6 and (b1 - b2).length < 1e-6:
                ra, rb = find(l1.face.index), find(l2.face.index)
                if ra != rb:
                    parent[ra] = rb
        isl = {}
        for f in bm.faces:
            isl.setdefault(find(f.index), []).append(f)
        n_back = 0
        for faces in isl.values():
            sc = max(w[f.index] for f in faces)
            if sc >= 1.0:
                continue
            n_back += 1
            pts = [l[uvl].uv.copy() for f in faces for l in f.loops]
            cx = sum(p.x for p in pts) / len(pts); cy = sum(p.y for p in pts) / len(pts)
            for f in faces:
                for l in f.loops:
                    u = l[uvl].uv
                    l[uvl].uv = (cx + (u.x - cx) * sc, cy + (u.y - cy) * sc)
        bm.to_mesh(me); bm.free()
        print(f"[uvbake]   {me.name:40s} islands {len(isl):5d} shrunk {n_back:5d} faces weight-1 {int((w >= 1).sum())}/{len(w)}")
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.select_all(action="SELECT")
    bpy.ops.uv.pack_islands(rotate=True, scale=True, margin_method="FRACTION", margin=MARGIN, shape_method="CONCAVE")
    bpy.ops.object.mode_set(mode="OBJECT")
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
        shared = "column" in me.name or "colbase" in me.name
        fn = np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0])
        fn /= np.maximum(np.linalg.norm(fn, axis=1, keepdims=True), 1e-12)
        w = np.ones(n) if shared else face_weight(pc, fn)
        front = (w >= 1.0) & (a3 > 1e-6)
        if front.any():
            dens.append((float(a3[front].sum()), float(a2[front].sum())))
        if (uvt < -1e-6).any() or (uvt > 1 + 1e-6).any():
            fails += 1
            print(f"[uvbake] UV OUTSIDE 0..1 on {me.name}")
        TU.append(uvt)
    TU = np.concatenate(TU)
    cnt = raster_count(TU, RES_CHK)
    cov = (cnt > 0).sum(); ovl = (cnt > 1).sum()
    a3f = sum(d[0] for d in dens); a2f = sum(d[1] for d in dens)
    tpm = math.sqrt(a2f * ATLAS * ATLAS / a3f) if a3f > 0 else 0.0
    bad = ovl > 0.0005 * cov
    fails += bad
    report[g] = dict(objects=names_out[g], meshes=[o.data.name for o in rl], triangles=int(len(TU)),
                     coverage=float(cov / RES_CHK ** 2), overlap_texels=int(ovl), overlap_frac=float(ovl / max(cov, 1)),
                     texels_per_m_front=tpm, front_area_m2=a3f)
    print(f"[uvbake] group {g}: tris {len(TU)} atlas fill {100 * cov / RES_CHK ** 2:.1f} % overlap texels {ovl} "
          f"({100 * ovl / max(cov, 1):.3f} %) {'FAIL' if bad else 'OK'}; lagoon-side {a3f:.0f} m2 at "
          f"{tpm:.0f} texels/m @ {ATLAS}")

json.dump({str(g): v["objects"] for g, v in report.items()}, open(OUT / "uvbake_groups.json", "w"), indent=1)
json.dump(report, open(OUT / "work" / "uvbake_report.json", "w"), indent=1)
if SAVE and not fails:
    common.save_blend(common.ASSETS / "architecture.blend")
    print("[uvbake] saved assets/architecture.blend")
elif SAVE:
    print(f"[uvbake] NOT SAVED: {fails} check(s) failed")
print(f"[uvbake] done, {fails} failure(s)")
