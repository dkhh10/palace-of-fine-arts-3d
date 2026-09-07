"""Assemble master.blend from the specialist asset files (lead-owned).
    blender -b --python scripts/build_master.py [-- --link] [-- --preview] [-- --no-env] [-- --render-lod N]
Default APPENDS every asset collection (local, editable, materials remappable); --link links instead.
Steps: append ARCH/ENV/ORN/LIGHT + world -> instance ORN assets onto ARCH sockets -> remap placeholder materials to
assets/materials.blend -> LODs (viewport LOD1, render LOD0) -> QA cameras -> lighting look -> save.
"""
import bpy, sys, os, math, re
from pathlib import Path
from mathutils import Matrix, Vector
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common
import qa_cameras

args = common.script_args()
LINK = "--link" in args
ROOT = common.ROOT
RENDER_LOD = int(args[args.index("--render-lod") + 1]) if "--render-lod" in args else 0

bpy.ops.wm.read_homefile(use_empty=True)
common.wipe_scene()
scene = common.setup_scene()
scene.name = "PalaceOfFineArts"


def layer_coll(name, root=None):
    root = root or bpy.context.view_layer.layer_collection
    if root.name == name:
        return root
    for ch in root.children:
        r = layer_coll(name, ch)
        if r:
            return r
    return None


# ----------------------------------------------------------------------------- 1. bring in the assets
linked = {}
plan = [("ARCH", "ARCH"), ("ENV", "ENV"), ("ORN", "ORN"), ("LIGHT", "LIGHT")]
if "--no-env" in args:
    plan = [p for p in plan if p[0] != "ENV"]
for key, coll_name in plan:
    path = common.ASSET_FILES[key]
    if not path.exists():
        print(f"[build_master] {key}: {path.name} missing")
        continue
    coll = common.link_collection(path, coll_name, link=LINK)
    if coll:
        linked[key] = coll
if "ARCH" not in linked and (common.ASSETS / "placeholder_blockout.blend").exists():
    linked["ARCH"] = common.link_collection(common.ASSETS / "placeholder_blockout.blend", "PLACEHOLDER", link=LINK)

# world
world = None
light_file = common.ASSET_FILES["LIGHT"]
if light_file.exists():
    with bpy.data.libraries.load(str(light_file), link=LINK) as (src, dst):
        if "WORLD_golden_hour" in src.worlds:
            dst.worlds = ["WORLD_golden_hour"]
    world = bpy.data.worlds.get("WORLD_golden_hour")
if world is None:
    world = bpy.data.worlds.new("WORLD_placeholder")
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs[0].default_value = (0.55, 0.65, 0.85, 1.0)
scene.world = world
if "LIGHT" not in linked:
    lc = common.rebuild_collection("LIGHT_placeholder")
    sun = bpy.data.lights.new("LIGHT_sun_placeholder", "SUN"); sun.energy = 4.0; sun.angle = 0.0093; sun.color = (1.0, 0.75, 0.5)
    so = bpy.data.objects.new("LIGHT_sun_placeholder", sun); lc.objects.link(so); common.aim_sun(so, 118.5, 7.4)

# ----------------------------------------------------------------------------- 2. ornament onto sockets
ORN_COLL = {
    "capital_rotunda": "ORN_capital_rotunda", "capital_inner": "ORN_capital_inner", "capital_colonnade": "ORN_capital_colonnade",
    "maiden": "ORN_maiden", "attic_figure": "ORN_attic_figure", "attic_panel": "ORN_attic_panel", "keystone": "ORN_keystone",
    "inner_figure": "ORN_winged_figure", "finial": "ORN_finial", "rosette_ceiling": "ORN_rosette_ceiling",
}
ROT_Z_FIX = {"inner_figure": math.pi}   # ARCH socket +Y = facing direction; ORN asset +Y = back (contract) -> turn 180
DESIGN_VARIANT = {"A": 1, "B": 2, "C": 3}
lod_pat = re.compile(r"^(ORN_.+?)_v(\d+)_LOD(\d)$")


def orn_variants(coll_name):
    """{variant_index: {lod: object}} for one ORN sub-collection."""
    coll = bpy.data.collections.get(coll_name)
    out = {}
    if coll is None:
        return out
    for o in coll.all_objects:
        m = lod_pat.match(o.name)
        if m and o.type == "MESH":
            out.setdefault(int(m.group(2)), {})[int(m.group(3))] = o
    return out


def place(ob, M):
    """Robust world placement for a fresh, not-yet-evaluated object (matrix_world setter is unreliable here)."""
    loc, rot, sca = M.decompose()
    ob.rotation_mode = "QUATERNION"
    ob.location = loc
    ob.rotation_quaternion = rot
    ob.scale = sca


def resolve_orn_path(p):
    p = str(p)
    if p.startswith("//"):
        return str(common.ASSETS / p[2:])
    return p


_orn_mat_cache = {}


def orn_material_for(src_obj, variant_key):
    """Per-asset copy of MAT_ornament_concrete with that asset's baked maps plugged into nodes named ORN_NORMAL / ORN_AO."""
    base = bpy.data.materials.get("MAT_ornament_concrete")
    if base is None or base.get("placeholder") or not base.use_nodes or "normal_map" not in src_obj.keys():
        return None
    if variant_key in _orn_mat_cache:
        return _orn_mat_cache[variant_key]
    if base.node_tree.nodes.get("ORN_NORMAL") is None:
        _orn_mat_cache[variant_key] = None
        return None
    m = base.copy(); m.name = f"MAT_ornament_concrete__{variant_key}"
    for prop, node_name, cs in (("normal_map", "ORN_NORMAL", "Non-Color"), ("ao_map", "ORN_AO", "Non-Color")):
        node = m.node_tree.nodes.get(node_name)
        path = src_obj.get(prop)
        if node and path and Path(resolve_orn_path(path)).exists():
            img = bpy.data.images.load(resolve_orn_path(path), check_existing=True)
            img.colorspace_settings.name = cs
            node.image = img
    _orn_mat_cache[variant_key] = m
    return m


inst_root = None
counts = {}
skipped = {}
if "ORN" in linked and "ARCH" in linked:
    bpy.context.view_layer.update()   # appended objects have stale matrix_world until the depsgraph runs
    inst_root = common.rebuild_collection("INSTANCES")
    sockets = [o for o in bpy.data.objects if o.name.startswith("SOCKET_") and o.get("orn_type")]
    at_origin = sum(1 for o in sockets if o.matrix_world.translation.length < 0.01)
    print(f"[build_master] {len(sockets)} sockets, {at_origin} at the origin (should be 0)")
    sub = {}
    for idx_all, sk in enumerate(sorted(sockets, key=lambda o: o.name)):
        t = sk["orn_type"]
        seed = int(sk.get("variant_seed", 0))
        coll_name = ORN_COLL.get(t)
        if t == "urn":
            coll_name = "ORN_urn_niche" if float(sk.get("size_hint", 3.0)) <= 2.0 else "ORN_urn"
        if t == "finial" and sk.get("subtype") == "volute_scroll":
            coll_name = "ORN_corner_scroll"   # paired volute scrolls over the attic corner figures (QA-01-13)
        if t == "drum_band":
            variants = orn_variants("ORN_drum_band")
            if not variants:
                skipped[t] = skipped.get(t, 0) + 1; continue
            v = variants[sorted(variants)[0]]
            unit_len = max(v[min(v)].dimensions.x, 0.3)
            n = max(8, int(round(float(sk.get("run_length", 113.4)) / unit_len)))
            sc = sub.setdefault(t, common.get_collection("INST_drum_band", parent=inst_root))
            for i in range(n):
                rot = Matrix.Rotation(2 * math.pi * i / n, 4, "Z")
                for lod, src in v.items():
                    ob = bpy.data.objects.new(f"INST_drum_band_{i:03d}_LOD{lod}", src.data)
                    place(ob, rot @ sk.matrix_world)
                    ob["instance_seed"] = i; ob["orn_type"] = t
                    sc.objects.link(ob)
            counts[t] = counts.get(t, 0) + n
            continue
        if coll_name is None:
            skipped[t] = skipped.get(t, 0) + 1
            continue
        variants = orn_variants(coll_name)
        if not variants:
            skipped[t] = skipped.get(t, 0) + 1
            continue
        keys = sorted(variants)
        vi = DESIGN_VARIANT.get(sk.get("design"), None)
        vi = vi if vi in variants else keys[(idx_all * 7919 + seed * 104729) % len(keys)]   # spread variants evenly
        lods = variants[vi]
        sc = sub.setdefault(t, common.get_collection(f"INST_{t}", parent=inst_root))
        idx = counts.get(t, 0)
        fix = Matrix.Rotation(ROT_Z_FIX.get(t, 0.0), 4, "Z")
        for lod, src in lods.items():
            ob = bpy.data.objects.new(f"INST_{t}_{idx:03d}_LOD{lod}", src.data)
            place(ob, sk.matrix_world @ fix)
            ob["instance_seed"] = seed; ob["orn_type"] = t; ob["variant"] = vi
            ob.parent = sk if False else None
            sc.objects.link(ob)
            mat = orn_material_for(src, f"{coll_name}_v{vi}_LOD{lod}")
            if mat is not None:
                for slot_i in range(len(ob.material_slots)):
                    ob.material_slots[slot_i].link = "OBJECT"; ob.material_slots[slot_i].material = mat
        counts[t] = idx + 1
    print("[build_master] ornament instanced:", counts, "skipped:", skipped)
    bad = [o.name for o in inst_root.all_objects if o.location.length < 0.01]
    print(f"[build_master] instances at the origin: {len(bad)} (should be 0)", bad[:3])
    # sources out of the view layer, ARCH's crude stand-ins off
    for name in ("ORN", "ARCH_placeholders"):
        lc = layer_coll(name)
        if lc:
            lc.exclude = True

# ----------------------------------------------------------------------------- 3. materials from the library
mat_lib = common.ASSET_FILES["MAT"]
if mat_lib.exists():
    with bpy.data.libraries.load(str(mat_lib), link=False) as (src, dst):
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
    print(f"[build_master] materials: {len(wanted)} library materials appended, {remapped} placeholders remapped")
    # per-asset ornament maps need the real MAT_ornament_concrete: redo the instance material pass
    if inst_root is not None:
        _orn_mat_cache.clear()
        for ob in inst_root.all_objects:
            if "variant" not in ob.keys():
                continue
            src_name = None
            m = re.match(r"^INST_(.+?)_(\d{3})_LOD(\d)$", ob.name)
            if not m:
                continue
            lod = int(m.group(3)); t = m.group(1)
            for o in bpy.data.objects:
                if o.data == ob.data and o.name.startswith("ORN_"):
                    src_name = o; break
            if src_name is None:
                continue
            mat = orn_material_for(src_name, src_name.name)
            if mat is not None:
                for slot_i in range(len(ob.material_slots)):
                    ob.material_slots[slot_i].link = "OBJECT"; ob.material_slots[slot_i].material = mat
else:
    print("[build_master] no materials library yet; placeholders stay")

# ----------------------------------------------------------------------------- 4. LODs, cameras, look, save
common.set_lod(viewport=1, render=RENDER_LOD)
qa_cameras.ensure(scene)
common.configure_eevee(scene, samples=32)
scene.render.resolution_x, scene.render.resolution_y = 1920, 1080
if "LIGHT" in linked:
    try:
        import light_presets
        light_presets.apply_look(scene, link=LINK)
    except Exception as e:
        print("[build_master] light_presets.apply_look failed:", e)

tri = 0
dg = bpy.context.evaluated_depsgraph_get()
for ob in bpy.data.objects:
    if ob.type == "MESH" and not ob.hide_viewport:
        tri += sum(len(p.vertices) - 2 for p in ob.data.polygons)
print(f"[build_master] viewport (LOD1) triangles ~{tri/1e6:.2f} M; objects {len(bpy.data.objects)}")

out = ROOT / "master.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(out), relative_remap=True, compress=True)
print(f"[build_master] saved {out} ({out.stat().st_size/1e6:.0f} MB); assets: {sorted(linked)}")

if "--preview" in args:
    common.render_previews("lead", samples=32)
