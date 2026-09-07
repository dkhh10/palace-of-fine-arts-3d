"""Trees for the Palace of Fine Arts environment: Sapling species presets -> meshes with 3 LODs -> placed instances.

Species (from docs/reference_sheet.md section 6): Monterey cypress, blue-gum eucalyptus, Monterey pine, weeping
willow, coast redwood, generic broadleaf. Each species has 2-3 seeds; every (species, seed, LOD) is ONE mesh shared by
all its instances. Instances are objects `ENV_tree_<species>_<nn>_LOD<k>` in ENV_tree_instances; the source objects
live in ENV_trees (hidden).

Standalone test (renders a line-up of every species against the sky):
    blender --background --python scripts/env_trees.py -- --lineup
"""
import bpy, bmesh, sys, os, math, random, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
import env_lib as L
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
        scale=20.0, scaleV=2.0, leaves=44, leafScale=0.85, leafScaleX=0.32, leafScaleV=0.35, bend=0.3, leafangle=5.0,
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
        scale=24.0, scaleV=2.0, leaves=44, leafScale=0.85, leafScaleX=0.32, leafScaleV=0.35, bend=0.3, leafangle=5.0,
        leafShape="rect", horzLeaves=False, leafDownAngle=55.0, leafDownAngleV=25.0, leafRotate=137.5, leafRotateV=40.0,
        bark="MAT_bark_cypress", leaf="MAT_leaf_cypress", height=(18, 28)),
    # tall straight trunk, high open crown, hanging foliage
    "eucalyptus": dict(
        levels=3, length=(1.0, 0.24, 0.5, 0.0), lengthV=(0.0, 0.2, 0.25, 0.0), branches=(0, 20, 14, 0),
        curveRes=(10, 5, 4, 1), curve=(0.0, 10.0, -25.0, 0.0), curveV=(25.0, 50.0, 80.0, 0.0),
        shape="8", customShape=(0.4, 1.0, 0.55, 0.6), branchDist=1.4, baseSize=0.4, baseSize_s=0.35,
        ratio=0.016, ratioPower=1.3, scale0=1.0, scaleV0=0.1, rootFlare=1.15,
        downAngle=(90.0, 32.0, 50.0, 45.0), downAngleV=(0.0, -20.0, 20.0, 10.0), rotate=(137.5, 137.5, 137.5, 137.5),
        rotateV=(20.0, 20.0, 40.0, 0.0), attractUp=(0.4, 0.8, -1.3, 0.0), segSplits=(0.15, 0.3, 0.0, 0.0),
        splitAngle=(20.0, 25.0, 0.0, 0.0), splitAngleV=(5.0, 8.0, 0.0, 0.0), splitByLen=True, splitHeight=0.35, baseSplits=1,
        scale=30.0, scaleV=3.0, leaves=32, leafScale=1.3, leafScaleX=0.45, leafScaleV=0.3, bend=0.2, leafangle=-70.0,
        leafDownAngle=70.0, leafDownAngleV=20.0, leafRotate=137.5, leafRotateV=40.0,
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
        scale=21.0, scaleV=2.0, leaves=40, leafScale=0.95, leafScaleX=0.3, leafScaleV=0.35, bend=0.3, leafangle=0.0,
        leafShape="rect", horzLeaves=False, leafDownAngle=60.0, leafDownAngleV=25.0, leafRotate=137.5, leafRotateV=40.0,
        bark="MAT_bark_cypress", leaf="MAT_leaf_cypress", height=(15, 24)),
    # weeping willow at the water's edge
    "willow": dict(
        levels=3, length=(0.75, 0.5, 1.4, 0.0), lengthV=(0.0, 0.1, 0.1, 0.0), branches=(0, 30, 14, 0),
        curveRes=(6, 8, 6, 1), curve=(0.0, 20.0, -40.0, 0.0), curveV=(120.0, 100.0, 0.0, 0.0), curveBack=(0.0, 20.0, 0.0, 0.0),
        shape="4", shapeS="4", branchDist=1.5, baseSize=0.2, baseSize_s=0.25, baseSplits=2,
        ratio=0.025, ratioPower=1.75, scale0=1.0, scaleV0=0.0, rootFlare=1.1,
        downAngle=(0.0, 20.0, 30.0, 20.0), downAngleV=(0.0, 20.0, 10.0, 10.0), rotate=(99.5, 137.5, -60.0, 140.0),
        rotateV=(15.0, 15.0, 45.0, 0.0), attractUp=(0.0, 0.0, -2.75, -3.0), segSplits=(0.1, 0.2, 0.2, 0.0),
        splitAngle=(12.0, 30.0, 16.0, 0.0), splitAngleV=(0.0, 10.0, 20.0, 0.0), splitByLen=True, handleType="1",
        scale=11.0, scaleV=1.5, leaves=50, leafScale=0.95, leafScaleX=0.16, leafScaleV=0.3, bend=0.0, leafangle=-70.0,
        leafDownAngle=30.0, leafDownAngleV=10.0, leafRotate=137.5, leafRotateV=30.0, horzLeaves=False, leafDist="10",
        bark="MAT_bark_cypress", leaf="MAT_leaf_broadleaf", height=(8, 12)),
    # coast redwood: narrow conical, flat horizontal sprays
    "redwood": dict(
        levels=3, length=(1.0, 0.24, 0.45, 0.0), lengthV=(0.0, 0.15, 0.2, 0.0), branches=(0, 55, 9, 0),
        curveRes=(10, 4, 3, 1), curve=(0.0, 5.0, -5.0, 0.0), curveV=(15.0, 30.0, 40.0, 0.0),
        shape="0", branchDist=1.0, baseSize=0.15, baseSize_s=0.3,
        ratio=0.014, ratioPower=1.2, scale0=1.1, scaleV0=0.05, rootFlare=1.4,
        downAngle=(90.0, 82.0, 50.0, 45.0), downAngleV=(0.0, 10.0, 15.0, 10.0), rotate=(137.5, 137.5, 137.5, 137.5),
        rotateV=(15.0, 20.0, 30.0, 0.0), attractUp=(0.0, 0.25, 0.1, 0.0), segSplits=(0.0, 0.0, 0.0, 0.0),
        splitAngle=(0.0, 0.0, 0.0, 0.0), splitAngleV=(0.0, 0.0, 0.0, 0.0), splitByLen=True,
        scale=30.0, scaleV=3.0, leaves=30, leafScale=0.9, leafScaleX=0.35, leafScaleV=0.35, bend=0.25, leafangle=0.0,
        leafShape="rect", horzLeaves=False, leafDownAngle=50.0, leafDownAngleV=20.0, leafRotate=137.5, leafRotateV=30.0,
        bark="MAT_bark_cypress", leaf="MAT_leaf_cypress", height=(18, 32)),
    # generic round-crowned broadleaf (acacia / plane / young oak)
    "broadleaf": dict(
        levels=3, length=(1.0, 0.5, 0.5, 0.0), lengthV=(0.0, 0.15, 0.2, 0.0), branches=(0, 22, 12, 0),
        curveRes=(6, 5, 3, 1), curve=(0.0, -20.0, -20.0, 0.0), curveV=(30.0, 60.0, 70.0, 0.0),
        shape="1", branchDist=1.0, baseSize=0.3, baseSize_s=0.3, baseSplits=2,
        ratio=0.02, ratioPower=1.2, scale0=1.0, scaleV0=0.1, rootFlare=1.2,
        downAngle=(90.0, 55.0, 45.0, 45.0), downAngleV=(0.0, -30.0, 10.0, 10.0), rotate=(137.5, 137.5, 137.5, 137.5),
        rotateV=(20.0, 20.0, 30.0, 0.0), attractUp=(0.5, 0.3, 0.2, 0.0), segSplits=(0.2, 0.3, 0.1, 0.0),
        splitAngle=(25.0, 25.0, 20.0, 0.0), splitAngleV=(5.0, 8.0, 8.0, 0.0), splitByLen=True, splitHeight=0.25,
        scale=12.0, scaleV=1.5, leaves=18, leafScale=0.75, leafScaleX=0.9, leafScaleV=0.3, bend=0.3, leafangle=0.0,
        leafDownAngle=45.0, leafDownAngleV=20.0, leafRotate=137.5, leafRotateV=40.0,
        bark="MAT_bark_cypress", leaf="MAT_leaf_broadleaf", height=(8, 14)),
}
SEEDS = {"cypress": (3, 17, 41), "cypress_column": (2, 31), "eucalyptus": (5, 23, 61), "pine": (7, 29), "willow": (11, 37),
         "redwood": (13, 43), "broadleaf": (19, 53)}

# LOD overrides: geometry resolution and leaf density (skeleton stays identical for the same seed)
LOD_OVERRIDES = {
    0: dict(bevelRes=1, resU=2),
    1: dict(bevelRes=0, resU=1, leaf_factor=0.5, leaf_scale=1.3),
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
    me.materials.append(L.mat(sp["leaf"]))
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
PLAN = [
    # A. peninsula north lobe (land X -40..-16, Y 0..26): the dense dark cluster right of the rotunda (user image, 169)
    ("pine", -31.0, 14.0, 21.0, "A peninsula north lobe, cluster core (satellite crown (-35,16))"),
    ("redwood", -27.0, 8.0, 16.0, "A young redwood in front of the north arch (ref 070)"),
    ("cypress", -36.0, 6.0, 24.0, "A dark mass right of the dome"),
    ("pine", -38.0, 17.0, 22.0, "A"),
    ("willow", -36.0, 24.0, 10.0, "A pale weeping willow at the water in front of the cluster (ref 169)"),
    ("broadleaf", -30.0, 22.0, 11.0, "A shore broadleaf"),
    # A2. strip between the north wing and the embayment (3-13 m wide per OSM, canopy overhangs both)
    ("cypress_column", -36.0, -18.0, 27.0, "A2 tall column right of the rotunda (user image x~1020)"),
    ("pine", -47.0, -13.0, 17.0, "A2 strip along the north wing (kept below the colonnade entablature)"),
    ("cypress_column", -58.0, -12.5, 27.0, "A2 second column (user image x~1220)"),
    ("cypress", -68.0, 9.5, 24.0, "A2 at the wing's first box"),
    # B. north wing strip further out and the north shore
    ("eucalyptus", -79.0, 26.0, 28.0, "B big eucalyptus on the strip (ref 141)"),
    ("pine", -90.0, 22.5, 20.0, "B"),
    ("willow", -100.0, 37.0, 9.0, "B willow at the water (refs 144/145)"),
    ("eucalyptus", -106.0, 20.0, 30.0, "B big eucalyptus behind the willows (ref 171)"),
    ("cypress", -118.0, 8.0, 22.0, "B beyond the north pylon"),
    ("cypress_column", -112.0, 40.0, 24.0, "B tall column beyond the north pylon (ref 169 right)"),
    # C. south side: columns on the strip between the south wing and the south embayment
    ("cypress_column", 45.0, -8.0, 26.0, "C cypress column left of the rotunda (user image x~290)"),
    ("cypress_column", 41.0, -13.0, 24.0, "C second column (user image x~330)"),
    ("broadleaf", 20.0, 17.0, 13.0, "C small dark tree touching the rotunda's left edge (user image x~410), in the podium planter zone"),
    ("eucalyptus", 62.0, -30.0, 30.0, "C broad eucalyptus behind the south wing (ref 169 left)"),
    ("pine", 24.0, -22.0, 18.0, "C satellite crown (19,-13)"),
    ("broadleaf", 31.0, -7.0, 10.0, "C satellite crown (26,-3), small"),
    # D. south shore near the south wing and pylon
    ("cypress_column", 66.0, 40.0, 22.0, "D dense cypress behind the south pylon (ref 169 far left)"),
    ("eucalyptus", 76.0, 46.0, 28.0, "D"),
    ("pine", 92.0, 58.0, 18.0, "D"),
    ("willow", 78.0, 50.0, 9.0, "D willow at the south end of the lagoon"),
    ("eucalyptus", 104.0, 52.0, 30.0, "D south pylon"),
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
FAR_RADIUS = 150.0   # beyond this, LOD0/LOD1 objects use the LOD1 mesh (LOD1 cap)


def redwood_screen(colonnade_polys, hall_poly):
    """Redwoods (1968 planting, DPR) in the strip between each colonnade's back edge and the hall's front wall."""
    out = []
    rnd = random.Random(5)
    for wing in colonnade_polys[:2]:
        xs = [p[0] for p in wing]
        x0, x1 = min(xs) + 4, max(xs) - 4
        x = x0
        while x <= x1:
            ys_w = [p[1] for p in wing if abs(p[0] - x) < 4.0]
            ys_h = [p[1] for p in hall_poly if abs(p[0] - x) < 6.0]
            if ys_w and ys_h:
                y_back = min(ys_w)
                y_hall = max(y for y in ys_h if y < y_back) if any(y < y_back for y in ys_h) else y_back - 22
                if y_back - y_hall > 8:
                    y = (y_back + y_hall) / 2 + rnd.uniform(-2.5, 2.5)
                    sp = "redwood" if rnd.random() < 0.7 else ("cypress" if rnd.random() < 0.5 else "pine")
                    h = rnd.uniform(22, 32) if sp == "redwood" else rnd.uniform(18, 24)
                    out.append((sp, x + rnd.uniform(-2, 2), y, h, "E redwood screen"))
            x += rnd.uniform(8.0, 11.0)
    return out


def plan_markdown(plan):
    lines = ["| # | species | X (S+) | Y (E+) | height m | note |", "|---|---|---|---|---|---|"]
    for i, (sp, x, y, h, note) in enumerate(plan):
        lines.append(f"| {i:02d} | {sp} | {x:.0f} | {y:.0f} | {h:.0f} | {note} |")
    return "\n".join(lines)


# ----------------------------------------------------------------------------- placement
def build_all(SUB, terrain_height, lagoon_field, islet_fields, quick=False, colonnade_polys=None, hall_poly=None):
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
        plan += redwood_screen(colonnade_polys, hall_poly)
    rnd = random.Random(77)
    counts = {}
    per_species_idx = {}
    for i, (sp, x, y, h, note) in enumerate(plan):
        seeds = [s for (s2, s) in lib.keys() if s2 == sp]
        if not seeds:
            continue
        seed = seeds[i % len(seeds)]
        lods = lib[(sp, seed)]
        gen_h = lods[0]["gen_height"]
        scale = h / max(1e-3, gen_h)
        # ground: trees stand on land; if a coordinate falls in the OSM water (shore trace vs photo), move it to the
        # nearest land within 15 m (spiral search) and report
        x0, y0 = x, y
        if lagoon_field.signed(x, y) < 1.0 and not any(f.signed(x, y) < 0 for f in islet_fields):
            best = None
            for r in range(1, 16):
                for k in range(16):
                    a = 2 * math.pi * k / 16
                    xx, yy = x0 + r * math.cos(a), y0 + r * math.sin(a)
                    if lagoon_field.signed(xx, yy) >= 1.0 or any(f.signed(xx, yy) < -0.5 for f in islet_fields):
                        best = (xx, yy)
                        break
                if best:
                    break
            if best:
                x, y = best
                print(f"[env_trees] moved {sp} ({x0:.0f},{y0:.0f}) -> ({x:.1f},{y:.1f}) onto land ({note[:30]})")
            else:
                print(f"[env_trees] WARNING {sp} at ({x0:.0f},{y0:.0f}) is in the water and no land within 15 m ({note[:30]})")
        z = terrain_height(x, y) - 0.15
        far = math.hypot(x, y) > FAR_RADIUS
        n = per_species_idx.get(sp, 0)
        per_species_idx[sp] = n + 1
        rot = rnd.uniform(0, 2 * math.pi)
        sxy = scale * rnd.uniform(0.9, 1.1)
        for lod in (0, 1, 2):
            me = lods[1] if (far and lod < 1) else lods[lod]
            o = bpy.data.objects.new(f"ENV_tree_{sp}_{n:02d}_LOD{lod}", me)
            o.location = (x, y, z)
            o.rotation_euler = (0.0, 0.0, rot)
            o.scale = (sxy, sxy, scale)
            o["species"] = sp
            o["seed"] = seed
            o["height_m"] = h
            o["note"] = note
            o.hide_render = lod != 0
            o.hide_viewport = lod != 1
            lod_colls[lod].objects.link(o)
        counts[sp] = counts.get(sp, 0) + 1
    print(f"[env_trees] placed {sum(counts.values())} trees {counts} in {time.time() - t0:.0f}s")
    return plan


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
