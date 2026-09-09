"""Materials verification inside the FULL assembled scene (round 3, QA-02-2 / -3 / -6).

    blender -b --python scripts/mat_scene_check.py -- [--blend master.blend] [--samples 48] [--tag r3]

The lineup in materials.blend cannot answer "does the algae band read at the waterline in the master" or "is the
stone still blotchy at 100 m", because it has neither ARCH's geometry nor ENV's water. This opens the assembled
master, adds two materials-owned close cameras (never saved back), and renders them with the lighting agent's final
Cycles preset:

  CAM_mat_scene_waterline  - a 50 mm three-quarter close on the podium / rostra where the stone meets z = WATER_Z,
                             placed from the actual bounding box of the podium objects so it does not need hand-tuning.
  CAM_mat_scene_stone      - a long lens on the entablature / spandrel zone from the hero station, i.e. QA's
                             "1:1 crop" of the hero, rendered directly instead of upscaled.

Outputs renders/previews/materials/<tag>_scene_<name>.png. Nothing is written back to any .blend.
"""
import bpy, sys, os, time, math
from pathlib import Path
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common

args = common.script_args()


def arg(name, default=None):
    if name in args:
        i = args.index(name)
        return args[i + 1] if i + 1 < len(args) else True
    return default


BLEND = Path(arg("--blend", str(common.ROOT / "master.blend")))
SAMPLES = int(arg("--samples", 48))
TAG = str(arg("--tag", "r3"))
OUT = common.RENDERS / "previews" / "materials"
OUT.mkdir(parents=True, exist_ok=True)

t0 = time.time()
bpy.ops.wm.open_mainfile(filepath=str(BLEND), load_ui=False)
scene = bpy.context.scene
bpy.context.view_layer.update()   # matrix_world is stale until the depsgraph runs (same trap as build_master)
print(f"[mat_scene] opened {BLEND.name} in {time.time() - t0:.1f}s; {len(bpy.data.objects)} objects")


def visible_bbox(pred):
    lo = Vector((1e9, 1e9, 1e9))
    hi = Vector((-1e9, -1e9, -1e9))
    n = 0
    for o in scene.objects:
        if o.type != "MESH" or o.hide_render or not pred(o.name):
            continue
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c)
            lo = Vector((min(lo[i], w[i]) for i in range(3)))
            hi = Vector((max(hi[i], w[i]) for i in range(3)))
        n += 1
    return (lo, hi, n) if n else (None, None, 0)


def add_cam(name, loc, aim, lens=50.0):
    cam = bpy.data.cameras.new(name)
    cam.lens = lens
    cam.clip_start, cam.clip_end = 0.1, 2000.0
    ob = bpy.data.objects.new(name, cam)
    scene.collection.objects.link(ob)
    ob.location = Vector(loc)
    d = Vector(aim) - Vector(loc)
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    return ob


lo, hi, n = visible_bbox(lambda s: s.startswith("ARCH_site"))
if n:
    print(f"[mat_scene] ARCH_site bbox from {n} objects: {[round(v,1) for v in lo]} .. {[round(v,1) for v in hi]}")

# Both close cameras stand at the hero station and use long lenses, so they crop exactly what QA crops out of the
# hero at 1:1 rather than showing a view nobody scores. (A bbox-placed camera picked up the whole site and framed a
# lawn instead of the shoreline.)
def swap_library():
    """Re-append assets/materials.blend over the copies build_master baked into this master, and redo the ornament
    per-asset material pass. build_master *appends* the library, so a rebuilt library never reaches an existing
    master; doing the swap here means the before/after pair differs by the library and by nothing else (same
    geometry, same rig, same baked light probes) instead of by two whole master builds."""
    # --lib lets the before/after pair be two *library versions* on one master: point it at a materials.blend
    # extracted from git (git show <rev>:assets/materials.blend > /tmp/mat_rN.blend) for the "before" render.
    lib = Path(str(arg("--lib", str(common.ASSET_FILES["MAT"]))))
    print(f"[mat_scene] swap library: {lib}")
    with bpy.data.libraries.load(str(lib), link=False) as (src, dst):
        lib_names = set(src.materials)
        wanted = sorted({m.name.split(".")[0] for m in bpy.data.materials} & lib_names)
        for m in list(bpy.data.materials):
            if m.name.split(".")[0] in wanted:
                m.name = m.name.split(".")[0] + "__old" + m.name[len(m.name.split(".")[0]):]
        dst.materials = wanted
    remapped = 0
    for m in list(bpy.data.materials):
        if "__old" in m.name:
            base = m.name.split("__old")[0]
            new = bpy.data.materials.get(base)
            if new is not None and new is not m:
                m.user_remap(new); bpy.data.materials.remove(m); remapped += 1
    print(f"[mat_scene] swap: {len(wanted)} library materials re-appended, {remapped} old copies remapped")
    # ornament per-asset maps: exactly build_master.orn_material_for(), so this verifies that routing too
    base = bpy.data.materials.get("MAT_ornament_concrete")
    if base is None or base.node_tree.nodes.get("ORN_NORMAL") is None:
        print("[mat_scene] swap: MAT_ornament_concrete has no ORN_NORMAL node, no per-asset copies")
        return
    cache, plugged = {}, 0
    inst = bpy.data.collections.get("INSTANCES")
    for ob in (inst.all_objects if inst else []):
        if "variant" not in ob.keys():
            continue
        src_obj = next((o for o in bpy.data.objects if o.data == ob.data and o.name.startswith("ORN_")), None)
        if src_obj is None or "normal_map" not in src_obj.keys():
            continue
        key = src_obj.name
        if key not in cache:
            m = base.copy(); m.name = f"MAT_ornament_concrete__{key}"
            for prop, node_name, cs in (("normal_map", "ORN_NORMAL", "Non-Color"), ("ao_map", "ORN_AO", "Non-Color")):
                node = m.node_tree.nodes.get(node_name)
                p = str(src_obj.get(prop) or "")
                p = str(common.ASSETS / p[2:]) if p.startswith("//") else p
                if node and p and Path(p).exists():
                    img = bpy.data.images.load(p, check_existing=True)
                    img.colorspace_settings.name = cs
                    node.image = img
            cache[key] = m
        for slot in ob.material_slots:
            slot.link = "OBJECT"; slot.material = cache[key]
        plugged += 1
    print(f"[mat_scene] swap: {len(cache)} per-asset ornament materials on {plugged} instances")


if "--swap" in args:
    swap_library()
if "--probe" in args:
    # QA-04-3c reported "the shore strip is one uniform pale concrete tone". Before spending a render on it, list
    # every mesh whose bounding box actually crosses the waterline band and say which material is on it: a band the
    # library paints at z = WATER_Z is invisible if the geometry there belongs to somebody else's material.
    from collections import defaultdict
    zlo, zhi = common.WATER_Z - 0.6, common.WATER_Z + 2.0
    hit = defaultdict(lambda: [0, 0.0])
    for o in scene.objects:
        if o.type != "MESH" or o.hide_render:
            continue
        zs = [(o.matrix_world @ Vector(c)).z for c in o.bound_box]
        if min(zs) > zhi or max(zs) < zlo:
            continue
        ctr = sum((o.matrix_world @ Vector(c) for c in o.bound_box), Vector()) / 8.0
        if ctr.length > 220.0:
            continue
        for sl in o.material_slots:
            key = (sl.material.name if sl.material else "<none>")
            hit[key][0] += 1
            hit[key][1] = max(hit[key][1], max(zs))
    print(f"[mat_scene] probe: meshes crossing z {zlo:.2f}..{zhi:.2f} within 220 m")
    for k, (n, ztop) in sorted(hit.items(), key=lambda kv: -kv[1][0]):
        print(f"[mat_scene]   {n:5d} slots  top z {ztop:7.2f}  {k}")
    sys.exit(0)


if "--debug-attr" in args:
    # every ornament instance rendered as a raw emission of ORN's `cavity` attribute: black = enclosed, white = open,
    # flat mid-grey = the attribute is not reaching the shader at all.
    dm = bpy.data.materials.new("MAT_debug_cavity"); dm.use_nodes = True
    nt = dm.node_tree; nt.nodes.clear()
    an = nt.nodes.new("ShaderNodeAttribute"); an.attribute_type = "GEOMETRY"; an.attribute_name = "cavity"
    em = nt.nodes.new("ShaderNodeEmission"); nt.links.new(an.outputs["Color"], em.inputs["Color"])
    o_ = nt.nodes.new("ShaderNodeOutputMaterial"); nt.links.new(em.outputs[0], o_.inputs["Surface"])
    inst_c = bpy.data.collections.get("INSTANCES")
    n_ = 0
    for ob in (inst_c.all_objects if inst_c else []):
        if ob.type == "MESH":
            for slot in ob.material_slots:
                slot.link = "OBJECT"; slot.material = dm
            n_ += 1
    print(f"[mat_scene] debug-attr: cavity emission on {n_} instances")

hero = bpy.data.objects.get("CAM_qa_01_lagoon_hero")
hloc = hero.location.copy() if hero else Vector((-16.0, 113.9, 1.0))
# waterline: the shore / podium base in front of the rotunda, where stone, rip-rap and z = WATER_Z meet
add_cam("CAM_mat_scene_waterline", hloc, Vector((-6.0, 34.0, -1.0)), lens=200.0)
# stone: the entablature / spandrel band, QA's "clean CAD at 1:1" crop
add_cam("CAM_mat_scene_stone", hloc, Vector((-2.0, 6.0, 20.0)), lens=135.0)
# capital (round 5, QA-03-15): the hero station again, on the nearest rotunda capital. 400 mm at 768 px is exactly
# 8x the hero's angular resolution (hero = 20 mm at 1920 px), so downsampling this render by 8 reproduces the hero
# pixel for pixel -- a capital is only ~12 px wide there, and "two readable leaf tiers" has to survive that.
# only real ornament instances: ARCH's crude stand-ins (PH_capital_rotunda_*) sit at the world origin and would
# aim this camera at the middle of the rotunda floor.
inst_coll = bpy.data.collections.get("INSTANCES")
pool = list(inst_coll.all_objects) if inst_coll else list(scene.objects)
caps = [o for o in pool if o.type == "MESH" and not o.hide_render and o.name.startswith("INST_") and "capital_rotunda" in o.name]
caps = caps or [o for o in pool if o.type == "MESH" and not o.hide_render and o.name.startswith("INST_") and "capital" in o.name]
if caps:
    # matrix_world stays (0,0,0) on these until a depsgraph evaluation actually runs in background mode, even after
    # view_layer.update(); `location` / matrix_basis are correct and the instances are unparented, so use those.
    def mw(o):
        return o.matrix_world if o.matrix_world.translation.length > 1e-6 else o.matrix_basis
    near = min(caps, key=lambda o: (mw(o).translation - hloc).length)
    ctr = sum((mw(near) @ Vector(c) for c in near.bound_box), Vector()) / 8.0
    print(f"[mat_scene] capital camera on {near.name} at {[round(v,1) for v in ctr]}, "
          f"{(ctr - hloc).length:.1f} m from the hero station")
    add_cam("CAM_mat_scene_capital", hloc, ctr, lens=400.0)

import light_presets
ENGINE = str(arg("--engine", "cycles")).lower()
LOD = int(arg("--lod", 0))
if LOD:
    common.set_lod(viewport=LOD, render=LOD)
if ENGINE.startswith("ee"):
    light_presets.apply_preview_eevee(scene, samples=max(16, SAMPLES))
else:
    light_presets.apply_final_cycles(scene, samples=SAMPLES)
common.setup_scene(scene)
scene.render.image_settings.color_depth = "8"

# The merged lighting.blend still carries round 2's exposure; the lighting agent is raising it by +0.9 EV this round
# (QA-02-4). Judge materials at the exposure they will ship at, so albedo does not silently compensate for it.
# Up to four agents share one 10-core M2, and a 15 M-triangle scene at 1080p OOM'd the Metal queue mid-render
# ("Insufficient Memory ... integrator_queued_paths_array"). Guiding is the biggest optional buffer and small tiles
# cap the path-state allocation, so both are forced here regardless of what the lighting preset asked for.
cy = scene.cycles
for k, v in (("use_guiding", False), ("use_auto_tile", True), ("tile_size", 256), ("debug_use_spatial_splits", False)):
    if hasattr(cy, k):
        setattr(cy, k, v)

EV = float(arg("--ev", 0.0))
scene.view_settings.exposure += EV
print(f"[mat_scene] view exposure {scene.view_settings.exposure - EV:.4f} {EV:+.2f} EV -> {scene.view_settings.exposure:.4f}")
if "--debug-attr" in args:   # raw attribute values, no tone curve
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    scene.view_settings.exposure = 0.0

JOBS = [("waterline", "CAM_mat_scene_waterline", (1600, 900)),
        ("stone", "CAM_mat_scene_stone", (1600, 900)),
        ("hero", "CAM_qa_01_lagoon_hero", (1920, 1080)),
        ("ceiling", "CAM_qa_04_rotunda_ceiling", (1280, 720)),
        ("capital", "CAM_mat_scene_capital", (768, 768)),
        # round 7: cam03 carries ENV's colonnade walk (MAT_paving_stone, QA-05-11) and cam05 the 115 m distance
        # test for the macro amplitude (QA-05-12). Both are rendered at QA's own preview resolution.
        ("cam03", "CAM_qa_03_colonnade_walk", (1280, 720)),
        ("cam05", "CAM_qa_05_south_lawn", (1280, 720)),
        ("cam06", "CAM_qa_06_aerial", (960, 540))]
WANT = str(arg("--cams", "waterline,stone,hero")).split(",")
# --scale renders the same framing at a fraction of the resolution: the measure tools upsample back to the QA frame,
# which lighting r12 verified reproduces the 1920x1080 numbers to ~1 lum, so iteration costs (2/3)^2 of a full hero.
SCALE = float(arg("--scale", 1.0))

for short, name, res in JOBS:
    if short not in WANT:
        continue
    ob = bpy.data.objects.get(name)
    if ob is None:
        print(f"[mat_scene] camera {name} missing, skipped")
        continue
    scene.camera = ob
    scene.render.resolution_x = int(round(res[0] * SCALE / 2)) * 2
    scene.render.resolution_y = int(round(res[1] * SCALE / 2)) * 2
    res = (scene.render.resolution_x, scene.render.resolution_y)
    fp = OUT / f"{TAG}_scene_{short}.png"
    scene.render.filepath = str(fp)
    t = time.time()
    bpy.ops.render.render(write_still=True)
    print(f"[mat_scene] {short} {res[0]}x{res[1]} {SAMPLES} spp in {time.time() - t:.1f}s -> {fp.name}")

print(f"[mat_scene] done in {time.time() - t0:.1f}s")
