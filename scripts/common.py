"""Shared helpers for the Palace of Fine Arts build. Import from any build script:

    import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
    import common

Conventions (binding, see CLAUDE.md): metric, 1 BU = 1 m, origin = rotunda floor centre, +Y toward the lagoon (east),
-X = north, +X = south, z = 0 = rotunda floor slab, water at WATER_Z.
"""
import bpy, os, sys, math, time, json
from pathlib import Path
from mathutils import Vector, Euler

# ----------------------------------------------------------------------------- paths
ROOT = Path(__file__).resolve().parents[1]                     # this checkout (may be a worktree)
MAIN_ROOT = Path("/Users/dk/Projects/3d render blender 3rd attempt building")   # main checkout (has reference photos)
REFERENCE_DIR = Path(os.environ.get("PFA_REFERENCE_DIR", str(MAIN_ROOT / "reference")))
ASSETS = ROOT / "assets"
RENDERS = ROOT / "renders"
DOCS = ROOT / "docs"
BLENDER_BIN = "/Applications/Blender.app/Contents/MacOS/Blender"

ASSET_FILES = {
    "ARCH": ASSETS / "architecture.blend",
    "ORN": ASSETS / "ornament.blend",
    "MAT": ASSETS / "materials.blend",
    "ENV": ASSETS / "environment.blend",
    "LIGHT": ASSETS / "lighting.blend",
}

# ----------------------------------------------------------------------------- site constants (metres)
WATER_Z = -1.3          # lagoon surface relative to the rotunda floor slab (z=0). Confirm from docs/reference_sheet.md.
GROUND_Z = -0.4         # typical lawn level near the rotunda
LAT, LON = 37.8029, -122.4484   # Palace of Fine Arts rotunda
NORTH_DIR = Vector((-1.0, 0.0, 0.0))   # world direction of true north
EAST_DIR = Vector((0.0, 1.0, 0.0))     # world direction of true east (toward the lagoon)


def osm_to_world(x_east, y_north, z=0.0):
    """Convert reference/plans/site_local.json coordinates (+x east, +y north, origin rotunda centre)
    to world coordinates (+Y east/lagoon, -X north)."""
    return (-y_north, x_east, z)


def load_site_local():
    """OSM footprints in world coordinates: {name: [polygon(list of (x,y)), ...]}."""
    p = REFERENCE_DIR / "plans" / "site_local.json"
    data = json.loads(p.read_text())
    out = {}
    for name, polys in data.items():
        out[name] = [[osm_to_world(x, y)[:2] for (x, y) in poly] for poly in polys]
    return out


# ----------------------------------------------------------------------------- args
def script_args():
    """Arguments after '--' on the blender command line."""
    argv = sys.argv
    return argv[argv.index("--") + 1:] if "--" in argv else []


def timestamp():
    return time.strftime("%Y%m%d_%H%M%S")


# ----------------------------------------------------------------------------- scene / collections
def setup_scene(scene=None):
    """Metric units, AgX, sensible defaults. Safe to call repeatedly."""
    s = scene or bpy.context.scene
    s.unit_settings.system = "METRIC"
    s.unit_settings.scale_length = 1.0
    s.unit_settings.length_unit = "METERS"
    try:
        s.view_settings.view_transform = "AgX"
    except TypeError:
        s.view_settings.view_transform = "Filmic"
    s.render.resolution_percentage = 100
    s.render.image_settings.file_format = "PNG"
    s.render.image_settings.color_depth = "8"
    return s


def get_collection(name, parent=None, create=True):
    coll = bpy.data.collections.get(name)
    if coll is None and create:
        coll = bpy.data.collections.new(name)
    if coll is not None:
        parent = parent or bpy.context.scene.collection
        if coll.name not in parent.children and coll.name not in [c.name for c in _all_children(parent)]:
            parent.children.link(coll)
    return coll


def _all_children(coll):
    for c in coll.children:
        yield c
        yield from _all_children(c)


def clear_collection(name, remove_collection=False):
    """Delete every object (and orphan mesh/curve/light/camera data) in the collection and its children."""
    coll = bpy.data.collections.get(name)
    if coll is None:
        return
    for child in list(coll.children):
        clear_collection(child.name, remove_collection=True)
    for obj in list(coll.objects):
        data = obj.data
        bpy.data.objects.remove(obj, do_unlink=True)
        if data is not None and getattr(data, "users", 1) == 0:
            for block in (bpy.data.meshes, bpy.data.curves, bpy.data.lights, bpy.data.cameras):
                try:
                    if data.name in block and block[data.name] == data:
                        block.remove(data)
                        break
                except Exception:
                    pass
    if remove_collection:
        bpy.data.collections.remove(coll)


def rebuild_collection(name, parent=None):
    """Idempotent entry point for a builder: wipes and returns a fresh empty collection of that name."""
    clear_collection(name)
    coll = bpy.data.collections.get(name)
    if coll is None:
        coll = bpy.data.collections.new(name)
        (parent or bpy.context.scene.collection).children.link(coll)
    return coll


def purge_orphans():
    for _ in range(3):
        bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=False, do_recursive=True)


def wipe_scene():
    """Remove everything in the current file (used by build_master and placeholder builders)."""
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for coll in list(bpy.data.collections):
        bpy.data.collections.remove(coll)
    purge_orphans()


# ----------------------------------------------------------------------------- objects
def link_object(obj, coll):
    for c in list(obj.users_collection):
        c.objects.unlink(obj)
    coll.objects.link(obj)
    return obj


def new_mesh_object(name, verts, faces, coll, edges=(), smooth=False):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], list(edges), [tuple(f) for f in faces])
    me.update(calc_edges=True)
    if smooth:
        for p in me.polygons:
            p.use_smooth = True
    obj = bpy.data.objects.new(name, me)
    coll.objects.link(obj)
    return obj


def add_empty(name, location, coll, size=0.5, rotation=(0, 0, 0), display="ARROWS"):
    e = bpy.data.objects.new(name, None)
    e.empty_display_type = display
    e.empty_display_size = size
    e.location = location
    e.rotation_euler = rotation
    coll.objects.link(e)
    return e


def set_lod(viewport=1, render=0):
    """LOD manager: objects AND collections whose names end in _LOD<k>: viewport shows <viewport>, render uses <render>."""
    import re
    pat = re.compile(r"_LOD(\d)$")
    n_obj = n_coll = 0
    for obj in list(bpy.data.objects):
        m = pat.search(obj.name)
        if m:
            k = int(m.group(1))
            obj.hide_viewport = (k != viewport)
            obj.hide_render = (k != render)
            n_obj += 1
    for coll in list(bpy.data.collections):
        m = pat.search(coll.name)
        if m:
            k = int(m.group(1))
            coll.hide_viewport = (k != viewport)
            coll.hide_render = (k != render)
            n_coll += 1
    print(f"[common] set_lod viewport=LOD{viewport} render=LOD{render}: {n_obj} objects, {n_coll} collections")


def set_lod_visibility(level=1):
    """Backward-compatible alias: viewport LOD<level>, render LOD0."""
    set_lod(viewport=level, render=0)


# ----------------------------------------------------------------------------- materials
def placeholder_material(name, color=(0.7, 0.6, 0.45, 1.0), roughness=0.7):
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = color
        bsdf.inputs["Roughness"].default_value = roughness
    m["placeholder"] = True
    return m


PLACEHOLDER_COLORS = {
    "MAT_concrete_ochre": (0.42, 0.29, 0.17, 1.0),
    "MAT_concrete_podium": (0.36, 0.30, 0.22, 1.0),
    "MAT_column_rose": (0.40, 0.17, 0.12, 1.0),
    "MAT_dome_membrane": (0.70, 0.66, 0.58, 1.0),
    "MAT_column_tan_inner": (0.45, 0.32, 0.17, 1.0),
    "MAT_concrete_inner": (0.36, 0.27, 0.16, 1.0),
    "MAT_plaster_ceiling": (0.50, 0.40, 0.25, 1.0),
    "MAT_plaster_ceiling_rib": (0.42, 0.34, 0.22, 1.0),
    "MAT_drum_band": (0.28, 0.18, 0.10, 1.0),
    "MAT_concrete_colonnade": (0.44, 0.31, 0.17, 1.0),
    "MAT_ornament_concrete": (0.42, 0.29, 0.17, 1.0),
    "MAT_paving": (0.45, 0.45, 0.42, 1.0),
    "MAT_water_lagoon": (0.05, 0.10, 0.09, 1.0),
    "MAT_lawn": (0.10, 0.18, 0.05, 1.0),
    "MAT_path_gravel": (0.45, 0.42, 0.36, 1.0),
    "MAT_bark": (0.20, 0.14, 0.10, 1.0),
    "MAT_leaf": (0.08, 0.16, 0.04, 1.0),
    "MAT_soil": (0.18, 0.12, 0.08, 1.0),
}


def load_material(name, link=False):
    """Fetch a library material by name from assets/materials.blend (append). Falls back to a placeholder."""
    m = bpy.data.materials.get(name)
    if m is not None and not m.get("placeholder"):
        return m
    lib = ASSET_FILES["MAT"]
    if lib.exists():
        with bpy.data.libraries.load(str(lib), link=link) as (src, dst):
            if name in src.materials:
                dst.materials = [name]
        m2 = bpy.data.materials.get(name)
        if m2 is not None and not m2.get("placeholder"):
            if m is not None and m is not m2:
                m.user_remap(m2)
                bpy.data.materials.remove(m)
            return m2
    if m is None:
        m = placeholder_material(name, PLACEHOLDER_COLORS.get(name, (0.6, 0.55, 0.5, 1.0)))
        print(f"[common] WARNING material {name} not in library, using placeholder")
    return m


def assign_material(obj, mat):
    if obj.data is None or not hasattr(obj.data, "materials"):
        return
    if len(obj.data.materials) == 0:
        obj.data.materials.append(mat)
    else:
        obj.data.materials[0] = mat


# ----------------------------------------------------------------------------- linking between files
def link_collection(blend_path, coll_name, link=True, parent=None):
    """Link (or append) a collection from another .blend into this scene. Returns the collection or None."""
    blend_path = Path(blend_path)
    if not blend_path.exists():
        print(f"[common] missing {blend_path}, skipping {coll_name}")
        return None
    with bpy.data.libraries.load(str(blend_path), link=link) as (src, dst):
        if coll_name not in src.collections:
            print(f"[common] {blend_path.name} has no collection {coll_name}")
            return None
        dst.collections = [coll_name]
    coll = None
    for c in bpy.data.collections:
        if c.name == coll_name and (c.library is not None) == link:
            coll = c
    if coll is None:
        coll = bpy.data.collections.get(coll_name)
    parent = parent or bpy.context.scene.collection
    if coll and coll.name not in parent.children:
        parent.children.link(coll)
    return coll


def save_blend(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(path), relative_remap=True, compress=False)
    print(f"[common] saved {path}")


# ----------------------------------------------------------------------------- sun helpers
def sun_direction(azimuth_deg, elevation_deg):
    """Unit vector pointing FROM the scene TOWARD the sun, world coords. Azimuth clockwise from north (-X), east = +Y."""
    az, el = math.radians(azimuth_deg), math.radians(elevation_deg)
    horiz = NORTH_DIR * math.cos(az) + EAST_DIR * math.sin(az)
    return (horiz * math.cos(el) + Vector((0, 0, math.sin(el)))).normalized()


def aim_sun(sun_obj, azimuth_deg, elevation_deg):
    """Rotate a Sun light so its rays travel away from the sun direction."""
    d = sun_direction(azimuth_deg, elevation_deg)
    sun_obj.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    return d


# ----------------------------------------------------------------------------- render
def configure_eevee(scene=None, samples=16):
    s = scene or bpy.context.scene
    s.render.engine = "BLENDER_EEVEE"
    e = s.eevee
    e.taa_render_samples = samples
    e.use_raytracing = True
    e.use_shadows = True
    try:
        e.shadow_ray_count = 2
        e.shadow_step_count = 4
    except Exception:
        pass
    return s


def configure_cycles(scene=None, samples=256, denoise=True, device="GPU"):
    s = scene or bpy.context.scene
    s.render.engine = "CYCLES"
    c = s.cycles
    c.samples = samples
    c.device = device
    c.use_denoising = denoise
    try:
        c.denoiser = "OPENIMAGEDENOISE"
        c.denoising_use_gpu = True
    except Exception:
        pass
    c.use_adaptive_sampling = True
    c.adaptive_threshold = 0.02
    prefs = bpy.context.preferences.addons.get("cycles")
    if prefs:
        prefs.preferences.compute_device_type = "METAL"
        try:
            prefs.preferences.refresh_devices()
            for d in prefs.preferences.devices:
                d.use = d.type == "METAL"
        except Exception:
            pass
    return s


def qa_cameras(scene=None):
    """Return the QA cameras (created if absent). Import lazily to avoid a cycle."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import qa_cameras as qc
    return qc.ensure(scene or bpy.context.scene)


def render_previews(agent, cameras=None, res=(1280, 720), samples=16, tag="", engine="EEVEE", cycles_samples=64):
    """Render the fixed QA cameras (or a subset by name) into renders/previews/<agent>/<timestamp>_<cam>.png."""
    s = bpy.context.scene
    setup_scene(s)
    cams = qa_cameras(s)
    if cameras:
        cams = [c for c in cams if any(k in c.name for k in cameras)]
    if engine.upper() == "CYCLES":
        configure_cycles(s, samples=cycles_samples)
    else:
        configure_eevee(s, samples=samples)
    s.render.resolution_x, s.render.resolution_y = res
    out_dir = RENDERS / "previews" / agent
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = timestamp()
    outputs = []
    for cam in cams:
        s.camera = cam
        short = cam.name.replace("CAM_qa_", "")
        fp = out_dir / f"{ts}_{short}{('_' + tag) if tag else ''}.png"
        s.render.filepath = str(fp)
        t = time.time()
        bpy.ops.render.render(write_still=True)
        print(f"[common] rendered {fp.name} in {time.time() - t:.1f}s")
        outputs.append(fp)
    return outputs


# ----------------------------------------------------------------------------- extensions
def ensure_extension(pkg_id):
    """Install + enable a blender.org extension headless (needs network). Returns True if enabled."""
    import addon_utils
    mod = f"bl_ext.blender_org.{pkg_id}"
    if addon_utils.check(mod)[1]:
        return True
    bpy.context.preferences.system.use_online_access = True
    try:
        bpy.ops.extensions.package_install(repo_index=0, pkg_id=pkg_id, enable_on_install=True)
        bpy.ops.wm.save_userpref()
    except Exception as e:
        print(f"[common] extension {pkg_id} install failed: {e}")
    return addon_utils.check(mod)[1]


def enable_addon(module):
    import addon_utils
    try:
        addon_utils.enable(module, default_set=True, persistent=True)
        return True
    except Exception as e:
        print(f"[common] enable {module} failed: {e}")
        return False


# ----------------------------------------------------------------------------- geometry helpers
def octagon_face_centers(apothem, rotation_deg=8.0):
    """Centres and outward normals of the 8 rotunda faces. rotation_deg = angle of face 0 from +Y (lagoon side)."""
    out = []
    for k in range(8):
        a = math.radians(rotation_deg + 45 * k)
        n = Vector((math.sin(a), math.cos(a), 0.0))   # face 0 points toward +Y (lagoon) when rotation_deg=0
        out.append((n * apothem, n))
    return out


def lookat_rotation(location, target, roll=0.0):
    d = Vector(target) - Vector(location)
    rot = d.to_track_quat("-Z", "Y").to_euler()
    if roll:
        rot.rotate_axis("Z", roll)
    return rot
