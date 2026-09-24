"""Trees for the Palace of Fine Arts environment: Sapling species presets -> meshes with 3 LODs -> placed instances.

Species (from docs/reference_sheet.md section 6): Monterey cypress, blue-gum eucalyptus, Monterey pine, weeping
willow, coast redwood, generic broadleaf. Each species has 2-3 seeds; every (species, seed, LOD) is ONE mesh shared by
all its instances. Instances are objects `ENV_tree_<species>_<nn>_LOD<k>` in ENV_tree_instances; the source objects
live in ENV_trees (hidden).

Standalone test (renders a line-up of every species against the sky):
    blender --background --python scripts/env_trees.py -- --lineup
"""
import bpy, bmesh, sys, os, math, random, time, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
import env_lib as L
import arch_params as AP
from mathutils import Vector

# ----------------------------------------------------------------------------- Sapling presets
# Keys are bpy.ops.curve.tree_add properties. 'scale' is roughly the trunk length in metres (final height is measured
# and the instance rescaled to the planting-plan height, so only proportions matter here).
BASE = dict(do_update=True, bevel=True, prune=False, showLeaves=True, useArm=False, makeMesh=False, handleType="0",
            rMode="rotate", autoTaper=True, closeTip=True, leafShape="hex", horzLeaves=True, leafDist="6")

SPECIES = {
    # dense, dark, wind-layered crown on a short heavy trunk; branches sweep up then flatten
    "cypress": dict(
        levels=3, length=(1.0, 0.52, 0.36, 0.0), lengthV=(0.0, 0.15, 0.2, 0.0), branches=(0, 30, 20, 0),
        curveRes=(8, 5, 3, 1), curve=(0.0, -15.0, -10.0, 0.0), curveV=(30.0, 70.0, 80.0, 0.0),
        shape="8", customShape=(0.8, 1.0, 0.5, 0.45), branchDist=1.2, nrings=5, baseSize=0.22, baseSize_s=0.3,
        ratio=0.022, ratioPower=1.25, scale0=1.1, scaleV0=0.1, rootFlare=1.3,
        downAngle=(90.0, 52.0, 42.0, 45.0), downAngleV=(0.0, -35.0, 15.0, 10.0), rotate=(137.5, 137.5, 137.5, 137.5),
        rotateV=(20.0, 30.0, 40.0, 0.0), attractUp=(0.0, 0.8, 0.6, 0.0), segSplits=(0.0, 0.25, 0.1, 0.0),
        splitAngle=(0.0, 25.0, 20.0, 0.0), splitAngleV=(0.0, 8.0, 8.0, 0.0), splitByLen=True, splitHeight=0.3,
        scale=20.0, scaleV=2.0, leaves=230, leafScale=0.62, leafScaleX=0.38, leafScaleV=0.35, bend=0.3, leafangle=5.0,
        leafShape="rect", horzLeaves=False, leafDownAngle=55.0, leafDownAngleV=25.0, leafRotate=137.5, leafRotateV=40.0,
        bark="MAT_bark_cypress", leaf="MAT_leaf_cypress", height=(15, 25)),
    # columnar Monterey cypress (younger / grouped trees): the narrow dark columns left of the rotunda in the user image
    "cypress_column": dict(
        levels=3, length=(1.0, 0.2, 0.42, 0.0), lengthV=(0.0, 0.15, 0.2, 0.0), branches=(0, 44, 16, 0),
        curveRes=(8, 5, 3, 1), curve=(0.0, -10.0, -10.0, 0.0), curveV=(20.0, 50.0, 70.0, 0.0),
        shape="8", customShape=(0.5, 0.7, 0.5, 0.5), branchDist=1.1, nrings=7, baseSize=0.12, baseSize_s=0.3,
        ratio=0.018, ratioPower=1.25, scale0=1.0, scaleV0=0.1, rootFlare=1.2,
        downAngle=(90.0, 45.0, 42.0, 45.0), downAngleV=(0.0, -25.0, 15.0, 10.0), rotate=(137.5, 137.5, 137.5, 137.5),
        rotateV=(20.0, 30.0, 40.0, 0.0), attractUp=(0.0, 1.0, 0.7, 0.0), segSplits=(0.0, 0.15, 0.1, 0.0),
        splitAngle=(0.0, 20.0, 20.0, 0.0), splitAngleV=(0.0, 8.0, 8.0, 0.0), splitByLen=True, splitHeight=0.3,
        scale=24.0, scaleV=2.0, leaves=230, leafScale=0.60, leafScaleX=0.38, leafScaleV=0.35, bend=0.3, leafangle=5.0,
        leafShape="rect", horzLeaves=False, leafDownAngle=55.0, leafDownAngleV=25.0, leafRotate=137.5, leafRotateV=40.0,
        bark="MAT_bark_cypress", leaf="MAT_leaf_cypress", height=(18, 28)),
    # tall straight trunk, high open crown, hanging foliage
    "eucalyptus": dict(
        levels=3, length=(1.0, 0.24, 0.5, 0.0), lengthV=(0.0, 0.2, 0.25, 0.0), branches=(0, 20, 14, 0),
        curveRes=(10, 5, 4, 1), curve=(0.0, 10.0, -25.0, 0.0), curveV=(25.0, 50.0, 80.0, 0.0),
        shape="8", customShape=(0.4, 1.0, 0.55, 0.6), branchDist=1.4, baseSize=0.4, baseSize_s=0.35,
        ratio=0.013, ratioPower=1.3, scale0=1.0, scaleV0=0.1, rootFlare=1.15,
        downAngle=(90.0, 32.0, 50.0, 45.0), downAngleV=(0.0, -20.0, 20.0, 10.0), rotate=(137.5, 137.5, 137.5, 137.5),
        rotateV=(20.0, 20.0, 40.0, 0.0), attractUp=(0.4, 0.8, -1.3, 0.0), segSplits=(0.15, 0.3, 0.0, 0.0),
        splitAngle=(20.0, 25.0, 0.0, 0.0), splitAngleV=(5.0, 8.0, 0.0, 0.0), splitByLen=True, splitHeight=0.35, baseSplits=1,
        scale=30.0, scaleV=3.0, leaves=400, leafScale=0.52, leafScaleX=0.42, leafScaleV=0.35, bend=0.2, leafangle=-70.0,
        leafShape="rect", horzLeaves=False, leafDownAngle=70.0, leafDownAngleV=20.0, leafRotate=137.5, leafRotateV=40.0,
        bark="MAT_bark_eucalyptus", leaf="MAT_leaf_eucalyptus", height=(22, 34)),
    # Monterey pine: irregular rounded crown of dense dark needle tufts
    "pine": dict(
        levels=3, length=(1.0, 0.36, 0.36, 0.0), lengthV=(0.0, 0.2, 0.2, 0.0), branches=(0, 30, 18, 0),
        curveRes=(8, 5, 3, 1), curve=(0.0, -10.0, 0.0, 0.0), curveV=(35.0, 60.0, 60.0, 0.0),
        shape="8", customShape=(0.5, 1.0, 0.55, 0.6), branchDist=1.1, baseSize=0.3, baseSize_s=0.3,
        ratio=0.02, ratioPower=1.25, scale0=1.0, scaleV0=0.1, rootFlare=1.2,
        downAngle=(90.0, 55.0, 45.0, 45.0), downAngleV=(0.0, -30.0, 10.0, 10.0), rotate=(137.5, 137.5, 137.5, 137.5),
        rotateV=(25.0, 30.0, 40.0, 0.0), attractUp=(0.0, 0.5, 0.35, 0.0), segSplits=(0.1, 0.25, 0.1, 0.0),
        splitAngle=(25.0, 25.0, 20.0, 0.0), splitAngleV=(5.0, 8.0, 8.0, 0.0), splitByLen=True, splitHeight=0.3, baseSplits=1,
        scale=21.0, scaleV=2.0, leaves=240, leafScale=0.60, leafScaleX=0.35, leafScaleV=0.35, bend=0.3, leafangle=0.0,
        leafShape="rect", horzLeaves=False, leafDownAngle=60.0, leafDownAngleV=25.0, leafRotate=137.5, leafRotateV=40.0,
        bark="MAT_bark_cypress", leaf=("MAT_leaf_pine", "MAT_leaf_cypress"), height=(15, 24)),
    # weeping willow at the water's edge
    "willow": dict(
        levels=3, length=(0.75, 0.5, 1.4, 0.0), lengthV=(0.0, 0.1, 0.1, 0.0), branches=(0, 40, 14, 0),
        curveRes=(6, 8, 6, 1), curve=(0.0, 20.0, -40.0, 0.0), curveV=(120.0, 100.0, 0.0, 0.0), curveBack=(0.0, 20.0, 0.0, 0.0),
        shape="4", shapeS="4", branchDist=1.5, baseSize=0.2, baseSize_s=0.25, baseSplits=2,
        ratio=0.025, ratioPower=1.75, scale0=1.0, scaleV0=0.0, rootFlare=1.1,
        downAngle=(0.0, 20.0, 30.0, 20.0), downAngleV=(0.0, 20.0, 10.0, 10.0), rotate=(99.5, 137.5, -60.0, 140.0),
        rotateV=(15.0, 15.0, 45.0, 0.0), attractUp=(0.0, 0.0, -2.75, -3.0), segSplits=(0.1, 0.2, 0.2, 0.0),
        splitAngle=(12.0, 30.0, 16.0, 0.0), splitAngleV=(0.0, 10.0, 20.0, 0.0), splitByLen=True, handleType="1",
        scale=11.0, scaleV=1.5, leaves=300, leafScale=0.52, leafScaleX=0.22, leafScaleV=0.35, bend=0.0, leafangle=-70.0,
        leafShape="rect", leafDownAngle=30.0, leafDownAngleV=10.0, leafRotate=137.5, leafRotateV=30.0, horzLeaves=False, leafDist="10",
        bark="MAT_bark_cypress", leaf="MAT_leaf_broadleaf", height=(8, 12)),
    # coast redwood: narrow conical, flat horizontal sprays
    "redwood": dict(
        levels=3, length=(1.0, 0.24, 0.45, 0.0), lengthV=(0.0, 0.15, 0.2, 0.0), branches=(0, 55, 9, 0),
        curveRes=(10, 4, 3, 1), curve=(0.0, 5.0, -5.0, 0.0), curveV=(15.0, 30.0, 40.0, 0.0),
        shape="0", branchDist=1.0, baseSize=0.15, baseSize_s=0.3,
        ratio=0.0115, ratioPower=1.2, scale0=1.1, scaleV0=0.05, rootFlare=1.4,
        downAngle=(90.0, 82.0, 50.0, 45.0), downAngleV=(0.0, 10.0, 15.0, 10.0), rotate=(137.5, 137.5, 137.5, 137.5),
        rotateV=(15.0, 20.0, 30.0, 0.0), attractUp=(0.0, 0.25, 0.1, 0.0), segSplits=(0.0, 0.0, 0.0, 0.0),
        splitAngle=(0.0, 0.0, 0.0, 0.0), splitAngleV=(0.0, 0.0, 0.0, 0.0), splitByLen=True,
        scale=30.0, scaleV=3.0, leaves=480, leafScale=0.46, leafScaleX=0.40, leafScaleV=0.35, bend=0.25, leafangle=0.0,
        leafShape="rect", horzLeaves=False, leafDownAngle=50.0, leafDownAngleV=20.0, leafRotate=137.5, leafRotateV=30.0,
        bark="MAT_bark_cypress", leaf=("MAT_leaf_pine", "MAT_leaf_cypress"), height=(18, 32)),
    # generic round-crowned broadleaf (acacia / plane / young oak)
    "broadleaf": dict(
        levels=3, length=(1.0, 0.5, 0.5, 0.0), lengthV=(0.0, 0.15, 0.2, 0.0), branches=(0, 22, 12, 0),
        curveRes=(6, 5, 3, 1), curve=(0.0, -20.0, -20.0, 0.0), curveV=(30.0, 60.0, 70.0, 0.0),
        shape="1", branchDist=1.0, baseSize=0.3, baseSize_s=0.3, baseSplits=2,
        ratio=0.02, ratioPower=1.2, scale0=1.0, scaleV0=0.1, rootFlare=1.2,
        downAngle=(90.0, 55.0, 45.0, 45.0), downAngleV=(0.0, -30.0, 10.0, 10.0), rotate=(137.5, 137.5, 137.5, 137.5),
        rotateV=(20.0, 20.0, 30.0, 0.0), attractUp=(0.5, 0.3, 0.2, 0.0), segSplits=(0.2, 0.3, 0.1, 0.0),
        splitAngle=(25.0, 25.0, 20.0, 0.0), splitAngleV=(5.0, 8.0, 8.0, 0.0), splitByLen=True, splitHeight=0.25,
        scale=12.0, scaleV=1.5, leaves=380, leafScale=0.44, leafScaleX=0.85, leafScaleV=0.35, bend=0.3, leafangle=0.0,
        leafShape="rect", leafDownAngle=45.0, leafDownAngleV=20.0, leafRotate=137.5, leafRotateV=40.0,
        bark="MAT_bark_cypress", leaf="MAT_leaf_broadleaf", height=(8, 14)),
}
SEEDS = {"cypress": (3, 17, 41), "cypress_column": (2, 31), "eucalyptus": (5, 23, 61), "pine": (7, 29), "willow": (11, 37),
         "redwood": (13, 43), "broadleaf": (19, 53)}

# LOD overrides: geometry resolution and leaf density (skeleton stays identical for the same seed)
LOD_OVERRIDES = {
    0: dict(bevelRes=1, resU=2),
    1: dict(bevelRes=0, resU=1, leaf_factor=0.42, leaf_scale=1.25),
    2: dict(bevelRes=0, resU=1, levels=2, leaf_factor=0.0, leaf_scale=1.0),
}
NON_OP_KEYS = ("bark", "leaf", "height")


# ----------------------------------------------------------------------------- generation
def _sapling_params(species, seed, lod):
    p = dict(BASE)
    p.update({k: v for k, v in SPECIES[species].items() if k not in NON_OP_KEYS})
    ov = LOD_OVERRIDES[lod]
    p["seed"] = seed
    p["bevelRes"] = ov["bevelRes"]
    p["resU"] = ov["resU"]
    if "levels" in ov:
        p["levels"] = ov["levels"]
        p["showLeaves"] = False
    lf = ov.get("leaf_factor", 1.0)
    if lf > 0:
        p["leaves"] = max(2, int(round(p["leaves"] * lf)))
        p["leafScale"] = p["leafScale"] * ov.get("leaf_scale", 1.0)
    return p


def _curve_to_mesh(obj):
    try:
        obj.data.use_uv_as_generated = True      # gone in 5.x; bark UVs are generated below instead
    except AttributeError:
        pass
    dg = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(dg)
    me = bpy.data.meshes.new_from_object(ev, preserve_all_data_layers=True, depsgraph=dg)
    if not me.uv_layers:
        # cylindrical fallback UVs (u = angle about the trunk axis, v = height / 4 m); bark shaders should prefer
        # object-space triplanar mapping anyway
        uv = me.uv_layers.new(name="UVMap")
        for loop in me.loops:
            v = me.vertices[loop.vertex_index].co
            uv.data[loop.index].uv = ((math.atan2(v.y, v.x) / (2 * math.pi)) % 1.0, v.z / 4.0)
    return me


def _lod2_cards(species, height, radius, base_z, rnd):
    """Billboard-style crown for LOD2: 4 vertical crossed cards + 1 horizontal disc-ish card set."""
    verts, faces = [], []
    n_cards = 4
    for i in range(n_cards):
        a = i * math.pi / n_cards + rnd.uniform(-0.15, 0.15)
        dx, dy = math.cos(a) * radius, math.sin(a) * radius
        z0, z1 = base_z, height
        base = len(verts)
        verts += [(-dx, -dy, z0), (dx, dy, z0), (dx, dy, z1), (-dx, -dy, z1)]
        faces.append((base, base + 1, base + 2, base + 3))
    # two horizontal layers for the flat-topped species
    for k, zf in enumerate((0.62, 0.85)):
        z = base_z + (height - base_z) * zf
        r = radius * (0.95 if k == 0 else 0.7)
        base = len(verts)
        verts += [(-r, -r, z), (r, -r, z), (r, r, z), (-r, r, z)]
        faces.append((base, base + 1, base + 2, base + 3))
    return verts, faces


def generate_tree_mesh(species, seed, lod, name):
    """Run Sapling headless and return a single mesh (slot 0 bark, slot 1 leaves) with UVs."""
    sp = SPECIES[species]
    params = _sapling_params(species, seed, lod)
    # Sapling reads bpy.context.object: make sure nothing is active/selected
    for ob in list(bpy.data.objects):
        try:
            ob.select_set(False)
        except Exception:
            pass
    bpy.context.view_layer.objects.active = None
    before = set(bpy.data.objects.keys())
    bpy.ops.curve.tree_add(**params)
    new = [bpy.data.objects[n] for n in bpy.data.objects.keys() if n not in before]
    tree = next((o for o in new if o.type == "CURVE"), None)
    leaves = next((o for o in new if o.type == "MESH"), None)
    assert tree is not None, "Sapling produced no curve"
    trunk_me = _curve_to_mesh(tree)
    # measure
    zs = [v.co.z for v in trunk_me.vertices]
    height = max(zs) if zs else 1.0
    xy = [math.hypot(v.co.x, v.co.y) for v in trunk_me.vertices]
    radius = max(xy) if xy else 1.0
    # assemble
    bm = bmesh.new()
    uv_layer = bm.loops.layers.uv.new("UVMap")
    verts = [bm.verts.new(v.co) for v in trunk_me.vertices]
    bm.verts.ensure_lookup_table()
    trunk_uv = trunk_me.uv_layers.active.data if trunk_me.uv_layers.active else None
    for poly in trunk_me.polygons:
        try:
            f = bm.faces.new([verts[i] for i in poly.vertices])
        except ValueError:
            continue
        f.material_index = 0
        f.smooth = True
        if trunk_uv is not None:
            for loop, li in zip(f.loops, poly.loop_indices):
                loop[uv_layer].uv = trunk_uv[li].uv
    leaf_count = 0
    if leaves is not None and lod < 2:
        lme = leaves.data
        luv = lme.uv_layers.active.data if lme.uv_layers.active else None
        lverts = [bm.verts.new(v.co) for v in lme.vertices]
        for poly in lme.polygons:
            try:
                f = bm.faces.new([lverts[i] for i in poly.vertices])
            except ValueError:
                continue
            f.material_index = 1
            f.smooth = True
            if luv is not None:
                for loop, li in zip(f.loops, poly.loop_indices):
                    loop[uv_layer].uv = luv[li].uv
        leaf_count = len(lme.polygons)
        for v in lme.vertices:
            height = max(height, v.co.z)
            radius = max(radius, math.hypot(v.co.x, v.co.y))
    if lod == 2:
        rnd = random.Random(seed)
        base_z = height * (sp.get("baseSize", 0.3) * 0.8)
        cv, cf = _lod2_cards(species, height * 1.02, radius * 0.9, base_z, rnd)
        cverts = [bm.verts.new(v) for v in cv]
        for face in cf:
            f = bm.faces.new([cverts[i] for i in face])
            f.material_index = 1
            for k, loop in enumerate(f.loops):
                loop[uv_layer].uv = ((0, 0), (1, 0), (1, 1), (0, 1))[k]
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(L.mat(sp["bark"]))
    lm = sp["leaf"]
    me.materials.append(L.mat_or(*lm) if isinstance(lm, tuple) else L.mat(lm))
    me["gen_height"] = height
    me["gen_radius"] = radius
    # clean up Sapling's objects
    for o in new:
        data = o.data
        bpy.data.objects.remove(o, do_unlink=True)
        if data is not None and data.users == 0:
            try:
                (bpy.data.curves if data.rna_type.name == "Curve" else bpy.data.meshes).remove(data)
            except Exception:
                pass
    bpy.data.meshes.remove(trunk_me)
    return me, height, radius, leaf_count


def generate_library(quick=False, species=None):
    """All (species, seed, lod) meshes. Returns {(species, seed): {lod: mesh}}."""
    lib = {}
    t0 = time.time()
    for sp, seeds in SEEDS.items():
        if species and sp not in species:
            continue
        if quick:
            seeds = seeds[:1]
        for seed in seeds:
            lib[(sp, seed)] = {}
            for lod in (0, 1, 2):
                me, h, r, nleaf = generate_tree_mesh(sp, seed, lod, f"ENV_tree_{sp}_s{seed}_LOD{lod}")
                tris = sum(len(p.vertices) - 2 for p in me.polygons)
                lib[(sp, seed)][lod] = me
                print(f"[env_trees] {sp:10s} seed {seed:3d} LOD{lod}: h {h:5.1f} m  r {r:4.1f} m  leaves {nleaf:6d}  tris {tris:7,d}  ({time.time() - t0:.0f}s)")
    return lib


# ----------------------------------------------------------------------------- planting plan
# (species, x, y, height_m, note). World: X south(+)/north(-), Y east(+). Heights from the reference sheet's table,
# positions from satellite_z20/z18 crowns and the hero-view geometry (docs/environment_notes.md explains each group).
# ROUND 9: these coordinates are now the SHIPPED coordinates.  Until r8 `shadow_relief` relocated hand-placed trees
# behind the plan's back - 12 m down-sun for a stubborn shadow blocker, and radially outward for QA-02-13's 37 m
# podium ring - so six entries here described a position no build ever used and every frame-x comment on them was
# stale (env r8 review, finding 3).  That pass may no longer move a pinned tree (see `policy`), so the six podium-ring
# corrections are baked in at the coordinate the push itself produced, computed with the PLAN height so the clearance
# holds however far the relief later lowers the crown (`env_r9_replan.py --podium`, renders/logs/env_r9_podium.log).
# The scene geometry is unchanged by that bake - the push was deterministic and idempotent - only the plan is honest.
# ROUND 9 REVIEW (finding 1): and the onto-land snap was still moving nine of them at placement time, after every
# gate.  It runs first now and refuses to move a pinned tree (`land_snap`), so the nine coordinates below were
# corrected by hand to the nearest point that passes ALL THREE hard gates - dry land, the 4.1 m gallery keep-out
# and the 37 m podium ring at the PLAN height - found with `env_r9_replan.py --land` and tagged `r9r LAND`.
# `env_r9_replan.py --verify` re-runs the two solvers that produced the rest (`env_r8_fit.solve` and the podium
# push) and fails if PLAN has drifted more than 0.2 m from them.
PLAN = [
    # A. peninsula north lobe (land X -40..-16, Y 0..26): the dense dark cluster right of the rotunda (user image, 169)
    #   ROUND 8, re-derived from ref 169 through the cam-01 projection.  Measured on the photo (env_r8_fit --ref):
    #   the dark mass runs frame x 0.61-0.735 (dark<60 0.35-0.58) and COLLAPSES to 0.14 at x 0.74; its solid top is
    #   frame y 0.45 with sparse tips to 0.35.  The tall conifers used to stand on the peninsula's north-west shore
    #   at 85-95 m, where they resolved to x 0.67-0.79 - 35 % of QA-04-6's box on their own, the whole left half of
    #   the north-wing band.  They could not be swung left there: QA-02-13's podium clearance (shadow_relief,
    #   PODIUM_R + CLEAR + crown radius = 44-46 m) throws anything nearer than that radially out into the lagoon
    #   and the land snap drops it straight back on the same shore line at X ~ -38, so X in the plan does nothing.
    #   The photo's mass is not on that shore: at 0.61-0.735 with a solid top at y 0.45 it is 120-135 m out - the
    #   grove on the far side of the north embayment, past the north arch - which is 34 m of open water and lawn
    #   nearer the rotunda than QA-02-13's ring.  The five conifers below are solved for their ref frame x at that
    #   distance (crown half-width 0.033-0.036 of frame, so the union spans 0.640-0.758), with heights raised to
    #   21-26 m so the mass keeps most of the photo's apparent height (top frame y 0.41-0.43 against ref 169's
    #   0.385).  24-30 m closes that last 0.025 of frame and costs the band nothing (the extra crown is above the
    #   box's top edge, foliage 38.5 -> 37.0 %), but it re-orders `shadow_relief`'s greedy loop - south wing in
    #   shadow 17.5 -> 11.2 %, and cam 03's ground std with it, 26.7 -> 21.4 against round 7's 27.4.  Not worth
    #   0.025 of frame: reverted (commit 98561e1, reverted here).  The three near trees stay on the
    #   peninsula: they are the pale willow and the shore broadleaf ref 169 puts at the water in front of the mass.
    #   ROUND 9.  The r8 coordinates above were solved for frame x on the arc ITSELF: `env_r9_replan` measures the
    #   four of them at 0.26 / 1.36 / 1.51 / 2.34 m from the colonnade gallery centreline, i.e. standing inside the
    #   north wing, and the walk probe found the same trees blocking LIGHT r14's flythrough.  They never rendered
    #   there: `shadow_relief` pushed them 12 m down-sun (to r_off +11..+13) before anything was built, which is
    #   why the r8 comments quoted a position the build did not ship and why the r8 review found the cypress at
    #   frame x 0.719 instead of the commented 0.668-0.740.  With that sweep now forbidden (see `policy` in
    #   shadow_relief) the coordinate has to be right in the plan, so the five are re-solved by the SAME round-8
    #   tool at the radial offset the r8 build actually shipped: `env_r8_fit.solve(centre_x, r_off = +13.0)`,
    #   which is the A2 construction with A2's +8 replaced by the shipped +13.  Frame-x centres are unchanged
    #   (0.672 / 0.684 / 0.704 / 0.713 / 0.723); the crowns read 0.003-0.004 of frame narrower because the axis
    #   distance goes 123-128 -> 134-138 m, and the spans in the notes below are the re-measured ones.
    ("pine", -37.2, -43.1, 21.0, "A cluster core, ships x 0.642-0.702 (ref 169 mass) (QA-01-6: clear of cam02's right 40%)"),
    ("redwood", -40.5, 9.3, 16.0, "A young redwood at the north arch (ref 070); r9r LAND+ring (-40.5,-2.2 was 4.9 m into the embayment), ships x 0.728-0.773"),
    ("cypress", -44.5, -41.4, 26.0, "A dark mass right of the dome, ships x 0.668-0.740 (ref 169)"),
    ("pine", -46.5, -40.8, 22.0, "A cluster, second crown, ships x 0.680-0.746 (ref 169)"),
    ("willow", -40.0, 16.0, 9.0, "A pale weeping willow at the water in front of the cluster (ref 169); r8 10 -> 9 m, its crown reached frame x 0.79 where ref 169 is clear colonnade"),
    ("broadleaf", -41.0, 13.0, 9.0, "A shore broadleaf at cam02's right edge; r8 11 -> 9 m, same reason as the willow; r9r LAND (-49,13 was 6.7 m into the water), ships x 0.736-0.787"),
    ("cypress", -48.6, -40.2, 24.0, "A cluster depth, ships x 0.689-0.757 (ref 169) (mass kept dense)"),
    ("pine", -40.0, -42.5, 21.0, "A cluster depth, ships x 0.653-0.715 (ref 169)"),
    # P. peninsula planting band in front of the podium (hero foreground; sheet s6 "low mounded shrubs ... small
    #    trees in the podium planter zone"). Kept off the central bay: all six project to cam01 x 0.21-0.30 or
    #    0.62-0.80 with their crowns below y 0.52, so the rotunda's body and arch stay clear (spans re-measured on
#    the r9r plan by `env_r9_replan`; the three hero-shore willows moved 1-3 m onto land, see below).
    ("broadleaf", -30.0, 30.0, 8.0, "P peninsula bed, right of the rotunda (cam01 x 0.71-0.78)"),
    ("willow", -22.0, 37.0, 7.0, "P low willow at the water in front of the podium; r9r LAND 38 -> 37, ships x 0.622-0.679"),
    ("broadleaf", -36.0, 20.0, 7.0, "P peninsula bed (cam01 x 0.75-0.80)"),
    ("broadleaf", 26.0, 32.0, 7.0, "P peninsula bed, left of the rotunda (cam01 x 0.21-0.26)"),
    ("willow", 18.0, 40.0, 7.0, "P low willow at the water, left (cam01 x 0.24-0.30)"),
    ("broadleaf", 34.7, 19.8, 6.0, "P peninsula bed, ships x 0.245-0.277; r9 QA-02-13 ring, r9r +0.5 m out so the ring is cleared, not touched"),
    # QA-04-4: ref 169's hero shoreline is not a quay, it is a willow curtain.  Mapped through the round-02 align
    # transform, its two big weeping crowns sit at cam 01 x 0.33-0.47 and x 0.56-0.73 - world X -4..14 / -24..-8 at
    # Y 43-48 - and they hang from ~7 m down to the water, hiding the podium base between the pier groups.  Nine
    # metres, not seven: in the photo they reach the top of the QA crop.  Group P, so they are pinned.
    # Phase 10 round 2 (scripts/env_p10r2_*.py): measured on the tree's OWN pixels (Cycles holdout alpha) against ref
    # 169's hand-segmented willow, the round-1 tree at (6.9, 43.4) h9 stood left of the photo's willow and 56 px too
    # tall in the willow box (crown-top row 548 vs ref 604; box share 17.3 vs 21.7 %).  Ref's willow is a low, broad
    # weeping crown: x 690-850 px, crown top row 601-604, curtain to the water at row 703 - 5.1 m above the tree's
    # ground at d 58.6 m.  So this ONE instance is planted at 5.4 m (outside the species window 8-12 m, which stays
    # as is for every other willow) and widened x1.7 in X/Y (P10R2_WIDEN: x1.4 rendered 126 px wide vs ref 159) to keep the photo's width; moved 2.5 m
    # north to put the trunk at frame x 0.401 (ref's centre 0.401).  Gates: env_p10r2_plan.py --check.
    ("willow", 4.4, 43.4, 5.4, "P hero-shore willow, ref 169 x 0.36-0.44; p10r2 (6.9,43.4) h9 -> here h5.4 w1.7 (ref crown-top row 604)"),
    ("willow", -2.6, 45.9, 8.5, "P hero-shore willow, ref 169 x 0.44-0.52 (right of the stair); r9r LAND (-1.5,47.0) -> here, ships x 0.423-0.500"),
    ("willow", -12.0, 44.0, 9.0, "P hero-shore willow, ref 169 x 0.56-0.64; r9r LAND 45 -> 44, ships x 0.517-0.598"),
    # A2. strip between the north wing and the embayment (3-13 m wide per OSM, canopy overhangs both).
    #   ROUND 8, re-derived from ref 169 through the cam-01 projection (scripts/env_r8_fit.py --solve).  The three
    #   trees below used to stand at arc radius 94-108, i.e. INSIDE the wing's arc (arch_params.COL_ARC_CENTER /
    #   COL_ARC_R = 117.4) - the courtyard side, not the OSM strip - so from the hero they stood in FRONT of the
    #   colonnade and hid its shafts: they were 23.1 % of QA-04-6's box (16.5 of it the "first box" cypress at
    #   frame x 0.90-0.99).  Ref 169 has no trunk in front of a shaft anywhere in x 0.76-0.99; what it has is
    #   crowns clearing the entablature at frame x 0.79-0.83 and 0.86-0.92.  Each is now solved for its ref frame x
    #   at r = COL_ARC_R + 8 m, which is the middle of the 3-13 m strip and behind the wing from cam 01.
    ("cypress_column", -37.9, -20.5, 27.0, "A2 tall column right of the rotunda (user image x~1020); r9 QA-02-13 ring, r9r LAND+ring, ships x 0.668-0.719"),
    ("pine", -60.5, -30.6, 13.0, "A2 strip along the north wing, r+8 (ref 169: crown over the cornice, x 0.79)"),
    ("cypress_column", -65.7, -28.2, 17.0, "A2 second column, r+8 (ref 169: crown over the cornice, x 0.82)"),
    ("cypress", -76.6, -22.3, 16.0, "A2 at the wing's first box, r+8 (ref 169: crown over the cornice, x 0.89)"),
    # B. north wing strip further out and the north shore
    ("eucalyptus", -84.7, 15.5, 28.0, "B big eucalyptus on the strip (ref 141); r9 QA-02-7, 12 m down-sun of the r8 plan coordinate (-79, 26) - the position shadow_relief used to sweep it to on every build"),
    ("pine", -90.0, 22.5, 20.0, "B"),
    ("willow", -100.0, 37.0, 9.0, "B willow at the water (refs 144/145)"),
    ("eucalyptus", -113.1, 15.1, 30.0, "B big eucalyptus behind the willows (ref 171); r9 pushed radially out of the north pylon's gallery keep-out (was -106, 20 = 2.6 m off the walk centreline)"),
    ("cypress", -118.0, 8.0, 22.0, "B beyond the north pylon"),
    ("cypress_column", -112.0, 40.0, 24.0, "B tall column beyond the north pylon (ref 169 right)"),
    # C. south side: columns on the strip between the south wing and the south embayment
    ("cypress_column", 34.8, 20.2, 16.0, "C cypress column left of the rotunda (user image x~290, cam01 x 0.259): QA-03-10/-13 26 -> 16 m, the user image spire tops out at the colonnade cornice; r9 QA-02-13 ring"),
    ("cypress_column", 29.7, 26.2, 13.0, "C second column (user image x~330, cam01 x 0.268), south lobe; QA-03-13 24 -> 13 m; r9 QA-02-13 ring"),
    ("broadleaf", 31.1, 26.4, 9.0, "C small dark tree left of the rotunda (user image x~410, cam01 x 0.258); QA-03-13 13 -> 9 m, clear of the rotunda silhouette at cam05; r9 QA-02-13 ring, 14.5 m out"),
    ("eucalyptus", 62.0, -30.0, 30.0, "C broad eucalyptus behind the south wing (ref 169 left)"),
    ("pine", 62.0, -46.0, 18.0, "C QA-01-6: moved out of cam03 (was 24,-22 = 7 m in front of the camera)"),
    ("broadleaf", 74.0, -38.0, 10.0, "C QA-01-6: moved out of cam03 (was 33,-20 = 5 m in front of the camera)"),
    # D. south shore near the south wing and pylon
    ("cypress_column", 66.0, 40.0, 22.0, "D dense cypress behind the south pylon (ref 169 far left)"),
    ("eucalyptus", 70.3, 35.5, 28.0, "D south-wing strip; r9 QA-02-7, 12 m down-sun of the r8 plan coordinate (76, 46) - the position shadow_relief used to sweep it to on every build"),
    ("pine", 92.2, 57.5, 18.0, "D; r9r LAND"),
    ("willow", 78.0, 50.0, 9.0, "D willow at the south end of the lagoon"),
    ("eucalyptus", 107.5, 51.0, 30.0, "D south pylon; r9 pushed radially out of the gallery keep-out (was 104, 52 = 2.4 m off the walk centreline)"),
    ("cypress", 112.0, 40.0, 22.0, "D"),
    # F. east and south-east shore (Baker Street side, behind the hero camera): blue-gum row + NE-corner cypresses
    ("eucalyptus", -110.0, 124.0, 30.0, "F east shore row"),
    ("eucalyptus", -90.0, 126.0, 28.0, "F east shore row"),
    ("eucalyptus", -70.0, 122.0, 32.0, "F east shore row"),
    ("eucalyptus", -48.0, 127.0, 30.0, "F east shore row"),
    ("eucalyptus", 12.0, 128.0, 30.0, "F east shore row"),
    ("broadleaf", 24.0, 130.0, 12.0, "F east lawn"),
    ("eucalyptus", 34.0, 126.0, 28.0, "F east shore row"),
    ("eucalyptus", 54.0, 124.0, 30.0, "F east shore row"),
    ("eucalyptus", 73.0, 120.0, 30.0, "F"),
    ("eucalyptus", 95.0, 118.0, 32.0, "F"),
    ("eucalyptus", 126.0, 127.0, 28.0, "F"),
    ("cypress", 168.0, 114.0, 22.0, "F"),
    ("eucalyptus", 158.0, 28.0, 32.0, "F"),
    ("pine", 130.0, -20.0, 20.0, "F"),
    ("eucalyptus", 130.0, -68.0, 28.0, "F"),
    ("cypress", 110.0, 14.0, 20.0, "F"),
    ("eucalyptus", 125.0, 74.0, 30.0, "F"),
    ("cypress", 155.0, 94.0, 24.0, "F"),
    ("cypress", -130.0, 110.0, 24.0, "F NE-corner Monterey cypress (DPR, Harbor View Inn era)"),
    ("cypress", -118.0, 96.0, 22.0, "F NE corner"),
    ("cypress", -140.0, 82.0, 22.0, "F NE corner"),
    ("eucalyptus", -158.0, 131.0, 30.0, "F"),
    # G. wooded islet (lagoon1: X -123..-72, Y 53..82)
    ("willow", -80.0, 72.0, 9.0, "G islet willow (herons, DPR)"),
    ("broadleaf", -92.0, 68.0, 12.0, "G"),
    ("eucalyptus", -108.0, 65.0, 24.0, "G"),
    ("willow", -100.0, 72.0, 8.0, "G"),
    ("broadleaf", -115.0, 62.0, 10.0, "G"),
    # H. backdrop trees (Presidio side, Marina, Palace Drive) from z18 crowns - LOD1 capped beyond FAR_RADIUS
    ("eucalyptus", -80.0, -111.0, 30.0, "H"),
    ("cypress", -95.0, -100.0, 22.0, "H"),
    ("eucalyptus", -70.0, -125.0, 28.0, "H"),
    ("pine", -105.0, -118.0, 20.0, "H"),
    ("eucalyptus", -268.0, -120.0, 30.0, "H"),
    ("cypress", -245.0, -304.0, 24.0, "H"),
    ("eucalyptus", -280.0, -26.0, 30.0, "H"),
    ("cypress", -197.0, 54.0, 22.0, "H"),
    ("eucalyptus", -216.0, 27.0, 28.0, "H"),
    ("cypress", -255.0, 120.0, 24.0, "H"),
    ("eucalyptus", -259.0, -79.0, 30.0, "H"),
    ("pine", -253.0, -174.0, 22.0, "H"),
    ("eucalyptus", 24.0, -295.0, 30.0, "H"),
    ("cypress", 170.0, -102.0, 24.0, "H"),
    ("eucalyptus", 168.0, 112.0, 30.0, "H"),
    ("eucalyptus", -88.0, -308.0, 30.0, "H"),
    ("cypress", -30.0, -290.0, 24.0, "H"),
]

# ----------------------------------------------------------------------------- Phase 10 item 1: the NE mass
# (species, x, y, height_m, note, crown-width factor).  Ref 169's conifer mass right of the rotunda has its crown-top
# row at y 0.369 (398 px, median over frame x 0.655-0.740; scripts/env_p10_boxes.py).  The A cluster that was solved
# for it stands 141-145 m down the view axis, where y 0.369 needs a crown top at z ~ 36 m - past every species window
# (cypress 15-25, cypress_column 18-28 m) - and shadow_relief holds it at 21-26 m, so it tops out at y 0.41-0.45 and
# the box read 97-99 % sky.  Leaf cards cannot fix a height.  Every ray through x 0.66-0.74 passes the rotunda at
# 27-35 m, so the only dry land that projects there outside QA-02-13's podium ring is the peninsula shore at
# d 64-73 m, where y 0.34-0.37 needs a crown of only 19-20 m (`scripts/env_p10_plan.py --search`).  Two columnar
# Monterey cypresses (an existing prototype; the broad `cypress` fails the ring or the 3.5 m trunk spacing at every
# passing coordinate) are solved there, left crown edge on the rotunda's right edge (0.66), right edge short of
# QA-04-6's north-wing band (0.76).  The width factor scales the instance in X/Y only; `env_p10_plan` checks the ring
# with max(CROWN_R, measured radius x factor) x height.
# They are APPENDED after the hall belt (like the 8d belt) so no existing tree's seed, RNG draw, relief or position
# changes; they are hand-placed composition ("A"), so none of the relief passes could have moved them anyway, and
# `build_all` re-checks the three hard gates for them and prints the shadow cost.
P10_ADD = [
    ("cypress_column", -26.5, 32.6, 20.0, "A p10 NE mass, front column on the rotunda's right edge (ref 169 x 0.66-0.71); 19 -> 20 m after the first after-render (crown top 422 px vs ref 398)", 1.4),
    ("cypress_column", -33.2, 24.6, 19.0, "A p10 NE mass, second column behind the peninsula bed (ref 169 x 0.69-0.76); 20 -> 19 m: at 20 m it shades 1 more north-wing band sample, 21.2 -> 22.5 % against SHADOW_TARGET 22 %", 1.8),
]
# Phase 10 item 2: extra X/Y crown scale per species (ref 169's willow left of the rotunda is ~13 m across at 8 m tall,
# R/H ~ 0.8; the Sapling willow measures R/H 0.45-0.52).
CROWN_XY = {"willow": 1.30}
# Phase 10 round 2: per-instance extra X/Y crown scale for hand-placed PLAN entries, keyed by the full note (applied
# like a P10_ADD width factor, after the RNG draws).  The ring gates read it (env_r9_replan --verify, env_p10r2_plan).
# Phase 10 round 2: moving the hero-shore willow onto ref 169's willow (above) bared the podium and stair at cam-01
# x 0.33-0.37, rows 540-690, where ref 169 has a second, taller pale crown with fine pendulous foliage (x 0.33-0.40,
# crown-top row 535) - the slot the round-1 9 m willow had been filling (x 0.336-0.417, top row 538).  One more
# instance of the existing willow prototype (no new prototype), appended like P10_ADD so no existing tree's seed,
# RNG draw or position changes, at the nearest dry coordinate 3.5 m from the moved willow (env_p10r2_plan --add).
P10R2_ADD = [
    ("willow", 7.9, 42.6, 9.0, "P p10r2 pale crown left of the hero-shore willow (ref 169 x 0.33-0.40, crown-top row 535)", 1.0),
]
P10R2_WIDEN = {"P hero-shore willow, ref 169 x 0.36-0.44; p10r2 (6.9,43.4) h9 -> here h5.4 w1.7 (ref crown-top row 604)": 1.7}
FAR_RADIUS = 130.0   # no QA camera within this distance -> LOD0/LOD1 objects use the LOD1/LOD2 mesh
try:
    import qa_cameras as _qc
    CAM_XY = [(c["loc"][0], c["loc"][1]) for c in _qc.CAMERAS]
except Exception:
    CAM_XY = [(-14.1, 100.0)]


def redwood_screen(colonnade_polys, hall_poly, hall_field=None):
    """Tree screen BEHIND both colonnade wings (DPR: redwoods planted 1968).

    The wings are arcs struck from (0, 52) (env_backdrop.ARC_CENTRE), so the screen is laid out in polar
    coordinates about that point: for every 2 deg of the wing's angular sweep the polygon's outermost radius is
    measured, and the rows are planted outside it.

    QA-02-7 (round 02): the round-01 screen (rows at +4.5 / +11 / +19 m, 26-36 m tall, continuous) filled every bay
    and read as a wall in front of the wings - sky through the bays fell to 1.7 / 9.5 % and both wings went 37-52 %
    dark. Ref 169 has trees behind AND between the columns with 15-20 % sky through the bays and crowns only a few
    metres above the entablature (19-21 m). So now:
      * the rows stand 6 / 12.5 / 20 m outside the wing instead of 4.5 / 11 / 19 (pushing them further than that
        walks them into the exhibition hall footprint, which deletes most of the two back rows);
      * crowns are 19-27 m, not 26-36, so the screen tops out ~5 m over the entablature instead of ~15;
      * the rows are CLUMPED - a run of trees, then a 9-20 m gap - so bays open onto sky instead of a green wall;
      * density is roughly a third of round 01's.
    `shadow_relief` afterwards removes whatever still stands between the low sun and a wing face.
    """
    C = Vector((0.0, 52.0))
    out = []
    rnd = random.Random(5)
    if hall_field is None:
        hall_field = L.PolyField(L.ensure_ccw(hall_poly), cell=10.0)
    fields = [L.PolyField(L.ensure_ccw(w), cell=6.0) for w in colonnade_polys]
    # QA-01-6: never plant a screen tree on top of a QA camera (cam 03 stands inside the south wing)
    try:
        import qa_cameras
        keepout = [(c["loc"][0], c["loc"][1]) for c in qa_cameras.CAMERAS if c["loc"][2] < 40.0]
    except Exception:
        keepout = []
    for wing in colonnade_polys[:2]:
        poly = L.ensure_ccw(wing)
        pts = L.resample_polyline(poly, 2.0, closed=True)
        bins = {}
        for (x, y) in pts:
            v = Vector((x, y)) - C
            k = int(round(math.degrees(math.atan2(v.y, v.x)) / 2.0))
            bins[k] = max(bins.get(k, 0.0), v.length)
        ks = sorted(bins)
        # keep the main run of the sweep (drop 2 deg stragglers) and smooth the outer radius
        outer = {k: max(bins.get(k + j, bins[k]) for j in (-1, 0, 1)) for k in ks}
        # Round 5 (QA-03-10): measured on the merged master's hero, the wing band (60 480 560 600) carried 36.1 %
        # of pixels below luminance 60 against ref 169's own 27.8 % over the same box - and 25.0 of those 36.1
        # points were foliage, 11.1 architecture (the wing's own shaded bays, which the photo has too).  The screen
        # was still about a third too dense THROUGH the bays: sky-ish pixels 13.6 % vs the photo's 16.5 %.  So the
        # two front rows keep their heights and their clumping but run shorter and gap wider.
        for row, (off, spacing, hmin, hmax, run, gap, tag) in enumerate((
                # E1 crowns 17-21 m rather than 18.5-23: ref 169 has the screen topping out only a few metres over
                # the entablature, and height is the one knob here that does NOT reshuffle the clumping RNG (same
                # number of draws), so it thins the band's first-hit foliage without moving a single crown.
                # Widening the gaps further was tried and rejected - it re-rolls the run/gap sequence and is not
                # monotone: gap 13-21 / 12-18 put a clump straight into the hero band (foliage 30.9 -> 37.3 %).
                (6.0, 5.0, 17.0, 21.0, (11.0, 20.0), (11.0, 19.0), "E1"),
                (12.5, 6.0, 20.0, 25.0, (14.0, 26.0), (10.0, 16.0), "E2"),
                # E3 keeps round 4's density: measured, thinning the back row changes the band by nothing at all
                # (its crowns are behind E1/E2, so they are never the first hit) and only costs trees.
                (20.0, 7.0, 21.0, 27.0, (22.0, 38.0), (7.0, 13.0), "E3"))):
            carry = rnd.uniform(0, spacing)
            # clumping state: metres of run left before the next gap, and metres of gap left
            run_left = rnd.uniform(*run)
            gap_left = 0.0
            for k in ks:
                r = outer[k] + off + rnd.uniform(-1.5, 1.5)
                arc = math.radians(2.0) * r          # metres covered by this 2 deg bin
                t = carry
                while t < arc:
                    if gap_left > 0.0:
                        step = min(gap_left, arc - t)
                        gap_left -= step
                        t += step
                        if gap_left <= 0.0:
                            run_left = rnd.uniform(*run)
                            carry = t
                        continue
                    ang = math.radians(2.0 * k) + (t / max(1e-6, r))
                    p = C + Vector((math.cos(ang), math.sin(ang))) * r
                    # Round 9: `fields` are the OSM roof polygons, whose outer edge falls INSIDE the modelled
                    # arc over the middle of both wings - row E1 (+6 m) landed screen trees on the gallery floor
                    # (the walk probe found ENV_tree_redwood_16 1.13 m from the centreline).  The keep-out is the
                    # arc itself, read from arch_params by env_lib.gallery_clear.
                    inside = (any(f.signed(p.x, p.y) < 1.5 for f in fields)
                              or not L.gallery_clear(p.x, p.y))
                    near_cam = any(math.hypot(p.x - cx, p.y - cy) < 16.0 for (cx, cy) in keepout)
                    if not inside and not near_cam and hall_field.signed(p.x, p.y) > 1.0:
                        u = rnd.random()
                        sp = "redwood" if u < 0.50 else ("cypress" if u < 0.80 else ("eucalyptus" if row else "pine"))
                        h = rnd.uniform(hmin, hmax) if sp != "pine" else rnd.uniform(18, 22)
                        out.append((sp, p.x, p.y, h, f"{tag} screen behind the colonnade"))
                    t += spacing
                    run_left -= spacing
                    if run_left <= 0.0:
                        gap_left = rnd.uniform(*gap)
                carry = max(0.0, t - arc)
    return out


# ----------------------------------------------------------- Phase 8d belt r2: the hall's east-face tree belt
# ref 169 at 100 % (the registered N and S bands, `qa_r22_probe.REF_XF`): behind BOTH colonnades the photograph has
# no lit wall - a dark, soft tree mass fills every intercolumniation from the shrub line up to roughly the
# architrave, and the exhibition hall shows only as a roof line above it.  8d R2 answered that with 89 lobed
# icospheres in MAT_backdrop_forest; QA 22 rejected them at 100 % as faceted untextured shards (docs/qa_round_22.md
# section 2), and the lead's decision (docs/decisions.md 2026-09-19) is to rebuild the belt out of the REAL tree
# prototypes through the far-tree path: every belt tree is an ordinary ENV_tree_* placement whose LOD0 object
# carries the LOD1 mesh and whose LOD1 object carries the LOD2 mesh (the `far` + `light` flags in `build_all`,
# exactly what the E2/E3 back screen rows do), so the export sees it as a far tree, gives it a 2-triangle
# billboard and an impostor from the 16 already-baked prototypes - no atlas re-bake.
#
# Placement geometry is inherited MEASURED from `env_backdrop.build_hall_belt` (which stays in the file behind
# `BELT_ICOSPHERE = False` as that measurement's record): an even arc-length walk along the hall's east-facing
# edges, the offset alternating so the silhouette has depth, and the hall footprint / rotunda platform /
# colonnade roof / gallery walk keep-outs.  What changes: the step is a tree's spacing, not a crown's (25-45
# trees instead of 89 blobs), and every tree stands on the ground on its own trunk.
#
# HEIGHT.  Heights are drawn 12-19 m and then capped by the TOP in world z at HALL_BELT_TOP_Z = 16.0 m, which is
# 4.0 m below the hall's 20.0 m roof crest (env_backdrop HALL_EAVE 15.5 + HALL_RISE 4.5) and 0.7 m below its
# 16.7 m parapet top, so the roof line always shows above the belt as it does in ref 169 - and the cap is in
# WORLD z, so undulating terrain cannot push a crown over the roof.  The belt stands 6-12 m in FRONT of the hall
# face, i.e. ~140-144 m from the hero against the face's ~150 m, so a 16.0 m top subtends the same angle as a
# 16.9 m point on the wall: the belt reads as just touching the parapet line, which is what the photograph shows.
# The cap binds on most draws, so the realised heights run 12.0-16.x m (reported per build).
HALL_BELT_TOP_Z = 16.0
# 4.5 m of face per tree, measured up from 6.5: at 6.5 the crowns stand clear of each other at the hero and the
# hall wall reads through the LOD1 foliage between them (the leaf density at LOD1 is 0.42 of LOD0's, so a crown is
# see-through even where the ray probe counts it as a hit).  At 4.5 m the two offset rows overlap and the belt
# reads as one mass with light through the gaps, which is what ref 169 shows.
HALL_BELT_STEP = 4.5
# Species read off ref 169's two bands at 100 %: dark Monterey cypress dominant, blue-gum eucalyptus and Monterey
# pine mixed through it, a few narrow columnar cypress, redwood for the darkest verticals.  Willow and broadleaf
# are the SHORE trees and are deliberately absent here.  Every species/seed in `SEEDS` has a baked impostor
# (the 16 of `export/out/gate3/gate3_set.json`), so the prototype_map resolves whatever this plants.
HALL_BELT_MIX = (("cypress",) * 5 + ("eucalyptus",) * 3 + ("pine",) * 2
                 + ("cypress_column",) * 2 + ("redwood",) * 2)


def hall_belt(hall_poly, hall_field, terrain_height, colonnade_polys=()):
    """The belt of real far trees along the exhibition hall's concave east face (Phase 8d belt r2).

    Returns plan entries `(species, x, y, height_m, note)` tagged `HB`, which `build_all` appends AFTER every
    relief pass and the gallery gate: the belt is measured against the hall, not composed against the frame, and
    appending it last leaves every existing tree's position, RNG draw, name and LOD byte-identical.
    """
    if hall_field is None:
        hall_field = L.PolyField(L.ensure_ccw(hall_poly), cell=10.0)
    poly = L.ensure_ccw(hall_poly)
    n = len(poly)
    rnd = random.Random(8104)

    def blocked(x, y):
        if hall_field.signed(x, y) < 3.0:
            return True                                  # inside the hall, or hard against its wall
        if math.hypot(x, y) < 34.0:
            return True                                  # the rotunda's own platform
        if not L.gallery_clear(x, y):
            return True                                  # never on the colonnade walk
        for cp in colonnade_polys:
            for (dx, dy) in ((0.0, 0.0), (3.0, 0.0), (-3.0, 0.0), (0.0, 3.0), (0.0, -3.0)):
                if L.point_in_poly(x + dx, y + dy, cp):
                    return True
        return False

    out = []
    last = None                   # last tree actually planted: the spacing is measured on the offset curve
    idx = skipped = 0
    # the species mix is DEALT from a shuffled deck, not drawn independently: 29 independent draws left one
    # eucalyptus out of the whole belt (measured, first build), which is not the mix ref 169 reads.
    deck = list(HALL_BELT_MIX)
    rnd.shuffle(deck)
    deck_i = 0
    for i in range(n):
        a, b = Vector(poly[i]), Vector(poly[(i + 1) % n])
        d = b - a
        seg = d.length
        if seg < 1.0:
            continue
        d = d / seg
        nrm = Vector((d.y, -d.x))                        # outward on the concave east face (as build_hall uses it)
        mid = (a + b) / 2
        to_origin = (Vector((0.0, 0.0)) - mid).normalized()
        if nrm.dot(to_origin) <= 0.20 or mid.length > 175.0:
            continue
        # The walk is FINE (1 m) and the spacing test is on the OFFSET curve, not on the hall polygon: stepping
        # 5.5 m along the polygon and then pushing each sample 6.5-11 m outward stretches the gaps wherever the
        # face turns away from the belt, and that is where the first build left them - measured with
        # `scripts/env_belt_probe.py`, the hall's south-east arm showed through 20.4 % of the rays that get past
        # the colonnade in the hero's frame-left band, at 10-16 m gaps between trees.  Measuring from the last
        # tree actually PLANTED also keeps the density across a rejected sample.
        u = 0.0
        while u < seg:
            base = a + d * u
            u += 1.0
            off = (6.5 if idx % 2 else 11.0) + rnd.uniform(-1.3, 1.3)
            p = base + nrm * off + d * rnd.uniform(-1.8, 1.8)
            # spacing along the FACE (project onto the local tangent), not the straight-line distance: the
            # offsets alternate 6.5 / 11 m, so a 3-D test counts the 4.5 m zig-zag as progress and plants three
            # times as many trees as asked (88 for a 5.5 m step, measured).
            if last is not None and (p - last).dot(d) < HALL_BELT_STEP:
                continue
            idx += 1
            if blocked(p.x, p.y):
                skipped += 1
                continue
            if deck_i >= len(deck):
                rnd.shuffle(deck)
                deck_i = 0
            sp = deck[deck_i]
            deck_i += 1
            z0 = terrain_height(p.x, p.y) - 0.15         # `build_all` grounds a tree at terrain - 0.15
            h = min(rnd.uniform(12.0, 19.0), HALL_BELT_TOP_Z - z0)
            if h < 8.0:                                  # ground this high would make it a bush, not a belt
                skipped += 1
                continue
            out.append((sp, p.x, p.y, h, "HB hall east-face belt (8d r2)"))
            last = p
    hs = [e[3] for e in out]
    print(f"[env_trees] hall east-face belt: {len(out)} far trees, {skipped} sample points rejected, "
          f"heights {min(hs):.1f}-{max(hs):.1f} m (top capped at {HALL_BELT_TOP_Z} m world z), "
          f"step {HALL_BELT_STEP} m")
    return out


# ------------------------------------------------- QA-04-6: the screen may not tower over the entablature
# Ref 169 shows the screen behind both wings topping out only a few metres over the colonnade cornice.  Round 6
# measured the hero's frame-RIGHT band at 74.6 % foliage against the frame-left band's 30.5 %, and the single
# biggest contributor (15.9 % of the box on its own) was a screen eucalyptus at (-79.4, -23.3): it stands 113 m
# from the hero camera while the wing it is meant to sit behind is 129 m away, so a 25 m crown reads 77 % taller
# than the 16.4 m entablature.  `frame_band_relief` cannot touch it - `behind="colonnade"` exempts it on purpose,
# because that IS where the screen belongs - so the discipline has to be a height cap, and the honest one is the
# same sight line the shore shrubs use: the crown may stand SCREEN_OVER of the frame height over the cornice.
# Only trees that really are behind a wing from the hero (the exact `_crosses` test) are capped.
# Read from arch_params, never copied: the r7 review's finding 2 (env_build) applies here too - the numbers match
# today and drift silently tomorrow.
COLONNADE_TOP_Z = AP.COLONNADE_ABACUS + AP.COLONNADE_ENTABLATURE_H   # cornice, on the -0.45 lawn
COLONNADE_ARC = (AP.COL_ARC_CENTER, AP.COL_ARC_R)
# Round 8: 0.022 -> 0.004.  With the A/A2 trees off the front of the wing (see PLAN), the whole of what was left in
# QA-04-6's box at frame x 0.87-0.97 was screen crown standing over the cornice - 18 % of the box, against ref
# 169's 0.01-0.19 dark fraction over those same columns.  This build's cornice sits ~0.02 of frame lower than the
# photo's, so the 2.2 % allowance lands inside the measured band instead of above it: 0.4 % left the box at
# 40.2 % foliage and 0.0 % - screen tops exactly on the cornice line - at 38.5 %.  The crowns ref 169 does show
# over the cornice (frame x 0.79-0.83, 0.86-0.92) are the A2 trees, which are hand-placed and never capped.
# Thinning the PROCEDURAL screen is the sanctioned way to clear a band (round-5 rule).
SCREEN_OVER = 0.000           # fraction of cam 01's frame height a screen crown may stand over the cornice
SCREEN_H_FLOOR = 11.0         # never cut a screen tree below this: it has to stay a screen


def screen_height_cap(entries, colonnade_polys, cam=None, lens=None, ground=-0.45, verbose=True):
    """Lower any screen tree that stands over the colonnade cornice by more than SCREEN_OVER of the frame.

    The hero station and lens come from `scripts/qa_cameras.py` unless the caller passes them: a copy here would
    keep capping against yesterday's camera after the next re-station without saying so.
    """
    if cam is None or lens is None:
        spec = L.qa_camera("_qa_01_", (-14.1, 100.0, 1.6), 20.0)
        if spec is not None:
            cam = cam if cam is not None else spec[0]
            lens = lens if lens is not None else spec[1]
        cam = cam if cam is not None else (-14.1, 100.0, 1.6)
        lens = lens if lens is not None else 20.0
    half_h = (0.5 * 36.0 / lens) * 9.0 / 16.0
    (cx, cy), R = COLONNADE_ARC
    out, cut, metres = [], 0, 0.0
    for e in entries:
        sp, x, y, h, tag = e
        if not _crosses(cam, x, y, colonnade_polys):
            out.append(e)
            continue
        dx, dy = x - cam[0], y - cam[1]
        d = math.hypot(dx, dy)
        ox, oy = cam[0] - cx, cam[1] - cy
        b = (ox * dx + oy * dy) / d
        disc = b * b - (ox * ox + oy * oy - R * R)
        if disc <= 0.0:
            out.append(e)
            continue
        d_col = -b + math.sqrt(disc)                       # the wing arc along this bearing
        tan_top = (COLONNADE_TOP_Z - cam[2]) / d_col + SCREEN_OVER * 2.0 * half_h
        h_max = max(SCREEN_H_FLOOR, cam[2] + tan_top * d - ground)
        if h > h_max + 0.05:
            metres += h - h_max
            cut += 1
            h = h_max
        out.append((sp, x, y, h, tag))
    if verbose:
        print(f"[env_trees] screen height cap: lowered {cut} of {len(entries)} screen crowns "
              f"({metres:.0f} m total, cornice + {SCREEN_OVER * 100:.1f} % of frame at cam 01)")
    return out


# ----------------------------------------------------------------------------- QA-02-7 sun relief
# The wing faces that carry the hero composition must be sunlit. At el 7.4 deg the sun's rays are nearly flat, so a
# crown 40 m up-sun of the entablature only has to be ~5 m taller than it to put it in shade. The round-02 master had
# 92.5 % (south) / 70.0 % (north) of the entablature band in tree shadow. This pass measures the shadow with
# env_lib.shadowed_fraction and, worst caster first, lowers the offending crown (a screen tree may lose up to 45 % of
# its height, a hand-placed PLAN tree only 25 %, since those carry named reference features), then drops screen trees
# that still block. Nothing inside the peninsula "A" cluster is ever dropped: it is the dark mass right of the
# rotunda in ref 169.
SHADOW_TARGET = 0.22          # <= this fraction of the readable wing band (z >= 12 m) may be in tree shadow
WATER_TARGET = 0.25           # ... and of the lagoon the hero camera actually sees (QA-02-6)
SHORE_TARGET = 0.25           # ... and of the hero's shore-shrub crop (QA-05-10)
SHADOW_BANDS = (12.0, 17.0)

# QA-05-10 (round 7).  The shore belt QA-04-4 built came back at lum 71.7 against ref 169's 114 over the crop
# 700 600 1200 740, "black-green where the photo's are sunlit soft green".  Materials had already raised the leaf
# tints x1.4, so round 7 measured the geometry side: at sun elevation 7.4 deg a 12 m crown standing 90 m up-sun
# throws its shadow straight across that belt, and `shadow_relief` protected the wing faces and the hero's water
# but never the shore.  These samples put the crop itself in the relief loop.
SHORE_BOX = (700 / 1920.0, 1200 / 1920.0, 600 / 1080.0, 740 / 1080.0)      # QA-05-10's crop, in frame coords
SHORE_OFFSETS = (2.0, 7.0, 13.0)      # metres inland from the water line - the belt QA-04-4 planted
SHORE_HEIGHTS = (1.0, 2.2)            # crown heights of that belt (band_sightline_cap allows 3.2-3.7 m)
# `shadow_relief` re-measures every sample against every tree up to 140 times, so the sample count is kept in the
# low hundreds: 3 offsets x 2 heights on a 5 m ring, clipped to QA's own crop.  MEASURED (env_r7b_build.log:119):
# **50 shore points** of 276 band samples - the crop is narrow, so the ring contributes far fewer than the
# ~150-250 first estimated.  50 points is a thin basis for SHORE_TARGET; round 7's null result (see the notes)
# means the belt is a level, not a shadow, so the density is left alone rather than raised for its own sake.


def shore_sun_samples(lagoon_field, terrain_height=None, step=5.0):
    """Points on the hero's shore-shrub belt that land inside QA-05-10's crop, as (3, x, y, z) samples."""
    cam = L.qa_camera("_qa_01_", (-14.1, 100.0, 1.6), 20.0)
    if cam is None or lagoon_field is None:
        return []
    (loc, lens) = cam
    try:
        import qa_cameras
        spec = next(c for c in qa_cameras.CAMERAS if "_qa_01_" in c["name"])
        target, shift_y = spec["target"], spec.get("shift_y", 0.0)
    except Exception:
        target, shift_y = (0.0, 0.0, 1.6), 0.06
    f, r, u = _cam_basis(dict(loc=loc, target=target))
    hw = 0.5 * 36.0 / lens
    hh = hw * 9.0 / 16.0
    x0, x1, y0, y1 = SHORE_BOX
    out = []
    for off in SHORE_OFFSETS:
        try:
            ring = L.resample_polyline(L.offset_polygon(lagoon_field.poly, off), step, closed=True) \
                if hasattr(lagoon_field, "poly") else []
        except Exception:
            ring = []
        for (x, y) in ring:
            if not (28.0 < math.hypot(x, y) < 62.0):        # the peninsula shore in front of the podium
                continue
            zg = terrain_height(x, y) if terrain_height else -0.45
            for h in SHORE_HEIGHTS:
                d = Vector((x, y, zg + h)) - Vector(loc)
                z = d.dot(f)
                if z <= 1.0:
                    continue
                fx = 0.5 + 0.5 * (d.dot(r) / z) / hw
                fy = 0.5 - 0.5 * (d.dot(u) / z) / hh + shift_y * (hw / hh)
                if x0 <= fx <= x1 and y0 <= fy <= y1:
                    out.append((3, x, y, zg + h))
    return out


def hero_water_samples(lagoon_field, step=6.0):
    """Points on the lagoon surface inside the hero camera's cone, as (2, x, y, z) samples.

    QA-02-6 measured the near field 7-10 m in front of CAM_qa_01 and the "mid-left band" at ~9 m; both sat 3.9x
    under ref 169 and went cyan. At sun elevation 7.4 deg the east-shore eucalyptus row (Y 118-131, 28-32 m) throws
    a 230 m shadow to the north-west - straight across that water. Nothing lit it, so it could only return sky.
    """
    try:
        import qa_cameras
        cam = next(c for c in qa_cameras.CAMERAS if "_qa_01_" in c["name"])
        cx, cy = cam["loc"][0], cam["loc"][1]
        tx, ty = cam["target"][0], cam["target"][1]
    except Exception:
        cx, cy, tx, ty = -14.1, 100.0, 0.0, 0.0
    fx, fy = tx - cx, ty - cy
    fl = math.hypot(fx, fy) or 1.0
    fx, fy = fx / fl, fy / fl
    out = []
    x = -110.0
    while x <= 70.0:
        y = 20.0
        while y <= 99.0:
            d = ((x - cx) * fx + (y - cy) * fy)
            if 4.0 < d < 85.0 and lagoon_field.signed(x, y) < -1.0:
                lat = abs(-(x - cx) * fy + (y - cy) * fx)
                if lat < 0.60 * d:                       # inside the 20 mm lens' horizontal cone
                    out.append((2, x, y, L.WATER_Z + 0.02))
            y += step
        x += step
    return out


def relief_policy(note, x, y):
    """`(height floor as a fraction of the original, may it be dropped?, may it be MOVED?)`

    Round 9 (env r8 review, finding 3).  This pass used to push any stubborn blocker 12 m down-sun, pinned or
    not, and it ran BEFORE `frame_band_relief`, whose pin tuple is therefore applied to positions this pass
    had already changed: the A cypress went from PLAN (-42, -30) to (-47.7, -40.5) and the A2 column from
    (-36, -18) to (-38.7, -20.8).  That is the 36-48 m sweep the round-5 rule forbids, in a smaller dose, and
    it is why every frame-x comment in PLAN described a position the build did not ship.  A hand-placed tree
    (any group in `PIN_HAND_PLACED`) may now only be LOWERED here; when it is at its floor the loop gives up
    on it and moves to the next worst blocker.
    """
    n = str(note)
    movable = n.split(" ")[0] not in PIN_HAND_PLACED
    if n.startswith(("E1", "E2", "E3")):
        return 0.55, True, movable              # generated screen: expendable
    if n.startswith(("F", "H")) and y > 105.0:
        return 0.45, True, movable              # east shore / backdrop, behind the hero camera
    if n.startswith("A"):
        return 0.80, False, movable             # the dark cluster right of the rotunda in ref 169: keep it
    if n.startswith("P"):
        return 0.90, False, movable             # QA-04-4's peninsula bed / ref-169 willows: composition, pinned
    return 0.72, False, movable


def shadow_relief(plan, colonnade_polys, lagoon_field=None, verbose=True, terrain_height=None):
    samples = L.wing_samples(colonnade_polys, heights=(6.0,) + SHADOW_BANDS)
    band = [s for s in samples if s[3] >= min(SHADOW_BANDS)]
    water = hero_water_samples(lagoon_field) if lagoon_field is not None else []
    shore = shore_sun_samples(lagoon_field, terrain_height) if lagoon_field is not None else []
    band = band + water + shore
    trees = [list(t) for t in plan]
    targets = {0: SHADOW_TARGET, 1: SHADOW_TARGET, 2: WATER_TARGET, 3: SHORE_TARGET}

    def measure():
        per, blockers = L.shadowed_fraction(band, trees)
        frac = {}
        for (wi, z), (tot, sh) in per.items():
            t, x = frac.get(wi, (0, 0))
            frac[wi] = (t + tot, x + sh)
        return {wi: v[1] / max(1, v[0]) for wi, v in frac.items()}, blockers

    before, blockers = measure()
    start = dict(before)
    iters = 0
    # r9 review, finding 2: there used to be a `moved_pinned` counter here, incremented inside the branch whose
    # own condition is `movable`, so the log's "hand-placed 0" was a tautology that proved nothing.  What proves
    # the claim is `moved` (every move below is a generated tree, and the branch asserts it) together with the two
    # refusal counters: `pin_floor` = hand-placed blockers the pass gave up on at their height floor, and
    # `pin_refused` = hand-placed crowns left inside the podium ring.  Both are printed with the trees named.
    changed = {"lowered": 0, "dropped": 0, "moved": 0, "pin_floor": 0, "pin_refused": 0, "metres": 0.0}
    pushes = {}
    orig_h = {i: t[3] for i, t in enumerate(trees)}
    suggested = set()
    for _ in range(400):
        iters += 1
        over = [wi for wi, f in before.items() if f > targets.get(wi, SHADOW_TARGET)]
        if not over or not blockers:
            break
        i = max(blockers, key=lambda k: blockers[k])
        sp, x, y, h, note = trees[i]
        frac, droppable, movable = relief_policy(note, x, y)
        floor = max(frac * orig_h[i], 8.0)
        if h > floor + 0.5:
            new_h = max(floor, h * 0.82)
            changed["metres"] += h - new_h
            changed["lowered"] += 1
            trees[i][3] = new_h
        elif droppable:
            trees[i][3] = 0.0
            changed["dropped"] += 1
        elif movable and pushes.get(i, 0) < 3:
            assert movable, "shadow_relief may never move a hand-placed tree"
            sx, sy, _ = L.sun_vector()               # push 12 m down-sun so the shadow clears the target
            trees[i][1] -= 12.0 * sx
            trees[i][2] -= 12.0 * sy
            pushes[i] = pushes.get(i, 0) + 1
            changed["moved"] += 1
        else:
            if not movable and i not in suggested:
                # Round 9: a hand-placed tree is never swept, but the pass still knows where it WOULD have gone.
                # Printing that coordinate is what lets the correction be baked into PLAN (the podium-ring
                # pattern), so the plan holds the shipped position and this pass has nothing left to do.
                sx, sy, _ = L.sun_vector()
                cands = "  ".join(f"{k * 12:.0f} m -> ({x - k * 12.0 * sx:6.1f},{y - k * 12.0 * sy:6.1f})"
                                  for k in (1, 2, 3))
                print(f"[env_trees] shadow relief: hand-placed {sp} ({x:.1f},{y:.1f}) h{h:.1f} still blocks "
                      f"{blockers.get(i, 0)} band samples at its height floor - NOT moved.  Down-sun: {cands}")
                suggested.add(i)
                changed["pin_floor"] += 1
            blockers.pop(i, None)                    # give up on this one, move to the next worst
            if not blockers:
                break
            continue
        before, blockers = measure()

    # QA-02-13: no tree crown within 6 m of the rotunda podium (podium radius ~31 m = env_build.APRON_R).
    # Round 9: a hand-placed tree is not swung out here either - it is REPORTED, and the PLAN coordinate is the
    # thing that gets corrected (see the A2 entry).  A silent radial push is how the A2 column came to stand 3.9 m
    # from where PLAN says it does.
    PODIUM_R, CLEAR = 31.0, 6.0
    for t in trees:
        if t[3] <= 0.1:
            continue
        d = math.hypot(t[1], t[2])
        rad = L.CROWN_R.get(t[0], 0.35) * t[3]
        if d - rad < PODIUM_R + CLEAR and d > 1e-3:
            if str(t[4]).split(" ")[0] in PIN_HAND_PLACED:
                print(f"[env_trees] QA-02-13: hand-placed {t[0]} ({t[1]:.1f},{t[2]:.1f}) h{t[3]:.0f} crown "
                      f"{rad:.1f} m reaches r {d - rad:.1f} m, {PODIUM_R + CLEAR - (d - rad):.1f} m inside the "
                      f"{PODIUM_R + CLEAR:.0f} m podium ring - NOT moved, fix the PLAN coordinate")
                changed["pin_refused"] += 1
                continue
            k = (PODIUM_R + CLEAR + rad) / d
            t[1] *= k
            t[2] *= k
            changed["moved"] += 1
    out = [tuple(t) for t in trees if t[3] > 0.1]
    after, rest = measure()
    if verbose:
        # Round 9: the pass can no longer sweep a hand-placed tree out of the way, so it has to be able to say
        # WHICH trees it gave up on - otherwise a target it cannot reach looks like a silent regression.
        top = sorted(rest.items(), key=lambda kv: -kv[1])[:8]
        print(f"[env_trees] shadow relief: {iters} iterations; worst remaining casters:")
        for i, n in top:
            t = trees[i]
            print(f"    {n:4d} samples  {t[0]:14s} ({t[1]:6.1f},{t[2]:6.1f}) h{t[3]:5.1f} "
                  f"(plan h{orig_h[i]:.0f})  [{str(t[4])[:44]}]")
        print(f"[env_trees] shadow relief: lowered {changed['lowered']} crowns ({changed['metres']:.0f} m total), "
              f"moved {changed['moved']} (all generated; {changed['pin_floor']} hand-placed left at their "
              f"height floor, {changed['pin_refused']} refused at the podium ring), "
              f"dropped {changed['dropped']}; in shadow -> north wing "
              f"{100 * after.get(0, 0):.1f} % south wing {100 * after.get(1, 0):.1f} % hero water "
              f"{100 * after.get(2, 0):.1f} % hero shore {100 * after.get(3, 0):.1f} % "
              f"(was {100 * start.get(0, 0):.1f}/{100 * start.get(1, 0):.1f}/"
              f"{100 * start.get(2, 0):.1f}/{100 * start.get(3, 0):.1f}) over "
              f"{len(band)} samples ({len(shore)} shore); {len(plan)} -> {len(out)} trees")
    return out


# ----------------------------------------------------------------------------- QA-03-10 / QA-03-13 frame bands
# Two QA boxes ask for parts of the *architecture* to be readable through the planting, not for the planting to
# go away.  Both are stated in frame coordinates, so they are enforced in frame coordinates.
#
#   QA-03-10  hero (cam 01), box x 60-560 / y 480-600 of 1920x1080 = frame x 0.031-0.292, y 0.444-0.556: the south
#             colonnade (QA calls it "north").  Ref 169 has that band open - eight sunlit shafts and sky between
#             them - with foliage only at the frame's left edge and one conifer group at x 0.19-0.29.  So the
#             guarded span stops at 0.205: the composition conifers of the user image (x ~290/330) stay.
#   QA-03-13  cam 05, the rotunda's own silhouette: no crown inside it.  The rotunda spans frame x 0.235-0.78.
#
# Only trees BETWEEN the camera and the subject can offend, so a tree is a candidate when it is nearer than the
# subject.  For the hero that is the colonnade arc: the wings are struck from ARC_CENTRE (0, 52) at radius ~93, so
# a tree inside that radius stands in front of the wing and a tree outside it stands behind (the redwood screen).
# Offenders are pushed along the camera's right axis - which moves them across the frame without changing their
# distance much - to the nearer edge of the band, and only shortened if no clear spot exists.
# Every HAND-PLACED PLAN group (see PLAN above).  E1/E2/E3 are the procedural `redwood_screen` rows and are the
# only trees a band may sweep: the lead's rule after the round-5 review is that a band is cleared by thinning the
# procedural screen, never by moving a tree that stands where a reference photo puts it.  All three bands share
# this tuple - round 7 shipped it on the hero south band only, and the round-7 build log then showed the north
# band moving 7 A/A2 trees 18-48 m and dropping 3 (incl. "A dark mass right of the dome").
PIN_HAND_PLACED = ("A", "A2", "B", "C", "D", "F", "G", "H", "P")

FRAME_BANDS = [
    # Offence band x 0.031-0.205: ref 169 and the user image both put a conifer group at x 0.19-0.29, so that is
    # composition, not a defect (round 4's call, kept - widening the offence band to QA's 0.292 costs the peninsula
    # bed and the user-image cypress spires, and buys 2 lum).  But QA-03-10 *measures* 60-560 px = x 0.031-0.292,
    # so `x1_exit` makes a tree that has to move leave the measured box instead of being parked just inside it:
    # in round 4 cypress_column_04 was pushed 4 m from x 0.20 to x 0.21 and still darkened the band.
    # `pin` are PLAN group letters whose trees stand where the reference puts them and are never relocated by this
    # band: P is the peninsula bed and C the user-image group (the two cypress spires at user-image x~330/410).
    # Lead decision after the round-5 review: the band is cleared by thinning the PROCEDURAL screen
    # (`redwood_screen`), never by sweeping a hand-placed tree 36-48 m across the site.
    # QA-05-5 (round 7).  Round 4 stopped the offence band at 0.205 because widening it to QA's own 0.292 "costs
    # the peninsula bed and the user-image cypress spires".  Since round 5 those are PINNED (`pin=("P","C")`), so
    # widening now touches nothing but the procedural screen - which is precisely the treatment that took the
    # north band from 0.63 to 1.00 of ref 169.  x1 therefore goes to the measured box edge.
    # ... and because the widened span now reaches groups the round-4 band never touched, every HAND-PLACED group
    # is pinned here, not just P and C (see PIN_HAND_PLACED).
    dict(cam="_qa_01_", x0=0.031, x1=0.292, x1_exit=0.292, y0=0.40, y1=0.60, behind="colonnade",
         pin=PIN_HAND_PLACED, label="QA-05-5 hero south-wing band"),
    # cam 05's guard stops at y 0.66: the rotunda's body ends there, and the 7-9 m willows and broadleaves of the
    # peninsula bed (tops at y 0.67-0.69) are the user image's own foreground - they belong in the picture.
    dict(cam="_qa_05_", x0=0.235, x1=0.780, y0=0.02, y1=0.66, near=112.0, pin=PIN_HAND_PLACED,
         label="QA-03-13 cam05 rotunda silhouette"),
    # QA-04-6 (round 6).  Round 5 measured and cleared the frame-LEFT band (60-560 px = x 0.031-0.292); nobody had
    # ever measured the frame-RIGHT one, and it came back at 74.6 % foliage / 24.2 % architecture / 1.2 % sky
    # against the left band's 30.5 / 57.8 / 11.6 - which is why its luminance regressed to 0.63 of ref 169 while
    # the left band passed.  In the photo over that same box the colonnade is clear from about x 0.75 rightwards:
    # trees only at the far left of it and glimpsed through the bays.  So the offence band starts at 0.775, which
    # leaves the "A" mass right of the rotunda (it projects to x 0.71-0.76) exactly where the reference has it and
    # only touches what stands over the wing itself.  `behind="colonnade"` exempts the screen rows planted behind
    # the wing; what it does NOT exempt is a screen tree that `redwood_screen` put in FRONT of it, which is how
    # cypress_02 (-73.7, -1.0) came to be 17.8 % of this box on its own - the screen is laid out in polar
    # coordinates about (0, 52) but the wings are struck from (-11.2, 84.7), so "outside the wing in C-polar" is
    # not "behind the wing from the hero" everywhere along the sweep.
    dict(cam="_qa_01_", x0=0.760, x1=0.985, x0_exit=0.760, x1_exit=0.985, y0=0.40, y1=0.60,
         behind="colonnade", pin=PIN_HAND_PLACED, label="QA-04-6 hero north-wing band"),
]
CROWN_SAFETY = 1.30      # the Sapling crowns spread wider than CROWN_R x height


def _cam_specs():
    import qa_cameras
    return qa_cameras.CAMERAS


def _cam_basis(spec):
    f = (Vector(spec["target"]) - Vector(spec["loc"])).normalized()
    r = f.cross(Vector((0.0, 0.0, 1.0))).normalized()
    u = r.cross(f).normalized()
    return f, r, u


def _frame_box(spec, f, r, u, x, y, h, species):
    """Crown bounding box in frame coordinates, plus the distance along the view axis."""
    rad = L.CROWN_R.get(species, 0.35) * h * CROWN_SAFETY
    half_w = 0.5 * 36.0 / spec["lens"]
    half_h = half_w * 9.0 / 16.0
    # Blender's shift_y is in units of the LARGER sensor dimension (the width here, sensor_fit HORIZONTAL),
    # so as a fraction of frame HEIGHT it must be scaled by the aspect ratio W/H = half_w/half_h = 16/9.
    # Positive shift_y moves the rendered content DOWN the image, i.e. up the frame-y axis used here.
    shift = spec.get("shift_y", 0.0) * (half_w / half_h)
    pts = []
    for dx, dy in ((rad, 0), (-rad, 0), (0, rad), (0, -rad)):
        for z in (h * 0.25, h * 0.6, h):
            d = Vector((x + dx, y + dy, -0.5 + z)) - Vector(spec["loc"])
            zz = d.dot(f)
            if zz <= 0.5:
                continue
            pts.append((0.5 + 0.5 * (d.dot(r) / zz) / half_w,
                        0.5 - 0.5 * (d.dot(u) / zz) / half_h + shift, zz))
    if not pts:
        return None
    return (min(p[0] for p in pts), max(p[0] for p in pts),
            min(p[1] for p in pts), max(p[1] for p in pts), min(p[2] for p in pts))


def _crosses(cam_loc, x, y, polys):
    """True if the camera->tree segment crosses one of `polys` - i.e. the tree stands behind that wall.

    The colonnade polygons are not annuli (roof306 runs r 68.7-105.5 m about ARC_CENTRE because the end pylon
    sticks out), so a single radius threshold mis-sorts the first screen row.  The segment test is exact.
    """
    ax, ay = cam_loc[0], cam_loc[1]
    for poly in polys:
        n = len(poly)
        for k in range(n):
            cx, cy = poly[k]
            dx, dy = poly[(k + 1) % n]
            d1 = (dx - cx) * (ay - cy) - (dy - cy) * (ax - cx)
            d2 = (dx - cx) * (y - cy) - (dy - cy) * (x - cx)
            d3 = (x - ax) * (cy - ay) - (y - ay) * (cx - ax)
            d4 = (x - ax) * (dy - ay) - (y - ay) * (dx - ax)
            if ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0)):
                return True
    return False


def frame_band_relief(plan, land_ok=None, occluders=(), verbose=True):
    """Move (or, failing that, shorten) any tree that stands in front of a guarded frame band."""
    try:
        specs = {s["name"]: s for s in _cam_specs()}
    except Exception as e:
        print(f"[env_trees] frame_band_relief skipped: {e}")
        return plan
    trees = [list(t) for t in plan]
    moved = shortened = dropped = kept = 0
    report = []
    for band in FRAME_BANDS:
        name = next((n for n in specs if band["cam"] in n), None)
        if not name:
            continue
        spec = specs[name]
        f, r, u = _cam_basis(spec)
        for i, t in enumerate(trees):
            if t[3] <= 0.1:
                continue
            sp, x, y, h = t[0], t[1], t[2], t[3]
            box = _frame_box(spec, f, r, u, x, y, h, sp)
            if box is None:
                continue
            bx0, bx1, by0, by1, dist = box
            if bx1 < band["x0"] or bx0 > band["x1"] or by1 < band["y0"] or by0 > band["y1"]:
                continue
            if band.get("behind") == "colonnade" and _crosses(spec["loc"], x, y, occluders):
                continue                                       # behind the wing: this is the screen, keep it
            if "near" in band and dist > band["near"]:
                continue                                       # behind the subject
            # A PINNED tree (a PLAN group listed in band["pin"]) stands where the reference puts it and is never
            # relocated or dropped: the relief may only lower its crown, and if even that will not clear the band
            # it stays and is reported.  Lead decision after the round-5 review - the bands are cleared by thinning
            # the procedural screen, not by sweeping a hand-placed tree 36-48 m across the site.
            pinned = bool(band.get("pin")) and str(t[4]).split(" ")[0] in band["pin"]
            # push along the camera's right axis, whichever way is shorter, in 2 m steps.  The escape edges are
            # x0_exit/x1_exit (the box QA measures), which can be wider than the offence band.
            ex0 = band.get("x0_exit", band["x0"])
            ex1 = band.get("x1_exit", band["x1"])
            best = None
            for sgn in () if pinned else (-1.0, 1.0):
                for step in range(1, 26):
                    nx, ny = x + sgn * 2.0 * step * r.x, y + sgn * 2.0 * step * r.y
                    if land_ok is not None and not land_ok(nx, ny):
                        continue
                    nb = _frame_box(spec, f, r, u, nx, ny, h, sp)
                    if nb is None:
                        continue
                    if nb[1] < ex0 or nb[0] > ex1:
                        if best is None or step < best[0]:
                            best = (step, nx, ny)
                        break
            if best:
                t[1], t[2] = best[1], best[2]
                moved += 1
                report.append(f"    moved {sp:14s} ({x:6.1f},{y:6.1f}) -> ({best[1]:6.1f},{best[2]:6.1f}) "
                              f"{best[0] * 2:3.0f} m   {str(t[4])[:34]}")
                continue
            # nowhere to go: shorten until the crown drops below the band, or drop it.  A pinned tree may lose at
            # most 25 % of its height (the same allowance shadow_relief gives a hand-placed PLAN tree, which
            # carries a named reference feature) - a 13 m user-image cypress spire cut to 7 m is no longer a spire.
            floor = max(6.0, 0.75 * h) if pinned else 6.0
            new_h = h
            while new_h > floor:
                new_h -= 1.5
                nb = _frame_box(spec, f, r, u, x, y, new_h, sp)
                if nb is None or nb[2] > band["y1"]:
                    break
            if new_h > floor and new_h < h:
                t[3] = new_h
                shortened += 1
                report.append(f"    shortened {sp:11s} ({x:6.1f},{y:6.1f}) {h:.0f} -> {new_h:.0f} m   {str(t[4])[:34]}")
            elif pinned:
                kept += 1
                report.append(f"    kept {sp:16s} ({x:6.1f},{y:6.1f}) h{h:.0f}   hand-placed   {str(t[4])[:34]}")
            else:
                t[3] = 0.0
                dropped += 1
                report.append(f"    dropped {sp:13s} ({x:6.1f},{y:6.1f}) h{h:.0f}   {str(t[4])[:34]}")
    out = [tuple(t) for t in trees if t[3] > 0.1]
    if verbose:
        print(f"[env_trees] frame-band relief: moved {moved}, shortened {shortened}, dropped {dropped}, "
              f"kept (hand-placed) {kept} "
              f"({len(plan)} -> {len(out)} trees)")
        for line in report:
            print(line)
    return out


def plan_markdown(plan):
    lines = ["| # | species | X (S+) | Y (E+) | height m | note |", "|---|---|---|---|---|---|"]
    for i, (sp, x, y, h, note) in enumerate(plan):
        lines.append(f"| {i:02d} | {sp} | {x:.0f} | {y:.0f} | {h:.0f} | {note} |")
    return "\n".join(lines)


# ----------------------------------------------------------------------------- onto-land snap
def land_snap(plan, lagoon_field, islet_fields, stage="", verbose=True):
    """Put a tree that stands in the OSM water on the nearest land - GENERATED trees only.

    Round 9 review, finding 1.  This snap used to sit in the placement loop, i.e. AFTER `shadow_relief`'s podium
    ring and AFTER the gallery keep-out gate, and it moved anything it liked: six hand-placed PLAN entries were
    shifted up to 5.6 m at the last moment (env_r9f_build.log:141-148), which is why "PLAN holds the shipped
    coordinate" was still not true.  The A2 column shipped at (-38.7,-20.8) against PLAN (-37.9,-19.0), and the A
    redwood was snapped to r 35.0 - back inside the very 37 m podium ring its bake had just cleared it of, because
    nothing re-checked the ring afterwards.

    So the snap runs FIRST, before every gate, and it may not move a hand-placed tree.  A PLAN coordinate in the
    water is a plan bug: it FAILS THE BUILD, naming the tree and the nearest land point, and the coordinate is
    corrected by hand.  Every gate below then sees the position that ships, and the plan is the shipped plan.

    It is called twice - before `shadow_relief` and again after the relief passes, before the gallery gate - so a
    generated tree that a 12 m down-sun push dropped in the lagoon is still caught, and the gallery gate stays
    last.  The second call can only ever move a generated tree: the passes between them do not move pinned ones.
    """
    if lagoon_field is None:
        return list(plan)
    tag = f" ({stage})" if stage else ""

    def in_water(px, py):
        return lagoon_field.signed(px, py) < 1.0 and not any(f.signed(px, py) < 0 for f in islet_fields)

    def nearest_land(px, py):
        for r in range(1, 16):                       # 1 m spiral steps out to 15 m, 16 bearings
            for k in range(16):
                a = 2 * math.pi * k / 16
                xx, yy = px + r * math.cos(a), py + r * math.sin(a)
                if lagoon_field.signed(xx, yy) >= 1.0 or any(f.signed(xx, yy) < -0.5 for f in islet_fields):
                    return xx, yy
        return None

    out, bad, moved, stranded = [], [], 0, 0
    for (sp, x, y, h, note) in plan:
        if not in_water(x, y):
            out.append((sp, x, y, h, note))
            continue
        best = nearest_land(x, y)
        if str(note).split(" ")[0] in PIN_HAND_PLACED:
            bad.append((sp, x, y, note, best))
            out.append((sp, x, y, h, note))
            continue
        if best is None:
            stranded += 1
            print(f"[env_trees] land snap{tag}: WARNING {sp} at ({x:.0f},{y:.0f}) is in the water and there is no "
                  f"land within 15 m ({str(note)[:40]})")
            out.append((sp, x, y, h, note))
            continue
        moved += 1
        print(f"[env_trees] land snap{tag}: moved {sp} ({x:.1f},{y:.1f}) -> ({best[0]:.1f},{best[1]:.1f}) onto "
              f"land ({str(note)[:40]})")
        out.append((sp, best[0], best[1], h, note))
    if bad:
        for (sp, x, y, note, best) in bad:
            where = "no land within 15 m" if best is None else f"nearest land ({best[0]:.1f},{best[1]:.1f})"
            print(f"[env_trees] PLAN ERROR: hand-placed {sp} ({x:.1f},{y:.1f}) stands in the water - {where}  "
                  f"[{str(note)[:60]}]")
        raise RuntimeError(
            f"[env_trees] land snap{tag}: {len(bad)} hand-placed PLAN coordinate(s) in the water: "
            + ", ".join(f"{sp} ({x:.1f},{y:.1f})" for (sp, x, y, _n, _b) in bad)
            + " - fix env_trees.PLAN by hand; this pass may not move a pinned tree (r9 review, finding 1)")
    if verbose:
        print(f"[env_trees] land snap{tag}: {len(out)} trees, {moved} generated moved onto land, "
              f"{stranded} stranded, 0 hand-placed moved (a hand-placed tree in the water fails the build)")
    return out


# ----------------------------------------------------------------------------- placement
# measured Sapling crown radius / height (LOD0, renders/logs/p9_env_build6.log): the ring test for a widened crown
P10_REAL_R = {"cypress": 0.385, "cypress_column": 0.11, "pine": 0.61, "willow": 0.49, "redwood": 0.30,
              "broadleaf": 0.72, "eucalyptus": 0.54}


def p10_shadow_report(before, after, colonnade_polys, lagoon_field, terrain_height):
    """shadow_relief's four fractions (same samples, same sun) without and with the P10 additions."""
    samples = L.wing_samples(colonnade_polys, heights=(6.0,) + SHADOW_BANDS)
    band = [s for s in samples if s[3] >= min(SHADOW_BANDS)]
    if lagoon_field is not None:
        band = band + hero_water_samples(lagoon_field) + shore_sun_samples(lagoon_field, terrain_height)
    out = []
    for trees in (before, after):
        per, _ = L.shadowed_fraction(band, [list(t) for t in trees])
        frac = {}
        for (wi, _z), (tot, sh) in per.items():
            t, x = frac.get(wi, (0, 0))
            frac[wi] = (t + tot, x + sh)
        out.append({wi: 100.0 * v[1] / max(1, v[0]) for wi, v in frac.items()})
    names = ("north wing", "south wing", "hero water", "hero shore")
    print("[env_trees] p10 shadow cost (before -> after the P10_ADD columns): " + "  ".join(
        f"{names[k]} {out[0].get(k, 0):.1f} -> {out[1].get(k, 0):.1f} %" for k in range(4)))


def build_all(SUB, terrain_height, lagoon_field, islet_fields, quick=False, colonnade_polys=None, hall_poly=None, hall_field=None):
    t0 = time.time()
    lib = generate_library(quick=quick)
    src_coll, inst_coll = SUB["ENV_trees"], SUB["ENV_tree_instances"]
    # one sub-collection per LOD so the lead can swap LODs by view-layer exclusion even though ENV is linked.
    # Object flags give the defaults: viewport shows LOD1, renders use LOD0.
    lod_colls = {}
    for lod in (0, 1, 2):
        c = common.get_collection(f"ENV_tree_instances_LOD{lod}", parent=inst_coll)
        lod_colls[lod] = c
    # park the source meshes as hidden objects so the data blocks have users
    k = 0
    for (sp, seed), lods in lib.items():
        for lod, me in lods.items():
            o = bpy.data.objects.new(me.name, me)
            o.location = (-600.0 + 12.0 * k, -600.0 + 30.0 * lod, 0.0)
            o.hide_render = True
            o.hide_viewport = True
            src_coll.objects.link(o)
        k += 1
    plan = list(PLAN)
    if colonnade_polys and hall_poly:
        plan += screen_height_cap(redwood_screen(colonnade_polys, hall_poly, hall_field), colonnade_polys)
    # Round 9 review, finding 1: the onto-land snap is the FIRST pass, before the podium ring and the gallery
    # gate, and it never moves a hand-placed tree - see `land_snap`.
    plan = land_snap(plan, lagoon_field, islet_fields, stage="plan")
    if colonnade_polys and hall_poly:
        # QA-02-7: keep the low sun off the colonnade faces (see shadow_relief); QA-05-10 adds the shore belt
        plan = shadow_relief(plan, colonnade_polys, lagoon_field, terrain_height=terrain_height)

        # QA-03-10 / QA-03-13: clear the guarded frame bands last, so the sun relief cannot push a crown back in
        def _land(px, py):
            if lagoon_field is not None and lagoon_field.signed(px, py) < 1.5:
                return False
            if math.hypot(px, py) < 37.0:                    # the podium apron
                return False
            if hall_field is not None and hall_field.signed(px, py) < 2.0:
                return False
            if not L.gallery_clear(px, py):              # round 9: never onto the colonnade walk
                return False
            return all(not L.point_in_poly(px, py, L.offset_polygon(p, 2.0)) for p in colonnade_polys)

        plan = frame_band_relief(plan, land_ok=_land, occluders=colonnade_polys)

        # Only `shadow_relief`'s 12 m down-sun push can put a tree in the water after the plan pass above (the
        # frame-band clearer tests `_land` before it moves anything), and that push only ever moves a generated
        # tree, so this second snap cannot touch a hand-placed one.  It runs BEFORE the gallery gate so the gate
        # still has the last word.
        plan = land_snap(plan, lagoon_field, islet_fields, stage="after relief")

        # Round 9, LAST gate: nothing stands on the colonnade gallery walk.  The relief passes above move trees,
        # so the check has to run after them.  A tree is DROPPED here, never nudged: a nudge would put it back in
        # a frame band the pass above has just cleared, and a tree inside the walk is a placement bug, not a
        # composition choice.  Hand-placed PLAN entries are named in the log so the coordinate can be corrected.
        gated = []
        for e in plan:
            off = L.gallery_offset(e[1], e[2])
            if off is not None and off < L.GALLERY_KEEPOUT:
                print(f"[env_trees] gallery keep-out: dropped {e[0]} ({e[1]:.1f},{e[2]:.1f}) h{e[3]:.0f} at "
                      f"{off:.2f} m from the walk centreline  [{str(e[4])[:40]}]")
                continue
            gated.append(e)
        print(f"[env_trees] gallery keep-out ({L.GALLERY_KEEPOUT} m): {len(plan)} -> {len(gated)} trees")
        plan = gated
        # Phase 8d belt r2, LAST: the hall's east-face belt is appended after every relief pass and after the
        # gallery gate.  It is placed against the HALL by measurement (see `hall_belt`), not composed against a
        # frame band, and it must not shift a single existing tree: appending it here leaves the relief passes'
        # inputs, their RNG streams, and the placement loop's own draw order for trees 0..N-1 exactly as they
        # were.  Its own keep-outs (hall, podium ring, gallery walk, colonnade roofs) are inside `hall_belt`.
        plan = plan + hall_belt(hall_poly, hall_field, terrain_height, colonnade_polys)
        # Phase 10 item 1, LAST: the two NE-mass columns (see P10_ADD).  Appended after everything so no existing
        # tree changes; the three hard gates are re-checked here and a failure stops the build.
        before = list(plan)
        for (sp, x, y, h, note, w) in P10_ADD:
            dry = lagoon_field is None or not (lagoon_field.signed(x, y) < 1.0
                                               and not any(f.signed(x, y) < 0 for f in islet_fields))
            off = L.gallery_offset(x, y)
            ring = math.hypot(x, y) - max(L.CROWN_R.get(sp, 0.35), P10_REAL_R.get(sp, 0.35) * w) * h
            assert dry and (off is None or off >= L.GALLERY_KEEPOUT) and ring >= 37.0, \
                f"P10_ADD {sp} ({x}, {y}) fails a hard gate: dry {dry} gallery {off} ring {ring:.1f}"
            plan.append((sp, x, y, h, note))
        # Phase 10 round 2, LAST: the crown ref 169 has left of the hero-shore willow (see P10R2_ADD).  Same rule
        # as P10_ADD (appended, nothing before it changes), and the gates ring the WIDENED crown (CROWN_XY x w)
        # and keep 3.5 m from every trunk already in the plan.
        for (sp, x, y, h, note, w) in P10R2_ADD:
            dry = lagoon_field is None or not (lagoon_field.signed(x, y) < 1.0
                                               and not any(f.signed(x, y) < 0 for f in islet_fields))
            off = L.gallery_offset(x, y)
            ring = math.hypot(x, y) - max(L.CROWN_R.get(sp, 0.35), P10_REAL_R.get(sp, 0.35) * CROWN_XY.get(sp, 1.0) * w) * h
            space = min(math.hypot(x - e[1], y - e[2]) for e in plan)
            assert dry and (off is None or off >= L.GALLERY_KEEPOUT) and ring >= 37.0 and space >= 3.5, \
                f"P10R2_ADD {sp} ({x}, {y}) fails a hard gate: dry {dry} gallery {off} ring {ring:.1f} space {space:.1f}"
            plan.append((sp, x, y, h, note))
        p10_shadow_report(before, plan, colonnade_polys, lagoon_field, terrain_height)
    rnd = random.Random(77)
    widen = {note: w for (_sp, _x, _y, _h, note, w) in P10_ADD + P10R2_ADD}
    widen.update(P10R2_WIDEN)
    counts = {}
    per_species_idx = {}
    belt_rows = []
    for i, (sp, x, y, h, note) in enumerate(plan):
        seeds = [s for (s2, s) in lib.keys() if s2 == sp]
        if not seeds:
            continue
        seed = seeds[i % len(seeds)]
        lods = lib[(sp, seed)]
        gen_h = lods[0]["gen_height"]
        scale = h / max(1e-3, gen_h)
        # Ground.  The onto-land snap is NOT here any more (r9 review, finding 1): it ran after every gate, so a
        # coordinate it moved was never re-checked against the podium ring or the gallery walk, and it moved
        # hand-placed trees.  It is `land_snap`, above, and by this point the plan is the shipped plan - the loop
        # only reads it.
        z = terrain_height(x, y) - 0.15
        # LOD0 budget: a tree uses the LOD1 mesh for LOD0 when no QA camera is within FAR_RADIUS of it, and the
        # E2/E3 back screen rows always do (they stand 100-140 m behind the wings and are half occluded by row E1).
        cam_d = min([math.hypot(x - cx, y - cy) for (cx, cy) in CAM_XY], default=1e9)
        far = cam_d > FAR_RADIUS or note.startswith(("H", "E2", "E3"))
        # back screen rows AND the 8d hall belt: LOD2 mesh for LOD1, i.e. the export's far-tree path (billboard +
        # baked impostor) and LOD1 geometry for the Cycles LOD0 at 140-150 m.
        light = note.startswith(("E2", "E3", "HB"))
        n = per_species_idx.get(sp, 0)
        per_species_idx[sp] = n + 1
        rot = rnd.uniform(0, 2 * math.pi)
        sx = scale * rnd.uniform(0.82, 1.16)
        sy = scale * rnd.uniform(0.82, 1.16)
        # Phase 10: extra X/Y crown width (per species, and per P10_ADD entry) - multiplies after the draws, so the
        # RNG stream every other tree reads is unchanged.
        xy = CROWN_XY.get(sp, 1.0) * widen.get(note, 1.0)
        sx, sy = sx * xy, sy * xy
        sz = scale * rnd.uniform(0.94, 1.08)
        tilt_a = rnd.uniform(0, 2 * math.pi)
        tilt = math.radians(rnd.uniform(0.0, 4.5))       # wind lean: no two crowns share a silhouette
        for lod in (0, 1, 2):
            me = lods[lod]
            if far and lod == 0:
                me = lods[1]
            if far and lod == 1:
                me = lods[2]
            if light and lod == 1:
                me = lods[2]
            o = bpy.data.objects.new(f"ENV_tree_{sp}_{n:02d}_LOD{lod}", me)
            o.location = (x, y, z)
            o.rotation_euler = (tilt * math.cos(tilt_a), tilt * math.sin(tilt_a), rot)
            o.scale = (sx, sy, sz)
            o["species"] = sp
            o["seed"] = seed
            o["height_m"] = h
            o["note"] = note
            o.hide_render = lod != 0
            o.hide_viewport = lod != 1
            lod_colls[lod].objects.link(o)
            if lod == 1 and str(note).startswith("HB"):
                # the export reads the _LOD1 OBJECT and keys its impostor on that object's MESH name
                # (`gate1_set.py` tree rows -> `prototype`), so that is what this row records.
                belt_rows.append(dict(name=o.name, lod1_object=o.name, prototype=me.name, species=sp, seed=seed,
                                      location=[round(x, 3), round(y, 3), round(z, 3)],
                                      scale=[round(sx, 4), round(sy, 4), round(sz, 4)],
                                      rotation_z_deg=round(math.degrees(rot), 2), height_m=round(h, 2),
                                      note=note))
        counts[sp] = counts.get(sp, 0) + 1
    print(f"[env_trees] placed {sum(counts.values())} trees {counts} in {time.time() - t0:.0f}s")
    if belt_rows:
        write_belt_manifest(belt_rows)
    return plan


# Phase 8d belt r2, item 5 of the brief: the far-tree rows the viewer will gain, in a form the export can diff.
# `prototype` is the LOD1 object's mesh name, which is exactly the key `export/gate1_set.py` puts on a far tree and
# `impostors.prototype_map` resolves to one of the 16 baked atlases.
BELT_MANIFEST = common.ROOT / "docs" / "phase8d_belt_r2_trees.json"


def write_belt_manifest(rows):
    protos = {}
    species = {}
    for r in rows:
        protos[r["prototype"]] = protos.get(r["prototype"], 0) + 1
        species[r["species"]] = species.get(r["species"], 0) + 1
    doc = dict(
        what="Phase 8d belt r2: the tree belt on the exhibition hall's east face, placed by env_trees.hall_belt "
             "and appended to the planting plan after every relief pass. Every row is an ordinary far tree: its "
             "_LOD1 object carries the _LOD2 mesh, so the export gives it a 2-triangle billboard and an impostor.",
        source="scripts/env_trees.py (hall_belt + build_all)",
        count=len(rows), species=species, prototypes=protos,
        top_cap_world_z=HALL_BELT_TOP_Z, step_m=HALL_BELT_STEP,
        prototype_key="the _LOD1 object's mesh name = export/gate1_set.py far-tree `prototype`; "
                      "impostors.prototype_map maps the _LOD2 name onto the baked _LOD1 atlas",
        trees=sorted(rows, key=lambda r: r["name"]))
    BELT_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    BELT_MANIFEST.write_text(json.dumps(doc, indent=1))
    print(f"[env_trees] hall belt manifest: {len(rows)} trees, {len(protos)} prototypes -> {BELT_MANIFEST}")


# ----------------------------------------------------------------------------- standalone line-up test
if __name__ == "__main__":
    args = common.script_args()
    bpy.ops.wm.read_homefile(use_empty=True)
    common.wipe_scene()
    scene = common.setup_scene()
    coll = common.rebuild_collection("LINEUP")
    only = [a for a in args if a in SPECIES]
    lib = generate_library(quick=("--all-seeds" not in args), species=only or None)
    spacing = 42.0
    ground = bpy.data.meshes.new("ground")
    ground.from_pydata([(-100, -3000, 0), (600, -3000, 0), (600, 300, 0), (-100, 300, 0)], [], [(0, 1, 2, 3)])
    go = bpy.data.objects.new("ground", ground)
    coll.objects.link(go)
    common.assign_material(go, L.mat("MAT_lawn"))
    rows = {0: [], 1: [], 2: []}
    x = 0.0
    order = []
    for (sp, seed), lods in lib.items():
        order.append(f"{sp}/{seed}")
        for lod in (0, 1, 2):
            o = bpy.data.objects.new(f"{sp}_{seed}_LOD{lod}", lods[lod])
            o.location = (x, -lod * 1000.0, 0.0)
            coll.objects.link(o)
            rows[lod].append(o)
        x += spacing
    print("[env_trees] line-up order (camera looks along -Y, so IMAGE LEFT -> RIGHT is):", ", ".join(reversed(order)))
    cam = bpy.data.cameras.new("cam")
    cam.lens = 24
    co = bpy.data.objects.new("cam", cam)
    coll.objects.link(co)
    scene.camera = co
    sun = bpy.data.lights.new("sun", "SUN")
    sun.energy = 3.0
    so = bpy.data.objects.new("sun", sun)
    coll.objects.link(so)
    common.aim_sun(so, 140, 35)
    world = bpy.data.worlds.new("w")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.5, 0.65, 0.9, 1)
    world.node_tree.nodes["Background"].inputs[1].default_value = 0.6
    scene.world = world
    common.configure_eevee(scene, samples=8)
    scene.render.resolution_x, scene.render.resolution_y = 1920, 640
    ts = common.timestamp()
    out_dir = common.RENDERS / "previews" / "environment"
    out_dir.mkdir(parents=True, exist_ok=True)
    cx = (x - spacing) / 2
    for lod in (0, 1, 2):
        co.location = (cx, -lod * 1000.0 + 150.0, 20.0)
        co.rotation_euler = common.lookat_rotation(co.location, (cx, -lod * 1000.0, 12.0))
        scene.render.filepath = str(out_dir / f"{ts}_tree_lineup_LOD{lod}.png")
        bpy.ops.render.render(write_still=True)
        print("[env_trees] lineup:", scene.render.filepath)
    # hero-distance test: LOD0 row from 120 m with the QA hero lens (31 mm), eye level
    co.location = (cx, 120.0, 1.0)
    cam.lens = 31
    co.rotation_euler = common.lookat_rotation(co.location, (cx, 0.0, 12.0))
    scene.render.filepath = str(out_dir / f"{ts}_tree_lineup_hero120m.png")
    bpy.ops.render.render(write_still=True)
    print("[env_trees] done")
